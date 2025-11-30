# Registro de Decisión de Arquitectura

## ADR-003: Refactoring Arquitectónico v0.3.0

**Proyecto:** Soni - Framework Open Source para Asistentes Conversacionales
**Fecha:** Diciembre 2025
**Estado:** Aprobado
**Autor:** Jorge - AI Solutions Architect
**Versión:** 1.0

---

## Resumen Ejecutivo

Este ADR documenta el refactoring arquitectónico realizado en v0.3.0 para resolver deuda técnica crítica identificada en el code review del Hito 13. El refactoring implementa Dependency Injection consistente, elimina "God Objects", y establece una arquitectura más modular y testeable.

**Resultados:**
- Dependency Inversion: 0% → 100%
- God Objects: 2 → 0
- Complejidad ciclomática: Reducida significativamente
- Cobertura de tests: Mantenida >80%

---

## Contexto

### Problemas Identificados

El code review del Hito 13 identificó problemas críticos:

1. **Dependency Inversion Violado Sistemáticamente** (CRÍTICO 1)
   - Constructores creaban dependencias directamente
   - Imposible mockear para tests
   - Acoplamiento fuerte entre módulos

2. **State Contaminado con Config** (CRÍTICO 2)
   - `DialogueState` contaminado con `config` en runtime
   - Hack temporal que violaba separación de concerns
   - Problemas de serialización

3. **God Objects** (CRÍTICO 5)
   - `SoniGraphBuilder`: 827 líneas, múltiples responsabilidades
   - `RuntimeLoop`: 405 líneas, múltiples responsabilidades

4. **Módulos Vacíos** (CRÍTICO 4)
   - `validation/` vacío (validators no implementados)
   - `actions/` sin registry (paths directos en YAML)

5. **Problemas de Calidad**
   - Bare exception handlers sin logging
   - Alta complejidad ciclomática
   - Type hints con `Any` evitables

---

## Decisiones Tomadas

### 1. Dependency Injection Consistente

**Decisión:** Todos los constructores aceptan Protocols como parámetros opcionales, con fallback a implementaciones por defecto.

**Implementación:**
- `RuntimeLoop` acepta `IScopeManager`, `INormalizer`, `INLUProvider`, `IActionHandler`
- `SoniGraphBuilder` acepta las mismas interfaces
- Nodos del grafo usan dependencias inyectadas via closures

**Resultado:**
- 100% Dependency Inversion
- Tests pueden mockear todas las dependencias
- Intercambio de implementaciones sin modificar código

### 2. RuntimeContext para Separar State/Config

**Decisión:** Crear `RuntimeContext` dataclass que contiene configuración y dependencias, separado de `DialogueState`.

**Implementación:**
- `RuntimeContext`: Contiene `config`, `scope_manager`, `normalizer`, `action_handler`, `du`
- `DialogueState`: Puro dataclass, sin `config`
- Nodos reciben `RuntimeContext` como parámetro

**Resultado:**
- `DialogueState` es puro y serializable
- Sin hacks temporales
- Separación clara de concerns

### 3. Separación de God Objects

**Decisión:** Dividir `SoniGraphBuilder` y `RuntimeLoop` en clases especializadas.

**SoniGraphBuilder → Múltiples módulos:**
- `dm/validators.py`: `FlowValidator`
- `compiler/flow_compiler.py`: `FlowCompiler`
- `compiler/dag.py`: Estructuras DAG intermedias
- `dm/persistence.py`: `CheckpointerFactory`
- `dm/routing.py`: Funciones de routing
- `dm/nodes.py`: Factory functions para nodos
- `dm/graph.py`: Solo orquestación (236 líneas, desde 827)

**RuntimeLoop → Múltiples managers:**
- `runtime/config_manager.py`: `ConfigurationManager`
- `runtime/conversation_manager.py`: `ConversationManager`
- `runtime/streaming_manager.py`: `StreamingManager`
- `runtime/runtime.py`: Solo orquestación (382 líneas, desde 405)

**Resultado:**
- Cada clase tiene responsabilidad única
- Código más mantenible y testeable
- 0 God Objects

### 4. Registries Implementados

**Decisión:** Implementar `ValidatorRegistry` y `ActionRegistry` con decoradores `@register()`.

**Implementación:**
- `validation/registry.py`: `ValidatorRegistry` con `@ValidatorRegistry.register()`
- `actions/registry.py`: `ActionRegistry` con `@ActionRegistry.register()`
- 4 validators de ejemplo implementados
- `ActionHandler` usa registry primero, fallback a Python path (backward compatibility)

**Resultado:**
- YAML usa nombres semánticos, no paths técnicos
- Zero-leakage architecture real
- Fácil agregar nuevos validators/actions

### 5. Mejoras de Calidad

**Logging agregado:**
- `dm/nodes.py`: Exception handlers con logging
- `du/optimizers.py`: Exception handlers con logging
- `du/metrics.py`: Exception handlers con logging

**Complejidad reducida:**
- `ConfigLoader.validate()`: Dividido en 6 métodos privados
- `ScopeManager._get_flow_actions()`: Dividido en 3 métodos privados
- `ScopeManager._get_pending_slots()`: Dividido en 2 métodos

**Type hints mejorados:**
- `IScopeManager.get_available_actions()`: Usa forward reference en lugar de `Any`
- `SoniGraphBuilder`: Type hints específicos para checkpointer

**Correcciones menores:**
- Líneas largas rotas
- Dependencia duplicada eliminada

---

## Consecuencias

### Positivas

1. **Testabilidad mejorada:**
   - Todas las dependencias pueden ser mockeadas
   - Tests más rápidos y aislados

2. **Mantenibilidad mejorada:**
   - Código más modular y fácil de entender
   - Cambios localizados en módulos específicos

3. **Extensibilidad mejorada:**
   - Fácil agregar nuevos validators/actions
   - Fácil intercambiar implementaciones

4. **Calidad de código mejorada:**
   - Sin hacks temporales
   - Sin God Objects
   - Complejidad reducida

### Negativas

1. **Breaking Changes:**
   - `DialogueState` ya no tiene `config` (era un hack)
   - Nodos requieren `RuntimeContext` (antes usaban `state.config`)

2. **Migración requerida:**
   - Código existente que usaba `state.config` necesita actualización
   - Actions deben migrarse a registry (opcional, backward compatible)

3. **Complejidad inicial:**
   - Más archivos y módulos
   - Curva de aprendizaje para nuevos desarrolladores

---

## Estado Después del Refactoring

### Métricas

| Métrica | Antes | Después | Objetivo |
|---------|-------|---------|----------|
| Dependency Inversion | 0% | 100% | 100% ✅ |
| God Objects | 2 | 0 | 0 ✅ |
| Líneas en GraphBuilder | 827 | 236 | <300 ✅ |
| Líneas en RuntimeLoop | 405 | 382 | <400 ✅ |
| Complejidad ciclomática | Alta | Reducida | <10 por método ✅ |
| Cobertura de tests | 85% | >80% | >80% ✅ |

### Estructura de Módulos

```
src/soni/
├── core/
│   ├── interfaces.py      # Protocols (IActionHandler agregado)
│   ├── state.py            # DialogueState (sin config), RuntimeContext
│   ├── config.py           # ConfigLoader (validate refactorizado)
│   └── scope.py            # ScopeManager (métodos refactorizados)
├── compiler/
│   ├── dag.py              # Estructuras DAG intermedias
│   └── flow_compiler.py    # FlowCompiler (YAML → DAG)
├── dm/
│   ├── graph.py            # SoniGraphBuilder (solo orquestación)
│   ├── validators.py       # FlowValidator
│   ├── nodes.py            # Factory functions para nodos
│   ├── persistence.py      # CheckpointerFactory
│   └── routing.py          # Funciones de routing
├── runtime/
│   ├── runtime.py          # RuntimeLoop (solo orquestación)
│   ├── config_manager.py   # ConfigurationManager
│   ├── conversation_manager.py  # ConversationManager
│   └── streaming_manager.py    # StreamingManager
├── validation/
│   ├── registry.py         # ValidatorRegistry
│   └── validators.py       # Validators de ejemplo
└── actions/
    ├── registry.py         # ActionRegistry
    └── base.py             # ActionHandler (usa registry)
```

---

## Referencias

- **Code Review:** `docs/code-review-hito-13.md`
- **Tareas implementadas:** Tasks 038-052
- **ADR-001:** Arquitectura base del framework
- **Plan de ejecución:** `plan-de-ejecuci-n-backlog.plan.md`

---

## Historial de Versiones

| Versión | Fecha | Cambios |
|---------|-------|---------|
| 1.0 | Diciembre 2025 | Versión inicial del ADR |
