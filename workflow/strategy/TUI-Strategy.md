# Estrategia de Implementación TUI (Textual)

**Proyecto:** Soni - Framework Open Source para Asistentes Conversacionales
**Documento:** Estrategia de Implementación de TUI (Text User Interface)
**Fecha:** 30 de Noviembre de 2025
**Versión:** 1.0
**Estado:** Aprobado

---

## Resumen Ejecutivo

Este documento define la estrategia de implementación de la **interfaz de terminal (TUI)** para Soni usando **Textual**, que permite a los desarrolladores interactuar con el bot, ver el estado interno en tiempo real y depurar el flujo de diálogo de manera eficiente.

**Dependencias:** Requiere la **Arquitectura de Eventos** implementada (ver `Event-Architecture-Strategy.md`).

**Filosofía:** La TUI es un consumidor de eventos del RuntimeLoop. No modifica el núcleo del framework, solo observa y presenta información.

---

## Objetivo

Implementar una interfaz de terminal moderna y asíncrona para Soni que:

1. **Interacción en tiempo real**: Chat interactivo con el bot
2. **Visualización de estado**: Panel de estado del diálogo (slots, intent, acciones)
3. **Debugging visual**: Logs y eventos del sistema
4. **Métricas en vivo**: Confianza del NLU, turn count, etc.

---

## Arquitectura y Dependencias

### Dependencia: Arquitectura de Eventos

La TUI depende completamente del sistema de eventos implementado en `Event-Architecture-Strategy.md`. La TUI:

- **Se suscribe** a eventos del RuntimeLoop (`message_received`, `nlu_result`, `state_updated`, etc.)
- **No modifica** el RuntimeLoop ni el core de Soni
- **No bloquea** el procesamiento (handlers async fire-and-forget)

**Referencia:** Ver `Event-Architecture-Strategy.md` para detalles completos del sistema de eventos.

### Integración Básica con Eventos

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

        # Suscribirse a eventos del RuntimeLoop
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
        await self.metrics_widget.update_nlu(event)

    async def _on_state_updated(self, event: StateUpdatedEvent):
        """Handler: Actualizar panel de estado"""
        await self.state_widget.update_state(event.state)

    async def _on_response_ready(self, event: ResponseReadyEvent):
        """Handler: Mostrar respuesta del bot en chat"""
        await self.chat_widget.add_bot_message(event.response)

    async def _on_error(self, event: ErrorOccurredEvent):
        """Handler: Mostrar error en debug panel"""
        await self.debug_widget.log_error(event)
```

## Hitos de Implementación

**IMPORTANTE:** Antes de iniciar estos hitos, debe estar completada la implementación de la Arquitectura de Eventos (ver `Event-Architecture-Strategy.md`).

---

### Hito 1: Setup y Prototipo Básico

**Duración:** 2-3 días
**Dependencias:** Arquitectura de Eventos implementada

#### Tareas

1.  **Setup de Proyecto**
    - Añadir dependencia `textual` al proyecto:
      ```bash
      uv add --group tui textual
      ```
    - Crear estructura de directorios:
      ```
      src/soni/tui/
      ├── __init__.py
      ├── app.py          # App principal de Textual
      ├── widgets/        # Widgets personalizados
      │   ├── __init__.py
      │   ├── chat.py
      │   ├── state.py
      │   └── debug.py
      └── styles.css      # Estilos de la TUI
      ```
    - Añadir comando CLI `soni tui` en `src/soni/cli/tui.py`:
      ```python
      @click.command()
      @click.option('--config', default='soni.yaml')
      def tui(config: str):
          """Launch the Soni TUI (Text User Interface)"""
          from soni.tui.app import SoniTUI
          from soni.runtime.runtime import RuntimeLoop

          runtime = RuntimeLoop(config_path=config)
          app = SoniTUI(runtime)
          app.run()
      ```

2.  **Prototipo Básico**
    - App mínima de Textual (`SoniTUI(App)`).
    - Layout básico usando Textual containers:
      - Header: Título "Soni TUI" + versión
      - Footer: Help hints ("Ctrl+C: Exit", "Ctrl+L: Clear")
      - Main Area: Placeholder para chat
    - Verificar que la app arranca sin errores.

3.  **Integración con Eventos**
    - Conectar `SoniTUI` al `RuntimeLoop` via eventos.
    - Suscribirse a un evento de prueba (`message_received`).
    - Mostrar evento en pantalla como proof-of-concept.

#### Criterios de Éxito

- [ ] Comando `soni tui` lanza la interfaz correctamente.
- [ ] Layout básico renderiza sin errores.
- [ ] TUI recibe y muestra un evento de prueba del RuntimeLoop.
- [ ] No hay acoplamiento: el RuntimeLoop no importa módulos de `tui`.

---

### Hito 2: Chat Interactivo (ChatWidget)

**Duración:** 2-3 días
**Dependencias:** Hito 1 completado

#### Tareas

1.  **ChatWidget**
    - Input de texto para usuario.
    - Área de historial de mensajes (scrollable).
    - Renderizado de Markdown para respuestas del bot.

2.  **Integración con RuntimeLoop**
    - Conectar Input del TUI -> `RuntimeLoop.process_message()`.
    - Suscribirse a eventos:
      - `message_received` → Mostrar mensaje del usuario en ChatWidget
      - `response_ready` → Mostrar respuesta del bot en ChatWidget
      - `error_occurred` → Mostrar error en ChatWidget/DebugWidget

#### Criterios de Éxito

- [ ] Puedo enviar mensajes desde el TUI.
- [ ] El bot responde y se muestra en el historial.
- [ ] La UI no se congela durante el procesamiento (gracias a async).

---

### Hito 3: Visualización de Estado (StateWidget)

**Duración:** 2-3 días
**Dependencias:** Hito 2 completado

#### Tareas

1.  **StateWidget (Panel Lateral)**
    - Tree view o JSON view colapsable.
    - Mostrar: Slots actuales, Intent detectado, Última acción.

2.  **Actualización Reactiva**
    - Escuchar evento `StateUpdated`.
    - Actualizar widget automáticamente cuando cambia el estado.

3.  **Métricas en Header/Panel**
    - Mostrar Turn Count, Confianza del NLU.

#### Criterios de Éxito

- [ ] El panel lateral muestra el estado actual del diálogo.
- [ ] Se actualiza en tiempo real tras cada interacción.
- [ ] Visualización clara de slots y valores.

---

### Hito 4: Debugging y Logs (DebugWidget)

**Duración:** 2-3 días
**Dependencias:** Hito 3 completado

#### Tareas

1.  **DebugWidget (Footer/Panel Inferior)**
    - Log viewer con colores por nivel (INFO, WARN, ERROR).
    - Filtros básicos (opcional).

2.  **Captura de Eventos de Sistema**
    - Suscribirse a todos los eventos relevantes:
      - `message_received` → Log INFO
      - `nlu_result` → Log DEBUG con detalles de NLU
      - `state_updated` → Log DEBUG con cambios de estado
      - `action_executed` → Log INFO con acción ejecutada
      - `error_occurred` → Log ERROR destacado
    - Mostrar trazas de error amigables en el TUI.
    - Filtrar eventos opcionales (solo mostrar relevantes para debugging).

#### Criterios de Éxito

- [ ] Logs del sistema visibles en el TUI.
- [ ] Errores se muestran de forma destacada pero no rompen la UI.

---

### Hito 5: Polish y Documentación

**Duración:** 1-2 días
**Dependencias:** Hitos 1-4 completados

#### Tareas

1.  **UX Improvements**
    - Atajos de teclado (Ctrl+C, Ctrl+L, etc.).
    - Help screen.

2.  **Documentación**
    - Actualizar `AGENTS.md` con arquitectura de eventos.
    - Guía de uso del TUI.

#### Criterios de Éxito

- [ ] Experiencia de usuario fluida.
- [ ] Documentación clara sobre cómo extender o debuggear usando el TUI.

---

## Consideraciones Técnicas

### Desacoplamiento con RuntimeLoop

**CRÍTICO:** La TUI **nunca debe ser importada** por el RuntimeLoop o cualquier módulo del core.

- **RuntimeLoop**:
  - No importa `textual` ni ningún módulo de `soni.tui`.
  - Solo emite eventos via `self.events.emit()` (ver `Event-Architecture-Strategy.md`).
- **TUI**:
  - Importa `soni.core.events` y `soni.runtime.runtime`.
  - Se suscribe a eventos: `runtime.events.subscribe(event_type, handler)`.
  - Los handlers son funciones async que reciben eventos tipados.

### Type Safety de Handlers

- Todos los handlers deben aceptar eventos tipados (dataclasses).
- Usar type hints completos para que `mypy` valide correctamente:

```python
async def _on_nlu_result(self, event: NLUResultEvent) -> None:
    # mypy valida que event tiene campos: intent, confidence, etc.
    await self.metrics_widget.update(event.confidence)
```

### Manejo de Errores en Handlers de TUI

**Política:**
- Si un handler de TUI falla, debe loguear el error pero **no debe romper la UI**.
- Usar try/except interno para errores críticos:

```python
async def _on_state_updated(self, event: StateUpdatedEvent) -> None:
    try:
        await self.state_widget.update_state(event.state)
    except Exception as e:
        # Loguear pero no romper la UI
        logger.error(f"Error updating state widget: {e}")
        # Opcional: Mostrar mensaje de error en UI
        await self.show_error_notification("State update failed")
```

### Performance de Handlers

**IMPORTANTE:** Los handlers de TUI deben ser rápidos (< 100ms).

- **Operaciones rápidas** (OK en handler):
  - Actualizar texto de un widget
  - Añadir línea a un log viewer
  - Actualizar un contador

- **Operaciones lentas** (delegar a task):
  - I/O pesado (archivos grandes, DB)
  - Procesamiento complejo
  - Múltiples updates que pueden batchearse

**Ejemplo de delegación:**

```python
async def _on_heavy_event(self, event: HeavyEvent) -> None:
    # Delegar procesamiento pesado
    asyncio.create_task(self._process_heavy_event(event))

async def _process_heavy_event(self, event: HeavyEvent) -> None:
    # Procesamiento pesado aquí
    result = await heavy_computation(event)
    # Actualizar UI cuando esté listo
    await self.widget.update(result)
```

### Relación con Logging

- La TUI puede capturar logs del sistema y mostrarlos en el DebugWidget.
- Los eventos y los logs coexisten:
  - **Eventos**: Para actualización reactiva de UI
  - **Logs**: Para persistencia y análisis post-mortem

## Riesgos y Mitigaciones

### Riesgo 1: UI se Congela Durante Procesamiento

**Descripción:** Si los handlers no son async correctos, la UI puede congelarse.

**Probabilidad:** Media
**Impacto:** Alto (mala UX)

**Mitigación:**
- Todos los handlers son `async def`.
- Usar Textual workers para operaciones pesadas.
- Testing de responsividad de UI.

**Validación:**
```python
# Test: UI debe responder durante procesamiento pesado
async def test_ui_responsiveness():
    # Simular procesamiento pesado
    heavy_event = HeavyEvent(data="large")
    await tui._on_heavy_event(heavy_event)

    # Verificar que UI sigue respondiendo
    assert tui.is_responsive()
```

---

### Riesgo 2: Acoplamiento Accidental con RuntimeLoop

**Descripción:** Importar accidentalmente módulos de TUI desde el core.

**Probabilidad:** Baja
**Impacto:** Crítico (rompe arquitectura)

**Mitigación:**
- Revisión de código estricta.
- Lint rule personalizada con `ruff`:
  ```toml
  [tool.ruff.lint.per-file-ignores]
  "src/soni/core/*" = ["F401"]  # Ban imports from tui
  "src/soni/runtime/*" = ["F401"]
  ```
- Test de desacoplamiento:
  ```python
  def test_core_has_no_tui_dependencies():
      import soni.core.events
      import soni.runtime.runtime
      # Si llega aquí, no hay imports de tui
  ```

---

### Riesgo 3: Handlers de TUI Rompen el RuntimeLoop

**Descripción:** Un error en un handler de TUI rompe el procesamiento del RuntimeLoop.

**Probabilidad:** Baja
**Impacto:** Crítico

**Mitigación:**
- El EventEmitter captura errores de handlers (ver `Event-Architecture-Strategy.md`).
- Los handlers de TUI tienen try/except internos.
- Tests de robustez:
  ```python
  async def test_handler_error_does_not_break_runtime():
      # Handler que falla
      async def bad_handler(event):
          raise ValueError("Test error")

      runtime.events.subscribe("test", bad_handler)

      # Debe continuar funcionando
      response = await runtime.process_message("test", "user-1")
      assert response is not None
  ```

---

### Riesgo 4: Textual No Soporta Caso de Uso Específico

**Descripción:** Alguna feature de la TUI no es posible con Textual.

**Probabilidad:** Baja
**Impacto:** Medio

**Mitigación:**
- Prototipar features complejas temprano.
- Tener fallback a terminal puro si Textual no funciona.
- Comunicación activa con comunidad de Textual.

---

## Conclusión

La TUI es un consumidor de eventos del RuntimeLoop, implementada con **Textual** para proporcionar una interfaz moderna y asíncrona de debugging y desarrollo. Gracias a la **Arquitectura de Eventos** (ver `Event-Architecture-Strategy.md`), la TUI está completamente desacoplada del core del framework, lo que permite:

1. **Desarrollo independiente**: La TUI puede evolucionar sin afectar al RuntimeLoop.
2. **Mantenibilidad**: Errores en la TUI no rompen el core.
3. **Extensibilidad**: Futuras interfaces (WebUI, CLI avanzado) pueden coexistir sin conflicto.

**Próximos Pasos:**

1. **Completar Arquitectura de Eventos** (pre-requisito crítico)
2. **Implementar Hito 1:** Setup y prototipo básico
3. **Iterar sobre Hitos 2-5:** Chat, Estado, Debug, Polish
4. **Validar UX con usuarios reales**

---

**Referencias:**
- `Event-Architecture-Strategy.md` - Arquitectura de eventos (Observer Pattern)
- `Implementation-Strategy.md` - Estrategia general de implementación de Soni

---

**Fin del Documento**
