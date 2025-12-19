# Roadmap: Post-Critical Improvements (P2 + Enhancements)

**Status**: 🟡 PLANNED - Post Production Launch
**Total Effort**: ~80 hours (~2 months at 40% allocation)
**Target Completion**: Q1 2026
**Owner**: TBD

---

## Executive Summary

This roadmap covers **improvements and enhancements** to be implemented after critical issues are resolved and the system is in production. Focus areas:
- Code quality and maintainability
- Enterprise features
- Developer experience
- Performance optimization

---

## Phase 1: Code Quality (P2 - High Priority)

**Duration**: 3 weeks
**Effort**: 26 hours

### Milestone 1.1: Refactor Large Components

#### Epic 1.1.1: Extract understand_node Orchestration (8h)
**Priority**: 🟡 P2
**Files**: `src/soni/dm/nodes/understand.py` (355 LOC → ~100 LOC)

**Problem**: Single function with multiple responsibilities violates SRP

**Solution**: Extract into cohesive components
```python
class UnderstandNodeOrchestrator:
    def __init__(
        self,
        context_builder: ContextBuilder,
        nlu_provider: NLUProvider,
        slot_extractor: SlotExtractor,
        command_dispatcher: CommandDispatcher
    ):
        ...

    async def process(
        self, state: DialogueState, context: RuntimeContext
    ) -> dict[str, Any]:
        # 1. Build context
        nlu_context = self.context_builder.build(state, context)

        # 2. Pass 1: Intent detection
        nlu_result = await self.nlu_provider.understand(
            state["user_message"], nlu_context
        )

        # 3. Pass 2: Slot extraction (if needed)
        commands = await self._extract_slots(nlu_result, state, context)

        # 4. Dispatch commands
        return await self.command_dispatcher.dispatch(commands, state, context)
```

**Benefits**:
- Easier to test each component
- Clear dependency injection
- Better code reuse
- Simpler maintenance

**Tasks**:
- [ ] Create `ContextBuilder` class
- [ ] Create `NLUProvider` wrapper interface
- [ ] Create `CommandDispatcher` class
- [ ] Update dependency injection
- [ ] Migrate tests
- [ ] Update documentation

**Testing**:
- Unit tests for each new component
- Integration test for orchestration
- Verify existing E2E tests pass

---

#### Epic 1.1.2: Refactor CommandHandlerRegistry (4h)
**Priority**: 🟡 P2
**Files**: `src/soni/dm/nodes/command_registry.py`

**Problem**: Hardcoded handler instantiation violates Open/Closed Principle

**Solution**: Plugin-style registration
```python
class CommandHandlerRegistry:
    def __init__(self):
        self._handlers: dict[str, CommandHandler] = {}
        self._register_builtin_handlers()

    def register(self, command_type: str, handler: CommandHandler) -> None:
        """Register a handler (open for extension)."""
        self._handlers[command_type] = handler

    def unregister(self, command_type: str) -> None:
        """Remove a handler."""
        del self._handlers[command_type]

    # No modification needed to add new handlers (closed for modification)
```

**Benefits**:
- Extensible without code changes
- Easier to test (mock handlers)
- Support for custom patterns
- Plugin ecosystem potential

**Tasks**:
- [ ] Refactor registry to plugin pattern
- [ ] Add handler discovery mechanism
- [ ] Document handler interface
- [ ] Add examples for custom handlers
- [ ] Migration guide for existing code

**Testing**:
- Test handler registration/unregistration
- Test custom handler integration
- Verify all existing handlers work

---

### Milestone 1.2: Testing Infrastructure (14h)

#### Epic 1.2.1: Add Integration Test Suite (8h)
**Priority**: 🟡 P2
**Files**: New `tests/integration/`

**Scope**:
- Real NLU (not mocked)
- Real database/checkpointer
- Complete dialogue flows
- Multi-turn conversations

**Test Categories**:
1. **Happy paths** (3h)
   - Single-flow completion
   - Multi-flow with interruptions
   - Slot collection and validation

2. **Error scenarios** (3h)
   - Invalid user input
   - Action failures
   - Network timeouts
   - State corruption

3. **Concurrency** (2h)
   - Multiple users simultaneously
   - Flow interruptions
   - State isolation

**Infrastructure**:
- [ ] Setup test database (SQLite)
- [ ] Load test NLU model
- [ ] Create test fixtures
- [ ] Add CI/CD integration

---

#### Epic 1.2.2: Add Performance Tests (3h)
**Priority**: 🟡 P2
**Files**: New `tests/performance/`

**Benchmarks**:
- Response latency (p50, p95, p99)
- Throughput (requests/second)
- Memory usage
- Database query count

**Tools**:
- `locust` for load testing
- `py-spy` for profiling
- `memory_profiler` for leaks

**Targets**:
- p95 latency: <200ms
- Throughput: >100 RPS
- Memory: <500MB for 1000 concurrent users

---

#### Epic 1.2.3: Add Chaos Engineering Tests (3h)
**Priority**: 🟡 P2
**Files**: New `tests/chaos/`

**Failure Injection**:
- Database connection loss
- Slow NLU responses (>5s)
- Action failures
- Out of memory conditions
- Network partitions

**Verification**:
- System recovers gracefully
- No data loss
- Error logging works
- Health checks accurate

---

## Phase 2: Enterprise Features (P2)

**Duration**: 4 weeks
**Effort**: 32 hours

### Milestone 2.1: API Improvements (8h)

#### Epic 2.1.1: Add API Versioning (4h)
**Files**: `src/soni/server/routes.py`

**Implementation**:
```python
# v1 routes
@app.include_router(
    routes.router,
    prefix="/api/v1",
    tags=["v1"]
)

# v2 routes (with breaking changes)
@app.include_router(
    routes_v2.router,
    prefix="/api/v2",
    tags=["v2"]
)
```

**Benefits**:
- Safe evolution of API
- Backwards compatibility
- Clear deprecation path

---

#### Epic 2.1.2: Add Rate Limiting (4h)
**Files**: New `src/soni/server/middleware/rate_limit.py`

**Strategy**: Token bucket algorithm

**Configuration**:
```yaml
rate_limits:
  default: 100/minute
  authenticated: 1000/minute
  endpoints:
    /chat: 10/minute  # Expensive
    /health: unlimited
```

**Implementation**:
- Use `slowapi` library
- Redis backend for distributed limiting
- Per-user and per-IP limits

---

### Milestone 2.2: Multi-Tenancy (12h)

#### Epic 2.2.1: Add User Isolation (8h)
**Files**: Multiple

**Features**:
- Separate state per tenant
- Resource quotas
- Access control
- Audit logging

**Schema**:
```python
class TenantConfig(BaseModel):
    tenant_id: str
    max_users: int
    max_flows: int
    allowed_actions: list[str]
    rate_limit: int
```

---

#### Epic 2.2.2: Add Audit Logging (4h)
**Files**: New `src/soni/observability/audit.py`

**Logged Events**:
- User actions
- Flow starts/completions
- Action executions
- State modifications
- API calls

**Format**: Structured JSON logs
```json
{
  "timestamp": "2025-12-18T18:56:00Z",
  "tenant_id": "acme_corp",
  "user_id": "user_123",
  "event_type": "flow_started",
  "flow_name": "transfer_funds",
  "metadata": {...}
}
```

---

### Milestone 2.3: Observability (12h)

#### Epic 2.3.1: Add Structured Logging (4h)
**Files**: All `src/soni/**/*.py`

**Migration**:
```python
# BEFORE
logger.info(f"Processing message: {msg}")

# AFTER
logger.info(
    "Processing message",
    extra={
        "user_id": user_id,
        "message_length": len(msg),
        "flow_stack_depth": len(state["flow_stack"])
    }
)
```

**Benefits**:
- Searchable logs
- Better debugging
- Metrics extraction

---

#### Epic 2.3.2: Add Metrics (4h)
**Files**: New `src/soni/observability/metrics.py`

**Metrics to Track**:
- Request count (by endpoint, status)
- Response time (histogram)
- Active users (gauge)
- Flow completions (counter)
- Error rate (counter)
- NLU confidence (histogram)

**Export**: Prometheus format

---

#### Epic 2.3.3: Add Distributed Tracing (4h)
**Files**: Multiple

**Tool**: OpenTelemetry

**Traced Operations**:
- HTTP requests
- NLU calls
- Database queries
- Action executions
- Inter-service calls

**Visualization**: Jaeger UI

---

## Phase 3: Developer Experience

**Duration**: 2 weeks
**Effort**: 16 hours

### Milestone 3.1: Documentation (8h)

#### Epic 3.1.1: Create Architecture Decision Records (4h)
**Files**: New `docs/adr/`

**ADRs to Write**:
1. ADR-001: Two-pass NLU Architecture
2. ADR-002: Immutable State with FlowDelta
3. ADR-003: Command Pattern for NLU→DM
4. ADR-004: Protocol-based Dependency Injection
5. ADR-005: LangGraph vs Custom State Machine

**Format**: Use [MADR template](https://adr.github.io/madr/)

---

#### Epic 3.1.2: Create API Documentation (4h)
**Files**: Add OpenAPI/Swagger

**Sections**:
- Authentication
- Endpoints reference
- Request/response schemas
- Error codes
- Rate limits
- Examples

**Tools**: FastAPI auto-generates from code

---

### Milestone 3.2: Tooling (8h)

#### Epic 3.2.1: Add Developer Scripts (4h)
**Files**: New `scripts/`

**Scripts**:
- `scripts/setup_dev.sh` - Local environment setup
- `scripts/run_tests.sh` - Run all test suites
- `scripts/lint.sh` - Run all linters
- `scripts/typecheck.sh` - Full type checking
- `scripts/benchmark.sh` - Performance benchmarks

---

#### Epic 3.2.2: Add Pre-commit Hooks (4h)
**Files**: `.pre-commit-config.yaml`

**Hooks**:
- Ruff formatting
- Mypy type checking
- Test suite (fast tests only)
- Commit message linting
- No secrets in code

---

## Phase 4: Performance & Optimization

**Duration**: 1 week
**Effort**: 8 hours

### Milestone 4.1: Profiling & Optimization (8h)

#### Epic 4.1.1: Profile Critical Paths (4h)

**Areas to Profile**:
- NLU call latency
- State hydration/extraction
- Command dispatching
- Database queries

**Tools**:
- `py-spy` for CPU profiling
- `memory_profiler` for memory
- `line_profiler` for hot paths

**Targets**:
- Identify bottlenecks >50ms
- Optimize top 3 slowest paths
- Reduce allocations in hot loops

---

#### Epic 4.1.2: Caching Strategy (4h)

**Cache Candidates**:
- Compiled graphs (per configuration)
- NLU model loading
- Slot definitions
- Flow configurations

**Implementation**:
- Use `functools.lru_cache` for in-process
- Redis for distributed caching
- TTL-based invalidation

---

## Phase 5: Nice-to-Have Features

**Duration**: Ad-hoc
**Effort**: Variable

### GraphQL API (8h)
Alternative to REST for complex queries

### WebSocket Support (12h)
Streaming responses, real-time updates

### Admin UI (40h)
- Flow management
- User analytics
- System monitoring
- Configuration editor

### A/B Testing Framework (16h)
- NLU model comparison
- Flow variant testing
- Metrics collection

---

## Quarterly Planning

### Q1 2026 (Jan-Mar)
**Focus**: Code Quality + Testing

- Week 1-2: Refactor large components
- Week 3-5: Testing infrastructure
- Week 6-8: Integration tests
- Weeks 9-12: Performance + chaos tests

**Deliverables**:
- Clean, maintainable code
- >90% test coverage
- Performance benchmarks

---

### Q2 2026 (Apr-Jun)
**Focus**: Enterprise Features

- Weeks 1-4: API improvements + multi-tenancy
- Weeks 5-8: Observability (logging, metrics, tracing)
- Weeks 9-12: Developer experience (docs, tooling)

**Deliverables**:
- Production-grade observability
- Complete documentation
- Enterprise-ready features

---

### Q3 2026 (Jul-Sep)
**Focus**: Advanced Features

- Performance optimization
- Caching strategy
- GraphQL API (if needed)
- WebSocket support (if needed)

**Deliverables**:
- Optimized performance
- Advanced API features

---

### Q4 2026 (Oct-Dec)
**Focus**: Innovation

- Admin UI
- A/B testing framework
- Plugin ecosystem
- Community features

**Deliverables**:
- Delightful developer experience
- Extensible platform

---

## Success Criteria

### Code Quality
- ✅ All files <300 LOC
- ✅ Cyclomatic complexity <10
- ✅ Test coverage >90%
- ✅ Zero technical debt incidents

### Enterprise Readiness
- ✅ Multi-tenant support
- ✅ Comprehensive monitoring
- ✅ SLA compliance (99.9% uptime)
- ✅ Security audit passed

### Developer Experience
- ✅ <30 min setup time
- ✅ <5 min CI/CD pipeline
- ✅ Complete documentation
- ✅ Active community

---

## Resource Allocation

### Team Composition
- 1 Senior Engineer (60% time)
- 1 Mid Engineer (40% time)
- 1 Technical Writer (20% time)

### Budget
- Engineering: 4 person-months
- Documentation: 1 person-month
- Infrastructure: $500/month (monitoring, testing)

---

## Risks & Mitigation

### Risk: Feature Creep
**Mitigation**: Strict prioritization, quarterly review

### Risk: Breaking Changes
**Mitigation**: API versioning, deprecation warnings

### Risk: Performance Regression
**Mitigation**: Continuous benchmarking, performance gates in CI

---

## Review & Retrospectives

### Monthly
- Progress review
- Adjust priorities
- Celebrate wins

### Quarterly
- Strategic planning
- Roadmap updates
- Team retrospective

---

**Last Updated**: 2025-12-18
**Next Review**: 2025-12-27
