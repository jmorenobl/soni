## Task: 609 - Cleanup: Identify and Remove Empty/Unused Modules

**ID de tarea:** 609
**Hito:** 6 - Final Validation & Cleanup
**Dependencias:** Task 608 (Architectural Compliance Validation)
**Duración estimada:** 2 horas

### Objetivo

Identificar y eliminar módulos vacíos o no utilizados que no se alinean con el diseño actual del framework.

### Contexto

Después de un refactoring mayor, pueden quedar módulos vacíos o no utilizados que:
- No se alinean con el diseño actual
- Están obsoletos o fueron reemplazados
- No tienen funcionalidad y solo ocupan espacio

**Importante**: Como la librería aún no está en uso, no hay necesidad de mantener retrocompatibilidad. Podemos eliminar código obsoleto de forma agresiva sin preocuparnos por romper código de usuarios externos.

Referencia: `docs/implementation/99-validation.md` - Sección 11: Identify Empty/Unused Modules

### Entregables

- [ ] Módulos vacíos identificados
- [ ] Módulos no utilizados identificados
- [ ] Módulos eliminados (si aplica)
- [ ] Cambios documentados
- [ ] Imports actualizados si es necesario

### Implementación Detallada

#### Paso 1: Identificar Módulos Vacíos

**Comando:**
```bash
find src/soni -name "__init__.py" -exec sh -c 'if [ ! -s "$1" ]; then echo "$1 is empty"; fi' _ {} \;
```

**Explicación:**
- Buscar todos los `__init__.py` vacíos
- Documentar módulos encontrados
- Verificar si son necesarios o pueden eliminarse

#### Paso 2: Identificar Directorios No Utilizados

**Proceso:**
- Revisar estructura de `src/soni/`
- Verificar que cada directorio tiene propósito
- Buscar imports para confirmar uso
- Comparar con diseño en `docs/design/03-components.md`

**Explicación:**
- Listar todos los directorios en `src/soni/`
- Verificar que cada uno está en el diseño
- Buscar referencias en código
- Identificar directorios sin uso

#### Paso 3: Verificar Imports

**Comando:**
```bash
grep -r "from soni\." src/ tests/ examples/
```

**Explicación:**
- Buscar todos los imports de módulos
- Verificar que los módulos importados existen
- Identificar módulos sin imports
- Documentar módulos no utilizados

#### Paso 4: Eliminar Módulos No Necesarios

**Archivos a eliminar:**
- Módulos vacíos identificados
- Directorios no utilizados
- Archivos obsoletos

**Explicación:**
- Eliminar módulos vacíos que no son necesarios
- Eliminar directorios no utilizados de forma agresiva
- Actualizar imports si es necesario
- Verificar que los tests internos siguen pasando (no hay usuarios externos que romper)

#### Paso 5: Documentar Cambios

**Archivo a actualizar:** `docs/implementation/99-validation.md` - Sección Cleanup Report

**Explicación:**
- Documentar módulos eliminados
- Explicar por qué se eliminaron
- Verificar que los cambios están documentados

### Tests Requeridos

**Verificar que los tests siguen pasando:**

```bash
uv run pytest tests/ -v
```

**Explicación:**
- Ejecutar todos los tests después de eliminar módulos
- Verificar que no se rompió nada
- Corregir imports rotos si es necesario

### Criterios de Éxito

- [ ] Módulos vacíos identificados y documentados
- [ ] Módulos no utilizados identificados y documentados
- [ ] Módulos eliminados (si aplica)
- [ ] Imports actualizados si es necesario
- [ ] Todos los tests siguen pasando
- [ ] Cambios documentados en cleanup report

### Validación Manual

**Comandos para validar:**
```bash
# Identificar módulos vacíos
find src/soni -name "__init__.py" -exec sh -c 'if [ ! -s "$1" ]; then echo "$1 is empty"; fi' _ {} \;

# Verificar estructura
ls -la src/soni/

# Verificar imports
grep -r "from soni\." src/ tests/ examples/

# Ejecutar tests
uv run pytest tests/ -v
```

**Resultado esperado:**
- Módulos vacíos/no utilizados identificados
- Módulos eliminados si es necesario
- Tests siguen pasando
- Cambios documentados

### Referencias

- `docs/implementation/99-validation.md` - Sección 11: Identify Empty/Unused Modules
- `docs/design/03-components.md` - Componentes esperados
- `src/soni/` - Estructura actual del código

### Notas Adicionales

- **No hay retrocompatibilidad que mantener**: Como nadie usa la librería aún, podemos eliminar módulos obsoletos de forma agresiva
- Eliminar cualquier módulo que no esté en el diseño actual, sin preocuparnos por código de usuarios externos
- Algunos `__init__.py` vacíos pueden ser necesarios para imports, pero eliminar los que no son necesarios
- Si un módulo no está en el diseño y no se usa en el código interno, eliminarlo directamente
- Verificar que los módulos eliminados no están en el diseño antes de eliminarlos
