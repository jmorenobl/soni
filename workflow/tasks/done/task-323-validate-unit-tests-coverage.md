## Task: 323 - Validación Final de Cobertura de Tests Unitarios

**ID de tarea:** 323
**Hito:** Tests Unitarios - Cobertura >85%
**Dependencias:** Todas las tareas de tests unitarios (308-322)
**Duración estimada:** 2-3 horas

### Objetivo

Validar que se ha alcanzado cobertura >85% en tests unitarios y que todos los criterios de calidad se cumplen.

### Contexto

Después de implementar todos los tests unitarios según el análisis, se debe validar:
- Cobertura total >85%
- Cobertura de módulos críticos >90%
- Todos los tests pasan
- Tests son deterministas
- Tests son rápidos
- Tests son independientes

### Entregables

- [ ] Reporte de cobertura total >85%
- [ ] Reporte de cobertura por módulo
- [ ] Verificación de que todos los tests pasan
- [ ] Verificación de determinismo
- [ ] Verificación de velocidad
- [ ] Verificación de independencia
- [ ] Documentación de resultados

### Implementación Detallada

#### Paso 1: Ejecutar Suite Completa de Tests

**Comandos:**

```bash
# Ejecutar todos los tests unitarios
uv run pytest tests/unit/ -v

# Verificar que todos pasan
uv run pytest tests/unit/ --tb=short
```

**Resultado esperado:**
- 100% de tests pasando
- Sin errores ni warnings críticos

#### Paso 2: Generar Reporte de Cobertura

**Comandos:**

```bash
# Cobertura completa con branches
uv run pytest tests/unit/ \
    --cov=src/soni \
    --cov-branch \
    --cov-report=term-missing \
    --cov-report=html

# Verificar cobertura por módulo
uv run pytest tests/unit/ \
    --cov=src/soni \
    --cov-report=term-missing | grep -E "(dm/routing|dm/nodes|runtime|flow|du|utils)"
```

**Resultado esperado:**
- Cobertura total >85%
- Cobertura de módulos críticos >90%

#### Paso 3: Verificar Determinismo

**Comandos:**

```bash
# Ejecutar tests en orden aleatorio múltiples veces
for i in {1..5}; do
    echo "Run $i:"
    uv run pytest tests/unit/ --random-order -q || exit 1
done
```

**Resultado esperado:**
- Todos los runs pasan
- Sin tests flaky

#### Paso 4: Verificar Velocidad

**Comandos:**

```bash
# Ver tests más lentos
uv run pytest tests/unit/ --durations=20

# Verificar tiempo total
time uv run pytest tests/unit/ -q
```

**Resultado esperado:**
- Suite completa <10 minutos
- Tests individuales <1 segundo cada uno

#### Paso 5: Verificar Independencia

**Comandos:**

```bash
# Ejecutar en orden aleatorio
uv run pytest tests/unit/ --random-order -v

# Ejecutar tests específicos aislados
uv run pytest tests/unit/test_dm_routing.py -v
uv run pytest tests/unit/test_dm_nodes_handle_correction.py -v
```

**Resultado esperado:**
- Tests pasan en cualquier orden
- Tests no dependen de estado global

#### Paso 6: Generar Reporte Final

**Crear documento:** `docs/testing/unit-tests-coverage-report.md`

**Contenido del reporte:**

```markdown
# Reporte de Cobertura de Tests Unitarios

**Fecha**: [Fecha]
**Cobertura Total**: [X]%
**Objetivo**: >85%
**Estado**: ✅ Alcanzado / ❌ No alcanzado

## Cobertura por Módulo

| Módulo | Cobertura | Estado |
|--------|-----------|--------|
| dm/routing.py | [X]% | ✅/❌ |
| dm/nodes/handle_correction.py | [X]% | ✅/❌ |
| ... | ... | ... |

## Métricas de Calidad

- **Tests totales**: [X]
- **Tests pasando**: [X] (100%)
- **Tiempo de ejecución**: [X] minutos
- **Tests flaky**: 0
- **Determinismo**: ✅

## Módulos que Requieren Atención

[Lista de módulos con cobertura <85% si los hay]

## Próximos Pasos

[Recomendaciones si no se alcanzó el objetivo]
```

### Criterios de Éxito

- [ ] Cobertura total >85%
- [ ] Cobertura de módulos críticos >90%
- [ ] Todos los tests pasan (100% pass rate)
- [ ] Tests son deterministas (0 tests flaky)
- [ ] Suite completa ejecuta en <10 minutos
- [ ] Tests son independientes (pasan en orden aleatorio)
- [ ] Reporte de cobertura generado
- [ ] Documentación actualizada

### Validación Manual

**Comandos finales:**

```bash
# Suite completa con todas las métricas
uv run pytest tests/unit/ \
    --cov=src/soni \
    --cov-branch \
    --cov-report=term-missing \
    --cov-report=html \
    --durations=10 \
    --random-order \
    -v

# Verificar HTML report
open htmlcov/index.html
```

**Resultado esperado:**
- Cobertura >85% visible en reporte
- Todos los módulos críticos >90%
- HTML report generado correctamente

### Referencias

- `docs/analysis/ANALISIS_TESTS_UNITARIOS_COBERTURA.md` - Sección 7
- `docs/analysis/GUIA_IMPLEMENTACION_TESTS_UNITARIOS.md` - Sección 4
- `docs/testing/unit-tests-coverage-report.md` - Reporte generado

### Notas Adicionales

- Si no se alcanza 85%, identificar módulos faltantes y crear tareas adicionales
- Documentar cualquier deuda técnica o limitación encontrada
- Celebrar el logro si se alcanza el objetivo 🎉
