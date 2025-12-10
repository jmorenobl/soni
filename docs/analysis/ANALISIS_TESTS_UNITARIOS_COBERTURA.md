# Análisis Exhaustivo de Tests Unitarios para Cobertura >85%

**Fecha**: 2025-12-10
**Objetivo**: Identificar tests unitarios necesarios para alcanzar cobertura >85% manteniendo NLU controlado
**Alcance**: Tests unitarios únicamente (no tests de integración)
**Metodología**: Tests deterministas con NLU mockeado para control total

---

## 1. Resumen Ejecutivo

### Estado Actual de Cobertura (Tests Unitarios Solamente)

Según el reporte de cobertura actual de `pytest tests/unit/`:
- **Cobertura Total Tests Unitarios**: 66.23%
- **Objetivo**: >85% de cobertura
- **Gap**: 18.77% adicional necesario
- **Tests actuales**: 596 tests unitarios pasando

**IMPORTANTE**: Este análisis se enfoca EXCLUSIVAMENTE en tests unitarios con NLU mockeado. Los tests de integración se analizarán por separado.

### Módulos con Baja Cobertura

#### Prioridad CRÍTICA (Cobertura <50%)

| Módulo | Cobertura | Gap | LOC | Tests Estimados |
|--------|-----------|-----|-----|-----------------|
| `dm/nodes/handle_correction.py` | **6%** | 79% | 267 | ~25-30 |
| `dm/nodes/handle_modification.py` | **6%** | 79% | 264 | ~20-25 |
| `du/optimizers.py` | **27%** | 58% | 84 | ~7-10* |
| `dm/routing.py` | **38%** | 47% | 661 | ~50-60 |
| `dm/nodes/handle_confirmation.py` | **40%** | 45% | 330 | ~20-25 |
| `dm/nodes/validate_slot.py` | **46%** | 39% | 190 | ~30-40 |

*Nota: `du/optimizers.py` requiere mocks de LLM para tests deterministas.

#### Prioridad ALTA (Cobertura 50-80%)

| Módulo | Cobertura | Gap | LOC | Tests Estimados |
|--------|-----------|-----|-----|-----------------|
| `runtime/runtime.py` | 59% | 26% | 250 | ~20-30 |
| `utils/response_generator.py` | 61% | 24% | 41 | ~5-8 |
| `du/normalizer.py` | 67% | 18% | 132 | ~10-15 |
| `flow/step_manager.py` | 69% | 16% | 168 | ~15-20 |
| `dm/nodes/handle_intent_change.py` | 69% | 16% | 210 | ~10-15 |

#### Módulos con Alta Cobertura (>80% - Ya cubiertos)

| Módulo | Cobertura | Acción |
|--------|-----------|--------|
| `utils/metadata_manager.py` | **100%** | ✅ Completo - No requiere tests adicionales |
| `utils/cycle_detector.py` | **100%** | ✅ Completo - No requiere tests adicionales |
| `utils/flow_cleanup.py` | **96%** | ✅ Casi completo - Revisar edge cases |
| `flow/manager.py` | 89% | ✅ Buena cobertura - Pocos tests adicionales |
| `dm/persistence.py` | 84% | ✅ Buena cobertura - Revisar completitud |

### Patrones Conversacionales a Probar

Según la documentación de diseño, los siguientes patrones deben estar completamente cubiertos:

1. ✅ **Flujo Secuencial Simple** - Parcialmente cubierto
2. ⚠️ **Múltiples Slots en un Mensaje** - Necesita más tests
3. ⚠️ **Corrección de Slots** - Necesita tests exhaustivos
4. ⚠️ **Modificación de Slots** - Necesita tests exhaustivos
5. ⚠️ **Confirmación (Yes/No)** - Necesita tests exhaustivos
6. ⚠️ **Corrección Durante Confirmación** - Necesita tests
7. ⚠️ **Interrupción (Nuevo Flow)** - Parcialmente cubierto
8. ⚠️ **Digresión** - Parcialmente cubierto
9. ⚠️ **Cancelación** - Necesita tests
10. ⚠️ **Manejo de Errores** - Parcialmente cubierto

---

## 2. Análisis Detallado por Módulo (Prioridad CRÍTICA)

### 2.1 `dm/nodes/handle_correction.py` (Cobertura: 6%, Gap: 79%)

**Estado**: Prácticamente sin tests unitarios dedicados (solo 6% cubierto)
**Complejidad**: Alta (267 líneas, lógica compleja de routing post-corrección)
**Impacto**: CRÍTICO - Patrón conversacional fundamental

**Función principal sin tests:**

#### 2.1.1 `handle_correction_node(state, runtime)` - **CRÍTICO**
- **Líneas**: 12-227
- **Complejidad**: Muy Alta
- **Tests necesarios (con NLU mockeado)**:
  ```python
  # Formato de slots - Determinista con mocks
  - test_handle_correction_slotvalue_format()  # Mock slot como SlotValue object
  - test_handle_correction_dict_format()       # Mock slot como dict

  # Casos de error - Edge cases
  - test_handle_correction_no_nlu_result()
  - test_handle_correction_no_slots()
  - test_handle_correction_no_active_flow()
  - test_handle_correction_unknown_slot_format()

  # Normalización - Mock normalizer
  - test_handle_correction_normalization_success()
  - test_handle_correction_normalization_failure()

  # Routing post-corrección - Lógica compleja a probar
  - test_handle_correction_returns_to_collect_step()
  - test_handle_correction_returns_to_confirmation_step()
  - test_handle_correction_returns_to_action_step()
  - test_handle_correction_all_slots_filled_routes_to_confirmation()
  - test_handle_correction_all_slots_filled_routes_to_action()
  - test_handle_correction_partial_slots_routes_to_collect()

  # Estados previos (conversation_state)
  - test_handle_correction_from_ready_for_action()
  - test_handle_correction_from_ready_for_confirmation()
  - test_handle_correction_from_confirming()
  - test_handle_correction_from_waiting_for_slot()

  # Metadata y response
  - test_handle_correction_sets_metadata_flags()
  - test_handle_correction_clears_modification_flags()
  - test_handle_correction_acknowledgment_message()
  - test_handle_correction_response_template_from_config()
  - test_handle_correction_response_template_default()
  ```

#### 2.1.2 `_get_response_template(config, template_name, default, **kwargs)` - **IMPORTANTE**
- **Líneas**: 230-267
- **Tests necesarios**:
  ```python
  - test_get_response_template_from_config_dict()
  - test_get_response_template_from_config_string()
  - test_get_response_template_default_fallback()
  - test_get_response_template_interpolation_single_var()
  - test_get_response_template_interpolation_multiple_vars()
  - test_get_response_template_missing_config()
  ```

**Total estimado**: ~30 tests para `handle_correction.py`

---

### 2.2 `dm/nodes/handle_modification.py` (Cobertura: 6%, Gap: 79%)

**Estado**: Prácticamente sin tests unitarios dedicados (solo 6% cubierto)
**Complejidad**: Alta (264 líneas, similar a correction)
**Impacto**: CRÍTICO - Patrón conversacional fundamental

**Estructura similar a handle_correction.py**:

#### 2.2.1 `handle_modification_node(state, runtime)` - **CRÍTICO**
- **Líneas**: 12-219
- **Tests necesarios (idénticos a correction pero con modification flags)**:
  ```python
  # Los mismos tests que handle_correction.py pero verificando:
  # 1. Se setean flags de modification (no correction)
  # 2. Se limpian flags de correction (no modification)
  # 3. Mensajes de acknowledgment específicos de modification

  - test_handle_modification_[...mismos casos que correction...]
  - test_handle_modification_sets_modification_flags()  # Verificar metadata
  - test_handle_modification_clears_correction_flags()  # Verificar metadata
  ```

**Total estimado**: ~25 tests para `handle_modification.py`

---

### 2.3 `dm/routing.py` (Cobertura: 38%, Gap: 47%)

**Estado**: Cobertura muy baja en funciones de routing críticas (661 líneas)
**Complejidad**: Muy Alta - Múltiples funciones de routing con lógica compleja
**Impacto**: CRÍTICO - Control de flujo de toda la aplicación

**Funciones sin tests o con cobertura insuficiente:**

#### 2.3.1 `route_after_understand(state)` - **CRÍTICO**
- **Líneas**: 225-421
- **Complejidad**: Alta (múltiples condiciones)
- **Tests necesarios**:
  ```python
  # Tests deterministas con NLU mockeado:
  - test_route_after_understand_intent_change()          # Mock NLU -> INTENT_CHANGE
  - test_route_after_understand_slot_value()             # Mock NLU -> SLOT_VALUE
  - test_route_after_understand_slot_value_when_confirming()  # Edge case especial
  - test_route_after_understand_slot_value_modification_after_denial()  # Edge case especial
  - test_route_after_understand_digression()             # Mock NLU -> QUESTION/HELP
  - test_route_after_understand_confirmation()           # Mock NLU -> CONFIRMATION
  - test_route_after_understand_correction()             # Mock NLU -> CORRECTION
  - test_route_after_understand_modification()           # Mock NLU -> MODIFICATION
  - test_route_after_understand_cancellation()           # Mock NLU -> CANCEL
  - test_route_after_understand_no_nlu_result()          # Edge case
  - test_route_after_understand_unknown_message_type()   # Edge case
  - test_route_after_understand_no_active_flow()         # Edge case
  ```

#### 2.1.2 `route_after_validate(state)` - **CRÍTICO**
- **Líneas**: ~482-524
- **Complejidad**: Alta
- **Tests necesarios**:
  ```python
  - test_route_after_validate_slot_valid()
  - test_route_after_validate_slot_invalid()
  - test_route_after_validate_all_slots_filled()
  - test_route_after_validate_needs_confirmation()
  - test_route_after_validate_ready_for_action()
  - test_route_after_validate_correction_detected()
  - test_route_after_validate_modification_detected()
  - test_route_after_validate_error_state()
  ```

#### 2.1.3 `route_after_correction(state)` - **CRÍTICO**
- **Líneas**: ~422-451
- **Complejidad**: Media-Alta
- **Tests necesarios**:
  ```python
  - test_route_after_correction_back_to_collect()
  - test_route_after_correction_back_to_confirmation()
  - test_route_after_correction_back_to_action()
  - test_route_after_correction_all_slots_filled()
  - test_route_after_correction_error_state()
  ```

#### 2.1.4 `route_after_modification(state)` - **CRÍTICO**
- **Líneas**: ~452-481
- **Complejidad**: Media-Alta
- **Tests necesarios**:
  ```python
  - test_route_after_modification_back_to_collect()
  - test_route_after_modification_back_to_confirmation()
  - test_route_after_modification_back_to_action()
  - test_route_after_modification_all_slots_filled()
  - test_route_after_modification_error_state()
  ```

#### 2.1.5 `route_after_collect_next_slot(state)` - **CRÍTICO**
- **Líneas**: ~525-583
- **Complejidad**: Alta
- **Tests necesarios**:
  ```python
  - test_route_after_collect_next_slot_has_next_slot()
  - test_route_after_collect_next_slot_no_next_slot()
  - test_route_after_collect_next_slot_ready_for_action()
  - test_route_after_collect_next_slot_ready_for_confirmation()
  - test_route_after_collect_next_slot_error_state()
  ```

#### 2.1.6 `route_after_action(state)` - **CRÍTICO**
- **Líneas**: ~584-627
- **Complejidad**: Media-Alta
- **Tests necesarios**:
  ```python
  - test_route_after_action_success()
  - test_route_after_action_failure()
  - test_route_after_action_has_next_step()
  - test_route_after_action_flow_completed()
  - test_route_after_action_error_state()
  ```

#### 2.1.7 `route_after_confirmation(state)` - **CRÍTICO**
- **Líneas**: ~628-662
- **Complejidad**: Alta
- **Tests necesarios**:
  ```python
  - test_route_after_confirmation_yes()
  - test_route_after_confirmation_no()
  - test_route_after_confirmation_unclear()
  - test_route_after_confirmation_correction_during()
  - test_route_after_confirmation_modification_during()
  - test_route_after_confirmation_error_state()
  ```

#### 2.1.8 `should_continue_flow(state)` - **IMPORTANTE**
- **Líneas**: ~196-224
- **Complejidad**: Media
- **Tests necesarios**:
  ```python
  - test_should_continue_flow_has_next_step()
  - test_should_continue_flow_no_next_step()
  - test_should_continue_flow_at_end()
  ```

#### 2.1.9 `activate_flow_by_intent(command, current_flow, config)` - **IMPORTANTE**
- **Líneas**: ~151-195
- **Complejidad**: Media
- **Tests necesarios**:
  ```python
  - test_activate_flow_by_intent_exact_match()
  - test_activate_flow_by_intent_normalized_match()
  - test_activate_flow_by_intent_no_match()
  - test_activate_flow_by_intent_already_active()
  - test_activate_flow_by_intent_with_spaces()
  - test_activate_flow_by_intent_with_hyphens()
  ```

#### 2.1.10 `create_branch_router(input_var, cases)` - **IMPORTANTE**
- **Líneas**: ~61-150
- **Complejidad**: Media
- **Tests necesarios**:
  ```python
  - test_create_branch_router_simple_case()
  - test_create_branch_router_multiple_cases()
  - test_create_branch_router_missing_variable()
  - test_create_branch_router_unmatched_value()
  - test_create_branch_router_nested_slots()
  ```

**Total estimado**: ~50-60 tests nuevos para `routing.py`

---

### 2.2 `dm/persistence.py` (Cobertura: ~58%, Gap: 27%)

**Clases y métodos sin tests:**

#### 2.2.1 `CheckpointerFactory.create()` - **CRÍTICO**
- **Líneas**: ~22-50
- **Complejidad**: Media
- **Tests necesarios**:
  ```python
  - test_checkpointer_factory_create_sqlite()
  - test_checkpointer_factory_create_sqlite_connection_error()
  - test_checkpointer_factory_create_sqlite_import_error()
  - test_checkpointer_factory_create_memory()
  - test_checkpointer_factory_create_none()
  - test_checkpointer_factory_create_unsupported_backend()
  - test_checkpointer_factory_create_unexpected_error()
  ```

#### 2.2.2 `CheckpointerFactory._create_sqlite_checkpointer()` - **IMPORTANTE**
- **Líneas**: ~53-85
- **Complejidad**: Media
- **Tests necesarios**:
  ```python
  - test_create_sqlite_checkpointer_success()
  - test_create_sqlite_checkpointer_os_error()
  - test_create_sqlite_checkpointer_connection_error()
  - test_create_sqlite_checkpointer_import_error()
  - test_create_sqlite_checkpointer_unexpected_error()
  ```

#### 2.2.3 `CheckpointerFactory._create_memory_checkpointer()` - **IMPORTANTE**
- **Líneas**: ~88-108
- **Complejidad**: Baja
- **Tests necesarios**:
  ```python
  - test_create_memory_checkpointer_success()
  - test_create_memory_checkpointer_returns_none_context()
  ```

#### 2.2.4 `CheckpointerFactory._create_none_checkpointer()` - **IMPORTANTE**
- **Líneas**: ~111-123
- **Complejidad**: Baja
- **Tests necesarios**:
  ```python
  - test_create_none_checkpointer_returns_none()
  ```

**Total estimado**: ~12-15 tests nuevos para `persistence.py`

---

### 2.3 `dm/node_factory_registry.py` (Cobertura: ~78%, Gap: 7%)

**Métodos sin tests o con cobertura insuficiente:**

#### 2.3.1 `NodeFactoryRegistry.get_all()` - **IMPORTANTE**
- **Líneas**: ~107-115
- **Complejidad**: Baja
- **Tests necesarios**:
  ```python
  - test_node_factory_registry_get_all_empty()
  - test_node_factory_registry_get_all_multiple()
  - test_node_factory_registry_get_all_returns_copy()
  ```

#### 2.3.2 `NodeFactoryRegistry.clear()` - **IMPORTANTE**
- **Líneas**: ~118-126
- **Complejidad**: Baja
- **Tests necesarios**:
  ```python
  - test_node_factory_registry_clear_removes_all()
  - test_node_factory_registry_clear_thread_safe()
  ```

**Total estimado**: ~5 tests nuevos para `node_factory_registry.py`

---

### 2.4 Nodos DM - Tests Adicionales Necesarios

#### 2.4.1 `handle_intent_change.py` - Tests Adicionales

**Funciones a probar más exhaustivamente:**

##### `_extract_slots_from_nlu(nlu_result)` - **IMPORTANTE**
- **Líneas**: ~11-50
- **Tests necesarios**:
  ```python
  - test_extract_slots_from_nlu_dict_format()
  - test_extract_slots_from_nlu_slotvalue_format()
  - test_extract_slots_from_nlu_mixed_format()
  - test_extract_slots_from_nlu_empty_list()
  - test_extract_slots_from_nlu_missing_name()
  - test_extract_slots_from_nlu_missing_value()
  - test_extract_slots_from_nlu_none_value()
  ```

##### `handle_intent_change_node()` - Casos Adicionales
- **Tests necesarios**:
  ```python
  - test_handle_intent_change_extracts_multiple_slots()
  - test_handle_intent_change_preserves_existing_slots()
  - test_handle_intent_change_flow_already_active()
  - test_handle_intent_change_no_nlu_result()
  - test_handle_intent_change_command_not_flow_but_active_flow()
  - test_handle_intent_change_advances_through_completed_steps()
  - test_handle_intent_change_clears_user_message()
  ```

**Total estimado**: ~15 tests adicionales para `handle_intent_change.py`

#### 2.4.2 `handle_correction.py` - Tests Exhaustivos

**Funciones a probar:**

##### `handle_correction_node()` - **CRÍTICO**
- **Líneas**: ~12-227
- **Complejidad**: Alta
- **Tests necesarios**:
  ```python
  - test_handle_correction_slotvalue_format()
  - test_handle_correction_dict_format()
  - test_handle_correction_unknown_format()
  - test_handle_correction_no_nlu_result()
  - test_handle_correction_no_slots()
  - test_handle_correction_no_active_flow()
  - test_handle_correction_normalization_failure()
  - test_handle_correction_returns_to_collect_step()
  - test_handle_correction_returns_to_confirmation_step()
  - test_handle_correction_returns_to_action_step()
  - test_handle_correction_all_slots_filled_returns_to_action()
  - test_handle_correction_all_slots_filled_returns_to_confirmation()
  - test_handle_correction_previous_state_ready_for_action()
  - test_handle_correction_previous_state_ready_for_confirmation()
  - test_handle_correction_fallback_to_collect_slot_step()
  - test_handle_correction_sets_metadata_flags()
  - test_handle_correction_acknowledgment_message()
  - test_handle_correction_response_template_from_config()
  - test_handle_correction_response_template_default()
  ```

##### `_get_response_template()` - **IMPORTANTE**
- **Líneas**: ~230-267
- **Tests necesarios**:
  ```python
  - test_get_response_template_from_config_dict()
  - test_get_response_template_from_config_string()
  - test_get_response_template_default()
  - test_get_response_template_interpolation()
  - test_get_response_template_multiple_variables()
  - test_get_response_template_missing_config()
  ```

**Total estimado**: ~25 tests para `handle_correction.py`

#### 2.4.3 `handle_modification.py` - Tests Exhaustivos

**Funciones a probar:**

##### `handle_modification_node()` - **CRÍTICO**
- **Líneas**: ~12-224
- **Complejidad**: Alta (similar a correction)
- **Tests necesarios**:
  ```python
  - test_handle_modification_slotvalue_format()
  - test_handle_modification_dict_format()
  - test_handle_modification_unknown_format()
  - test_handle_modification_no_nlu_result()
  - test_handle_modification_no_slots()
  - test_handle_modification_no_active_flow()
  - test_handle_modification_normalization_failure()
  - test_handle_modification_returns_to_collect_step()
  - test_handle_modification_returns_to_confirmation_step()
  - test_handle_modification_returns_to_action_step()
  - test_handle_modification_all_slots_filled_returns_to_action()
  - test_handle_modification_all_slots_filled_returns_to_confirmation()
  - test_handle_modification_previous_state_ready_for_action()
  - test_handle_modification_previous_state_ready_for_confirmation()
  - test_handle_modification_fallback_to_collect_slot_step()
  - test_handle_modification_sets_metadata_flags()
  - test_handle_modification_acknowledgment_message()
  - test_handle_modification_response_template_from_config()
  - test_handle_modification_response_template_default()
  ```

##### `_get_response_template()` - **IMPORTANTE**
- **Líneas**: ~227-264
- **Tests necesarios**: (mismos que correction)

**Total estimado**: ~20 tests para `handle_modification.py`

#### 2.4.4 `handle_confirmation.py` - Tests Exhaustivos

**Funciones a probar:**

##### `handle_confirmation_node()` - **CRÍTICO**
- **Líneas**: ~13-178
- **Complejidad**: Muy Alta
- **Tests necesarios**:
  ```python
  - test_handle_confirmation_yes_proceeds_to_action()
  - test_handle_confirmation_no_allows_modification()
  - test_handle_confirmation_unclear_asks_again()
  - test_handle_confirmation_unclear_increments_attempts()
  - test_handle_confirmation_max_attempts_exceeded()
  - test_handle_confirmation_max_attempts_before_processing()
  - test_handle_confirmation_correction_during_confirmation()
  - test_handle_confirmation_modification_during_confirmation()
  - test_handle_confirmation_unexpected_message_type()
  - test_handle_confirmation_no_nlu_result()
  - test_handle_confirmation_clears_flags_on_success()
  - test_handle_confirmation_clears_flags_on_denial()
  - test_handle_confirmation_clears_flags_on_error()
  ```

##### `_handle_correction_during_confirmation()` - **CRÍTICO**
- **Líneas**: ~181-290
- **Complejidad**: Alta
- **Tests necesarios**:
  ```python
  - test_handle_correction_during_confirmation_slotvalue_format()
  - test_handle_correction_during_confirmation_dict_format()
  - test_handle_correction_during_confirmation_no_slots()
  - test_handle_correction_during_confirmation_unknown_format()
  - test_handle_correction_during_confirmation_normalization_failure()
  - test_handle_correction_during_confirmation_no_active_flow()
  - test_handle_correction_during_confirmation_updates_slot()
  - test_handle_correction_during_confirmation_sets_metadata_flags()
  - test_handle_correction_during_confirmation_regenerates_confirmation()
  - test_handle_correction_during_confirmation_acknowledgment_message()
  - test_handle_correction_during_confirmation_combined_response()
  ```

##### `_get_response_template()` - **IMPORTANTE**
- **Líneas**: ~293-330
- **Tests necesarios**: (mismos que correction)

**Total estimado**: ~25 tests para `handle_confirmation.py`

#### 2.4.5 `confirm_action.py` - Tests Exhaustivos

**Funciones a probar:**

##### `confirm_action_node()` - **CRÍTICO**
- **Líneas**: ~10-147
- **Complejidad**: Alta
- **Tests necesarios**:
  ```python
  - test_confirm_action_no_active_flow()
  - test_confirm_action_not_confirm_step()
  - test_confirm_action_builds_confirmation_message()
  - test_confirm_action_interpolates_slots()
  - test_confirm_action_missing_slot_in_interpolation()
  - test_confirm_action_no_slots_interpolated()
  - test_confirm_action_adds_slots_manually()
  - test_confirm_action_first_execution_interrupts()
  - test_confirm_action_re_execution_after_resume()
  - test_confirm_action_preserves_existing_response()
  - test_confirm_action_confirmation_processed_flag()
  - test_confirm_action_passes_through_first_re_execution()
  ```

**Total estimado**: ~12 tests para `confirm_action.py`

#### 2.4.6 `collect_next_slot.py` - Tests Adicionales

**Funciones a probar:**

##### `collect_next_slot_node()` - **IMPORTANTE**
- **Líneas**: ~11-93
- **Complejidad**: Media
- **Tests necesarios**:
  ```python
  - test_collect_next_slot_no_active_flow()
  - test_collect_next_slot_no_current_step_advances()
  - test_collect_next_slot_no_current_step_no_next_step()
  - test_collect_next_slot_no_next_slot_advances_step()
  - test_collect_next_slot_gets_slot_config()
  - test_collect_next_slot_slot_config_not_found()
  - test_collect_next_slot_interrupts_with_prompt()
  - test_collect_next_slot_re_execution_after_resume()
  ```

**Total estimado**: ~8 tests adicionales para `collect_next_slot.py`

---

### 2.5 `core/state.py` - Funciones Helper Sin Tests

**Funciones sin tests o con cobertura insuficiente:**

#### 2.5.1 Funciones de Configuración
```python
- test_get_slot_config_exists()
- test_get_slot_config_not_found()
- test_get_action_config_exists()
- test_get_action_config_not_found()
- test_get_flow_config_exists()
- test_get_flow_config_not_found()
```

#### 2.5.2 Funciones de Serialización
```python
- test_state_to_dict_complete()
- test_state_to_dict_partial()
- test_state_from_dict_complete()
- test_state_from_dict_partial()
- test_state_from_dict_allow_partial_true()
- test_state_from_dict_allow_partial_false()
- test_state_to_json()
- test_state_from_json()
- test_state_to_json_from_json_roundtrip()
```

#### 2.5.3 Funciones de Mensajes
```python
- test_add_message_user()
- test_add_message_assistant()
- test_add_message_system()
- test_get_user_messages_empty()
- test_get_user_messages_multiple()
- test_get_assistant_messages_empty()
- test_get_assistant_messages_multiple()
```

#### 2.5.4 Funciones de Slots
```python
- test_get_slot_exists()
- test_get_slot_not_exists_default()
- test_get_slot_not_exists_no_default()
- test_set_slot_new()
- test_set_slot_update()
- test_has_slot_true()
- test_has_slot_false()
- test_clear_slots()
```

#### 2.5.5 Funciones de Estado
```python
- test_increment_turn()
- test_add_trace()
- test_get_current_flow_active()
- test_get_current_flow_no_active()
- test_get_current_flow_context_active()
- test_get_current_flow_context_no_active()
- test_get_all_slots()
- test_get_nlu_result()
- test_get_metadata()
- test_get_conversation_state()
- test_get_flow_stack()
- test_get_user_message()
- test_get_last_response()
- test_get_action_result()
- test_set_all_slots()
```

#### 2.5.6 Funciones de Steps
```python
- test_get_current_step_config_exists()
- test_get_current_step_config_not_exists()
- test_get_next_step_config_exists()
- test_get_next_step_config_not_exists()
- test_update_current_step()
```

**Total estimado**: ~50-60 tests para `core/state.py`

---

### 2.6 `utils/` - Módulos Sin Tests

#### 2.6.1 `utils/cycle_detector.py` - **IMPORTANTE**

**Clase `StateTransitionCycleDetector`:**

```python
- test_cycle_detector_initialization()
- test_cycle_detector_detect_cycle_simple()
- test_cycle_detector_detect_cycle_complex()
- test_cycle_detector_no_cycle()
- test_cycle_detector_reset()
- test_cycle_detector_max_depth()
```

**Total estimado**: ~6 tests para `cycle_detector.py`

#### 2.6.2 `utils/flow_cleanup.py` - **IMPORTANTE**

**Clase `FlowCleanupManager`:**

```python
- test_flow_cleanup_manager_initialization()
- test_flow_cleanup_manager_cleanup_completed_flows()
- test_flow_cleanup_manager_cleanup_old_flows()
- test_flow_cleanup_manager_cleanup_by_age()
- test_flow_cleanup_manager_preserve_active_flows()
- test_flow_cleanup_manager_preserve_recent_flows()
```

**Total estimado**: ~6 tests para `flow_cleanup.py`

#### 2.6.3 `utils/metadata_manager.py` - **IMPORTANTE**

**Clase `MetadataManager`:**

```python
- test_metadata_manager_set_correction_flags()
- test_metadata_manager_set_modification_flags()
- test_metadata_manager_set_confirmation_flags()
- test_metadata_manager_clear_confirmation_flags()
- test_metadata_manager_increment_confirmation_attempts()
- test_metadata_manager_get_confirmation_attempts()
- test_metadata_manager_get_correction_slot()
- test_metadata_manager_get_modification_slot()
```

**Total estimado**: ~8 tests para `metadata_manager.py`

#### 2.6.4 `utils/response_generator.py` - **IMPORTANTE**

**Clase `ResponseGenerator`:**

```python
- test_response_generator_generate_confirmation()
- test_response_generator_generate_confirmation_with_template()
- test_response_generator_generate_confirmation_no_template()
- test_response_generator_generate_error_message()
- test_response_generator_generate_help_message()
- test_response_generator_interpolate_slots()
```

**Total estimado**: ~6 tests para `response_generator.py`

---

### 2.7 `du/optimizers.py` - Tests con Mocking

**Funciones a probar con mocks (sin LLM real):**

```python
- test_optimize_soni_du_with_mock_lm()
- test_optimize_soni_du_evaluation_metric()
- test_optimize_soni_du_convergence()
- test_optimize_soni_du_max_iterations()
- test_evaluate_module_with_mock()
- test_load_optimized_module_exists()
- test_load_optimized_module_not_exists()
```

**Total estimado**: ~7 tests para `du/optimizers.py` (con mocking)

---

## 3. Patrones Conversacionales - Tests Deterministas

### 3.1 Flujo Secuencial Simple

**Escenario**: Usuario proporciona slots uno por uno

```python
# Tests necesarios:
- test_sequential_flow_turn_1_intent()
- test_sequential_flow_turn_2_first_slot()
- test_sequential_flow_turn_3_second_slot()
- test_sequential_flow_turn_4_last_slot_ready_for_action()
- test_sequential_flow_turn_5_action_executed()
- test_sequential_flow_complete_state_transitions()
```

### 3.2 Múltiples Slots en un Mensaje

**Escenario**: Usuario proporciona múltiples slots en un solo mensaje

```python
# Tests necesarios:
- test_multiple_slots_turn_1_origin_destination()
- test_multiple_slots_turn_1_advances_to_next_slot()
- test_multiple_slots_turn_2_completes_flow()
- test_multiple_slots_all_slots_in_one_message()
- test_multiple_slots_partial_slots_in_message()
```

### 3.3 Corrección de Slots

**Escenario**: Usuario corrige un valor previamente proporcionado

```python
# Tests necesarios:
- test_correction_during_collection()
- test_correction_during_confirmation()
- test_correction_returns_to_correct_step()
- test_correction_preserves_other_slots()
- test_correction_updates_metadata()
```

### 3.4 Modificación de Slots

**Escenario**: Usuario modifica intencionalmente un slot

```python
# Tests necesarios:
- test_modification_during_collection()
- test_modification_during_confirmation()
- test_modification_returns_to_correct_step()
- test_modification_preserves_other_slots()
- test_modification_updates_metadata()
```

### 3.5 Confirmación (Yes/No)

**Escenario**: Sistema pide confirmación antes de ejecutar acción

```python
# Tests necesarios:
- test_confirmation_flow_request()
- test_confirmation_flow_user_yes()
- test_confirmation_flow_user_no()
- test_confirmation_flow_user_unclear()
- test_confirmation_flow_max_attempts()
- test_confirmation_flow_correction_during()
```

### 3.6 Interrupción (Nuevo Flow)

**Escenario**: Usuario inicia un nuevo flow mientras otro está activo

```python
# Tests necesarios:
- test_interruption_pauses_current_flow()
- test_interruption_starts_new_flow()
- test_interruption_resumes_previous_flow()
- test_interruption_stack_limit()
- test_interruption_multiple_levels()
```

### 3.7 Digresión

**Escenario**: Usuario hace pregunta off-topic sin cambiar flow

```python
# Tests necesarios:
- test_digression_question_answered()
- test_digression_returns_to_same_step()
- test_digression_preserves_flow_state()
- test_digression_multiple_digressions()
```

### 3.8 Cancelación

**Escenario**: Usuario cancela el flow actual

```python
# Tests necesarios:
- test_cancellation_during_collection()
- test_cancellation_during_confirmation()
- test_cancellation_pops_flow()
- test_cancellation_returns_to_previous()
- test_cancellation_returns_to_idle()
```

### 3.9 Manejo de Errores

**Escenario**: Errores en diferentes puntos del flujo

```python
# Tests necesarios:
- test_error_validation_error()
- test_error_nlu_error()
- test_error_action_error()
- test_error_generic_error()
- test_error_recovery()
- test_error_clears_metadata()
```

---

## 4. Resumen de Tests Necesarios

### 4.1 Por Módulo (Basado en Cobertura Real)

#### Prioridad CRÍTICA (<50% cobertura)

| Módulo | Cobertura | Tests Necesarios | Impacto |
|--------|-----------|------------------|---------|
| `dm/nodes/handle_correction.py` | 6% | ~30 | Patrón conversacional crítico |
| `dm/nodes/handle_modification.py` | 6% | ~25 | Patrón conversacional crítico |
| `dm/routing.py` | 38% | ~50-60 | Control de flujo crítico |
| `dm/nodes/handle_confirmation.py` | 40% | ~20-25 | Confirmación crítica |
| `dm/nodes/validate_slot.py` | 46% | ~30-40 | Validación crítica |
| `du/optimizers.py` | 27% | ~7-10* | Optimización DSPy |

**Total Prioridad CRÍTICA**: ~162-190 tests necesarios

*Nota: Requiere mocks de LLM para tests deterministas

#### Prioridad ALTA (50-80% cobertura)

| Módulo | Cobertura | Tests Necesarios | Impacto |
|--------|-----------|------------------|---------|
| `runtime/runtime.py` | 59% | ~20-30 | Orquestación principal |
| `utils/response_generator.py` | 61% | ~5-8 | Generación de respuestas |
| `du/normalizer.py` | 67% | ~10-15 | Normalización de slots |
| `flow/step_manager.py` | 69% | ~15-20 | Gestión de steps |
| `dm/nodes/handle_intent_change.py` | 69% | ~10-15 | Cambio de intención |

**Total Prioridad ALTA**: ~60-88 tests necesarios

#### Módulos con Cobertura >80% (Verificar completitud)

| Módulo | Cobertura | Acción |
|--------|-----------|--------|
| `utils/metadata_manager.py` | 100% | ✅ No requiere tests adicionales |
| `utils/cycle_detector.py` | 100% | ✅ No requiere tests adicionales |
| `utils/flow_cleanup.py` | 96% | ✅ Revisar 1-2 edge cases |
| `flow/manager.py` | 89% | ✅ Revisar completitud (~5 tests) |
| `dm/persistence.py` | 84% | ✅ Revisar completitud (~5 tests) |

**Total Módulos >80%**: ~10-12 tests adicionales

### 4.2 Estimación Total

- **Tests actuales**: 596 tests pasando
- **Tests necesarios (Prioridad CRÍTICA)**: ~162-190 tests
- **Tests necesarios (Prioridad ALTA)**: ~60-88 tests
- **Tests necesarios (Módulos >80%)**: ~10-12 tests
- **TOTAL ESTIMADO**: ~232-290 tests nuevos
- **Cobertura esperada**: 85-90% (desde 66% actual)

---

## 5. Estrategia de Implementación (Por Prioridad)

### 5.1 Fase CRÍTICA: Nodos de Corrección/Modificación y Routing

**Objetivo**: Cubrir los módulos con cobertura <50% que implementan patrones conversacionales críticos

**Módulos a implementar**:
1. `dm/nodes/handle_correction.py` (~30 tests)
   - Implementar todos los tests de manejo de correcciones
   - Mockear NLU para retornar CORRECTION message_type
   - Mockear normalizer para valores deterministas
   - Verificar routing post-corrección a todos los steps posibles
   - Verificar metadata flags (_correction_slot, _correction_value)

2. `dm/nodes/handle_modification.py` (~25 tests)
   - Misma estructura que correction pero con flags de modification
   - Verificar que limpia flags de correction cuando setea modification

3. `dm/routing.py` (~50-60 tests)
   - Implementar tests para todas las funciones route_after_*
   - Mockear NLU con todos los message_type posibles
   - Verificar edge cases especiales (confirming state, modification after denial)
   - Verificar transiciones de estado correctas

4. `dm/nodes/handle_confirmation.py` (~20-25 tests adicionales)
   - Completar tests de corrección durante confirmación
   - Tests de max retries
   - Tests de cleanup de metadata

5. `dm/nodes/validate_slot.py` (~30-40 tests)
   - Tests de validación con validators mockeados
   - Tests de slot filling logic
   - Tests de normalización

**Resultado esperado**: +155-180 tests, cobertura sube de 66% a ~78-80%

### 5.2 Fase ALTA: Runtime y Utilidades

**Objetivo**: Cubrir módulos con cobertura 50-80%

**Módulos a implementar**:
1. `runtime/runtime.py` (~20-30 tests)
2. `utils/response_generator.py` (~5-8 tests)
3. `du/normalizer.py` (~10-15 tests)
4. `flow/step_manager.py` (~15-20 tests)
5. `dm/nodes/handle_intent_change.py` (~10-15 tests)

**Resultado esperado**: +60-88 tests, cobertura sube a ~83-85%

### 5.3 Fase FINAL: Completitud

**Objetivo**: Alcanzar >85% en módulos que ya tienen alta cobertura

**Módulos a implementar**:
1. `flow/manager.py` (~5 tests)
2. `dm/persistence.py` (~5 tests)
3. `utils/flow_cleanup.py` (~1-2 tests)
4. `du/optimizers.py` (~7-10 tests con mocks)

**Resultado esperado**: +18-22 tests, cobertura final >85%

---

## 6. Mejores Prácticas para Implementación

### 6.1 Patrón AAA (Arrange-Act-Assert)

**TODOS los tests deben seguir este patrón:**

```python
@pytest.mark.asyncio
async def test_example():
    """Test description."""
    # Arrange - Set up test data and conditions
    state = create_empty_state()
    state["nlu_result"] = {"command": "book_flight"}
    mock_runtime = create_mock_runtime()

    # Act - Execute the function being tested
    result = await handle_intent_change_node(state, mock_runtime)

    # Assert - Verify the expected outcome
    assert result["conversation_state"] == "waiting_for_slot"
    assert "book_flight" in result.get("flow_stack", [{}])[0].get("flow_name", "")
```

### 6.2 Mocking de NLU - **CRÍTICO para Tests Deterministas**

**⚠️ TODOS los tests unitarios DEBEN mockear el NLU (NUNCA usar LLM real):**

**Razones**:
1. **Determinismo**: LLMs son no-deterministas, tests deben ser 100% reproducibles
2. **Velocidad**: Tests unitarios deben ser rápidos (<1s cada uno)
3. **Control**: Necesitamos controlar exactamente qué retorna el NLU para cada caso
4. **Coste**: No gastar tokens en tests unitarios
5. **Independencia**: Tests unitarios no deben depender de servicios externos

**Cómo mockear el NLU**:

```python
from unittest.mock import MagicMock, AsyncMock
from soni.du.models import NLUOutput, MessageType, SlotValue

@pytest.fixture
def mock_nlu_provider():
    """Create mocked NLU provider for deterministic tests."""
    nlu = AsyncMock()
    # Mock determinista: siempre retorna SLOT_VALUE con slot "origin"
    nlu.predict.return_value = NLUOutput(
        message_type=MessageType.SLOT_VALUE,
        command="continue",
        slots=[SlotValue(name="origin", value="Madrid", confidence=0.95)],
        confidence=0.95,
        reasoning="User provided origin"
    )
    return nlu

@pytest.fixture
def mock_nlu_correction():
    """Mock NLU returning CORRECTION message_type."""
    nlu = AsyncMock()
    nlu.predict.return_value = NLUOutput(
        message_type=MessageType.CORRECTION,
        command="continue",
        slots=[SlotValue(name="destination", value="Barcelona", confidence=0.95)],
        confidence=0.95,
        reasoning="User is correcting destination"
    )
    return nlu

@pytest.fixture
def mock_nlu_confirmation_yes():
    """Mock NLU returning YES confirmation."""
    nlu = AsyncMock()
    nlu.predict.return_value = NLUOutput(
        message_type=MessageType.CONFIRMATION,
        command="continue",
        confirmation_value=True,
        confidence=0.95,
        reasoning="User confirmed"
    )
    return nlu

# Ejemplo de test usando mock
@pytest.mark.asyncio
async def test_handle_correction_updates_slot(mock_nlu_correction):
    """Test that handle_correction updates the slot value."""
    # Arrange
    state = create_state_with_slots({"destination": "Madrid"})
    state["nlu_result"] = mock_nlu_correction.predict.return_value.model_dump()
    mock_runtime = create_mock_runtime()

    # Act
    result = await handle_correction_node(state, mock_runtime)

    # Assert
    assert result["flow_slots"]["flow_1"]["destination"] == "Barcelona"
    assert result["metadata"]["_correction_slot"] == "destination"
```

**Patrón para mockear diferentes message_types**:

```python
# En conftest.py o en el test file
@pytest.fixture
def create_nlu_mock():
    """Factory fixture to create NLU mocks with specific message_type."""
    def _create(message_type: MessageType, **kwargs):
        nlu = AsyncMock()
        nlu.predict.return_value = NLUOutput(
            message_type=message_type,
            command=kwargs.get("command", "continue"),
            slots=kwargs.get("slots", []),
            confidence=kwargs.get("confidence", 0.95),
            confirmation_value=kwargs.get("confirmation_value"),
            reasoning=kwargs.get("reasoning", "Mocked NLU")
        )
        return nlu
    return _create

# Uso en test
def test_routing_with_different_message_types(create_nlu_mock):
    """Test routing handles all message types correctly."""
    # Test SLOT_VALUE
    nlu_slot = create_nlu_mock(
        MessageType.SLOT_VALUE,
        slots=[SlotValue(name="origin", value="Madrid")]
    )
    # ...

    # Test CORRECTION
    nlu_correction = create_nlu_mock(
        MessageType.CORRECTION,
        slots=[SlotValue(name="origin", value="Barcelona")]
    )
    # ...
```

### 6.3 Fixtures Reutilizables

**Crear fixtures comunes en `conftest.py`:**

```python
@pytest.fixture
def mock_runtime_context():
    """Create mock runtime context."""
    return {
        "flow_manager": MagicMock(),
        "step_manager": MagicMock(),
        "nlu_provider": AsyncMock(),
        "normalizer": AsyncMock(),
        "config": MagicMock(),
    }

@pytest.fixture
def sample_state():
    """Create sample dialogue state."""
    state = create_empty_state()
    state["flow_stack"] = [{
        "flow_id": "flow_1",
        "flow_name": "book_flight",
        "current_step": "collect_origin",
        "flow_state": "active",
        # ...
    }]
    state["flow_slots"] = {"flow_1": {}}
    return state
```

### 6.4 Tests Deterministas

**Todos los tests deben ser deterministas (sin aleatoriedad):**

```python
# ✅ CORRECTO - Determinista
def test_routing_deterministic():
    state = create_state_with_nlu_result({"command": "book_flight"})
    result = route_after_understand(state)
    assert result == "handle_intent_change"

# ❌ INCORRECTO - No determinista
def test_routing_random():
    state = create_random_state()  # ❌ Aleatorio
    result = route_after_understand(state)
    assert result in ["handle_intent_change", "validate_slot"]  # ❌ Múltiples resultados válidos
```

### 6.5 Cobertura de Edge Cases

**Incluir tests para casos límite:**

```python
# Tests para edge cases:
- test_function_with_empty_input()
- test_function_with_none_input()
- test_function_with_invalid_input()
- test_function_with_missing_dependencies()
- test_function_with_error_conditions()
```

### 6.6 Documentación de Tests

**Cada test debe tener docstring descriptivo:**

```python
def test_handle_correction_returns_to_confirmation_step():
    """
    Test that correction during confirmation returns to confirmation step.

    When user corrects a slot value during confirmation:
    - Slot should be updated
    - System should return to confirmation step
    - Confirmation message should be re-generated with updated values
    - Metadata flags should be set correctly
    """
    # Arrange
    # ...
```

---

## 7. Validación y Verificación

### 7.1 Criterios de Éxito

- ✅ Cobertura total >85%
- ✅ Cobertura de módulos críticos >90%
- ✅ Todos los tests pasan (100% pass rate)
- ✅ Tests deterministas (sin dependencias externas)
- ✅ NLU completamente mockeado
- ✅ Todos los patrones conversacionales cubiertos

### 7.2 Comandos de Verificación

```bash
# Ejecutar tests con cobertura
uv run pytest --cov=src/soni --cov-report=term-missing --cov-report=html

# Verificar cobertura por módulo
uv run pytest --cov=src/soni --cov-report=term-missing | grep -E "(dm/routing|dm/persistence|dm/nodes)"

# Ejecutar tests específicos
uv run pytest tests/unit/test_dm_routing.py -v

# Verificar que todos los tests pasan
uv run pytest tests/unit/ -v --tb=short
```

### 7.3 Checklist de Implementación

Para cada módulo:

- [ ] Tests implementados según análisis
- [ ] Tests siguen patrón AAA
- [ ] NLU mockeado (no LLM real)
- [ ] Tests deterministas
- [ ] Edge cases cubiertos
- [ ] Docstrings en todos los tests
- [ ] Cobertura >85% para el módulo
- [ ] Todos los tests pasan

---

## 8. Conclusión

### Resumen Ejecutivo

Para alcanzar cobertura >85% en tests unitarios (con NLU mockeado), se necesitan aproximadamente **232-290 tests unitarios nuevos**, distribuidos en:

- **Prioridad CRÍTICA** (<50% cobertura): ~162-190 tests
  - handle_correction.py (~30)
  - handle_modification.py (~25)
  - routing.py (~50-60)
  - handle_confirmation.py (~20-25)
  - validate_slot.py (~30-40)
  - optimizers.py (~7-10)

- **Prioridad ALTA** (50-80% cobertura): ~60-88 tests
  - runtime.py (~20-30)
  - response_generator.py (~5-8)
  - normalizer.py (~10-15)
  - step_manager.py (~15-20)
  - handle_intent_change.py (~10-15)

- **Prioridad MEDIA/BAJA** (>80% cobertura): ~10-12 tests
  - Módulos que ya tienen buena cobertura

### Impacto Esperado

- **Cobertura actual (tests unitarios)**: 66.23%
- **Cobertura objetivo**: >85%
- **Gap a cubrir**: 18.77%
- **Tests actuales**: 596 tests pasando
- **Tests necesarios**: ~232-290 tests nuevos
- **Tests finales esperados**: ~828-886 tests unitarios

### Principios Clave

1. **Tests 100% Deterministas**: TODOS los tests unitarios DEBEN mockear el NLU
2. **No LLMs en tests unitarios**: Solo en tests de integración
3. **Rápidos**: Cada test <1s, suite completa <10 minutos
4. **Independientes**: Sin dependencias externas (DB, API, LLM)
5. **Patrones Conversacionales**: Cubrir todos los patrones definidos en diseño

### Próximos Pasos

1. **Fase CRÍTICA**: Implementar tests para módulos con <50% cobertura
   - Prioridad: handle_correction, handle_modification, routing
   - Resultado esperado: Cobertura sube a ~78-80%

2. **Fase ALTA**: Implementar tests para módulos con 50-80% cobertura
   - Prioridad: runtime, normalizer, step_manager
   - Resultado esperado: Cobertura sube a ~83-85%

3. **Fase FINAL**: Completar tests en módulos >80%
   - Prioridad: Alcanzar >85% en todos los módulos
   - Resultado esperado: Cobertura >85%

4. **Validación continua**: Ejecutar `uv run pytest tests/unit/ --cov` después de cada grupo de tests

### Notas Importantes

- **No incluye tests de integración**: Este análisis es SOLO para tests unitarios
- **NLU siempre mockeado**: Tests deterministas, reproducibles, rápidos
- **Enfoque en DM**: La mayoría de tests son para Dialogue Management (routing, nodos)
- **Patrones conversacionales**: Cada patrón (corrección, modificación, confirmación) debe tener cobertura completa

---

**Documento generado**: 2025-12-08
**Última actualización**: 2025-12-10
**Versión**: 2.0 (Actualizado con cobertura real de tests unitarios)
**Estado**: Listo para implementación - Basado en datos reales de cobertura
