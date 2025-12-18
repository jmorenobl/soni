## Task: 004 - Update CLAUDE.md to Reflect Actual Architecture

**ID de tarea:** 004
**Hito:** 1 - Critical Fixes
**Dependencias:** Ninguna
**Duración estimada:** 2 horas
**Prioridad:** ALTA

### Objetivo

Actualizar CLAUDE.md para que refleje la arquitectura real del código fuente. Actualmente hay discrepancias entre la documentación y la implementación, lo cual causa confusión.

### Contexto

Durante el análisis del código se identificaron las siguientes discrepancias:

1. **DigressionHandler:** CLAUDE.md menciona "DigressionHandler (Coordinator)" pero esta clase no existe. Las digresiones se manejan via `ChitChat` command en `command_registry.py`.

2. **Estructura de directorios:** El árbol de directorios en CLAUDE.md no incluye todos los módulos actuales.

3. **Patrones obsoletos:** Algunos patrones descritos no coinciden con la implementación actual.

4. **Referencias a archivos .mdc:** Los archivos en `.cursor/rules/` pueden no estar actualizados.

### Entregables

- [ ] Eliminar referencia a DigressionHandler inexistente
- [ ] Documentar cómo se manejan realmente las digresiones (ChitChat pattern)
- [ ] Actualizar árbol de estructura de proyecto
- [ ] Verificar y actualizar referencias a archivos de reglas
- [ ] Agregar sección sobre patrones actuales (FlowDelta, two-pass NLU)

### Implementación Detallada

#### Paso 1: Auditar discrepancias actuales

**Verificar existencia de componentes mencionados:**

```bash
# DigressionHandler - no existe
grep -r "class DigressionHandler" src/soni/
# Resultado: ninguno

# Cómo se manejan digresiones realmente
grep -r "ChitChat" src/soni/
# Resultado: dm/nodes/command_registry.py
```

#### Paso 2: Actualizar sección de componentes clave

**Archivo a modificar:** `CLAUDE.md`

**Cambiar de:**

```markdown
### DigressionHandler (Coordinator)
Coordinates question/help handling. **Does NOT modify flow stack**.
```

**A:**

```markdown
### ChitChat Pattern (Digression Handling)
Digresiones (preguntas fuera de flujo, chitchat) se manejan via el comando `ChitChat`
en `dm/nodes/command_registry.py`. El patrón:

1. NLU detecta intent fuera de flujo → emite `ChitChat` command
2. `ChitChatHandler` genera respuesta sin modificar flow stack
3. Conversación continúa en el flujo activo

**Importante:** Las digresiones NO modifican el flow stack - el usuario puede
hacer preguntas mientras está en medio de un flujo y luego continuar.
```

#### Paso 3: Actualizar estructura de proyecto

**Cambiar de:**

```markdown
## Project Structure

```
src/soni/
├── core/          # Interfaces, state, errors, types, config
├── du/            # Dialogue Understanding (DSPy modules)
├── dm/            # Dialogue Management (LangGraph)
│   └── nodes/     # LangGraph node implementations (package)
├── compiler/      # YAML to Graph compilation
├── actions/       # Action Registry
├── validation/    # Validator Registry
├── server/        # FastAPI
├── cli/           # CLI commands
├── config/        # Configuration package
├── flow/          # FlowManager
├── observability/ # Logging
├── runtime/       # RuntimeLoop and managers
└── utils/         # Utilities
```
```

**A (estructura actualizada basada en código real):**

```markdown
## Project Structure

```
src/soni/
├── core/              # Core abstractions
│   ├── types.py       # Protocols (DUProtocol, FlowManagerProtocol, etc.)
│   ├── state.py       # DialogueState TypedDict and helpers
│   ├── errors.py      # Exception hierarchy (SoniError, ConfigError, etc.)
│   ├── constants.py   # Enums (FlowState, ConversationState, etc.)
│   ├── commands.py    # Command Pydantic models (StartFlow, SetSlot, etc.)
│   ├── expression.py  # Condition expression evaluator
│   └── validation.py  # Slot value validation
├── du/                # Dialogue Understanding (DSPy-based NLU)
│   ├── base.py        # OptimizableDSPyModule base class
│   ├── modules.py     # SoniDU main NLU module
│   ├── slot_extractor.py  # Pass-2 slot extraction
│   ├── signatures.py  # DSPy signatures
│   ├── models.py      # DialogueContext, NLUOutput, etc.
│   ├── optimizer.py   # GEPA/MIPROv2 optimization
│   └── metrics.py     # Optimization metrics
├── dm/                # Dialogue Management (LangGraph)
│   ├── builder.py     # Main graph builder
│   ├── nodes/         # LangGraph node implementations
│   │   ├── understand.py   # NLU processing node
│   │   ├── execute.py      # Flow routing node
│   │   ├── resume.py       # Flow lifecycle node
│   │   ├── respond.py      # Response generation node
│   │   └── command_registry.py  # Command dispatch
│   └── patterns/      # Pattern handlers (correction, cancellation, etc.)
├── compiler/          # YAML → LangGraph compilation
│   ├── factory.py     # Node factory registry
│   ├── subgraph.py    # Flow subgraph builder
│   └── nodes/         # Step-type specific factories
├── config/            # Configuration loading
│   ├── loader.py      # YAML loading with directory support
│   ├── main.py        # SoniConfig root model
│   ├── models.py      # FlowConfig, SlotConfig, etc.
│   └── steps.py       # Step configuration models
├── actions/           # Action system
│   ├── registry.py    # ActionRegistry with global/local actions
│   └── handler.py     # ActionHandler execution
├── flow/              # Flow state management
│   └── manager.py     # FlowManager with FlowDelta pattern
├── runtime/           # Runtime orchestration
│   ├── loop.py        # RuntimeLoop main orchestrator
│   ├── initializer.py # Component creation
│   ├── hydrator.py    # State preparation
│   ├── extractor.py   # Response extraction
│   └── checkpointer.py # Persistence factory
├── server/            # FastAPI server
│   ├── api.py         # Endpoints and lifecycle
│   ├── models.py      # Request/Response Pydantic models
│   ├── errors.py      # Error handling and sanitization
│   └── dependencies.py # DI helpers
├── cli/               # Typer CLI
│   ├── main.py        # CLI entrypoint
│   └── commands/      # Subcommands (chat, server, optimize)
└── dataset/           # Training data generation
```
```

#### Paso 4: Agregar sección de patrones actuales

**Agregar nueva sección:**

```markdown
## Key Implementation Patterns

### FlowDelta Pattern (Immutable State Updates)
All state mutations in FlowManager return `FlowDelta` objects instead of mutating state:

```python
@dataclass
class FlowDelta:
    flow_stack: list[FlowContext] | None = None
    flow_slots: dict[str, dict[str, Any]] | None = None

# Usage
delta = flow_manager.push_flow(state, "book_flight")
merge_delta(updates, delta)  # Merge into node return dict
return updates  # LangGraph applies changes
```

### Two-Pass NLU Architecture
1. **Pass 1 (SoniDU):** Intent detection without slot definitions (avoids context overload)
2. **Pass 2 (SlotExtractor):** Slot value extraction, only if StartFlow detected

```python
# In understand_node:
nlu_result = await du.acall(user_message, context)  # Pass 1

if any(isinstance(cmd, StartFlow) for cmd in nlu_result.commands):
    slot_commands = await slot_extractor.acall(user_message, slot_defs)  # Pass 2
    commands.extend(slot_commands)
```

### Command Registry Pattern
Commands from NLU are dispatched to handlers via registry:

```python
COMMAND_HANDLERS: dict[type, CommandHandler] = {
    StartFlow: StartFlowHandler(),
    SetSlot: SetSlotHandler(),
    ChitChat: ChitChatHandler(),  # Digression handling
    ...
}
```

### Protocol-Based Dependency Injection
All dependencies are injected via RuntimeContext using protocols:

```python
@dataclass
class RuntimeContext:
    config: ConfigProtocol
    flow_manager: FlowManagerProtocol
    action_handler: ActionHandlerProtocol
    du: DUProtocol
```
```

#### Paso 5: Actualizar Quick Reference Commands

**Actualizar sección de comandos:**

```markdown
## Quick Reference Commands

```bash
# Setup
uv sync
uv run pre-commit install

# Development
uv run pytest                           # Run all tests
uv run pytest tests/unit/ -v            # Unit tests only
uv run pytest tests/integration/ -v     # Integration tests
uv run ruff check . && ruff format .    # Lint & format
uv run mypy src/soni                    # Type check

# Server
uv run soni server --config examples/banking/soni.yaml

# Interactive Chat
uv run soni chat --config examples/banking/soni.yaml \
    --module examples.banking.handlers

# Optimization
uv run soni optimize run --config examples/banking/soni.yaml

# Validation
uv run python scripts/validate_flows.py examples/banking/
```
```

### Exception: Test-After

**Reason for test-after:**
- [x] Other: Documentation update, no code changes

**Justification:**
This task only updates documentation (CLAUDE.md). No functional code changes are made, so TDD is not applicable.

### Criterios de Éxito

- [ ] CLAUDE.md no menciona componentes que no existen
- [ ] Estructura de proyecto refleja directorios reales
- [ ] Patrones documentados coinciden con implementación
- [ ] Referencias a archivos de reglas son válidas
- [ ] Ejemplos de código son ejecutables

### Validación Manual

**Comandos para validar:**

```bash
# Verificar que componentes mencionados existen
grep -o "src/soni/[a-z_/]*" CLAUDE.md | sort -u | while read path; do
    if [ ! -e "$path" ] && [ ! -e "${path}.py" ]; then
        echo "Missing: $path"
    fi
done

# Verificar que archivos .mdc referenciados existen
grep -o "\.cursor/rules/[0-9a-z_-]*\.mdc" CLAUDE.md | while read file; do
    if [ ! -f "$file" ]; then
        echo "Missing: $file"
    fi
done
```

**Resultado esperado:**
- No hay paths faltantes
- Todos los archivos referenciados existen

### Referencias

- `CLAUDE.md` - Archivo a actualizar
- `.cursor/rules/*.mdc` - Archivos de reglas referenciados
- `src/soni/` - Código fuente para verificación

### Notas Adicionales

**Proceso sugerido:**
1. Hacer backup de CLAUDE.md actual
2. Aplicar cambios incrementalmente
3. Verificar cada sección contra el código
4. Pedir review antes de merge

**Mantenimiento futuro:**
- Considerar agregar CI check que valide paths en CLAUDE.md
- Actualizar CLAUDE.md como parte de PRs que cambien arquitectura
