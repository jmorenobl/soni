# Complex Conversations and Flow Management

**Document Version**: 1.1
**Last Updated**: 2025-12-02
**Status**: ✅ Design Proposal (Updated)

> **Ground Truth**: See [01-architecture-overview.md](01-architecture-overview.md) for the definitive architecture.

## Table of Contents

1. [Overview](#overview)
2. [Problems to Solve](#problems-to-solve)
3. [Flow Stack Architecture](#flow-stack-architecture)
4. [Digression Management](#digression-management)
5. [Flow Metadata and Descriptions](#flow-metadata-and-descriptions)
6. [Flow State Machine](#flow-state-machine)
7. [Implementation Design](#implementation-design)
8. [YAML Configuration Updates](#yaml-configuration-updates)
9. [Examples](#examples)

---

## Overview

Real conversations are messy. Users:
- Change their mind mid-flow ("Actually, I want to cancel instead")
- Ask questions ("What cities do you support?")
- Start new tasks before finishing current ones
- Come back to previous topics ("Going back to my booking...")

This document extends the core architecture to handle these **complex conversation patterns**.

### Design Goals

1. ✅ Support **flow interruptions** without losing state
2. ✅ Enable **digression detection** and handling
3. ✅ Provide **rich context** to LLM for better intent understanding
4. ✅ Allow **resuming paused flows** when user returns
5. ✅ Maintain **conversation coherence** across flow switches

---

## Problems to Solve

### Problem 1: Flow Interruption

**Scenario**:
```
User: "I want to book a flight"
Bot:  "Where would you like to fly from?"
User: "Actually, I want to check my existing booking first"
```

**Question**: What happens to the `book_flight` flow?
- ❌ Cancel it? User loses progress
- ❌ Continue it? Bot ignores user intent
- ✅ **Pause it** and allow resuming later

### Problem 2: Digressions

**Scenario**:
```
Bot:  "Where would you like to fly from?"
User: "What cities do you support?"
Bot:  [answers question]
Bot:  "So, where would you like to fly from?"  ← Resume original question
```

**Question**: How to detect and handle digressions?
- Digression = temporary deviation that should return to main flow
- Need to distinguish from intent changes

### Problem 3: Limited LLM Context

**Scenario**:
```yaml
flows:
  book_flight:
    trigger:
      intents:
        - "I want to book a flight"
```

**Problem**: The LLM only sees intent examples, not what the flow actually does.

**Solution**: Add rich descriptions:
```yaml
flows:
  book_flight:
    description: "Book a new flight reservation. Collects origin, destination, and date, then searches for available flights."
    trigger:
      intents:
        - "I want to book a flight"
```

### Problem 4: Flow State Tracking

**Current State**:
```python
state.current_flow = "book_flight"  # Only tracks ONE active flow
```

**Problem**:
- Can't track paused flows
- Can't distinguish between "active" and "paused"
- No history of completed flows

---

## Flow Stack Architecture

### Concept: Flow Stack

Instead of a single `current_flow`, maintain a **stack of flow contexts**:

```python
state.flow_stack = [
    {
        "flow_name": "book_flight",
        "flow_state": "paused",
        "current_step": "collect_origin",
        "collected_slots": {"origin": None, "destination": None},
        "paused_at": 1701234567.89,
        "context": "User asked to check booking first"
    },
    {
        "flow_name": "check_booking",
        "flow_state": "active",
        "current_step": "request_booking_ref",
        "collected_slots": {"booking_ref": None},
        "started_at": 1701234590.12,
        "context": None
    }
]
```

**Stack semantics**:
- **Top of stack** = Currently active flow
- **Below top** = Paused flows that can be resumed
- **Pop** when flow completes (returns to previous flow)
- **Push** when new flow starts (pauses current flow)

### Updated DialogueState Schema

```python
from dataclasses import dataclass
from enum import Enum

class FlowState(str, Enum):
    """State of a flow in the stack"""
    ACTIVE = "active"       # Currently executing
    PAUSED = "paused"       # Interrupted, can resume
    COMPLETED = "completed" # Finished successfully
    CANCELLED = "cancelled" # User cancelled

@dataclass
class FlowContext:
    """Complete context for a flow in the stack"""
    flow_name: str
    flow_state: FlowState
    current_step: str | None
    collected_slots: dict[str, Any]
    started_at: float
    paused_at: float | None = None
    completed_at: float | None = None
    context: str | None = None  # Why paused/cancelled

class DialogueState(TypedDict):
    # ... existing fields ...

    # NEW: Flow management
    flow_stack: list[FlowContext]
    """Stack of flow contexts. Top = active flow."""

    current_flow: str  # DEPRECATED: Use flow_stack[-1].flow_name
    """Maintained for backward compatibility"""

    # NEW: Digression tracking
    digression_depth: int
    """How many digressions deep are we? 0 = main flow"""

    last_digression_type: str | None
    """Type of last digression: 'question', 'clarification', 'new_intent'"""
```

### Flow Stack Operations

Flow stack operations are simple list manipulations handled directly by RuntimeLoop as helper methods:

```python
# In RuntimeLoop class

def _push_flow(self, state: DialogueState, flow_name: str, reason: str = None):
    """
    Helper: Push new flow to stack, pausing current one.

    This is a simple list operation - no need for a separate manager class.
    """
    # Pause current flow if exists
    if state.flow_stack:
        current = state.flow_stack[-1]
        current.flow_state = FlowState.PAUSED
        current.paused_at = time.time()
        current.context = reason

    # Push new flow
    new_flow = FlowContext(
        flow_name=flow_name,
        flow_state=FlowState.ACTIVE,
        current_step=None,
        collected_slots={},
        started_at=time.time(),
    )
    state.flow_stack.append(new_flow)
    state.current_flow = flow_name  # Backward compatibility

def _pop_flow(self, state: DialogueState, result: FlowState = FlowState.COMPLETED):
    """
    Helper: Pop current flow and resume previous one.

    This is a simple list operation - no need for a separate manager class.
    """
    if not state.flow_stack:
        raise ValueError("Cannot pop empty flow stack")

    # Complete current flow
    current = state.flow_stack.pop()
    current.flow_state = result
    current.completed_at = time.time()

    # Archive completed flow in state.metadata
    state.metadata.setdefault("completed_flows", []).append(current)

    # Resume previous flow if exists
    if state.flow_stack:
        previous = state.flow_stack[-1]
        previous.flow_state = FlowState.ACTIVE
        state.current_flow = previous.flow_name
    else:
        state.current_flow = "none"

def _get_active_flow(self, state: DialogueState) -> FlowContext | None:
    """Helper: Get currently active flow (top of stack)"""
    return state.flow_stack[-1] if state.flow_stack else None

def _get_paused_flows(self, state: DialogueState) -> list[FlowContext]:
    """Helper: Get all paused flows"""
    return [f for f in state.flow_stack if f.flow_state == FlowState.PAUSED]
```

**Design Decision**: These are simple list operations, not complex domain logic. Keeping them as helper methods on RuntimeLoop avoids unnecessary class extraction while maintaining code organization.

---

## Digression Management

### What is a Digression?

**Digression**: Temporary deviation from main flow that should **return to the original context**.

**Types of Digressions**:

1. **Questions**: "What cities do you support?"
2. **Clarifications**: "Why do you need my date of birth?"
3. **Help requests**: "How does this work?"
4. **Status checks**: "What information do you still need?"

**NOT digressions** (these are intent changes):
- "Actually, I want to cancel instead" → Intent change, pause current flow
- "Book a different flight" → Intent change, start new flow

### Digression Detection

The **NLU** must detect digressions:

```python
class DigressionType(str, Enum):
    NONE = "none"
    QUESTION = "question"           # "What X?"
    CLARIFICATION = "clarification" # "Why do you need X?"
    HELP = "help"                   # "How does this work?"
    STATUS = "status"               # "What do you still need?"
    SMALL_TALK = "small_talk"       # "How are you?"

@dataclass
class NLUResult:
    # ... existing fields ...

    # NEW: Digression detection
    is_digression: bool
    """True if message is a digression, not a slot value or intent change"""

    digression_type: DigressionType | None
    """Type of digression if is_digression=True"""

    digression_topic: str | None
    """What the digression is about (e.g., "supported cities")"""
```

### Digression Handling Flow

```
Message received
  ↓
NLU with enriched context
  ↓
Is digression detected?
  ├─ YES → Handle digression
  │   ↓
  │   Answer question/provide help
  │   ↓
  │   Re-prompt original question
  │   ↓
  │   Continue main flow (don't change flow_stack)
  │
  └─ NO → Continue normal processing
```

### Implementation Architecture

The digression handling is decomposed into focused components:

```python
class DigressionHandler:
    """
    Coordinator for digression handling.

    Delegates to specialized components based on digression type.
    """

    def __init__(self, knowledge_base: KnowledgeBase, help_generator: HelpGenerator):
        self.knowledge_base = knowledge_base
        self.help_generator = help_generator

    async def handle(
        self,
        state: DialogueState,
        digression_type: DigressionType,
        digression_topic: str,
    ) -> DialogueState:
        """
        Handle a digression without changing flow stack.

        Args:
            state: Current dialogue state
            digression_type: Type of digression
            digression_topic: What user asked about

        Returns:
            Updated state with digression response
        """
        # Track digression depth
        state.digression_depth += 1
        state.last_digression_type = digression_type

        # Delegate to appropriate component
        if digression_type == DigressionType.QUESTION:
            response = await self.knowledge_base.answer_question(
                digression_topic,
                state
            )
        elif digression_type in (DigressionType.CLARIFICATION, DigressionType.HELP):
            response = await self.help_generator.generate_help(state)
        elif digression_type == DigressionType.STATUS:
            response = await self.help_generator.generate_status(state)
        else:
            response = "I'm not sure how to help with that."

        # Re-prompt original question
        if state.waiting_for_slot:
            slot_config = self.config.slots[state.waiting_for_slot]
            reprompt = slot_config.prompt
            response = f"{response}\n\n{reprompt}"

        state.last_response = response
        state.digression_depth -= 1

        return state


class KnowledgeBase:
    """
    Answers domain-specific questions using knowledge base, RAG, or documentation.

    Can be extended with:
    - Vector database for semantic search
    - RAG pipeline for contextual answers
    - FAQ database
    """

    async def answer_question(self, topic: str, context: DialogueState) -> str:
        """
        Answer a domain-specific question.

        Args:
            topic: What the user is asking about
            context: Current dialogue state for contextualization

        Returns:
            Answer to the question
        """
        # Implementation: Query knowledge base, use RAG, etc.
        pass


class HelpGenerator:
    """
    Generates contextual help and clarifications based on conversation state.
    """

    async def generate_help(self, state: DialogueState) -> str:
        """
        Generate contextual help message.

        Args:
            state: Current dialogue state

        Returns:
            Help message tailored to current context
        """
        # Implementation: Generate help based on current flow and step
        pass

    async def generate_status(self, state: DialogueState) -> str:
        """
        Generate status message showing what's been collected.

        Args:
            state: Current dialogue state

        Returns:
            Status summary
        """
        # Implementation: Summarize collected slots and next steps
        pass

    async def generate_clarification(self, topic: str, state: DialogueState) -> str:
        """
        Explain why we need certain information.

        Args:
            topic: What needs clarification
            state: Current dialogue state

        Returns:
            Clarification message
        """
        # Implementation: Explain purpose of requested information
        pass
```

---

## Flow Metadata and Descriptions

### Enhanced Flow Configuration

```yaml
flows:
  book_flight:
    # NEW: Rich description for LLM context
    description: >
      Book a new flight reservation. This flow collects the origin city,
      destination city, and departure date from the user, then searches
      for available flights and confirms the booking.

    # NEW: Metadata for better context
    metadata:
      category: "booking"
      priority: "high"
      average_duration: 4  # Average number of turns
      can_be_paused: true  # Can this flow be interrupted?
      can_be_resumed: true # Can this flow be resumed after pause?

    # Trigger configuration
    trigger:
      # Intent examples (for NLU training)
      intents:
        - "I want to book a flight"
        - "Book me a flight"
        - "I need to fly to {destination}"

      # NEW: Keywords that strongly suggest this flow
      keywords:
        - "book"
        - "flight"
        - "reservation"

    # Steps remain the same
    steps:
      - step: collect_origin
        type: collect
        slot: origin
```

### Using Descriptions in NLU

The **NLU context** should include flow descriptions:

```python
class NLUContext:
    # ... existing fields ...

    # NEW: Enhanced flow context
    available_flows: list[FlowInfo]
    """List of available flows with descriptions"""

    active_flow_description: str | None
    """Description of currently active flow"""

    paused_flows: list[FlowInfo]
    """List of paused flows (for resume detection)"""

@dataclass
class FlowInfo:
    """Flow information for NLU context"""
    name: str
    description: str
    category: str
    keywords: list[str]
```

### NLU Prompt with Context

```python
async def build_nlu_prompt(self, state: DialogueState) -> str:
    """Build NLU prompt with rich flow context"""

    # Get available flows
    flows_context = []
    for flow_name, flow_config in self.config.flows.items():
        flows_context.append(
            f"- {flow_name}: {flow_config.description}"
        )

    # Get paused flows
    paused = self.flow_stack.get_paused_flows(state)
    paused_context = ""
    if paused:
        paused_context = "\n\nPaused flows that can be resumed:\n"
        for flow in paused:
            flow_config = self.config.flows[flow.flow_name]
            paused_context += f"- {flow.flow_name}: {flow_config.description}\n"

    # Build prompt
    prompt = f"""
You are a dialogue understanding system. Analyze the user's message and determine:
1. Is it a slot value for the current question?
2. Is it a digression (question, clarification, help)?
3. Is it an intent change (new task or flow switch)?
4. Is it a request to resume a paused flow?

Available flows:
{chr(10).join(flows_context)}
{paused_context}

Current conversation state: {state.conversation_state}
Current flow: {state.current_flow}
Waiting for slot: {state.waiting_for_slot}

User message: {message}

Analyze and respond with:
- intent: The detected intent or flow name
- is_digression: true/false
- digression_type: question/clarification/help/status/none
- slot_values: {{slot_name: value}}
- confidence: 0.0-1.0
"""
    return prompt
```

---

## Flow State Machine

### Flow States

```python
class FlowState(str, Enum):
    """State of a flow in the stack"""

    ACTIVE = "active"
    """Currently executing, at top of stack"""

    PAUSED = "paused"
    """Interrupted by another flow, can be resumed"""

    COMPLETED = "completed"
    """Finished successfully"""

    CANCELLED = "cancelled"
    """User explicitly cancelled"""

    ABANDONED = "abandoned"
    """User started something else, didn't come back"""

    ERROR = "error"
    """Flow failed due to error"""
```

### State Transitions

```
        START
          │
          ▼
      ┌─────────┐
      │ ACTIVE  │◄──────┐
      └────┬────┘       │
           │            │
    ┌──────┼──────┐    │
    │      │      │    │
    │      │      │  Resume
    │      │      │    │
    ▼      ▼      ▼    │
┌────────┐ │  ┌────────┴──┐
│COMPLETE│ │  │  PAUSED   │
└────────┘ │  └───────────┘
           │
    ┌──────┼──────┐
    │      │      │
    ▼      ▼      ▼
┌────────┐ │  ┌──────────┐
│CANCEL  │ │  │  ERROR   │
└────────┘ │  └──────────┘
           │
           ▼
      ┌──────────┐
      │ABANDONED │
      └──────────┘
```

### Transition Rules

| From | To | Trigger | Conditions |
|------|-----|---------|------------|
| ACTIVE | PAUSED | New flow started | Another flow pushed to stack |
| ACTIVE | COMPLETED | Flow finished | All steps completed successfully |
| ACTIVE | CANCELLED | User cancels | User explicitly cancels ("cancel", "stop") |
| ACTIVE | ERROR | Exception | Unhandled error during execution |
| PAUSED | ACTIVE | Resume | User asks to resume OR previous flow completes |
| PAUSED | ABANDONED | Timeout | Paused for too long (configurable) |
| PAUSED | CANCELLED | User cancels | User explicitly cancels paused flow |

---

## Implementation Design

### 1. Update RuntimeLoop

```python
class RuntimeLoop:
    """
    Main orchestrator for message processing.

    Responsibilities:
    - Route messages to appropriate handlers
    - Manage flow stack (simple push/pop operations)
    - Coordinate NLU, graph execution, and state management
    """

    def __init__(self, config, nlu_provider, graph, checkpointer):
        self.config = config
        self.nlu_provider = nlu_provider
        self.graph = graph
        self.checkpointer = checkpointer

        # Dependency injection for digression handling
        knowledge_base = KnowledgeBase(config)
        help_generator = HelpGenerator(config)
        self.digression_handler = DigressionHandler(knowledge_base, help_generator)

    async def process_message(self, msg: str, user_id: str) -> str:
        """Process message with flow stack support"""

        # Load state
        state = await self._load_state(user_id)

        # Route message
        route = await self.route_message(msg, state)

        # Check for digression
        if route.is_digression:
            state = await self.digression_handler.handle(
                state,
                route.digression_type,
                route.digression_topic
            )
            await self._save_state(user_id, state)
            return state.last_response

        # Check for flow switch
        if route.type == "intent_change":
            new_flow = route.detected_flow

            # Push new flow (pauses current) - simple list operation
            self._push_flow(state, new_flow, reason=f"User requested: {msg}")

        # Check for resume request
        if route.type == "resume_flow":
            flow_to_resume = route.flow_name
            # Pop flows until we get to the one to resume
            self._pop_to_flow(state, flow_to_resume)

        # Continue with normal processing
        # ...

    def _push_flow(self, state: DialogueState, flow_name: str, reason: str = None):
        """Helper: Push new flow to stack (simple list operation)"""
        if state.flow_stack:
            state.flow_stack[-1].flow_state = FlowState.PAUSED
            state.flow_stack[-1].paused_at = time.time()
            state.flow_stack[-1].context = reason

        new_flow = FlowContext(
            flow_name=flow_name,
            flow_state=FlowState.ACTIVE,
            current_step=None,
            collected_slots={},
            started_at=time.time(),
        )
        state.flow_stack.append(new_flow)
        state.current_flow = flow_name

    def _pop_flow(self, state: DialogueState, result: FlowState = FlowState.COMPLETED):
        """Helper: Pop flow from stack (simple list operation)"""
        if not state.flow_stack:
            raise ValueError("Cannot pop empty flow stack")

        current = state.flow_stack.pop()
        current.flow_state = result
        current.completed_at = time.time()

        # Archive completed flow
        state.metadata.setdefault("completed_flows", []).append(current)

        # Resume previous flow if exists
        if state.flow_stack:
            previous = state.flow_stack[-1]
            previous.flow_state = FlowState.ACTIVE
            state.current_flow = previous.flow_name
        else:
            state.current_flow = "none"

    def _pop_to_flow(self, state: DialogueState, flow_name: str):
        """Helper: Pop flows until reaching specified flow"""
        while state.flow_stack:
            if state.flow_stack[-1].flow_name == flow_name:
                state.flow_stack[-1].flow_state = FlowState.ACTIVE
                state.current_flow = flow_name
                return
            self._pop_flow(state, FlowState.CANCELLED)

        raise ValueError(f"Flow {flow_name} not found in stack")
```

### 2. Update NLU Signatures

```python
class UnderstandUserMessage(dspy.Signature):
    """Enhanced NLU signature with digression and flow context"""

    # Inputs
    user_message: str = dspy.InputField(desc="The user's message")
    conversation_context: str = dspy.InputField(desc="Current conversation context")
    available_flows: str = dspy.InputField(desc="Available flows with descriptions")
    paused_flows: str = dspy.InputField(desc="Paused flows that can be resumed")
    waiting_for_slot: str | None = dspy.InputField(desc="Slot we're waiting for, if any")

    # Outputs
    intent: str = dspy.OutputField(desc="Detected intent or flow name")
    is_digression: bool = dspy.OutputField(desc="Is this a digression?")
    digression_type: str = dspy.OutputField(desc="Type: question/clarification/help/status/none")
    is_resume_request: bool = dspy.OutputField(desc="Is user asking to resume a paused flow?")
    resume_flow_name: str | None = dspy.OutputField(desc="Which flow to resume, if any")
    slot_values: dict[str, str] = dspy.OutputField(desc="Extracted slot values")
    confidence: float = dspy.OutputField(desc="Confidence 0.0-1.0")
```

### 3. Update YAML Schema

```yaml
# Enhanced flow configuration
flows:
  book_flight:
    # Required
    description: "Human-readable description for LLM context"

    # Optional metadata
    metadata:
      category: "booking"        # Group flows by category
      priority: "high"            # Priority for intent resolution
      can_be_paused: true        # Can interrupt this flow?
      can_be_resumed: true       # Can resume after pause?
      max_pause_duration: 3600   # Abandon after 1 hour

    # Trigger configuration
    trigger:
      intents: [...]             # Intent examples
      keywords: [...]            # Strongly indicative keywords

    # Steps
    steps: [...]
```

---

## YAML Configuration Updates

### Example: Complete Configuration

```yaml
version: "0.2"  # New version with flow stack support

settings:
  # ... existing settings ...

  # NEW: Flow management settings
  flow_management:
    max_stack_depth: 3          # Maximum nested flows
    abandon_timeout: 3600       # Seconds before paused flow is abandoned
    allow_flow_interruption: true  # Can flows be interrupted?

flows:
  book_flight:
    description: >
      Book a new flight reservation. Collects origin, destination, and
      departure date, then searches for available flights.

    metadata:
      category: "booking"
      priority: "high"
      can_be_paused: true
      can_be_resumed: true

    trigger:
      intents:
        - "I want to book a flight"
        - "Book me a flight"
      keywords:
        - "book"
        - "flight"

    steps:
      - step: collect_origin
        type: collect
        slot: origin
      # ... more steps ...

  check_booking:
    description: >
      Check status of an existing booking. Requires booking reference number.

    metadata:
      category: "information"
      priority: "medium"
      can_be_paused: false  # Quick flow, don't allow interruption
      can_be_resumed: false

    trigger:
      intents:
        - "Check my booking"
        - "What's the status of my booking?"
      keywords:
        - "check"
        - "status"
        - "booking"

    steps:
      - step: request_booking_ref
        type: collect
        slot: booking_ref

      - step: fetch_booking
        type: action
        call: get_booking_details
        map_outputs:
          booking_status: status
          flight_info: flight

  help:
    description: >
      Provide help and information about what the bot can do.
      This is a digression handler that doesn't interrupt other flows.

    metadata:
      category: "utility"
      priority: "low"
      is_digression_handler: true  # Special flag

    trigger:
      intents:
        - "Help"
        - "What can you do?"
      keywords:
        - "help"

    steps:
      - step: show_help
        type: action
        call: generate_help_message
```

---

## Examples

### Example 1: Flow Interruption

```python
# Turn 1: Start booking flow
User: "I want to book a flight"

State:
{
    "flow_stack": [
        {
            "flow_name": "book_flight",
            "flow_state": "active",
            "current_step": "collect_origin",
            "collected_slots": {}
        }
    ]
}

Bot: "Where would you like to fly from?"

# Turn 2: User interrupts to check existing booking
User: "Actually, let me check my existing booking first"

# NLU detects intent change
NLU Result:
{
    "intent": "check_booking",
    "is_digression": false,  # This is an intent change, not digression
    "confidence": 0.95
}

# System pushes new flow, pauses current
State:
{
    "flow_stack": [
        {
            "flow_name": "book_flight",
            "flow_state": "paused",      # PAUSED
            "current_step": "collect_origin",
            "collected_slots": {},
            "paused_at": 1701234567.89,
            "context": "User requested: Actually, let me check my existing booking first"
        },
        {
            "flow_name": "check_booking",
            "flow_state": "active",       # ACTIVE
            "current_step": "request_booking_ref",
            "collected_slots": {}
        }
    ]
}

Bot: "Sure! What's your booking reference number?"

# Turn 3: User provides booking ref
User: "BK-12345"

# ... check_booking flow completes ...

# Turn 4: System offers to resume paused flow
Bot: "Your booking is confirmed for Dec 15. Would you like to continue booking a new flight?"

User: "Yes"

# System pops check_booking, resumes book_flight
State:
{
    "flow_stack": [
        {
            "flow_name": "book_flight",
            "flow_state": "active",       # ACTIVE AGAIN
            "current_step": "collect_origin",
            "collected_slots": {}
        }
    ]
}

Bot: "Great! Where would you like to fly from?"
```

### Example 2: Digression Handling

```python
# Turn 1: Bot asks for origin
Bot: "Where would you like to fly from?"

State:
{
    "conversation_state": "waiting_for_slot",
    "waiting_for_slot": "origin",
    "digression_depth": 0
}

# Turn 2: User asks a question (digression)
User: "What cities do you support?"

# NLU detects digression
Result:
{
    "outcome_type": "question",
    "is_digression": true,
    "digression_type": "question",
    "digression_topic": "supported cities",
    "confidence": 0.92
}

# System handles digression WITHOUT changing flow stack
State:
{
    "conversation_state": "waiting_for_slot",  # UNCHANGED
    "waiting_for_slot": "origin",               # UNCHANGED
    "digression_depth": 1,                      # Incremented
    "last_digression_type": "question",
    "flow_stack": [...] # UNCHANGED
}

Bot: "We support all major cities in the US including New York, Los Angeles, Chicago, and more. Where would you like to fly from?"

# Turn 3: User provides answer to original question
User: "New York"

State:
{
    "conversation_state": "validating_slot",
    "waiting_for_slot": "origin",
    "digression_depth": 0,  # Back to 0
    "slots": {"origin": "New York"}
}
```

### Example 3: Complex Multi-Flow

```python
# Turn 1: Start booking
User: "Book a flight to LA"

flow_stack: [book_flight (active)]

# Turn 2: User interrupts to check existing booking
User: "Wait, let me check my current booking first"

flow_stack: [book_flight (paused), check_booking (active)]

# Turn 3: While checking, user asks a question
User: "What cities do you fly to?"

# Digression - no stack change
digression_depth: 1
Bot answers, re-prompts

# Turn 4: Complete check_booking
User: "BK-12345"
# ... check completes ...

flow_stack: [book_flight (active)]  # check_booking popped

# Turn 5: User wants to modify that booking instead
User: "Actually, I want to modify that booking"

flow_stack: [book_flight (cancelled), modify_booking (active)]
# book_flight cancelled, not resumed

# Turn 6: Complete modification
# ... modify_booking completes ...

flow_stack: []  # Empty, back to idle
```

---

## Summary

This design extends the core architecture with:

1. ✅ **Flow Stack**: Track multiple flows (active + paused)
2. ✅ **Flow States**: active, paused, completed, cancelled, abandoned
3. ✅ **Digression Handling**: Decomposed into focused components (DigressionHandler → KnowledgeBase + HelpGenerator)
4. ✅ **Rich Flow Metadata**: Descriptions and context for better LLM understanding
5. ✅ **Resume Capability**: Return to paused flows intelligently
6. ✅ **Stack Operations**: Simple push/pop helpers in RuntimeLoop (not a separate class)

### Key Benefits

- **Realistic conversations**: Handles how humans actually talk
- **No lost context**: Paused flows can be resumed
- **Better NLU**: Rich descriptions improve intent detection
- **Flexible**: Users can switch tasks, ask questions, and return
- **Traceable**: Full audit trail of flow transitions
- **Clean architecture**: Proper separation of concerns without over-engineering

### Architecture Highlights

- **RuntimeLoop**: Orchestrator with simple flow stack helpers (push/pop)
- **DigressionHandler**: Coordinator that delegates to specialized components
- **KnowledgeBase**: Answers questions using RAG, knowledge base, or documentation
- **HelpGenerator**: Generates contextual help and clarifications
- **No God Objects**: Each component has focused responsibilities

### Next Steps

1. Update DialogueState schema with flow_stack
2. Implement RuntimeLoop with flow stack helper methods
3. Implement DigressionHandler with KnowledgeBase and HelpGenerator
4. Update NLU signatures for digression detection
5. Enhance YAML schema with flow descriptions
6. Implement resume flow logic with disambiguation
7. Add comprehensive tests for complex scenarios

---

**Ground Truth**: See [01-architecture-overview.md](01-architecture-overview.md) for the definitive architecture.

**LangGraph Integration Notes**:
- Use `interrupt()` to pause execution waiting for user input
- Use `Command(resume=)` to continue after user responds
- Flow stack is managed in DialogueState, persisted via LangGraph checkpointing
- Every message passes through understand_node (NLU) FIRST

**Status**: Design proposal ready for review and implementation
**Impact**: Enables realistic, flexible conversations with clean architecture
**Complexity**: Medium (builds on existing architecture with proper decomposition)
