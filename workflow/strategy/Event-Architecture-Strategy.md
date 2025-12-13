# Arquitectura de Eventos - Soni Framework

**Proyecto:** Soni - Framework Open Source para Asistentes Conversacionales
**Documento:** Estrategia de Arquitectura de Eventos (Observer Pattern)
**Fecha:** 30 de Noviembre de 2025
**Versión:** 1.0
**Estado:** Aprobado

---

## Resumen Ejecutivo

Este documento define la arquitectura de eventos basada en el **patrón Observer** para Soni Framework. El objetivo es lograr un **desacoplamiento completo** entre el núcleo del framework (`RuntimeLoop`) y las interfaces de usuario o sistemas externos (TUI, WebUI, Analytics, etc.).

**Filosofía:** El RuntimeLoop no debe conocer a sus observadores. Solo emite eventos semánticos que cualquier componente externo puede consumir.

---

## Principios Fundamentales

### 1. Desacoplamiento Estricto
- El `RuntimeLoop` no sabe que existe una TUI, WebUI o cualquier otro consumidor.
- Solo emite eventos en puntos clave del procesamiento.
- Los consumidores se suscriben a los eventos que les interesan.

### 2. Type Safety
- Todos los eventos son dataclasses tipadas (no diccionarios genéricos).
- Los handlers usan el Protocol `EventHandler` para type checking.
- `mypy` puede validar que los eventos se usan correctamente.

### 3. Async-First
- La emisión y manejo de eventos es totalmente asíncrona.
- Los handlers se ejecutan con fire-and-forget (no bloquean).
- Compatible con el resto de la arquitectura async de Soni.

### 4. Zero-Overhead
- Si no hay suscriptores, el overhead es despreciable (simple verificación de diccionario).
- La emisión es eficiente: verifica si hay handlers antes de procesar.

### 5. Reliability
- Si un handler falla, se loguea el error pero no se propaga.
- Esto evita que un handler mal escrito rompa el RuntimeLoop.
- Los handlers deben manejar sus propios errores internamente.

---

## Diseño de la Arquitectura

### Componentes Principales

```
┌─────────────────┐
│  RuntimeLoop    │
│  (Core)         │
│                 │
│  ┌──────────┐   │
│  │ Events   │───┼──> emit("message_received", event)
│  │ Emitter  │   │
│  └──────────┘   │
└─────────────────┘
        │
        │ (async events)
        │
        ├──────────────────┬──────────────────┬──────────────────┐
        ▼                  ▼                  ▼                  ▼
   ┌────────┐         ┌────────┐         ┌──────────┐      ┌──────────┐
   │  TUI   │         │ WebUI  │         │Analytics │      │ Logger   │
   │(Textual)│        │(FastAPI)│        │ System   │      │ Service  │
   └────────┘         └────────┘         └──────────┘      └──────────┘
```

### EventEmitter Core

```python
# src/soni/core/events.py
from dataclasses import dataclass
from typing import Any, Callable, Protocol
from collections.abc import Awaitable
import asyncio
import logging

logger = logging.getLogger(__name__)

class EventHandler(Protocol):
    """Protocolo para handlers de eventos async"""
    async def __call__(self, event: Any) -> None: ...

class EventEmitter:
    """Sistema de eventos async-first para desacoplamiento"""

    def __init__(self):
        self._handlers: dict[str, list[EventHandler]] = {}
        self._lock = asyncio.Lock()

    async def emit(self, event_type: str, event: Any) -> None:
        """
        Emitir un evento a todos los suscriptores.

        Args:
            event_type: Identificador del tipo de evento (ej. "message_received")
            event: Instancia del evento (dataclass tipada)
        """
        if event_type not in self._handlers:
            return  # Zero-overhead si no hay suscriptores

        async with self._lock:
            handlers = self._handlers.get(event_type, []).copy()

        # Ejecutar handlers en paralelo (no bloquea)
        for handler in handlers:
            # Capturar handler en closure para evitar problemas de referencia
            async def safe_handler(h: EventHandler = handler) -> None:
                try:
                    await h(event)
                except Exception as e:
                    logger.error(f"Error in event handler for {event_type}: {e}")

            # Crear task sin esperar (fire-and-forget)
            asyncio.create_task(safe_handler())

    def subscribe(self, event_type: str, handler: EventHandler) -> None:
        """
        Suscribirse a un tipo de evento.

        Args:
            event_type: Identificador del tipo de evento
            handler: Función async que maneja el evento
        """
        if event_type not in self._handlers:
            self._handlers[event_type] = []
        self._handlers[event_type].append(handler)

    def unsubscribe(self, event_type: str, handler: EventHandler) -> None:
        """
        Desuscribirse de un tipo de evento.

        Args:
            event_type: Identificador del tipo de evento
            handler: Función async previamente suscrita
        """
        if event_type in self._handlers:
            self._handlers[event_type].remove(handler)
```

---

## Tipos de Eventos

Todos los eventos son dataclasses tipadas que representan eventos semánticos en el ciclo de vida del diálogo.

### 1. MessageReceivedEvent

```python
@dataclass
class MessageReceivedEvent:
    """Evento emitido cuando se recibe un mensaje del usuario"""
    user_id: str
    message: str
    timestamp: float
```

**Cuándo se emite:** Al inicio de `process_message()`, inmediatamente después de recibir el mensaje del usuario.

**Uso típico:**
- TUI: Mostrar mensaje en el chat
- Analytics: Registrar interacción del usuario
- Logger: Log de entrada de usuario

---

### 2. NLUResultEvent

```python
@dataclass
class NLUResultEvent:
    """Evento emitido después de procesar NLU"""
    user_id: str
    intent: str
    confidence: float
    slots: dict[str, Any]
    scoped_actions: list[str]
```

**Cuándo se emite:** Después de ejecutar el módulo de NLU (SoniDU), cuando se ha determinado el intent y extraído los slots.

**Uso típico:**
- TUI: Mostrar intent detectado y confianza en panel de estado
- Analytics: Métricas de accuracy del NLU
- Logger: Log de resultado de NLU para debugging

---

### 3. StateUpdatedEvent

```python
@dataclass
class StateUpdatedEvent:
    """Evento emitido cuando se actualiza el estado del diálogo"""
    user_id: str
    state: DialogueState
    turn_count: int
```

**Cuándo se emite:** Después de cada actualización del estado del diálogo (post-NLU, post-acción, etc.).

**Uso típico:**
- TUI: Actualizar panel de estado con slots actuales
- WebUI: Sincronizar estado del cliente
- Checkpointer: Trigger de persistencia (opcional)

---

### 4. ResponseReadyEvent

```python
@dataclass
class ResponseReadyEvent:
    """Evento emitido cuando la respuesta está lista"""
    user_id: str
    response: str
```

**Cuándo se emite:** Cuando la respuesta final del bot está lista para ser entregada.

**Uso típico:**
- TUI: Mostrar respuesta del bot en el chat
- WebUI: Enviar respuesta al cliente
- Analytics: Registrar tiempo de respuesta

---

### 5. ActionExecutedEvent

```python
@dataclass
class ActionExecutedEvent:
    """Evento emitido cuando se ejecuta una acción"""
    user_id: str
    action_name: str
    result: dict[str, Any]
```

**Cuándo se emite:** Después de ejecutar exitosamente una acción registrada.

**Uso típico:**
- TUI: Mostrar en debug log qué acción se ejecutó
- Analytics: Métricas de uso de acciones
- Logger: Log de ejecución de acciones

---

### 6. ErrorOccurredEvent

```python
@dataclass
class ErrorOccurredEvent:
    """Evento emitido cuando ocurre un error"""
    user_id: str
    error_type: str
    error_message: str
    context: dict[str, Any] | None = None
```

**Cuándo se emite:** Cuando ocurre un error durante el procesamiento (NLU, acción, validación, etc.).

**Uso típico:**
- TUI: Mostrar error destacado en debug panel
- WebUI: Notificar al usuario del error
- Analytics: Registrar errores para análisis
- Logger: Log detallado de errores

---

## Integración en RuntimeLoop

### Inicialización

```python
# src/soni/runtime/runtime.py
from soni.core.events import EventEmitter

class RuntimeLoop:
    def __init__(
        self,
        config_path: str,
        optimized_du_path: str | None = None
    ):
        # ... inicialización existente ...

        # Inicializar sistema de eventos
        self.events = EventEmitter()
```

### Emisión de Eventos en process_message()

```python
async def process_message(self, user_msg: str, user_id: str) -> str:
    """
    Procesa un mensaje del usuario y retorna la respuesta del bot.

    Emite eventos en puntos clave para observadores externos.
    """
    # 1. Emitir evento: mensaje recibido
    await self.events.emit("message_received", MessageReceivedEvent(
        user_id=user_id,
        message=user_msg,
        timestamp=time.time()
    ))

    try:
        # 2. Validar y cargar estado
        state = await self._load_or_create_state(user_id, user_msg)

        # 3. Ejecutar grafo (NLU, acciones, etc.)
        result = await self._execute_graph(state, user_id)

        # 4. Emitir evento: resultado NLU (si está disponible)
        if "nlu_result" in result:
            await self.events.emit("nlu_result", NLUResultEvent(
                user_id=user_id,
                intent=result["nlu_result"]["intent"],
                confidence=result["nlu_result"]["confidence"],
                slots=result["nlu_result"]["slots"],
                scoped_actions=result["nlu_result"].get("scoped_actions", [])
            ))

        # 5. Emitir evento: acción ejecutada (si aplica)
        if "action_executed" in result:
            await self.events.emit("action_executed", ActionExecutedEvent(
                user_id=user_id,
                action_name=result["action_executed"]["name"],
                result=result["action_executed"]["result"]
            ))

        # 6. Emitir evento: estado actualizado
        await self.events.emit("state_updated", StateUpdatedEvent(
            user_id=user_id,
            state=DialogueState.from_dict(result),
            turn_count=result.get("turn_count", 0)
        ))

        # 7. Extraer respuesta
        response = self._extract_response(result, user_id)

        # 8. Emitir evento: respuesta lista
        await self.events.emit("response_ready", ResponseReadyEvent(
            user_id=user_id,
            response=response
        ))

        return response

    except Exception as e:
        # Emitir evento de error
        await self.events.emit("error_occurred", ErrorOccurredEvent(
            user_id=user_id,
            error_type=type(e).__name__,
            error_message=str(e),
            context={"traceback": traceback.format_exc()}
        ))

        # Re-raise o manejar según política de errores
        raise
```

---

## Casos de Uso

### Caso 1: TUI (Textual User Interface)

```python
# src/soni/tui/app.py
from textual.app import App
from soni.core.events import (
    MessageReceivedEvent,
    NLUResultEvent,
    StateUpdatedEvent,
    ResponseReadyEvent,
    ErrorOccurredEvent
)

class SoniTUI(App):
    def __init__(self, runtime: RuntimeLoop):
        super().__init__()
        self.runtime = runtime

        # Suscribirse a eventos relevantes
        runtime.events.subscribe("message_received", self._on_message_received)
        runtime.events.subscribe("nlu_result", self._on_nlu_result)
        runtime.events.subscribe("state_updated", self._on_state_updated)
        runtime.events.subscribe("response_ready", self._on_response_ready)
        runtime.events.subscribe("error_occurred", self._on_error)

    async def _on_message_received(self, event: MessageReceivedEvent):
        """Handler: Mostrar mensaje del usuario en chat"""
        await self.chat_widget.add_user_message(event.message)

    async def _on_nlu_result(self, event: NLUResultEvent):
        """Handler: Actualizar métricas de NLU"""
        await self.metrics_widget.update_nlu(
            intent=event.intent,
            confidence=event.confidence
        )

    async def _on_state_updated(self, event: StateUpdatedEvent):
        """Handler: Actualizar panel de estado"""
        await self.state_widget.update_state(event.state)

    async def _on_response_ready(self, event: ResponseReadyEvent):
        """Handler: Mostrar respuesta del bot en chat"""
        await self.chat_widget.add_bot_message(event.response)

    async def _on_error(self, event: ErrorOccurredEvent):
        """Handler: Mostrar error en debug panel"""
        await self.debug_widget.log_error(
            error_type=event.error_type,
            message=event.error_message
        )
```

---

### Caso 2: Analytics Service

```python
# src/soni/analytics/service.py
from soni.core.events import NLUResultEvent, ActionExecutedEvent
import time

class AnalyticsService:
    def __init__(self, runtime: RuntimeLoop):
        self.runtime = runtime
        self.metrics = {
            "nlu_calls": 0,
            "avg_confidence": 0.0,
            "action_counts": {}
        }

        # Suscribirse solo a eventos relevantes
        runtime.events.subscribe("nlu_result", self._track_nlu)
        runtime.events.subscribe("action_executed", self._track_action)

    async def _track_nlu(self, event: NLUResultEvent):
        """Registrar métricas de NLU"""
        self.metrics["nlu_calls"] += 1
        self.metrics["avg_confidence"] = (
            (self.metrics["avg_confidence"] * (self.metrics["nlu_calls"] - 1)
             + event.confidence) / self.metrics["nlu_calls"]
        )

    async def _track_action(self, event: ActionExecutedEvent):
        """Registrar métricas de acciones"""
        action_name = event.action_name
        self.metrics["action_counts"][action_name] = \
            self.metrics["action_counts"].get(action_name, 0) + 1
```

---

### Caso 3: WebSocket Server

```python
# src/soni/server/websocket.py
from fastapi import WebSocket
from soni.core.events import ResponseReadyEvent, StateUpdatedEvent

class WebSocketManager:
    def __init__(self, runtime: RuntimeLoop):
        self.runtime = runtime
        self.active_connections: dict[str, WebSocket] = {}

        # Suscribirse a eventos para enviar al cliente
        runtime.events.subscribe("response_ready", self._send_response)
        runtime.events.subscribe("state_updated", self._send_state_update)

    async def _send_response(self, event: ResponseReadyEvent):
        """Enviar respuesta al cliente WebSocket"""
        websocket = self.active_connections.get(event.user_id)
        if websocket:
            await websocket.send_json({
                "type": "response",
                "data": event.response
            })

    async def _send_state_update(self, event: StateUpdatedEvent):
        """Enviar actualización de estado al cliente"""
        websocket = self.active_connections.get(event.user_id)
        if websocket:
            await websocket.send_json({
                "type": "state_update",
                "data": event.state.to_dict()
            })
```

---

## Consideraciones Técnicas

### Desacoplamiento (Crucial)

**RuntimeLoop (Core):**
- No importa `textual`, `fastapi`, ni ningún módulo externo de UI.
- Usa `self.events.emit(event_type, event)` donde `event` es una dataclass tipada.
- El `EventEmitter` es parte del núcleo (`core/events.py`) sin dependencias externas.

**Consumidores (TUI, WebUI, etc.):**
- Importan `soni.core.events` y `soni.runtime.runtime`.
- Se suscriben a eventos: `runtime.events.subscribe(event_type, handler)`.
- Los handlers son funciones async que reciben eventos tipados.

**Tests:**
- El `EventEmitter` facilita los tests de integración al permitir verificar que los eventos correctos se dispararon.
- Se pueden mockear handlers para capturar eventos sin efectos secundarios.
- Tests unitarios del EventEmitter validan suscripción/emisión.

---

### Type Safety

- Todos los eventos son dataclasses tipadas (no diccionarios genéricos).
- Los handlers usan `EventHandler` Protocol para type checking.
- `mypy` puede validar que los eventos se usan correctamente.

**Ejemplo de error detectado por mypy:**

```python
# Esto falla en type checking si NLUResultEvent no tiene campo "intensity"
async def bad_handler(event: NLUResultEvent):
    print(event.intensity)  # mypy error: NLUResultEvent has no attribute 'intensity'
```

---

### Manejo de Errores en Handlers

**Política:**
- Si un handler falla, se loguea el error pero **no se propaga** al RuntimeLoop.
- Esto evita que un handler mal escrito rompa el RuntimeLoop.
- Los handlers deben manejar sus propios errores internamente si requieren lógica de recuperación.

**Implementación en EventEmitter:**

```python
async def safe_handler(h: EventHandler = handler) -> None:
    try:
        await h(event)
    except Exception as e:
        logger.error(f"Error in event handler for {event_type}: {e}")
```

**Implicaciones:**
- Un error en el TUI no rompe el RuntimeLoop.
- Un error en Analytics no afecta al WebSocket.
- Los errores críticos deben ser manejados dentro del handler mismo.

---

### Performance

#### Zero-Overhead cuando no hay suscriptores

```python
async def emit(self, event_type: str, event: Any) -> None:
    if event_type not in self._handlers:
        return  # <-- Retorna inmediatamente, sin procesamiento
```

- El overhead es una simple verificación de diccionario (`O(1)`).
- Si no hay suscriptores, no hay serialización, no hay tasks creados.
- Ideal para producción sin debugging habilitado.

#### Async no-bloqueante

- Los handlers se ejecutan con `asyncio.create_task()` (fire-and-forget).
- El `emit()` no espera que los handlers terminen.
- Si un handler es lento, no bloquea el RuntimeLoop ni otros handlers.

**Diagrama de flujo:**

```
RuntimeLoop.process_message()
    │
    ├─> emit("message_received")  ──┐
    │                                │ (no espera)
    ├─> [procesamiento NLU]          │
    │                                ▼
    ├─> emit("nlu_result")       Handler 1 (async task)
    │                                │
    ├─> [procesamiento acción]       ▼
    │                            Handler 2 (async task)
    └─> emit("response_ready")
```

#### Restricciones para Handlers

- Los handlers deben ser **rápidos** (< 100ms idealmente).
- Operaciones lentas (I/O, procesamiento pesado) deben crear su propio task interno:

```python
async def slow_handler(event: NLUResultEvent):
    # INCORRECTO: Esto bloquea el event loop
    await heavy_database_operation(event)

    # CORRECTO: Delegar a un task separado
    asyncio.create_task(heavy_database_operation(event))
```

#### Thread-Safety

- En Python async, el EventEmitter usa `asyncio.Lock` para proteger la lista de handlers.
- La emisión de eventos es **thread-safe** para múltiples coroutines concurrentes.
- No se requiere locking adicional en los consumidores.

---

### Relación con Logging

**Eventos complementan, no reemplazan logging:**

| Aspecto | Logging | Eventos |
|---------|---------|---------|
| **Propósito** | Persistencia, auditoría, debugging | Interfaces reactivas, métricas en vivo |
| **Consumidores** | Archivos de log, stdout, sistemas de logging | TUI, WebUI, Analytics, Dashboards |
| **Latencia** | Síncrono (o buffer async) | Async, tiempo real |
| **Persistencia** | Sí (archivos, bases de datos) | No (efímero, en memoria) |
| **Formato** | Texto plano, JSON logs | Dataclasses tipadas |

**Casos de uso:**

- **Logging:** Debugging post-mortem, auditoría de compliance, análisis de logs.
- **Eventos:** Actualización de UI en tiempo real, métricas en dashboards, notificaciones push.

**Ejemplo combinado:**

```python
async def process_message(self, user_msg: str, user_id: str) -> str:
    # Logging tradicional
    logger.info(f"Processing message from user {user_id}")

    # Emisión de evento para UI
    await self.events.emit("message_received", MessageReceivedEvent(...))

    # Ambos coexisten sin conflicto
```

---

## Riesgos y Mitigaciones

### Riesgo 1: Acoplamiento Accidental

**Descripción:** El RuntimeLoop importa accidentalmente módulos de `tui` o `server`.

**Probabilidad:** Media
**Impacto:** Alto

**Mitigación:**
- Revisión de código estricta para asegurar que `core` nunca importa `tui`.
- Lint rule personalizada con `ruff` para detectar imports prohibidos.
- Tests de integración que validen que `core` es importable sin dependencias externas.

**Validación:**

```python
# Test de desacoplamiento
def test_core_has_no_external_dependencies():
    import soni.core.events
    import soni.runtime.runtime
    # Si llega aquí sin ImportError, el desacoplamiento está OK
```

---

### Riesgo 2: Overhead de Eventos en Producción

**Descripción:** La emisión de eventos añade latencia significativa.

**Probabilidad:** Baja
**Impacto:** Medio

**Mitigación:**
- Implementación eficiente con verificación temprana de suscriptores.
- Benchmark temprano para validar zero-overhead.
- Profiling en modo producción sin TUI habilitado.

**Validación:**

```python
# Benchmark: Emisión sin suscriptores
import time
emitter = EventEmitter()
start = time.perf_counter()
for _ in range(10000):
    await emitter.emit("test", TestEvent())
end = time.perf_counter()
print(f"Overhead: {(end - start) * 1000:.2f}ms para 10k emisiones")
# Esperado: < 10ms (< 1µs por emisión)
```

---

### Riesgo 3: Handlers Lentos Bloquean el Event Loop

**Descripción:** Un handler lento (ej. query a DB) bloquea el RuntimeLoop.

**Probabilidad:** Media
**Impacto:** Medio

**Mitigación:**
- Handlers se ejecutan con fire-and-forget (no bloquean).
- Documentar que handlers deben ser rápidos.
- Si un handler necesita procesamiento pesado, debe usar `asyncio.create_task()`.

**Documentación para desarrolladores:**

> **IMPORTANTE:** Los handlers de eventos deben completarse en < 100ms.
> Si necesitas realizar operaciones lentas (I/O, procesamiento pesado), delega a un task separado:
>
> ```python
> async def my_handler(event: MyEvent):
>     # Delegar operación lenta
>     asyncio.create_task(slow_operation(event))
> ```

---

### Riesgo 4: Eventos Perdidos si Handler Falla

**Descripción:** Si un handler falla, el evento se pierde y no se vuelve a procesar.

**Probabilidad:** Baja
**Impacto:** Bajo

**Mitigación:**
- Errores en handlers se capturan y loguean, no se propagan.
- Si es crítico, el handler puede tener su propio try/except interno con lógica de reintentos.
- Para casos críticos (ej. facturación), usar sistemas de mensajería robustos (RabbitMQ, Kafka) en lugar de eventos in-memory.

**Ejemplo de handler robusto:**

```python
async def critical_handler(event: ActionExecutedEvent):
    try:
        await send_to_billing_system(event)
    except Exception as e:
        # Logging crítico
        logger.critical(f"Billing event lost: {e}")
        # Persistir para retry manual
        await save_failed_event_to_db(event)
```

---

## Hitos de Implementación

### Hito 1: EventEmitter Core (2 días)

**Tareas:**
- [ ] Implementar `EventEmitter` en `src/soni/core/events.py`
- [ ] Definir todos los tipos de eventos como dataclasses
- [ ] Tests unitarios de `EventEmitter` (subscribe, unsubscribe, emit)
- [ ] Benchmark de zero-overhead

**Criterios de Éxito:**
- [ ] `EventEmitter` implementado y testeado
- [ ] Overhead de emisión sin suscriptores < 1µs
- [ ] Type checking pasa con mypy

---

### Hito 2: Integración en RuntimeLoop (1 día)

**Tareas:**
- [ ] Añadir `self.events = EventEmitter()` en `RuntimeLoop.__init__()`
- [ ] Emitir eventos en puntos clave de `process_message()`
- [ ] Tests de integración: validar que eventos se emiten correctamente

**Criterios de Éxito:**
- [ ] RuntimeLoop emite todos los eventos definidos
- [ ] Tests de integración pasando
- [ ] No se rompe funcionalidad existente

---

### Hito 3: Documentación y Ejemplos (1 día)

**Tareas:**
- [ ] Documentar arquitectura de eventos en `docs/architecture.md`
- [ ] Crear ejemplo de consumidor simple (Logger de eventos)
- [ ] Actualizar AGENTS.md con guía de eventos

**Criterios de Éxito:**
- [ ] Documentación clara y completa
- [ ] Ejemplo funcional de consumidor

---

## Métricas de Éxito

### Performance
- **Overhead sin suscriptores:** < 1µs por emisión
- **Overhead con 5 suscriptores:** < 100µs por emisión
- **Memoria:** < 100KB para EventEmitter con 20 tipos de eventos

### Calidad
- **Type coverage:** 100% (todos los eventos tipados)
- **Test coverage:** > 90% en `core/events.py`
- **Documentación:** Todos los eventos documentados con casos de uso

### Usabilidad
- **Tiempo de integración:** < 30 minutos para añadir un nuevo consumidor
- **Errores de integración:** 0 errores de acoplamiento detectados en revisión

---

## Próximos Pasos

1. **Implementar Hito 1:** EventEmitter Core
2. **Validar con ejemplo simple:** Logger de eventos
3. **Integrar en RuntimeLoop:** Hito 2
4. **Habilitar consumidores externos:** TUI, Analytics, etc.

---

**Fin del Documento**
