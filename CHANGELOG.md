# Changelog

All notable changes to Soni Framework will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [0.4.0] - 2024-11-30

### Added
- **Zero-Leakage Architecture**: YAML configuration is completely semantic (no technical details)
- **Action Registry Integration**: Complete integration of ActionRegistry in compiler
  - Auto-discovery of actions from `actions.py` or `actions/__init__.py` in config directory
  - Actions registered via `@ActionRegistry.register()` decorator
  - No Python paths in YAML configuration
- **Validator Registry Integration**: Complete integration of ValidatorRegistry in validation pipeline
  - Validators registered via `@ValidatorRegistry.register()` decorator
  - No regex patterns in YAML configuration
  - Built-in validators: `city_name`, `future_date_only`, `iata_code`, `booking_reference`
- **Output Mapping**: Complete implementation of `map_outputs` in action nodes
  - Decouples technical data structures from flat state variables
  - Actions can return complex structures that are mapped to simple variables
  - Validation of map_outputs during compilation
- Integration tests for ActionRegistry + Compiler
- Integration tests for ValidatorRegistry + Pipeline
- Integration tests for output mapping

### Changed
- **Breaking**: Action handlers must be registered via `@ActionRegistry.register()` (no Python paths in YAML)
- **Breaking**: Validators must be registered via `@ValidatorRegistry.register()` (no regex patterns in YAML)
- `ActionHandler.execute()` now uses `ActionRegistry` exclusively (removed `_load_handler()` method)
- `create_action_node_factory()` now accepts `map_outputs` parameter for output mapping
- All YAML examples updated to use semantic names only (no technical details)

### Features
- **Zero-Leakage Architecture**: YAML describes WHAT, Python implements HOW
- **Auto-Discovery**: Runtime automatically imports actions from config directory
- **Output Mapping**: Technical structures mapped to flat state variables
- **Semantic Configuration**: All YAML uses semantic names (actions, validators)

### Documentation
- Updated architecture documentation with Zero-Leakage principles
- Added examples of Action Registry and Validator Registry usage
- Documented output mapping with examples
- Updated DSL guide with output mapping details

### Testing
- Tests for ActionRegistry integration with compiler
- Tests for ValidatorRegistry integration with pipeline
- Tests for output mapping functionality
- Validation that YAML contains no technical details (handler paths, regex patterns)

### Migration Notes
- **From v0.3.0**: Actions must be migrated to use `@ActionRegistry.register()` decorator
- **From v0.3.0**: Validators must be migrated to use `@ValidatorRegistry.register()` decorator
- **From v0.3.0**: Remove any `handler:` fields from YAML action definitions
- **From v0.3.0**: Replace regex patterns in `validator:` fields with semantic validator names

## [0.3.0] - 2024-11-30

### Added
- Step Compiler for procedural flow definition
- StepParser for parsing and validating flow steps
- StepCompiler for generating LangGraph StateGraph from steps
- Support for branch steps with conditional routing
- Support for jump_to for explicit control flow
- Graph validation (cycles, unreachable nodes, valid targets)
- DAG intermediate representation for flow compilation
- Advanced examples with retry loops and complex branching
- DSL Guide documentation (`docs/dsl-guide.md`)

### Changed
- Procedural DSL with `process` section for complex flows
- Simple linear flows still supported via `steps` array
- Compiler generates StateGraph from procedural steps
- Improved flow control with branches and jumps

### Features
- **Branches**: Conditional routing based on values
- **Jumps**: Explicit control flow with `jump_to`
- **Validation**: Automatic detection of cycles and unreachable nodes
- **Compilation**: >95% success rate for valid YAML configurations

### Documentation
- DSL Guide with complete syntax and examples
- Advanced examples (retry loops, complex branching)
- Migration guide from v0.2.x to v0.3.0

### Testing
- 48+ tests for compiler (parser, builder, validation)
- Tests for branches, jumps, and complex flows
- Graph validation tests
- Coverage: >80% for compiler module

### Known Issues
- Some edge cases in complex branching may require refinement
- Performance optimization for large flows (planned for v0.4.0)

## [0.2.1] - 2025-01-XX

### Fixed
- Fixed concurrent graph initialization race condition that caused `RuntimeError: threads can only be started once`
- Added `asyncio.Lock` to protect graph initialization from concurrent access
- Fixed issue where multiple concurrent requests could fail when initializing AsyncSqliteSaver
- Improved thread-safety in RuntimeLoop for concurrent message processing

### Changed
- Makefile now cleans `dist/` directory before building to prevent publishing old package versions

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
- Technical Validation Results

### Changed
- N/A

### Fixed
- N/A

---

[Unreleased]: https://github.com/jmorenobl/soni/compare/v0.4.0...HEAD
[0.4.0]: https://github.com/jmorenobl/soni/compare/v0.3.0...v0.4.0
[0.3.0]: https://github.com/jmorenobl/soni/compare/v0.2.1...v0.3.0
[0.2.1]: https://github.com/jmorenobl/soni/compare/v0.2.0...v0.2.1
[0.2.0]: https://github.com/jmorenobl/soni/compare/v0.1.0...v0.2.0
[0.1.0]: https://github.com/jmorenobl/soni/compare/v0.0.1...v0.1.0
[0.0.1]: https://github.com/jmorenobl/soni/releases/tag/v0.0.1
