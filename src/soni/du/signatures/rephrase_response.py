"""DSPy signature for response rephrasing."""

import dspy


class RephraserSignature(dspy.Signature):
    """Polish a template response to sound more natural.

    You are a helpful assistant that rephrases template responses to be more
    natural and conversational while preserving ALL factual information.

    CRITICAL RULES:
    1. PRESERVE all numbers, amounts, dates, names exactly as given
    2. Do NOT add information not in the template
    3. Maintain the specified tone consistently
    4. Keep responses concise - don't over-elaborate
    """

    template_response: str = dspy.InputField(desc="Original template response to polish")
    conversation_context: str = dspy.InputField(desc="Recent conversation history for context")
    tone: str = dspy.InputField(desc="Desired tone: friendly, professional, or formal")

    polished_response: str = dspy.OutputField(
        desc="Polished response that preserves all factual information"
    )
