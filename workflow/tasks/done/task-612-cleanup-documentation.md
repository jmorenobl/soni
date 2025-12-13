## Task: 612 - Cleanup: Update Documentation

**ID de tarea:** 612
**Hito:** 6 - Final Validation & Cleanup
**Dependencias:** Task 611 (Cleanup: Design Alignment)
**Duración estimada:** 3 horas

### Objetivo

Actualizar la documentación para reflejar los cambios realizados durante la limpieza: eliminar referencias a módulos eliminados, actualizar ejemplos de imports, y verificar que todos los ejemplos de código funcionan.

### Contexto

Después de eliminar módulos y código muerto, la documentación puede quedar desactualizada:
- Referencias a módulos eliminados
- Ejemplos de imports incorrectos
- Ejemplos de código que no funcionan
- Referencias a funcionalidades eliminadas

**Importante**: Como la librería aún no está en uso, podemos actualizar la documentación de forma agresiva, eliminando referencias a código obsoleto sin preocuparnos por usuarios que dependan de documentación antigua.

Referencia: `docs/implementation/99-validation.md` - Sección 14: Clean Up Documentation

### Entregables

- [ ] Referencias a módulos eliminados removidas
- [ ] Ejemplos de imports actualizados
- [ ] Ejemplos de código verificados y actualizados
- [ ] Documentación consistente con código actual
- [ ] Cambios documentados

### Implementación Detallada

#### Paso 1: Buscar Referencias a Módulos Eliminados

**Proceso:**
- Listar módulos eliminados en tareas anteriores
- Buscar referencias en documentación
- Identificar archivos que necesitan actualización

**Comando:**
```bash
# Buscar referencias a módulos eliminados
grep -r "soni.config" docs/
grep -r "from soni.config" docs/
```

**Explicación:**
- Buscar referencias a módulos eliminados
- Identificar archivos de documentación afectados
- Listar cambios necesarios

#### Paso 2: Actualizar Ejemplos de Imports

**Archivos a revisar:**
- `docs/api/**/*.md` - Documentación de API
- `docs/design/**/*.md` - Documentación de diseño
- `docs/implementation/**/*.md` - Documentación de implementación
- `README.md` - README principal
- `AGENTS.md` - Documentación para agentes

**Explicación:**
- Revisar ejemplos de imports en documentación
- Actualizar imports a rutas correctas
- Verificar que los imports funcionan
- Documentar cambios

#### Paso 3: Verificar Ejemplos de Código

**Proceso:**
- Revisar ejemplos de código en documentación
- Probar que los ejemplos funcionan
- Actualizar ejemplos que no funcionan
- Eliminar ejemplos obsoletos

**Explicación:**
- Para cada ejemplo de código:
  - Verificar que los imports son correctos
  - Verificar que el código funciona
  - Actualizar si es necesario
  - Eliminar si está obsoleto

#### Paso 4: Actualizar Referencias a Funcionalidades

**Proceso:**
- Buscar referencias a funcionalidades eliminadas
- Actualizar o eliminar referencias
- Verificar que la documentación es consistente

**Explicación:**
- Buscar referencias a funcionalidades que ya no existen
- **Eliminar agresivamente** secciones obsoletas - no hay usuarios que dependan de documentación antigua
- Actualizar documentación para reflejar solo el estado actual del código

#### Paso 5: Verificar Consistencia

**Proceso:**
- Revisar que la documentación es consistente
- Verificar que no hay contradicciones
- Asegurar que todos los ejemplos funcionan

**Explicación:**
- Revisar documentación completa
- Verificar consistencia entre documentos
- Corregir contradicciones
- Asegurar que ejemplos funcionan

### Tests Requeridos

**No se requieren tests automatizados**, pero se debe:
- Verificar manualmente que los ejemplos funcionan
- Probar comandos documentados
- Verificar que las referencias son correctas

### Criterios de Éxito

- [ ] Referencias a módulos eliminados removidas
- [ ] Ejemplos de imports actualizados y funcionando
- [ ] Ejemplos de código verificados y funcionando
- [ ] Documentación consistente con código actual
- [ ] No hay referencias rotas
- [ ] Cambios documentados

### Validación Manual

**Comandos para validar:**
```bash
# Buscar referencias a módulos eliminados
grep -r "soni.config" docs/

# Verificar ejemplos de código (manual)
# Revisar documentación y probar ejemplos

# Verificar links rotos (si hay herramienta)
# Usar herramienta de validación de links en markdown
```

**Resultado esperado:**
- No hay referencias a módulos eliminados
- Ejemplos de código funcionan
- Documentación es consistente
- No hay referencias rotas

### Referencias

- `docs/implementation/99-validation.md` - Sección 14: Clean Up Documentation
- `docs/api/` - Documentación de API
- `docs/design/` - Documentación de diseño
- `docs/implementation/` - Documentación de implementación
- `README.md` - README principal
- `AGENTS.md` - Documentación para agentes

### Notas Adicionales

- Priorizar actualización de documentación crítica (README, AGENTS.md)
- Verificar que los ejemplos de código están actualizados
- Considerar usar herramientas de validación de links en markdown
- Documentar cambios significativos en documentación
