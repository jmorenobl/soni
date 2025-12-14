"""Generate training dataset by simulating conversations from YAML config.

This module walks through flow definitions to generate contextually-aware
training examples at each point in the conversation.
"""

from dataclasses import dataclass, field

import dspy

from soni.core.config import FlowConfig, SoniConfig, StepConfig
from soni.du.models import (
    DialogueContext,
    MessageType,
    NLUOutput,
    SlotAction,
    SlotValue,
)


@dataclass
class SimulatedTurn:
    """A single turn in a simulated conversation."""

    user_message: str
    history: dspy.History
    context: DialogueContext
    expected_output: NLUOutput
    current_datetime: str = "2024-12-11T10:00:00"


@dataclass
class ConversationState:
    """Tracks state during conversation simulation."""

    current_flow: str = "none"
    current_slots: dict[str, str] = field(default_factory=dict)
    messages: list[dict[str, str]] = field(default_factory=list)
    conversation_state: str | None = None


class ConversationSimulator:
    """Simulate conversations from YAML configuration to generate training data.

    Walks through flow definitions and generates contextual training examples
    at each conversation point.
    """

    def __init__(self, config: SoniConfig):
        """Initialize simulator with YAML config.

        Args:
            config: Parsed SoniConfig from YAML file.
        """
        self.config = config
        # Use flow descriptions for semantic matching during NLU
        self._available_flows = {name: flow.description for name, flow in config.flows.items()}
        self._available_actions = list(config.actions.keys())

    def generate_dataset(
        self,
        examples_per_pattern: int = 3,
        include_edge_cases: bool = True,
    ) -> list[dspy.Example]:
        """Generate complete training dataset from YAML.

        Args:
            examples_per_pattern: Number of variations per pattern type.
            include_edge_cases: Whether to include boundary case examples.

        Returns:
            List of dspy.Example for optimization.
        """
        examples: list[dspy.Example] = []

        # Generate examples for each flow
        for flow_name, flow_config in self.config.flows.items():
            turns = self.simulate_flow(flow_name, flow_config)
            for turn in turns:
                examples.append(self._turn_to_example(turn))

        # Generate cross-flow interruption examples
        if include_edge_cases:
            examples.extend(self._generate_interruption_during_flow())
            examples.extend(self._generate_confirmation_variations())
            examples.extend(self._generate_cancellation_examples())
            # Include edge_cases from edge_cases.py for critical boundary examples
            # Oversample these to give them more weight during training
            edge_case_examples = self._get_domain_edge_cases()
            OVERSAMPLE_FACTOR = 5  # Repeat edge cases 5x for better learning
            for _ in range(OVERSAMPLE_FACTOR):
                examples.extend(edge_case_examples)

        return examples

    def _get_domain_edge_cases(self) -> list[dspy.Example]:
        """Get domain-specific edge cases from edge_cases.py.

        Filters edge cases to only include those relevant to the current domain
        (based on flows defined in the YAML config).
        """
        from soni.dataset.edge_cases import get_all_edge_cases

        edge_cases = get_all_edge_cases()
        domain_examples: list[dspy.Example] = []

        # Determine domain from config flows
        flow_names = set(self.config.flows.keys())

        for template in edge_cases:
            # Check if the template's command matches a flow in our config
            if template.expected_output.command in flow_names:
                # Convert to dspy.Example with correct available_flows
                example = dspy.Example(
                    user_message=template.user_message,
                    history=template.conversation_context.history,
                    context=DialogueContext(
                        current_flow=template.conversation_context.current_flow,
                        current_slots=dict(template.conversation_context.current_slots),
                        expected_slots=list(template.conversation_context.expected_slots),
                        available_flows=self._available_flows,  # Use our flow descriptions!
                        available_actions=self._available_actions,
                        conversation_state=template.conversation_context.conversation_state,
                    ),
                    result=template.expected_output,
                    current_datetime=template.current_datetime,
                ).with_inputs("user_message", "history", "context", "current_datetime")
                domain_examples.append(example)

        return domain_examples

    def simulate_flow(
        self,
        flow_name: str,
        flow_config: FlowConfig,
    ) -> list[SimulatedTurn]:
        """Simulate a complete flow and generate training examples.

        Args:
            flow_name: Name of the flow.
            flow_config: Flow configuration.

        Returns:
            List of simulated conversation turns.
        """
        turns: list[SimulatedTurn] = []
        state = ConversationState()

        # 1. Generate INTERRUPTION examples from trigger intents
        if flow_config.trigger and flow_config.trigger.intents:
            for intent in flow_config.trigger.intents:
                turns.append(
                    self._create_interruption_turn(
                        user_message=intent,
                        target_flow=flow_name,
                        current_state=state,
                    )
                )

        # 2. Walk through steps and generate contextual examples
        state.current_flow = flow_name
        steps = flow_config.steps_or_process

        for step in steps:
            step_turns = self._simulate_step(step, state, flow_name)
            turns.extend(step_turns)

        return turns

    def _simulate_step(
        self,
        step: StepConfig,
        state: ConversationState,
        flow_name: str,
    ) -> list[SimulatedTurn]:
        """Generate examples for a single step.

        Args:
            step: Step configuration.
            state: Current conversation state.
            flow_name: Current flow name.

        Returns:
            List of turns for this step.
        """
        turns: list[SimulatedTurn] = []

        if step.type == "collect" and step.slot:
            turns.extend(self._simulate_collect_step(step, state, flow_name))
        elif step.type == "confirm":
            turns.extend(self._simulate_confirm_step(step, state, flow_name))
        elif step.type == "action":
            # Actions don't require user input, skip
            pass

        return turns

    def _simulate_collect_step(
        self,
        step: StepConfig,
        state: ConversationState,
        flow_name: str,
    ) -> list[SimulatedTurn]:
        """Generate examples for a collect step.

        Args:
            step: Step configuration.
            state: Current conversation state.
            flow_name: Current flow name.

        Returns:
            List of SLOT_VALUE and CORRECTION turns.
        """
        turns: list[SimulatedTurn] = []
        slot_name = step.slot
        if not slot_name:
            return turns

        # Get slot config for examples
        slot_config = self.config.slots.get(slot_name)
        prompt = slot_config.prompt if slot_config else (step.slot or slot_name)

        # Add bot prompt to history
        state.messages.append({"role": "assistant", "content": prompt})

        # Generate example slot values based on slot name
        example_values = self._get_example_values_for_slot(slot_name)

        for value in example_values[:2]:  # Take first 2 values
            # SLOT_VALUE example
            turns.append(
                self._create_slot_value_turn(
                    user_message=value,
                    slot_name=slot_name,
                    slot_value=value,
                    state=state,
                    flow_name=flow_name,
                )
            )

        # CORRECTION example (if slot already filled)
        if state.current_slots:
            filled_slot = list(state.current_slots.keys())[0]
            old_value = state.current_slots[filled_slot]
            new_value = f"not {old_value}"
            turns.append(
                self._create_correction_turn(
                    user_message=f"Actually, {new_value}",
                    slot_name=filled_slot,
                    new_value=new_value,
                    old_value=old_value,
                    state=state,
                    flow_name=flow_name,
                )
            )

        # Update state
        if example_values:
            state.current_slots[slot_name] = example_values[0]
            state.messages.append({"role": "user", "content": example_values[0]})

        return turns

    def _simulate_confirm_step(
        self,
        step: StepConfig,
        state: ConversationState,
        flow_name: str,
    ) -> list[SimulatedTurn]:
        """Generate examples for a confirm step.

        Args:
            step: Step configuration.
            state: Current conversation state.
            flow_name: Current flow name.

        Returns:
            List of CONFIRMATION turns (yes, no, unclear).
        """
        turns: list[SimulatedTurn] = []

        # Add confirmation prompt to history
        message = step.message or "Please confirm"
        state.messages.append({"role": "assistant", "content": message})
        state.conversation_state = "confirming"

        # Positive confirmations
        for phrase in ["Yes", "Yes, that's correct", "Confirm"]:
            turns.append(
                self._create_confirmation_turn(
                    user_message=phrase,
                    confirmation_value=True,
                    state=state,
                    flow_name=flow_name,
                )
            )

        # Negative confirmations
        for phrase in ["No", "No, that's wrong", "Cancel"]:
            turns.append(
                self._create_confirmation_turn(
                    user_message=phrase,
                    confirmation_value=False,
                    state=state,
                    flow_name=flow_name,
                )
            )

        # Ambiguous confirmations
        for phrase in ["Maybe", "I'm not sure", "Hmm"]:
            turns.append(
                self._create_confirmation_turn(
                    user_message=phrase,
                    confirmation_value=None,
                    state=state,
                    flow_name=flow_name,
                )
            )

        return turns

    # =========================================================================
    # Turn creation helpers
    # =========================================================================

    def _create_interruption_turn(
        self,
        user_message: str,
        target_flow: str,
        current_state: ConversationState,
    ) -> SimulatedTurn:
        """Create an INTERRUPTION turn."""
        context = self._build_context(current_state)

        # Try to extract slots from the message
        slots = self._extract_slots_from_intent(user_message, target_flow)

        return SimulatedTurn(
            user_message=user_message,
            history=dspy.History(messages=list(current_state.messages)),
            context=context,
            expected_output=NLUOutput(
                message_type=MessageType.INTERRUPTION,
                command=target_flow,
                slots=slots,
                confidence=0.90,
            ),
        )

    def _create_slot_value_turn(
        self,
        user_message: str,
        slot_name: str,
        slot_value: str,
        state: ConversationState,
        flow_name: str,
    ) -> SimulatedTurn:
        """Create a SLOT_VALUE turn."""
        context = self._build_context(state)
        context.expected_slots = [slot_name]

        return SimulatedTurn(
            user_message=user_message,
            history=dspy.History(messages=list(state.messages)),
            context=context,
            expected_output=NLUOutput(
                message_type=MessageType.SLOT_VALUE,
                command=flow_name,
                slots=[
                    SlotValue(
                        name=slot_name,
                        value=slot_value,
                        confidence=0.95,
                        action=SlotAction.PROVIDE,
                    )
                ],
                confidence=0.95,
            ),
        )

    def _create_correction_turn(
        self,
        user_message: str,
        slot_name: str,
        new_value: str,
        old_value: str,
        state: ConversationState,
        flow_name: str,
    ) -> SimulatedTurn:
        """Create a CORRECTION turn."""
        context = self._build_context(state)

        return SimulatedTurn(
            user_message=user_message,
            history=dspy.History(messages=list(state.messages)),
            context=context,
            expected_output=NLUOutput(
                message_type=MessageType.CORRECTION,
                command=flow_name,
                slots=[
                    SlotValue(
                        name=slot_name,
                        value=new_value,
                        confidence=0.90,
                        action=SlotAction.CORRECT,
                        previous_value=old_value,
                    )
                ],
                confidence=0.90,
            ),
        )

    def _create_confirmation_turn(
        self,
        user_message: str,
        confirmation_value: bool | None,
        state: ConversationState,
        flow_name: str,
    ) -> SimulatedTurn:
        """Create a CONFIRMATION turn."""
        context = self._build_context(state)
        context.conversation_state = "confirming"

        return SimulatedTurn(
            user_message=user_message,
            history=dspy.History(messages=list(state.messages)),
            context=context,
            expected_output=NLUOutput(
                message_type=MessageType.CONFIRMATION,
                command=flow_name,
                slots=[],
                confidence=0.90 if confirmation_value is not None else 0.60,
                confirmation_value=confirmation_value,
            ),
        )

    # =========================================================================
    # Edge case generators
    # =========================================================================

    def _generate_interruption_during_flow(self) -> list[dspy.Example]:
        """Generate examples of interrupting one flow with another.

        These examples teach the NLU to recognize when a user wants to switch
        to a different flow while in the middle of an active flow (e.g., asking
        about balance while in the middle of a transfer).
        """
        examples: list[dspy.Example] = []
        flow_names = list(self.config.flows.keys())

        for source_flow in flow_names:
            source_config = self.config.flows[source_flow]
            if not source_config.steps_or_process:
                continue

            for target_flow in flow_names:
                if source_flow == target_flow:
                    continue

                target_config = self.config.flows[target_flow]
                if not target_config.trigger or not target_config.trigger.intents:
                    continue

                # Create realistic state: in middle of collecting a slot
                state = ConversationState(
                    current_flow=source_flow,
                    current_slots={"some_slot": "some_value"},
                    messages=[
                        {"role": "user", "content": f"I want to {source_flow}"},
                        {"role": "assistant", "content": "Please provide the next value"},
                    ],
                    conversation_state="waiting_for_slot",  # Critical for realistic context
                )

                # Generate examples for MULTIPLE intents from target flow (not just first)
                for intent in target_config.trigger.intents[:3]:  # Up to 3 intents
                    turn = self._create_interruption_turn(
                        user_message=intent,
                        target_flow=target_flow,
                        current_state=state,
                    )
                    examples.append(self._turn_to_example(turn))

        return examples

    def _generate_confirmation_variations(self) -> list[dspy.Example]:
        """Generate additional confirmation edge cases."""
        examples: list[dspy.Example] = []

        # Find a flow with confirm step
        for flow_name, flow_config in self.config.flows.items():
            steps = flow_config.steps_or_process
            for step in steps:
                if step.type == "confirm":
                    state = ConversationState(
                        current_flow=flow_name,
                        current_slots={"amount": "100", "recipient": "mom"},
                        messages=[
                            {"role": "assistant", "content": "Please confirm"},
                        ],
                        conversation_state="confirming",
                    )

                    # Add edge cases
                    edge_phrases = [
                        ("I guess so", None),
                        ("Let me think", None),
                        ("Well...", None),
                        ("Go ahead", True),
                        ("That's wrong", False),
                    ]

                    for phrase, conf_val in edge_phrases:
                        turn = self._create_confirmation_turn(
                            user_message=phrase,
                            confirmation_value=conf_val,
                            state=state,
                            flow_name=flow_name,
                        )
                        examples.append(self._turn_to_example(turn))

                    return examples  # Only need one flow

        return examples

    def _generate_cancellation_examples(self) -> list[dspy.Example]:
        """Generate CANCELLATION examples for each flow."""
        examples: list[dspy.Example] = []

        for flow_name in list(self.config.flows.keys())[:3]:  # Limit
            state = ConversationState(
                current_flow=flow_name,
                current_slots={"some_slot": "some_value"},
                messages=[
                    {"role": "user", "content": f"Starting {flow_name}"},
                ],
            )

            context = self._build_context(state)

            for phrase in ["Cancel", "Never mind", "Forget it"]:
                turn = SimulatedTurn(
                    user_message=phrase,
                    history=dspy.History(messages=list(state.messages)),
                    context=context,
                    expected_output=NLUOutput(
                        message_type=MessageType.CANCELLATION,
                        command=flow_name,
                        slots=[],
                        confidence=0.90,
                    ),
                )
                examples.append(self._turn_to_example(turn))

        return examples

    # =========================================================================
    # Utility methods
    # =========================================================================

    def _build_context(self, state: ConversationState) -> DialogueContext:
        """Build DialogueContext from current state."""
        # Get expected slots from config
        expected_slots = []
        slot_prompts = {}
        for slot_name, slot_config in self.config.slots.items():
            expected_slots.append(slot_name)
            slot_prompts[slot_name] = slot_config.prompt

        return DialogueContext(
            current_slots=dict(state.current_slots),
            available_flows=dict(self._available_flows),
            available_actions=list(self._available_actions),
            current_flow=state.current_flow,
            expected_slots=expected_slots,
            conversation_state=state.conversation_state,
        )

    def _turn_to_example(self, turn: SimulatedTurn) -> dspy.Example:
        """Convert SimulatedTurn to dspy.Example."""
        return dspy.Example(
            user_message=turn.user_message,
            history=turn.history,
            context=turn.context,
            current_datetime=turn.current_datetime,
            result=turn.expected_output,
        ).with_inputs("user_message", "history", "context", "current_datetime")

    def _get_example_values_for_slot(self, slot_name: str) -> list[str]:
        """Get example values for a slot based on its name."""
        # Common patterns
        patterns: dict[str, list[str]] = {
            "amount": ["100", "50", "1000", "25"],
            "currency": ["USD", "EUR", "GBP"],
            "recipient": ["mom", "dad", "John", "Alice"],
            "account_type": ["checking", "savings"],
            "source_account": ["checking", "savings"],
            "card_type": ["credit", "debit"],
            "card_last_4": ["1234", "5678", "9999"],
        }

        # Check for partial matches
        slot_lower = slot_name.lower()
        for pattern, values in patterns.items():
            if pattern in slot_lower:
                return values

        # Default
        return ["value1", "value2", "value3"]

    def _extract_slots_from_intent(
        self,
        user_message: str,
        flow_name: str,
    ) -> list[SlotValue]:
        """Try to extract slot values from an intent phrase.

        This is a simple heuristic - looks for patterns like "100 to mom".
        """
        slots: list[SlotValue] = []

        # Simple numeric extraction
        import re

        numbers = re.findall(r"\b\d+\b", user_message)
        if numbers and "amount" in str(self.config.slots):
            slots.append(
                SlotValue(
                    name="amount",
                    value=numbers[0],
                    confidence=0.85,
                    action=SlotAction.PROVIDE,
                )
            )

        return slots
