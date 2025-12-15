# Soni v3.0 - Arquitectura con Subgrafos

Este documento detalla cómo implementar las ideas de `ideas.md` en el diseño actual de Soni, con especial enfoque en la arquitectura de **subgrafos de LangGraph**.

## Motivacion

### Problema del Diseno Actual (v2.0)

Soni v2.0 usa un **grafo monolitico** donde:
- Un solo `StateGraph` con nodos genericos
- Los nodos (`collect_next_slot`, `confirm_action`, etc.) manejan TODOS los flows
- El `flow_stack` determina que flow esta activo
- La logica de cada flow esta dispersa en nodos genericos

```
ACTUAL (v2.0):
┌─────────────────────────────────────────┐
│          Grafo Monolitico               │
│  ┌─────────────────────────────────┐    │
│  │ understand -> execute_commands  │    │
│  │ -> collect_slot -> confirm ->   │    │
│  │ action                          │    │
│  └─────────────────────────────────┘    │
│     (nodos genericos para TODO)         │
└─────────────────────────────────────────┘
```

### Solucion Propuesta (v3.0)

**1 Flow YAML = 1 Subgrafo LangGraph**

```
PROPUESTO (v3.0):
┌─────────────────────────────────────────────────────────────┐
│                    Orchestrator Graph                        │
│  ┌─────────────────────────────────────────────────────┐    │
│  │ understand -> route_to_flow -> [subgrafo] -> END    │    │
│  └─────────────────────────────────────────────────────┘    │
└───────────────────────────┬─────────────────────────────────┘
                            │
          ┌─────────────────┼─────────────────┐
          ▼                 ▼                 ▼
    ┌──────────┐      ┌──────────┐      ┌──────────┐
    │ book_    │      │ cancel_  │      │ check_   │
    │ flight   │      │ booking  │      │ status   │
    │ Subgraph │      │ Subgraph │      │ Subgraph │
    └──────────┘      └──────────┘      └──────────┘
```

---

## Arquitectura en 3 Capas (de ideas.md)

### Capa 1: Definicion Declarativa (YAML)

Sin cambios significativos. El DSL actual ya soporta esto:

```yaml
flows:
  book_flight:
    description: "Book a flight reservation"

    slots:
      origin:
        type: city
        prompt: "Where would you like to fly from?"
      destination:
        type: city
        prompt: "Where would you like to fly to?"
      departure_date:
        type: date
        prompt: "What date would you like to depart?"

    process:
      - step: collect_origin
        type: collect
        slot: origin

      - step: collect_destination
        type: collect
        slot: destination

      - step: collect_date
        type: collect
        slot: departure_date

      - step: search
        type: action
        call: search_flights

      - step: check_results
        type: branch
        when:
          - condition: "result_count == 0"
            then: no_flights
          - else: show_flights

      - step: no_flights
        type: say
        message: "No flights found. Try different dates?"
        jump_to: collect_date

      - step: show_flights
        type: collect
        slot: selected_flight
        from: flights

      - step: confirm
        type: confirm
        message: |
          Please confirm:
          - From: {origin}
          - To: {destination}
          - Date: {departure_date}
          - Flight: {selected_flight.flight_number}
        on_yes: book
        on_no: collect_origin

      - step: book
        type: action
        call: book_flight
```

### Capa 2: Orquestacion con LangGraph (NUEVO)

**Cambio clave**: Un compilador convierte cada flow YAML en un subgrafo LangGraph.

```
flows/
├── book_flight.yaml    ──┐
├── cancel_booking.yaml ──┼──> FlowCompiler ──> CompiledFlows{
└── check_status.yaml   ──┘                      "book_flight": CompiledGraph,
                                                 "cancel_booking": CompiledGraph,
                                                 "check_status": CompiledGraph
                                               }
```

### Capa 3: Inteligencia con DSPy

Sin cambios. SoniDU sigue produciendo Commands que el Orchestrator ejecuta.

---

## Componentes Nuevos

### 1. FlowCompiler

Convierte YAML flows a subgrafos LangGraph en tiempo de startup.

```python
class FlowCompiler:
    """Compiles YAML flows to LangGraph subgraphs."""

    def __init__(self, config: SoniConfig):
        self.config = config
        self.node_factories = {
            "collect": CollectNodeFactory(),
            "action": ActionNodeFactory(),
            "branch": BranchNodeFactory(),
            "confirm": ConfirmNodeFactory(),
            "say": SayNodeFactory(),
            "generate": GenerateNodeFactory(),
            "call_flow": CallFlowNodeFactory(),
            "set": SetNodeFactory(),
            "handoff": HandoffNodeFactory(),
        }

    def compile_all(self, flows_dir: Path) -> dict[str, CompiledGraph]:
        """Compile all YAML flows to subgraphs."""
        compiled = {}
        for yaml_file in flows_dir.glob("*.yaml"):
            flow_def = self._load_yaml(yaml_file)
            for flow_name, flow_config in flow_def.get("flows", {}).items():
                compiled[flow_name] = self.compile_flow(flow_name, flow_config)
        return compiled

    def compile_flow(self, flow_name: str, flow_config: dict) -> CompiledGraph:
        """Compile single flow to subgraph."""
        builder = StateGraph(FlowState)

        # Build nodes from steps
        steps = flow_config["process"]
        for step in steps:
            node_name = step["step"]
            step_type = step["type"]

            # Get factory and create node
            factory = self.node_factories[step_type]
            node_fn = factory.create(step, flow_config)
            builder.add_node(node_name, node_fn)

        # Build edges
        self._add_edges(builder, steps, flow_config)

        return builder.compile()
```

### 2. Node Factories

Cada step type tiene una factory que genera la funcion del nodo:

```python
class CollectNodeFactory:
    """Factory for collect step nodes."""

    def create(self, step: dict, flow_config: dict) -> Callable:
        slot_name = step["slot"]
        slot_config = flow_config["slots"].get(slot_name, {})

        async def collect_node(state: FlowState) -> dict:
            # Check if slot already filled
            if state["slots"].get(slot_name) and not step.get("force"):
                return {"step_status": "skipped"}

            # Request slot value via interrupt
            prompt = step.get("prompt") or slot_config.get("prompt", f"Please provide {slot_name}")
            user_response = interrupt({
                "type": "slot_request",
                "slot": slot_name,
                "prompt": prompt
            })

            return {
                "pending_slot": slot_name,
                "user_response": user_response,
                "step_status": "waiting"
            }

        collect_node.__name__ = f"collect_{slot_name}"
        return collect_node


class ActionNodeFactory:
    """Factory for action step nodes."""

    def create(self, step: dict, flow_config: dict) -> Callable:
        action_name = step["call"]
        output_mapping = step.get("map_outputs", {})

        async def action_node(
            state: FlowState,
            runtime: Runtime[RuntimeContext]
        ) -> dict:
            handler = runtime.context["action_handler"]

            # Execute with current slots as inputs
            result = await handler.execute(action_name, state["slots"])

            # Map outputs to slots
            slot_updates = {}
            for action_output, state_key in output_mapping.items():
                if action_output in result:
                    slot_updates[state_key] = result[action_output]

            # If no mapping, use action outputs directly
            if not output_mapping:
                slot_updates = result

            return {
                "slots": {**state["slots"], **slot_updates},
                "step_status": "completed"
            }

        action_node.__name__ = f"action_{action_name}"
        return action_node


class BranchNodeFactory:
    """Factory for branch step nodes."""

    def create(self, step: dict, flow_config: dict) -> Callable:
        conditions = step["when"]

        def branch_node(state: FlowState) -> dict:
            # Evaluate conditions in order
            for condition in conditions:
                if "condition" in condition:
                    if self._evaluate(condition["condition"], state["slots"]):
                        return {"next_step": condition["then"]}
                elif "else" in condition:
                    return {"next_step": condition["else"]}

            return {"next_step": "__end__"}

        branch_node.__name__ = f"branch_{step['step']}"
        return branch_node

    def _evaluate(self, condition: str, context: dict) -> bool:
        """Evaluate condition expression."""
        # Simple expression evaluator
        # In production, use a proper expression parser
        try:
            return eval(condition, {"__builtins__": {}}, context)
        except Exception:
            return False


class ConfirmNodeFactory:
    """Factory for confirm step nodes."""

    def create(self, step: dict, flow_config: dict) -> Callable:
        message_template = step["message"]
        on_yes = step.get("on_yes", "__next__")
        on_no = step.get("on_no", "__cancel__")

        async def confirm_node(state: FlowState) -> dict:
            # Interpolate message with slots
            message = self._interpolate(message_template, state["slots"])

            # Request confirmation via interrupt
            user_response = interrupt({
                "type": "confirmation",
                "message": message,
                "options": ["yes", "no"]
            })

            return {
                "confirmation_response": user_response,
                "confirmation_on_yes": on_yes,
                "confirmation_on_no": on_no,
                "step_status": "waiting"
            }

        confirm_node.__name__ = f"confirm_{step['step']}"
        return confirm_node

    def _interpolate(self, template: str, context: dict) -> str:
        """Interpolate {var} placeholders."""
        import re
        def replacer(match):
            key = match.group(1)
            parts = key.split(".")
            value = context
            for part in parts:
                value = value.get(part, f"{{{key}}}")
                if not isinstance(value, dict):
                    break
            return str(value)
        return re.sub(r"\{([^}]+)\}", replacer, template)


class SayNodeFactory:
    """Factory for say step nodes."""

    def create(self, step: dict, flow_config: dict) -> Callable:
        message_template = step.get("message", "")

        async def say_node(state: FlowState) -> dict:
            message = self._interpolate(message_template, state["slots"])
            return {
                "response": message,
                "step_status": "completed"
            }

        say_node.__name__ = f"say_{step['step']}"
        return say_node

    def _interpolate(self, template: str, context: dict) -> str:
        import re
        def replacer(match):
            key = match.group(1)
            return str(context.get(key, f"{{{key}}}"))
        return re.sub(r"\{([^}]+)\}", replacer, template)
```

### 3. OrchestratorGraph

Grafo principal que coordina entre subgrafos:

```python
class OrchestratorGraph:
    """Main graph that routes to flow subgraphs."""

    def __init__(
        self,
        compiled_flows: dict[str, CompiledGraph],
        nlu_provider: INLUProvider,
        command_executor: CommandExecutor,
        checkpointer: BaseCheckpointSaver
    ):
        self.flows = compiled_flows
        self.nlu = nlu_provider
        self.executor = command_executor
        self.graph = self._build_graph(checkpointer)

    def _build_graph(self, checkpointer) -> CompiledGraph:
        builder = StateGraph(DialogueState)

        # Core orchestrator nodes
        builder.add_node("understand", self._understand_node)
        builder.add_node("execute_commands", self._execute_commands_node)
        builder.add_node("generate_response", self._generate_response_node)

        # Add flow subgraphs as nodes
        for flow_name, subgraph in self.flows.items():
            builder.add_node(
                f"flow_{flow_name}",
                self._wrap_subgraph(flow_name, subgraph)
            )

        # Entry point
        builder.add_edge(START, "understand")
        builder.add_edge("understand", "execute_commands")

        # Route after commands
        builder.add_conditional_edges(
            "execute_commands",
            self._route_after_commands,
            {
                **{f"flow_{name}": f"flow_{name}" for name in self.flows},
                "generate_response": "generate_response",
            }
        )

        # Route after each flow subgraph
        for flow_name in self.flows:
            builder.add_conditional_edges(
                f"flow_{flow_name}",
                self._route_after_flow,
                {
                    "continue": f"flow_{flow_name}",
                    "complete": "generate_response",
                    "intent_change": "understand",
                }
            )

        builder.add_edge("generate_response", END)

        return builder.compile(checkpointer=checkpointer)

    def _wrap_subgraph(self, flow_name: str, subgraph: CompiledGraph):
        """Wrap subgraph to sync state with orchestrator."""

        async def wrapped(state: DialogueState) -> dict:
            # Extract flow-specific state
            flow_state = self._extract_flow_state(state)

            # Run subgraph
            result = await subgraph.ainvoke(flow_state)

            # Sync back to global state
            return self._merge_flow_result(state, result)

        wrapped.__name__ = f"flow_{flow_name}"
        return wrapped

    def _extract_flow_state(self, state: DialogueState) -> FlowState:
        """Extract flow-specific state from global state."""
        current = state.get("current_flow_state") or {}
        return {
            "flow_id": state.get("active_flow_id", ""),
            "slots": current.get("slots", {}),
            "current_step": current.get("current_step"),
            "pending_slot": None,
            "user_response": state["user_message"],
            "flow_status": "active",
            "outputs": {},
            "response": ""
        }

    def _merge_flow_result(self, state: DialogueState, result: FlowState) -> dict:
        """Merge flow result back to global state."""
        return {
            "current_flow_state": result,
            "last_response": result.get("response", ""),
        }

    def _route_after_commands(self, state: DialogueState) -> str:
        """Route based on commands executed."""
        active_flow = state.get("active_flow_name")
        if active_flow and active_flow in self.flows:
            return f"flow_{active_flow}"
        return "generate_response"

    def _route_after_flow(self, state: DialogueState) -> str:
        """Route after flow subgraph returns."""
        flow_state = state.get("current_flow_state", {})
        status = flow_state.get("flow_status", "active")

        if status == "completed":
            return "complete"
        elif status == "intent_change":
            return "intent_change"
        else:
            return "continue"

    async def process_message(self, msg: str, user_id: str) -> str:
        """Process user message."""
        config = {"configurable": {"thread_id": user_id}}

        current_state = await self.graph.aget_state(config)

        if current_state.next:
            # Resume interrupted conversation
            from langgraph.types import Command
            result = await self.graph.ainvoke(
                Command(resume=msg),
                config=config
            )
        else:
            # New turn
            result = await self.graph.ainvoke(
                {"user_message": msg},
                config=config
            )

        return result.get("last_response", "")
```

### 4. FlowState (TypedDict para subgrafos)

```python
from typing import TypedDict, Literal, Any

class FlowState(TypedDict):
    """State for a single flow subgraph."""

    flow_id: str
    """Unique instance ID."""

    slots: dict[str, Any]
    """Slot values collected in this flow."""

    current_step: str | None
    """Current step name."""

    pending_slot: str | None
    """Slot waiting for user input."""

    user_response: str | None
    """Latest user response."""

    flow_status: Literal["active", "completed", "cancelled", "error", "intent_change"]
    """Current flow status."""

    outputs: dict[str, Any]
    """Final outputs when flow completes."""

    response: str
    """Response to send to user."""

    step_status: str | None
    """Status of current step (completed, waiting, skipped)."""

    next_step: str | None
    """Override for next step (from branch)."""

    confirmation_response: str | None
    """User's confirmation response."""

    confirmation_on_yes: str | None
    """Step to go to on yes."""

    confirmation_on_no: str | None
    """Step to go to on no."""
```

---

## Edge Generation

El compilador genera edges automaticamente basandose en los steps:

```python
class EdgeBuilder:
    """Builds edges for compiled flow subgraphs."""

    def build_edges(
        self,
        builder: StateGraph,
        steps: list[dict],
        flow_config: dict
    ) -> None:
        """Generate all edges for the flow."""

        # Entry point
        if steps:
            builder.add_edge(START, steps[0]["step"])

        for i, step in enumerate(steps):
            step_name = step["step"]
            step_type = step["type"]
            next_step = self._get_next_step(steps, i)

            if step_type == "branch":
                self._add_branch_edges(builder, step, steps)

            elif step_type in ("collect", "confirm"):
                # These steps need validation after interrupt
                validate_name = f"{step_name}_validate"
                builder.add_node(validate_name, self._create_validate_node(step))
                builder.add_edge(step_name, validate_name)

                # After validation: valid -> next, invalid -> retry
                builder.add_conditional_edges(
                    validate_name,
                    self._validation_router,
                    {
                        "valid": next_step or END,
                        "invalid": step_name,
                        "intent_change": END,  # Signal to orchestrator
                    }
                )

            elif step.get("jump_to"):
                # Explicit jump
                target = step["jump_to"]
                if target == "end":
                    builder.add_edge(step_name, END)
                else:
                    builder.add_edge(step_name, target)

            else:
                # Sequential edge
                if next_step:
                    builder.add_edge(step_name, next_step)
                else:
                    builder.add_edge(step_name, END)

    def _add_branch_edges(
        self,
        builder: StateGraph,
        step: dict,
        steps: list[dict]
    ) -> None:
        """Add conditional edges for branch step."""
        step_name = step["step"]
        routes = {}

        for condition in step["when"]:
            if "then" in condition:
                target = condition["then"]
                if target == "end":
                    routes[target] = END
                elif target == "continue":
                    next_step = self._get_step_after(steps, step_name)
                    routes["continue"] = next_step or END
                else:
                    routes[target] = target

            if "else" in condition:
                target = condition["else"]
                if target == "end":
                    routes["__else__"] = END
                else:
                    routes["__else__"] = target

        builder.add_conditional_edges(
            step_name,
            self._branch_router,
            routes
        )

    def _branch_router(self, state: FlowState) -> str:
        """Route based on branch evaluation."""
        return state.get("next_step", "__else__")

    def _validation_router(self, state: FlowState) -> str:
        """Route based on validation result."""
        status = state.get("step_status")
        if status == "valid" or status == "completed":
            return "valid"
        elif status == "intent_change":
            return "intent_change"
        else:
            return "invalid"

    def _get_next_step(self, steps: list[dict], current_index: int) -> str | None:
        """Get the next step name, or None if last."""
        if current_index + 1 < len(steps):
            return steps[current_index + 1]["step"]
        return None

    def _get_step_after(self, steps: list[dict], step_name: str) -> str | None:
        """Get step that comes after the named step."""
        for i, step in enumerate(steps):
            if step["step"] == step_name:
                return self._get_next_step(steps, i)
        return None

    def _create_validate_node(self, step: dict):
        """Create validation node for collect/confirm steps."""
        step_type = step["type"]

        async def validate_node(
            state: FlowState,
            runtime: Runtime[RuntimeContext]
        ) -> dict:
            if step_type == "collect":
                return await self._validate_slot(state, step, runtime)
            elif step_type == "confirm":
                return self._validate_confirmation(state, step)
            return {"step_status": "valid"}

        validate_node.__name__ = f"{step['step']}_validate"
        return validate_node

    async def _validate_slot(
        self,
        state: FlowState,
        step: dict,
        runtime: Runtime[RuntimeContext]
    ) -> dict:
        """Validate collected slot value."""
        slot_name = step["slot"]
        user_response = state.get("user_response", "")

        # Get validator and normalizer
        validator = runtime.context.get("validator")
        normalizer = runtime.context.get("normalizer")

        try:
            # Normalize value
            normalized = user_response
            if normalizer:
                normalized = await normalizer.normalize(slot_name, user_response)

            # Validate
            is_valid = True
            if validator:
                is_valid = await validator.validate(slot_name, normalized, state["slots"])

            if is_valid:
                # Store in slots
                new_slots = {**state["slots"], slot_name: normalized}
                return {
                    "slots": new_slots,
                    "step_status": "valid",
                    "pending_slot": None
                }
            else:
                return {"step_status": "invalid"}

        except Exception:
            return {"step_status": "invalid"}

    def _validate_confirmation(self, state: FlowState, step: dict) -> dict:
        """Validate confirmation response."""
        response = state.get("confirmation_response", "").lower()

        if response in ("yes", "si", "confirm", "ok", "sure"):
            return {
                "step_status": "valid",
                "next_step": state.get("confirmation_on_yes", "__next__")
            }
        elif response in ("no", "cancel", "nope"):
            on_no = state.get("confirmation_on_no", "__cancel__")
            if on_no == "__cancel__":
                return {
                    "step_status": "valid",
                    "flow_status": "cancelled"
                }
            return {
                "step_status": "valid",
                "next_step": on_no
            }
        else:
            # Unclear response, might be slot correction or intent change
            return {"step_status": "invalid"}
```

---

## Ejemplo de Compilacion

### Input YAML

```yaml
# book_flight.yaml
flows:
  book_flight:
    description: "Book a flight"

    slots:
      origin:
        type: city
        prompt: "Where from?"
      destination:
        type: city
        prompt: "Where to?"

    process:
      - step: collect_origin
        type: collect
        slot: origin

      - step: collect_destination
        type: collect
        slot: destination

      - step: search
        type: action
        call: search_flights

      - step: confirm
        type: confirm
        message: "Book {origin} to {destination}?"
        on_yes: book
        on_no: end

      - step: book
        type: action
        call: book_flight
```

### Output: Compiled Subgraph

```
book_flight Subgraph:

START
  │
  ▼
collect_origin ◄─────────────────────┐
  │                                  │
  ▼                                  │
collect_origin_validate ─────────────┘
  │                        (invalid)
  │ (valid)
  ▼
collect_destination ◄────────────────┐
  │                                  │
  ▼                                  │
collect_destination_validate ────────┘
  │                        (invalid)
  │ (valid)
  ▼
search
  │
  ▼
confirm ◄────────────────────────────┐
  │                                  │
  ▼                                  │
confirm_validate                     │
  │         │                        │
  │ (on_no) └────────────► END       │
  │                                  │
  │ (on_yes)                         │
  ▼                                  │
book                                 │
  │                                  │
  ▼                                  │
END                                  │
```

---

## Estructura de Proyecto

```
src/soni/
├── compiler/                    # NEW
│   ├── __init__.py
│   ├── flow_compiler.py         # FlowCompiler
│   ├── edge_builder.py          # EdgeBuilder
│   └── node_factories/          # Factory per step type
│       ├── __init__.py
│       ├── base.py              # NodeFactory protocol
│       ├── collect.py
│       ├── action.py
│       ├── branch.py
│       ├── confirm.py
│       ├── say.py
│       ├── generate.py
│       ├── call_flow.py
│       ├── set.py
│       └── handoff.py
│
├── dm/
│   ├── orchestrator.py          # NEW - OrchestratorGraph
│   ├── builder.py               # MODIFIED - builds orchestrator
│   ├── executor.py              # CommandExecutor (unchanged)
│   └── nodes/                   # REDUCED - only orchestrator nodes
│       ├── __init__.py
│       ├── understand.py
│       ├── execute_commands.py
│       └── generate_response.py
│
├── flow/
│   ├── manager.py               # MODIFIED - manages subgraph instances
│   ├── state.py                 # NEW - FlowState TypedDict
│   └── stack.py                 # Flow stack management
│
├── core/
│   └── types.py                 # MODIFIED - add FlowState
│
└── ...
```

---

## Documentos de Diseno a Modificar

### 1. `02-architecture.md`

- Agregar seccion "Orchestrator + Subgraphs Architecture"
- Actualizar diagrama de capas
- Documentar flujo de compilacion

### 2. `03-components.md`

- Agregar `FlowCompiler`
- Agregar `OrchestratorGraph`
- Agregar `NodeFactory` protocol
- Reducir seccion de nodos DM

### 3. `08-langgraph-integration.md`

- Nueva seccion "Subgraph Pattern"
- Documentar comunicacion orchestrator <-> subgraph
- Actualizar ejemplos de Graph Construction

### 4. `07-flow-management.md`

- Actualizar `FlowManager` para gestionar subgrafos
- Documentar `FlowState` TypedDict
- Actualizar patron de stack

### 5. Crear `13-flow-compiler.md` (NUEVO)

- Especificacion completa del compilador
- Documentar todas las NodeFactories
- Ejemplos de compilacion

---

## Beneficios

| Aspecto | Antes (v2.0) | Despues (v3.0) |
|---------|--------------|----------------|
| **Modularidad** | Baja - nodos genericos | Alta - flow = subgraph |
| **Testing** | Dificil aislar | Test unitario por flow |
| **Compilacion** | Runtime | Startup |
| **Debugging** | Flow stack abstracto | Subgraph visible |
| **Extensibilidad** | Modificar nodos | Nueva NodeFactory |
| **Performance** | Routing dinamico | Routing compilado |
| **Claridad** | Logica dispersa | Logica encapsulada |

---

## Plan de Implementacion

### Fase 1: Infraestructura (2-3 dias)

- [ ] Crear `FlowState` TypedDict
- [ ] Crear `NodeFactory` protocol
- [ ] Implementar `FlowCompiler` basico
- [ ] Implementar factories: `collect`, `action`, `say`

### Fase 2: Subgraph Compilation (3-4 dias)

- [ ] Implementar `EdgeBuilder`
- [ ] Implementar factories: `branch`, `confirm`
- [ ] Compilar flow simple (book_flight)
- [ ] Tests unitarios de subgraph

### Fase 3: Orchestrator (3-4 dias)

- [ ] Crear `OrchestratorGraph`
- [ ] Integrar NLU y CommandExecutor
- [ ] Manejar transiciones entre flows
- [ ] Tests de integracion

### Fase 4: Factories Completas (2-3 dias)

- [ ] Implementar `call_flow` (subflows)
- [ ] Implementar `generate` (LLM responses)
- [ ] Implementar `set`, `handoff`
- [ ] Tests e2e

### Fase 5: Migracion (2-3 dias)

- [ ] Migrar ejemplos existentes
- [ ] Actualizar documentacion
- [ ] Deprecar nodos legacy
- [ ] Release v3.0

---

## Referencias

- [ideas.md](ideas.md) - Ideas originales
- [LangGraph Subgraphs](https://langchain-ai.github.io/langgraph/how-tos/subgraph/) - Documentacion oficial
- [docs/design/](docs/design/) - Documentacion de diseno actual
