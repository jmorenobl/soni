# Registro de Decisión de Arquitectura

## ADR-001: Arquitectura Híbrida Optimizada para Framework ToD Moderno

**Proyecto:** Soni - Framework Open Source para Asistentes Conversacionales
**Fecha:** 28 de Noviembre de 2025
**Estado:** Aprobado (Revisión v1.3 - Final)
**Autor:** Jorge - AI Solutions Architect
**Versión:** 1.3

---

## Resumen Ejecutivo

Este ADR define la arquitectura de **Soni**, un framework open source para sistemas de diálogo orientado a tareas (ToD) que combina la flexibilidad semántica de los LLMs con el control determinista requerido por aplicaciones empresariales.

**La propuesta de valor central es la optimización automática**: el módulo de Dialogue Understanding (`SoniDU`) hereda de `dspy.Module` y puede ser optimizado automáticamente con MIPROv2, SIMBA, o GEPA, eliminando la necesidad de prompt engineering manual.

**Arquitectura asíncrona**: El framework es exclusivamente asíncrono. Esto garantiza máximo throughput, streaming nativo de tokens, y compatibilidad directa con FastAPI.

La v1.1 incorpora mejoras críticas sobre la arquitectura base: **Scoping Dinámico** (para evitar saturación de contexto), **Estrategia de Normalización** (puente entre LLM y validación estricta), **Interfaces SOLID** (desacoplamiento total), y **Streaming** para reducción de latencia percibida.

**La v1.2 introduce un cambio radical en el DSL**: Se reemplaza la definición técnica de grafos (nodos/aristas) por una definición **procedural basada en pasos (`steps`)**. Esto permite que analistas no técnicos definan flujos complejos leyendo el archivo YAML como si fuera una "receta" o un diagrama de flujo lineal, mientras que el **Graph Builder** se encarga de compilar esto automáticamente a una máquina de estados `LangGraph` robusta y asíncrona.

**La v1.3 define una arquitectura "Zero-Leakage"**: El YAML es **puramente semántico** y describe *qué* debe pasar, no *cómo*. Se introducen tres abstracciones clave: **Action Registry** (desacoplamiento entre definición YAML y ejecución Python/HTTP), **Semantic Validators** (validadores nominales en lugar de regex), y **Output Mapping** (desacoplamiento de estructuras de datos). El resultado es un sistema donde un analista de negocio puede leer y editar el flujo sin riesgo de romper la integración técnica.

---

## 1. Contexto y Problema

### 1.1 Estado del Ecosistema Open Source

El panorama actual de frameworks ToD de código abierto presenta una brecha crítica que Soni pretende cubrir:

| Framework | Estado (Nov 2025) | Limitaciones |
|-----------|-------------------|--------------|
| **Rasa** | Activo, pero bifurcado | Innovación LLM restringida a versión comercial (Pro). Versión OS mantiene arquitectura legacy. |
| **Botpress** | Cloud-First | Ecosistema fragmentado; prioridad en SaaS propietario sobre versión self-hosted comunitaria. |
| **Chatterbot** | Legacy con parches | Arquitectura base obsoleta. Soporte LLM experimental y no nativo. |
| **Parlant** | Inmaduro | Problemas críticos de latencia reportados en producción (9x overhead). |

### 1.2 Problemas de los Enfoques Actuales

#### Riesgo de LLM Puro (End-to-End)
- Volatilidad en el Dialogue State Tracking (DST)
- Falta de trazabilidad en decisiones de política
- Comportamiento no determinista en lógica de negocio crítica
- Dificultad para auditar y depurar flujos de conversación
- Imposibilidad de garantizar cumplimiento de políticas de empresa

#### Fragilidad de Prompt Engineering Manual
- Prompts frágiles que se rompen con cambios menores
- Dificultad para mantener y versionar la lógica de NLU
- No escala ante cambios en requisitos del dominio
- Dependencia de "magia negra" en el diseño de prompts
- Falta de optimización sistemática

### 1.3 El Reto de la Escalabilidad en ToD Híbridos

La aproximación híbrida (Neuro-Simbólica) resuelve la dicotomía entre flexibilidad y control, pero introduce nuevos retos técnicos al escalar:

1. **Contaminación de Contexto:** Inyectar cientos de acciones posibles en el prompt del LLM degrada la precisión y aumenta costes/latencia.
2. **Conflicto de Validación:** La extracción "blanda" de los LLMs (ej: "Madrid, creo") choca con la validación "dura" (Regex) requerida por el negocio.
3. **Latencia Acumulada:** La arquitectura de "doble salto" (NLU LLM + Respuesta LLM) puede generar tiempos de respuesta inaceptables sin optimización.
4. **Acoplamiento:** Depender directamente de implementaciones concretas (DSPy/LangGraph) viola el principio de Inversión de Dependencias (D in SOLID).

### 1.4 El Problema de la "Abstracción con Fugas" (v1.2)

En versiones anteriores, obligar a los usuarios a definir `nodes`, `edges` y `conditional_transitions` en el YAML exponía demasiada complejidad técnica. Un analista de negocio piensa en "pasos secuenciales" y "decisiones", no en teoría de grafos. Esto creaba una barrera de entrada innecesaria y dificultaba el mantenimiento de flujos complejos.

### 1.5 El Problema de las Fugas de Abstracción (v1.3)

En la v1.2, aunque mejoramos el flujo procedural, persistían detalles técnicos que acoplaban la lógica de negocio a la infraestructura:

- **Acoplamiento HTTP:** Definir `method: POST`, `url`, y `jsonpath` en el YAML hace que un cambio en la API rompa la definición de negocio.
- **Validación Opaca:** Expresiones como `^[A-Z]{6}$` son ilegibles y propensas a errores para no-programadores.
- **Acoplamiento de Datos:** Navegar objetos (`res.data.status`) en el flujo crea dependencias ocultas sobre la estructura interna de las respuestas.

Esto viola el principio de **Separación de Responsabilidades** y dificulta el mantenimiento cuando cambian las APIs externas o las estructuras de datos.

### 1.6 Objetivos

Construir un framework ToD que combine la flexibilidad semántica del LLM con el control determinista requerido por el negocio, utilizando herramientas modernas de código abierto, permitiendo la definición declarativa mediante archivos YAML, implementando **Scoping Dinámico** para la gestión de contexto, una capa intermedia de **Normalización**, arquitectura basada en **Interfaces Abstractas** para garantizar testabilidad y evolución, y garantizando trazabilidad completa y respuestas seguras.

**Objetivos específicos de la v1.2:**

1. **Simplificación Cognitiva:** El YAML debe leerse de arriba a abajo. El paso B sigue al paso A implícitamente.
2. **Potencia Oculta:** Mantener la capacidad de saltos (`jump_to`) y bucles complejos sin complicar la sintaxis básica.
3. **Traducción Automática:** El compilador debe transformar esta lista lineal en el grafo dirigido cíclico necesario para el runtime.

**Objetivos específicos de la v1.3 (Zero-Leakage):**

1. **Arquitectura Hexagonal Real:** El YAML (Núcleo) solo habla el lenguaje del dominio (Vuelos, Reservas, Fechas). Los Adaptadores (Código) manejan la suciedad técnica (HTTP, Regex, SQL).
2. **Separación de Responsabilidades:** Analistas/PMs editan YAML (Qué). Ingenieros editan Python (Cómo).
3. **Robustez ante Cambios:** Cambios en APIs externas solo requieren actualizar código Python, no el YAML de negocio.

---

## 2. Decisión de Arquitectura

Se adopta una **Arquitectura Híbrida Desacoplada** que sigue el principio de **Separación de Responsabilidades** entre Interpretación Semántica y Ejecución Determinista, reforzada con patrones de **Dynamic Context Injection** y **Data Normalization Middleware**. Todo el framework es asíncrono.

### 2.1 Componentes Centrales

| Capa | Componente | Herramienta | Función | Optimización v1.1/v1.2/v1.3 |
|------|------------|-------------|---------|---------------------------|
| **Configuración** | **Semantic YAML** | YAML | **v1.3:** YAML puramente semántico, sin detalles técnicos | - |
| **Abstracción** | Core Interfaces | Python Protocols | Contratos async del sistema | Desacoplamiento total (SOLID) |
| **Registro** | **Action Registry** | Python Decorators | **v1.3:** Desacoplamiento entre definición YAML y ejecución | - |
| **Registro** | **Validator Registry** | Python Decorators | **v1.3:** Validadores semánticos en lugar de regex | - |
| **Interpretación** | SoniDU | DSPy (`acall()`) | Traducir entrada a Comando Estructurado optimizado | **Scoping Dinámico** |
| **Mediación** | Normalizer | Heurístico + LLM | Limpieza de datos | **Sanitización async** previa a validación |
| **Control** | **Step Compiler** | Python | **v1.2:** Traduce `steps` lineales a `StateGraph` de LangGraph | **v1.3:** Manejo de `map_outputs` |
| **Ejecución** | LangGraph Runtime | LangGraph (`astream()`) | Ejecución determinista asíncrona | **Streaming async** de tokens |
| **Persistencia** | State Manager | aiosqlite/asyncpg/aioredis | Historial y Contexto | **I/O async** + Resumen Inteligente |

### 2.2 Diagrama de Arquitectura (v1.3 - Zero-Leakage)

```
┌────────────────────┐      ┌───────────────────────────────────┐
│  Business Config   │      │       Technical Implementation    │
│    (soni.yaml)     │      │           (Python Code)           │
│                    │      │                                   │
│  [ Flows / Steps ] │      │  ┌──────────┐   ┌──────────────┐  │
│          │         │      │  │ Registry │◀──│ @action      │  │
│  [ Action Defs ]───┼──────┼─▶│ (Lookup) │   │ implementation│  │
│          │         │      │  └──────────┘   └──────────────┘  │
│  [ Entities ]──────┼──────┼─▶┌──────────┐   ┌──────────────┐  │
└────────────────────┘      │  │Validator │◀──│ @validator   │  │
           │                │  │ Factory  │   │     logic    │  │
           ▼                │  └──────────┘   └──────────────┘  │
┌────────────────────┐      └───────────────────────────────────┘
│   Step Compiler    │◀───────────────┘
│ (YAML -> Graph)    │
└──────────┬─────────┘
           ▼
┌─────────────────────────────────────────────────────────────┐
│                     Runtime Loop (Async)                    │
│                                                             │
│  ┌───────┐  ┌──────────┐  ┌────────────┐  ┌───────────────┐│
│  │ Input │─▶│  SoniDU  │─▶│ Normalizer │─▶│   LangGraph   ││
│  │ User  │  │  (DSPy)  │  │(Heuristic) │  │     (DM)      ││
│  └───────┘  └──────────┘  └────────────┘  └───────┬───────┘│
│                  ▲                                │        │
│                  └──────────(Streaming)───────────┘        │
│                                   │                        │
│                                   ▼                        │
│  ┌─────────────────────────────────────────────────────┐   │
│  │                    Dialogue State                    │   │
│  │  (slots, history, current_node, trace, summary)     │   │
│  └─────────────────────────────────────────────────────┘   │
│                                   │                        │
│                                   ▼                        │
│  ┌─────────────┐  ┌─────────────┐  ┌───────────────────┐  │
│  │   Tools     │  │   Handoff   │  │   Output Stream   │  │
│  │  (External  │  │   (Human)   │  │   (Respuesta)     │  │
│  │    APIs)    │  │             │  │                   │  │
│  └─────────────┘  └─────────────┘  └───────────────────┘  │
│                                                             │
│  ┌─────────────────────────────────────────────────────┐   │
│  │              Checkpoint (Persistence)                │   │
│  │         SQLite / PostgreSQL / Redis                  │   │
│  └─────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────┘
```

**Separación de Responsabilidades (v1.3):**
- **YAML (Núcleo):** Solo habla el lenguaje del dominio (Vuelos, Reservas, Fechas).
- **Python (Adaptadores):** Maneja la suciedad técnica (HTTP, Regex, SQL).

### 2.3 Flujo de Control Detallado

1. **Carga del Grafo**: Al iniciar, el Graph Builder consume los archivos YAML y construye el StateGraph de LangGraph dinámicamente.
2. **Entrada del Usuario**: El usuario introduce un mensaje de lenguaje natural.
3. **Carga de Estado (`await`)**: El StateStore carga el estado del usuario de forma async (aiosqlite, asyncpg, aioredis).
4. **Scoping Dinámico**: El ScopeManager filtra las acciones disponibles según el estado actual (flujo activo, slots completados).
5. **Interpretación por DSPy (`await acall()`)**:
   - El módulo DU utiliza `acall()` para invocación async al LLM optimizado
   - Recibe solo las acciones válidas filtradas (reducción de ruido)
   - Genera slots extraídos, nivel de confianza y reasoning
6. **Normalización (`await`)**:
   - Los slots extraídos pasan por el Normalizer
   - Limpieza heurística o LLM async antes de validación estricta
7. **Validación de Seguridad**:
   - Verificación de acciones permitidas (guardrails)
   - Validación de slots contra constraints del YAML
   - Detección de intents fuera de alcance
8. **Ejecución por LangGraph (`async for ... astream()`)**:
   - El grafo recibe el comando y ejecuta transiciones deterministas mediante aristas condicionales
   - Los nodos de política (todos `async def`) deciden el siguiente paso basándose en lógica Python pura
   - `astream()` emite eventos en tiempo real
9. **Actualización de Estado (`await`)**:
   - El DST se actualiza con checkpointer persistente async
   - Se registra la traza completa para auditoría
   - Si el historial supera el límite, se genera resumen inteligente
10. **Generación de Respuesta con Streaming**:
    - Los tokens se envían al frontend inmediatamente via `AsyncGenerator`
    - Compatible con SSE (Server-Sent Events) y WebSockets

---

## 3. Especificación del Schema YAML

El schema YAML sigue un enfoque **híbrido**: declarativo por defecto con override explícito. Esto permite que el 80% de los flujos ToD estándar se definan de forma simple, mientras casos complejos tienen control total sobre el grafo.

### 3.1 Nivel 1: Configuración Global

```yaml
version: "1.0"

settings:
  # Estrategia de modelos diferenciada para reducir latencia (v1.1)
  models:
    nlu:
      provider: openai
      model: gpt-4o-mini       # Modelo rápido para clasificación
      temperature: 0.1
    generation:
      provider: openai
      model: gpt-4o            # Modelo potente para respuestas complejas
      temperature: 0.7
      max_tokens: 500

  dspy:
    optimizer: MIPROv2         # MIPROv2, BootstrapFewShot, COPRO, SIMBA, GEPA
    metric: intent_accuracy
    num_candidates: 10
    auto_config: medium        # light, medium, heavy (v1.1 - auto-hyperparams)

  persistence:
    backend: sqlite            # sqlite, postgresql, redis
    path: ./dialogue_state.db

  security:
    enable_guardrails: true
    allowed_actions: []        # Lista vacía = todas permitidas
    blocked_intents: []
    max_confidence_threshold: 0.95

  logging:
    level: INFO
    trace_graphs: true
    audit_log: true            # Registro de auditoría completo

  # Configuración de resumen de historial (v1.1)
  history:
    max_messages: 10
    summarize_after: 10
    summary_model: gpt-4o-mini

entities:
  - name: city
    type: string
    examples: [Madrid, Barcelona, NYC, London, París]
    # Pipeline: Extracción -> Normalización -> Validación (v1.1/v1.3)
    normalization:
      strategy: "llm_correction"  # lowercase, trim, llm_correction, custom_func
    # v1.3: Validación semántica (implementada en código Python)
    validator: city_format

  - name: date
    type: datetime
    format: "%Y-%m-%d"
    normalization:
      strategy: "trim"
    # v1.3: Validador semántico
    validator: future_date_only

  - name: cabin_class
    type: enum
    values: [economy, business, first]

  - name: booking_ref
    type: custom
    # v1.3: Abstracción - Referencia a un validador registrado en código
    # Ya no hay regex aquí. Solo nombres de validadores que el equipo técnico implementa.
    validator: booking_ref_format
    examples: ["AJX892", "KLM110"]
```

### 3.2 Nivel 2: Flujos Declarativos

Para flujos simples de slot-filling, el framework infiere automáticamente el grafo de estados:

```yaml
flows:
  book_flight:
    description: "Reserva de vuelos"

    # Ejemplos para entrenar DSPy (no keywords exactos)
    triggers:
      - "quiero reservar un vuelo"
      - "necesito volar a {destination}"
      - "busca vuelos de {origin} a {destination}"
      - "hay aviones a {destination} el {date}?"

    slots:
      origin:
        entity: city
        required: true
        prompt: "¿Desde qué ciudad quieres salir?"
      destination:
        entity: city
        required: true
        prompt: "¿A qué ciudad quieres volar?"
      date:
        entity: date
        required: true
        prompt: "¿Qué día quieres viajar?"
      cabin:
        entity: cabin_class
        required: false
        default: economy

    # Validaciones entre slots
    constraints:
      - condition: "origin != destination"
        error: "El origen y destino no pueden ser iguales"

    # Acción al completar todos los slots
    on_complete:
      action: search_flights
      confirm: true
      confirmation_template: |
        Voy a buscar vuelos de {origin} a {destination}
        para el {date} en clase {cabin}. ¿Confirmas?

    # Respuestas según resultado de la acción
    responses:
      success: "Encontré {count} vuelos. El más barato: {cheapest}"
      no_results: "No hay vuelos disponibles para esa fecha."
      error: "Ha ocurrido un error al buscar vuelos."
```

**Grafo Inferido Automáticamente:**

```
[understand] → [route_to_flow] → [slot_loop] ←──┐
                                      │         │
                                      ▼         │
                              [check_slots]─────┘ (slots faltantes)
                                      │
                                      │ (completo)
                                      ▼
                              [validate_constraints]
                                      │
                                      ▼
                              [confirm] → [execute_action] → [respond]
```

### 3.3 Nivel 3: Procesos Procedurales (Business Logic) (v1.2)

Este es el nuevo estándar para flujos con lógica. Se lee como un guion, de forma lineal y secuencial. El compilador transforma automáticamente esta lista de pasos en el grafo de estados necesario.

```yaml
flows:
  modify_booking:
    description: "Modificar reserva existente"
    triggers:
      - "cambiar mi vuelo"
      - "modificar reserva"

    # NUEVO: Definición por Pasos (Procedural) - v1.2
    process:
      # Paso 1: Recolectar información (Abstracción de Slot Filling)
      - step: request_id
        type: collect
        slot: booking_ref  # Usa la entidad definida globalmente

      # Paso 2: Ejecutar acción de negocio (v1.3: Caja negra)
      - step: verify_status
        type: action
        call: check_booking_rules
        # v1.3: Mapeo Explícito - Desempaquetar resultado técnico a variables de flujo
        map_outputs:
          status: api_status       # output_accion -> variable_flujo
          rejection_reason: reason # output_accion -> variable_flujo

      # Paso 3: Decisión (Sobre variables planas, no objetos anidados)
      - step: decide_path
        type: branch
        input: api_status          # v1.3: Usamos la variable mapeada, no un objeto
        cases:
          modifiable: continue       # Sigue al siguiente paso
          not_modifiable: jump_to_explain
          not_found: jump_to_error

      # Paso 4: Interacción con usuario (Menú)
      - step: select_modification
        type: choice
        prompt: "¿Qué quieres modificar?"
        options:
          - label: "Fecha del vuelo"
            jump_to: change_date_flow
          - label: "Cancelar reserva"
            jump_to: cancel_flow

      # Sub-flujo: Cambio de fecha
      - step: change_date_flow      # Etiqueta de destino (Label)
        type: collect
        slot: new_date

      - step: apply_changes
        type: action
        call: modify_booking_api

      - step: confirm_success
        type: say
        message: "Cambio realizado correctamente. Nueva fecha: {new_date}"
        # Fin implícito del flujo

      # Bloques de manejo de errores (Targets de saltos)
      - step: jump_to_explain
        type: say
        message: "Lo siento, esta reserva no permite cambios: {reason}"  # v1.3: Variable plana

      - step: jump_to_error
        type: say
        message: "No he podido encontrar esa reserva en el sistema."
```

**Ventajas de este formato (v1.2/v1.3):**

1. **Next implícito:** No hay que escribir `next: verify_status` en el paso 1. Se asume secuencialidad.
2. **Vocabulario de Negocio:** `collect`, `action`, `branch`, `say`, `choice` en lugar de `node`, `edge`, `conditional_transition`.
3. **Saltos claros:** `jump_to` explícito para romper la linealidad cuando es necesario.
4. **Legibilidad:** Un analista de negocio puede leer el flujo de arriba a abajo como una receta.
5. **v1.3 - Desacoplamiento de Datos:** `map_outputs` evita la notación de punto (`.`) y desacopla estructuras. El flujo trabaja con variables planas, no objetos anidados.

**Tipos de pasos soportados:**

- `collect`: Recolecta un slot (equivalente a slot-filling)
- `action`: Ejecuta una acción externa (HTTP, Python, LangChain Tool)
- `branch`: Decisión condicional basada en estado
- `choice`: Menú de opciones para el usuario
- `say`: Genera una respuesta al usuario
- `confirm`: Solicita confirmación del usuario

### 3.4 Definición de Acciones (v1.3 - Contratos Semánticos)

**v1.3: Solo definimos las "Firmas" (Interfaces). La implementación HTTP/Python desaparece de aquí.**

```yaml
actions:
  # v1.3: Contrato semántico - Sin detalles técnicos
  - name: check_booking_rules
    description: "Verifica si una reserva permite modificaciones"
    inputs: [booking_ref]
    # Contrato de salida: Garantizamos que la acción devuelve esto
    outputs: [status, rejection_reason]

  - name: modify_booking_api
    description: "Modifica una reserva existente"
    inputs: [booking_ref, new_date]
    outputs: [confirmation_id]

  - name: search_flights
    description: "Busca vuelos disponibles"
    inputs: [origin, destination, date]
    outputs: [count, cheapest, results]
```

**Comparación v1.2 vs v1.3:**

| Aspecto | v1.2 (Técnico) | v1.3 (Semántico) |
|--------|----------------|------------------|
| **URL/Endpoint** | Definido en YAML | Implementado en Python |
| **Headers/Auth** | En YAML | En código Python |
| **JSONPath** | `$.results.length` | Mapeo en `map_outputs` |
| **Módulo Python** | `module: soni_actions.bookings` | Decorador `@ActionRegistry.register` |
| **Cambios en API** | Requiere editar YAML | Solo editar Python |

### 3.5 Comportamiento Global

```yaml
fallback:
  no_intent:
    response: "No he entendido. ¿Puedes reformularlo?"
    max_retries: 2
    then: handoff_human

  out_of_scope:
    response: "Solo puedo ayudarte con reservas de vuelos."

  action_error:
    response: "Ha ocurrido un error. ¿Quieres intentarlo de nuevo?"
    log_level: ERROR

interruptions:
  allow_during_flow: true
  intents:
    - name: cancel
      triggers: ["cancelar", "déjalo", "no quiero"]
      action: abort_current_flow
    - name: help
      triggers: ["ayuda", "no entiendo", "qué puedo hacer"]
      action: show_current_options
    - name: restart
      triggers: ["empezar de nuevo", "reiniciar"]
      action: reset_flow_state

handoff:
  enabled: true
  triggers:
    - "hablar con un humano"
    - "agente real"
  webhook: "https://api.company.com/handoff"
  message: "Te paso con un agente. Un momento..."
  include_context: true  # Pasa slots y historial al agente humano
```

---

## 4. Implementación Técnica

### 4.1 Abstracción: Interfaces SOLID (v1.1)

**IMPORTANTE**: No hay versiones síncronas de las interfaces.

```python
# soni/core/interfaces.py
from typing import Protocol, List, Dict, Any, AsyncGenerator
from dataclasses import dataclass

@dataclass
class NLUResult:
    command: str
    slots: Dict[str, Any]
    confidence: float
    reasoning: str

@dataclass
class DialogueState:
    messages: List[Dict]
    current_flow: str
    slots: Dict[str, Any]
    pending_action: str | None
    last_response: str
    turn_count: int
    trace: List[Dict]
    summary: str | None = None

class INLUProvider(Protocol):
    """Interfaz async para proveedores de Entendimiento de Lenguaje."""
    async def predict(
        self,
        message: str,
        context: Dict[str, Any],
        scoped_actions: List[str]
    ) -> NLUResult:
        """Método async obligatorio."""
        ...

class IDialogueManager(Protocol):
    """Interfaz async para el gestor de estado y flujo."""
    async def process_turn(
        self,
        input_data: NLUResult,
        state: DialogueState
    ) -> AsyncGenerator[str, None]:
        """Método async obligatorio que produce tokens en streaming."""
        ...

class INormalizer(Protocol):
    """Interfaz para limpieza de slots (puede ser sync, operación rápida)."""
    def normalize(self, value: Any, entity_config: Dict) -> Any:
        ...

class IScopeManager(Protocol):
    """Interfaz para gestión de contexto dinámico (sync, operación rápida)."""
    def get_available_actions(self, state: DialogueState) -> List[str]:
        ...
```

### 4.2 Scoping Dinámico: Solución a Contaminación de Contexto (v1.1)

En lugar de pasar todas las acciones, filtramos según el estado actual del diálogo.

```python
# soni/core/scope.py
from typing import List

class ScopeManager(IScopeManager):
    def __init__(self, config: dict):
        self.global_intents = ["help", "cancel", "restart"]
        self.flows = config['flows']

    def get_available_actions(self, state: DialogueState) -> List[str]:
        """
        Retorna solo las acciones lógica y contextualmente posibles.
        Reduce drásticamente el ruido para el LLM.
        """
        # 1. Siempre incluir comandos globales
        actions = self.global_intents.copy()

        current_flow = state.current_flow

        if current_flow and current_flow != 'none':
            # 2. Si estamos en un flujo, solo permitir acciones de ese flujo
            # (El usuario debe cancelar para salir, reduciendo alucinaciones)
            flow_config = self.flows.get(current_flow)
            if flow_config:
                actions.extend(flow_config.get('local_actions', []))
                # Añadir slots pendientes como acciones válidas
                for slot_name in flow_config.get('slots', {}).keys():
                    if slot_name not in state.slots:
                        actions.append(f"provide_{slot_name}")
        else:
            # 3. Si no hay flujo, permitir triggers de inicio de flujos
            for flow_name, flow_cfg in self.flows.items():
                actions.append(f"start_{flow_name}")

        return list(set(actions))  # Eliminar duplicados
```

### 4.3 Integración DSPy: Módulo Optimizable

El módulo `SoniDU` **debe heredar de `dspy.Module`** e implementar `aforward()` (async) para ser optimizable con MIPROv2, SIMBA, GEPA, etc.

**NOTA**: Usamos `aforward()` + `acall()` en runtime. El método `forward()` existe solo para los optimizadores DSPy.

```python
# soni/du/signatures.py
import dspy

class DialogueUnderstanding(dspy.Signature):
    """Interpreta la intención del usuario en contexto del diálogo."""

    user_message: str = dspy.InputField(
        desc="Último mensaje del usuario"
    )
    dialogue_history: str = dspy.InputField(
        desc="Historial resumido + últimos 5 mensajes"
    )
    current_slots: dict = dspy.InputField(
        desc="Slots actuales con sus valores"
    )
    available_actions: list[str] = dspy.InputField(
        desc="Acciones válidas FILTRADAS según contexto actual"
    )
    current_flow: str = dspy.InputField(
        desc="Flujo activo actual o 'none'"
    )

    structured_command: str = dspy.OutputField(
        desc="Comando: action_name(slot=value, ...) o NONE"
    )
    extracted_slots: dict = dspy.OutputField(
        desc="Slots extraídos del mensaje: {slot_name: value}"
    )
    confidence: float = dspy.OutputField(
        desc="Confianza de la predicción: 0.0 a 1.0"
    )
    reasoning: str = dspy.OutputField(
        desc="Explicación del razonamiento"
    )
```

```python
# soni/du/modules.py
import dspy
from typing import Dict, Any, List
from dataclasses import dataclass

@dataclass
class NLUResult:
    command: str
    slots: Dict[str, Any]
    confidence: float
    reasoning: str


class SoniDU(dspy.Module):
    """
    Módulo DSPy optimizable para Dialogue Understanding.

    CRÍTICO:
    - Hereda de dspy.Module
    - Implementa aforward() para runtime, forward() para optimizadores
    - Los optimizadores (MIPROv2, etc.) pueden optimizar este módulo
    """

    def __init__(self, scope_manager: 'ScopeManager' = None):
        super().__init__()  # IMPORTANTE: Llamar a super().__init__()

        # Predictor interno - ESTO es lo que se optimiza
        self.predictor = dspy.ChainOfThought(DialogueUnderstanding)
        self.scope_manager = scope_manager

    async def aforward(
        self,
        user_message: str,
        dialogue_history: str,
        current_slots: dict,
        current_flow: str,
        available_actions: List[str] = None
    ) -> dspy.Prediction:
        """
        Método aforward() ASYNC requerido por DSPy para ejecución asíncrona.

        Los optimizadores (MIPROv2, etc.) usan forward() durante training,
        pero en runtime usamos aforward() via acall() para async.

        DSPy automáticamente delega acall() -> aforward() si existe.
        """
        # Si tenemos scope_manager y no se pasaron acciones, calcularlas
        if available_actions is None and self.scope_manager:
            state = {
                'current_flow': current_flow,
                'slots': current_slots
            }
            available_actions = self.scope_manager.get_available_actions(state)

        # Llamar al predictor usando acall() para async
        result = await self.predictor.acall(
            user_message=user_message,
            dialogue_history=dialogue_history,
            current_slots=current_slots,
            available_actions=available_actions or [],
            current_flow=current_flow
        )

        return result

    def forward(
        self,
        user_message: str,
        dialogue_history: str,
        current_slots: dict,
        current_flow: str,
        available_actions: List[str] = None
    ) -> dspy.Prediction:
        """
        Método forward() SYNC requerido por optimizadores DSPy.

        NOTA: Los optimizadores como MIPROv2 usan forward() durante
        el proceso de bootstrapping. Este método es necesario para
        que la optimización funcione, pero NO se usa en runtime.
        """
        if available_actions is None and self.scope_manager:
            state = {
                'current_flow': current_flow,
                'slots': current_slots
            }
            available_actions = self.scope_manager.get_available_actions(state)

        result = self.predictor(
            user_message=user_message,
            dialogue_history=dialogue_history,
            current_slots=current_slots,
            available_actions=available_actions or [],
            current_flow=current_flow
        )

        return result

    async def predict(self, message: str, state: Dict[str, Any]) -> NLUResult:
        """
        Wrapper async de conveniencia para uso en runtime.
        Internamente llama a aforward() via acall().
        """
        # Preparar historial resumido
        history_context = (state.get('summary') or "") + \
                         str(state.get('messages', [])[-5:])

        # Llamar a acall() que usa aforward() internamente
        result = await self.acall(
            user_message=message,
            dialogue_history=history_context,
            current_slots=state.get('slots', {}),
            current_flow=state.get('current_flow', 'none')
        )

        return NLUResult(
            command=result.structured_command,
            slots=result.extracted_slots,
            confidence=result.confidence,
            reasoning=result.reasoning
        )
```

### 4.4 Optimización del Módulo SoniDU

```python
# soni/du/optimizers.py
import dspy
from dspy.teleprompt import MIPROv2, BootstrapFewShotWithRandomSearch
from dspy.evaluate import Evaluate

def create_training_examples(yaml_config: dict) -> list[dspy.Example]:
    """
    Crea ejemplos de entrenamiento desde los triggers del YAML.
    """
    examples = []
    for flow_name, flow_cfg in yaml_config.get('flows', {}).items():
        for trigger in flow_cfg.get('triggers', []):
            # Crear ejemplo con inputs y outputs esperados
            example = dspy.Example(
                user_message=trigger,
                dialogue_history="",
                current_slots={},
                current_flow="none",
                available_actions=[f"start_{flow_name}", "help", "cancel"],
                # Outputs esperados
                structured_command=f"start_{flow_name}()",
                extracted_slots={},
                confidence=0.95,
                reasoning=f"Usuario quiere iniciar flujo {flow_name}"
            ).with_inputs(
                "user_message",
                "dialogue_history",
                "current_slots",
                "current_flow",
                "available_actions"
            )
            examples.append(example)
    return examples


def intent_accuracy_metric(example, prediction, trace=None) -> float:
    """
    Métrica de evaluación para optimización.
    Evalúa si el comando predicho es correcto.
    """
    expected_cmd = example.structured_command.split("(")[0]
    predicted_cmd = prediction.structured_command.split("(")[0]

    # Coincidencia exacta del comando
    cmd_match = 1.0 if expected_cmd == predicted_cmd else 0.0

    # Bonus por slots extraídos correctamente
    slot_score = 0.0
    if hasattr(example, 'extracted_slots') and example.extracted_slots:
        expected_slots = set(example.extracted_slots.keys())
        predicted_slots = set(prediction.extracted_slots.keys())
        if expected_slots:
            slot_score = len(expected_slots & predicted_slots) / len(expected_slots)

    return 0.7 * cmd_match + 0.3 * slot_score


def optimize_soni_du(
    base_module: SoniDU,
    trainset: list[dspy.Example],
    valset: list[dspy.Example] = None,
    optimizer_type: str = "MIPROv2",
    auto_config: str = "medium"
) -> SoniDU:
    """
    Optimiza el módulo SoniDU usando el optimizador especificado.

    Args:
        base_module: Instancia de SoniDU sin optimizar
        trainset: Ejemplos de entrenamiento
        valset: Ejemplos de validación (opcional)
        optimizer_type: "MIPROv2", "BootstrapFewShot", "SIMBA", "GEPA"
        auto_config: "light", "medium", "heavy"

    Returns:
        SoniDU optimizado con prompts mejorados
    """
    if valset is None:
        # Split 80/20 si no hay valset
        split_idx = int(len(trainset) * 0.8)
        valset = trainset[split_idx:]
        trainset = trainset[:split_idx]

    if optimizer_type == "MIPROv2":
        optimizer = MIPROv2(
            metric=intent_accuracy_metric,
            auto=auto_config,  # light, medium, heavy
            verbose=True
        )

        optimized = optimizer.compile(
            base_module,
            trainset=trainset,
            max_bootstrapped_demos=3,
            max_labeled_demos=4,
            requires_permission_to_run=False
        )

    elif optimizer_type == "BootstrapFewShot":
        optimizer = BootstrapFewShotWithRandomSearch(
            metric=intent_accuracy_metric,
            max_bootstrapped_demos=4,
            num_candidate_programs=10
        )
        optimized = optimizer.compile(base_module, trainset=trainset)

    # Evaluar mejora
    evaluator = Evaluate(
        devset=valset,
        metric=intent_accuracy_metric,
        num_threads=4,
        display_progress=True
    )

    baseline_score = evaluator(base_module, devset=valset)
    optimized_score = evaluator(optimized, devset=valset)

    print(f"Baseline: {baseline_score:.2%} -> Optimizado: {optimized_score:.2%}")
    print(f"Mejora: {(optimized_score - baseline_score):.2%}")

    return optimized


# Script de optimización
if __name__ == "__main__":
    import yaml

    # Cargar configuración
    with open("soni.yaml") as f:
        config = yaml.safe_load(f)

    # Configurar LM
    dspy.configure(lm=dspy.LM('openai/gpt-4o-mini'))

    # Crear módulo base
    scope_manager = ScopeManager(config)
    base_du = SoniDU(scope_manager=scope_manager)

    # Crear ejemplos de entrenamiento
    trainset = create_training_examples(config)

    # Optimizar
    optimized_du = optimize_soni_du(
        base_du,
        trainset=trainset,
        optimizer_type="MIPROv2",
        auto_config="medium"
    )

    # Guardar módulo optimizado
    optimized_du.save("optimized_soni_du.json")
    print("Módulo optimizado guardado en optimized_soni_du.json")
```

### 4.5 Adapter para Interfaces SOLID

Para mantener el desacoplamiento SOLID, creamos un adapter async que implementa `INLUProvider` y envuelve el módulo DSPy:

```python
# soni/du/adapter.py
from typing import Dict, Any

class SoniDUAdapter(INLUProvider):
    """
    Adapter ASYNC que implementa INLUProvider envolviendo un módulo DSPy.

    Permite:
    1. Mantener el módulo DSPy puro y optimizable
    2. Cumplir con la interfaz INLUProvider async para el runtime
    3. Swap de implementaciones sin cambiar el resto del sistema
    """

    def __init__(self, dspy_module: SoniDU):
        self.module = dspy_module

    async def predict(
        self,
        message: str,
        context: Dict[str, Any],
        scoped_actions: list[str]
    ) -> NLUResult:
        """
        Implementa INLUProvider.predict() async.
        Delega al módulo DSPy usando acall().
        """
        # Preparar historial
        history = context.get('summary', '') + str(context.get('messages', [])[-5:])

        # Llamar a acall() que usa aforward() internamente
        result = await self.module.acall(
            user_message=message,
            dialogue_history=history,
            current_slots=context.get('slots', {}),
            current_flow=context.get('current_flow', 'none'),
            available_actions=scoped_actions
        )

        return NLUResult(
            command=result.structured_command,
            slots=result.extracted_slots,
            confidence=result.confidence,
            reasoning=result.reasoning
        )

    @classmethod
    def from_optimized(cls, path: str, scope_manager: 'ScopeManager') -> 'SoniDUAdapter':
        """Carga un módulo optimizado y lo envuelve en el adapter."""
        module = SoniDU(scope_manager=scope_manager)
        module.load(path)
        return cls(module)
```

### 4.6 Estrategia de Normalización (v1.1)

Puente entre la extracción "fuzzy" del LLM y la validación estricta del negocio.
Cuando usa LLM para corrección, es async.

```python
# soni/du/normalizer.py
import dspy
from typing import Any, Dict

class SlotNormalizer(INormalizer):
    """
    Normaliza slots extraídos antes de validación.

    NOTA: Las estrategias simples (trim, lowercase) son sync.
    La estrategia llm_correction es async internamente.
    """

    def __init__(self, config: dict):
        self.config = config
        # Modelo rápido para correcciones
        self.cleanup_lm = dspy.LM("openai/gpt-4o-mini", temperature=0)

    def normalize(self, raw_value: Any, entity_config: Dict) -> Any:
        """
        Normalización sync para estrategias simples.
        Para llm_correction, usar normalize().
        """
        strategy = entity_config.get('normalization', {}).get('strategy', 'none')

        if strategy == 'none':
            return raw_value

        if strategy == 'trim':
            return str(raw_value).strip()

        elif strategy == 'lowercase':
            return str(raw_value).lower().strip()

        elif strategy == 'llm_correction':
            # Marcador para procesamiento async posterior
            return {'__needs_async__': True, 'value': raw_value, 'config': entity_config}

        elif strategy == 'custom_func':
            func_name = entity_config.get('normalization', {}).get('function')
            if func_name:
                return self._call_custom_func(func_name, raw_value)

        return raw_value

    async def normalize(self, raw_value: Any, entity_config: Dict) -> Any:
        """
        Normalización async para estrategias que requieren LLM.
        """
        strategy = entity_config.get('normalization', {}).get('strategy', 'none')

        if strategy == 'llm_correction':
            return await self._llm_cleanup(raw_value, entity_config)

        # Para otras estrategias, delegar a sync
        return self.normalize(raw_value, entity_config)

    async def _llm_cleanup(self, raw_value: str, entity_config: Dict) -> str:
        """Limpieza async usando LLM pequeño."""
        entity_type = entity_config.get('type', 'string')
        examples = entity_config.get('examples', [])

        prompt = f"""Extract only the {entity_type} value from this text.
Input: "{raw_value}"
Examples of valid values: {examples[:5]}
Return ONLY the clean value, nothing else."""

        # Usar llamada async del LM
        response = await self.cleanup_lm.acall(prompt)
        return response.strip().strip('"\'')

    async def process(self, slots: Dict[str, Any]) -> Dict[str, Any]:
        """Normaliza todos los slots extraídos de forma async."""
        import asyncio

        entities = {e['name']: e for e in self.config.get('entities', [])}

        async def normalize_slot(slot_name: str, raw_value: Any) -> tuple:
            entity_config = entities.get(slot_name, {})
            normalized = await self.normalize(raw_value, entity_config)
            return slot_name, normalized

        # Procesar todos los slots en paralelo
        tasks = [normalize_slot(name, value) for name, value in slots.items()]
        results = await asyncio.gather(*tasks)

        return dict(results)

        return normalized
```

### 4.7 Graph Builder: Compilador de Pasos a LangGraph (v1.2)

**IMPORTANTE**: Todos los nodos del grafo son funciones `async def`.
LangGraph soporta nativamente nodos async y usa `astream()`/`ainvoke()` para ejecución.

El Graph Builder ahora incluye un **Step Compiler** que traduce la lista secuencial de pasos (formato procedural) en el grafo de estados de LangGraph.

```python
# soni/core/builder.py
from langgraph.graph import StateGraph, END
from langgraph.checkpoint.sqlite import SqliteSaver
from typing import TypedDict, Annotated, Dict, Any
import operator
import os
import yaml

class SoniGraphBuilder:
    def __init__(self, config_path: str, optimized_du_path: str = None):
        self.config = yaml.safe_load(open(config_path))
        self.graph = StateGraph(DialogueState)
        self.scope_manager = ScopeManager(self.config)
        self.normalizer = SlotNormalizer(self.config)

        # Cargar módulo DSPy (optimizado o base)
        self._init_du_module(optimized_du_path)

    def _init_du_module(self, optimized_path: str = None):
        """Inicializa el módulo DU, cargando versión optimizada si existe."""
        base_module = SoniDU(scope_manager=self.scope_manager)

        if optimized_path and os.path.exists(optimized_path):
            base_module.load(optimized_path)
            print(f"✓ Módulo DU optimizado cargado desde {optimized_path}")
        else:
            print("⚠ Usando módulo DU sin optimizar. Ejecuta optimize_soni_du() para mejorar.")

        # Envolver en adapter async para cumplir interfaz
        self.du_adapter = SoniDUAdapter(base_module)
        self.du_module = base_module

    def _create_du_node(self):
        """Crea nodo async para Dialogue Understanding."""
        adapter = self.du_adapter
        scope_manager = self.scope_manager

        async def understand_node(state: DialogueState) -> Dict[str, Any]:
            """Nodo async que llama al módulo DSPy via acall()."""
            scoped_actions = scope_manager.get_available_actions(state)

            # Llamada async al adapter
            nlu_result = await adapter.predict(
                message=state['messages'][-1]['content'],
                context=state,
                scoped_actions=scoped_actions
            )

            return {
                'nlu_result': nlu_result,
                'trace': state['trace'] + [{
                    'step': 'understand',
                    'command': nlu_result.command,
                    'confidence': nlu_result.confidence
                }]
            }

        return understand_node

    def _create_normalizer_node(self):
        """Crea nodo async para normalización."""
        normalizer = self.normalizer

        async def normalize_node(state: DialogueState) -> Dict[str, Any]:
            """Nodo async que normaliza slots extraídos."""
            nlu_result = state.get('nlu_result')
            if not nlu_result or not nlu_result.slots:
                return {}

            # Normalización async (puede usar LLM)
            normalized_slots = await normalizer.process(nlu_result.slots)

            # Merge con slots existentes
            updated_slots = {**state.get('slots', {}), **normalized_slots}

            return {'slots': updated_slots}

        return normalize_node

    def build(self) -> CompiledGraph:
        """Construye el grafo con todos los nodos async."""

        # Nodos base siempre presentes (todos async)
        self.graph.add_node("understand", self._create_du_node())
        self.graph.add_node("normalize", self._create_normalizer_node())
        self.graph.add_node("route", self._create_router_node())
        self.graph.add_node("fallback", self._create_fallback_node())
        self.graph.add_node("handoff", self._create_handoff_node())

        # Construir nodos dinámicos desde YAML
        for flow_name, flow_cfg in self.config['flows'].items():
            if 'process' in flow_cfg:
                # v1.2: Compilar proceso procedural
                self._build_process_graph(flow_name, flow_cfg['process'])
            elif 'graph' in flow_cfg:
                # v1.1: Mantener compatibilidad con grafos explícitos (deprecated)
                self._build_explicit_graph(flow_name, flow_cfg)
            else:
                # Nivel 2: Inferencia automática de slot-filling
                self._build_inferred_graph(flow_name, flow_cfg)

        self.graph.set_entry_point("understand")
        self.graph.add_edge("understand", "normalize")
        self.graph.add_edge("normalize", "route")

        checkpointer = self._get_checkpointer()
        return self.graph.compile(checkpointer=checkpointer)

    def _build_process_graph(self, flow_name: str, steps: list):
        """
        v1.2: Compila una lista secuencial de pasos (Business Logic)
        en un Grafo de Estados (Technical Implementation).

        Esta es la "magia" que traduce la sintaxis procedural a LangGraph.
        """
        previous_node_name = f"{flow_name}_entry"

        # Crear nodo de entrada dummy para anclar el flujo
        self.graph.add_node(previous_node_name, self._create_pass_node())

        # Mapeo de nombres de paso a nombres de nodo para saltos
        step_to_node = {}

        for i, step in enumerate(steps):
            step_name = step['step']
            node_name = f"{flow_name}_{step_name}"
            step_type = step['type']

            # Registrar para saltos
            step_to_node[step_name] = node_name

            # 1. Factory de Nodos: Crear el nodo LangGraph según el tipo de alto nivel
            if step_type == 'collect':
                self.graph.add_node(node_name, self._create_slot_node(step))
            elif step_type == 'action':
                self.graph.add_node(node_name, self._create_action_node(step))
            elif step_type == 'branch':
                # Los branches son nodos de decisión, no de proceso
                self.graph.add_node(node_name, self._create_router_node(step))
            elif step_type == 'say':
                self.graph.add_node(node_name, self._create_response_node(step))
            elif step_type == 'choice':
                self.graph.add_node(node_name, self._create_choice_node(step))
            elif step_type == 'confirm':
                self.graph.add_node(node_name, self._create_confirm_node(step))

            # 2. Conexión Automática (Implicit Next)
            # Conectar el nodo anterior con este, salvo que el anterior fuera terminal o un router
            if i > 0:
                prev_step = steps[i-1]
                prev_node_name = f"{flow_name}_{prev_step['step']}"

                # Si el paso anterior NO tenía lógica de saltos explícita, conectar linealmente
                if not self._is_branching_step(prev_step):
                    self.graph.add_edge(prev_node_name, node_name)

            # Conectar entrada del flujo al primer paso
            if i == 0:
                self.graph.add_edge(previous_node_name, node_name)

            # 3. Gestión de Saltos (Branching Logic)
            if 'jump_to' in step:
                target = step['jump_to']
                # Resolver el nombre del nodo destino
                target_node = step_to_node.get(target, f"{flow_name}_{target}")
                self.graph.add_edge(node_name, target_node)

            elif step_type == 'branch':
                # Crear aristas condicionales complejas
                mapping = {}
                for case_key, case_target in step['cases'].items():
                    if case_target == 'continue':
                        # Buscar el siguiente paso en la lista
                        if i + 1 < len(steps):
                            next_step_name = steps[i+1]['step']
                            mapping[case_key] = f"{flow_name}_{next_step_name}"
                        else:
                            mapping[case_key] = END
                    elif case_target.startswith('jump_to_'):
                        # Resolver salto
                        target = case_target.replace('jump_to_', '')
                        target_node = step_to_node.get(target, f"{flow_name}_{target}")
                        mapping[case_key] = target_node
                    else:
                        # Nombre directo del paso
                        target_node = step_to_node.get(case_target, f"{flow_name}_{case_target}")
                        mapping[case_key] = target_node

                self.graph.add_conditional_edges(
                    node_name,
                    self._get_branch_selector(step),
                    mapping
                )

            elif step_type == 'choice':
                # Crear aristas condicionales para opciones
                mapping = {}
                for option in step.get('options', []):
                    if 'jump_to' in option:
                        target = option['jump_to']
                        target_node = step_to_node.get(target, f"{flow_name}_{target}")
                        mapping[option['label']] = target_node

                self.graph.add_conditional_edges(
                    node_name,
                    self._get_choice_selector(step),
                    mapping
                )

    def _is_branching_step(self, step):
        """Determina si un paso gestiona su propio flujo de salida."""
        return step['type'] in ['branch', 'choice'] or 'jump_to' in step

    def _get_branch_selector(self, step):
        """Crea función selector para branches."""
        input_path = step.get('input', '')

        def selector(state: DialogueState) -> str:
            # Evaluar expresión de ruta (ej: "booking_status.status")
            value = self._resolve_path(state, input_path)
            return str(value)

        return selector

    def _get_choice_selector(self, step):
        """Crea función selector para choices (basado en input del usuario)."""
        def selector(state: DialogueState) -> str:
            # El usuario selecciona una opción del menú
            # Esto se maneja en el nodo choice_node
            last_message = state.get('messages', [])[-1] if state.get('messages') else {}
            return last_message.get('content', '')

        return selector

    def _resolve_path(self, obj: dict, path: str) -> Any:
        """Resuelve una ruta tipo 'a.b.c' en un objeto anidado."""
        parts = path.split('.')
        value = obj
        for part in parts:
            value = value.get(part, {})
        return value

    def _create_pass_node(self):
        """Nodo passthrough para puntos de entrada."""
        async def pass_node(state: DialogueState) -> Dict[str, Any]:
            return {}
        return pass_node

    def _create_slot_node(self, step: dict):
        """Crea nodo para recolectar un slot."""
        slot_name = step.get('slot')

        async def slot_node(state: DialogueState) -> Dict[str, Any]:
            # Lógica de slot-filling
            # Si el slot ya está en nlu_result, usarlo
            nlu_result = state.get('nlu_result')
            if nlu_result and slot_name in nlu_result.slots:
                updated_slots = {**state.get('slots', {}), slot_name: nlu_result.slots[slot_name]}
                return {'slots': updated_slots}
            # Si no, solicitar al usuario
            return {'pending_slot': slot_name}

        return slot_node

    def _create_action_node(self, step: dict):
        """Crea nodo para ejecutar una acción."""
        action_name = step.get('call')
        result_into = step.get('result_into')

        async def action_node(state: DialogueState) -> Dict[str, Any]:
            # Ejecutar acción async
            action_result = await self._execute_action(action_name, state)

            result = {}
            if result_into:
                result[result_into] = action_result

            return result

        return action_node

    def _create_response_node(self, step: dict):
        """Crea nodo para generar respuesta."""
        message_template = step.get('message', '')

        async def response_node(state: DialogueState) -> Dict[str, Any]:
            # Renderizar template con slots
            message = self._render_template(message_template, state.get('slots', {}))
            return {'last_response': message}

        return response_node

    def _create_router_node(self, step: dict):
        """Crea nodo router para branches."""
        # La lógica de routing se maneja en _get_branch_selector
        async def router_node(state: DialogueState) -> Dict[str, Any]:
            return {}

        return router_node

    def _create_choice_node(self, step: dict):
        """Crea nodo para menús de opciones."""
        prompt = step.get('prompt', '')
        options = step.get('options', [])

        async def choice_node(state: DialogueState) -> Dict[str, Any]:
            # Generar mensaje con opciones
            options_text = '\n'.join([f"- {opt['label']}" for opt in options])
            message = f"{prompt}\n\n{options_text}"
            return {'last_response': message, 'pending_choice': True}

        return choice_node

    def _create_confirm_node(self, step: dict):
        """Crea nodo para confirmaciones."""
        template = step.get('template', '')

        async def confirm_node(state: DialogueState) -> Dict[str, Any]:
            message = self._render_template(template, state.get('slots', {}))
            return {'last_response': message, 'pending_confirm': True}

        return confirm_node

    def _execute_action(self, action_name: str, state: dict) -> dict:
        """Ejecuta una acción definida en el YAML."""
        # Implementación de ejecución de acciones
        # (HTTP, Python, LangChain Tools)
        ...

    def _render_template(self, template: str, context: dict) -> str:
        """Renderiza un template con variables del contexto."""
        return template.format(**context)

    def _build_inferred_graph(self, flow_name: str, cfg: dict):
        """Genera grafo estándar de slot-filling (Nivel 2)."""

        # Nodo de slot-filling iterativo
        self.graph.add_node(
            f"{flow_name}_fill_slots",
            self._create_slot_filler(flow_name, cfg['slots'])
        )

        # Nodo de validación de constraints
        if 'constraints' in cfg:
            self.graph.add_node(
                f"{flow_name}_validate",
                self._create_validator(cfg['constraints'])
            )

        # Nodo de confirmación
        if cfg.get('on_complete', {}).get('confirm'):
            self.graph.add_node(
                f"{flow_name}_confirm",
                self._create_confirmation(cfg['on_complete'])
            )

        # Nodo de ejecución de acción
        self.graph.add_node(
            f"{flow_name}_execute",
            self._create_action_executor(cfg['on_complete']['action'])
        )

        # Configurar transiciones condicionales
        self.graph.add_conditional_edges(
            f"{flow_name}_fill_slots",
            self._check_slots_complete(cfg['slots']),
            {
                "complete": f"{flow_name}_validate",
                "missing": f"{flow_name}_fill_slots"
            }
        )

    def _get_checkpointer(self):
        """Configura el backend de persistencia."""
        backend = self.config.get('settings', {}).get('persistence', {}).get('backend', 'sqlite')

        if backend == 'sqlite':
            path = self.config['settings']['persistence'].get('path', './dialogue.db')
            return SqliteSaver.from_conn_string(path)
        elif backend == 'postgresql':
            from langgraph.checkpoint.postgres import PostgresSaver
            conn_string = self.config['settings']['persistence']['connection_string']
            return PostgresSaver.from_conn_string(conn_string)
        elif backend == 'redis':
            from langgraph.checkpoint.redis import RedisSaver
            url = self.config['settings']['persistence']['url']
            return RedisSaver.from_url(url)
```

### 4.7.1 Action Registry & Implementation (v1.3)

**v1.3:** Usamos decoradores para registrar las implementaciones. Esto permite cambiar de una API REST a una llamada a Base de Datos sin tocar el YAML.

```python
# soni/actions/registry.py
from typing import Callable, Any, Dict

class ActionRegistry:
    """Registry para acciones registradas mediante decoradores."""
    _actions: Dict[str, Callable] = {}

    @classmethod
    def register(cls, name: str):
        """Decorador para registrar una acción."""
        def decorator(func: Callable):
            cls._actions[name] = func
            return func
        return decorator

    @classmethod
    def get(cls, name: str) -> Callable:
        """Obtiene una acción registrada por nombre."""
        if name not in cls._actions:
            raise ValueError(f"Action '{name}' not registered. Available: {list(cls._actions.keys())}")
        return cls._actions[name]

    @classmethod
    def list_actions(cls) -> list[str]:
        """Lista todas las acciones registradas."""
        return list(cls._actions.keys())


# project/integrations/bookings.py
# Ejemplo de implementación técnica
from soni.actions import ActionRegistry
import httpx
import os

@ActionRegistry.register("check_booking_rules")
async def impl_check_booking(booking_ref: str) -> dict:
    """
    Implementación técnica: Aquí van los headers, URLs y JSONPaths.

    El YAML solo conoce el contrato (inputs/outputs), no esta implementación.
    """
    async with httpx.AsyncClient() as client:
        # Detalles sucios ocultos al analista de negocio
        resp = await client.post(
            "https://legacy-api.corp/v1/rules",
            json={"id": booking_ref},
            headers={"X-Auth": os.getenv("API_KEY")}
        )
        data = resp.json()

        # Adaptador: Normaliza la respuesta al contrato esperado
        return {
            "status": data.get("rule_status"),  # Mapping técnico
            "rejection_reason": data.get("error_msg", None)
        }


@ActionRegistry.register("modify_booking_api")
async def impl_modify_booking(booking_ref: str, new_date: str) -> dict:
    """Otra implementación - podría ser DB, gRPC, etc."""
    # Implementación técnica aquí
    return {"confirmation_id": "ABC123"}


@ActionRegistry.register("search_flights")
async def impl_search_flights(origin: str, destination: str, date: str) -> dict:
    """Implementación de búsqueda de vuelos."""
    # Llamada a API externa, procesamiento, etc.
    return {
        "count": 5,
        "cheapest": 299.99,
        "results": [...]
    }
```

### 4.7.2 Semantic Validators (v1.3)

**v1.3:** Igual que las acciones, los validadores se implementan en código Python, no en el YAML.

```python
# soni/validation/registry.py
from typing import Callable, Any, Dict

class ValidatorRegistry:
    """Registry para validadores semánticos."""
    _validators: Dict[str, Callable] = {}

    @classmethod
    def register(cls, name: str):
        """Decorador para registrar un validador."""
        def decorator(func: Callable):
            cls._validators[name] = func
            return func
        return decorator

    @classmethod
    def get(cls, name: str) -> Callable:
        """Obtiene un validador registrado por nombre."""
        if name not in cls._validators:
            raise ValueError(f"Validator '{name}' not registered. Available: {list(cls._validators.keys())}")
        return cls._validators[name]


# project/validators.py
from soni.validation import ValidatorRegistry
import re
from datetime import datetime

@ValidatorRegistry.register("booking_ref_format")
def validate_ref(value: str) -> bool:
    """
    Validador semántico: La regex compleja vive aquí, testeable unitariamente.

    El YAML solo referencia 'booking_ref_format', no contiene la regex.
    """
    return bool(re.match(r"^[A-Z]{2,3}\d{3,4}$", value))


@ValidatorRegistry.register("future_date_only")
def validate_future(value: datetime) -> bool:
    """Valida que la fecha sea futura."""
    return value > datetime.now()


@ValidatorRegistry.register("city_format")
def validate_city(value: str) -> bool:
    """Valida formato de ciudad."""
    return bool(re.match(r"^[A-Za-z\s]+$", value)) and len(value) >= 2
```

### 4.7.3 Step Compiler Actualizado: Manejo de Output Mapping (v1.3)

El compilador ahora debe gestionar el mapeo de variables (`map_outputs`) para desacoplar estructuras de datos.

```python
# soni/core/builder.py (actualización del método _create_action_node)

    def _create_action_node(self, step: dict):
        """Crea nodo para ejecutar una acción con soporte de map_outputs (v1.3)."""
        action_name = step.get('call')
        output_mapping = step.get('map_outputs', {})  # v1.3: Mapeo de outputs

        async def action_node(state: DialogueState) -> Dict[str, Any]:
            # 1. Resolver implementación desde el Registry
            func = ActionRegistry.get(action_name)

            # 2. Preparar argumentos desde slots actuales
            # (Simplificado: asume que args coinciden con inputs del contrato)
            import inspect
            sig = inspect.signature(func)
            args = {}
            for param_name in sig.parameters.keys():
                if param_name in state.slots:
                    args[param_name] = state.slots[param_name]

            # 3. Ejecutar implementación técnica
            raw_result = await func(**args)

            # 4. Aplicar Output Mapping (Flattening) - v1.3
            # Convierte el dict de resultado en variables planas de estado
            updates = {}
            if output_mapping:
                # Mapeo explícito: output_accion -> variable_flujo
                for tech_key, flow_key in output_mapping.items():
                    updates[flow_key] = raw_result.get(tech_key)
            else:
                # Fallback: volcar todo si no hay mapping
                updates = raw_result

            # Actualizar estado (slots temporales o de contexto)
            return {"slots": {**state.get('slots', {}), **updates}}

        return action_node
```

### 4.8 Runtime con Streaming (v1.1)

```python
# soni/runtime.py
from typing import AsyncGenerator
import asyncio

class RuntimeLoop:
    """Runtime loop para Soni."""

    def __init__(self, config_path: str, optimized_du_path: str = None):
        builder = SoniGraphBuilder(config_path, optimized_du_path)
        self.graph = builder.build()

        # Usar el adapter async que envuelve el módulo DSPy optimizado
        self.nlu = builder.du_adapter  # INLUProvider (async)
        self.normalizer = builder.normalizer  # SlotNormalizer (async)
        self.state_store = StateStore(builder.config)
        self.security = SecurityGuard(builder.config)
        self.tracer = TraceLogger(builder.config)
        self.scope_manager = builder.scope_manager

    async def process_message(
        self,
        user_msg: str,
        user_id: str
    ) -> AsyncGenerator[str, None]:
        """
        Procesa un mensaje con streaming de respuesta.
        Todo el pipeline es async.
        """
        # 1. Cargar estado (async I/O)
        state = await self.state_store.load(user_id)

        # 2. Obtener acciones disponibles según contexto
        scoped_actions = self.scope_manager.get_available_actions(state)

        # 3. NLU async (DSPy acall -> gpt-4o-mini)
        nlu_result = await self.nlu.predict(
            message=user_msg,
            context=state,
            scoped_actions=scoped_actions
        )

        # 4. Normalización async (puede usar LLM)
        nlu_result.slots = await self.normalizer.process(nlu_result.slots)

        # 5. Validación de seguridad (sync, operación rápida CPU-bound)
        is_valid, error_msg = self.security.validate_action(
            nlu_result.command,
            state
        )
        if not is_valid:
            yield error_msg
            return

        # 6. LangGraph Execution con astream (Streaming async)
        async for event in self.graph.astream(
            state,
            input={"nlu_result": nlu_result},
            stream_mode="updates"
        ):
            if event.get('type') == 'token':
                yield event['content']  # Enviar al frontend inmediatamente
            elif event.get('type') == 'state_update':
                await self.state_store.save(user_id, event['new_state'])

        # 7. Logging async de trazabilidad
        await self.tracer.log_turn(state, nlu_result, event.get('policy_decision', {}))


class StateStore:
    """Almacenamiento de estado async."""

    def __init__(self, config: dict):
        self.backend = config.get('persistence', {}).get('backend', 'sqlite')
        # Inicializar conexión async según backend

    async def load(self, user_id: str) -> dict:
        """Carga estado de forma async."""
        # Implementar con aiosqlite, asyncpg, aioredis, etc.
        ...

    async def save(self, user_id: str, state: dict):
        """Guarda estado de forma async."""
        ...


class TraceLogger:
    """Logger async para trazabilidad."""

    def __init__(self, config: dict):
        self.audit_enabled = config.get('logging', {}).get('audit_log', False)

    async def log_turn(self, state: dict, nlu_result, policy_decision: dict):
        """Log async del turno."""
        if self.audit_enabled:
            # Escribir a archivo/DB de forma async
            ...
```

### 4.8.1 Integración con FastAPI

```python
# soni/api/main.py
from fastapi import FastAPI
from fastapi.responses import StreamingResponse
import asyncio

app = FastAPI()
runtime = RuntimeLoop("config.yaml", "optimized_du.json")

@app.post("/chat/{user_id}")
async def chat(user_id: str, message: str):
    """Endpoint async con streaming SSE."""

    async def generate():
        async for token in runtime.process_message(message, user_id):
            yield f"data: {token}\n\n"
        yield "data: [DONE]\n\n"

    return StreamingResponse(
        generate(),
        media_type="text/event-stream"
    )

@app.get("/health")
async def health():
    return {"status": "ok"}
```

### 4.9 Sistema de Seguridad y Guardrails

```python
# soni/security/guardrails.py
class SecurityGuard:
    """Sistema de guardrails para validar acciones y prevenir comportamientos no deseados."""

    def __init__(self, config: dict):
        self.allowed_actions = config.get('security', {}).get('allowed_actions', [])
        self.blocked_intents = config.get('security', {}).get('blocked_intents', [])
        self.max_confidence = config.get('security', {}).get('max_confidence_threshold', 0.95)

    def validate_action(self, action: str, state: dict) -> tuple[bool, str]:
        """Valida si una acción está permitida."""
        if self.allowed_actions and action not in self.allowed_actions:
            return False, f"Acción '{action}' no está en la lista de acciones permitidas"

        # Validaciones adicionales de negocio
        if action.startswith("delete_") and not state.get('admin_mode'):
            return False, "Acciones de eliminación requieren modo administrador"

        return True, ""

    def validate_intent(self, intent: str) -> tuple[bool, str]:
        """Valida si un intent está permitido."""
        if intent in self.blocked_intents:
            return False, f"Intent '{intent}' está bloqueado"
        return True, ""

    def validate_confidence(self, confidence: float) -> tuple[bool, str]:
        """Valida el nivel de confianza."""
        if confidence > self.max_confidence:
            return False, f"Confianza {confidence} excede el umbral máximo {self.max_confidence}"
        return True, ""
```

### 4.10 Sistema de Trazabilidad

```python
# soni/tracing/logger.py
from datetime import datetime
import aiosqlite  # O asyncpg para PostgreSQL

class TraceLogger:
    """Sistema de logging y trazabilidad async para auditoría."""

    def __init__(self, config: dict):
        self.audit_enabled = config.get('logging', {}).get('audit_log', False)
        self.trace_enabled = config.get('logging', {}).get('trace_graphs', False)
        self.db_path = config.get('logging', {}).get('db_path', 'audit.db')

    async def log_turn(
        self,
        state: DialogueState,
        nlu_result: NLUResult,
        policy_decision: dict
    ):
        """Registra un turno completo de conversación de forma async."""
        if not self.audit_enabled:
            return

        trace_entry = {
            'timestamp': datetime.now().isoformat(),
            'turn': state.turn_count,
            'user_message': state.messages[-1] if state.messages else None,
            'nlu': {
                'command': nlu_result.command,
                'slots': nlu_result.slots,
                'confidence': nlu_result.confidence,
                'reasoning': nlu_result.reasoning
            },
            'policy': {
                'action': policy_decision.get('action'),
                'next_node': policy_decision.get('next_node'),
                'reasoning': policy_decision.get('reasoning')
            },
            'state_snapshot': {
                'current_flow': state.current_flow,
                'slots': state.slots
            }
        }

        state.trace.append(trace_entry)

        # Persistir en base de datos de auditoría de forma async
        if self.audit_enabled:
            await self._persist_audit_log(trace_entry)

    async def _persist_audit_log(self, trace_entry: dict):
        """Persiste entrada de auditoría de forma async."""
        import json
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                "INSERT INTO audit_log (timestamp, data) VALUES (?, ?)",
                (trace_entry['timestamp'], json.dumps(trace_entry))
            )
            await db.commit()
```

### 4.11 Human Handoff

```python
# soni/handoff/manager.py
import httpx  # Cliente HTTP async
from datetime import datetime

class HandoffManager:
    """Gestiona la transferencia de control a agentes humanos de forma async."""

    def __init__(self, config: dict):
        self.enabled = config.get('handoff', {}).get('enabled', False)
        self.webhook = config.get('handoff', {}).get('webhook')
        self.include_context = config.get('handoff', {}).get('include_context', True)
        # Cliente HTTP async reutilizable
        self._client: httpx.AsyncClient | None = None

    async def _get_client(self) -> httpx.AsyncClient:
        """Obtiene o crea cliente HTTP async."""
        if self._client is None:
            self._client = httpx.AsyncClient(timeout=30.0)
        return self._client

    async def initiate_handoff(self, state: DialogueState, reason: str) -> dict:
        """Inicia el proceso de handoff a un agente humano de forma async."""
        if not self.enabled:
            return {}

        handoff_data = {
            'conversation_id': state.get('conversation_id'),
            'reason': reason,
            'timestamp': datetime.now().isoformat()
        }

        if self.include_context:
            handoff_data['context'] = {
                'current_flow': state.current_flow,
                'slots': state.slots,
                'history': state.messages[-10:],  # Últimos 10 mensajes
                'trace': state.trace[-5:]  # Últimos 5 turnos
            }

        # Notificar al sistema externo de forma async
        if self.webhook:
            client = await self._get_client()
            await client.post(self.webhook, json=handoff_data)

        return {
            'action': 'paused',
            'message': "Un agente humano tomará el control en breve."
        }

    async def close(self):
        """Cierra el cliente HTTP async."""
        if self._client:
            await self._client.aclose()
            self._client = None
```

### 4.12 Estructura del Proyecto

```
soni/
├── pyproject.toml
├── soni/
│   ├── __init__.py
│   ├── core/
│   │   ├── builder.py        # SoniGraphBuilder
│   │   ├── state.py          # DialogueState
│   │   ├── config.py         # Carga y validación YAML
│   │   ├── interfaces.py     # Protocolos (INLUProvider, IDialogueManager, etc.)
│   │   ├── scope.py          # ScopeManager (v1.1)
│   │   └── errors.py         # Excepciones del dominio
│   ├── du/
│   │   ├── signatures.py     # DSPy Signatures (DialogueUnderstanding)
│   │   ├── modules.py        # SoniDU (dspy.Module optimizable)
│   │   ├── adapter.py        # SoniDUAdapter (implementa INLUProvider)
│   │   ├── normalizer.py     # SlotNormalizer (v1.1)
│   │   ├── optimizers.py     # MIPROv2, SIMBA, GEPA configs + optimize_soni_du()
│   │   └── metrics.py        # Métricas de evaluación (intent_accuracy, slot_f1)
│   ├── dm/
│   │   ├── nodes.py          # Nodos del grafo
│   │   ├── edges.py          # Lógica de transiciones
│   │   └── checkpointers.py  # Adaptadores persistencia
│   ├── security/
│   │   ├── guardrails.py     # Sistema de guardrails
│   │   └── validator.py      # Validación de acciones
│   ├── tracing/
│   │   ├── logger.py         # Sistema de trazabilidad
│   │   └── audit.py          # Auditoría
│   ├── actions/
│   │   ├── registry.py       # Action Registry (v1.3)
│   │   └── base.py           # Base classes para acciones
│   ├── validation/
│   │   ├── registry.py       # Validator Registry (v1.3)
│   │   └── base.py           # Base classes para validadores
│   ├── handoff/
│   │   └── manager.py        # Gestión de handoff
│   ├── nlg/
│   │   ├── templates.py      # Respuestas template
│   │   └── generative.py     # Respuestas LLM con streaming
│   ├── server/
│   │   ├── api.py            # FastAPI endpoints
│   │   └── websocket.py      # WebSocket support con streaming
│   └── cli/
│       ├── __init__.py
│       └── optimize.py       # CLI: soni optimize --config soni.yaml
├── tests/
│   ├── unit/
│   │   ├── test_du_module.py # Tests del módulo DSPy
│   │   └── test_optimizer.py # Tests de optimización
│   ├── integration/
│   └── e2e/
├── examples/
│   ├── flight_booking/
│   │   ├── soni.yaml
│   │   ├── actions.py
│   │   └── optimized_du.json # Módulo optimizado guardado
│   └── customer_service/
├── docs/
├── optimized/                 # Directorio para módulos optimizados
│   └── .gitkeep
└── langgraph.json            # Configuración LangGraph Studio
```

### 4.13 Dependencias

```toml
# pyproject.toml
[project]
name = "soni"
version = "1.3.0"
requires-python = ">=3.11"  # Python 3.11+ para mejor soporte async

dependencies = [
    # Core async
    "asyncio>=3.4",

    # Frameworks principales
    "dspy>=2.6.0",          # Soporte nativo async: acall(), aforward()
    "langgraph>=0.2.0",     # Soporte nativo async: astream(), ainvoke()

    # Persistencia async
    "aiosqlite>=0.19.0",    # SQLite async
    "asyncpg>=0.29.0",      # PostgreSQL async (opcional)
    "aioredis>=2.0.0",      # Redis async (opcional)

    # Web framework async-native
    "fastapi>=0.109.0",
    "uvicorn[standard]>=0.27.0",

    # HTTP async
    "httpx>=0.26.0",        # Cliente HTTP async para acciones
    "aiohttp>=3.9.0",       # Alternativa para WebSockets

    # LLM providers (todos usan async internamente via litellm)
    "litellm>=1.30.0",

    # Observabilidad
    "langfuse>=2.0.0",      # Async compatible

    # Validación
    "pydantic>=2.5.0",
    "pyyaml>=6.0.0",
]

[project.optional-dependencies]
dev = [
    "pytest>=7.4.0",
    "pytest-asyncio>=0.23.0",  # Tests async
    "anyio>=4.2.0",
]
```

**NOTA IMPORTANTE**: No se incluyen wrappers sync-to-async como `asyncify` porque el framework es nativo async. Todas las interfaces expuestas son async por diseño.

---

## 5. Justificación Técnica

### 5.1 Por qué DSPy para Dialogue Understanding

DSPy (versión actual: 2.6.x, Nov 2025) es el framework elegido porque **la optimización automática es la propuesta de valor central de Soni**:

- **Módulo optimizable**: `SoniDU` hereda de `dspy.Module` y define `aforward()`, permitiendo que los optimizadores mejoren automáticamente los prompts
- **Invocación con `acall()`**: Integración natural con el runtime
- **MIPROv2 con auto-configuración**: Modos light/medium/heavy que ajustan hiperparámetros automáticamente
- **Nuevos optimizadores**: SIMBA para tareas agenticas de horizonte largo, GEPA con evolución reflexiva
- **Serialización**: `.save()` y `.load()` permiten guardar y reutilizar módulos optimizados
- **Modularidad**: Las Signatures son componibles y testeables de forma aislada
- **Portabilidad**: Cambiar de GPT-4 a Claude o Llama requiere solo reoptimizar, no reescribir
- **Métricas personalizadas**: El optimizer usa métricas de negocio (`intent_accuracy`, `slot_f1`)
- **Constrained generation**: `available_actions` (filtradas por ScopeManager) reduce alucinaciones
- **Explicabilidad**: Cada predicción incluye `reasoning` para debugging
- **Observabilidad**: Integración nativa con MLflow 3.0 y Langfuse para tracking de optimización
- **Adopción empresarial**: JetBlue, Databricks, Walmart, VMware, Replit, Sephora, Moody's

### 5.2 Por qué LangGraph para Dialogue Management

LangGraph (actualizado continuamente, Nov 2025) es el framework elegido porque:

- **Ejecución con `astream()`/`ainvoke()`**: Nodos son funciones `async def`
- **Determinismo**: Las transiciones son funciones Python puras, no generación LLM
- **Trazabilidad**: El grafo es visualizable y auditable (LangGraph Studio v2)
- **Persistencia nativa**: Checkpointers para SQLite, PostgreSQL, Redis out-of-the-box
- **Memoria a largo plazo**: LangMem SDK para aprendizaje y mejora a través de memoria persistente
- **Human-in-the-loop**: `interrupt` nativo para flujos con intervención humana
- **Command API**: Flujos dinámicos sin aristas fijas
- **Time Travel**: Capacidad de rebobinar y re-ejecutar desde cualquier punto
- **Streaming nativo**: `astream()` con múltiples modos (updates, messages, custom) para streaming de tokens y eventos
- **Node caching**: Cache a nivel de nodo/tarea para desarrollo más rápido
- **Deferred nodes**: Ejecución diferida hasta completar caminos upstream
- **Multi-agent**: LangGraph Supervisor y LangGraph Swarm para sistemas multi-agente
- **Adopción empresarial**: Klarna, Replit, Elastic, JetBlue

### 5.3 Por qué YAML como DSL

- **Legibilidad**: Un product manager puede entender y modificar flujos sin código
- **Versionable**: Git diff muestra cambios claros en la lógica de negocio
- **Validación**: JSON Schema permite validar configuraciones antes de runtime
- **Separación de concerns**: La lógica de negocio está separada del framework
- **Híbrido**: El 80% de casos usa inferencia automática, el 20% tiene control total
- **Declarativo**: Define QUÉ hacer, no CÓMO hacerlo

### 5.4 Justificación de Cambios v1.1

#### 5.4.1 Scoping Dinámico

**Problema:** Al tener 50 flujos, el prompt contenía demasiadas opciones, confundiendo al LLM.
**Solución:** El `ScopeManager` actúa como un filtro de atención forzada. El LLM solo ve lo que es relevante *ahora*.
**Beneficio:** Aumenta drásticamente la precisión (`intent_accuracy`) y reduce el consumo de tokens de entrada.

#### 5.4.2 NLU Layering (Modelos Rápidos)

**Problema:** Usar GPT-4 para extraer entidades simples es lento y caro.
**Solución:** Separar la configuración de modelos. NLU usa modelos rápidos (`gpt-4o-mini`, `Llama-3-8b`), Generación usa modelos capaces.
**Beneficio:** Reducción de latencia del 40-60% en el primer salto.

#### 5.4.3 Normalización Explícita

**Problema:** Rechazo de datos válidos porque el usuario añadió ruido ("Quiero ir a Madrid, por favor" → Slot "Madrid, por favor" → Regex Fallido).
**Solución:** Capa intermedia que limpia el dato antes de validarlo.
**Beneficio:** Experiencia de usuario más fluida, menos repeticiones de "No he entendido el destino".

#### 5.4.4 Interfaces SOLID

**Problema:** Dependencia directa de DSPy y LangGraph dificultaba testing y evolución.
**Solución:** Protocolos Python que definen contratos claros.
**Beneficio:** Permite mocking para tests, swap de implementaciones, y evolución independiente.

### 5.5 Justificación de Cambios v1.2

#### 5.5.1 DSL Procedural (Business-First)

**Problema:** En versiones anteriores, obligar a los usuarios a definir `nodes`, `edges` y `conditional_transitions` en el YAML exponía demasiada complejidad técnica. Un analista de negocio piensa en "pasos secuenciales" y "decisiones", no en teoría de grafos.

**Solución:** Se reemplaza la definición técnica de grafos por una definición **procedural basada en pasos (`steps`)**. El YAML se lee de arriba a abajo como una receta, con `next` implícito y saltos explícitos solo cuando son necesarios.

**Beneficios:**
- **Reducción de Carga Cognitiva:** Al pasar de un modelo mental de grafo a uno procedural, alineamos la herramienta con la forma en que los humanos describen procesos: "Primero haz A, luego B, si pasa X ve a Z".
- **Mantenibilidad:** Es más fácil reordenar una lista en YAML que reconectar nodos y aristas manualmente. El compilador asume la responsabilidad de la coherencia de las conexiones.
- **Sin Pérdida de Potencia:** Aunque la sintaxis es lineal por defecto, el soporte de `jump_to` y `branch` permite representar cualquier máquina de estados compleja (bucles, saltos condicionales, máquinas de estado finito).
- **Democratización:** Permite que analistas de negocio y product managers definan flujos complejos sin conocimiento de teoría de grafos.

### 5.6 Justificación de Cambios v1.3 (Zero-Leakage Architecture)

#### 5.6.1 Arquitectura Hexagonal Real

**Problema:** En v1.2, aunque mejoramos el flujo procedural, persistían detalles técnicos (HTTP, JSONPath, Regex) que acoplaban la lógica de negocio a la infraestructura. Un cambio en una API externa requería editar el YAML de negocio.

**Solución:** Se implementa una **Arquitectura Hexagonal (Ports & Adapters)** real:
- **YAML (Núcleo):** Solo habla el lenguaje del dominio (Vuelos, Reservas, Fechas).
- **Python (Adaptadores):** Maneja la suciedad técnica (HTTP, Regex, SQL).

**Beneficios:**
- **Robustez ante Cambios:** Si la API de vuelos cambia su respuesta de `error_msg` a `details.message`, solo el desarrollador actualiza `impl_check_booking` en Python. El archivo YAML del flujo de negocio permanece intacto.
- **Testabilidad Aislada:**
  - **YAML:** Se valida contra esquema.
  - **Acciones Python:** Se testean con PyTest y Mocks de HTTP.
  - **Validadores:** Unit testing puro (`assert validate_ref("ABC") == False`).
- **Roles Claros:**
  - **Analista/PM:** Edita YAML. Define "Qué".
  - **Ingeniero:** Edita Python. Define "Cómo".
- **Reusabilidad:** El validador `booking_ref_format` se define una vez y se usa en 10 flujos diferentes.

#### 5.6.2 Action Registry (Desacoplamiento de Implementación)

**Problema:** Definir `method: POST`, `url`, y `jsonpath` en el YAML crea acoplamiento directo con la infraestructura HTTP.

**Solución:** **Action Registry** con decoradores. Las acciones se definen como contratos en YAML (inputs/outputs) y se implementan en Python con `@ActionRegistry.register`.

**Beneficio:** Permite cambiar de una API REST a una llamada a Base de Datos sin tocar el YAML. El flujo de negocio es inmune a cambios en la infraestructura.

#### 5.6.3 Semantic Validators (Desacoplamiento de Regex)

**Problema:** Expresiones como `^[A-Z]{6}$` en el YAML son ilegibles y propensas a errores para no-programadores.

**Solución:** **Validator Registry** con decoradores. Los validadores se referencian por nombre semántico (`booking_ref_format`) y se implementan en Python.

**Beneficio:** El YAML es legible para analistas de negocio. La complejidad técnica (regex, lógica de validación) vive en código testeable.

#### 5.6.4 Output Mapping (Desacoplamiento de Estructuras)

**Problema:** Navegar objetos (`res.data.status`) en el flujo crea dependencias ocultas sobre la estructura interna de las respuestas.

**Solución:** **`map_outputs`** en pasos de acción. Mapea outputs técnicos a variables planas del flujo.

**Beneficio:** El flujo trabaja con variables planas (`api_status`), no objetos anidados. Cambios en la estructura de respuesta solo requieren actualizar el mapeo, no el flujo completo.

---

## 6. Seguridad y Trazabilidad

### 6.1 Guardrails y Validación

El framework implementa múltiples capas de seguridad:

1. **Validación de Acciones**: Solo acciones definidas en YAML pueden ejecutarse
2. **Validación de Intents**: Intents bloqueados no pueden activarse
3. **Validación de Slots**: Constraints del YAML validan valores antes de ejecutar acciones
4. **Umbrales de Confianza**: Acciones críticas requieren alta confianza
5. **Sanitización de Inputs**: Todos los inputs del usuario son sanitizados antes de procesar
6. **Scoping Dinámico**: El LLM solo puede "ver" acciones contextualmente válidas

### 6.2 Trazabilidad Completa

Cada turno de conversación genera una traza completa que incluye:

- Mensaje del usuario
- Resultado de NLU (intent, slots, confianza, reasoning)
- Decisión de política (acción, siguiente nodo, reasoning)
- Estado del diálogo (slots, flujo activo)
- Timestamp y metadata

Esto permite:
- **Debugging**: Identificar exactamente dónde falló el sistema
- **Auditoría**: Cumplimiento de regulaciones (GDPR, etc.)
- **Mejora continua**: Análisis de conversaciones fallidas para optimización
- **Explicabilidad**: Mostrar al usuario por qué se tomó una decisión

### 6.3 Visualización y Debugging

- **LangGraph Studio v2**: Visualización interactiva del grafo en tiempo real con integración LangSmith
- **State Inspection**: Inspección y modificación del estado en cualquier punto
- **Trace Visualization**: Visualización de la traza completa de una conversación
- **Performance Metrics**: Métricas de latencia y uso de recursos
- **Time Travel Debugging**: Rebobinar y re-ejecutar desde cualquier punto

---

## 7. Consecuencias

### 7.1 Positivas

| Aspecto | Beneficio |
|---------|-----------|
| **Optimización Automática** | `SoniDU` como `dspy.Module` permite optimizar prompts con MIPROv2/SIMBA sin prompt engineering manual. |
| **Alto Throughput** | Arquitectura asíncrona permite máximo rendimiento, streaming nativo, integración directa con FastAPI. |
| **Robustez** | Separación DU/DM mitiga fallos en cascada. DST persistente sobrevive a reinicios. |
| **Escalabilidad** | DSPy permite optimización automática sin reentrenar modelos manualmente. Scoping reduce carga de contexto. |
| **Trazabilidad** | El grafo ES la política. Debugging y RCOF simplificados. |
| **Mantenibilidad** | YAML como fuente de verdad. Cambios de negocio sin tocar código Python. |
| **Time-to-Market** | Flujos declarativos permiten prototipar asistentes en horas, no semanas. |
| **Seguridad** | Guardrails y validaciones previenen comportamientos no deseados. |
| **Auditabilidad** | Trazabilidad completa para cumplimiento regulatorio. |
| **Latencia** | Modelos diferenciados + Streaming reducen latencia percibida hasta 60%. |
| **Testabilidad** | Interfaces SOLID permiten mocking y tests unitarios aislados. |
| **Accesibilidad (v1.2)** | DSL procedural permite que analistas de negocio definan flujos sin conocimiento técnico de grafos. |
| **Robustez (v1.3)** | Zero-Leakage Architecture: Cambios en APIs externas solo requieren actualizar código Python, no el YAML de negocio. |
| **Separación de Responsabilidades (v1.3)** | Roles claros: Analistas editan YAML (Qué), Ingenieros editan Python (Cómo). |

### 7.2 Negativas y Mitigaciones

| Riesgo | Impacto | Mitigación |
|--------|---------|------------|
| **Complejidad de integración** | Esfuerzo inicial para crear el Graph Builder | Inversión única. Templates y ejemplos reducen curva. |
| **Dependencia de librerías** | Acoplamiento a DSPy y LangGraph | Interfaces abstractas permiten swap. Ambas son activamente mantenidas. |
| **Curva de aprendizaje** | Desarrolladores deben aprender dos paradigmas | Documentación exhaustiva + ejemplos progresivos. |
| **Latencia residual** | Aún hay doble llamada en algunos casos | Caching agresivo. Modelos pequeños para NLU. Streaming para UX. |
| **Costo de LLM** | Múltiples llamadas por turno | Modelos locales para desarrollo, optimización de prompts, modelos mini para NLU. |

---

## 8. Alternativas Consideradas

### 8.1 LLM End-to-End Puro

**Rechazado porque:**
- No garantiza determinismo en lógica de negocio crítica
- DST volátil y difícil de auditar
- Costes de inferencia más altos por turno
- Dificultad para implementar políticas de empresa estrictas
- Imposibilidad de garantizar seguridad y cumplimiento

### 8.2 Rasa con Componentes LLM

**Rechazado porque:**
- Arquitectura legacy no diseñada para LLMs
- Mantenimiento incierto del proyecto
- Configuración compleja (múltiples archivos YAML, entrenamiento NLU)
- No aprovecha optimización automática de prompts

### 8.3 Solo DSPy sin LangGraph

**Rechazado porque:**
- DSPy no tiene primitivas de máquina de estados
- Gestión de estado manual propensa a errores
- Sin persistencia built-in
- Falta de trazabilidad visual
- Dificultad para implementar políticas complejas

### 8.4 LangGraph sin DSPy

**Rechazado porque:**
- Requiere prompt engineering manual (frágil)
- No hay optimización automática
- Dificultad para adaptar a nuevos dominios
- Mantenimiento costoso de prompts

### 8.5 Google ADK

**Considerado pero descartado porque:**
- Todavía en fase early-stage (Nov 2025)
- Mejor para experimentación que producción
- Mayor acoplamiento con ecosistema Google

---

## 9. Roadmap de Implementación

| Fase | Entregable | Descripción |
|------|------------|-------------|
| **1** | Core & Interfaces | Definición de protocolos `INLUProvider`, `IDialogueManager`, `INormalizer`, `IScopeManager` |
| **2** | DSPy Module Base | Implementar `SoniDU` como `dspy.Module` con `forward()` optimizable |
| **3** | Scoping Dinámico | Implementar `ScopeManager` para filtrado de contexto |
| **4** | Normalización & Validación | Implementar `SlotNormalizer` con estrategias |
| **5** | **Optimización DSPy** | **Pipeline de optimización con MIPROv2/SIMBA, métricas, datasets, evaluación** |
| **6** | YAML Parser + State | Parsing YAML, validación JSON Schema, DialogueState base |
| **7** | Graph Builder (Nivel 2) | Inferencia automática de grafos desde flujos declarativos |
| **8** | **Step Compiler (v1.2)** | **Implementar la lógica de traducción `List[Step] -> StateGraph`** |
| **9** | Action Registry | Sistema de plugins: HTTP, Python, LangChain Tools |
| **10** | Security & Tracing | Guardrails, validación, sistema de trazabilidad |
| **11** | Runtime Async/Stream | Loop principal con soporte WebSocket y streaming |
| **12** | Persistencia + Server | Checkpointers, FastAPI, WebSocket |
| **13** | Handoff & Integrations | Human handoff, integración con sistemas externos |
| **14** | CLI de Optimización | Comando `soni optimize` para optimizar módulos fácilmente |
| **15** | Documentación + Ejemplos | Docs site, ejemplos progresivos, video tutorials |

---

## 10. Referencias

### Documentación Oficial
1. DSPy Documentation: https://dspy.ai
2. LangGraph Documentation: https://langchain-ai.github.io/langgraph/
3. LangGraph Studio: https://www.langchain.com/langgraph

### Papers y Optimizadores
4. DSPy: Compiling Declarative Language Model Calls into Self-Improving Pipelines (Khattab et al., 2024)
5. MIPROv2: Optimizing Prompts via Multi-stage Instruction Proposal
6. SIMBA: Prompt optimizer for agentic/long-horizon tasks
7. GEPA: Reflective Prompt Evolution (Agrawal et al., 2025)
8. Arbor: Multi-module GRPO for DSPy programs (Ziems et al., 2025)

### Arquitectura y Patrones
9. Task-Oriented Dialogue Systems Survey (2023)
10. Hybrid ToD Systems: Combining Neural and Symbolic Approaches

### Herramientas Complementarias
11. LangMem SDK: https://github.com/langchain-ai/langmem
12. LangGraph Supervisor: https://github.com/langchain-ai/langgraph-supervisor
13. MLflow 3.0: https://mlflow.org

---

## Apéndice A: Ejemplo Completo de YAML

```yaml
# soni.yaml - Flight Booking Assistant
version: "1.0"

settings:
  models:
    nlu:
      provider: openai
      model: gpt-4o-mini
      temperature: 0.1
    generation:
      provider: openai
      model: gpt-4o
      temperature: 0.7
  dspy:
    optimizer: MIPROv2
    metric: intent_accuracy
    auto_config: medium
  persistence:
    backend: sqlite
    path: ./data/dialogue.db
  security:
    enable_guardrails: true
    max_confidence_threshold: 0.95
  logging:
    level: INFO
    trace_graphs: true
    audit_log: true
  history:
    max_messages: 10
    summarize_after: 10
    summary_model: gpt-4o-mini

entities:
  - name: city
    type: string
    examples: [Madrid, Barcelona, NYC, London, París, Roma]
    normalization:
      strategy: llm_correction
  - name: date
    type: datetime
    format: "%Y-%m-%d"
    normalization:
      strategy: trim
  - name: cabin_class
    type: enum
    values: [economy, business, first]

flows:
  book_flight:
    description: "Reserva de vuelos"
    triggers:
      - "quiero reservar un vuelo"
      - "necesito volar a {destination}"
      - "busca vuelos"
    slots:
      origin:
        entity: city
        required: true
        prompt: "¿Desde qué ciudad quieres salir?"
      destination:
        entity: city
        required: true
        prompt: "¿A qué ciudad quieres volar?"
      date:
        entity: date
        required: true
        prompt: "¿Qué día quieres viajar?"
      cabin:
        entity: cabin_class
        required: false
        default: economy
    constraints:
      - condition: "origin != destination"
        error: "Origen y destino deben ser diferentes"
    on_complete:
      action: search_flights
      confirm: true
      confirmation_template: |
        Buscaré vuelos de {origin} a {destination}
        el {date} en clase {cabin}. ¿Confirmas?
    responses:
      success: "Encontré {count} vuelos. El más económico: {cheapest}€"
      no_results: "No hay vuelos disponibles."

actions:
  search_flights:
    type: http
    method: POST
    url: "https://api.example.com/flights/search"
    body:
      origin: "{origin}"
      destination: "{destination}"
      date: "{date}"

fallback:
  no_intent:
    response: "No entendí. ¿Puedes reformular?"
    max_retries: 2
  out_of_scope:
    response: "Solo puedo ayudar con vuelos."

interruptions:
  allow_during_flow: true
  intents:
    - name: cancel
      triggers: ["cancelar", "déjalo"]
      action: abort_current_flow

handoff:
  enabled: true
  triggers:
    - "hablar con un humano"
  webhook: "https://api.company.com/handoff"
  message: "Te paso con un agente. Un momento..."
  include_context: true
```

---

## Historial de Versiones

| Versión | Fecha | Cambios |
|---------|-------|---------|
| 1.0 | 28/11/2025 | Versión inicial: Arquitectura Híbrida Desacoplada |
| 1.1 | 28/11/2025 | Añadido: Scoping Dinámico, Normalización, Interfaces SOLID, Streaming, referencias actualizadas |
| 1.2 | 28/11/2025 | **DSL Procedural:** Reemplazo de grafos explícitos por definición procedural basada en pasos (`process`, `steps`). Step Compiler para traducción automática a LangGraph. Mantiene compatibilidad con v1.1. |
| 1.3 | 28/11/2025 | **Zero-Leakage Architecture:** YAML puramente semántico. Action Registry y Validator Registry para desacoplamiento total. Output Mapping (`map_outputs`) para desacoplar estructuras de datos. Arquitectura Hexagonal real (Ports & Adapters). |

---

**Fin del Documento**
