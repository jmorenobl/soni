## Task: 603 - Integration Tests Validation

**ID de tarea:** 603
**Hito:** 6 - Final Validation & Cleanup
**Dependencias:** Task 602 (Test Coverage Validation)
**Duración estimada:** 2 horas

### Objetivo

Validar que todos los tests de integración pasan correctamente, incluyendo flujos de diálogo end-to-end y endpoints de API.

### Contexto

Los tests de integración validan que los componentes trabajan correctamente juntos. Es crítico verificar:
- Flujos de diálogo completos funcionan correctamente
- Endpoints de API responden como se espera
- Interrupciones y reanudaciones de flujos funcionan

Referencia: `docs/implementation/99-validation.md` - Sección 3: Integration Tests

### Entregables

- [ ] Test de flujo de diálogo end-to-end pasa
- [ ] Tests de endpoints de API pasan
- [ ] Flujos con interrupciones funcionan correctamente
- [ ] Cualquier test fallido corregido

### Implementación Detallada

#### Paso 1: Ejecutar Test de Flujo de Diálogo

**Comando:**
```bash
uv run pytest tests/integration/test_dialogue_flow.py -v
```

**Explicación:**
- Ejecutar test de flujo end-to-end
- Verificar que el flujo completo funciona
- Verificar que las interrupciones funcionan
- Documentar cualquier fallo

#### Paso 2: Ejecutar Tests de API

**Comando:**
```bash
uv run pytest tests/integration/test_api.py -v
```

**Explicación:**
- Ejecutar todos los tests de endpoints de API
- Verificar que todos los endpoints responden correctamente
- Verificar manejo de errores en endpoints
- Documentar cualquier fallo

#### Paso 3: Corregir Tests Fallidos (si aplica)

**Archivos potenciales a modificar:**
- `tests/integration/test_dialogue_flow.py`
- `tests/integration/test_api.py`
- Código fuente que cause fallos en tests

**Explicación:**
- Identificar causa raíz de fallos
- Corregir código o tests según corresponda
- Verificar que correcciones no rompen otros tests

#### Paso 4: Verificar Flujos con Interrupciones

**Explicación:**
- Asegurar que los tests cubren escenarios de interrupción
- Verificar que los flujos se pueden reanudar correctamente
- Documentar comportamiento esperado

### Tests Requeridos

**Verificar que los siguientes tests existen y pasan:**

```python
# En tests/integration/test_dialogue_flow.py
def test_complete_dialogue_flow():
    """Test que valida un flujo de diálogo completo end-to-end"""
    # Arrange
    # Act
    # Assert

def test_dialogue_flow_with_interrupt():
    """Test que valida interrupción y reanudación de flujo"""
    # Arrange
    # Act
    # Assert

# En tests/integration/test_api.py
def test_health_endpoint():
    """Test que valida el endpoint de health check"""
    # Arrange
    # Act
    # Assert

def test_message_endpoint():
    """Test que valida el endpoint de mensajes"""
    # Arrange
    # Act
    # Assert
```

### Criterios de Éxito

- [ ] `uv run pytest tests/integration/test_dialogue_flow.py -v` pasa sin errores
- [ ] `uv run pytest tests/integration/test_api.py -v` pasa sin errores
- [ ] Flujos con interrupciones funcionan correctamente
- [ ] Todos los endpoints de API responden como se espera
- [ ] No hay tests fallidos

### Validación Manual

**Comandos para validar:**
```bash
# Test de flujo de diálogo
uv run pytest tests/integration/test_dialogue_flow.py -v

# Tests de API
uv run pytest tests/integration/test_api.py -v

# Todos los tests de integración
uv run pytest tests/integration/ -v
```

**Resultado esperado:**
- Todos los tests de integración pasan
- Flujos end-to-end funcionan correctamente
- Endpoints de API responden correctamente

### Referencias

- `docs/implementation/99-validation.md` - Sección 3: Integration Tests
- `tests/integration/test_dialogue_flow.py`
- `tests/integration/test_api.py`

### Notas Adicionales

- Si hay tests fallidos, priorizar corrección de tests críticos
- Asegurar que los tests cubren casos de éxito y error
- Verificar que los tests son determinísticos y no dependen de estado externo
