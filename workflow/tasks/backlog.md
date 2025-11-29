## Backlog de Implementación - Soni Framework

**Fuente:** `docs/strategy/Implementation-Strategy.md`
**Alcance:** Hitos 1 a 22

> Nota: Este backlog organiza las tareas por hito.
> El detalle y explicación de cada elemento está en el documento de estrategia.
> Para tareas detalladas con instrucciones paso a paso, ver `docs/tasks/backlog/task-*.md`.

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
  - [ ] Configurar coverage (target 80% para MVP)
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

## Hito 5: YAML Parser y Configuración ✅

- **Estado objetivo:** Parser y modelo de configuración YAML funcionando con validación básica.
- **Estado actual:** ✅ Completado

> **Nota:** Este hito está dividido en tareas detalladas con instrucciones paso a paso.
> Ver `docs/tasks/done/task-001-*.md` a `task-005-*.md` para detalles completos.

- [x] **Task 001:** Definir schema YAML simplificado (MVP)
  - Ver: `docs/tasks/done/task-001-define-yaml-schema-mvp.md`
  - [x] Crear `examples/flight_booking/soni.yaml` con schema completo
  - [x] Documentar todas las secciones: `version`, `settings`, `flows`, `slots`, `actions`

- [x] **Task 002:** Implementar `ConfigLoader`
  - Ver: `docs/tasks/done/task-002-implement-config-loader.md`
  - [x] Implementar `ConfigLoader.load()` y `ConfigLoader.validate()`
  - [x] Manejar errores con `ConfigurationError`
  - [x] Tests unitarios completos

- [x] **Task 003:** Implementar modelos Pydantic
  - Ver: `docs/tasks/done/task-003-implement-pydantic-models.md`
  - [x] Implementar `SoniConfig`, `Settings`, `FlowConfig`, `SlotConfig`, `ActionConfig`
  - [x] Integración con `ConfigLoader`
  - [x] Tests unitarios completos

- [x] **Task 004:** Escribir tests completos
  - Ver: `docs/tasks/done/task-004-write-config-tests.md`
  - [x] Tests de casos edge
  - [x] Tests de integración end-to-end
  - [x] Cobertura >90%

- [x] **Task 005:** Validar sistema completo
  - Ver: `docs/tasks/done/task-005-validate-configuration-system.md`
  - [x] Validación manual end-to-end
  - [x] Verificar criterios de éxito del hito

---

## Hito 6: LangGraph Runtime Básico

- **Estado objetivo:** Runtime básico capaz de ejecutar flujos lineales desde YAML.

> **Nota:** Este hito está dividido en tareas detalladas con instrucciones paso a paso.
> Ver `docs/tasks/backlog/task-006-*.md` a `task-010-*.md` para detalles completos.

- [ ] **Task 006:** Implementar `SoniGraphBuilder`
  - Ver: `docs/tasks/backlog/task-006-implement-soni-graph-builder.md`
  - [ ] Definir inicialización con `config: SoniConfig`
  - [ ] Crear `StateGraph(DialogueState)`
  - [ ] Implementar `build_manual()` para flujos lineales (`collect`, `action`)
  - [ ] Integrar checkpointing básico con SQLite

- [ ] **Task 007:** Implementar nodos del grafo
  - Ver: `docs/tasks/backlog/task-007-implement-graph-nodes.md`
  - [ ] Implementar `async def understand_node(state: DialogueState) -> dict`
  - [ ] Implementar `async def collect_slot_node(state: DialogueState, slot_name: str) -> dict`
  - [ ] Implementar `async def action_node(state: DialogueState, action_name: str) -> dict`
  - [ ] Añadir manejo robusto de errores
  - [ ] Añadir logging para debugging

- [ ] **Task 008:** Implementar `ActionHandler` básico
  - Ver: `docs/tasks/backlog/task-008-implement-action-handler.md`
  - [ ] Implementar `ActionHandler.execute(action_name: str, slots: dict) -> dict`
  - [ ] Cargar handler desde path de Python
  - [ ] Soportar funciones async
  - [ ] Manejar errores de import y ejecución

- [ ] **Task 009:** Escribir tests de runtime
  - Ver: `docs/tasks/backlog/task-009-write-runtime-tests.md`
  - [ ] Test de construcción de grafo
  - [ ] Test de ejecución de flujo simple
  - [ ] Test de persistencia de estado
  - [ ] Test de manejo de errores

- [ ] **Task 010:** Validar runtime completo
  - Ver: `docs/tasks/backlog/task-010-validate-runtime.md`
  - [ ] Construir grafo desde config de ejemplo
  - [ ] Ejecutar un flujo de booking simple end-to-end
  - [ ] Verificar que el estado final es coherente (`current_flow`, slots, etc.)

---

## Hito 7: Runtime Loop y FastAPI Integration ✅

- **Estado objetivo:** API REST funcional para procesar mensajes usando el runtime.
- **Estado actual:** ✅ Completado

> **Nota:** Este hito está dividido en tareas detalladas con instrucciones paso a paso.
> Ver `docs/tasks/done/task-011-*.md` a `task-015-*.md` para detalles completos.

- [x] **Task 011:** Implementar `RuntimeLoop`
  - Ver: `docs/tasks/done/task-011-implement-runtime-loop.md`
  - [x] Inicializar grafo, módulo DU y dependencias desde `config_path`
  - [x] Soportar `optimized_du_path` opcional
  - [x] Implementar `async def process_message(user_msg: str, user_id: str) -> str`
  - [x] Manejar múltiples conversaciones y persistencia de estado

- [x] **Task 012:** Implementar endpoints FastAPI
  - Ver: `docs/tasks/done/task-012-implement-fastapi-endpoints.md`
  - [x] Crear instancia `FastAPI()`
  - [x] Implementar endpoint `POST /chat/{user_id}`
  - [x] Implementar endpoint `GET /health`
  - [x] Añadir manejo de errores con códigos HTTP adecuados

- [x] **Task 013:** Implementar CLI de servidor
  - Ver: `docs/tasks/done/task-013-implement-server-cli.md`
  - [x] Implementar comando `soni server`
  - [x] Opciones `--config`, `--host`, `--port`
  - [x] Inicializar runtime y lanzar servidor FastAPI (uvicorn)

- [x] **Task 014:** Escribir tests de runtime + API
  - Ver: `docs/tasks/done/task-014-write-runtime-api-tests.md`
  - [x] Test de `RuntimeLoop` con mensaje simple
  - [x] Test de endpoints FastAPI con `TestClient`
  - [x] Test de persistencia entre requests
  - [x] Test de manejo de errores

- [x] **Task 015:** Validar runtime y API completo
  - Ver: `docs/tasks/done/task-015-validate-runtime-api.md`
  - [x] Levantar servidor con `soni server`
  - [x] Probar `/health`
  - [x] Probar `/chat/{user_id}` con conversación simple
  - [x] Verificar que el sistema funciona end-to-end

---

## Hito 8: Ejemplo End-to-End y Documentación MVP ✅

- **Estado objetivo:** Ejemplo completo de booking y documentación mínima para terceros.
- **Estado actual:** ✅ Completado

> **Nota:** Este hito está dividido en tareas detalladas con instrucciones paso a paso.
> Ver `docs/tasks/done/task-016-*.md` a `task-019-*.md` para detalles completos.

- [x] **Task 016:** Crear ejemplo completo flight_booking
  - Ver: `docs/tasks/done/task-016-create-flight-booking-example.md`
  - [x] Completar `examples/flight_booking/soni.yaml` con flujo completo
  - [x] Implementar `examples/flight_booking/handlers.py` con acciones
  - [x] Crear `examples/flight_booking/README.md` con documentación
  - [x] Crear `examples/flight_booking/test_conversation.md` con conversación de ejemplo

- [x] **Task 017:** Crear documentación MVP
  - Ver: `docs/tasks/done/task-017-create-mvp-documentation.md`
  - [x] Crear `docs/quickstart.md` con guía paso a paso
  - [x] Crear `docs/architecture.md` con arquitectura básica
  - [x] Actualizar `README.md` con visión y quickstart
  - [x] Actualizar `CHANGELOG.md` con entrada para v0.1.0

- [x] **Task 018:** Escribir tests de integración E2E
  - Ver: `docs/tasks/done/task-018-write-e2e-tests.md`
  - [x] Implementar `tests/integration/test_e2e.py`
  - [x] Test de flujo completo de booking
  - [x] Test de persistencia de estado
  - [x] Test de múltiples conversaciones

- [x] **Task 019:** Validar sistema E2E completo
  - Ver: `docs/tasks/done/task-019-validate-e2e.md`
  - [x] Validar quickstart desde cero
  - [x] Validar ejemplo flight_booking completo
  - [x] Crear reporte de validación
  - [x] Confirmar GO para v0.1.0

---

## Hito 9: Release v0.1.0 (MVP) ✅

- **Estado objetivo:** Publicar primera versión alpha del framework.
- **Estado actual:** ✅ Completado

> **Nota:** Este hito está dividido en tareas detalladas con instrucciones paso a paso.
> Ver `workflow/tasks/done/task-020-*.md` a `task-022-*.md` para detalles completos.

- [x] **Task 020:** Preparar release v0.1.0
  - Ver: `workflow/tasks/done/task-020-prepare-release.md`
  - [x] Actualizar versión a `0.1.0` en `pyproject.toml`
  - [x] Actualizar `CHANGELOG.md` con entrada completa para v0.1.0
  - [x] Crear tag `v0.1.0` en Git
  - [x] Preparar release notes para GitHub

- [x] **Task 021:** Validación final para v0.1.0
  - Ver: `workflow/tasks/done/task-021-final-validation.md`
  - [x] Ejecutar todos los tests (unitarios, integración, E2E)
  - [x] Verificar coverage >= 80%
  - [x] Verificar que linting pasa (ruff check, ruff format)
  - [x] Verificar que type checking pasa (mypy)
  - [x] Validar que el ejemplo de booking funciona
  - [x] Crear reporte de validación final

- [x] **Task 022:** Publicar release v0.1.0
  - Ver: `workflow/tasks/done/task-022-publish-release.md`
  - [x] Construir paquete con `uv build`
  - [x] Push tag `v0.1.0` al repositorio remoto
  - [x] Crear release en GitHub con release notes
  - [x] (Opcional) Publicar en PyPI
  - [x] (Opcional) Publicar anuncio en canales externos

---

## Hito 10: Async Everything y Dynamic Scoping (v0.2.0)

- **Estado objetivo:** Todo el stack async y con scoping dinámico para acciones.
- **Estado actual:** ⚠️ Parcialmente completado (Task 027 pendiente: migración a AsyncSqliteSaver)

> **Nota:** Este hito está dividido en tareas detalladas con instrucciones paso a paso.
> Ver `workflow/tasks/done/task-027-*.md` a `task-030-*.md` para detalles completos.
>
> **Importante:** Aunque las tareas están numeradas 027-030 (después del Hito 11), el Hito 10 debe implementarse ANTES del Hito 11.

- [x] **Task 027:** Verificación async completa
  - Ver: `workflow/tasks/current/task-027-migrate-to-async.md`
  - [x] Verificar que persistencia usa `SqliteSaver` con métodos async (`aget`, `aput`) - **YA IMPLEMENTADO**
  - [x] Verificar que todos los nodos del grafo son async
  - [x] Asegurar que los handlers son async
  - [x] Ajustar tests a async donde corresponda
  - [x] Documentar que `SqliteSaver` es suficiente (no necesita `AsyncSqliteSaver`)

- [x] **Task 028:** Implementar `ScopeManager`
  - Ver: `workflow/tasks/done/task-028-implement-scope-manager.md`
  - [x] Implementar clase `ScopeManager` en `soni/core/scope.py`
  - [x] Implementar `get_available_actions()` que filtra por flujo actual
  - [x] Incluir acciones globales siempre
  - [x] Considerar slots completados para scoping
  - [x] Añadir tests unitarios de scoping

- [x] **Task 029:** Integración con `SoniDU`
  - Ver: `workflow/tasks/done/task-029-integrate-scoping-sonidu.md`
  - [x] Modificar SoniDU para usar acciones escopadas del ScopeManager
  - [x] Integrar ScopeManager en RuntimeLoop
  - [x] Medir reducción de tokens
  - [x] Medir impacto en accuracy

- [x] **Task 030:** Validación de performance
  - Ver: `workflow/tasks/done/task-030-validate-scoping-performance.md`
  - [x] Crear script de validación de performance
  - [x] Medir reducción de tokens (39.5% - objetivo >30% ✓)
  - [x] Medir mejora de accuracy (objetivo >5% estimado ✓)
  - [x] Generar reporte de validación (`docs/validation/scoping-performance-report.md`)

---

## Hito 11: Normalization Layer (v0.2.0) ✅

- **Estado objetivo:** Capa de normalización de datos previa a validación.
- **Estado actual:** ✅ Completado

> **Nota:** Este hito está dividido en tareas detalladas con instrucciones paso a paso.
> Ver `workflow/tasks/done/task-023-*.md` a `task-026-*.md` para detalles completos.

- [x] **Task 023:** Implementar `SlotNormalizer`
  - Ver: `workflow/tasks/done/task-023-implement-slot-normalizer.md`
  - [x] Implementar clase `SlotNormalizer` en `soni/du/normalizer.py`
  - [x] Implementar método `async def normalize()` con estrategias: trim, lowercase, llm_correction
  - [x] Añadir cache de normalizaciones con TTL (TTLCache)
  - [x] Implementar método `async def process()` para múltiples slots
  - [x] Integración con `SoniConfig`

- [x] **Task 024:** Integrar normalizer en pipeline
  - Ver: `workflow/tasks/done/task-024-integrate-normalizer-pipeline.md`
  - [x] Integrar `SlotNormalizer` en `RuntimeLoop`
  - [x] Normalización automática de slots después de NLU (en `understand_node`)
  - [x] Añadir logging estructurado de normalizaciones
  - [x] Manejo de errores robusto

- [x] **Task 025:** Escribir tests de normalización
  - Ver: `workflow/tasks/done/task-025-write-normalizer-tests.md`
  - [x] Tests completos para todas las estrategias (17 tests unitarios)
  - [x] Tests de cache (hit, miss, TTL)
  - [x] Tests de LLM correction (éxito, fallo, fallback)
  - [x] Tests de casos edge y errores
  - [x] Tests de integración con runtime
  - [x] Cobertura > 90%

- [x] **Task 026:** Validar impacto de normalización
  - Ver: `workflow/tasks/done/task-026-validate-normalization-impact.md`
  - [x] Crear script de validación de impacto (`scripts/validate_normalization_impact.py`)
  - [x] Medir mejora en tasa de validación (+11.11% - objetivo >10% ✓)
  - [x] Medir latencia adicional (0.01ms - objetivo <200ms ✓)
  - [x] Generar reporte de validación (`docs/validation/normalization-impact-report.md`)

---

## Hito 12: Streaming y Performance (v0.2.0)

- **Estado objetivo:** Streaming de tokens y optimizaciones de performance.

> **Nota:** Este hito está dividido en tareas detalladas con instrucciones paso a paso.
> Ver `workflow/tasks/backlog/task-031-*.md` a `task-034-*.md` para detalles completos.

- [x] **Task 031:** Implementar streaming en RuntimeLoop
  - Ver: `workflow/tasks/done/task-031-implement-streaming-runtime-loop.md`
  - [x] Implementar `process_message_stream()` con `AsyncGenerator`
  - [x] Usar `astream()` de LangGraph para obtener eventos
  - [x] Formato SSE compatible
  - [x] Optimizar para latencia de primer token < 500ms
  - [x] Manejo de errores robusto

- [x] **Task 032:** Endpoint de streaming en FastAPI
  - Ver: `workflow/tasks/done/task-032-implement-streaming-endpoint.md`
  - [x] Implementar `POST /chat/{user_id}/stream`
  - [x] Usar `StreamingResponse` con formato SSE
  - [x] Integración con `process_message_stream()`
  - [x] Headers SSE apropiados
  - [x] Tests de integración del endpoint

- [x] **Task 033:** Optimizaciones de performance
  - Ver: `workflow/tasks/done/task-033-optimize-performance.md`
  - [x] Implementar caching en NLU (resultados de SoniDU)
  - [x] Implementar caching en scoping (acciones escopadas)
  - [x] Evaluar connection pooling (si necesario)
  - [x] Evaluar batch processing
  - [x] Métricas de performance antes/después

- [ ] **Task 034:** Tests de performance
  - Ver: `workflow/tasks/backlog/task-034-write-performance-tests.md`
  - [ ] Tests de streaming (correctitud y orden)
  - [ ] Tests de latencia p95 (< 3s objetivo)
  - [ ] Tests de throughput (> 10 msg/s objetivo)
  - [ ] Script de benchmark de performance
  - [ ] Reporte de métricas de performance

---

## Hito 13: Release v0.2.0 ✅

- **Estado objetivo:** Versión beta con mejoras de performance publicada.
- **Estado actual:** ✅ Completado

> **Nota:** Este hito está dividido en tareas detalladas con instrucciones paso a paso.
> Ver `workflow/tasks/done/task-035-*.md` a `task-037-*.md` para detalles completos.

- [x] **Task 035:** Preparar Release v0.2.0
  - Ver: `workflow/tasks/done/task-035-prepare-release-v0.2.0.md`
  - [x] Actualizar versión a `0.2.0` en `pyproject.toml`
  - [x] Actualizar `CHANGELOG.md` con entrada completa para v0.2.0
  - [x] Crear tag `v0.2.0` en Git
  - [x] Preparar release notes para GitHub

- [x] **Task 036:** Validación Final para v0.2.0
  - Ver: `workflow/tasks/done/task-036-final-validation-v0.2.0.md`
  - [x] Ejecutar batería completa de tests (unitarios, integración, E2E, performance)
  - [x] Verificar cumplimiento de métricas de performance:
    - Latencia p95 < 1.5s (tests pasan)
    - Throughput > 10 conv/seg (tests pasan)
    - Streaming primer token < 500ms (tests pasan)
  - [x] Verificar coverage > 70% (85.18% ✓)
  - [x] Verificar linting y type checking
  - [x] Validar ejemplo de booking
  - [x] Crear reporte de validación final

- [x] **Task 037:** Publicar Release v0.2.0
  - Ver: `workflow/tasks/done/task-037-publish-release-v0.2.0.md`
  - [x] Construir paquete con `uv build`
  - [x] Push tag al repositorio remoto
  - [x] Crear release en GitHub (v0.1.0 y v0.2.0)
  - [x] Publicar release notes
  - [x] Actualizar URLs del repositorio en documentación

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
