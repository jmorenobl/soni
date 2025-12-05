# Testing Quick Reference

## Comandos Principales

```bash
# Desarrollo diario (rápido, ~1 min)
make test

# Antes de merge/PR (moderado, ~3-5 min)
make test-ci

# Release completo (lento, ~5+ min)
make test-all
```

## Estructura de Tests

```
tests/
├── unit/           → 520 tests unitarios (rápidos, mockeados)
├── integration/    → 39 tests de integración (requieren LLM API)
└── performance/    → 11 tests de rendimiento (benchmarks)
```

## Estado Actual

| Categoría | Tests | Status | Tiempo |
|-----------|-------|--------|--------|
| **Unit** | 512 | ✅ 100% | ~52s |
| **Integration** | 32 | ⚠️ Algunos flaky | Variable |
| **Performance** | 11 | ⚠️ Depende del entorno | Variable |
| **TOTAL** | 555 | ✅ 97.7% | Varía |

## Configuración

### Para tests de integración

Crea un archivo `.env` en la raíz del proyecto:

```bash
OPENAI_API_KEY=sk-...
```

### Markers configurados

- `@pytest.mark.integration` - Tests que requieren LLM o componentes externos
- `@pytest.mark.performance` - Tests de benchmarking y rendimiento

## Comandos Make Completos

```bash
make test               # Solo unit tests (recomendado para desarrollo)
make test-all           # Todos los tests
make test-integration   # Solo integration tests
make test-performance   # Solo performance tests
make test-ci            # Unit + Integration (ideal para CI/CD)
```

## Calidad del Código

```bash
make lint        # Ruff linting
make type-check  # Mypy type checking
make format      # Auto-format código
make check       # Todo lo anterior + tests
```

## Más Información

- Ver `TESTING.md` para guía completa de testing
- Ver `MIGRATION_COMPLETE.md` para detalles de la migración
- Ver `FINAL_SUMMARY.md` para resumen ejecutivo
