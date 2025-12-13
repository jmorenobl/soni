## Task: 602 - Test Coverage Validation

**ID de tarea:** 602
**Hito:** 6 - Final Validation & Cleanup
**Dependencias:** Task 601 (Code Quality Validation)
**Duración estimada:** 3 horas

### Objetivo

Validar que todos los tests pasan y que la cobertura de código alcanza al menos el 80% requerido, identificando áreas críticas sin cobertura.

### Contexto

La cobertura de tests es un indicador clave de calidad y confiabilidad. Antes de considerar el proyecto listo para producción, debemos:
- Asegurar que todos los tests pasan
- Verificar que la cobertura mínima (80%) se cumple
- Identificar y documentar áreas críticas sin cobertura

Referencia: `docs/implementation/99-validation.md` - Sección 2: Test Coverage

### Entregables

- [ ] Todos los tests unitarios pasan
- [ ] Todos los tests de integración pasan
- [ ] Cobertura ≥ 80% verificada
- [ ] Reporte de cobertura generado y revisado
- [ ] Áreas críticas sin cobertura documentadas (si las hay)

### Implementación Detallada

#### Paso 1: Ejecutar Todos los Tests

**Comando:**
```bash
uv run pytest tests/ -v
```

**Explicación:**
- Ejecutar todos los tests (unitarios e integración)
- Documentar cualquier test que falle
- Corregir tests rotos o código que cause fallos
- Verificar que todos los tests pasan

#### Paso 2: Generar Reporte de Cobertura

**Comando:**
```bash
uv run pytest tests/ --cov=soni --cov-report=term-missing --cov-report=html
```

**Explicación:**
- Generar reporte de cobertura en terminal y HTML
- Verificar que la cobertura total ≥ 80%
- Identificar módulos con baja cobertura
- Documentar áreas críticas sin cobertura

#### Paso 3: Revisar Reporte HTML

**Comando:**
```bash
open htmlcov/index.html
```

**Explicación:**
- Abrir reporte HTML en navegador
- Revisar módulos con baja cobertura
- Identificar funciones/métodos críticos sin tests
- Priorizar áreas que requieren más tests

#### Paso 4: Documentar Resultados

**Archivo a crear/modificar:** `docs/validation/test-coverage-report.md` (opcional)

**Explicación:**
- Documentar cobertura por módulo
- Listar áreas críticas sin cobertura
- Proponer tests adicionales si es necesario (para futuras tareas)

### Tests Requeridos

**No se requieren tests nuevos**, pero se debe:
- Verificar que todos los tests existentes pasan
- Identificar gaps de cobertura para futuras mejoras

### Criterios de Éxito

- [ ] `uv run pytest tests/ -v` retorna exit code 0 con todos los tests pasando
- [ ] Cobertura total ≥ 80% verificada
- [ ] Reporte HTML generado en `htmlcov/index.html`
- [ ] Áreas críticas sin cobertura documentadas (si aplica)
- [ ] No hay tests rotos o fallando

### Validación Manual

**Comandos para validar:**
```bash
# Ejecutar todos los tests
uv run pytest tests/ -v

# Generar reporte de cobertura
uv run pytest tests/ --cov=soni --cov-report=term-missing --cov-report=html

# Abrir reporte HTML
open htmlcov/index.html
```

**Resultado esperado:**
- Todos los tests pasan
- Cobertura ≥ 80%
- Reporte HTML generado correctamente
- Áreas críticas identificadas y documentadas

### Referencias

- `docs/implementation/99-validation.md` - Sección 2: Test Coverage
- `AGENTS.md` - Testing Conventions
- `pyproject.toml` - Configuración de pytest y coverage

### Notas Adicionales

- Si la cobertura está por debajo del 80%, priorizar tests para módulos críticos
- No es necesario alcanzar 100% de cobertura, pero sí cubrir todos los paths críticos
- Documentar decisiones sobre áreas que no requieren tests (ej: código experimental)
