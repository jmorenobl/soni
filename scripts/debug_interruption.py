import asyncio
import logging
import os
import sys
from pprint import pprint

import dspy

# Ensure src is in python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../src")))

# Import handlers to register them
from soni.core.config import SoniConfig
from soni.core.constants import ConversationState
from soni.runtime.runtime import RuntimeLoop

import examples.banking.handlers


async def debug_interruption():
    print("=== Debugging Interruption Flow ===")

    config_path = "examples/banking/soni.yaml"
    if not os.path.exists(config_path):
        print(f"Error: Config file not found at {config_path}")
        return

    # Check for API Key
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        print("Error: OPENAI_API_KEY not found in environment.")
        return

    # Load config to get model settings
    try:
        soni_config = SoniConfig.from_yaml(config_path)
        nlu_config = soni_config.settings.models.nlu
        lm = dspy.LM(
            f"{nlu_config.provider}/{nlu_config.model}",
            api_key=api_key,
            temperature=nlu_config.temperature,
        )
        dspy.configure(lm=lm)
        print(f"DSPy configured with {nlu_config.provider}/{nlu_config.model}")
    except Exception as e:
        print(f"Error configuring DSPy: {e}")
        return

    # Setup Logging
    logging.basicConfig(level=logging.INFO)
    # Silence some noisy loggers
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)
    logging.getLogger("openai").setLevel(logging.WARNING)
    logging.getLogger("sqlite3").setLevel(logging.WARNING)
    logging.getLogger("aiosqlite").setLevel(logging.WARNING)

    # Initialize Runtime (Synchronous)
    print(f"Initializing Runtime with {config_path}...")
    try:
        runtime = RuntimeLoop(config_path)
    except Exception as e:
        print(f"Error initializing RuntimeLoop: {e}")
        return

    # Ensure graph is initialized
    await runtime._ensure_graph_initialized()

    user_id = "debug-user-1"

    try:
        # Turn 0: Greeting (Match CLI)
        print("\n--- Turn 0: 'Hi' ---")
        response0 = await runtime.process_message("Hi", user_id)
        print(f"Assistant: {response0}")

        # Turn 1: Start Transfer
        print("\n--- Turn 1: 'I want to transfer money to my mom' ---")
        response1 = await runtime.process_message("I want to transfer money to my mom", user_id)
        print(f"Assistant: {response1}")

        # Inspect State 1
        state1 = await runtime.graph.aget_state({"configurable": {"thread_id": user_id}})
        print("\n[State 1 Analysis]")
        print(f"Flow Stack: {[f['flow_name'] for f in state1.values.get('flow_stack', [])]}")
        print(f"Conv State: {state1.values.get('conversation_state')}")
        print(f"Waiting For: {state1.values.get('waiting_for_slot')}")

        # Turn 2: Interruption
        print("\n--- Turn 2: 'How mucho do I have?' ---")
        response2 = await runtime.process_message("How mucho do I have?", user_id)
        print(f"Assistant: {response2}")

        # Inspect State 2
        state2 = await runtime.graph.aget_state({"configurable": {"thread_id": user_id}})
        nlu_result = state2.values.get("nlu_result", {})

        print("\n[State 2 Analysis]")
        print("NLU Result:")
        pprint(nlu_result)

        print(f"Flow Stack: {[f['flow_name'] for f in state2.values.get('flow_stack', [])]}")
        print(f"Conv State: {state2.values.get('conversation_state')}")

        # Verification
        flow_stack = state2.values.get("flow_stack", [])
        top_flow = flow_stack[-1]["flow_name"] if flow_stack else "None"

        if top_flow == "check_balance":
            print("\n✅ SUCCESS: Successfully switched to 'check_balance' flow.")
        else:
            print(f"\n❌ FAILURE: Expected top flow 'check_balance', got '{top_flow}'.")
            print("This confirms the issue reported by the user.")

    finally:
        await runtime.cleanup()


if __name__ == "__main__":
    asyncio.run(debug_interruption())
