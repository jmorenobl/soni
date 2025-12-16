# Soni vs Rasa CALM (2025): Auto-Resume Analysis

## 1. Interaction Analysis

### The User Scenario
The user experienced the following interaction flows:
1.  **Flow A (Transfer Funds)** starts.
    -   Collect `recipient` -> Done.
    -   Collect `amount` -> User interrupts: "How much do I have?".
2.  **Flow B (Check Balance)** starts (Interruption).
    -   Collect `account_type` -> Done ("savings").
    -   Action `get_balance` -> Done ("12000").
    -   Say `result` -> Done ("Your savings balance is...").
3.  **Flow B Ends**.
    -   **Current Behavior**: Soni stops. The session waits for user input.
    -   **Expected Behavior (Rasa CALM style)**: Soni should automatically "pop" Flow B and **resume Flow A**. It should immediately ask: *"Got it. How much do you want to transfer?"* (re-evaluating the last pending step of Flow A).

### The NLU Gap
User input: "1000€"
-   **Current**: Soni interpreted this as `amount=1000` (likely) but missed `currency=EUR`. It then aks "In which currency?".
-   **Expected**: Entity extraction should identify both value and unit from the symbol.

## 2. Rasa CALM Architecture (Reference)

Rasa CALM (Conversational AI with Language Models) relies on a native **Dialogue Stack**.
-   **Business Logic**: Defined as strict flows.
-   **Dialogue Manager**:
    1.  Maintains a stack of active flows.
    2.  When a flow is triggered, it is pushed to the stack.
    3.  When a flow completes, it is **popped** from the stack.
    4.  **Auto-Resume**: Immediately after a pop, the manager checks the **new top of the stack**. It re-evaluates the "next step" logic for that flow.
        -   If the flow was waiting for a slot, it re-issues the prompt.
        -   This creates a seamless "return to topic" experience without user stored input.

## 3. Soni Current Architecture (The Gap)

Soni implements a similar stack (`flow_stack` in `DialogueState`), but the **Lifecycle Management** is incomplete in the Orchestrator.

### Current Logic
1.  `RuntimeLoop` triggers `orchestrator` graph.
2.  `orchestrator` runs until `END`.
3.  Inside a flow (Subgraph), `__end_flow__` (the implicit end state) returns `END` to the parent graph.
4.  The parent graph edges route flow completion to `respond_node` -> `END`.
5.  **Critically**: The `flow_stack` is **NOT popped**. The finished flow remains "active" on top of the stack, but valid steps are exhausted.
6.  Interpretation stops. `FlowManager` does not have a "Resume" hook.

## 4. Proposed Solution: Auto-Resume Loop

To match Rasa CALM's fluid conversational capability, we need to implement an **Orchestration Loop** for stack management.

### Implementation Plan

#### Phase 1: Stack Cleanup (The "Pop")
We need a `cleanup_flow` node in the Orchestrator or logic within `manage_flow_lifecycle`.
-   When a subgraph returns (finishes):
    -   Call `FlowManager.pop_flow()`.
    -   This removes the completed specific flow (e.g., `check_balance`).

#### Phase 2: Resume Logic (The "Loop")
After popping, we check `len(state["flow_stack"])`.
-   **Case Empty**: Route to `respond_node` (Wait for user).
-   **Case Non-Empty (Auto-Resume)**:
    -   Peek at new top flow (e.g., `transfer_funds`).
    -   Update `active_flow` context.
    -   **Route back to `execute_node`** (or specific flow entry).
    -   This re-enters the `transfer_funds` flow.
    -   The flow logic sees it is at `collect_amount` (still empty).
    -   It re-generates the prompt: "Got it. How much do you want to transfer?".

### Graph Changes
**Current**:
`START` -> `understand` -> `execute` -> `flow_X` -> `respond` -> `END`

**Proposed**:
`START` -> `understand` -> `execute` -> `flow_X` -> **`resume_logic`**
-   **`resume_logic`**:
    -   `pop_flow()`
    -   If stack empty -> `respond` -> `END`
    -   If stack > 0 -> `execute` (Loop back!)

## 5. NLU Enhancement (Currency handling)
The `1000€` issue is an NLU extraction problem.
-   **Solution**: Update `src/soni/du/signatures.py` or `models.py` (SlotValue definitions) to explicitly mention currency symbol handling in the prompt instructions or few-shot examples for the LLM.
-   Ensure `amount` and `currency` slots can be filled simultaneously from a single utterance.
