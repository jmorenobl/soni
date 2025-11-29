Registro de Decisión de Arquitectura
ADR-001
Título	Arquitectura Híbrida para Framework ToD: DSPy + LangGraph
Proyecto	Soni - Framework Open Source para Asistentes Conversacionales
Fecha	28 de Noviembre de 2025
Estado	Propuesto
Autor	Jorge - AI Solutions Architect
1. Contexto y Problema
1.1 Estado del Ecosistema Open Source
El panorama actual de frameworks de diálogo orientado a tareas (ToD) de código abierto presenta una brecha crítica que Soni pretende cubrir:
•	Rasa: Arquitectura percibida como desatendida, sin actualizaciones significativas hacia paradigmas LLM-first.
•	Botpress: Transición a modelo propietario, abandonando el código abierto.
•	Chatterbot y similares: Arquitecturas obsoletas basadas en pattern matching.
•	Parlant: Enfoque moderno pero con problemas de rendimiento y latencia reportados.
1.2 Problemas de los Enfoques Actuales
Riesgo de LLM Puro (End-to-End):
•	Volatilidad en el Dialogue State Tracking (DST)
•	Falta de trazabilidad en decisiones de política
•	Comportamiento no determinista en lógica de negocio crítica
•	Dificultad para auditar y depurar flujos de conversación
Fragilidad de Prompt Engineering Manual:
•	Prompts frágiles que se rompen con cambios menores
•	Dificultad para mantener y versionar la lógica de NLU
•	No escala ante cambios en requisitos del dominio
•	Dependencia de "magia negra" en el diseño de prompts
1.3 Problema a Resolver
¿Cómo construir un framework ToD que combine la flexibilidad semántica del LLM con el control determinista requerido por el negocio, utilizando herramientas modernas de código abierto y permitiendo la definición declarativa mediante archivos YAML?
2. Decisión de Arquitectura
Se adopta una Arquitectura Híbrida Desacoplada que sigue el principio de Separación de Responsabilidades entre Interpretación Semántica y Ejecución Determinista.
2.1 Componentes Centrales
Capa	Herramienta	Función	Rol ToD Clásico
Configuración	YAML (DSL)	Definición declarativa de Slots, Acciones y Flujos	Domain-Specific Language
Interpretación	DSPy	Traducir entrada a Comando Estructurado optimizado	NLU / Dialogue Understanding
Control	LangGraph	Ejecución determinista, DST persistente, Política	Dialogue Manager / DST
2.2 Diagrama de Arquitectura
┌─────────────────────────────────────────────────────────────┐
│                         YAML Config                         │
│  (flows, slots, actions, responses, entities)               │
└─────────────────────┬───────────────────────────────────────┘
                      │ parse & build
                      ▼
┌─────────────────────────────────────────────────────────────┐
│                    Graph Builder                            │
│  Traduce YAML → StateGraph de LangGraph dinámicamente       │
└─────────────────────┬───────────────────────────────────────┘
                      │
                      ▼
┌─────────────────────────────────────────────────────────────┐
│                     Runtime Loop                            │
│  ┌─────────┐    ┌──────────┐    ┌──────────┐   ┌─────────┐ │
│  │ Entrada │───▶│   DSPy   │───▶│ LangGraph│──▶│Respuesta│ │
│  │ Usuario │    │   (DU)   │    │   (DM)   │   │  (NLG)  │ │
│  └─────────┘    └──────────┘    └──────────┘   └─────────┘ │
│                      │               │                      │
│                      │    ┌──────────┴──────────┐           │
│                      │    │   Dialogue State    │           │
│                      └───▶│  (slots, history,   │           │
│                           │   current_node)     │           │
│                           └─────────────────────┘           │
└─────────────────────────────────────────────────────────────┘
2.3 Flujo de Control Detallado
1.	Carga del Grafo: Al iniciar, el Graph Builder consume los archivos YAML y construye el StateGraph de LangGraph dinámicamente.
2.	Entrada del Usuario: El usuario introduce un mensaje de lenguaje natural.
3.	Interpretación por DSPy: El módulo DU utiliza el LLM optimizado para predecir el Comando Estructurado, recibiendo el estado actual y las acciones válidas como contexto.
4.	Ejecución por LangGraph: El grafo recibe el comando y ejecuta transiciones deterministas mediante aristas condicionales.
5.	Actualización de Estado: El DST se actualiza con checkpointer persistente (SQLite, PostgreSQL, Redis).
6.	Generación de Respuesta: Se genera la respuesta al usuario (template o LLM).
3. Especificación del Schema YAML
El schema YAML sigue un enfoque híbrido: declarativo por defecto con override explícito. Esto permite que el 80% de los flujos ToD estándar se definan de forma simple, mientras casos complejos tienen control total sobre el grafo.
3.1 Nivel 1: Configuración Global
version: "1.0"

settings:
  llm:
    provider: openai          # openai, anthropic, local
    model: gpt-4o-mini
    temperature: 0.1
  dspy:
    optimizer: MIPROv2        # MIPROv2, BootstrapFewShot, COPRO
    metric: intent_accuracy
    num_candidates: 10
  persistence:
    backend: sqlite           # sqlite, postgresql, redis
    path: ./dialogue_state.db
  logging:
    level: INFO
    trace_graphs: true

entities:
  - name: city
    type: string
    examples: [Madrid, Barcelona, NYC, London, París]
  - name: date
    type: datetime
    format: "%Y-%m-%d"
  - name: cabin_class
    type: enum
    values: [economy, business, first]
  - name: booking_ref
    type: string
    validation: "^[A-Z]{6}$"
3.2 Nivel 2: Flujos Declarativos
Para flujos simples de slot-filling, el framework infiere automáticamente el grafo de estados. El desarrollador solo define slots, triggers y acciones:
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
Grafo Inferido Automáticamente
Para flujos declarativos, el Graph Builder genera este patrón estándar:
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
3.3 Nivel 3: Grafos Explícitos
Para flujos con lógica no lineal, se puede definir el grafo explícitamente:
  modify_booking:
    description: "Modificar reserva existente"
    triggers:
      - "cambiar mi vuelo"
      - "modificar reserva"
    
    # Control total: definición explícita del grafo
    graph:
      entry: get_booking
      
      nodes:
        get_booking:
          type: slot_fill
          slots: [booking_ref]
          next: check_modifiable
        
        check_modifiable:
          type: action
          action: check_booking_rules
          transitions:
            modifiable: choose_modification
            not_modifiable: explain_policy
            not_found: booking_not_found
        
        choose_modification:
          type: choice
          prompt: "¿Qué quieres modificar?"
          options:
            - label: "Fecha del vuelo"
              next: change_date
            - label: "Datos de pasajeros"
              next: change_passengers
            - label: "Cancelar reserva"
              next: cancel_flow
        
        change_date:
          type: slot_fill
          slots: [new_date]
          next: calculate_fee
        
        calculate_fee:
          type: action
          action: get_change_fee
          transitions:
            free: confirm_change
            paid: show_fee_and_confirm
        
        show_fee_and_confirm:
          type: confirm
          template: "El cambio tiene un coste de {fee}€. ¿Procedo?"
          yes: execute_change
          no: end
        
        confirm_change:
          type: confirm
          template: "¿Confirmas el cambio de fecha a {new_date}?"
          yes: execute_change
          no: end
        
        execute_change:
          type: action
          action: modify_booking_api
          next: success_response
        
        explain_policy:
          type: response
          template: "Esta reserva no se puede modificar: {reason}"
          next: end
        
        booking_not_found:
          type: response
          template: "No encontré ninguna reserva con código {booking_ref}"
          next: end
        
        success_response:
          type: response
          template: "Reserva modificada correctamente. Nueva fecha: {new_date}"
          next: end
3.4 Definición de Acciones
actions:
  # Acción HTTP
  search_flights:
    type: http
    method: POST
    url: "https://api.flights.com/search"
    headers:
      Authorization: "Bearer ${env.FLIGHTS_API_KEY}"
    body:
      from: "{origin}"
      to: "{destination}"
      date: "{date}"
    response_mapping:
      count: "$.results.length"
      cheapest: "$.results[0].price"
  
  # Acción Python personalizada
  check_booking_rules:
    type: python
    module: soni_actions.bookings
    function: check_modification_rules
    # Retorna: {status: 'modifiable'|'not_modifiable', reason: str}
  
  # Acción con tool de LangChain
  get_weather:
    type: langchain_tool
    tool: OpenWeatherMapQueryRun
    config:
      api_key: "${env.OPENWEATHER_KEY}"
3.5 Comportamiento Global
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
4. Implementación Técnica
4.1 Integración DSPy para Dialogue Understanding
import dspy
from typing import Literal

class DialogueUnderstanding(dspy.Signature):
    """Interpreta la intención del usuario en contexto del diálogo."""
    
    user_message: str = dspy.InputField(
        desc="Último mensaje del usuario"
    )
    dialogue_history: list[dict] = dspy.InputField(
        desc="Historial de mensajes previos"
    )
    current_slots: dict = dspy.InputField(
        desc="Slots actuales con sus valores"
    )
    available_actions: list[str] = dspy.InputField(
        desc="Acciones válidas desde el YAML"
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


class SoniDU(dspy.Module):
    def __init__(self, yaml_config: dict):
        self.config = yaml_config
        self.predictor = dspy.ChainOfThought(DialogueUnderstanding)
    
    def forward(self, state: dict) -> dict:
        # Construir lista de acciones válidas desde YAML
        valid_actions = self._get_valid_actions(state)
        
        result = self.predictor(
            user_message=state['messages'][-1]['content'],
            dialogue_history=state['messages'][:-1],
            current_slots=state['slots'],
            available_actions=valid_actions,
            current_flow=state.get('current_flow', 'none')
        )
        
        return {
            'command': result.structured_command,
            'slots': result.extracted_slots,
            'confidence': result.confidence
        }
4.2 Graph Builder: YAML a LangGraph
from langgraph.graph import StateGraph, END
from langgraph.checkpoint.sqlite import SqliteSaver
from typing import TypedDict, Annotated
import operator

class DialogueState(TypedDict):
    messages: Annotated[list, operator.add]
    current_flow: str
    slots: dict
    pending_action: str | None
    last_response: str
    turn_count: int


class SoniGraphBuilder:
    def __init__(self, config_path: str):
        self.config = yaml.safe_load(open(config_path))
        self.graph = StateGraph(DialogueState)
        self.du_module = SoniDU(self.config)
    
    def build(self) -> CompiledGraph:
        # Nodos base siempre presentes
        self.graph.add_node("understand", self._create_du_node())
        self.graph.add_node("route", self._create_router_node())
        self.graph.add_node("fallback", self._create_fallback_node())
        
        # Construir nodos dinámicos desde YAML
        for flow_name, flow_cfg in self.config['flows'].items():
            if 'graph' in flow_cfg:
                # Nivel 3: Grafo explícito
                self._build_explicit_graph(flow_name, flow_cfg)
            else:
                # Nivel 2: Inferir grafo estándar
                self._build_inferred_graph(flow_name, flow_cfg)
        
        self.graph.set_entry_point("understand")
        
        # Configurar persistencia
        checkpointer = self._get_checkpointer()
        return self.graph.compile(checkpointer=checkpointer)
    
    def _build_inferred_graph(self, flow_name: str, cfg: dict):
        """Genera grafo estándar de slot-filling."""
        
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
4.3 Estructura del Proyecto
soni/
├── pyproject.toml
├── soni/
│   ├── __init__.py
│   ├── core/
│   │   ├── builder.py        # SoniGraphBuilder
│   │   ├── state.py          # DialogueState
│   │   └── config.py         # Carga y validación YAML
│   ├── du/
│   │   ├── signatures.py     # DSPy Signatures
│   │   ├── modules.py        # SoniDU, SlotExtractor
│   │   └── optimizers.py     # Configuración MIPROv2
│   ├── dm/
│   │   ├── nodes.py          # Nodos del grafo
│   │   ├── edges.py          # Lógica de transiciones
│   │   └── checkpointers.py  # Adaptadores persistencia
│   ├── actions/
│   │   ├── http.py           # Acciones HTTP
│   │   ├── python.py         # Acciones Python
│   │   └── registry.py       # Action Registry
│   ├── nlg/
│   │   ├── templates.py      # Respuestas template
│   │   └── generative.py     # Respuestas LLM
│   └── server/
│       ├── api.py            # FastAPI endpoints
│       └── websocket.py      # WebSocket support
├── tests/
├── examples/
│   ├── flight_booking/
│   │   ├── soni.yaml
│   │   └── actions.py
│   └── customer_service/
└── docs/
5. Justificación Técnica
5.1 Por qué DSPy para Dialogue Understanding
•	Optimización automática: MIPROv2 encuentra el prompt óptimo sin ingeniería manual.
•	Modularidad: Las Signatures son componibles y testeables de forma aislada.
•	Portabilidad: Cambiar de GPT-4 a Claude o Llama requiere solo reoptimizar, no reescribir.
•	Métricas integradas: El optimizer usa métricas de negocio (intent_accuracy, slot_f1).
•	Constrained generation: available_actions limita el espacio de salida, reduciendo alucinaciones.
5.2 Por qué LangGraph para Dialogue Management
•	Determinismo: Las transiciones son funciones Python puras, no generación LLM.
•	Trazabilidad: El grafo es visualizable y auditable (langgraph studio).
•	Persistencia nativa: Checkpointers para SQLite, PostgreSQL, Redis out-of-the-box.
•	Recuperación de errores: Los nodos pueden tener fallbacks y retries configurables.
•	Ecosistema: Integración directa con LangChain Tools para acciones.
5.3 Por qué YAML como DSL
•	Legibilidad: Un product manager puede entender y modificar flujos sin código.
•	Versionable: Git diff muestra cambios claros en la lógica de negocio.
•	Validación: JSON Schema permite validar configuraciones antes de runtime.
•	Separación de concerns: La lógica de negocio está separada del framework.
•	Híbrido: El 80% de casos usa inferencia automática, el 20% tiene control total.
6. Consecuencias
6.1 Positivas
Aspecto	Beneficio
Robustez	Separación DU/DM mitiga fallos en cascada. DST persistente sobrevive a reinicios.
Escalabilidad	DSPy permite optimización automática sin reentrenar modelos manualmente.
Trazabilidad	El grafo ES la política. Debugging y RCOF simplificados.
Mantenibilidad	YAML como fuente de verdad. Cambios de negocio sin tocar código Python.
Time-to-Market	Flujos declarativos permiten prototipar asistentes en horas, no semanas.
6.2 Negativas y Mitigaciones
Riesgo	Impacto	Mitigación
Complejidad de integración	Esfuerzo inicial para crear el Graph Builder	Inversión única. Templates y ejemplos reducen curva.
Dependencia de librerías	Acoplamiento a DSPy y LangGraph	Abstracciones internas permiten swap. Ambas son activamente mantenidas.
Curva de aprendizaje	Desarrolladores deben aprender dos paradigmas	Documentación exhaustiva + ejemplos progresivos.
Latencia	Doble llamada: DSPy + LangGraph	Caching agresivo. DSPy con modelos pequeños optimizados.
7. Alternativas Consideradas
7.1 LLM End-to-End Puro
Rechazado porque:
•	No garantiza determinismo en lógica de negocio crítica
•	DST volátil y difícil de auditar
•	Costes de inferencia más altos por turno
•	Dificultad para implementar políticas de empresa estrictas
7.2 Rasa con Componentes LLM
Rechazado porque:
•	Arquitectura legacy no diseñada para LLMs
•	Mantenimiento incierto del proyecto
•	Configuración compleja (múltiples archivos YAML, entrenamiento NLU)
7.3 Solo DSPy sin LangGraph
Rechazado porque:
•	DSPy no tiene primitivas de máquina de estados
•	Gestión de estado manual propensa a errores
•	Sin persistencia built-in
8. Roadmap de Implementación
Fase	Entregable	Descripción
1	Core: YAML Parser + State	Parsing YAML, validación JSON Schema, DialogueState base
2	DSPy Integration	DialogueUnderstanding Signature, SlotExtractor, optimización MIPROv2
3	Graph Builder (Nivel 2)	Inferencia automática de grafos desde flujos declarativos
4	Graph Builder (Nivel 3)	Soporte para definición explícita de grafos
5	Action Registry	Sistema de plugins: HTTP, Python, LangChain Tools
6	Persistencia + Server	Checkpointers, FastAPI, WebSocket
7	Documentación + Ejemplos	Docs site, ejemplos progresivos, video tutorials
9. Referencias
7.	DSPy Documentation: https://dspy-docs.vercel.app
8.	LangGraph Documentation: https://langchain-ai.github.io/langgraph/
9.	Task-Oriented Dialogue Systems Survey (2023)
10.	MIPROv2: Optimizing Prompts via Multi-stage Instruction Proposal
11.	Hybrid ToD Systems: Combining Neural and Symbolic Approaches
Apéndice A: Schema YAML Completo de Ejemplo
A continuación se presenta un archivo YAML completo funcional para un asistente de reservas de vuelos:
# soni.yaml - Flight Booking Assistant
version: "1.0"

settings:
  llm:
    provider: openai
    model: gpt-4o-mini
    temperature: 0.1
  dspy:
    optimizer: MIPROv2
    metric: intent_accuracy
  persistence:
    backend: sqlite
    path: ./data/dialogue.db

entities:
  - name: city
    type: string
    examples: [Madrid, Barcelona, NYC, London, París, Roma]
  - name: date
    type: datetime
    format: "%Y-%m-%d"
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

— Fin del Documento —
