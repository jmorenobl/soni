Gemini
Mis cosas
Chatbots Orientados a Tareas: Técnicas y Paradigmas
Imagen de
Imagen de

Adobe Pro: Funciones y Automatización con Python
Arquitectura Híbrida para Chatbots ToD
Chatbots Orientados a Tareas: Técnicas Clásicas y Nuevas
Chatbots Orientados a Tareas: Técnicas Clásicas y Nuevas
Delorean aparece en centro comercial
T-800 Fotorrealista con Escopeta
Selfie Cinematográfica de los 80 Estilo Stranger Things
Prompt para Foto de Terminator
Diseño de Máquina Virtual Semántica
Implementación MCP para Análisis de Excel
Edición de Foto Oscura con Foco
Blender HDRI para Detección de Drones
Docker vs. VPS: ¿Cuál elegir?
Conversación con Gemini
Cómo sería una implementación de este ADR:



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

---



No hace falta que entres en todos los detalles. Con una visión global y un poco de código me vale. Busca en internet si hace falta para obtener información actualizada.

Esta es una arquitectura excelente. Soluciona el problema de la "caja negra" de los agentes puramente LLM (como los Assistants API de OpenAI) y devuelve el control de la lógica de negocio al código, dejando que la IA haga solo lo que mejor sabe hacer: entender el lenguaje flexible.

Aquí tienes una visión global de la implementación siguiendo buenas prácticas de ingeniería de software (SOLID) y modularidad.

Visión Global del Sistema
El sistema funciona como un "cerebro dividido":

Lóbulo Creativo (DSPy): Traduce "Quiero ir a Madrid mañana" -> Intención: reservar_vuelo, Slots: {destino: 'Madrid', fecha: 'mañana'}.

Lóbulo Lógico (LangGraph): Toma esos datos estructurados y ejecuta una máquina de estados: Si tengo destino pero no origen -> Preguntar origen.

1. La Definición (YAML - DSL)
Primero, definimos el "contrato" del asistente. Esto permite cambiar el flujo sin tocar Python.

YAML
# config/flight_assistant.yaml
domain: "vuelos"

intents:
  book_flight:
    description: "Reservar un vuelo aéreo"
    required_slots:
      - origin
      - destination
      - date

states:
  - id: "init"
    type: "start"
  - id: "collect_info"
    type: "slot_filling"
  - id: "confirm_booking"
    type: "action"
    tool: "api_book_flight"
2. La Capa de Comprensión (DSPy)
Aquí creamos el módulo de Dialogue Understanding (DU). Observa que no escribimos prompts largos; definimos una Signature (Firma) y dejamos que DSPy optimice el prompt internamente.

Python
import dspy
from pydantic import BaseModel, Field

# Definimos la estructura de salida deseada (Pydantic para validación fuerte)
class NLUOutput(BaseModel):
    intent: str = Field(description="La intención del usuario basada en el YAML")
    slots: dict = Field(description="Diccionario de entidades extraídas")
    reasoning: str = Field(description="Explicación breve de por qué se eligió esta intención")

class DialogueSignature(dspy.Signature):
    """
    Analiza la entrada del usuario y el historial de conversación para determinar
    la intención y extraer entidades (slots) relevantes.
    """
    history = dspy.InputField(desc="Historial de mensajes previos")
    user_input = dspy.InputField(desc="El último mensaje del usuario")
    config_context = dspy.InputField(desc="Definiciones de intents y slots del YAML")

    parsed_output: NLUOutput = dspy.OutputField(desc="Objeto JSON estructurado")

class DSPyInterpreter:
    def __init__(self, schema_config: str):
        self.schema = schema_config
        # ChainOfThought mejora el razonamiento antes de extraer
        self.predictor = dspy.ChainOfThought(DialogueSignature)

    def predict(self, history: str, user_input: str) -> NLUOutput:
        # Aquí DSPy hace su magia de optimización/inferencia
        pred = self.predictor(
            history=history,
            user_input=user_input,
            config_context=self.schema
        )
        # En una implementación real, aquí añadiríamos lógica de 'Assert'
        # de DSPy para reintentar si el JSON es inválido.
        return pred.parsed_output
3. La Capa de Control y Política (LangGraph)
Aquí es donde garantizamos el determinismo. Usamos LangGraph para gestionar el estado.

Python
from typing import TypedDict, Annotated
from langgraph.graph import StateGraph, END

# Estado Persistente del Diálogo (DST)
class AgentState(TypedDict):
    history: list[str]  # Historial crudo
    current_slots: dict # Estado de los slots (DST real)
    last_intent: str    # Última intención detectada
    next_action: str    # Siguiente paso calculado

class DialogueGraph:
    def __init__(self, nlu_engine: DSPyInterpreter, yaml_config: dict):
        self.nlu = nlu_engine
        self.config = yaml_config
        self.workflow = self._build_graph()

    def _node_nlu(self, state: AgentState):
        """Nodo 1: Entender al usuario"""
        last_msg = state['history'][-1]
        history_str = "\n".join(state['history'][:-1])

        # Llamada a DSPy
        result = self.nlu.predict(history_str, last_msg)

        # Actualizamos slots (Merge de lo nuevo con lo viejo)
        updated_slots = state.get('current_slots', {}).copy()
        updated_slots.update(result.slots)

        return {
            "last_intent": result.intent,
            "current_slots": updated_slots
        }

    def _node_policy(self, state: AgentState):
        """Nodo 2: Lógica Determinista (Router)"""
        # Aquí leemos el YAML para ver qué falta
        intent_config = self.config['intents'].get(state['last_intent'])

        if not intent_config:
            return {"next_action": "default_fallback"}

        required = set(intent_config['required_slots'])
        filled = set(state['current_slots'].keys())
        missing = required - filled

        if missing:
            # Determinismo puro: Si falta X, pide X.
            next_slot = list(missing)[0]
            return {"next_action": f"ask_{next_slot}"}
        else:
            return {"next_action": "execute_transaction"}

    def _build_graph(self):
        workflow = StateGraph(AgentState)

        # Definir Nodos
        workflow.add_node("nlu_processor", self._node_nlu)
        workflow.add_node("policy_engine", self._node_policy)
        # Aquí añadiríamos nodos de ejecución de herramientas...

        # Definir Flujo
        workflow.set_entry_point("nlu_processor")
        workflow.add_edge("nlu_processor", "policy_engine")
        workflow.add_edge("policy_engine", END) # O loop de vuelta

        return workflow.compile()
4. Cómo se conecta todo (Main)
Python
import yaml

# 1. Cargar Configuración
with open("config/flight_assistant.yaml") as f:
    config = yaml.safe_load(f)

# 2. Inicializar Componentes
dspy_brain = DSPyInterpreter(schema_config=str(config))
bot_graph = DialogueGraph(dspy_brain, config)

# 3. Simulación de ejecución
initial_state = {
    "history": ["Quiero un vuelo a Nueva York"],
    "current_slots": {},
    "last_intent": None
}

# Ejecutar el grafo
final_state = bot_graph.workflow.invoke(initial_state)

print(f"Intención Detectada: {final_state['last_intent']}")
print(f"Slots Capturados: {final_state['current_slots']}")
print(f"Siguiente Acción (Política): {final_state['next_action']}")
Por qué esta implementación es robusta:
Testabilidad: Puedes escribir tests unitarios para _node_policy sin necesitar un LLM. Puedes asegurar que si missing = {'origin'}, la acción siempre es ask_origin.

Optimización: Puedes usar el optimizador BootstrapFewShot de DSPy para mejorar la clase DialogueSignature automáticamente si el asistente falla al entender ciertas frases, sin tocar el código de LangGraph.

Trazabilidad: LangGraph guarda el estado de cada paso. Si algo falla, sabes exactamente si fue error de comprensión (NLU) o error de lógica (Policy).

¿Te gustaría que profundice en cómo generar el dataset de entrenamiento para el módulo DSPy usando tus datos sintéticos?

Me interesa el tema de las integraciones¿Cómo se conecta con sistemas externos o con agentes humanos para que tomen el control de la conversación?

Integrar sistemas externos y humanos es donde la arquitectura de LangGraph brilla con fuerza frente a un LLM puro. En lugar de rezar para que el modelo decida llamar a una API, tú programas explícitamente cuándo y cómo sucede.

Aquí te muestro cómo extender la arquitectura anterior para incluir:

Ejecución de Herramientas (Tools): Conectar con APIs/BDs.

Human-in-the-loop (Handoff): Transferencia de control a un agente humano.

1. Integración con Sistemas Externos (Tools)
Para esto, añadimos un nuevo tipo de nodo al grafo: el ToolExecutor. Siguiendo los principios SOLID, encapsulamos las herramientas externas (API del tiempo, Base de Datos de Vuelos) usando el patrón Adapter o simplemente las herramientas de LangChain.

El Código (Extensión)
Definimos una herramienta simulada y actualizamos el grafo.

Python
from langchain.tools import tool

# 1. Definición de la Herramienta (Interface con el sistema externo)
@tool
def check_flight_availability(origin: str, destination: str, date: str) -> str:
    """Consulta la API externa de vuelos para ver disponibilidad."""
    # Aquí iría tu request real (requests.get...)
    return f"Vuelo disponible de {origin} a {destination} el {date}. Precio: 120€."

# 2. Nodo de Ejecución de Herramientas
def _node_tools(state: AgentState):
    """
    Este nodo se ejecuta SOLO si la política decide que hace falta una herramienta.
    """
    action = state['next_action'] # Ej: "call_check_flight_availability"
    slots = state['current_slots']

    # Mapeo simple de string a función (podría ser un Factory Pattern)
    if action == "call_check_flight_availability":
        # Ejecutamos la herramienta con los slots recolectados
        result = check_flight_availability.invoke({
            "origin": slots.get("origin"),
            "destination": slots.get("destination"),
            "date": slots.get("date")
        })

        return {
            "history": [f"System Tool Output: {result}"], # Añadimos al historial para que DSPy lo vea después
            "next_action": "inform_user" # Devolvemos el control para generar respuesta
        }

    return {"next_action": "error"}
2. Human Handoff (Transferencia a Humano)
La transferencia a un humano no es más que un cambio de estado en el grafo que redirige el flujo hacia un nodo terminal o de "pausa".

Podemos activar esto por dos vías:

Explícita: El usuario dice "Quiero hablar con una persona" (Detectado por DSPy como intent human_handoff).

Implícita: Sentimiento negativo detectado o confianza baja en la predicción repetida.

Implementación en el Grafo
Python
# 3. Nodo de Transferencia (Handoff)
def _node_human_handoff(state: AgentState):
    """
    Marca la conversación para atención humana y detiene al bot.
    """
    print(">>> ALERTA: Transfiriendo conversación a agente humano...")

    # Aquí llamarías a tu sistema de ticketing (Zendesk, Salesforce, WebSocket)
    # external_system.notify_agent(chat_id=state['id'])

    return {
        "next_action": "paused", # Estado especial
        "history": ["System: Transferencia realizada. Un agente entrará en breve."]
    }

# 4. Lógica de Enrutamiento (Router)
def _router(state: AgentState):
    """Decide hacia qué nodo ir basándose en 'next_action'."""
    action = state['next_action']

    if action == "human_handoff":
        return "human_node"
    elif action.startswith("call_"):
        return "tools_node"
    elif action == "inform_user":
        return "response_node"
    else:
        return "policy_node" # O volver al inicio
3. La Arquitectura Completa (Visual)
Al ensamblar esto, tu StateGraph deja de ser lineal y se convierte en una verdadera orquestación lógica:

Python
# Construcción del Grafo Actualizado
workflow = StateGraph(AgentState)

# Nodos
workflow.add_node("nlu_processor", _node_nlu)       # DSPy (Cerebro)
workflow.add_node("policy_engine", _node_policy)    # Reglas de Negocio
workflow.add_node("tools_node", _node_tools)        # APIs Externas
workflow.add_node("human_node", _node_human_handoff)# Escalado

# Punto de entrada
workflow.set_entry_point("nlu_processor")

# Aristas (Flujo)
workflow.add_edge("nlu_processor", "policy_engine")

# Aristas Condicionales (El Router)
workflow.add_conditional_edges(
    "policy_engine",
    _router,
    {
        "tools_node": "tools_node",
        "human_node": "human_node",
        "response_node": END, # Fin del turno del bot
        "policy_node": "policy_engine"
    }
)

# Loop de vuelta desde las herramientas para que el bot "lea" el resultado
workflow.add_edge("tools_node", "policy_engine")

app = workflow.compile()
Resumen de ventajas de este enfoque:
Seguridad (Guardrails): El nodo policy_engine actúa como un firewall. Si DSPy alucina y pide "borrar base de datos", la política (código Python determinista) puede bloquear esa acción antes de llegar al tools_node.

Contexto para el Humano: Cuando se activa _node_human_handoff, pasas el objeto state completo al agente humano. El agente no solo ve el chat, sino también los slots que el bot ya había capturado ("Ah, veo que querías ir a Madrid...").

Modularidad: Puedes cambiar la API de vuelos en _node_tools sin tocar ni una línea de la lógica de comprensión (DSPy) ni de la política de diálogo.

Dado que mencionaste que quieres generar datasets (aviones, drones, clima) para entrenar modelos, ¿te interesaría ver cómo podríamos usar este mismo flujo de DSPy para generar diálogos sintéticos de alta calidad que simulen a operadores de drones interactuando con este sistema?

Hay alguna forma de usar langgraph visualmente?

Sí, absolutamente. De hecho, la visualización y la depuración visual son dos de las ventajas más fuertes de LangGraph frente a otras librerías de agentes.

Tienes principalmente dos formas de hacerlo: una para desarrollo/debugging interactivo (la más potente) y otra para documentación/verificación rápida.

1. LangGraph Studio (El "IDE" visual)
LangChain (la empresa detrás de LangGraph) lanzó una herramienta llamada LangGraph Studio. No es solo un visor, es un entorno de desarrollo integrado especializado en agentes.

Imagina que levantas tu aplicación y ves esto:

Grafo Visual: Ves tus nodos (nlu_processor, policy_engine, tools) y las flechas conectados en tiempo real.

Ejecución Paso a Paso: Cuando envías un mensaje, ves cómo se ilumina el camino que toma el agente.

Modificación de Estado (State Editing): Esto es crítico. Puedes pausar el agente justo antes de que llame a una API, editar manualmente el JSON del state (por ejemplo, corregir un slot que DSPy predijo mal) y reanudar la ejecución.

Time Travel: Puedes "rebobinar" la conversación a un paso anterior, cambiar el código o el estado, y volver a ejecutar desde ahí (Forking).

Cómo se configura: Solo necesitas un archivo langgraph.json en la raíz de tu proyecto que apunte a tu grafo compilado.

JSON
{
  "dependencies": ["."],
  "graphs": {
    "agent": "./my_agent.py:app"
  },
  "env": ".env"
}
2. Visualización Estática (Mermaid)
Si solo quieres verificar que tu lógica de enrutamiento y tus conditional_edges están bien conectados (ideal para generar diagramas para tu documentación o ADRs), puedes generar una imagen directamente desde el código Python.

LangGraph usa la sintaxis Mermaid bajo el capó.

Python
from IPython.display import Image, display

# Suponiendo que 'app' es tu grafo compilado (workflow.compile())
try:
    # Genera el diagrama en formato PNG
    diagrama = app.get_graph().draw_mermaid_png()
    display(Image(diagrama))

    # Opcional: Guardarlo en disco para documentación
    with open("arquitectura_dialogo.png", "wb") as f:
        f.write(diagrama)

except Exception as e:
    print(f"No se pudo generar el gráfico. Asegúrate de tener graphviz/mermaid instalados: {e}")
¿Por qué esto es vital para tu ADR?
Para tu propuesta de arquitectura híbrida, usar LangGraph Studio valida uno de tus puntos fuertes: la Trazabilidad.

Debugging de DSPy vs Política: Si el bot falla, miras el visualizador.

¿Entró en el nodo nlu_processor y salió con el intent incorrecto? -> Culpa de DSPy/LLM.

¿Salió con el intent correcto pero se fue por la rama equivocada del grafo? -> Culpa de la lógica en Python (LangGraph).

Human-in-the-loop Visual: Puedes simular el nodo de "Human Handoff" en el Studio. El flujo se detiene, tú (actuando como el humano) inyectas una respuesta en el estado, y dejas que el bot continúe.

Siguiente paso: Si quieres, puedo prepararte el archivo de configuración (langgraph.json) y la estructura de carpetas necesaria para que tu proyecto sea compatible con LangGraph Studio desde el primer día. ¿Te parece bien?

Vale, dame un estructura de proyecto potencial que siga las mejores prácticas de software, principios solid, etc.

Esta estructura está diseñada siguiendo Clean Architecture (Arquitectura Hexagonal). El objetivo es desacoplar el "Core" (Lógica de dominio) de la "Infraestructura" (DSPy, LangGraph, APIs externas).

Esto cumple con el Principio de Inversión de Dependencias (D en SOLID): los detalles de implementación (DSPy/LangGraph) dependen de las abstracciones del dominio, y no al revés.

Estructura de Carpetas
Plaintext
my-tod-framework/
├── config/                     # Definiciones Declarativas (ADR Requisito)
│   ├── domains/
│   │   ├── flights.yaml        # Tu DSL de vuelos
│   │   └── drones.yaml         # Futuro dominio (contexto usuario)
│   └── settings.yaml           # Configuración global (API keys, timeouts)
│
├── src/
│   ├── core/                   # CAPA DE DOMINIO (Puro Python, sin deps pesadas)
│   │   ├── entities.py         # Modelos Pydantic (State, Slot, Intent)
│   │   ├── interfaces.py       # Protocolos/ABCs (INLUProvider, ITool)
│   │   └── errors.py           # Excepciones personalizadas del dominio
│   │
│   ├── application/            # CAPA DE APLICACIÓN (Casos de uso)
│   │   ├── dtos.py             # Data Transfer Objects
│   │   └── registry.py         # Factory/Registry para cargar Tools dinámicamente
│   │
│   ├── infrastructure/         # CAPA DE INFRAESTRUCTURA (Implementaciones)
│   │   ├── dspy/               # Adaptador para Dialogue Understanding
│   │   │   ├── signatures.py   # Firmas de DSPy (Prompts implícitos)
│   │   │   ├── modules.py      # Módulos DSPy (ChainOfThought, etc.)
│   │   │   └── provider.py     # Implementación de INLUProvider
│   │   │
│   │   ├── langgraph/          # Adaptador para Control & Policy
│   │   │   ├── state.py        # TypedDict específico de LangGraph
│   │   │   ├── nodes.py        # Lógica de los nodos (wrappers)
│   │   │   └── builder.py      # Constructor del StateGraph
│   │   │
│   │   └── tools/              # Adaptadores para sistemas externos
│   │       ├── flight_api.py
│   │       └── simulator.py    # Futuro: Generador de datos sintéticos
│   │
│   └── main.py                 # Composition Root (Inyección de Dependencias)
│
├── tests/                      # Testing (Crucial para SOLID)
│   ├── unit/
│   │   ├── test_core.py        # Testear lógica sin LLMs
│   │   └── test_nodes.py       # Testear nodos de LangGraph aislados
│   ├── integration/
│   │   └── test_workflow.py    # Test del grafo completo (mockeando LLM)
│   └── e2e/                    # Tests reales con LLM
│
├── notebooks/                  # Experimentación y análisis de trazas
├── langgraph.json              # Configuración para LangGraph Studio
├── pyproject.toml              # Gestión de dependencias (Poetry/UV)
├── .env                        # Variables de entorno
└── README.md
Detalles de Implementación SOLID
Aquí es donde la estructura brilla. Fíjate cómo aplicamos los principios:

1. Interfaces (Core/Interfaces.py) - Interface Segregation & Dependency Inversion
Definimos qué necesita nuestro sistema, sin importar si usamos DSPy, OpenAI directo o Regex.

Python
# src/core/interfaces.py
from typing import Protocol
from src.core.entities import DialogueContext, NLUResult

class INLUProvider(Protocol):
    """Contrato que debe cumplir cualquier motor de comprensión (DSPy, etc.)"""
    def predict_intent(self, context: DialogueContext) -> NLUResult:
        ...

class IToolExecutor(Protocol):
    """Contrato para ejecutar herramientas externas"""
    def execute(self, tool_name: str, params: dict) -> dict:
        ...
2. Implementación DSPy (Infra/DSPy/Provider.py) - Single Responsibility
Esta clase solo se preocupa de traducir los tipos de DSPy a los tipos de tu Dominio.

Python
# src/infrastructure/dspy/provider.py
import dspy
from src.core.interfaces import INLUProvider
from src.core.entities import DialogueContext, NLUResult
from .signatures import IntentSignature

class DSPyNLUProvider(INLUProvider):
    def __init__(self, schema_config: dict):
        self.predictor = dspy.ChainOfThought(IntentSignature)
        self.config = schema_config

    def predict_intent(self, context: DialogueContext) -> NLUResult:
        # Lógica específica de DSPy
        pred = self.predictor(history=context.history_str, ...)
        # Mapping a entidad de dominio limpia
        return NLUResult(
            intent=pred.intent,
            slots=pred.slots,
            confidence=0.9 # Simulado o calculado
        )
3. Configuración de LangGraph Studio (langgraph.json)
Este archivo en la raíz permite levantar la UI visual automáticamente.

JSON
{
  "dependencies": ["."],
  "graphs": {
    "flight_bot": "./src/main.py:graph_app"
  },
  "env": ".env"
}
4. Composition Root (src/main.py) - Dependency Injection
Aquí es donde se "pegan" las piezas. Si mañana quieres cambiar DSPy por otro modelo, solo cambias una línea aquí.

Python
# src/main.py
import yaml
from src.infrastructure.dspy.provider import DSPyNLUProvider
from src.infrastructure.langgraph.builder import DialogueGraphBuilder
from src.infrastructure.tools.flight_api import FlightAPIAdapter

# 1. Cargar Configuración (YAML)
with open("config/domains/flights.yaml") as f:
    domain_config = yaml.safe_load(f)

# 2. Instanciar Dependencias (Infraestructura)
nlu_service = DSPyNLUProvider(schema_config=domain_config)
tools_service = FlightAPIAdapter()

# 3. Inyectar dependencias en el Constructor del Grafo
graph_builder = DialogueGraphBuilder(
    nlu=nlu_service,
    tools=tools_service,
    config=domain_config
)

# 4. Exponer el ejecutable (para LangGraph Studio o Producción)
graph_app = graph_builder.build()
Siguiente paso sugerido
Esta estructura está lista para producción. Dado que tienes interés en la generación de datasets (tu idea de drones/aviones), ¿te gustaría que preparemos el módulo de tests/ con un enfoque en Data-Driven Testing?

Podríamos usar DSPy no solo para el bot, sino crear un script en src/infrastructure/tools/simulator.py que genere casos de prueba (diálogos usuario-bot sintéticos) basados en tu YAML para validar la robustez del grafo antes de desplegar.




Gemini puede cometer errores, incluso sobre personas, así que verifica sus respuestas. Tu privacidad y GeminiSe abre en una ventana nueva
