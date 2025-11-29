## Backlog de Implementación - Soni Framework

**Fuente:** `docs/strategy/Implementation-Strategy.md`
**Alcance:** Hitos 0 a 22

> Nota: Este backlog organiza las tareas por hito.
> El detalle y explicación de cada elemento está en el documento de estrategia.

---

## Hito 0: Validación Técnica Pre-Desarrollo

- **Estado objetivo:** Validar tecnologías core (DSPy, LangGraph, persistencia async) antes de desarrollo extensivo.

- [ ] 0.1 Ejecutar experimento de validación DSPy (MIPROv2)
  - [ ] Implementar script `experiments/01_dspy_validation.py`
  - [ ] Preparar dataset mínimo para intents/entities
  - [ ] Ejecutar optimización MIPROv2 sin errores
  - [ ] Medir accuracy baseline vs optimizado (objetivo ≥ 5% mejora)
  - [ ] Medir tiempo de optimización (< 10 minutos)
  - [ ] Verificar que el módulo optimizado se puede serializar (`.save()`)
  - [ ] Documentar resultados y conclusiones

- [ ] 0.2 Ejecutar experimento de validación LangGraph Streaming
  - [ ] Implementar script `experiments/02_langgraph_streaming.py`
  - [ ] Crear ejemplo mínimo de grafo con streaming async
  - [ ] Integrar con FastAPI (endpoint de prueba)
  - [ ] Verificar que los chunks llegan en orden
  - [ ] Validar compatibilidad con SSE (Server-Sent Events)
  - [ ] Medir latencia de primer token (< 500ms)
  - [ ] Documentar resultados y conclusiones

- [ ] 0.3 Ejecutar experimento de validación de persistencia async
  - [ ] Implementar script `experiments/03_async_persistence.py`
  - [ ] Probar checkpointing con `aiosqlite`
  - [ ] Verificar persistencia de estado entre invocaciones
  - [ ] Probar múltiples conversaciones simultáneas
  - [ ] Verificar ausencia de race conditions
  - [ ] Medir performance por operación (< 100ms)
  - [ ] Documentar resultados y conclusiones

- [ ] 0.4 Redactar reporte de resultados y decisión GO/NO-GO
  - [ ] Consolidar métricas de los 3 experimentos
  - [ ] Evaluar cumplimiento de criterios de éxito
  - [ ] Documentar riesgos y alternativas
  - [ ] Registrar decisión GO/NO-GO en `docs/adr/` o similar

---

## Hito 1: Setup de Proyecto y Arquitectura Base

- **Estado objetivo:** Repositorio inicializado, estructura de paquetes y tooling básico funcionando.

- [ ] 1.1 Setup de repositorio
  - [ ] Crear repositorio GitHub `soni-framework`
  - [ ] Configurar `.gitignore` (Python, IDEs, OS)
  - [ ] Añadir licencia MIT
  - [ ] Crear README básico con visión del proyecto

- [ ] 1.2 Gestión de dependencias con `uv`
  - [ ] Ejecutar `uv init --lib soni` en la raíz del repo
  - [ ] Verificar creación de `pyproject.toml` y paquete bajo `src/soni/` (o estructura equivalente)
  - [ ] Añadir dependencias core con `uv add` (DSPy, LangGraph, FastAPI, etc.)
  - [ ] Añadir dependencias de desarrollo con `uv add --dev` (pytest, ruff, mypy, etc.)
  - [ ] Configurar version pinning estricto en `pyproject.toml`

- [ ] 1.3 Crear estructura de paquetes
  - [ ] Crear paquete `soni/core/` con `__init__.py`, `interfaces.py`, `state.py`, `errors.py`
  - [ ] Crear paquete `soni/du/` con `__init__.py`, `signatures.py`, `modules.py`
  - [ ] Crear paquete `soni/dm/` con `__init__.py`, `graph.py`
  - [ ] Crear paquete `soni/cli/` con `__init__.py`
  - [ ] Crear carpeta `tests/unit/` y `examples/flight_booking/`

- [ ] 1.4 Configurar tooling de desarrollo
  - [ ] Configurar pre-commit hooks con ruff y mypy
  - [ ] Configurar pytest y pytest-asyncio
  - [ ] Configurar coverage (target 60% para MVP)
  - [ ] Crear workflow básico de GitHub Actions (lint + tests)

- [ ] 1.5 Documentación inicial
  - [ ] Completar README con quickstart placeholder
  - [ ] Crear `CONTRIBUTING.md` básico
  - [ ] Crear `CHANGELOG.md` inicial

- [ ] 1.6 Validación de setup
  - [ ] Ejecutar `uv sync`
  - [ ] Ejecutar `uv run pytest tests/`
  - [ ] Ejecutar `uv run ruff check soni/`
  - [ ] Ejecutar `uv run mypy soni/`

---

## Hito 2: Core Interfaces y State Management

- **Estado objetivo:** Interfaces SOLID definidas y modelo de estado base funcional.

- [ ] 2.1 Definir protocolos en `soni/core/interfaces.py`
  - [ ] Definir `INLUProvider` (Protocol)
  - [ ] Definir `IDialogueManager` (Protocol)
  - [ ] Definir `INormalizer` (Protocol)
  - [ ] Definir `IScopeManager` (Protocol)
  - [ ] Asegurar métodos async donde aplique
  - [ ] Añadir type hints completos
  - [ ] Añadir docstrings a todos los métodos

- [ ] 2.2 Implementar `DialogueState` en `soni/core/state.py`
  - [ ] Definir `@dataclass DialogueState` con campos según estrategia
  - [ ] Evaluar inmutabilidad donde sea posible
  - [ ] Asegurar serialización a JSON
  - [ ] Añadir helpers para acceso común (mensajes, slots, etc.)

- [ ] 2.3 Definir excepciones de dominio en `soni/core/errors.py`
  - [ ] Implementar `SoniError` (base)
  - [ ] Implementar `NLUError`
  - [ ] Implementar `ValidationError`
  - [ ] Implementar `ActionNotFoundError`
  - [ ] Implementar `CompilationError`
  - [ ] Asegurar mensajes de error informativos y con contexto

- [ ] 2.4 Tests unitarios de core
  - [ ] Test de serialización de `DialogueState`
  - [ ] Test de protocolos con mocks
  - [ ] Test de jerarquía de excepciones

- [ ] 2.5 Validación de core
  - [ ] Verificar que las importaciones desde `soni.core` compilan sin errores
  - [ ] Ejecutar `mypy soni/core/` sin errores

---

## Hito 3: SoniDU - Módulo DSPy Base

- **Estado objetivo:** Módulo de Dialogue Understanding optimizable con DSPy.

- [ ] 3.1 Definir signature de DSPy en `soni/du/signatures.py`
  - [ ] Implementar `class DialogueUnderstanding(dspy.Signature)`
  - [ ] Definir `user_message`, `dialogue_history`, `current_slots`, `available_actions`, `current_flow` como `InputField`
  - [ ] Definir `structured_command`, `extracted_slots`, `confidence`, `reasoning` como `OutputField`
  - [ ] Añadir descripciones claras y type hints

- [ ] 3.2 Implementar `SoniDU` en `soni/du/modules.py`
  - [ ] Implementar clase `SoniDU(dspy.Module)`
  - [ ] Configurar `self.predictor = dspy.ChainOfThought(DialogueUnderstanding)`
  - [ ] Integrar `scope_manager` opcional
  - [ ] Implementar `forward()` (sync) para optimizadores
  - [ ] Implementar `aforward()` (async) para runtime
  - [ ] Implementar `async def predict(...) -> NLUResult` como wrapper

- [ ] 3.3 Definir `NLUResult` dataclass
  - [ ] Implementar dataclass con `command`, `slots`, `confidence`, `reasoning`
  - [ ] Asegurar type hints y docstrings

- [ ] 3.4 Tests de SoniDU
  - [ ] Test de `SoniDU.forward()` con mock de LM
  - [ ] Test de `SoniDU.aforward()` async
  - [ ] Test de integración con DSPy real (ej. `gpt-4o-mini`)
  - [ ] Test de serialización (`.save()` / `.load()`)

- [ ] 3.5 Validación manual
  - [ ] Configurar LM de ejemplo en DSPy
  - [ ] Ejecutar `SoniDU.aforward(...)` con un caso de booking
  - [ ] Verificar que `structured_command` y slots se completan

---

## Hito 4: Optimización DSPy (MIPROv2)

- **Estado objetivo:** Pipeline de optimización con MIPROv2 funcionando y medible.

- [ ] 4.1 Implementar métricas de evaluación en `soni/du/metrics.py`
  - [ ] Implementar `intent_accuracy_metric(example, prediction, trace=None) -> float`
  - [ ] Manejar casos edge (predicciones vacías, etc.)
  - [ ] Asegurar retorno en rango \[0.0, 1.0\]

- [ ] 4.2 Implementar pipeline de optimización en `soni/du/optimizers.py`
  - [ ] Implementar función `optimize_soni_du(...) -> SoniDU`
  - [ ] Soportar `optimizer_type="MIPROv2"` en modo light
  - [ ] Crear trainset desde YAML de triggers
  - [ ] Evaluar baseline vs optimized
  - [ ] Serializar módulo optimizado

- [ ] 4.3 Implementar CLI de optimización en `soni/cli/optimize.py`
  - [ ] Implementar comando `soni optimize`
  - [ ] Leer configuración desde YAML (`--config`)
  - [ ] Generar módulo optimizado (`--output`)
  - [ ] Mostrar métricas de mejora en consola

- [ ] 4.4 Tests de optimización
  - [ ] Test de métrica con ejemplos conocidos
  - [ ] Test de optimización con dataset pequeño
  - [ ] Test de serialización y carga de módulo optimizado

- [ ] 4.5 Validación de pipeline
  - [ ] Ejecutar `uv run soni optimize --config examples/flight_booking/soni.yaml`
  - [ ] Verificar que se genera el archivo optimizado
  - [ ] Cargar módulo optimizado desde código y probar predicciones

---

## Hito 5: YAML Parser y Configuración

- **Estado objetivo:** Parser y modelo de configuración YAML funcionando con validación básica.

- [ ] 5.1 Definir schema YAML simplificado (MVP)
  - [ ] Documentar ejemplo de YAML en `examples/flight_booking/soni.yaml`
  - [ ] Incluir secciones `version`, `settings.models.nlu`, `flows`, `slots`, `actions`

- [ ] 5.2 Implementar `ConfigLoader` en `soni/core/config.py`
  - [ ] Implementar `ConfigLoader.load(path: str) -> dict`
  - [ ] Implementar `ConfigLoader.validate(config: dict) -> List[ValidationError]`
  - [ ] Validar campos requeridos
  - [ ] Añadir mensajes de error claros
  - [ ] Soportar includes/imports básicos

- [ ] 5.3 Implementar modelo de configuración con Pydantic
  - [ ] Implementar `SoniConfig` y submodelos (`Settings`, `FlowConfig`, `SlotConfig`, `ActionConfig`)
  - [ ] Añadir type hints completos
  - [ ] Definir valores por defecto donde aplique

- [ ] 5.4 Tests de configuración
  - [ ] Test de carga de YAML válido
  - [ ] Test de detección de YAML inválido
  - [ ] Test de valores por defecto
  - [ ] Test de mensajes de error informativos

- [ ] 5.5 Validación de configuración
  - [ ] Cargar YAML de ejemplo con `ConfigLoader.load`
  - [ ] Verificar presencia de `version` y `flows` esperados

---

## Hito 6: LangGraph Runtime Básico

- **Estado objetivo:** Runtime básico capaz de ejecutar flujos lineales desde YAML.

- [ ] 6.1 Implementar `SoniGraphBuilder` en `soni/dm/graph.py`
  - [ ] Definir inicialización con `config: dict`
  - [ ] Crear `StateGraph(DialogueState)`
  - [ ] Implementar `build_manual()` para flujos lineales (`collect`, `action`)
  - [ ] Integrar checkpointing básico con SQLite

- [ ] 6.2 Implementar nodos del grafo
  - [ ] Implementar `async def understand_node(state: DialogueState) -> dict`
  - [ ] Implementar `async def collect_slot_node(state: DialogueState, slot_name: str) -> dict`
  - [ ] Implementar `async def action_node(state: DialogueState, action_name: str) -> dict`
  - [ ] Añadir manejo robusto de errores
  - [ ] Añadir logging para debugging

- [ ] 6.3 Implementar `ActionHandler` básico en `soni/actions/base.py`
  - [ ] Implementar `ActionHandler.execute(action_name: str, slots: dict) -> dict`
  - [ ] Cargar handler desde path de Python
  - [ ] Soportar funciones async
  - [ ] Manejar errores de import y ejecución

- [ ] 6.4 Tests de runtime básico
  - [ ] Test de construcción de grafo
  - [ ] Test de ejecución de flujo simple
  - [ ] Test de persistencia de estado
  - [ ] Test de manejo de errores

- [ ] 6.5 Validación de runtime
  - [ ] Construir grafo desde config de ejemplo
  - [ ] Ejecutar un flujo de booking simple end-to-end
  - [ ] Verificar que el estado final es coherente (`current_flow`, slots, etc.)

---

## Hito 7: Runtime Loop y FastAPI Integration

- **Estado objetivo:** API REST funcional para procesar mensajes usando el runtime.

- [ ] 7.1 Implementar `RuntimeLoop` en `soni/runtime.py`
  - [ ] Inicializar grafo, módulo DU y dependencias desde `config_path`
  - [ ] Soportar `optimized_du_path` opcional
  - [ ] Implementar `async def process_message(user_msg: str, user_id: str) -> str`
  - [ ] Manejar múltiples conversaciones y persistencia de estado

- [ ] 7.2 Implementar endpoints FastAPI en `soni/server/api.py`
  - [ ] Crear instancia `FastAPI()`
  - [ ] Implementar endpoint `POST /chat/{user_id}`
  - [ ] Implementar endpoint `GET /health`
  - [ ] Añadir manejo de errores con códigos HTTP adecuados

- [ ] 7.3 Implementar CLI de servidor en `soni/cli/server.py`
  - [ ] Implementar comando `soni server`
  - [ ] Opciones `--config`, `--host`, `--port`
  - [ ] Inicializar runtime y lanzar servidor FastAPI (uvicorn)

- [ ] 7.4 Tests de runtime + API
  - [ ] Test de `RuntimeLoop` con mensaje simple
  - [ ] Test de endpoints FastAPI con `TestClient`
  - [ ] Test de persistencia entre requests
  - [ ] Test de manejo de errores

- [ ] 7.5 Validación manual de API
  - [ ] Levantar servidor con `soni server`
  - [ ] Probar `/health`
  - [ ] Probar `/chat/{user_id}` con conversación simple

---

## Hito 8: Ejemplo End-to-End y Documentación MVP

- **Estado objetivo:** Ejemplo completo de booking y documentación mínima para terceros.

- [ ] 8.1 Crear ejemplo `examples/flight_booking/`
  - [ ] Definir `soni.yaml` con flujo completo de booking
  - [ ] Implementar `handlers.py` con actions (pueden ser mocks)
  - [ ] Crear `README.md` del ejemplo
  - [ ] Crear `test_conversation.md` con conversación de ejemplo

- [ ] 8.2 Documentación MVP
  - [ ] Completar `README.md` del proyecto con quickstart y visión
  - [ ] Crear `docs/quickstart.md` con guía paso a paso
  - [ ] Crear `docs/architecture.md` con arquitectura básica
  - [ ] Actualizar `CHANGELOG.md` con cambios relevantes

- [ ] 8.3 Tests de integración E2E
  - [ ] Implementar `tests/integration/test_e2e.py`
  - [ ] Cubrir flujo completo de booking
  - [ ] Usar configuración real del ejemplo

- [ ] 8.4 Validación E2E
  - [ ] Ejecutar quickstart desde cero siguiendo la documentación
  - [ ] Confirmar que el ejemplo funciona sin errores

---

## Hito 9: Release v0.1.0 (MVP)

- **Estado objetivo:** Publicar primera versión alpha del framework.

- [ ] 9.1 Preparación de release
  - [ ] Actualizar versión a `0.1.0` en `pyproject.toml`
  - [ ] Actualizar `CHANGELOG.md` con entrada para v0.1.0
  - [ ] Crear tag `v0.1.0` en Git
  - [ ] Redactar release notes en GitHub

- [ ] 9.2 Validación final
  - [ ] Ejecutar todos los tests (unitarios, integración, E2E)
  - [ ] Verificar coverage > 60%
  - [ ] Verificar que linting pasa
  - [ ] Verificar que type checking pasa
  - [ ] Validar que el ejemplo de booking funciona

- [ ] 9.3 Publicación
  - [ ] Construir paquete con `uv build`
  - [ ] Publicar en PyPI (opcional para alpha)
  - [ ] Crear release en GitHub
  - [ ] (Opcional) Publicar anuncio en canales externos

---

## Hito 10: Async Everything y Dynamic Scoping (v0.2.0)

- **Estado objetivo:** Todo el stack async y con scoping dinámico para acciones.

- [ ] 10.1 Migración a async
  - [ ] Asegurar persistencia async (aiosqlite)
  - [ ] Verificar que todos los nodos del grafo son async
  - [ ] Asegurar que los handlers son async
  - [ ] Ajustar tests a async donde corresponda

- [ ] 10.2 Implementar `ScopeManager` en `soni/core/scope.py`
  - [ ] Implementar `get_available_actions(self, state: DialogueState) -> List[str]`
  - [ ] Filtrar acciones por flujo actual
  - [ ] Incluir acciones globales siempre
  - [ ] Considerar slots completados para scoping
  - [ ] Añadir tests unitarios de scoping

- [ ] 10.3 Integración con `SoniDU`
  - [ ] Modificar SoniDU para usar acciones escopadas
  - [ ] Medir reducción de tokens
  - [ ] Medir impacto en accuracy

- [ ] 10.4 Validación de performance inicial
  - [ ] Medir reducción de tokens (> 30% objetivo)
  - [ ] Medir mejora de accuracy (> 5% objetivo)

---

## Hito 11: Normalization Layer (v0.2.0)

- **Estado objetivo:** Capa de normalización de datos previa a validación.

- [ ] 11.1 Implementar `SlotNormalizer` en `soni/du/normalizer.py`
  - [ ] Implementar método `normalize(self, value: Any, entity_config: Dict) -> Any`
  - [ ] Soportar estrategias básicas: trim, lowercase
  - [ ] Implementar estrategia de LLM correction async
  - [ ] Añadir cache de normalizaciones

- [ ] 11.2 Integrar normalizer en pipeline
  - [ ] Integrar normalización en el runtime loop antes de validación
  - [ ] Añadir logging de normalizaciones

- [ ] 11.3 Tests de normalización
  - [ ] Test de estrategias básicas
  - [ ] Test de LLM correction
  - [ ] Test de cache
  - [ ] Test de integración con runtime

- [ ] 11.4 Validación de impacto
  - [ ] Medir mejora en tasa de validación (> 10% objetivo)
  - [ ] Medir latencia adicional (< 200ms objetivo)

---

## Hito 12: Streaming y Performance (v0.2.0)

- **Estado objetivo:** Streaming de tokens y optimizaciones de performance.

- [ ] 12.1 Implementar streaming en `RuntimeLoop`
  - [ ] Implementar `process_message_stream(self, user_msg: str, user_id: str) -> AsyncGenerator[str, None]`
  - [ ] Asegurar compatibilidad con SSE
  - [ ] Optimizar para latencia de primer token < 500ms

- [ ] 12.2 Endpoint de streaming en FastAPI
  - [ ] Implementar `POST /chat/{user_id}/stream`
  - [ ] Usar `StreamingResponse` con formato SSE
  - [ ] Añadir tests de integración del endpoint

- [ ] 12.3 Optimizaciones de performance
  - [ ] Implementar connection pooling donde aplique
  - [ ] Añadir caching agresivo en puntos críticos
  - [ ] Evaluar batch processing donde tenga sentido

- [ ] 12.4 Tests de performance
  - [ ] Test de streaming (correctitud y orden)
  - [ ] Medir latencia p95
  - [ ] Medir throughput

---

## Hito 13: Release v0.2.0

- **Estado objetivo:** Versión beta con mejoras de performance publicada.

- [ ] 13.1 Preparación de release
  - [ ] Actualizar versión a `0.2.0`
  - [ ] Actualizar `CHANGELOG.md`
  - [ ] Redactar release notes

- [ ] 13.2 Validación final
  - [ ] Ejecutar batería completa de tests
  - [ ] Verificar cumplimiento de métricas de performance
  - [ ] Actualizar documentación asociada

- [ ] 13.3 Publicación
  - [ ] Publicar paquete actualizado
  - [ ] Crear release en GitHub

---

## Hito 14: Step Compiler (Parte 1 - Lineal) (v0.3.0)

- **Estado objetivo:** Compilador de steps lineales desde YAML a LangGraph.

- [ ] 14.1 Implementar `StepParser` en `soni/compiler/parser.py`
  - [ ] Implementar `parse(self, steps: List[dict]) -> List[Step]`
  - [ ] Parsea steps lineales desde YAML
  - [ ] Valida sintaxis básica
  - [ ] Añadir errores claros y accionables

- [ ] 14.2 Implementar `StepCompiler` en `soni/compiler/builder.py`
  - [ ] Implementar `compile(self, flow_name: str, steps: List[Step]) -> StateGraph`
  - [ ] Generar grafo lineal conectando nodos secuencialmente
  - [ ] Validar grafo resultante

- [ ] 14.3 Tests del compilador lineal
  - [ ] Test de parsing de steps
  - [ ] Test de compilación a grafo
  - [ ] Test de que el grafo generado es válido

---

## Hito 15: Step Compiler (Parte 2 - Condicionales) (v0.3.0)

- **Estado objetivo:** Soporte para branches, jumps y condicionales en el compilador.

- [ ] 15.1 Soporte de branches
  - [ ] Extender parser para steps de tipo `branch`
  - [ ] Generar `conditional_edges` en el grafo
  - [ ] Resolver saltos por caso (`success`, `error`, etc.)

- [ ] 15.2 Soporte de jumps
  - [ ] Implementar sintaxis `jump_to` explícita o implícita
  - [ ] Validar que los targets existan
  - [ ] Manejar loops de forma segura

- [ ] 15.3 Validación de grafo compilado
  - [ ] Detectar ciclos inválidos
  - [ ] Validar consistencia de todos los targets
  - [ ] Definir mensajes de error informativos

- [ ] 15.4 Tests del compilador con condicionales
  - [ ] Test de branches
  - [ ] Test de jumps
  - [ ] Test de validación de grafo
  - [ ] Test de detección de loops problemáticos

---

## Hito 16: Release v0.3.0

- **Estado objetivo:** Publicar versión con DSL Compiler completo.

- [ ] 16.1 Preparación de release
  - [ ] Actualizar versión a `0.3.0`
  - [ ] Documentar DSL y compilador en la documentación
  - [ ] Añadir ejemplos avanzados de flujos

- [ ] 16.2 Validación y publicación
  - [ ] Ejecutar suite de tests con enfoque en compiler
  - [ ] Publicar release y actualizar documentación

---

## Hito 17: Action Registry (Zero-Leakage Parte 1) (v0.4.0)

- **Estado objetivo:** Sistema de registro de acciones desacoplado del YAML.

- [ ] 17.1 Implementar `ActionRegistry` en `soni/actions/registry.py`
  - [ ] Implementar decorador `register(name: str)`
  - [ ] Implementar método `get(name: str) -> Callable`
  - [ ] Manejar errores cuando una acción no existe
  - [ ] Añadir tests unitarios del registry

- [ ] 17.2 Integrar registry en compiler/runtime
  - [ ] Modificar compiler para usar registry en lugar de paths directos
  - [ ] Validar que todas las acciones referenciadas están registradas
  - [ ] Producir errores claros cuando falten acciones

- [ ] 17.3 Ajustar YAML a semántica de acciones
  - [ ] Definir acciones en YAML sin detalles técnicos (solo contratos)
  - [ ] Validar consistencia entre YAML y registry

- [ ] 17.4 Tests de integración de acciones
  - [ ] Test de decorador y lookup
  - [ ] Test de flujo que usa ActionRegistry

---

## Hito 18: Validator Registry (Zero-Leakage Parte 2) (v0.4.0)

- **Estado objetivo:** Sistema de validadores semánticos desacoplado del YAML.

- [ ] 18.1 Implementar `ValidatorRegistry` en `soni/validation/registry.py`
  - [ ] Implementar decorador `register(name: str)`
  - [ ] Gestionar validadores por nombre
  - [ ] Añadir tests unitarios del registry

- [ ] 18.2 Integrar validadores en pipeline
  - [ ] Permitir que YAML referencie validadores por nombre semántico
  - [ ] Integrar validadores en el flujo de validación de slots
  - [ ] Producir errores claros cuando falten validadores

- [ ] 18.3 Tests de validación
  - [ ] Test de registro y uso de validadores
  - [ ] Test de integración en un flujo real

---

## Hito 19: Output Mapping (Zero-Leakage Parte 3) (v0.4.0)

- **Estado objetivo:** Mapeo de outputs desacoplando estructuras internas del YAML.

- [ ] 19.1 Implementar `map_outputs` en compiler
  - [ ] Extender lógica de creación de nodos de acción para soportar `map_outputs`
  - [ ] Garantizar que las variables resultantes queden planas en el estado
  - [ ] Validar mapeos y producir errores claros

- [ ] 19.2 Integración y tests
  - [ ] Ajustar compiler para respetar `map_outputs`
  - [ ] Añadir tests de mapeo de outputs
  - [ ] Verificar que cambios de estructura interna no rompen el YAML

---

## Hito 20: Release v0.4.0

- **Estado objetivo:** Publicar versión con arquitectura Zero-Leakage completa.

- [ ] 20.1 Preparación de release
  - [ ] Actualizar versión a `0.4.0`
  - [ ] Documentar Zero-Leakage en la documentación
  - [ ] Añadir ejemplos específicos de Zero-Leakage

- [ ] 20.2 Validación y publicación
  - [ ] Verificar que el YAML no contiene detalles técnicos
  - [ ] Ejecutar suite de tests completa
  - [ ] Publicar release y actualizar documentación

---

## Hito 21: Validación y Polish para v1.0.0

- **Estado objetivo:** Proyecto listo para release estable, alineado con el ADR.

- [ ] 21.1 Auditoría completa
  - [ ] Revisar ADR vs implementación
  - [ ] Crear checklist de features
  - [ ] Identificar y priorizar gaps

- [ ] 21.2 Testing exhaustivo
  - [ ] Aumentar coverage > 80%
  - [ ] Completar tests E2E
  - [ ] Ejecutar performance tests
  - [ ] Realizar security audit básica

- [ ] 21.3 Documentación final
  - [ ] Completar sitio de documentación
  - [ ] Generar API reference
  - [ ] Añadir tutoriales
  - [ ] Crear migration guide si aplica

- [ ] 21.4 Caso de uso real
  - [ ] Desplegar en un entorno de producción real o cercano
  - [ ] Validar con usuarios
  - [ ] Recoger métricas reales de uso, performance y errores

---

## Hito 22: Release v1.0.0

- **Estado objetivo:** Publicación de versión estable 1.0.0.

- [ ] 22.1 Preparación de release estable
  - [ ] Actualizar versión a `1.0.0`
  - [ ] Redactar release notes completos
  - [ ] Asegurar que la documentación está actualizada y accesible

- [ ] 22.2 Publicación y comunicación
  - [ ] Publicar en PyPI la versión estable
  - [ ] Crear release en GitHub
  - [ ] Preparar anuncio para la comunidad (blog post, etc.)
