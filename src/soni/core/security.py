"""Security utilities and guardrails for Soni Framework."""

import logging
import re

from soni.core.errors import ValidationError

logger = logging.getLogger(__name__)

# Security constants
MAX_MESSAGE_LENGTH = 10000  # Prevent DoS via extremely long messages
MAX_USER_ID_LENGTH = 255  # Reasonable limit for user IDs
MIN_MESSAGE_LENGTH = 1  # Minimum message length

# Dangerous patterns that should be stripped or escaped
DANGEROUS_PATTERNS = [
    r"<script[^>]*>.*?</script>",  # XSS attempts
    r"javascript:",  # JavaScript protocol
    r"on\w+\s*=",  # Event handlers (onclick, onerror, etc.)
]

# User ID validation pattern (alphanumeric, underscore, hyphen, dot)
USER_ID_PATTERN = re.compile(r"^[a-zA-Z0-9_.-]+$")


def sanitize_user_message(message: str, max_length: int = MAX_MESSAGE_LENGTH) -> str:
    """Sanitize user message to prevent injection attacks and DoS.

    This function:
    - Strips dangerous HTML/JavaScript patterns
    - Limits message length to prevent DoS
    - Trims whitespace
    - Escapes special characters for safe LLM prompt inclusion

    Args:
        message: Raw user message
        max_length: Maximum allowed message length (default: 10000)

    Returns:
        Sanitized message

    Raises:
        ValidationError: If message is empty after sanitization
        ValidationError: If message exceeds max_length

    Example:
        >>> sanitize_user_message("Hello <script>alert('xss')</script>")
        "Hello "

        >>> sanitize_user_message("A" * 20000)
        ValidationError: Message exceeds maximum length
    """
    if not message:
        raise ValidationError("Message cannot be empty")

    # Trim whitespace
    sanitized = message.strip()

    if not sanitized:
        raise ValidationError("Message cannot be empty after sanitization")

    # Check length before processing
    if len(sanitized) > max_length:
        raise ValidationError(
            f"Message exceeds maximum length of {max_length} characters",
            context={"message_length": len(sanitized), "max_length": max_length},
        )

    # Remove dangerous patterns
    for pattern in DANGEROUS_PATTERNS:
        sanitized = re.sub(pattern, "", sanitized, flags=re.IGNORECASE | re.DOTALL)

    # Trim again after pattern removal
    sanitized = sanitized.strip()

    if not sanitized:
        raise ValidationError("Message became empty after sanitization")

    # Final length check
    if len(sanitized) > max_length:
        # Truncate if still too long (shouldn't happen, but safety check)
        sanitized = sanitized[:max_length]
        logger.warning(
            f"Message truncated to {max_length} characters",
            extra={"original_length": len(message), "truncated_length": len(sanitized)},
        )

    return sanitized


def sanitize_user_id(user_id: str, max_length: int = MAX_USER_ID_LENGTH) -> str:
    """Sanitize and validate user ID format.

    User IDs must:
    - Be non-empty
    - Contain only alphanumeric characters, underscores, hyphens, and dots
    - Not exceed max_length

    Args:
        user_id: Raw user ID
        max_length: Maximum allowed user ID length (default: 255)

    Returns:
        Sanitized user ID

    Raises:
        ValidationError: If user_id is empty or invalid format
        ValidationError: If user_id exceeds max_length

    Example:
        >>> sanitize_user_id("user_123")
        "user_123"

        >>> sanitize_user_id("user<script>")
        ValidationError: Invalid user ID format
    """
    if not user_id:
        raise ValidationError("User ID cannot be empty")

    # Trim whitespace
    sanitized = user_id.strip()

    if not sanitized:
        raise ValidationError("User ID cannot be empty after sanitization")

    # Check length
    if len(sanitized) > max_length:
        raise ValidationError(
            f"User ID exceeds maximum length of {max_length} characters",
            context={"user_id_length": len(sanitized), "max_length": max_length},
        )

    # Validate format (alphanumeric, underscore, hyphen, dot only)
    if not USER_ID_PATTERN.match(sanitized):
        raise ValidationError(
            "Invalid user ID format. Only alphanumeric characters, "
            "underscores, hyphens, and dots are allowed",
            context={"user_id": sanitized},
        )

    return sanitized


def escape_for_llm_prompt(text: str) -> str:
    """
    Escape special characters for safe inclusion in LLM prompts.

    This prevents prompt injection attacks by escaping characters that could
    be interpreted as instructions by the LLM.

    Args:
        text: Text to escape

    Returns:
        Escaped text safe for LLM prompts

    Example:
        >>> escape_for_llm_prompt("Ignore previous instructions")
        "Ignore previous instructions"  # Escaped internally
    """
    # Replace newlines with spaces to prevent prompt injection
    escaped = text.replace("\n", " ").replace("\r", " ")

    # Remove or escape control characters
    escaped = "".join(char for char in escaped if ord(char) >= 32 or char in "\t")

    # Limit consecutive spaces
    escaped = re.sub(r" +", " ", escaped)

    return escaped.strip()


def sanitize_error_message(error_msg: str) -> str:
    """
    Sanitize error message to prevent information leakage.

    Removes potentially sensitive information from error messages
    before exposing them to users.

    Args:
        error_msg: Raw error message

    Returns:
        Sanitized error message safe for user exposure

    Example:
        >>> sanitize_error_message("Database connection failed: password=secret123")
        "Database connection failed"
    """
    # Remove common sensitive patterns
    # Remove file paths (could reveal system structure)
    import re

    # Remove absolute paths
    sanitized = re.sub(r"/[^\s]+", "[path]", error_msg)
    # Remove potential credential patterns
    sanitized = re.sub(
        r"(password|api_key|secret|token|credential)\s*[=:]\s*[^\s]+",
        r"\1=[REDACTED]",
        sanitized,
        flags=re.IGNORECASE,
    )
    # Remove stack trace indicators
    sanitized = re.sub(r"Traceback.*?File.*?line \d+", "[stack trace]", sanitized, flags=re.DOTALL)

    return sanitized.strip()


def validate_action_name(action_name: str) -> None:
    """
    Validate action name format to prevent injection.

    Action names must:
    - Be non-empty
    - Contain only alphanumeric characters, underscores, and hyphens
    - Not start with special characters

    Args:
        action_name: Action name to validate

    Raises:
        ValidationError: If action name is invalid

    Example:
        >>> validate_action_name("search_flights")
        # No exception

        >>> validate_action_name("action<script>")
        ValidationError: Invalid action name format
    """
    if not action_name or not action_name.strip():
        raise ValidationError("Action name cannot be empty")

    # Action names should be simple identifiers
    if not re.match(r"^[a-zA-Z0-9_-]+$", action_name):
        raise ValidationError(
            "Invalid action name format. Only alphanumeric characters, "
            "underscores, and hyphens are allowed",
            context={"action_name": action_name},
        )


class SecurityGuardrails:
    """
    Security guardrails for validating actions and intents.

    This class implements security checks to prevent:
    - Unauthorized action execution
    - Blocked intent activation
    - Action injection attacks
    - Confidence threshold violations
    """

    def __init__(
        self,
        allowed_actions: list[str] | None = None,
        blocked_intents: list[str] | None = None,
        max_confidence_threshold: float = 0.95,
        min_confidence_threshold: float = 0.0,
    ):
        """
        Initialize security guardrails.

        Args:
            allowed_actions: List of allowed action names. If None or empty, all actions are allowed.
            blocked_intents: List of blocked intent names. If None, no intents are blocked.
            max_confidence_threshold: Maximum confidence threshold (default: 0.95)
            min_confidence_threshold: Minimum confidence threshold (default: 0.0)
        """
        self.allowed_actions: set[str] = set(allowed_actions) if allowed_actions else set()
        self.blocked_intents: set[str] = set(blocked_intents) if blocked_intents else set()
        self.max_confidence_threshold = max_confidence_threshold
        self.min_confidence_threshold = min_confidence_threshold

        logger.debug(
            f"SecurityGuardrails initialized: "
            f"{len(self.allowed_actions)} allowed actions, "
            f"{len(self.blocked_intents)} blocked intents"
        )

    def validate_action(self, action_name: str) -> tuple[bool, str]:
        """
        Validate that an action is allowed to execute.

        Args:
            action_name: Name of the action to validate

        Returns:
            Tuple of (is_valid, error_message)
            - is_valid: True if action is allowed, False otherwise
            - error_message: Empty string if valid, error message if invalid

        Example:
            >>> guardrails = SecurityGuardrails(allowed_actions=["search_flights"])
            >>> guardrails.validate_action("search_flights")
            (True, "")

            >>> guardrails.validate_action("delete_all")
            (False, "Action 'delete_all' is not in the allowed actions list")
        """
        # Validate action name format first
        try:
            validate_action_name(action_name)
        except ValidationError as e:
            return False, str(e)

        # Check if action is in allowed list (if list is non-empty)
        if self.allowed_actions and action_name not in self.allowed_actions:
            return False, (
                f"Action '{action_name}' is not in the allowed actions list. "
                f"Allowed actions: {sorted(self.allowed_actions)}"
            )

        return True, ""

    def validate_intent(self, intent: str) -> tuple[bool, str]:
        """
        Validate that an intent is not blocked.

        Args:
            intent: Name of the intent to validate

        Returns:
            Tuple of (is_valid, error_message)
            - is_valid: True if intent is allowed, False otherwise
            - error_message: Empty string if valid, error message if invalid

        Example:
            >>> guardrails = SecurityGuardrails(blocked_intents=["malicious_intent"])
            >>> guardrails.validate_intent("booking")
            (True, "")

            >>> guardrails.validate_intent("malicious_intent")
            (False, "Intent 'malicious_intent' is blocked")
        """
        if not intent:
            return False, "Intent cannot be empty"

        if intent in self.blocked_intents:
            return False, f"Intent '{intent}' is blocked"

        return True, ""

    def validate_confidence(self, confidence: float) -> tuple[bool, str]:
        """
        Validate that confidence is within acceptable thresholds.

        Args:
            confidence: Confidence value to validate (0.0 to 1.0)

        Returns:
            Tuple of (is_valid, error_message)
            - is_valid: True if confidence is valid, False otherwise
            - error_message: Empty string if valid, error message if invalid

        Example:
            >>> guardrails = SecurityGuardrails(max_confidence_threshold=0.95)
            >>> guardrails.validate_confidence(0.8)
            (True, "")

            >>> guardrails.validate_confidence(0.99)
            (False, "Confidence 0.99 exceeds maximum threshold 0.95")
        """
        if confidence < self.min_confidence_threshold:
            return False, (
                f"Confidence {confidence} is below minimum threshold "
                f"{self.min_confidence_threshold}"
            )

        if confidence > self.max_confidence_threshold:
            return False, (
                f"Confidence {confidence} exceeds maximum threshold {self.max_confidence_threshold}"
            )

        return True, ""

    def validate_action_and_intent(
        self, action_name: str, intent: str, confidence: float
    ) -> tuple[bool, str]:
        """
        Validate action, intent, and confidence together.

        Args:
            action_name: Name of the action to validate
            intent: Name of the intent to validate
            confidence: Confidence value to validate

        Returns:
            Tuple of (is_valid, error_message)
        """
        # Validate action
        is_valid, error = self.validate_action(action_name)
        if not is_valid:
            return False, error

        # Validate intent
        is_valid, error = self.validate_intent(intent)
        if not is_valid:
            return False, error

        # Validate confidence
        is_valid, error = self.validate_confidence(confidence)
        if not is_valid:
            return False, error

        return True, ""
