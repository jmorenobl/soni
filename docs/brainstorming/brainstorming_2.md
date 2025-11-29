
Cómo ves una implementación moderna de un sistema tod de asistentes conversacionales basada en DSPy y langgraph?

Absolutamente. La propuesta de utilizar la dualidad DSPy y LangGraph para crear un framework de código abierto state-of-the-art es una Decisión de Arquitectura fundamental.
A continuación, presento el Registro de Decisión de Arquitectura (ADR) formalizando esta propuesta, incluyendo el requisito de la definición del asistente mediante archivos YAML.
Registro de Decisión de Arquitectura (ADR 001)
Título: Arquitectura Híbrida para Chatbots ToD Abiertos: DSPy para DU y LangGraph para Política Determinista
Fecha: 28 de Noviembre de 2025
1. Contexto y Problema
El panorama actual de frameworks de diálogo orientado a tareas (ToD) de código abierto presenta una brecha crítica:
 * Volatilidad del Ecosistema: Los referentes anteriores han abandonado el código abierto o sus arquitecturas son percibidas como desatendidas. Existe una clara necesidad de un sustituto moderno y robusto en la comunidad de código abierto.
 * Riesgo de LLM Puro: Los sistemas ToD que dependen de un LLM puro (End-to-End) para la gestión de la política de diálogo exhiben problemas de volatilidad y falta de trazabilidad en el Dialogue State Tracking (DST), lo cual es inaceptable para la lógica de negocio crítica.[1, 2, 3]
 * Fragilidad de Prompts: La implementación de la capa de Dialogue Understanding (DU) mediante prompt engineering manual es frágil, difícil de mantener y no escala ante cambios en los requisitos del dominio.
El problema es cómo construir un framework ToD que combine la flexibilidad del LLM con el control determinista requerido por el negocio, utilizando herramientas modernas de código abierto y permitiendo la definición del flujo de diálogo mediante archivos declarativos (YAML).
2. Decisión de Arquitectura
Se elegirá una Arquitectura Híbrida Desacoplada que sigue el principio de Separación de Responsabilidades (Interpretación vs. Ejecución).
2.1. Componentes Centrales
El framework se construirá sobre tres capas principales:
| Capa | Herramienta | Función | Rol Clásico de ToD |
|---|---|---|---|
| Configuración | YAML (DSL) | Definición declarativa de Slots, Acciones y Flujos (Flows). | Domain-Specific Language (DSL) |
| Interpretación (DU) | DSPy | Optimizar el LLM para traducir la entrada del usuario y el historial en un Comando Estructurado preciso (e.g., book_flight(origin='NY')). | Natural Language Understanding (NLU) |
| Control & Política (DM) | LangGraph [2, 3] | Ejecución determinista del comando, Dialogue State Tracking (DST) persistente y gestión de transiciones de flujo (Política). | Dialogue Manager (DM) & DST |
2.2. Flujo de Control
 * Carga del Grafo: Al iniciar, el framework consume los archivos YAML que definen los Flujos de Diálogo. Esta definición se utiliza para construir y cargar el StateGraph de LangGraph [3] dinámicamente, inicializando la política determinista.
 * Entrada del Usuario: El usuario introduce un mensaje de lenguaje natural.
 * Interpretación por DSPy (Predicción del Comando):
   * DSPy utiliza el LLM (optimizado) para leer la última entrada y el Estado Persistente de LangGraph (DST).
   * El LLM predice el Comando Estructurado (o la Acción) más probable que se debe ejecutar, seleccionándolo de un conjunto predefinido en el YAML.[4]
 * Ejecución por LangGraph (Política Determinista):
   * LangGraph recibe el Comando Estructurado.
   * Utiliza una Arista Condicional para decidir el siguiente nodo a ejecutar en el StateGraph. La decisión no es generativa, sino lógica (p. ej., "¿Están todos los slots llenos?").
   * El nodo de destino actualiza el Estado Persistente (DST) o llama a una Acción Externa (LangChain Tool/API).
 * Generación de Respuesta: Se genera la respuesta al usuario.
3. Justificación Técnica
 * Aprovechamiento de DSPy: DSPy reemplaza la ingeniería de prompts frágil por un enfoque declarativo de automejora. Esto garantiza una capa de NLU/DU altamente eficiente, modular y fácil de mantener, que puede adaptarse al modelo de lenguaje (LLM) subyacente sin reescribir la lógica de prompt.
 * Determinismo con LangGraph: LangGraph impone una estructura de máquina de estados finitos (el Grafo) sobre el flujo de diálogo, lo cual es esencial para el ToD.[3] Esto garantiza que la lógica de negocio crítica sea auditable, predecible y no dependa de la estocasticidad del LLM.[4]
 * Configuración Declarativa (YAML): El uso de YAML para la definición de los Flujos de Diálogo (la política) y los slots cumple el requisito de ser un DSL (Domain-Specific Language), separando la lógica de negocio de la implementación del framework. Esto mejora la transparencia y permite a los desarrolladores de negocio configurar el asistente sin tocar el código fuente.[4]
4. Consecuencias
| Positivas | Negativas |
|---|---|
| Robustez: La separación entre interpretación (DSPy) y ejecución (LangGraph) mitiga el riesgo de fallos en cascada y garantiza el DST persistente.[1, 3] | Complejidad de Integración: Requiere un esfuerzo de desarrollo inicial para crear la capa que traduzca las definiciones YAML en un StateGraph de LangGraph operativo. |
| Escalabilidad: DSPy permite la optimización automática del LLM/Prompt, escalando la precisión del DU sin requerir entrenamiento manual intensivo de ejemplos de diálogo. | Dependencia de Múltiples Librerías: La arquitectura está fuertemente acoplada a la evolución de DSPy y LangGraph/LangChain. |
| Trazabilidad: LangGraph facilita el seguimiento del estado y la lógica de ejecución (el grafo es la política), simplificando el debugging y la atribución de la causa raíz de fallos (RCOF).[5] | Curva de Aprendizaje: Los desarrolladores deberán dominar los paradigmas de DSPy (programación declarativa de LLM) y LangGraph (máquinas de estado/grafos). |

Mostrar más

Evaluó arquitectura híbrida DSPy-LangGraph con análisis técnico profundo.
20s








Me parece una arquitectura muy sólida, Jorge. La separación DU/DM que propones es el enfoque clásico de ToD pero modernizado con las herramientas correctas. Tengo algunas observaciones técnicas que podrían fortalecer el diseño:

Sobre el flujo DSPy → LangGraph

La parte más crítica es cómo defines la Signature de DSPy para el DU. Necesitas que el contexto incluya no solo el último mensaje sino el estado actual del grafo (slots llenados, nodo actual). Algo como:

python
class DialogueUnderstanding(dspy.Signature):
    """Interpreta la intención del usuario dado el contexto del diálogo."""
    user_message: str = dspy.InputField()
    dialogue_state: dict = dspy.InputField(desc="Slots actuales y flujo activo")
    available_actions: list[str] = dspy.InputField(desc="Acciones válidas desde YAML")
    
    structured_command: str = dspy.OutputField(desc="Acción estructurada: action_name(slot=value)")
La clave está en pasar available_actions como input constrained desde el YAML. Esto reduce la alucinación del LLM porque le das un espacio cerrado de opciones.

El slot filling iterativo

Un gap que veo en el ADR es quién orquesta el slot filling cuando faltan valores. ¿DSPy extrae parcialmente y LangGraph itera preguntando por slots faltantes? Yo lo estructuraría así: LangGraph mantiene un nodo slot_elicitation que, cuando detecta slots vacíos requeridos, genera la pregunta (puede ser template o LLM) y vuelve a invocar a DSPy con la respuesta.

Sobre la construcción dinámica del grafo desde YAML

Esto es donde se pone interesante. El schema YAML necesita mapear a primitivas de LangGraph. Por ejemplo:

yaml
flows:
  book_flight:
    slots:
      - name: origin
        type: city
        required: true
        elicitation: "¿Desde qué ciudad quieres volar?"
      - name: destination
        type: city
        required: true
    transitions:
      all_slots_filled: confirm_booking
      cancel_intent: end_flow
    actions:
      confirm_booking:
        type: api_call
        endpoint: /bookings
Luego un builder que traduce esto a StateGraph.add_conditional_edges() dinámicamente.

Una preocupación arquitectónica

El ADR asume que DSPy predice una acción por turno. Pero en ToD real tienes casos como "Reserva un vuelo a Madrid y también un hotel" (multi-intent). ¿El grafo soporta ejecución paralela de subflows o es estrictamente secuencial?

¿Esto es evolución de Soni o un proyecto nuevo? Porque la arquitectura que describes tiene bastante overlap con lo que ya estabas construyendo con DSPy + YAML.

Sería una evolución de Soni. Estoy pensando cómo hacerlo y me dieron la idea de usar langgraph que no la he usado antes. Parece que tiene sentido. Me gustaría rellenar el gap que hay en el ámbito del OpenSource de frameworks de asistentes conversacionales porque rasa está desatendia, botpress no es OpenSource ya. El resto como chatterbot han quedado desfasados. Existe parlant, pero por lo que he visto es bastante lenta. Por lo que Soni vendría a cubrir el gap con las técnicas y tecnologías modernas como DSPy y langgraph pero me gustaría entender mejor como sería.


Validó mercado, estructuró arquitectura con DSPy y LangGraph.




Tiene mucho sentido la oportunidad. El hueco está ahí y tienes el conocimiento de DSPy para llenarlo. Déjame explicarte cómo encajaría LangGraph en Soni y qué cambiaría respecto a lo que ya tienes.

Qué es LangGraph en esencia

LangGraph es una máquina de estados con persistencia. La idea central es simple: defines nodos (funciones), aristas (transiciones), y un estado compartido que se pasa entre nodos. Lo que lo hace potente para ToD es que las transiciones pueden ser condicionales y el estado persiste entre turnos de conversación.

python
from langgraph.graph import StateGraph, END
from typing import TypedDict

class DialogueState(TypedDict):
    messages: list[str]
    current_flow: str
    slots: dict
    pending_action: str | None

graph = StateGraph(DialogueState)

# Nodos
graph.add_node("understand", understand_user)  # Aquí entra DSPy
graph.add_node("check_slots", check_required_slots)
graph.add_node("elicit_slot", ask_for_missing_slot)
graph.add_node("execute_action", run_action)
graph.add_node("respond", generate_response)

# Transiciones condicionales
graph.add_conditional_edges(
    "check_slots",
    lambda state: "complete" if all_slots_filled(state) else "missing",
    {"complete": "execute_action", "missing": "elicit_slot"}
)
```

**Cómo cambia la arquitectura de Soni**

Actualmente en Soni tienes DSPy haciendo el trabajo pesado con el YAML definiendo la configuración. Con LangGraph, la responsabilidad se redistribuye así:

| Componente | Soni actual | Soni + LangGraph |
|------------|-------------|------------------|
| Orquestación | DSPy controla el flujo | LangGraph controla el flujo |
| NLU/DU | DSPy | DSPy (sin cambios) |
| Estado del diálogo | Gestionado manualmente | `StateGraph` con checkpointer |
| Política | Implícita en el prompt | Explícita en el grafo |
| Persistencia | Custom | Built-in (SQLite, PostgreSQL, Redis) |

**La arquitectura concreta**
```
┌─────────────────────────────────────────────────────────────┐
│                         YAML Config                          │
│  (flows, slots, actions, responses)                          │
└─────────────────────┬───────────────────────────────────────┘
                      │ parse & build
                      ▼
┌─────────────────────────────────────────────────────────────┐
│                    Graph Builder                             │
│  Traduce YAML → StateGraph de LangGraph                      │
└─────────────────────┬───────────────────────────────────────┘
                      │
                      ▼
┌─────────────────────────────────────────────────────────────┐
│                     Runtime Loop                             │
│  ┌─────────┐    ┌──────────┐    ┌─────────┐    ┌─────────┐  │
│  │ Entrada │───▶│   DSPy   │───▶│ LangGraph│───▶│Respuesta│  │
│  │ Usuario │    │   (DU)   │    │   (DM)   │    │  (NLG)  │  │
│  └─────────┘    └──────────┘    └─────────┘    └─────────┘  │
│                      │               │                       │
│                      │    ┌──────────┴──────────┐            │
│                      │    │   Dialogue State    │            │
│                      └───▶│  (slots, history,   │            │
│                           │   current_node)     │            │
│                           └─────────────────────┘            │
└─────────────────────────────────────────────────────────────┘
El Graph Builder es la pieza clave nueva

Este componente lee el YAML y construye el grafo dinámicamente:

python
class SoniGraphBuilder:
    def __init__(self, config_path: str):
        self.config = yaml.safe_load(open(config_path))
        self.graph = StateGraph(DialogueState)
        
    def build(self) -> CompiledGraph:
        # Nodos base siempre presentes
        self.graph.add_node("understand", self._create_du_node())
        self.graph.add_node("route", self._create_router_node())
        
        # Nodos dinámicos desde YAML
        for flow_name, flow_config in self.config["flows"].items():
            self._add_flow_nodes(flow_name, flow_config)
            
        self.graph.set_entry_point("understand")
        return self.graph.compile(checkpointer=MemorySaver())
    
    def _create_du_node(self):
        """Nodo que usa DSPy para interpretar"""
        du_module = dspy.ChainOfThought(DialogueUnderstanding)
        
        def understand(state: DialogueState) -> DialogueState:
            result = du_module(
                user_message=state["messages"][-1],
                dialogue_state=state["slots"],
                available_actions=self._get_valid_actions(state)
            )
            state["pending_action"] = result.structured_command
            return state
        
        return understand
Lo que ganas con este enfoque

Trazabilidad total: Puedes visualizar el grafo, ver exactamente qué nodo ejecutó qué y por qué transitó donde lo hizo.
Persistencia gratis: LangGraph tiene checkpointers para SQLite, PostgreSQL, Redis. El estado del diálogo sobrevive a reinicios sin código extra.
Recuperación de errores: Si DSPy falla o el LLM alucina una acción inválida, el grafo puede tener un nodo de fallback que pide clarificación.
Multi-turn nativo: El patrón de slot-filling iterativo es simplemente un ciclo en el grafo.
Lo que necesitas implementar

Graph Builder: El traductor YAML → StateGraph
DSPy Signatures: Para DU, slot extraction, y posiblemente NLG
Action Registry: Sistema de plugins para las acciones (API calls, etc.)
Checkpointer integration: Para elegir backend de persistencia
Una pregunta de diseño importante

¿Quieres que el YAML defina el grafo completo explícitamente (nodos y transiciones) o prefieres un enfoque más declarativo donde defines slots/acciones y el framework infiere el grafo? Lo primero da más control, lo segundo es más simple para el usuario pero menos flexible.

¿Quieres que profundicemos en alguna de estas piezas? Puedo ayudarte a diseñar el schema YAML o la integración DSPy-LangGraph con más detalle.

Que recomiendas para el yaml?


Evaluó enfoques YAML híbridos y preparó ejemplos comparativos.






Recomiendo un enfoque híbrido: declarativo por defecto con override explícito. La razón es pragmática: el 80% de los flujos ToD son slot-filling estándar donde el grafo se puede inferir, pero necesitas escape hatches para casos complejos.

El schema que propongo tiene tres niveles

yaml
# soni.yaml
version: "1.0"

# ============================================
# NIVEL 1: Definiciones globales
# ============================================
settings:
  llm:
    provider: openai
    model: gpt-4o-mini
  dspy:
    optimizer: MIPROv2
    metric: intent_accuracy
  persistence:
    backend: sqlite
    path: ./dialogue_state.db

entities:
  - name: city
    type: string
    examples: [Madrid, Barcelona, NYC, London]
  - name: date
    type: datetime
    format: "%Y-%m-%d"
  - name: cabin_class
    type: enum
    values: [economy, business, first]

# ============================================
# NIVEL 2: Flujos declarativos (el framework infiere el grafo)
# ============================================
flows:
  book_flight:
    description: "Reserva de vuelos"
    triggers:
      - "quiero reservar un vuelo"
      - "necesito volar a {destination}"
      - "billete de avión"
    
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
    
    # Acción al completar slots
    on_complete:
      action: search_flights
      confirm: true  # Pide confirmación antes de ejecutar
      confirmation_template: |
        Voy a buscar vuelos de {origin} a {destination} 
        para el {date} en clase {cabin}. ¿Confirmas?
    
    # Respuestas según resultado
    responses:
      success: "He encontrado {count} vuelos. El más barato es {cheapest}."
      no_results: "No hay vuelos disponibles para esa fecha."
      error: "Ha ocurrido un error al buscar vuelos."

  check_booking:
    description: "Consultar estado de reserva"
    triggers:
      - "estado de mi reserva"
      - "mi vuelo"
    slots:
      booking_ref:
        type: string
        required: true
        prompt: "¿Cuál es tu código de reserva?"
        validation: "^[A-Z]{6}$"
    on_complete:
      action: get_booking_status

# ============================================
# NIVEL 3: Override explícito del grafo (casos complejos)
# ============================================
  modify_booking:
    description: "Modificar reserva existente"
    triggers:
      - "cambiar mi vuelo"
      - "modificar reserva"
    
    # Cuando necesitas control total, defines el grafo
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
            - label: "Fecha"
              next: change_date
            - label: "Pasajeros"
              next: change_passengers
            - label: "Cancelar"
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
        
        execute_change:
          type: action
          action: modify_booking_api
          next: end
        
        explain_policy:
          type: response
          template: "Esta reserva no se puede modificar porque {reason}."
          next: end

# ============================================
# Acciones (plugins)
# ============================================
actions:
  search_flights:
    type: http
    method: POST
    url: "https://api.flights.com/search"
    body:
      from: "{origin}"
      to: "{destination}"
      date: "{date}"
    
  get_booking_status:
    type: http
    method: GET
    url: "https://api.flights.com/bookings/{booking_ref}"
  
  check_booking_rules:
    type: python
    module: soni_actions.bookings
    function: check_modification_rules

# ============================================
# Comportamiento global
# ============================================
fallback:
  no_intent:
    response: "No he entendido. ¿Puedes reformularlo?"
    max_retries: 2
    then: handoff_human
  
  out_of_scope:
    response: "Solo puedo ayudarte con reservas de vuelos."

interruptions:
  allow_during_flow: true
  intents:
    - cancel  # "cancelar", "déjalo"
    - help    # "ayuda", "no entiendo"
    - restart # "empezar de nuevo"
```

**Por qué este diseño**

1. **Flujos simples son simples**: `book_flight` solo define slots y el framework genera automáticamente el ciclo de slot-filling, las transiciones, y el nodo de confirmación.

2. **Flujos complejos son posibles**: `modify_booking` usa `graph:` para definir explícitamente nodos y transiciones cuando la lógica no es lineal.

3. **Separación clara**: Las `actions` están fuera de los flujos. Esto permite reutilizarlas y testearlas independientemente.

4. **El YAML es el contrato**: Un desarrollador de negocio puede leer este archivo y entender qué hace el bot sin mirar código Python.

**Cómo el Graph Builder interpreta esto**

Para flujos declarativos, el builder genera un grafo estándar:
```
[understand] → [route_to_flow] → [slot_loop] ←──┐
                                      │         │
                                      ▼         │
                              [check_slots]─────┘
                                      │ (complete)
                                      ▼
                              [confirm] → [execute_action] → [respond]
Para flujos con graph: explícito, construye exactamente lo que defines.

Un detalle importante sobre los triggers

Los triggers no son keywords exactos sino ejemplos para DSPy. El optimizer los usa para aprender a clasificar intents. Cuantos más ejemplos variados, mejor generaliza:

yaml
triggers:
  - "quiero reservar un vuelo"
  - "necesito volar a {destination}"  # Con slot inline
  - "busca vuelos"
  - "hay aviones a {destination} el {date}?"
¿Te parece un buen punto de partida? Podemos iterar sobre el schema, especialmente la parte de graph: explícito que es donde hay más decisiones de diseño.

Me gustaría que crearas un ADR completo con todo lo que has visto.


Orchestrated comprehensive ADR documentation spanning architecture decisions and trade-offs.


Voy a crear un ADR completo como documento Word. Primero déjame revisar el skill de documentos.


2 pasos

Leer la documentación completa de docx-js para crear documentos Word

Orchestrated comprehensive ADR document with technical justification and diagrams.


Ahora creo el ADR completo como documento Word:


2 pasos

Generar el documento Word con el ADR completo



Generó documento y preparó enlace para compartir.

Ver tu ADR completo

El documento incluye:

Contexto y Problema: Análisis del gap en el ecosistema open source y problemas de enfoques actuales
Decisión de Arquitectura: Componentes centrales (DSPy + LangGraph + YAML), diagrama de arquitectura y flujo de control detallado
Especificación YAML completa con los tres niveles:
Nivel 1: Configuración global (LLM, DSPy optimizer, persistencia, entities)
Nivel 2: Flujos declarativos con inferencia automática del grafo
Nivel 3: Override explícito para grafos complejos
Implementación técnica: Código de la Signature DSPy para DU, Graph Builder, y estructura del proyecto
Justificación técnica de cada componente
Consecuencias positivas y negativas con mitigaciones
Alternativas consideradas y por qué se rechazaron
Roadmap de implementación en 7 fases
Apéndice con un YAML completo funcional
¿Quieres que profundicemos en alguna sección específica o empezamos a prototipar algún componente?

Adr 001 soni dspy langgraph
Documento · DOCX 


¿Cómo puedo ayudarle hoy?






Artefactos
Adr 001 soni dspy langgraph
Documento · DOCX 
