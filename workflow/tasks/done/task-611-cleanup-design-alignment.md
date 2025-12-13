## Task: 611 - Cleanup: Verify Design Alignment

**ID de tarea:** 611
**Hito:** 6 - Final Validation & Cleanup
**Dependencias:** Task 610 (Cleanup: Dead Code)
**Duración estimada:** 2 horas

### Objetivo

Verificar que todos los módulos en `src/soni/` se alinean con el diseño especificado en la documentación, eliminando módulos que no coinciden con el diseño actual.

### Contexto

Después de un refactoring, puede haber módulos que:
- No están en el diseño actual
- Fueron reemplazados por otros módulos
- No se alinean con la arquitectura actual
- Están obsoletos o fueron deprecados

**Importante**: Como la librería aún no está en uso, podemos eliminar módulos no alineados con el diseño de forma agresiva. No hay necesidad de mantener módulos obsoletos "por compatibilidad" - si no están en el diseño y no se usan, eliminarlos.

Referencia: `docs/implementation/99-validation.md` - Sección 13: Verify Design Alignment

### Entregables

- [ ] Módulos comparados con diseño
- [ ] Módulos no alineados identificados
- [ ] Módulos no alineados eliminados o documentados
- [ ] Desalineaciones documentadas
- [ ] Código actualizado para alinearse con diseño

### Implementación Detallada

#### Paso 1: Revisar Documentación de Diseño

**Archivo:** `docs/design/03-components.md`

**Explicación:**
- Leer documentación de componentes esperados
- Listar módulos esperados según diseño
- Identificar estructura esperada
- Documentar componentes esperados

#### Paso 2: Comparar con Estructura Actual

**Comando:**
```bash
find src/soni -type f -name "*.py" | sort
```

**Explicación:**
- Listar todos los archivos Python en `src/soni/`
- Comparar con lista de componentes esperados
- Identificar módulos que no están en el diseño
- Identificar módulos faltantes según diseño

#### Paso 3: Verificar Módulos No Alineados

**Proceso:**
- Para cada módulo no en el diseño, verificar:
  - ¿Está obsoleto?
  - ¿Fue reemplazado?
  - ¿Es necesario mantenerlo?
  - ¿Debe eliminarse?

**Explicación:**
- Revisar cada módulo no alineado
- Verificar si se usa en código interno, tests o ejemplos
- **Si no está en el diseño y no se usa, eliminarlo directamente**
- No mantener módulos "por si acaso" - el diseño es la fuente de verdad

#### Paso 4: Eliminar Módulos No Alineados

**Archivos a eliminar:**
- Módulos obsoletos identificados
- Módulos reemplazados
- Módulos que no están en el diseño

**Explicación:**
- Eliminar agresivamente módulos no alineados con el diseño
- Actualizar imports si es necesario
- Verificar que los tests internos siguen pasando (no hay usuarios externos)

#### Paso 5: Documentar Desalineaciones

**Archivo a actualizar:** `docs/implementation/99-validation.md` - Sección Cleanup Report

**Explicación:**
- Documentar módulos eliminados y por qué (no estaban en diseño)
- **No mantener módulos fuera del diseño** - si no están en el diseño, eliminarlos
- Documentar módulos faltantes según diseño (para futuras tareas)

### Tests Requeridos

**Verificar que los tests siguen pasando:**

```bash
uv run pytest tests/ -v
```

**Explicación:**
- Ejecutar todos los tests después de cambios
- Verificar que no se rompió nada
- Corregir cualquier problema

### Criterios de Éxito

- [ ] Módulos comparados con diseño documentado
- [ ] Módulos no alineados identificados
- [ ] Módulos no alineados eliminados o documentados (con justificación)
- [ ] Desalineaciones documentadas
- [ ] Todos los tests siguen pasando
- [ ] Cambios documentados en cleanup report

### Validación Manual

**Comandos para validar:**
```bash
# Listar estructura actual
find src/soni -type f -name "*.py" | sort

# Comparar con diseño
cat docs/design/03-components.md

# Verificar imports
grep -r "from soni\." src/ tests/ examples/

# Ejecutar tests
uv run pytest tests/ -v
```

**Resultado esperado:**
- Módulos alineados con diseño
- Módulos no alineados identificados y manejados
- Tests siguen pasando
- Cambios documentados

### Referencias

- `docs/implementation/99-validation.md` - Sección 13: Verify Design Alignment
- `docs/design/03-components.md` - Componentes esperados
- `src/soni/` - Estructura actual del código

### Notas Adicionales

- **No hay retrocompatibilidad que mantener**: Si un módulo no está en el diseño, eliminarlo
- **El diseño es la fuente de verdad**: Si no está en `docs/design/03-components.md` y no se usa en código interno, eliminarlo
- No mantener módulos "por si acaso" - si no están en el diseño, no son necesarios
- Si un módulo es realmente necesario pero no está en el diseño, primero actualizar el diseño, luego mantener el módulo
- Identificar módulos faltantes según diseño para futuras tareas
