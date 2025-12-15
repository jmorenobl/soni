import asyncio
import logging
import os
import sys
from pprint import pprint

import dspy

# Ensure src is in python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../src")))

# Import handlers
import examples.banking.handlers
from soni.core.config import SoniConfig
from soni.runtime.runtime import RuntimeLoop


async def debug_followup():
    print("=== Debugging Follow-up Query ===")

    config_path = "examples/banking/soni.yaml"
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        print("Error: OPENAI_API_KEY required")
        return

    # Log setup
    logging.basicConfig(level=logging.INFO)
    logging.getLogger("httpx").setLevel(logging.WARNING)

    # Configure DSPy
    try:
        soni_config = SoniConfig.from_yaml(config_path)
        nlu_config = soni_config.settings.models.nlu
        lm = dspy.LM(f"{nlu_config.provider}/{nlu_config.model}", api_key=api_key)
        dspy.configure(lm=lm)
    except Exception as e:
        print(f"Error config: {e}")
        return

    # Runtime
    runtime = RuntimeLoop(config_path)
    await runtime._ensure_graph_initialized()

    user_id = "debug-followup-1"

    try:
        # Sequence mirroring user report
        turns = [
            "Hi",
            "I want to transfer money to my mom",
            "How much do I have?",
            "debit account",
            "and what about my credit account?",
        ]

        for i, msg in enumerate(turns):
            print(f"\n--- Turn {i}: '{msg}' ---")
            response = await runtime.process_message(msg, user_id)
            print(f"Assistant: {response}")

            # Additional analysis for the trouble spots
            if i >= 3:
                state = await runtime.graph.aget_state({"configurable": {"thread_id": user_id}})
                print(f"[State Analysis Turn {i}]")
                print(f"Flow Stack: {[f['flow_name'] for f in state.values.get('flow_stack', [])]}")
                print(f"NLU Result: {state.values.get('nlu_result')}")
                print(f"Action Result: {state.values.get('action_result')}")

    finally:
        await runtime.cleanup()


if __name__ == "__main__":
    asyncio.run(debug_followup())
