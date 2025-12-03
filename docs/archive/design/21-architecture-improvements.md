# Pending Implementation Gaps and Improvements

**Document Version**: 1.0
**Last Updated**: 2025-12-02
**Status**: 📋 Implementation Backlog

> **Important**: This document describes **gaps to be implemented in the future**, NOT the current architecture. For the current architecture, see [01-architecture-overview.md](01-architecture-overview.md).

## Overview

This document captures critical improvements **identified but not yet implemented** through architectural analysis of the complex conversation management design. These are enhancements that should be added to make the system production-ready for very difficult conversations.

---

## Table of Contents

1. [Critical Gaps to Address](#critical-gaps-to-address)
2. [Over-Engineering to Simplify](#over-engineering-to-simplify)
3. [Architecture Refinements Applied](#architecture-refinements-applied)
4. [Implementation Priorities](#implementation-priorities)

---

## Critical Gaps to Address

### 1. Flow Stack Depth Limit Handling

**Problem**: Configuration sets `max_stack_depth: 3`, but no clear strategy when limit is reached.

**Impact**: HIGH - System could crash or behave unpredictably when users create deeply nested flows.

**Real Scenario**:
```
book_flight (active)
  → check_booking (pushes, pauses book_flight)
    → help flow (pushes, pauses check_booking)
      → User: "Actually, let me modify my booking" (would be 4th level!)
```

**Solution**:
```yaml
settings:
  flow_management:
    max_stack_depth: 3
    on_limit_reached: "cancel_oldest"  # or "reject_new" or "ask_user"
```

**Implementation**:
```python
def _push_flow(self, state: DialogueState, flow_name: str, reason: str = None):
    """Push new flow with depth limit handling"""

    # Check depth limit
    if len(state.flow_stack) >= self.config.flow_management.max_stack_depth:
        strategy = self.config.flow_management.on_limit_reached

        if strategy == "cancel_oldest":
            # Cancel oldest paused flow
            oldest = state.flow_stack.pop(0)
            oldest.flow_state = FlowState.CANCELLED
            state.metadata.setdefault("completed_flows", []).append(oldest)

        elif strategy == "reject_new":
            # Reject new flow, ask user to complete current
            raise FlowStackLimitError(
                f"Maximum flow depth ({self.config.max_stack_depth}) reached. "
                "Please complete or cancel current task before starting a new one."
            )

        elif strategy == "ask_user":
            # Ask user which flow to cancel
            return self._ask_which_flow_to_cancel(state, flow_name)

    # Proceed with push
    # ...
```

**Priority**: HIGH

---

### 2. Slot Scoping Conflicts

**Problem**: Same slot names across different flows with global `state.slots` dict.

**Impact**: HIGH - Slot values from one flow could incorrectly affect another paused flow.

**Example**:
```yaml
book_flight:
  slots: [origin, destination, date]

modify_booking:
  slots: [booking_ref, origin, destination, date]  # Same names!
```

**Issue**: If user changes `origin` in modify_booking, does it affect paused book_flight?

**Solution Option 1: Flow-Scoped Slots** (Recommended)
```python
state.flow_slots: dict[str, dict[str, Any]] = {
    "book_flight": {"origin": "NYC", "destination": "LA"},
    "modify_booking": {"booking_ref": "BK123", "origin": "Boston"}
}

# In RuntimeLoop
def _get_slot(self, state: DialogueState, slot_name: str) -> Any:
    """Get slot from current flow's scope"""
    active_flow = self._get_active_flow(state)
    if active_flow:
        return state.flow_slots.get(active_flow.flow_name, {}).get(slot_name)
    return None

def _set_slot(self, state: DialogueState, slot_name: str, value: Any):
    """Set slot in current flow's scope"""
    active_flow = self._get_active_flow(state)
    if active_flow:
        if active_flow.flow_name not in state.flow_slots:
            state.flow_slots[active_flow.flow_name] = {}
        state.flow_slots[active_flow.flow_name][slot_name] = value
```

**Solution Option 2: Explicit Namespacing**
```yaml
modify_booking:
  slots: [booking_ref, new_origin, new_destination]  # Prefixed
```

**Recommendation**: Use flow-scoped slots for better isolation.

**Priority**: HIGH

---

### 3. Cross-Flow Data Transfer

**Problem**: No mechanism to pass data between flows.

**Impact**: MEDIUM - Common use case not supported.

**Scenario**:
```
1. User: "Check my booking"
2. System: [checks] "BK-12345 is confirmed for Dec 15"
3. User: "Actually, I want to modify that booking"
   # How does modify_booking get booking_ref from check_booking?
```

**Solution**:
```python
@dataclass
class FlowContext:
    flow_name: str
    flow_state: FlowState
    current_step: str | None
    collected_slots: dict[str, Any]
    outputs: dict[str, Any] = field(default_factory=dict)  # NEW: Flow outputs
    started_at: float = field(default_factory=time.time)

# When check_booking completes
flow_context.outputs["booking_ref"] = "BK-12345"
flow_context.outputs["booking_status"] = "confirmed"

# When modify_booking starts
previous_flow = state.metadata.get("completed_flows", [])[-1]
if "booking_ref" in previous_flow.outputs:
    state.flow_slots["modify_booking"]["booking_ref"] = previous_flow.outputs["booking_ref"]
```

**Priority**: MEDIUM

---

### 4. Ambiguous Flow Resumption

**Problem**: Multiple paused flows with similar names, unclear which to resume.

**Impact**: MEDIUM - Poor UX when multiple flows are paused.

**Scenario**:
```
Flow stack: [book_flight(PAUSED), check_booking(PAUSED), modify_booking(ACTIVE)]
User: "Go back to booking"  # Which booking? book_flight or modify_booking?
```

**Solution**:
```python
def _disambiguate_resume_request(
    self,
    resume_intent: str,
    paused_flows: list[FlowContext]
) -> str:
    """
    Rank paused flows by relevance to resume request.

    Factors:
    - Keyword match with flow name/description
    - Recency (more recent = higher priority)
    - Flow category similarity
    """

    # Calculate relevance scores
    scores = []
    for flow in paused_flows:
        score = 0

        # Keyword match
        if any(kw in resume_intent.lower() for kw in flow.flow_name.split("_")):
            score += 10

        # Recency (inverse of pause time)
        time_paused = time.time() - flow.paused_at
        score += 5 / (1 + time_paused / 60)  # Decay over time

        scores.append((score, flow))

    # Sort by score
    scores.sort(reverse=True, key=lambda x: x[0])

    # If ambiguous (top 2 scores similar), ask user
    if len(scores) > 1 and abs(scores[0][0] - scores[1][0]) < 2:
        return self._ask_which_flow([s[1] for s in scores[:3]])

    # Return highest scoring flow
    return scores[0][1].flow_name
```

**Priority**: MEDIUM

---

### 5. Conversation Memory Management

**Problem**: No strategy for long conversations (100+ turns).

**Impact**: MEDIUM - Memory growth, performance degradation.

**Current Approach**: Unbounded growth
- `state.messages` grows infinitely
- `state.trace` grows infinitely
- `flow_stack` tracks all completed flows in metadata

**Solution**:
```yaml
settings:
  memory_management:
    max_history_messages: 50
    max_trace_events: 100
    summarize_after_turns: 20
    archive_completed_flows_after: 10
```

```python
def _prune_state(self, state: DialogueState):
    """Prune state to prevent unbounded growth"""

    # Prune message history
    if len(state.messages) > self.config.memory_management.max_history_messages:
        state.messages = state.messages[-self.config.max_history_messages:]

    # Prune trace
    if len(state.trace) > self.config.memory_management.max_trace_events:
        state.trace = state.trace[-self.config.max_trace_events:]

    # Archive old completed flows
    completed = state.metadata.get("completed_flows", [])
    if len(completed) > self.config.memory_management.archive_completed_flows_after:
        # Keep only recent N
        state.metadata["completed_flows"] = completed[-self.config.archive_completed_flows_after:]
```

**Priority**: MEDIUM

---

### 6. Message Queue Management

**Problem**: Queuing messages during `EXECUTING_ACTION` is underspecified.

**Impact**: LOW - Edge case but could cause issues.

**Missing**:
- Queue size limit
- Queue processing order
- Handling intent changes in queue

**Solution**:
```python
class MessageQueue:
    """Manages queued messages during action execution"""

    def __init__(self, max_size: int = 5):
        self.max_size = max_size
        self.queue: list[str] = []

    def enqueue(self, msg: str) -> bool:
        """Add message to queue"""
        if len(self.queue) >= self.max_size:
            return False  # Reject, queue full
        self.queue.append(msg)
        return True

    async def process_queued(self, state: DialogueState) -> list[str]:
        """Process queued messages after action completes"""
        responses = []

        while self.queue:
            msg = self.queue.pop(0)

            # Process message normally
            response = await self.process_message(msg, state)
            responses.append(response)

            # Stop if intent change detected
            if state.current_flow != previous_flow:
                break

        return responses
```

**Priority**: LOW

---

## Over-Engineering to Simplify

### 1. ✅ Separate VALIDATING_SLOT State (APPLIED)

**Issue**: VALIDATING_SLOT is not really a conversation state, it's instantaneous.

**Simplification**: Merge into WAITING_FOR_SLOT
```python
# In WAITING_FOR_SLOT handler
value = nlu_result.slot_value
if not validate(value):
    return reprompt_state(slot)  # Stay in WAITING_FOR_SLOT
else:
    state.slots[slot] = value
    return next_step_state()
```

**Status**: ❌ Keep VALIDATING_SLOT - it's useful for tracing and debugging

---

### 2. ✅ FlowStackManager as Separate Class (APPLIED)

**Issue**: Operations are simple list manipulations.

**Simplification**: Methods on RuntimeLoop
```python
class RuntimeLoop:
    def _push_flow(self, state, flow_name, reason): ...
    def _pop_flow(self, state, result): ...
```

**Status**: ✅ APPLIED - Now helper methods in RuntimeLoop

---

### 3. ✅ DigressionHandler Decomposition (APPLIED)

**Issue**: Original had single class with mixed responsibilities.

**Improvement**: Decompose into focused components
```python
class DigressionHandler:  # Coordinator
    def __init__(self, knowledge_base, help_generator):
        self.knowledge_base = knowledge_base
        self.help_generator = help_generator

class KnowledgeBase:  # Answers questions
class HelpGenerator:  # Generates help
```

**Status**: ✅ APPLIED - Proper separation of concerns

---

### 4. Excessive Flow Metadata

**Issue**: Too much unused metadata in flows.

**Current**:
```yaml
metadata:
  category: "booking"
  priority: "high"
  can_be_paused: true
  can_be_resumed: true
  max_pause_duration: 3600
  average_duration: 4
```

**Simplified**:
```yaml
metadata:
  can_be_paused: true  # Only what's actually used
```

**Status**: ⏳ TODO - Simplify in implementation

---

### 5. FlowContext Timing Complexity

**Issue**: Excessive timing tracking.

**Simplified**:
```python
@dataclass
class FlowContext:
    flow_name: str
    flow_state: FlowState
    current_step: str | None
    collected_slots: dict
    # Remove: started_at, paused_at, completed_at
    # Timing can be in trace if needed
```

**Status**: ❌ Keep timing - useful for debugging and timeout handling

---

### 6. Keywords Field in Trigger

**Issue**: Redundant with NLU training.

**Simplified**: Remove keywords, NLU learns from examples
```yaml
trigger:
  intents: [...]  # Only intents needed
  # Remove: keywords
```

**Status**: ⏳ TODO - Consider removing in implementation

---

## Architecture Refinements Already Applied ✅

The following refinements have been applied and are documented in [01-architecture-overview.md](01-architecture-overview.md):

### 1. ✅ RuntimeLoop as Orchestrator (APPLIED)

Flow stack operations simplified to helper methods in RuntimeLoop instead of a separate FlowStackManager class.

**Status**: Documented in architecture overview.

---

### 2. ✅ Digression Handler Decomposition (APPLIED)

DigressionHandler decomposed into:
- DigressionHandler (Coordinator)
- KnowledgeBase (Answer questions)
- HelpGenerator (Generate help/clarifications)

**Status**: Documented in architecture overview.

---

## Implementation Priorities

### Phase 1: High Priority Gaps (Week 1-2)

1. **Flow Stack Depth Limiting**
   - Implement `on_limit_reached` strategies
   - Add configuration options
   - Test edge cases

2. **Slot Scoping**
   - Implement flow-scoped slots (`state.flow_slots`)
   - Update slot getter/setter methods
   - Migrate existing code

3. **Cross-Flow Data Transfer**
   - Add `outputs` field to FlowContext
   - Implement output passing logic
   - Update YAML schema for output declarations

### Phase 2: Medium Priority Gaps (Week 3-4)

4. **Ambiguous Flow Resumption**
   - Implement disambiguation logic
   - Add user clarification prompts
   - Test with multiple paused flows

5. **Conversation Memory Management**
   - Implement pruning strategies
   - Add configuration options
   - Test with long conversations

### Phase 3: Low Priority & Simplifications (Week 5)

6. **Message Queue Management**
   - Implement proper queue handling
   - Add size limits
   - Handle intent changes in queue

7. **Simplify Flow Metadata**
   - Remove unused fields
   - Update documentation
   - Clean up YAML examples

---

## Summary

**Important**: This document describes **future improvements**, not current architecture.

**Current Status**:
- ✅ Architecture refinements applied (see doc 01)
- 🔴 High priority gaps identified but NOT YET implemented
- 🟡 Medium priority gaps identified but NOT YET implemented
- 🟢 Low priority items for future consideration

**Gaps to Implement (Priority Order)**:
1. 🔴 **HIGH**: Flow stack depth limiting
2. 🔴 **HIGH**: Slot scoping for flow isolation
3. 🟡 **MEDIUM**: Cross-flow data transfer
4. 🟡 **MEDIUM**: Flow resumption disambiguation
5. 🟡 **MEDIUM**: Conversation memory management
6. 🟢 **LOW**: Message queue management
7. 🟢 **LOW**: Simplify excessive metadata

**Implementation Plan**:
- Phase 1 (Week 1-2): High priority gaps
- Phase 2 (Week 3-4): Medium priority gaps
- Phase 3 (Week 5): Low priority items

**Where to Find Current Architecture**:
- [01-architecture-overview.md](01-architecture-overview.md) - Complete current architecture
- [05-complex-conversations.md](05-complex-conversations.md) - Flow stack and digression handling
- [06-flow-diagrams.md](06-flow-diagrams.md) - Visual diagrams

---

**Document Status**: Implementation backlog (NOT current architecture)
**Last Updated**: 2025-12-02
