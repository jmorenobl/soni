# Análisis de Viabilidad - ADR-001: Soni Framework Architecture

**Proyecto:** Soni - Framework Open Source para Asistentes Conversacionales  
**Documento:** Análisis de Viabilidad Técnica  
**Fecha de Análisis:** 29 de Noviembre de 2025  
**Analista:** Jorge - AI Solutions Architect  
**Versión:** 1.0  
**Estado:** Aprobado

---

## Resumen Ejecutivo

Este documento presenta un análisis exhaustivo de la viabilidad técnica del ADR-001 de Soni Framework, basado en investigación actualizada de las tecnologías propuestas (DSPy, LangGraph, MIPROv2, SIMBA, GEPA) y evaluación del panorama competitivo actual.

**Veredicto General:** ✅ **VIABLE con ajustes estratégicos recomendados**

**Puntuación de Viabilidad:** 8.5/10

---

## 1. Análisis de Tecnologías Core

### 1.1 DSPy y Optimizadores

#### Estado Actual: ✅ EXCELENTE

**Versión Analizada:** DSPy 3.0.4 (Noviembre 2025)

**Novedades Importantes en DSPy 3.0:**
- **Async nativo**: Soporte completo para programas DSPy asíncronos con `dspy.syncify` para ejecutar optimizadores en programas async
- **Streaming mejorado**: Streaming de tokens y estado desde cualquier capa, no solo salida final
- **Observabilidad**: Integración nativa con MLflow 3.0 para tracing, tracking de optimizadores, y deployment
- **Adapters**: Sistema extensible (ChatAdapter, JSONAdapter, XMLAdapter, BAMLAdapter) con fallback inteligente
- **Tipos multi-modal**: dspy.Image, dspy.Audio, y tipos compuestos (list[dspy.Image], modelos Pydantic)
- **Escalabilidad**: Module.batch con DSPy settings thread-safe, caches de alta concurrencia configurables
- **Nuevos módulos**: dspy.CodeAct, dspy.Refine, ReAct mejorado, PythonInterpreter más confiable
- **GRPO**: Biblioteca Arbor para entrenamiento RL de sistemas compound AI

#### MIPROv2 (Multiprompt Instruction Proposal Optimizer v2)

**Estado:** Activo y maduro

**Hallazgos:**
- DSPy 3.0 introduce mejoras significativas: escalabilidad con Module.batch y configuraciones thread-safe, soporte async nativo, caches de alta concurrencia, streaming de tokens y estado desde cualquier capa, tracking de uso, y callbacks enriquecidos
- Nuevos módulos: dspy.CodeAct, dspy.Refine, ReAct mejorado, y PythonInterpreter más confiable
- Integración nativa con MLflow 3.0 para trazabilidad, tracking de optimizadores, y flujos de deployment mejorados
- MIPROv2 sustancialmente más confiable con selección automática de hiperparámetros y múltiples correcciones
- Soporte para Adapters (ChatAdapter, JSONAdapter, XMLAdapter, BAMLAdapter) con streaming de tokens/estado, paths async, y fallback inteligente a salidas estructuradas nativas del LLM
- Tipos multi-modal vía dspy.Image y dspy.Audio, tipos compuestos (list[dspy.Image], modelos Pydantic), y I/O de alto nivel como dspy.History y dspy.ToolCalls
- Implementación estable con soporte completo para optimización conjunta de instrucciones y ejemplos few-shot
- Utiliza Optimización Bayesiana para búsqueda efectiva en el espacio de prompts
- Configuración flexible: `auto="light|medium|heavy"` para diferentes presupuestos de optimización
- Soporte para optimización 0-shot (solo instrucciones) y few-shot (instrucciones + demos)

**Código de Ejemplo Verificado:**
```python
from dspy.teleprompt import MIPROv2

teleprompter = MIPROv2(
    metric=gsm8k_metric,
    auto="medium",  # light, medium, heavy
)

optimized_program = teleprompter.compile(
    dspy.ChainOfThought("question -> answer"),
    trainset=gsm8k.train,
)
```

**Fuentes:**
- Documentación oficial DSPy: https://dspy.ai/api/optimizers/MIPROv2/
- Paper: "MIPROv2: Optimizing Prompts via Multi-stage Instruction Proposal"
- Integración con LangWatch para UI de baja-código disponible

#### SIMBA (Stochastic Introspective Mini-Batch Ascent)

**Estado:** Activo y en producción

**Hallazgos:**
- Usa muestreo mini-batch estocástico para identificar ejemplos desafiantes con alta variabilidad de salida
- El LLM analiza introspectivamente sus propios fallos
- Genera reglas de mejora auto-reflexivas o añade demos exitosas
- Mayor eficiencia de muestra y estabilidad vs MIPROv2 en LLMs avanzados

**Características Clave:**
- Auto-introspección del modelo
- Mejor rendimiento con modelos más capaces (GPT-4, Claude, etc.)
- Ideal para tareas agentic/long-horizon

**Código de Ejemplo:**
```python
from dspy.teleprompt import SIMBA

optimizer = dspy.SIMBA(
    metric=your_metric,
    max_steps=12,
    max_demos=10
)
optimized_program = optimizer.compile(
    your_dspy_program, 
    trainset=trainset
)
```

#### GEPA (Genetic-Pareto Optimizer)

**Estado:** ✅ ESTADO DEL ARTE (Introducido 2025)

**Hallazgos Críticos:**
- Paper: "GEPA: Reflective Prompt Evolution Can Outperform Reinforcement Learning" (Agrawal et al., 2025)
- Mejoras de hasta 11% sobre MIPROv2 en diversos benchmarks
- Extremadamente eficiente con pocos datos (34 ejemplos en casos documentados)
- +10% de mejora en AIME 2025 con GPT-4o Mini

**Características Revolucionarias:**
- Evolución reflexiva de prompts usando feedback textual
- Construcción de árbol Pareto de prompts
- Puede producir prompts más cortos mientras mejora rendimiento
- Soporte para multi-objetivo (accuracy, safety, compliance)

**Código de Ejemplo:**
```python
import dspy

teleprompter = dspy.GEPA(
    metric=your_feedback_metric,  # Puede retornar texto + score
    auto="light",
    use_merge=True,
    num_threads=4
)

optimized = teleprompter.compile(
    student=your_program,
    trainset=trainset,
    valset=valset
)
```

**Ventaja Única:** Acepta feedback textual rico, no solo scores escalares.

#### Integración MLflow

**Estado:** ✅ Disponible

GEPA está integrado en MLflow 3.0+ a través de `mlflow.genai.optimize_prompts()` API para optimización automática de prompts usando métricas de evaluación.

#### Conclusión Tecnológica - DSPy

**Veredicto:** ✅✅✅ **EXTREMADAMENTE VIABLE**

**Fortalezas:**
- Ecosystem maduro y activamente mantenido por Stanford NLP (con soporte adicional de Databricks)
- **DSPy 3.0** introduce mejoras críticas: async nativo, streaming completo, escalabilidad thread-safe
- Tres optimizadores state-of-the-art disponibles (MIPROv2 mejorado, SIMBA, GEPA)
- Integración nativa con MLflow 3.0 para observabilidad, tracing y tracking de optimizadores
- Sistema de **Adapters** para diferentes formatos (Chat, JSON, XML, BAML) con fallback inteligente
- Tipos multi-modal (dspy.Image, dspy.Audio) y tipos compuestos (Pydantic models)
- Biblioteca **Arbor** para GRPO (RL training de sistemas compound AI)
- Soporte completo para módulos async (`acall()`) y batch processing
- Composición de optimizadores permitida (pipeline optimization)

**Riesgos:**
- Desarrollo rápido puede introducir cambios menores entre versiones 3.0.x
- DSPy 3.0 es estable pero el ecosistema sigue evolucionando
- Breaking change menor en 3.0: retriever integration descontinuado (afecta a muy pocos usuarios)

**Recomendación:** 
- ✅ Usar como pilar central de la arquitectura
- Pin versión: `dspy>=3.0.4,<4.0.0`
- Tu propuesta de `SoniDU(dspy.Module)` es el approach correcto
- Aprovechar nuevas características de 3.0: async nativo, streaming, Adapters

---

### 1.2 LangGraph - Orquestación y Streaming

#### Estado Actual: ✅ EXCELENTE

**Versión Analizada:** LangGraph 1.0.4 (Noviembre 2025)

#### Soporte Asíncrono

**Estado:** ✅ Production-ready

**Hallazgos:**
- Soporte nativo completo para async/await
- Métodos async: `.ainvoke()`, `.astream()`, `.astream_events()`
- Compatible con Python 3.11+ (contextvars propagation automática)
- Zero overhead para workflows asíncronos

**Nota sobre Python < 3.11:**
- En Python 3.8-3.10 se requiere pasar `RunnableConfig` explícitamente
- No se puede usar `get_stream_writer` en nodos async (usar argumento `writer`)
- **Recomendación:** Target Python 3.11+ para mejor DX

#### Streaming System

**Estado:** ✅ Producción con múltiples modos

**Modos de Streaming Disponibles:**

1. **`values`** - Estado completo después de cada paso
2. **`updates`** - Deltas incrementales del estado
3. **`messages`** - Tokens LLM + metadata
4. **`custom`** - Datos arbitrarios definidos por usuario
5. **`debug`** - Trazas detalladas para debugging

**Código de Ejemplo Verificado:**
```python
# Streaming async básico
async for chunk in graph.astream(input, stream_mode="values"):
    print(chunk)

# Streaming de tokens LLM
async for event in graph.astream_events(input, version="v2"):
    if event["event"] == "on_chat_model_stream":
        token = event["data"]["chunk"].content
        print(token, end="")
```

**Streaming Custom en Nodos:**
```python
from langgraph.types import StreamWriter

async def streaming_node(state, writer: StreamWriter):
    for word in message.split():
        writer(AIMessageChunk(content=word))
    return {"messages": final_message}
```

#### Compatibilidad con FastAPI

**Estado:** ✅ Integración nativa

**Hallazgos:**
- Diseño específico para streaming workflows
- Sin overhead adicional
- Patrones documentados para FastAPI + LangGraph + Streamlit

**Ejemplo de Integración:**
```python
from fastapi import FastAPI
from fastapi.responses import StreamingResponse

app = FastAPI()

@app.post("/chat/stream")
async def chat_stream(message: str):
    async def generate():
        async for chunk in graph.astream({"messages": [message]}):
            yield chunk
    
    return StreamingResponse(generate(), media_type="text/event-stream")
```

#### Persistencia y Checkpointing

**Estado:** ✅ Soporte completo

**Backends Soportados:**
- SQLite (sync y async con aiosqlite)
- PostgreSQL (async con asyncpg)
- Redis (async con aioredis)
- Custom checkpointers

**Tu Propuesta:**
```yaml
persistence:
  backend: sqlite
  path: ./data/dialogue.db
```

**Validación:** ✅ Completamente soportado

#### LangGraph Studio

**Estado:** ✅ Disponible

- Herramienta visual para debugging y prototipado
- Deploy 1-click con LangGraph Platform
- Monitoreo con LangSmith integration

#### Desarrollo y Mantenimiento

**Estado:** ✅ Muy activo

- Releases frecuentes (última: 1.0.4 en Nov 2025)
- Desarrollo por LangChain (empresa con funding)
- Documentación completa y en mejora constante
- Usado en producción por empresas (Klarna, Replit, Elastic)

#### Conclusión Tecnológica - LangGraph

**Veredicto:** ✅✅✅ **EXTREMADAMENTE VIABLE**

**Fortalezas:**
- Arquitectura async-first sin overhead
- Sistema de streaming robusto y flexible
- Múltiples backends de persistencia
- Integración natural con FastAPI
- Ecosistema maduro y bien mantenido

**Riesgos:**
- En fase 1.0.x, posibles cambios menores en API
- Dependencia de LangChain ecosystem

**Recomendación:**
- ✅ Usar como runtime principal
- Pin versión: `langgraph>=1.0.0,<1.1.0`
- Tu arquitectura async es completamente viable
- Streaming nativo cumple todos tus requisitos

---

### 1.3 Bibliotecas Auxiliares

#### aiosqlite / asyncpg / aioredis

**Estado:** ✅ Maduras y estables

- `aiosqlite`: Wrapper async sobre sqlite3
- `asyncpg`: Driver PostgreSQL async de alto rendimiento
- `aioredis`: Cliente Redis async (ahora parte de redis-py)

**Recomendación:** Soportadas, usar sin problemas.

#### FastAPI

**Estado:** ✅ Industry standard

- Framework async de facto para Python
- Validación con Pydantic
- OpenAPI/Swagger automático
- Streaming nativo con Server-Sent Events

**Recomendación:** Elección perfecta para tu API layer.

---

## 2. Análisis del Panorama Competitivo

### 2.1 Rasa - Evaluación Actualizada

#### Tu Evaluación Original (ADR)

> "Rasa: Activo, pero bifurcado. Innovación LLM restringida a versión comercial (Pro). Versión OS mantiene arquitectura legacy."

#### Hallazgos de Investigación (Nov 2025)

**Estado Real:** ⚠️ **TU EVALUACIÓN ES PARCIALMENTE CORRECTA PERO NECESITA MATICES**

#### Rasa Open Source

**Estado:** Activo pero con limitaciones LLM

- Componentes LLM disponibles en **beta** (experimental)
- `LLMIntentClassifier` usando RAG disponible en OS
- Configuración básica de LLMs (OpenAI, Azure) soportada
- **PERO:** Características avanzadas exclusivas de Rasa Pro

**Características OS:**
- Intent classification con LLM (RAG-based)
- Few-shot learning
- Multilingual support
- Configuración de temperatura, prompts, etc.

**Limitaciones OS:**
- Sin CALM architecture
- Sin CompactLLMCommandGenerator
- Sin LLMBasedRouter avanzado
- Sin ContextualResponseRephraser
- Sin Rasa Studio (UI visual)

#### Rasa Pro (Versión Comercial)

**Estado:** ✅ **MUY COMPETITIVO** (Actualización crítica para tu ADR)

**Arquitectura CALM (Conversational AI with Language Models):**
- Introducida en 2024-2025
- Paradigm shift completo hacia LLM-native
- Integración de LLMs manteniendo determinismo empresarial

**Componentes Avanzados (Rasa Pro):**

1. **CompactLLMCommandGenerator** (Nuevo en 3.12+)
   - Prompts optimizados para GPT-4o y Claude 3.5 Sonnet
   - 10x reducción de costes vs generadores anteriores
   - Multi-step command generation

2. **LLMBasedRouter**
   - Routing inteligente entre flujos CALM
   - Soporte sticky/non-sticky routing
   - Multi-LLM routing para escalado

3. **ContextualResponseRephraser**
   - Rephrasing contextual de respuestas
   - Mantiene control sobre contenido base

4. **Rasa Studio** (UI No-Code)
   - Visual Flow Builder drag-and-drop
   - Prompt Engineering integrado
   - Voice testing 1-click
   - Colaboración para no-técnicos

**Modelos Soportados (Rasa Pro 3.13+):**
- GPT-4o (2024-11-20)
- GPT-4.1-mini (2025-04-14)
- Claude 3.5 Sonnet (2024-06-20)
- Embeddings: text-embedding-3-large

**Características Empresariales:**
- Multi-language support con traducciones automáticas
- ReAct-style agents nativos
- Call steps para invocar agents desde flows
- LLM Judge para testing E2E
- Enterprise Search Policy

#### Implicaciones para Soni

**Conclusión:** Rasa Pro es **significativamente más competitivo** de lo que tu ADR sugiere.

**¿Invalida tu propuesta?** ❌ **NO, pero cambia tu posicionamiento**

**Diferenciadores de Soni vs Rasa Pro:**

| Aspecto | Soni | Rasa Pro |
|---------|------|----------|
| **Licencia** | ✅ 100% Open Source | ❌ Comercial (precio no público) |
| **Optimización** | ✅ Automática (DSPy) | ❌ Manual (prompt engineering) |
| **Bifurcación** | ✅ Sin split OS/Pro | ❌ Features clave en Pro |
| **Control** | ✅ Total (self-hosted) | ⚠️ Depende del plan |
| **LLM Support** | ✅ DSPy-native | ✅ LLM-native (CALM) |
| **UI Visual** | ⚠️ Pendiente | ✅ Rasa Studio |
| **Enterprise** | ⚠️ Por construir | ✅ Maduro |

**Tu Ventaja Real:**

1. **Optimización Automática** - El killer feature
   - Rasa Pro usa prompt engineering manual
   - Tú usas MIPROv2/SIMBA/GEPA automático
   - Esto es un **game-changer** para equipos sin expertos en prompting

2. **100% Open Source** - Sin vendor lock-in
   - Rasa bifurca innovación hacia Pro
   - Tú mantienes todo en OS

3. **DSPy-First Architecture**
   - Programas, no prompteas
   - Módulos optimizables de forma sistemática
   - Composabilidad nativa

**Recomendación Crítica:**

⚠️ **REPOSICIONA TU PROPUESTA DE VALOR**

**En lugar de:**
> "Rasa está obsoleto en LLMs"

**Di:**
> "Soni elimina el prompt engineering manual mediante optimización automática con DSPy, mientras que otros frameworks (incluyendo Rasa Pro comercial) requieren tuning manual de prompts. 100% open source, sin bifurcación comercial."

---

### 2.2 Otros Competidores

#### Botpress

**Estado:** Cloud-first con OS secundario

- Enfoque en SaaS
- Versión self-hosted existe pero es secundaria
- UI visual fuerte
- **Tu ventaja:** Open source puro, optimización automática

#### Chatterbot

**Estado:** Legacy en mantenimiento

- Arquitectura obsoleta
- Soporte LLM experimental y frágil
- **Tu ventaja:** Todo tu stack moderno

#### Parlant

**Estado:** Inmaduro con problemas

- Problemas de latencia reportados (9x overhead)
- Framework muy joven
- **Tu ventaja:** LangGraph probado + DSPy maduro

---

## 3. Evaluación de la Arquitectura Propuesta

### 3.1 Arquitectura Híbrida Desacoplada

**Evaluación:** ✅ **EXCELENTE DISEÑO**

**Componentes Core:**

#### SoniDU (Dialogue Understanding)

```python
class SoniDU(dspy.Module):
    async def acall(self, input: str) -> Command:
        # Traducir entrada a comando estructurado
        pass
```

**Validación:** ✅ Pattern correcto
- Hereda de `dspy.Module` ✓
- Usa `acall()` para async ✓
- Retorna estructura validable ✓

#### Dynamic Scoping

**Concepto:** Inyectar solo acciones relevantes en contexto LLM

**Evaluación:** ✅ CRÍTICO PARA ESCALABILIDAD

**Problema que resuelve:**
- Sin scoping: 100 acciones → contexto saturado → precisión baja
- Con scoping: 5-10 acciones relevantes → contexto limpio → precisión alta

**Implementación sugerida:**
```python
class DynamicScoper:
    async def get_relevant_actions(
        self, 
        current_state: DialogueState,
        intent: str
    ) -> List[Action]:
        # Filtrado semántico con embeddings
        # O reglas basadas en flow actual
        pass
```

**Riesgo:** Complejidad media
**Recomendación:** Empieza con scoping basado en flows, añade semántico después.

#### Normalization Layer

**Concepto:** Puente entre salida "blanda" del LLM y validación "dura"

**Ejemplo:**
```
User: "Quiero volar a Madriz mañana"
LLM extrae: "Madriz, probablemente Madrid"
Normalizer: "Madriz" → "Madrid" (fuzzy match + LLM)
Validator: "Madrid" ✓ (en lista de ciudades)
```

**Evaluación:** ✅ ESENCIAL PARA ROBUSTEZ

**Estrategias:**
1. Heurísticas (trim, lowercase, fuzzy matching)
2. LLM correction (para casos ambiguos)
3. Fallback a usuario (cuando confianza baja)

**Tu Propuesta en YAML:**
```yaml
entities:
  - name: city
    normalization:
      strategy: llm_correction  # ✓ Correcto
  - name: date
    normalization:
      strategy: trim  # ✓ Correcto
```

**Recomendación:** Implementar en fases
- v0.1.0 (MVP): Solo heurísticas
- v0.2.0: Añadir LLM correction

#### Step Compiler (v0.3.0)

**Concepto:** Traducir YAML procedural a LangGraph StateGraph

**Entrada (YAML):**
```yaml
process:
  - step: collect_origin
  - step: collect_destination
  - step: search_flights
    conditions:
      - if: "no_results"
        jump_to: suggest_alternatives
```

**Salida (Python):**
```python
graph = StateGraph(DialogueState)
graph.add_node("collect_origin", collect_origin_fn)
graph.add_node("collect_destination", collect_destination_fn)
graph.add_node("search_flights", search_flights_fn)
graph.add_conditional_edges("search_flights", route_fn)
```

**Evaluación:** ⚠️ **COMPLEJIDAD ALTA PERO VIABLE**

**Desafíos:**
1. Parsear condiciones complejas
2. Generar funciones de routing dinámicas
3. Mantener trazabilidad YAML ↔ Graph
4. Validar que el grafo resultante es válido

**Recomendación:**
- v0.1.0 (MVP): Solo steps lineales (secuencia simple)
- v0.3.0: Añadir condicionales y jumps
- Usar AST manipulation para generar código limpio
- Tests exhaustivos de compilación

**Riesgo:** Si falla, todo el framework falla
**Mitigación:** Suite de tests golden-path + edge cases

---

### 3.2 Zero-Leakage Architecture (v0.4.0)

**Evaluación:** ✅✅✅ **DISEÑO BRILLANTE - DIFERENCIADOR CLAVE**

Esta es tu **innovación arquitectónica** más importante.

#### Problema que Resuelve

**Antes (v0.3.0):**
```yaml
actions:
  search_flights:
    type: http
    method: POST  # ❌ Detalle técnico
    url: "https://api.example.com/flights"  # ❌ Acoplamiento
    body:
      origin: "{origin}"
    jsonpath: "$.data.flights"  # ❌ Estructura interna
```

**Después (v0.4.0):**
```yaml
actions:
  search_flights:
    description: "Busca vuelos disponibles"  # ✓ Semántico
    params:
      - origin
      - destination
      - date
    map_outputs:
      flight_count: num_results  # ✓ Mapeo desacoplado
```

#### Action Registry

**Implementación Python:**
```python
from soni.registry import action

@action("search_flights")
async def search_flights_impl(
    origin: str,
    destination: str,
    date: datetime
) -> FlightSearchResult:
    # Toda la lógica HTTP aquí
    async with httpx.AsyncClient() as client:
        response = await client.post(
            "https://api.example.com/flights",
            json={...}
        )
    return FlightSearchResult.parse(response.json())
```

**Ventajas:**
1. ✅ Analistas editan YAML sin romper integraciones
2. ✅ Devs cambian APIs sin tocar YAML
3. ✅ Testing independiente (mock actions)
4. ✅ Versionado separado (business logic vs tech)

#### Validator Registry

**Implementación:**
```python
from soni.registry import validator

@validator("is_valid_iata_code")
def validate_iata(value: str) -> bool:
    # Regex oculta, nombre semántico expuesto
    return re.match(r'^[A-Z]{3}$', value) is not None

@validator("is_future_date")
def validate_future_date(value: datetime) -> bool:
    return value > datetime.now()
```

**YAML:**
```yaml
entities:
  - name: airport_code
    validators:
      - is_valid_iata_code  # ✓ Legible por humanos
  - name: departure_date
    validators:
      - is_future_date  # ✓ Semántico
```

#### Output Mapping

**Problema:**
```python
# API retorna:
{
  "data": {
    "search_results": {
      "total": 42,
      "items": [...]
    }
  }
}
```

**Sin mapping (v0.3.0):**
```yaml
# Usuario necesita saber estructura interna ❌
response_template: "Encontré {res.data.search_results.total} vuelos"
```

**Con mapping (v0.4.0):**
```yaml
# Action define mapeo
map_outputs:
  flight_count: data.search_results.total
  flights: data.search_results.items

# Usuario usa nombres semánticos ✓
response_template: "Encontré {flight_count} vuelos"
```

**Implementación:**
```python
@action("search_flights")
async def search_flights_impl(...) -> dict:
    result = await call_api(...)
    return {
        "flight_count": result["data"]["search_results"]["total"],
        "flights": result["data"]["search_results"]["items"]
    }
```

#### Conclusión Zero-Leakage

**Veredicto:** ✅✅✅ **ESTE ES TU MOAT**

**Valor Único:**
- Ningún framework ToD open source tiene esta separación
- Rasa Pro lo intenta con CALM Flows pero no al nivel de abstracción que propones
- Es tu ventaja competitiva #1 junto con optimización DSPy

**Complejidad:**
- Media-Alta para implementar
- Requiere reflection/introspection cuidadosa
- Testing riguroso de registry system

**Recomendación:**
- ✅ Mantener como objetivo core
- Implementar en v0.4.0 (después de consolidar base)
- Documentación exhaustiva para developers
- Examples claros de cómo extender

---

## 4. Riesgos y Mitigaciones

### 4.1 Riesgos Técnicos

#### Riesgo 1: Complejidad del Step Compiler

**Probabilidad:** Media  
**Impacto:** Alto  
**Severidad:** ⚠️ MEDIO-ALTO

**Descripción:**
Traducir YAML procedural a StateGraph puede introducir bugs difíciles de depurar.

**Mitigación:**
1. Suite de tests exhaustiva
2. Validación de YAML en tiempo de carga
3. Generación de visualización del grafo resultante
4. Logging detallado de compilación
5. Empezar con subset simple de features

**Implementación sugerida:**
```python
class StepCompiler:
    def validate_yaml(self, yaml_config: dict) -> List[ValidationError]:
        """Validar antes de compilar"""
        pass
    
    def compile(self, yaml_config: dict) -> StateGraph:
        """Compilar con validación"""
        errors = self.validate_yaml(yaml_config)
        if errors:
            raise CompilationError(errors)
        
        graph = self._build_graph(yaml_config)
        self._validate_graph(graph)
        return graph
    
    def visualize(self, graph: StateGraph) -> str:
        """Generar mermaid diagram para debugging"""
        pass
```

#### Riesgo 2: Rendimiento del Normalizer

**Probabilidad:** Media  
**Impacto:** Medio  
**Severidad:** ⚠️ MEDIO

**Descripción:**
Llamadas LLM adicionales para normalización pueden aumentar latencia.

**Mitigación:**
1. Cache de normalizaciones frecuentes
2. Heurísticas primero, LLM solo si necesario
3. Normalización async no-bloqueante
4. Threshold de confianza para skip LLM

**Implementación:**
```python
class Normalizer:
    def __init__(self):
        self.cache = TTLCache(maxsize=1000, ttl=3600)
    
    async def normalize(
        self, 
        value: str, 
        entity_type: str
    ) -> NormalizedValue:
        # 1. Check cache
        cache_key = f"{entity_type}:{value}"
        if cache_key in self.cache:
            return self.cache[cache_key]
        
        # 2. Try heuristics
        heuristic_result = self.apply_heuristics(value, entity_type)
        if heuristic_result.confidence > 0.9:
            self.cache[cache_key] = heuristic_result
            return heuristic_result
        
        # 3. Fallback to LLM
        llm_result = await self.llm_normalize(value, entity_type)
        self.cache[cache_key] = llm_result
        return llm_result
```

#### Riesgo 3: Breaking Changes en Dependencias

**Probabilidad:** Media  
**Impacto:** Alto  
**Severidad:** ⚠️ MEDIO-ALTO

**Descripción:**
DSPy y LangGraph están en desarrollo activo. Breaking changes pueden romper Soni.

**Mitigación:**
1. **Version pinning estricto:**
   ```
   dspy>=3.0.4,<4.0.0
   langgraph>=1.0.0,<1.1.0
   langchain-core>=0.3.0,<0.4.0
   ```

2. **Tests de integración continuos:**
   ```python
   # tests/integration/test_dependencies.py
   def test_dspy_module_interface():
       """Verificar que dspy.Module API no ha cambiado"""
       assert hasattr(dspy.Module, 'forward')
       assert hasattr(dspy.Module, '__call__')
   
   def test_langgraph_streaming():
       """Verificar que streaming API funciona"""
       # ...
   ```

3. **Monitoring de repos:**
   - GitHub watch de stanfordnlp/dspy
   - GitHub watch de langchain-ai/langgraph
   - Alertas de nuevos releases

4. **Estrategia de actualización:**
   - Probar nuevas versiones en branch separada
   - Actualizar solo minor/patch, no major sin evaluación
   - Mantener changelog de compatibilidad

#### Riesgo 4: Over-Engineering

**Probabilidad:** Alta  
**Impacto:** Alto  
**Severidad:** ⚠️⚠️ ALTO

**Descripción:**
Tu arquitectura completa (ADR v1.3 → Soni v0.4.0) es ambiciosa. Riesgo de gastar 12 meses sin MVP funcional.

**Mitigación:**
✅ **IMPLEMENTACIÓN INCREMENTAL OBLIGATORIA**

Ver sección 5 (Roadmap Revisado) para plan detallado.

**Principios:**
1. **MVP First** - Funcionalidad antes que elegancia
2. **Validación Temprana** - Users reales cuanto antes
3. **Refactoring Iterativo** - No diseñes todo upfront
4. **Kill Your Darlings** - Si algo no aporta valor, elimínalo

---

### 4.2 Riesgos de Mercado

#### Riesgo 1: Rasa Pro Evoluciona Más Rápido

**Probabilidad:** Media  
**Impacto:** Medio  
**Severidad:** ⚠️ MEDIO

**Descripción:**
Rasa tiene equipo grande y funding. Pueden innovar más rápido.

**Mitigación:**
1. **Enfocarte en tu diferenciador:** Optimización automática
2. **Comunidad open source:** Contribuidores externos
3. **Nicho específico:** Devs que quieren control total + auto-optimization
4. **Velocidad de iteración:** Como solo eres tú, puedes pivotar rápido

#### Riesgo 2: Aparece Nuevo Competidor

**Probabilidad:** Media  
**Impacto:** Medio  
**Severidad:** ⚠️ MEDIO

**Descripción:**
Alguien más podría tener idea similar (DSPy + LangGraph framework).

**Mitigación:**
1. **Time to market:** Lanzar MVP rápido
2. **Documentación excellent:** Ser el más fácil de usar
3. **Casos de uso claros:** Ejemplos end-to-end que funcionen
4. **Comunidad:** Engagement activo, responsive a issues

---

## 5. Roadmap Revisado - Implementación Incremental

### Filosofía

⚠️ **NO IMPLEMENTES TODO A LA VEZ**

El ADR-001 (v1.3) define el estado final deseado, que se alcanzará en **Soni v1.0.0**. El camino para llegar debe ser **iterativo y validado**, pasando por versiones 0.1.0 → 0.4.0 antes del release estable.

### Estrategia de Versionado

**Principio:** La versión 1.0.0 solo se alcanzará cuando el ADR-001 esté **completamente implementado y validado**.

**Mapeo ADR → Versiones Soni:**
- **ADR v1.0 (Base):** Implementado en Soni v0.1.0 (MVP)
- **ADR v1.1 (Scoping + Normalization):** Implementado en Soni v0.2.0
- **ADR v1.2 (Step Compiler):** Implementado en Soni v0.3.0
- **ADR v1.3 (Zero-Leakage):** Implementado en Soni v0.4.0
- **ADR Completo + Validación:** Soni v1.0.0 (Stable Release)

**Versiones Pre-1.0:**
- `0.1.0` - Alpha: MVP funcional básico
- `0.2.0` - Beta: Performance y UX mejoradas
- `0.3.0` - Beta Avanzado: DSL Compiler completo
- `0.4.0` - Release Candidate: Arquitectura Zero-Leakage completa
- `1.0.0` - Stable: ADR completo, validado y listo para producción

### Resumen del Roadmap

| Fase | Versión | ADR Equivalente | Duración | Estado Objetivo |
|------|---------|-----------------|----------|-----------------|
| 1 | v0.1.0 | ADR v1.0 (Base) | 3 meses | MVP funcional |
| 2 | v0.2.0 | ADR v1.1 | 2 meses | Performance y UX |
| 3 | v0.3.0 | ADR v1.2 | 2 meses | DSL Compiler |
| 4 | v0.4.0 | ADR v1.3 | 3 meses | Zero-Leakage completo |
| 5 | v1.0.0 | ADR completo | 1-2 meses | Release estable |
| **Total** | | | **11-13 meses** | **ADR completamente implementado** |

### Fase 1: MVP Funcional → v0.1.0 (3 meses)

**Objetivo:** Sistema ToD básico funcional con optimización DSPy

**Versión Objetivo:** `0.1.0` (Alpha)

**Features Core:**
- ✅ SoniDU como `dspy.Module` con intent + entity extraction
- ✅ Optimización con MIPROv2 (solo light mode)
- ✅ LangGraph StateGraph manual (sin compiler)
- ✅ Steps lineales en YAML (sin condicionales)
- ✅ Persistencia SQLite básica (sync está ok para MVP)
- ✅ Actions hardcoded en Python (sin registry todavía)
- ✅ Validación básica con Pydantic

**YAML Simplificado (MVP):**
```yaml
version: "0.1"

settings:
  models:
    nlu:
      provider: openai
      model: gpt-4o-mini

flows:
  book_flight:
    description: "Book a flight"
    steps:
      - collect: origin
      - collect: destination
      - collect: date
      - action: search_flights
    
slots:
  origin:
    type: string
    prompt: "Which city are you flying from?"
  destination:
    type: string
    prompt: "Where do you want to go?"
  date:
    type: date
    prompt: "When do you want to travel?"

actions:
  search_flights:
    handler: "handlers.flights.search"  # Python path
```

**Criterios de Éxito:**
- [ ] Usuario puede tener conversación completa de booking
- [ ] Sistema es optimizable con MIPROv2
- [ ] Mejora medible en accuracy post-optimización
- [ ] Respuestas en <2 segundos

**Tiempo Estimado:** 2-3 meses (1 persona full-time)

**Deliverables:**
- Código en GitHub
- README con quickstart
- 1 ejemplo funcional end-to-end
- Tests básicos

---

### Fase 2: Performance y UX → v0.2.0 (2 meses)

**Objetivo:** Sistema production-ready con optimizaciones clave

**Versión Objetivo:** `0.2.0` (Beta)

**Features:**
- ✅ **Async Everything** - Migrar todo a async/await
- ✅ **Dynamic Scoping** - Filtrado de acciones por contexto
- ✅ **Normalization Layer** - Heurísticas + LLM correction
- ✅ **Streaming** - Tokens en tiempo real
- ✅ **FastAPI Integration** - REST API completa
- ✅ **Persistencia Async** - aiosqlite/asyncpg
- ✅ **SIMBA Optimizer** - Añadir como alternativa a MIPROv2

**Arquitectura:**
```python
# soni/core.py
class SoniDU(dspy.Module):
    async def acall(self, input: str, context: Context) -> Command:
        # Dynamic scoping
        relevant_actions = await self.scoper.get_relevant(context)
        
        # LLM call con contexto filtrado
        command = await self.predict(input, relevant_actions)
        
        # Normalization
        normalized = await self.normalizer.normalize(command)
        
        return normalized
```

**Criterios de Éxito:**
- [ ] Latencia p95 < 1.5s
- [ ] Streaming funcional en frontend
- [ ] API RESTful completa
- [ ] Soporte para 10+ conversaciones concurrentes

**Tiempo Estimado:** 1.5-2 meses

**Deliverables:**
- FastAPI endpoints documentados
- Ejemplo con frontend (React/Vue simple)
- Performance benchmarks
- Guía de deployment

---

### Fase 3: DSL Compiler → v0.3.0 (2 meses)

**Objetivo:** YAML procedural con Step Compiler

**Versión Objetivo:** `0.3.0` (Beta Avanzado)

**Features:**
- ✅ **Step Compiler** - YAML → StateGraph automático
- ✅ **Conditional Flows** - If/else, jumps
- ✅ **Loop Support** - Retry logic, confirmations
- ✅ **Graph Visualization** - Mermaid diagrams auto-generados
- ✅ **YAML Validation** - Schema completo con errores claros

**YAML Avanzado:**
```yaml
flows:
  book_flight:
    process:
      - step: collect_info
      - step: search_flights
        on_error:
          action: log_error
          next: ask_retry
      - step: confirm_booking
        conditions:
          - if: "price > 1000"
            action: escalate_to_human
          - else:
            next: process_payment
      - step: process_payment
        on_success: send_confirmation
        on_failure: 
          jump_to: payment_retry
```

**Implementación:**
```python
# soni/compiler.py
class StepCompiler:
    def compile(self, yaml_config: dict) -> CompiledGraph:
        # Parse y validar
        validated = self.validator.validate(yaml_config)
        
        # Build graph
        graph = StateGraph(DialogueState)
        
        for flow_name, flow_def in validated.flows.items():
            self._compile_flow(graph, flow_name, flow_def)
        
        return CompiledGraph(
            graph=graph,
            metadata=self._extract_metadata(yaml_config)
        )
    
    def _compile_flow(self, graph, flow_name, flow_def):
        steps = flow_def['process']
        
        for i, step in enumerate(steps):
            node_fn = self._create_node_fn(step)
            graph.add_node(f"{flow_name}_{i}", node_fn)
            
            if i > 0:
                self._add_edge(graph, steps[i-1], step)
        
        # Handle conditions
        for step in steps:
            if 'conditions' in step:
                self._add_conditional_edges(graph, step)
```

**Criterios de Éxito:**
- [ ] Compiler genera grafos válidos para 95% de casos de uso
- [ ] Errores de compilación son claros y accionables
- [ ] Visualización ayuda a debugging
- [ ] Documentación completa de sintaxis YAML

**Tiempo Estimado:** 2 meses

**Deliverables:**
- Compiler robusto con tests
- JSON Schema para YAML
- VSCode extension con autocomplete (nice-to-have)
- Tutorial completo de YAML DSL

---

### Fase 4: Zero-Leakage → v0.4.0 (3 meses)

**Objetivo:** Arquitectura hexagonal completa (ADR v1.3 completo)

**Versión Objetivo:** `0.4.0` (Release Candidate)

**Features:**
- ✅ **Action Registry** - Decoradores para actions
- ✅ **Validator Registry** - Validadores semánticos
- ✅ **Output Mapping** - Desacoplamiento de datos
- ✅ **Plugin System** - Extensibilidad
- ✅ **GEPA Optimizer** - State-of-the-art optimization

**Implementación:**
```python
# soni/registry.py
class ActionRegistry:
    _actions: Dict[str, Callable] = {}
    
    @classmethod
    def register(cls, name: str):
        def decorator(func: Callable):
            cls._actions[name] = func
            return func
        return decorator
    
    @classmethod
    def get(cls, name: str) -> Callable:
        if name not in cls._actions:
            raise ActionNotFoundError(f"Action '{name}' not registered")
        return cls._actions[name]

# Usage
from soni.registry import action

@action("search_flights")
async def search_flights(
    origin: str,
    destination: str,
    date: datetime
) -> FlightSearchResult:
    # Implementation
    pass
```

**YAML Final:**
```yaml
# Purely semantic - no technical details
actions:
  search_flights:
    description: "Search for available flights"
    params: [origin, destination, date]
    map_outputs:
      num_flights: flight_count
      options: flight_list
      cheapest_price: min_price

entities:
  - name: airport_code
    validators:
      - is_valid_iata  # Semantic, not regex
      - is_major_airport
```

**Criterios de Éxito:**
- [ ] 100% separación entre YAML y código
- [ ] Cambios en API externa no requieren cambio de YAML
- [ ] Analista de negocio puede editar YAML sin dev
- [ ] Sistema de plugins funcional

**Tiempo Estimado:** 2-3 meses

**Deliverables:**
- Sistema de registry completo
- Plugin examples
- Migración guide de v0.3.0 a v0.4.0
- Case study: integrando nueva API sin tocar YAML

---

### Fase 5: Release 1.0.0 - ADR Completo (1-2 meses)

**Objetivo:** Validación completa del ADR-001 y release estable

**Versión Objetivo:** `1.0.0` (Stable Release)

**Criterios para 1.0.0:**
- ✅ Todas las fases anteriores completadas (0.1.0 → 0.4.0)
- ✅ ADR-001 completamente implementado (todas las features v1.3)
- ✅ Tests de integración E2E pasando
- ✅ Documentación completa y revisada
- ✅ Al menos 1 caso de uso en producción
- ✅ Performance benchmarks cumplidos
- ✅ Sin bugs críticos conocidos

**Actividades:**
- Auditoría completa de código
- Security review
- Performance testing exhaustivo
- Documentación final
- Preparación de release notes
- Community outreach

**Tiempo Estimado:** 1-2 meses

**Deliverables:**
- Release 1.0.0 estable
- Release notes completos
- Migration guide desde 0.x
- Production deployment guide
- Community announcement

---

### Fase 6: Polish y Ecosystem (Post-1.0, Ongoing)

**Features:**
- 📚 Documentación profesional (docs site)
- 🎨 Ejemplos variados (travel, banking, support)
- 🔌 Integraciones (Slack, Discord, WhatsApp)
- 📊 Monitoring y observability (LangSmith)
- 🧪 Testing framework robusto
- 🎓 Tutorials y screencasts

---

## 6. Validaciones Técnicas Pre-Inicio

Antes de empezar desarrollo, ejecuta estos experimentos:

### 6.1 Validación DSPy Optimization

**Objetivo:** Verificar que optimización funciona para tu caso de uso

```python
# experiments/01_dspy_validation.py
import dspy
from dspy.teleprompt import MIPROv2

# 1. Define tu signature
class IntentExtraction(dspy.Signature):
    """Extract user intent and entities from message"""
    message = dspy.InputField()
    intent = dspy.OutputField(desc="User's intent (book_flight, cancel, ...)")
    entities = dspy.OutputField(desc="Extracted entities as JSON")

# 2. Create module
class SimpleNLU(dspy.Module):
    def __init__(self):
        self.predict = dspy.Predict(IntentExtraction)
    
    def forward(self, message):
        return self.predict(message=message)

# 3. Setup LM
lm = dspy.LM('openai/gpt-4o-mini')
dspy.configure(lm=lm)

# 4. Create trainset (mínimo 20 ejemplos)
trainset = [
    dspy.Example(
        message="I want to fly to Paris tomorrow",
        intent="book_flight",
        entities='{"destination": "Paris", "date": "tomorrow"}'
    ).with_inputs("message"),
    # ... más ejemplos
]

# 5. Define metric
def intent_accuracy(example, pred, trace=None):
    return example.intent == pred.intent

# 6. Optimize
teleprompter = MIPROv2(metric=intent_accuracy, auto="light")
optimized_nlu = teleprompter.compile(
    SimpleNLU(),
    trainset=trainset
)

# 7. Test
test_message = "Book me a flight to London"
result = optimized_nlu(message=test_message)
print(f"Intent: {result.intent}")
print(f"Entities: {result.entities}")

# 8. Compare before/after
baseline_nlu = SimpleNLU()
print("\n=== Baseline ===")
print(baseline_nlu(message=test_message))

print("\n=== Optimized ===")
print(optimized_nlu(message=test_message))
```

**Criterio de Éxito:**
- [ ] Optimización completa sin errores
- [ ] Mejora medible en accuracy (al menos +5%)
- [ ] Tiempo de optimización < 10 minutos

---

### 6.2 Validación LangGraph Streaming

**Objetivo:** Verificar streaming async con FastAPI

```python
# experiments/02_langgraph_streaming.py
from langgraph.graph import StateGraph, START, END
from typing_extensions import TypedDict
from fastapi import FastAPI
from fastapi.responses import StreamingResponse
import asyncio

# 1. Define state
class State(TypedDict):
    messages: list[str]
    response: str

# 2. Define async node
async def generate_response(state: State):
    # Simulate streaming LLM
    full_response = "This is a streaming response from LangGraph"
    chunks = full_response.split()
    
    response = ""
    for chunk in chunks:
        await asyncio.sleep(0.1)  # Simulate latency
        response += chunk + " "
    
    return {"response": response.strip()}

# 3. Build graph
graph = StateGraph(State)
graph.add_node("generate", generate_response)
graph.add_edge(START, "generate")
graph.add_edge("generate", END)
compiled_graph = graph.compile()

# 4. FastAPI integration
app = FastAPI()

@app.post("/chat/stream")
async def chat_stream(message: str):
    async def generate():
        async for chunk in compiled_graph.astream(
            {"messages": [message]},
            stream_mode="values"
        ):
            if "response" in chunk:
                yield f"data: {chunk['response']}\n\n"
    
    return StreamingResponse(
        generate(),
        media_type="text/event-stream"
    )

# 5. Test
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
```

**Criterio de Éxito:**
- [ ] Streaming funciona sin errores
- [ ] Chunks llegan en orden correcto
- [ ] Compatible con SSE (Server-Sent Events)

---

### 6.3 Validación Persistencia Async

**Objetivo:** Verificar checkpointing con aiosqlite

```python
# experiments/03_async_persistence.py
import aiosqlite
from langgraph.checkpoint.aiosqlite import AsyncSqliteSaver
from langgraph.graph import StateGraph, START, END

# 1. Setup checkpointer
async def test_persistence():
    async with AsyncSqliteSaver.from_conn_string("./test.db") as checkpointer:
        # 2. Create graph with checkpointing
        graph = StateGraph(State)
        graph.add_node("step1", lambda s: {"count": s.get("count", 0) + 1})
        graph.add_edge(START, "step1")
        graph.add_edge("step1", END)
        
        app = graph.compile(checkpointer=checkpointer)
        
        # 3. Run with thread_id for persistence
        config = {"configurable": {"thread_id": "test-conversation"}}
        
        result1 = await app.ainvoke({"count": 0}, config)
        print(f"First run: {result1}")
        
        # 4. Resume same conversation
        result2 = await app.ainvoke({}, config)
        print(f"Second run (resumed): {result2}")

asyncio.run(test_persistence())
```

**Criterio de Éxito:**
- [ ] Estado persiste entre invocaciones
- [ ] Múltiples conversaciones simultáneas funcionan
- [ ] No hay race conditions

---

## 7. Métricas de Éxito

### 7.1 Métricas Técnicas

**v0.1.0 - MVP (Fase 1):**
- [ ] Intent accuracy > 85% (post-optimization)
- [ ] Entity extraction F1 > 80%
- [ ] Latencia p95 < 3s
- [ ] 0 crashes en 100 conversaciones de prueba

**v0.2.0 - Performance (Fase 2):**
- [ ] Latencia p95 < 1.5s
- [ ] Throughput > 10 conversaciones/segundo
- [ ] Streaming latency to first token < 500ms
- [ ] Memory usage < 500MB por conversación

**v0.3.0 - DSL Compiler (Fase 3):**
- [ ] YAML compilation success rate > 95%
- [ ] Compiler errors son accionables (no stack traces crudos)
- [ ] Compiled graphs visualizables automáticamente

**v0.4.0 - Zero-Leakage (Fase 4):**
- [ ] 0 detalles técnicos en YAML
- [ ] Cambio de API externa no requiere cambio de YAML
- [ ] Plugin system funciona para 3+ casos de uso

**v1.0.0 - Release Estable (Fase 5):**
- [ ] Todas las métricas anteriores cumplidas
- [ ] Test coverage > 80%
- [ ] 0 bugs críticos conocidos
- [ ] Documentación 100% completa
- [ ] Al menos 1 deployment en producción validado

### 7.2 Métricas de Producto

**Adopción:**
- GitHub stars > 100 (6 meses post-launch)
- Contributors externos > 5 (1 año)
- Production deployments > 10 (1 año)

**Documentación:**
- Quickstart funcional en < 10 minutos
- 5+ ejemplos end-to-end
- API docs completa

**Comunidad:**
- Discord/Slack community activo
- Response time a issues < 48h
- Monthly blog posts / tutorials

---

## 8. Decisión Final y Recomendaciones

### 8.1 Veredicto de Viabilidad

**Rating Global: 8.5/10** ✅

| Dimensión | Score | Justificación |
|-----------|-------|---------------|
| **Fundamentos Técnicos** | 9/10 | DSPy + LangGraph son rock-solid |
| **Innovación** | 9/10 | Zero-Leakage + Auto-opt es único |
| **Viabilidad Comercial** | 7/10 | Nicho claro pero competido |
| **Complejidad** | 6/10 | Ambiciosa, riesgo de over-eng |
| **Time-to-Market** | 7/10 | MVP en 3 meses es factible |

### 8.2 Recomendaciones Críticas

#### ✅ MANTENER

1. **DSPy como pilar central** - Es tu diferenciador #1
2. **Zero-Leakage architecture** - Innovación arquitectónica clave
3. **Async-first** - Requisito para producción moderna
4. **100% Open Source** - Tu ventaja vs Rasa Pro

#### ⚠️ AJUSTAR

1. **Narrativa competitiva**
   - ❌ "Rasa está obsoleto"
   - ✅ "Soni elimina prompt engineering manual con optimización automática"

2. **Roadmap**
   - ❌ Implementar ADR completo (v1.3) de golpe
   - ✅ Fases incrementales (0.1.0 → 0.4.0 → 1.0.0) con validación

3. **Scope inicial**
   - ❌ Todos los features del ADR
   - ✅ MVP funcional → iterar basado en feedback

#### ❌ EVITAR

1. **Over-engineering prematuro** - Resiste la tentación de perfección
2. **Feature creep** - Mantén scope limitado hasta tener usuarios
3. **Competir directamente con Rasa Pro** - Son mercados diferentes

### 8.3 Plan de Acción Inmediato

**Semana 1-2: Validación Técnica**
```
☐ Ejecutar experimentos de validación (sección 6)
☐ Confirmar que DSPy optimization funciona para tu dominio
☐ Confirmar que LangGraph streaming cumple requisitos
☐ Documentar resultados
```

**Semana 3-4: Setup de Proyecto**
```
☐ Crear repo GitHub (soni-framework)
☐ Setup básico (poetry, pre-commit, testing)
☐ Definir arquitectura de paquetes
☐ Escribir ADR-002: Technology Stack Validation
```

**Mes 2-4: MVP Development (v0.1.0)**
```
☐ Implementar SoniDU (dspy.Module)
☐ Implementar LangGraph runtime básico
☐ YAML parser simple
☐ Ejemplo end-to-end funcional
☐ Tests básicos
```

**Mes 5: Alpha Release (v0.1.0)**
```
☐ Documentación básica
☐ Publicar v0.1.0 en GitHub
☐ Post en Reddit/HN
☐ Recoger feedback
☐ Planificar siguiente fase (v0.2.0)
```

### 8.4 Señales de Alerta (Stop Conditions)

Si durante desarrollo encuentras:

🛑 **STOP si:**
- DSPy optimization no mejora accuracy en tu dominio
- Latencia post-optimization es > 5s consistentemente
- Compiler YAML→Graph es imposiblemente complejo
- No puedes implementar MVP en 4 meses

⚠️ **REEVALUAR si:**
- Rasa Pro anuncia optimización automática
- Aparece competidor directo con funding
- Comunidad DSPy/LangGraph se fragmenta
- No hay interés tras alpha release

### 8.5 Conclusión Final

Tu ADR-001 es **técnicamente sólido y viable**. Las tecnologías que propones (DSPy, LangGraph) están maduras y en producción. Tu arquitectura Zero-Leakage es innovadora y resuelve problemas reales.

**Los ajustes necesarios son estratégicos, no técnicos:**
1. Reposicionar vs competencia (enfoque en auto-optimization)
2. Implementar incrementalmente (no todo de golpe)
3. Validar temprano con usuarios reales

**El proyecto tiene potencial de éxito si:**
- Ejecutas con disciplina el roadmap incremental (0.1.0 → 0.4.0 → 1.0.0)
- Mantienes el foco en diferenciadores clave
- Construyes comunidad activamente
- Iteras basado en feedback real
- No te apresuras a 1.0.0 sin completar todas las fases del ADR

**Mi recomendación:** ✅ **PROCEDER CON IMPLEMENTACIÓN**

El mercado de frameworks ToD open source tiene espacio para una alternativa moderna, developer-friendly, con optimización automática. Tu combinación de DSPy + LangGraph + Zero-Leakage es única.

**Roadmap Resumido:**
- **v0.1.0** (3 meses): MVP funcional
- **v0.2.0** (2 meses): Performance y UX
- **v0.3.0** (2 meses): DSL Compiler
- **v0.4.0** (3 meses): Zero-Leakage (ADR completo)
- **v1.0.0** (1-2 meses): Validación y release estable
- **Total estimado:** 11-13 meses hasta 1.0.0

---

## 9. Referencias y Fuentes

### Documentación Oficial Verificada

**DSPy:**
- https://dspy.ai/api/optimizers/MIPROv2/
- https://dspy.ai/api/optimizers/SIMBA/
- https://dspy.ai/api/optimizers/GEPA/overview/
- https://github.com/stanfordnlp/dspy

**LangGraph:**
- https://docs.langchain.com/oss/python/langgraph/streaming
- https://www.langchain.com/langgraph
- https://github.com/langchain-ai/langgraph

**Papers:**
- Khattab et al. (2024): "DSPy: Compiling Declarative Language Model Calls"
- Agrawal et al. (2025): "GEPA: Reflective Prompt Evolution Can Outperform RL"

### Análisis Competitivo

**Rasa:**
- https://rasa.com/docs/reference/config/components/llm-configuration
- https://rasa.com/docs/reference/changelogs/rasa-pro-changelog
- https://www.communeify.com/en/blog/what-is-rasa/

### Artículos y Blogs

- "Grokking MIPROv2 - the new optimizer from DSPy" (Langtrace)
- "Learning DSPy (3): Working with optimizers" (The Data Quarry, Oct 2025)
- "Building Real-Time AI Apps with LangGraph, FastAPI & Streamlit" (Medium)

---

## Apéndice A: Tabla de Decisiones Arquitecturales

| Decisión | Opción Elegida | Alternativas Consideradas | Justificación |
|----------|----------------|---------------------------|---------------|
| Framework de Optimización | DSPy | Prompt engineering manual, LangChain prompts | Auto-optimization, soporte para múltiples optimizadores |
| Runtime de Diálogo | LangGraph | Rasa, Custom state machine | Async nativo, streaming, checkpointing |
| Optimizador Principal | MIPROv2 | SIMBA, GEPA, BootstrapFewShot | Balance entre rendimiento y velocidad |
| Persistencia | SQLite/PostgreSQL async | Redis, Filesystem | Simplicidad (SQLite), escalabilidad (PostgreSQL) |
| API Framework | FastAPI | Flask, Django | Async nativo, validación automática, docs |
| DSL | YAML procedural | Python DSL, JSON, Custom | Legibilidad para no-programadores |

---

## Apéndice B: Glosario de Términos

**ToD (Task-oriented Dialogue):** Sistema de diálogo enfocado en completar tareas específicas (booking, support, etc.)

**DSPy:** Framework para programar (no promptear) LLMs con optimización automática

**MIPROv2:** Optimizador que usa Bayesian Optimization para encontrar mejores prompts

**SIMBA:** Optimizador introspectivo que analiza fallos del modelo

**GEPA:** Optimizador evolutivo con reflexión textual

**LangGraph:** Framework para construir aplicaciones stateful multi-actor con LLMs

**StateGraph:** Grafo de estados en LangGraph para control de flujo

**Zero-Leakage:** Arquitectura donde detalles técnicos no "filtran" al YAML semántico

**Dynamic Scoping:** Inyectar solo información relevante en contexto del LLM

**CALM:** Conversational AI with Language Models (arquitectura de Rasa Pro)

---

**Fin del Documento**

---

*Este análisis ha sido realizado con investigación actualizada al 29 de Noviembre de 2025. Se recomienda re-validar hallazgos críticos antes de decisiones mayores de arquitectura.*