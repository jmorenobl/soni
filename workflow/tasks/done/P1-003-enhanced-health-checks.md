## Task: P1-003 - Add Enhanced Health and Readiness Endpoints

**Task ID:** P1-003
**Milestone:** 2.3 - Observability
**Dependencies:** None
**Estimated Duration:** 2 hours

### Objective

Improve health check system with separate endpoints for liveness (`/health`) and readiness (`/ready`), compatible with Kubernetes and container orchestration systems.

### Context

**Current state:**
The `/health` endpoint only checks if runtime exists:

```python
@app.get("/health")
async def health_check(request: Request) -> HealthResponse:
    runtime = getattr(request.app.state, "runtime", None)
    return HealthResponse(
        status="healthy" if runtime is not None else "starting",
        version=__version__,
        initialized=runtime is not None,
    )
```

**Problems:**
- Doesn't distinguish "alive but not ready" from "ready for traffic"
- Doesn't verify dependency status (checkpointer, DU module)
- Kubernetes can't do safe rolling updates

**Solution - Separate probes:**
1. **Liveness Probe (`/health`)**: Is the process alive? (restart if fails)
2. **Readiness Probe (`/ready`)**: Can it receive traffic? (remove from LB if fails)

**Kubernetes usage:**
```yaml
livenessProbe:
  httpGet:
    path: /health
    port: 8000
  periodSeconds: 10

readinessProbe:
  httpGet:
    path: /ready
    port: 8000
  periodSeconds: 5
```

### Deliverables

- [ ] Endpoint `/ready` implemented
- [ ] `/health` enhanced with component information
- [ ] Response model updated with component details
- [ ] Tests for all health/ready scenarios
- [ ] OpenAPI documentation updated

---

### Implementation Details

#### Step 1: Add response models

**File:** `src/soni/server/models.py`

**Replace current HealthResponse and add new models:**

```python
from datetime import datetime
from typing import Literal


class ComponentStatus(BaseModel):
    """Status of a single component."""

    name: str
    status: Literal["healthy", "degraded", "unhealthy"]
    message: str | None = None


class HealthResponse(BaseModel):
    """Health check response with component details.

    Breaking change: `initialized` field removed.
    Use `status` field or /ready endpoint instead.
    """

    status: Literal["healthy", "starting", "degraded", "unhealthy"]
    version: str
    timestamp: str  # ISO format
    components: dict[str, ComponentStatus] | None = None


class ReadinessResponse(BaseModel):
    """Readiness probe response."""

    ready: bool
    message: str
    checks: dict[str, bool] | None = None
```

#### Step 2: Implement /ready endpoint

**File:** `src/soni/server/api.py`

**Add imports:**

```python
from datetime import datetime, timezone
from fastapi import HTTPException
```

**Add /ready endpoint:**

```python
@app.get("/ready", response_model=ReadinessResponse)
async def readiness_check(request: Request) -> ReadinessResponse:
    """Readiness probe for Kubernetes.

    Returns 200 if the service is ready to accept traffic.
    Returns 503 if the service is not ready.

    Use this for Kubernetes readiness probes to control
    when pods receive traffic after startup or during issues.
    """
    runtime: RuntimeLoop | None = getattr(request.app.state, "runtime", None)

    checks: dict[str, bool] = {}

    # Check 1: Runtime exists
    checks["runtime_exists"] = runtime is not None

    # Check 2: Components initialized
    components_ok = False
    if runtime and runtime._components:
        components_ok = (
            runtime._components.graph is not None
            and runtime._components.du is not None
            and runtime._components.flow_manager is not None
        )
    checks["components_initialized"] = components_ok

    # Check 3: Graph is compiled (can process messages)
    checks["graph_ready"] = (
        runtime is not None
        and runtime._components is not None
        and runtime._components.graph is not None
    )

    # Overall readiness
    ready = all(checks.values())

    if not ready:
        failed_checks = [k for k, v in checks.items() if not v]
        raise HTTPException(
            status_code=503,
            detail={
                "ready": False,
                "message": f"Not ready: {', '.join(failed_checks)}",
                "checks": checks,
            },
        )

    return ReadinessResponse(
        ready=True,
        message="Service is ready to accept traffic",
        checks=checks,
    )
```

#### Step 3: Enhance /health endpoint

**File:** `src/soni/server/api.py`

**Replace current /health implementation:**

```python
@app.get("/health", response_model=HealthResponse)
async def health_check(request: Request) -> HealthResponse:
    """Liveness probe for Kubernetes.

    Returns basic health status. Use for Kubernetes liveness probes
    to detect if the process needs to be restarted.

    For detailed component status, see /ready endpoint.
    """
    runtime: RuntimeLoop | None = getattr(request.app.state, "runtime", None)

    # Determine overall status
    if runtime is None:
        status = "starting"
    elif runtime._components is None:
        status = "starting"
    elif runtime._components.graph is None:
        status = "degraded"
    else:
        status = "healthy"

    # Build component status (optional detail)
    components: dict[str, ComponentStatus] | None = None
    if runtime and runtime._components:
        components = {
            "runtime": ComponentStatus(
                name="runtime",
                status="healthy",
                message=None,
            ),
            "graph": ComponentStatus(
                name="graph",
                status="healthy" if runtime._components.graph else "unhealthy",
                message="Compiled and ready" if runtime._components.graph else "Not compiled",
            ),
            "checkpointer": ComponentStatus(
                name="checkpointer",
                status="healthy" if runtime._components.checkpointer else "degraded",
                message="Connected" if runtime._components.checkpointer else "None (in-memory only)",
            ),
        }

    return HealthResponse(
        status=status,
        version=__version__,
        timestamp=datetime.now(timezone.utc).isoformat(),
        components=components,
    )
```

#### Step 4: Add startup endpoint (optional but recommended)

**File:** `src/soni/server/api.py`

```python
@app.get("/startup")
async def startup_check(request: Request) -> dict[str, bool]:
    """Startup probe for Kubernetes.

    Returns 200 once initial startup is complete.
    Use for Kubernetes startupProbe to give the app time to initialize.
    """
    runtime: RuntimeLoop | None = getattr(request.app.state, "runtime", None)

    if runtime is None or runtime._components is None:
        raise HTTPException(
            status_code=503,
            detail={"started": False, "message": "Still initializing"},
        )

    return {"started": True}
```

---

### TDD Cycle (MANDATORY)

#### Red Phase: Write Failing Tests

**Test file:** `tests/unit/server/test_health_endpoints.py`

```python
"""Tests for health and readiness endpoints.

Verifies /health and /ready endpoints work correctly for Kubernetes integration.
"""

from datetime import datetime
from unittest.mock import MagicMock

import pytest
from fastapi.testclient import TestClient

from soni.server.api import app


@pytest.fixture
def client() -> TestClient:
    """Create test client."""
    return TestClient(app, raise_server_exceptions=False)


@pytest.fixture
def mock_runtime() -> MagicMock:
    """Create fully initialized mock runtime."""
    runtime = MagicMock()
    runtime._components = MagicMock()
    runtime._components.graph = MagicMock()
    runtime._components.du = MagicMock()
    runtime._components.flow_manager = MagicMock()
    runtime._components.checkpointer = MagicMock()
    return runtime


@pytest.fixture(autouse=True)
def reset_app_state() -> None:
    """Reset app state before each test."""
    app.state.runtime = None
    app.state.config = None


class TestHealthEndpoint:
    """Tests for /health liveness endpoint."""

    def test_health_returns_healthy_when_initialized(
        self, client: TestClient, mock_runtime: MagicMock
    ) -> None:
        """Test /health returns healthy when runtime is fully initialized."""
        app.state.runtime = mock_runtime

        response = client.get("/health")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert "version" in data
        assert "timestamp" in data

    def test_health_returns_starting_when_no_runtime(
        self, client: TestClient
    ) -> None:
        """Test /health returns starting when runtime not yet created."""
        response = client.get("/health")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "starting"

    def test_health_returns_starting_when_no_components(
        self, client: TestClient
    ) -> None:
        """Test /health returns starting when runtime has no components."""
        runtime = MagicMock()
        runtime._components = None
        app.state.runtime = runtime

        response = client.get("/health")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "starting"

    def test_health_returns_degraded_when_graph_missing(
        self, client: TestClient
    ) -> None:
        """Test /health returns degraded when graph is not compiled."""
        runtime = MagicMock()
        runtime._components = MagicMock()
        runtime._components.graph = None
        app.state.runtime = runtime

        response = client.get("/health")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "degraded"

    def test_health_includes_component_details(
        self, client: TestClient, mock_runtime: MagicMock
    ) -> None:
        """Test /health includes component status details."""
        app.state.runtime = mock_runtime

        response = client.get("/health")

        data = response.json()
        assert "components" in data
        assert "runtime" in data["components"]
        assert "graph" in data["components"]

    def test_health_timestamp_is_valid_iso(
        self, client: TestClient, mock_runtime: MagicMock
    ) -> None:
        """Test timestamp is valid ISO format."""
        app.state.runtime = mock_runtime

        response = client.get("/health")

        data = response.json()
        # Should not raise
        datetime.fromisoformat(data["timestamp"].replace("Z", "+00:00"))


class TestReadinessEndpoint:
    """Tests for /ready readiness endpoint."""

    def test_ready_returns_200_when_fully_initialized(
        self, client: TestClient, mock_runtime: MagicMock
    ) -> None:
        """Test /ready returns 200 when service is ready."""
        app.state.runtime = mock_runtime

        response = client.get("/ready")

        assert response.status_code == 200
        data = response.json()
        assert data["ready"] is True
        assert "checks" in data

    def test_ready_returns_503_when_no_runtime(
        self, client: TestClient
    ) -> None:
        """Test /ready returns 503 when runtime not created."""
        response = client.get("/ready")

        assert response.status_code == 503
        data = response.json()["detail"]
        assert data["ready"] is False
        assert "runtime_exists" in data["checks"]

    def test_ready_returns_503_when_graph_missing(
        self, client: TestClient
    ) -> None:
        """Test /ready returns 503 when graph not compiled."""
        runtime = MagicMock()
        runtime._components = MagicMock()
        runtime._components.graph = None
        runtime._components.du = MagicMock()
        runtime._components.flow_manager = MagicMock()
        app.state.runtime = runtime

        response = client.get("/ready")

        assert response.status_code == 503

    def test_ready_checks_all_components(
        self, client: TestClient, mock_runtime: MagicMock
    ) -> None:
        """Test /ready checks all required components."""
        app.state.runtime = mock_runtime

        response = client.get("/ready")

        data = response.json()
        checks = data["checks"]
        assert "runtime_exists" in checks
        assert "components_initialized" in checks
        assert "graph_ready" in checks

    def test_ready_fails_if_du_missing(
        self, client: TestClient
    ) -> None:
        """Test /ready fails if DU module is missing."""
        runtime = MagicMock()
        runtime._components = MagicMock()
        runtime._components.graph = MagicMock()
        runtime._components.du = None  # Missing!
        runtime._components.flow_manager = MagicMock()
        app.state.runtime = runtime

        response = client.get("/ready")

        assert response.status_code == 503


class TestStartupEndpoint:
    """Tests for /startup startup probe endpoint."""

    def test_startup_returns_200_when_initialized(
        self, client: TestClient, mock_runtime: MagicMock
    ) -> None:
        """Test /startup returns 200 after initialization."""
        app.state.runtime = mock_runtime

        response = client.get("/startup")

        assert response.status_code == 200
        assert response.json()["started"] is True

    def test_startup_returns_503_during_init(
        self, client: TestClient
    ) -> None:
        """Test /startup returns 503 during initialization."""
        response = client.get("/startup")

        assert response.status_code == 503


class TestKubernetesIntegration:
    """Tests simulating Kubernetes probe behavior."""

    def test_probe_sequence_during_startup(
        self, client: TestClient, mock_runtime: MagicMock
    ) -> None:
        """Test typical Kubernetes probe sequence during app startup."""
        # Phase 1: App starting, no runtime yet
        # Startup probe should fail (503)
        assert client.get("/startup").status_code == 503
        # Readiness should fail (503)
        assert client.get("/ready").status_code == 503
        # Health should return starting (200)
        assert client.get("/health").status_code == 200
        assert client.get("/health").json()["status"] == "starting"

        # Phase 2: Runtime initialized
        app.state.runtime = mock_runtime

        # All probes should succeed
        assert client.get("/startup").status_code == 200
        assert client.get("/ready").status_code == 200
        assert client.get("/health").status_code == 200
        assert client.get("/health").json()["status"] == "healthy"

    def test_probe_during_graceful_shutdown(
        self, client: TestClient, mock_runtime: MagicMock
    ) -> None:
        """Test probe behavior during graceful shutdown."""
        app.state.runtime = mock_runtime

        # Initially ready
        assert client.get("/ready").status_code == 200

        # Simulate shutdown: components being cleaned up
        mock_runtime._components = None

        # Readiness should fail (remove from load balancer)
        assert client.get("/ready").status_code == 503
        # Health should show starting/degraded
        assert client.get("/health").json()["status"] in ["starting", "degraded"]
```

**Run tests (should fail):**
```bash
uv run pytest tests/unit/server/test_health_endpoints.py -v
# Expected: FAILED (/ready not implemented)
```

**Commit:**
```bash
git add tests/
git commit -m "test: add failing tests for enhanced health endpoints (P1-003)"
```

#### Green Phase: Make Tests Pass

**Implement changes from "Implementation Details" section.**

**Verify:**
```bash
uv run pytest tests/unit/server/test_health_endpoints.py -v
# Expected: PASSED ✅
```

**Commit:**
```bash
git add src/ tests/
git commit -m "feat: add /ready endpoint and enhance /health (P1-003)"
```

---

### Success Criteria

- [ ] `/ready` returns 200 when all components ready
- [ ] `/ready` returns 503 when any component missing
- [ ] `/health` includes component details and timestamp
- [ ] `/startup` works for startup probe
- [ ] All tests pass
- [ ] OpenAPI docs show new endpoints

### Manual Validation

```bash
# 1. Run health endpoint tests
uv run pytest tests/unit/server/test_health_endpoints.py -v

# 2. Start server and test manually
uv run soni server --config examples/banking/domain &
SERVER_PID=$!
sleep 5

# Test endpoints
curl http://localhost:8000/health | jq
curl http://localhost:8000/ready | jq
curl http://localhost:8000/startup | jq

# Check OpenAPI docs
curl http://localhost:8000/openapi.json | jq '.paths | keys'

kill $SERVER_PID

# 3. Run all server tests
uv run pytest tests/unit/server/ -v
```

### References

- `src/soni/server/api.py` - Current endpoints
- `src/soni/server/models.py` - Response models
- [Kubernetes Probes](https://kubernetes.io/docs/tasks/configure-pod-container/configure-liveness-readiness-startup-probes/)
- [FastAPI OpenAPI](https://fastapi.tiangolo.com/tutorial/path-operation-configuration/)

### Notes

**Probe differences:**

| Probe | Purpose | Failure = |
|-------|---------|-----------|
| Startup | App finished initializing | Wait (don't restart) |
| Liveness | Process is alive | Restart pod |
| Readiness | Can receive traffic | Remove from LB |

**Recommended Kubernetes config:**

```yaml
startupProbe:
  httpGet:
    path: /startup
    port: 8000
  failureThreshold: 30
  periodSeconds: 2
  # Waits up to 60s for initialization

livenessProbe:
  httpGet:
    path: /health
    port: 8000
  initialDelaySeconds: 0  # startup probe already verified
  periodSeconds: 10
  failureThreshold: 3

readinessProbe:
  httpGet:
    path: /ready
    port: 8000
  initialDelaySeconds: 0
  periodSeconds: 5
  failureThreshold: 1  # Remove from LB immediately
```

**Don't check external dependencies in liveness:**
Liveness should be "is my process alive?", not "is the database alive?". If DB is down, restarting the pod won't help. That's what readiness is for.
