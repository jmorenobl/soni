## Hito 0: Validación Técnica Pre-Desarrollo

**ID de tarea:** 0001  
**Objetivo principal:** Validar que las tecnologías core (DSPy, LangGraph y persistencia async con `aiosqlite`) funcionan para el caso de uso de Soni antes de invertir meses de desarrollo.  
**Definición de éxito:** Todas las validaciones completadas, métricas dentro de los umbrales definidos y decisión GO/NO-GO documentada.

---

### Prerrequisitos y entorno de trabajo

**Suposiciones:**
- Estás en la raíz del repo de Soni: `/Users/jorge/Projects/Playground/soni`.
- Tienes `python` 3.11+ instalado.
- Usaremos **uv** como gestor de entorno y dependencias.
- Dispones de credenciales para el LLM que uses con DSPy (por ejemplo `OPENAI_API_KEY` exportada en tu entorno).

**1. Instalar `uv` (si aún no lo tienes):**

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
# Recarga tu shell si es necesario para que el binario `uv` esté disponible
```

**2. Inicializar un entorno de trabajo para los experimentos del Hito 0:**

Este hito es pre-desarrollo, pero es útil tener un entorno reproducible.  
Desde la raíz del repo:

```bash
cd /Users/jorge/Projects/Playground/soni

# Crear un pyproject mínimo para experimentos
uv init --app soni-hito0-experiments

# Añadir dependencias necesarias para los tres experimentos
uv add dspy langgraph fastapi uvicorn[standard] httpx pyyaml aiosqlite
uv add --dev pytest pytest-asyncio anyio

# Sincronizar entorno
uv sync
```

Esto creará un `pyproject.toml`, un entorno aislado gestionado por `uv` y permitirá ejecutar todos los scripts del directorio `experiments/` con `uv run`.

> **Nota sobre credenciales de LLM:**  
> Antes de ejecutar los experimentos DSPy, asegúrate de exportar la variable adecuada (por ejemplo):
> ```bash
> export OPENAI_API_KEY="tu_api_key_aquí"
> ```

**3. Estructura mínima recomendada para el Hito 0:**

```text
soni/
├── pyproject.toml          # creado por uv init
├── uv.lock                 # generado por uv sync
├── experiments/
│   ├── 01_dspy_validation.py
│   ├── 02_langgraph_streaming.py
│   └── 03_async_persistence.py
└── docs/
    └── ...
```

---

### Cómo ejecutar este hito (resumen operativo)

Una vez creados los scripts indicados en las secciones siguientes:

```bash
cd /Users/jorge/Projects/Playground/soni

# Ejecutar experimento DSPy
uv run experiments/01_dspy_validation.py

# Ejecutar experimento LangGraph Streaming
uv run experiments/02_langgraph_streaming.py

# Ejecutar experimento de persistencia async
uv run experiments/03_async_persistence.py
```

Tras cada ejecución, anota métricas y observaciones en el reporte del punto **0.4**.  
Cuando los tres scripts pasen los criterios de éxito, redacta el informe de decisión GO/NO-GO.

---

### Referencias directas al ADR-001 (para implementación del código)

Para los detalles exactos de implementación de cada script, esta tarea se apoya en los ejemplos canónicos definidos en el ADR:

- **6.1 Validación DSPy Optimization** → código de referencia para `experiments/01_dspy_validation.py`.
- **6.2 Validación LangGraph Streaming** → código de referencia para `experiments/02_langgraph_streaming.py` (incluye ejemplo de FastAPI + `StreamingResponse` + `uvicorn`).
- **6.3 Validación Persistencia Async** → código de referencia para `experiments/03_async_persistence.py` (incluye uso de `AsyncSqliteSaver` y `StateGraph`).

La expectativa es que copies/adaptes esos snippets al directorio `experiments/` y los ejecutes con los comandos indicados arriba usando `uv run` (o `uv run uvicorn ...` en el caso del endpoint FastAPI de streaming).

---

### 0.1 Experimento de validación DSPy (MIPROv2)

**Propósito:**  
Demostrar que un módulo DSPy optimizado con MIPROv2 mejora de forma medible la accuracy en extracción de intents y entidades frente a un baseline sin optimización.

**Entregables concretos:**
- Script `experiments/01_dspy_validation.py` funcional y reproducible.
- Dataset mínimo curado de ejemplos de intents/entities representativos del dominio inicial (p. ej. booking de vuelos).
- Métricas de accuracy baseline vs optimizado, con mejora ≥ 5%.
- Evidencia de que el módulo optimizado se puede serializar (`.save()` / `.load()`).

**Pasos detallados:**
- [ ] Diseñar un pequeño dataset de entrenamiento y evaluación:
  - [ ] Definir 10–30 ejemplos de usuario con intents y entidades etiquetadas.
  - [ ] Cubrir casos positivos, ambiguos y edge cases.
  - [ ] Guardar dataset en formato fácil de cargar (YAML/JSON/CSV).
- [ ] Implementar script `experiments/01_dspy_validation.py`:
  - [ ] Configurar LM base en DSPy (ej. `gpt-4o-mini`).
  - [ ] Definir la `Signature` de DU según el ADR (inputs y outputs estructurados).
  - [ ] Implementar módulo baseline sin optimización.
  - [ ] Implementar pipeline de optimización con MIPROv2 (modo light).
- [ ] Ejecutar experimento de baseline:
  - [ ] Medir accuracy en intents y entidades en el dataset de evaluación.
  - [ ] Registrar métricas y ejemplos de errores.
- [ ] Ejecutar optimización MIPROv2:
  - [ ] Lanzar optimización sobre el dataset de entrenamiento.
  - [ ] Verificar que el proceso termina sin errores.
  - [ ] Medir tiempo total de optimización y comprobar que es < 10 minutos.
- [ ] Evaluar módulo optimizado:
  - [ ] Medir nuevamente accuracy en el mismo dataset de evaluación.
  - [ ] Comparar baseline vs optimizado, buscando mejora ≥ 5%.
  - [ ] Analizar ejemplos donde mejora y donde falla.
- [ ] Validar serialización:
  - [ ] Guardar el módulo optimizado a disco (`.save()`).
  - [ ] Cargarlo en un nuevo proceso y ejecutar predicciones.
  - [ ] Confirmar que el comportamiento es consistente tras la carga.
- [ ] Documentar resultados:
  - [ ] Crear sección de resultados en `docs/adr/` o `docs/strategy/`.
  - [ ] Incluir tablas de métricas antes/después.
  - [ ] Documentar posibles riesgos o limitaciones observadas.

---

### 0.2 Experimento de validación LangGraph Streaming

**Propósito:**  
Verificar que LangGraph soporta streaming async de tokens de forma fiable, integrado con FastAPI y compatible con SSE, cumpliendo con una latencia razonable de primer token.

**Entregables concretos:**
- Script `experiments/02_langgraph_streaming.py`.
- Endpoint de prueba FastAPI que exponga streaming usando LangGraph.
- Métricas de latencia de primer token y orden correcto de los chunks.

**Pasos detallados:**
- [ ] Diseñar un grafo mínimo de conversación:
  - [ ] Nodo que invoque al LLM y emita tokens de respuesta progresivamente.
  - [ ] Estado mínimo (ej. mensajes y un identificador de conversación).
- [ ] Implementar script `experiments/02_langgraph_streaming.py`:
  - [ ] Definir grafo con LangGraph usando nodos async.
  - [ ] Configurar un `StateGraph` simple con entrada de mensaje de usuario.
  - [ ] Implementar callback/stream para emisión de tokens.
- [ ] Integrar con FastAPI:
  - [ ] Crear una app FastAPI mínima en el script de experimento.
  - [ ] Definir endpoint `/stream-test` que conecte con el grafo de LangGraph.
  - [ ] Usar `StreamingResponse` para emitir tokens via SSE.
- [ ] Validar orden y consistencia de chunks:
  - [ ] Probar con varios mensajes de usuario.
  - [ ] Confirmar que los chunks llegan en el orden generado.
  - [ ] Verificar que no hay duplicados ni pérdidas de tokens.
- [ ] Medir latencia de primer token:
  - [ ] Registrar timestamps de petición y primer chunk emitido.
  - [ ] Confirmar que la latencia de primer token es < 500 ms en condiciones normales.
- [ ] Documentar resultados:
  - [ ] Describir arquitectura mínima del grafo de prueba.
  - [ ] Incluir mediciones de latencia y posibles cuellos de botella.

---

### 0.3 Experimento de validación de persistencia async (aiosqlite)

**Propósito:**  
Garantizar que es viable usar `aiosqlite` para checkpointing y persistencia del estado de conversación en un contexto altamente concurrente.

**Entregables concretos:**
- Script `experiments/03_async_persistence.py`.
- Esquema de tablas SQLite para estados de conversación.
- Pruebas de concurrencia y latencia por operación.

**Pasos detallados:**
- [ ] Diseñar modelo de datos mínimo de `DialogueState` para persistencia:
  - [ ] Identificador de conversación / usuario.
  - [ ] Snapshot del estado (`JSON` o campos desnormalizados).
  - [ ] Timestamps de creación/actualización.
- [ ] Implementar script `experiments/03_async_persistence.py`:
  - [ ] Configurar conexión async con `aiosqlite`.
  - [ ] Implementar funciones async de `save_state` y `load_state`.
  - [ ] Añadir índices mínimos para rendimiento.
- [ ] Probar persistencia básica:
  - [ ] Guardar estado de una conversación.
  - [ ] Recuperarlo y comparar con el original.
- [ ] Probar múltiples conversaciones simultáneas:
  - [ ] Lanzar varias corrutinas que guarden/carguen estados en paralelo.
  - [ ] Verificar que no hay inconsistencias entre estados.
  - [ ] Observar posibles bloqueos o deadlocks.
- [ ] Detectar y mitigar race conditions:
  - [ ] Inyectar pequeñas esperas aleatorias para forzar interleaving.
  - [ ] Verificar que los últimos estados guardados son los que se leen.
- [ ] Medir performance:
  - [ ] Registrar tiempo de operaciones de lectura y escritura.
  - [ ] Comprobar que el tiempo medio por operación es < 100 ms.
- [ ] Documentar resultados y riesgos:
  - [ ] Documentar patrón de acceso recomendado (ej. upserts, locking).
  - [ ] Evaluar si es necesario considerar PostgreSQL/Redis a futuro.

---

### 0.4 Reporte y decisión GO/NO-GO

**Propósito:**  
Tomar una decisión informada sobre continuar con la arquitectura propuesta, basándose en datos objetivos de los experimentos.

**Entregables concretos:**
- Reporte de resultados consolidado.
- Decisión GO/NO-GO explícita.
- Registro de riesgos y alternativas.

**Pasos detallados:**
- [ ] Consolidar métricas y hallazgos:
  - [ ] Recoger métricas clave de los tres experimentos (accuracy, latencias, tiempos).
  - [ ] Resumir problemas encontrados y soluciones propuestas.
- [ ] Evaluar criterios de éxito:
  - [ ] Verificar que la optimización DSPy cumple las mejoras esperadas.
  - [ ] Confirmar que el streaming cumple latencia y estabilidad.
  - [ ] Asegurar que la persistencia async es robusta y suficientemente rápida.
- [ ] Redactar reporte:
  - [ ] Crear documento en `docs/adr/` o `docs/strategy/` con resumen ejecutivo.
  - [ ] Incluir secciones de experimentos, resultados, conclusiones y riesgos.
- [ ] Registrar decisión:
  - [ ] Definir claramente si se continúa (GO) o se replantea arquitectura (NO-GO).
  - [ ] En caso de NO-GO, listar alternativas tecnológicas y próximos pasos.


