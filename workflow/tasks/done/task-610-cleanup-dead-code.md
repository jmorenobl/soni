## Task: 610 - Cleanup: Identify and Remove Dead Code

**ID de tarea:** 610
**Hito:** 6 - Final Validation & Cleanup
**Dependencias:** Task 609 (Cleanup: Empty/Unused Modules)
**Duración estimada:** 3 horas

### Objetivo

Identificar y eliminar código muerto: imports no utilizados, variables no utilizadas, funciones/clases no utilizadas, y código inalcanzable.

### Contexto

El código muerto aumenta la complejidad y el mantenimiento. Después de un refactoring, puede quedar:
- Imports no utilizados
- Variables no utilizadas
- Funciones/clases no utilizadas
- Código inalcanzable
- Implementaciones duplicadas

**Importante**: Como la librería aún no está en uso, podemos eliminar código muerto de forma agresiva sin preocuparnos por romper código de usuarios externos. No hay necesidad de mantener funciones/clases "por si acaso" alguien las usa.

Referencia: `docs/implementation/99-validation.md` - Sección 12: Identify Dead Code

### Entregables

- [ ] Imports no utilizados identificados y eliminados
- [ ] Variables no utilizadas identificadas y eliminadas
- [ ] Funciones/clases no utilizadas identificadas y eliminadas
- [ ] Código inalcanzable identificado y eliminado
- [ ] Cambios documentados

### Implementación Detallada

#### Paso 1: Identificar Imports No Utilizados

**Comando:**
```bash
uv run ruff check --select F401 src/soni
```

**Explicación:**
- Ejecutar ruff para encontrar imports no utilizados
- Revisar cada import identificado
- Eliminar imports no utilizados
- Verificar que no se rompe nada

#### Paso 2: Identificar Variables No Utilizadas

**Comando:**
```bash
uv run ruff check --select F841 src/soni
```

**Explicación:**
- Ejecutar ruff para encontrar variables no utilizadas
- Revisar cada variable identificada
- Eliminar variables no utilizadas o usarlas si son necesarias
- Verificar que no se rompe nada

#### Paso 3: Identificar Código Inalcanzable

**Proceso:**
- Revisar código para branches inalcanzables
- Buscar código después de `return` o `raise` sin condiciones
- Identificar funciones que nunca se llaman
- Buscar implementaciones duplicadas

**Explicación:**
- Revisar manualmente código crítico
- Usar herramientas de análisis estático si están disponibles
- Documentar código inalcanzable encontrado
- Eliminar código inalcanzable

#### Paso 4: Identificar Funciones/Clases No Utilizadas

**Proceso:**
- Buscar definiciones de funciones/clases
- Verificar que se usan en algún lugar
- Buscar imports de funciones/clases
- Identificar funciones/clases sin uso

**Explicación:**
- Usar grep para buscar usos de funciones/clases
- Verificar que no se usan en tests ni en código interno
- **Eliminar agresivamente** funciones/clases no utilizadas (no hay usuarios externos)
- No mantener código "por si acaso" - si no se usa, eliminarlo

#### Paso 5: Eliminar Código Muerto

**Archivos a modificar:**
- Cualquier archivo con código muerto identificado

**Explicación:**
- Eliminar imports no utilizados de forma agresiva
- Eliminar variables no utilizadas (excepto las necesarias para type hints)
- Eliminar funciones/clases no utilizadas sin preocuparse por usuarios externos
- Eliminar código inalcanzable
- Verificar que los tests internos siguen pasando

#### Paso 6: Verificar Tests

**Comando:**
```bash
uv run pytest tests/ -v
```

**Explicación:**
- Ejecutar todos los tests después de eliminar código muerto
- Verificar que no se rompió nada
- Corregir cualquier problema

### Tests Requeridos

**Verificar que los tests siguen pasando:**

```bash
uv run pytest tests/ -v
```

**Explicación:**
- Ejecutar todos los tests
- Verificar que no hay regresiones
- Corregir cualquier test roto

### Criterios de Éxito

- [ ] `uv run ruff check --select F401 src/soni` no reporta imports no utilizados
- [ ] `uv run ruff check --select F841 src/soni` no reporta variables no utilizadas
- [ ] Código inalcanzable eliminado
- [ ] Funciones/clases no utilizadas eliminadas
- [ ] Todos los tests siguen pasando
- [ ] Cambios documentados

### Validación Manual

**Comandos para validar:**
```bash
# Imports no utilizados
uv run ruff check --select F401 src/soni

# Variables no utilizadas
uv run ruff check --select F841 src/soni

# Ejecutar tests
uv run pytest tests/ -v

# Verificar linting general
uv run ruff check .
```

**Resultado esperado:**
- No hay imports no utilizados
- No hay variables no utilizadas
- Código muerto eliminado
- Tests siguen pasando
- Linting pasa sin errores

### Referencias

- `docs/implementation/99-validation.md` - Sección 12: Identify Dead Code
- `AGENTS.md` - Code Conventions
- `pyproject.toml` - Configuración de ruff

### Notas Adicionales

- **No hay retrocompatibilidad que mantener**: Eliminar código muerto de forma agresiva
- Algunas variables pueden ser necesarias para type hints o documentación - mantener solo estas
- **No mantener funciones/clases "públicas" no usadas** - si no se usan en el código interno ni en tests, eliminarlas
- Si el código no se usa en ningún lugar (código interno, tests, ejemplos), eliminarlo directamente
- No documentar "código que se mantiene aunque parezca no usado" - si no se usa, eliminarlo
