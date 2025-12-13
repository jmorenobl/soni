## Task: 601 - Code Quality Validation

**ID de tarea:** 601
**Hito:** 6 - Final Validation & Cleanup
**Dependencias:** Todas las fases 1-5 completadas
**Duración estimada:** 2 horas

### Objetivo

Validar que todo el código cumple con los estándares de calidad: type checking sin errores, linting sin errores, y formato consistente en todo el proyecto.

### Contexto

Antes de considerar el refactoring completo, es crítico asegurar que:
- Todos los tipos están correctamente anotados y verificados
- El código sigue las convenciones de estilo (PEP 8, ruff)
- No hay errores de linting que puedan causar problemas en producción

Referencia: `docs/implementation/99-validation.md` - Sección 1: Code Quality

### Entregables

- [ ] Type checking con mypy pasa sin errores
- [ ] Linting con ruff pasa sin errores
- [ ] Formato con ruff format verificado
- [ ] Todos los errores encontrados corregidos y documentados

### Implementación Detallada

#### Paso 1: Ejecutar Type Checking

**Comando:**
```bash
uv run mypy src/soni
```

**Explicación:**
- Ejecutar mypy en todo el código fuente
- Documentar todos los errores encontrados
- Corregir errores de tipos uno por uno
- Verificar que no quedan errores

#### Paso 2: Ejecutar Linting

**Comando:**
```bash
uv run ruff check .
```

**Explicación:**
- Ejecutar ruff check en todo el proyecto
- Documentar todos los errores encontrados
- Corregir errores de linting
- Verificar que no quedan errores

#### Paso 3: Verificar Formato

**Comando:**
```bash
uv run ruff format --check .
```

**Explicación:**
- Verificar que todos los archivos están formateados correctamente
- Si hay archivos sin formato, ejecutar `uv run ruff format .`
- Verificar que todos los archivos quedan formateados

#### Paso 4: Corregir Errores Encontrados

**Archivos potenciales a modificar:**
- Cualquier archivo con errores de tipo
- Cualquier archivo con errores de linting
- Cualquier archivo sin formato

**Explicación:**
- Corregir errores sistemáticamente
- Mantener el estilo consistente
- Asegurar que las correcciones no rompen funcionalidad existente

### Tests Requeridos

**No se requieren tests nuevos**, pero se debe verificar que:
- Todos los tests existentes siguen pasando después de las correcciones
- No se introdujeron regresiones

**Comando para verificar:**
```bash
uv run pytest tests/ -v
```

### Criterios de Éxito

- [ ] `uv run mypy src/soni` retorna exit code 0 sin errores
- [ ] `uv run ruff check .` retorna exit code 0 sin errores
- [ ] `uv run ruff format --check .` retorna exit code 0 (todos formateados)
- [ ] Todos los tests existentes siguen pasando
- [ ] Errores corregidos documentados en el commit

### Validación Manual

**Comandos para validar:**
```bash
# Type checking
uv run mypy src/soni

# Linting
uv run ruff check .

# Formato
uv run ruff format --check .

# Verificar tests siguen pasando
uv run pytest tests/ -v
```

**Resultado esperado:**
- Todos los comandos retornan exit code 0
- No hay errores reportados
- Todos los tests pasan

### Referencias

- `docs/implementation/99-validation.md` - Sección 1: Code Quality
- `AGENTS.md` - Code Conventions
- `pyproject.toml` - Configuración de ruff y mypy

### Notas Adicionales

- Si hay errores de tipo complejos, documentarlos y considerar si requieren refactoring adicional
- Priorizar correcciones que afecten la funcionalidad sobre mejoras estéticas
- Mantener consistencia con el estilo existente del proyecto
