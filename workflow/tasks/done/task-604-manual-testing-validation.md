## Task: 604 - Manual Testing and Server Validation

**ID de tarea:** 604
**Hito:** 6 - Final Validation & Cleanup
**Dependencias:** Task 603 (Integration Tests Validation)
**Duración estimada:** 2 horas

### Objetivo

Validar manualmente que el servidor FastAPI inicia correctamente y que los endpoints responden como se espera en un entorno real.

### Contexto

Aunque los tests automatizados son importantes, la validación manual del servidor es crucial para:
- Verificar que el servidor inicia sin errores
- Validar respuestas reales de endpoints
- Probar flujos de diálogo en un entorno más realista

Referencia: `docs/implementation/99-validation.md` - Sección 4: Manual Testing

### Entregables

- [ ] Servidor FastAPI inicia sin errores
- [ ] Endpoint de health check responde correctamente
- [ ] Endpoint de mensajes funciona correctamente
- [ ] Flujo de diálogo completo probado manualmente
- [ ] Resultados documentados

### Implementación Detallada

#### Paso 1: Iniciar Servidor

**Comando:**
```bash
uv run uvicorn soni.server.api:app --reload
```

**Explicación:**
- Iniciar servidor FastAPI en modo desarrollo
- Verificar que no hay errores al iniciar
- Verificar que el servidor escucha en el puerto correcto
- Documentar cualquier error o advertencia

#### Paso 2: Probar Health Check

**Comando:**
```bash
curl http://localhost:8000/health
```

**Resultado esperado:**
```json
{
  "status": "healthy",
  "version": "0.8.0",
  "graph_initialized": true
}
```

**Explicación:**
- Verificar que el endpoint responde
- Verificar que el formato JSON es correcto
- Verificar que los campos esperados están presentes
- Documentar cualquier discrepancia

#### Paso 3: Probar Flujo de Mensajes

**Comando 1 - Iniciar booking:**
```bash
curl -X POST http://localhost:8000/message \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": "test-user-1",
    "message": "I want to book a flight"
  }'
```

**Comando 2 - Proporcionar slot:**
```bash
curl -X POST http://localhost:8000/message \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": "test-user-1",
    "message": "From Madrid"
  }'
```

**Explicación:**
- Verificar que el primer mensaje inicia el flujo correctamente
- Verificar que el segundo mensaje actualiza el estado
- Verificar que las respuestas son apropiadas en cada paso
- Documentar cualquier comportamiento inesperado

#### Paso 4: Probar Flujo Completo

**Explicación:**
- Probar un flujo de diálogo completo desde inicio hasta fin
- Verificar que el estado se mantiene entre mensajes
- Verificar que las transiciones de estado funcionan
- Documentar el flujo probado

### Tests Requeridos

**No se requieren tests automatizados**, pero se debe:
- Documentar los casos probados manualmente
- Registrar cualquier comportamiento inesperado
- Verificar que los resultados coinciden con los tests automatizados

### Criterios de Éxito

- [ ] Servidor inicia sin errores
- [ ] Health check responde con formato correcto
- [ ] Endpoint de mensajes procesa mensajes correctamente
- [ ] Flujo de diálogo completo funciona manualmente
- [ ] Respuestas son apropiadas en cada paso
- [ ] Resultados documentados

### Validación Manual

**Comandos para validar:**
```bash
# Iniciar servidor
uv run uvicorn soni.server.api:app --reload

# En otra terminal, probar health check
curl http://localhost:8000/health

# Probar mensajes
curl -X POST http://localhost:8000/message \
  -H "Content-Type: application/json" \
  -d '{"user_id": "test-user-1", "message": "I want to book a flight"}'

curl -X POST http://localhost:8000/message \
  -H "Content-Type: application/json" \
  -d '{"user_id": "test-user-1", "message": "From Madrid"}'
```

**Resultado esperado:**
- Servidor inicia correctamente
- Health check retorna JSON válido con status "healthy"
- Mensajes se procesan y retornan respuestas apropiadas
- Flujo completo funciona como se espera

### Referencias

- `docs/implementation/99-validation.md` - Sección 4: Manual Testing
- `src/soni/server/api.py` - Endpoints de FastAPI
- `examples/flight_booking/soni.yaml` - Configuración de ejemplo

### Notas Adicionales

- Si hay errores al iniciar el servidor, verificar configuración y dependencias
- Probar con diferentes usuarios para verificar aislamiento de estado
- Considerar probar casos de error (mensajes inválidos, usuarios no existentes, etc.)
