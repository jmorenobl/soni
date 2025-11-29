# Changelog

All notable changes to Soni Framework will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [0.1.0] - 2025-11-29

### Added
- Core interfaces and state management (`DialogueState`, `INLUProvider`, `IDialogueManager`)
- SoniDU module with DSPy integration for automatic NLU optimization
- DSPy optimization pipeline with MIPROv2 optimizer
- YAML configuration system with Pydantic validation
- LangGraph runtime with basic graph building
- RuntimeLoop for message processing
- FastAPI server with REST endpoints (`POST /chat/{user_id}`, `GET /health`)
- CLI commands (`soni optimize`, `soni server`)
- Flight booking example with complete configuration
- Quickstart and architecture documentation

### Features
- Linear dialogue flows with slot collection
- Action handlers for external business logic
- State persistence with SQLite checkpointing
- Multi-conversation support
- Configuration validation

### Limitations (MVP)
- Linear flows only (no branching logic)
- No explicit jumps between steps
- Validators referenced by name only (implementation in v0.4.0)
- Action handlers by Python path (Action Registry in v0.4.0)
- SqliteSaver instead of AsyncSqliteSaver (will be fixed in v0.2.0)

### Documentation
- Quickstart guide (`docs/quickstart.md`)
- Architecture guide (`docs/architecture.md`)
- Flight booking example (`examples/flight_booking/`)
- E2E validation report (`docs/validation/e2e-validation-report.md`)

### Testing
- Unit tests for core components
- Integration tests for runtime and API
- E2E tests (some skip pending AsyncSqliteSaver)
- Coverage: 30% (low due to skipped E2E tests)

### Known Issues
- E2E tests require AsyncSqliteSaver (will be implemented in v0.2.0)
- Some tests are skipped due to checkpointing limitations

## [0.0.1] - 2025-11-29

### Added
- Initial project setup
- Technical validation experiments (Hito 0)
  - DSPy validation experiment
  - LangGraph streaming validation
  - Async persistence validation
- Project documentation structure
- ADR-002: Technical Validation Results

### Changed
- N/A

### Fixed
- N/A

---

[Unreleased]: https://github.com/your-org/soni/compare/v0.1.0...HEAD
[0.1.0]: https://github.com/your-org/soni/compare/v0.0.1...v0.1.0
[0.0.1]: https://github.com/your-org/soni/releases/tag/v0.0.1
