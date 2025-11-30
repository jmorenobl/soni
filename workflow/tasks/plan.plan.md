<!-- 50d34630-76d1-4281-9081-3e7198473d0d 5b4dc29b-6349-4b9b-9247-a6c2b578e692 -->
# Plan de Ejecución - Backlog Soni Framework

## Visión General

Este plan organiza la ejecución de **23 hitos** (0-22) del backlog, desde validación técnica pre-desarrollo hasta release estable v1.0.0. La estrategia sigue un enfoque **MVP First** con validación continua.

**Duración Total Estimada:** 11-13 meses
**Fuente:** `docs/tasks/backlog.md` y `docs/strategy/Implementation-Strategy.md`

---

## Fase 0: Validación Técnica (CRÍTICA - Hacer Primero)

### Hito 0: Validación Técnica Pre-Desarrollo

**Duración:** 1-2 semanas | **Bloqueador:** Sí

**Tareas:**

- **0.1** Experimento DSPy (MIPROv2): Validar optimización, accuracy ≥5%, tiempo <10min
- **0.2** Experimento LangGraph Streaming: Validar streaming async, latencia <500ms, SSE compatible
- **0.3** Experimento Persistencia Async: Validar aiosqlite, concurrencia, performance <100ms
- **0.4** Reporte GO/NO-GO: Consolidar métricas y tomar decisión

**Archivos clave:**

- Scripts: `experiments/01_dspy_validation.py`, `02_langgraph_streaming.py`, `03_async_persistence.py`

**Criterio de éxito:** Las 3 validaciones pasan con métricas dentro de umbrales → **GO** para continuar

---

## Fase 1: MVP (v0.1.0) - 3 meses

### Hito 1: Setup de Proyecto y Arquitectura Base

**Duración:** 1 semana | **Dependencias:** Hito 0 (GO)

- Setup repositorio GitHub, `.gitignore`, licencia MIT
- Gestión dependencias con `uv` (`pyproject.toml`, version pinning)
- Estructura paquetes: `soni/core/`, `soni/du/`, `soni/dm/`, `soni/cli/`
- Tooling: pre-commit, pytest, ruff, mypy, GitHub Actions
- Documentación inicial: README, CONTRIBUTING, CHANGELOG

### Hito 2: Core Interfaces y State Management

**Duración:** 1 semana | **Dependencias:** Hito 1

- Protocolos SOLID en `soni/core/interfaces.py`: `INLUProvider`, `IDialogueManager`, `INormalizer`, `IScopeManager`
- `DialogueState` dataclass en `soni/core/state.py` (serializable a JSON)
- Excepciones dominio en `soni/core/errors.py`
- Tests unitarios de core

### Hito 3: SoniDU - Módulo DSPy Base

**Duración:** 2 semanas | **Dependencias:** Hito 2

- Signature DSPy en `soni/du/signatures.py`: `DialogueUnderstanding`
- Módulo `SoniDU(dspy.Module)` en `soni/du/modules.py` con `forward()` (sync) y `aforward()` (async)
- `NLUResult` dataclass
- Tests con mock LM e integración real

### Hito 4: Optimización DSPy (MIPROv2)

**Duración:** 1 semana | **Dependencias:** Hito 3

- Métricas evaluación en `soni/du/metrics.py`: `intent_accuracy_metric()`
- Pipeline optimización en `soni/du/optimizers.py`: `optimize_soni_du()` con MIPROv2
- CLI `soni optimize` en `soni/cli/optimize.py`
- Tests de optimización y serialización

### Hito 5: YAML Parser y Configuración

**Duración:** 1 semana | **Dependencias:** Hito 4

- Schema YAML MVP documentado en `examples/flight_booking/soni.yaml`
- `ConfigLoader` en `soni/core/config.py` con validación
- Modelos Pydantic: `SoniConfig`, `Settings`, `FlowConfig`, `SlotConfig`, `ActionConfig`
- Tests de carga y validación

### Hito 6: LangGraph Runtime Básico

**Duración:** 2 semanas | **Dependencias:** Hitos 3, 5

- `SoniGraphBuilder` en `soni/dm/graph.py` para construcción manual de grafos
- Nodos async: `understand_node()`, `collect_slot_node()`, `action_node()`
- `ActionHandler` básico en `soni/actions/base.py`
- Tests de runtime y persistencia

### Hito 7: Runtime Loop y FastAPI Integration

**Duración:** 1 semana | **Dependencias:** Hito 6

- `RuntimeLoop` en `soni/runtime.py` con `process_message()`
- Endpoints FastAPI en `soni/server/api.py`: `POST /chat/{user_id}`, `GET /health`
- CLI `soni server` en `soni/cli/server.py`
- Tests de runtime + API

### Hito 8: Ejemplo End-to-End y Documentación MVP

**Duración:** 1 semana | **Dependencias:** Hito 7

> **Nota:** Este hito está dividido en tareas detalladas (Task 016-019).
> Ver `docs/tasks/backlog/task-016-*.md` a `task-019-*.md` para detalles completos.

- **Task 016:** Ejemplo completo `examples/flight_booking/` con `soni.yaml`, `handlers.py`, README, `test_conversation.md`
- **Task 017:** Documentación: `docs/quickstart.md`, `docs/architecture.md`, README actualizado, CHANGELOG
- **Task 018:** Tests E2E en `tests/integration/test_e2e.py` con flujo completo
- **Task 019:** Validación E2E completa y reporte de validación

### Hito 9: Release v0.1.0 (MVP)

**Duración:** 3 días | **Dependencias:** Hito 8

> **Nota:** Este hito está dividido en tareas detalladas (Task 020-022).
> Ver `docs/tasks/backlog/task-020-*.md` a `task-022-*.md` para detalles completos.

- **Task 020:** Preparar release (versión, CHANGELOG, tag, release notes)
- **Task 021:** Validación final (tests, coverage, linting, type checking, ejemplo)
- **Task 022:** Publicar release (build, GitHub, PyPI opcional)

**Métricas MVP:** Intent accuracy >85%, latencia p95 <3s, 0 crashes en 100 conversaciones

---

## Fase 2: Performance y Optimizaciones (v0.2.0) - 2 meses

### Hito 10: Async Everything y Dynamic Scoping

**Duración:** 2 semanas | **Dependencias:** Hito 9

- Migración completa a async (persistencia, nodos, handlers)
- `ScopeManager` en `soni/core/scope.py` para filtrado dinámico de acciones
- Integración con `SoniDU` para reducir tokens (>30%) y mejorar accuracy (>5%)

### Hito 11: Normalization Layer

**Duración:** 1 semana | **Dependencias:** Hito 10

- `SlotNormalizer` en `soni/du/normalizer.py` con estrategias: trim, lowercase, LLM correction
- Integración en pipeline antes de validación
- Cache de normalizaciones

### Hito 12: Streaming y Performance

**Duración:** 1 semana | **Dependencias:** Hito 11

- Streaming en `RuntimeLoop`: `process_message_stream()` con SSE
- Endpoint `POST /chat/{user_id}/stream` en FastAPI
- Optimizaciones: connection pooling, caching, batch processing
- Tests de streaming y performance

### Hito 13: Release v0.2.0

**Duración:** 3 días | **Dependencias:** Hito 12

- Versionar `0.2.0`, actualizar CHANGELOG, release notes
- Validación métricas: latencia p95 <1.5s, throughput >10 conv/seg, streaming <500ms

---

## Fase 3: DSL Compiler (v0.3.0) - 2 meses

### Hito 14: Step Compiler (Parte 1 - Lineal)

**Duración:** 2 semanas | **Dependencias:** Hito 13

- `StepParser` en `soni/compiler/parser.py` para steps lineales
- `StepCompiler` en `soni/compiler/builder.py` para generar grafos lineales
- Tests de parsing y compilación

### Hito 15: Step Compiler (Parte 2 - Condicionales)

**Duración:** 2 semanas | **Dependencias:** Hito 14

- Soporte branches y `conditional_edges`
- Soporte jumps (`jump_to`) con validación de targets
- Validación de grafo: detección ciclos, consistencia
- Tests de branches, jumps, validación

### Hito 16: Release v0.3.0

**Duración:** 3 días | **Dependencias:** Hito 15

- Versionar `0.3.0`, documentar DSL, ejemplos avanzados
- Validación: compilation success >95%, errores accionables

---

## Fase 4: Zero-Leakage Architecture (v0.4.0) - 3 meses

### Hito 17: Action Registry (Zero-Leakage Parte 1)

**Duración:** 2 semanas | **Dependencias:** Hito 16

- `ActionRegistry` en `soni/actions/registry.py` con decorador `@register()`
- Integración en compiler para desacoplar YAML de implementación
- YAML semántico sin detalles técnicos

### Hito 18: Validator Registry (Zero-Leakage Parte 2)

**Duración:** 1 semana | **Dependencias:** Hito 17

- `ValidatorRegistry` en `soni/validation/registry.py`
- Integración en pipeline de validación
- YAML sin regex, solo nombres semánticos

### Hito 19: Output Mapping (Zero-Leakage Parte 3)

**Duración:** 1 semana | **Dependencias:** Hito 18

- `map_outputs` en compiler para desacoplar estructuras de datos
- Variables planas en estado
- Validación de mapeos

### Hito 20: Release v0.4.0

**Duración:** 3 días | **Dependencias:** Hito 19

- Versionar `0.4.0`, documentar Zero-Leakage
- Validación: 0 detalles técnicos en YAML, cambios API no requieren cambio YAML

---

## Fase 5: Validación y Release Stable (v1.0.0) - 1-2 meses

### Hito 21: Validación y Polish para v1.0.0

**Duración:** 1-2 meses | **Dependencias:** Hito 20

- Auditoría completa: revisar ADR vs implementación, checklist features
- Testing exhaustivo: coverage >80%, tests E2E, performance tests, security audit
- Documentación final: docs site, API reference, tutoriales, migration guide
- Caso de uso real: deployment producción, validación usuarios, métricas reales

### Hito 22: Release v1.0.0

**Duración:** 1 semana | **Dependencias:** Hito 21

- Versionar `1.0.0`, release notes completos
- Publicación PyPI estable, GitHub Release, community announcement

---

## Principios de Ejecución

1. **Validación Temprana:** Hito 0 es bloqueador crítico - no avanzar sin GO
2. **Dependencias Estrictas:** No iniciar hito hasta que dependencias estén completadas
3. **Definition of Done:** Cada hito requiere código, tests, documentación y validación
4. **Iteración Incremental:** MVP primero, luego mejoras incrementales
5. **Gestión de Riesgos:** Identificar bloqueadores temprano, tener alternativas

## Tracking y Métricas

- **Por Hito:** Criterios de éxito medibles definidos en backlog
- **Por Versión:** Métricas específicas (accuracy, latencia, coverage)
- **Continuo:** CI/CD con tests automáticos, linting, type checking

## Archivos de Referencia

- Backlog principal: `docs/tasks/backlog.md`
- Tareas detalladas: `docs/tasks/backlog/task-*.md`
- Estrategia: `docs/strategy/Implementation-Strategy.md`
- ADR: `docs/adr/ADR-001-Soni-Framework-Architecture.md`

### To-dos

- [x] Hito 0: Validación Técnica Pre-Desarrollo - Ejecutar 3 experimentos (DSPy, LangGraph, Persistencia) y reporte GO/NO-GO
- [x] Hito 1: Setup de Proyecto - Repositorio, dependencias con uv, estructura paquetes, tooling, documentación inicial
- [x] Hito 2: Core Interfaces y State - Protocolos SOLID, DialogueState, excepciones dominio, tests
- [x] Hito 3: SoniDU Module - Signature DSPy, módulo optimizable con forward/aforward, NLUResult, tests
- [x] Hito 4: Optimización DSPy - Métricas evaluación, pipeline MIPROv2, CLI optimize, tests
- [x] Hito 5: YAML Parser - Schema MVP, ConfigLoader, modelos Pydantic, validación, tests
- [x] Hito 6: LangGraph Runtime Básico - SoniGraphBuilder, nodos async, ActionHandler, tests
- [x] Hito 7: Runtime Loop y FastAPI - RuntimeLoop, endpoints REST, CLI server, tests
- [x] Hito 8: Ejemplo E2E y Docs MVP - Task 016 (ejemplo), Task 017 (docs), Task 018 (tests E2E), Task 019 (validación)
- [x] Hito 9: Release v0.1.0 MVP - Versionar, validación final, publicación PyPI/GitHub
- [x] Hito 10: Async Everything y Scoping - Migración async completa, ScopeManager, integración SoniDU
  - [x] Task 027: Implementación AsyncSqliteSaver - Migrado de SqliteSaver a AsyncSqliteSaver para soporte async completo
  - [x] Task 028: ScopeManager implementado
  - [x] Task 029: Integración con SoniDU completada
  - [x] Task 030: Validación de performance completada (39.5% reducción tokens ✓)
- [x] Hito 11: Normalization Layer - SlotNormalizer, integración pipeline, tests completos, validación impacto
  - [x] Task 023: SlotNormalizer implementado (trim, lowercase, llm_correction, cache TTL)
  - [x] Task 024: Integración en pipeline (RuntimeLoop, understand_node)
  - [x] Task 025: Tests completos (17 tests unitarios + integración)
  - [x] Task 026: Validación de impacto completada (+11.11% validación, 0.01ms latencia ✓)
- [x] Hito 12: Streaming y Performance - Streaming SSE, endpoint /stream, optimizaciones, tests
  - [x] Task 031: Implementar streaming en RuntimeLoop (process_message_stream, SSE, <500ms primer token)
  - [x] Task 032: Endpoint de streaming en FastAPI (POST /chat/{user_id}/stream, StreamingResponse)
  - [x] Task 033: Optimizaciones de performance (caching NLU/scoping, connection pooling, batch)
  - [x] Task 034: Tests de performance (streaming, latencia p95, throughput, benchmark)
- [x] Hito 13: Release v0.2.0 - Versionar, validación métricas performance, publicación
  - [x] Task 035: Preparar Release v0.2.0 (versión, CHANGELOG, tag, release notes)
  - [x] Task 036: Validación Final para v0.2.0 (tests, coverage 85%, métricas performance)
  - [x] Task 037: Publicar Release v0.2.0 (build, GitHub releases v0.1.0 y v0.2.0)
- [ ] Hito 14: Step Compiler Parte 1 - StepParser lineal, StepCompiler, tests parsing/compilación
  - [ ] Task 054: Implementar StepParser para parsing de steps lineales
  - [ ] Task 055: Implementar StepCompiler para generar grafos lineales
  - [ ] Task 056: Tests del compilador lineal
- [ ] Hito 15: Step Compiler Parte 2 - Branches, jumps, validación grafo, tests condicionales
  - [ ] Task 057: Soporte de branches en el compilador
  - [ ] Task 058: Soporte de jumps en el compilador
  - [ ] Task 059: Validación de grafo compilado
  - [ ] Task 060: Tests del compilador con condicionales
- [ ] Hito 16: Release v0.3.0 - Versionar, documentar DSL, ejemplos avanzados, publicación
- [ ] Hito 17: Action Registry - ActionRegistry con decorador, integración compiler, YAML semántico
- [ ] Hito 18: Validator Registry - ValidatorRegistry, integración pipeline, YAML sin regex
- [ ] Hito 19: Output Mapping - map_outputs en compiler, variables planas, validación mapeos
- [ ] Hito 20: Release v0.4.0 - Versionar, documentar Zero-Leakage, validación arquitectura
- [ ] Hito 21: Validación y Polish v1.0.0 - Auditoría completa, testing exhaustivo, docs final, caso uso real
- [ ] Hito 22: Release v1.0.0 - Versionar estable, release notes, publicación PyPI, community announcement
