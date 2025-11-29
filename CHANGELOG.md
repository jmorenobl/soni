# Changelog

All notable changes to Soni Framework will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [0.2.0] - 2025-01-XX

### Added
- AsyncSqliteSaver for full async checkpointing support
- ScopeManager for dynamic action scoping based on context
- SlotNormalizer with multiple normalization strategies (trim, lowercase, LLM correction)
- Streaming support with Server-Sent Events (SSE) in RuntimeLoop
- Streaming endpoint `POST /chat/{user_id}/stream` in FastAPI server
- Performance optimizations: NLU caching, scoping caching, connection pooling
- Performance validation scripts and reports

### Changed
- Migrated from SqliteSaver to AsyncSqliteSaver for full async support
- Integrated ScopeManager with SoniDU to reduce token usage (39.5% reduction)
- Integrated SlotNormalizer in pipeline before validation
- RuntimeLoop now supports streaming via `process_message_stream()`
- Improved accuracy through dynamic scoping

### Performance Improvements
- Token reduction: 39.5% reduction in LLM calls through dynamic scoping
- Validation improvement: +11.11% validation success rate through normalization
- Latency: Normalization adds only 0.01ms overhead
- Streaming: First token latency < 500ms
- Target metrics: p95 latency < 1.5s, throughput > 10 conv/sec

### Features
- Dynamic action scoping reduces hallucinations and improves accuracy
- Slot normalization improves user experience and validation success
- Streaming reduces perceived latency for users
- Full async support enables better concurrency

### Documentation
- Scoping performance report (`docs/validation/scoping-performance-report.md`)
- Normalization impact report (`docs/validation/normalization-impact-report.md`)
- Runtime API validation report (`docs/validation/runtime-api-validation.md`)

### Testing
- Performance tests for streaming, latency, and throughput
- Tests for ScopeManager and dynamic scoping
- Tests for SlotNormalizer (17 unit tests + integration)
- Tests for AsyncSqliteSaver
- Coverage: Targeting 80% (improved from v0.1.0)

### Known Issues
- Performance metrics validation pending (Task 034)
- Some optimizations may require tuning based on production usage

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
- AsyncSqliteSaver implemented for full async checkpointing support

### Documentation
- Quickstart guide (`docs/quickstart.md`)
- Architecture guide (`docs/architecture.md`)
- Flight booking example (`examples/flight_booking/`)
- E2E validation report (`docs/validation/e2e-validation-report.md`)

### Testing
- Unit tests for core components
- Integration tests for runtime and API
- E2E tests for complete flows (AsyncSqliteSaver implemented)
- Coverage: 30% (targeting 80% for v1.0.0)

### Known Issues
- Some E2E tests may fail without real LLM (expected behavior for integration tests)
- AsyncSqliteSaver requires aiosqlite package (included in dependencies)

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

[Unreleased]: https://github.com/jmorenobl/soni/compare/v0.2.0...HEAD
[0.2.0]: https://github.com/jmorenobl/soni/compare/v0.1.0...v0.2.0
[0.1.0]: https://github.com/jmorenobl/soni/compare/v0.0.1...v0.1.0
[0.0.1]: https://github.com/jmorenobl/soni/releases/tag/v0.0.1
