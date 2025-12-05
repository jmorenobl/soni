"""Slot normalization layer for Soni Framework."""

import logging
from datetime import datetime, timedelta
from typing import Any

import dspy
from cachetools import TTLCache

from soni.core.config import SoniConfig
from soni.core.interfaces import INormalizer
from soni.utils.hashing import generate_cache_key

logger = logging.getLogger(__name__)


class SlotNormalizer(INormalizer):
    """Normalizes slot values before validation.

    This class implements the INormalizer protocol and provides:
    - Basic normalization strategies (trim, lowercase)
    - LLM-based correction for complex cases
    - Caching to avoid repeated normalizations
    """

    def __init__(
        self,
        config: SoniConfig | dict[str, Any] | None = None,
        cache_size: int = 1000,
        cache_ttl: int = 3600,
    ) -> None:
        """Initialize SlotNormalizer.

        Args:
            config: SoniConfig or configuration dictionary
            cache_size: Maximum number of cached normalizations
            cache_ttl: Time-to-live for cache entries in seconds
        """
        if isinstance(config, SoniConfig):
            # Extract config dict from SoniConfig
            self.config = config.model_dump()
        else:
            self.config = config or {}

        self.cache: TTLCache[str, Any] = TTLCache(maxsize=cache_size, ttl=cache_ttl)
        self._llm: dspy.LM | None = None
        self.slots_config: dict[str, Any] = self.config.get("slots", {})

    @property
    def llm(self) -> dspy.LM:
        """Lazy-load LLM for corrections."""
        if self._llm is None:
            model = (
                self.config.get("settings", {})
                .get("models", {})
                .get("nlu", {})
                .get("model", "gpt-4o-mini")
            )
            provider = (
                self.config.get("settings", {})
                .get("models", {})
                .get("nlu", {})
                .get("provider", "openai")
            )
            self._llm = dspy.LM(f"{provider}/{model}", temperature=0)
        return self._llm

    async def normalize(
        self,
        value: Any,
        entity_config: dict[str, Any],
    ) -> Any:
        """Normalize a slot/entity value.

        Args:
            value: Raw value to normalize
            entity_config: Configuration for the entity type

        Returns:
            Normalized value
        """
        # Check cache first
        cache_key = self._get_cache_key(value, entity_config)
        if cache_key in self.cache:
            logger.debug(f"Cache hit for normalization: {cache_key}")
            return self.cache[cache_key]

        # Get normalization strategy
        normalization_config = entity_config.get("normalization", {})
        strategy = normalization_config.get("strategy", "none")

        # Apply normalization strategy
        if strategy == "none":
            normalized = value
        elif strategy == "trim":
            normalized = self._trim(value)
        elif strategy == "lowercase":
            normalized = self._lowercase(value)
        elif strategy == "natural_date":
            normalized = await self._natural_date(value)
        elif strategy == "llm_correction":
            normalized = await self._llm_correction(value, entity_config)
        else:
            logger.warning(f"Unknown normalization strategy: {strategy}, using original value")
            normalized = value

        # Cache result
        self.cache[cache_key] = normalized
        logger.debug(f"Normalized '{value}' -> '{normalized}' using strategy '{strategy}'")

        return normalized

    def _trim(self, value: Any) -> str:
        """Trim whitespace from value."""
        if value is None:
            return ""
        return str(value).strip()

    def _lowercase(self, value: Any) -> str:
        """Convert value to lowercase and trim."""
        if value is None:
            return ""
        return str(value).lower().strip()

    async def _natural_date(self, value: Any) -> str:
        """Convert natural language dates to ISO format.

        Handles expressions like:
        - "tomorrow", "today", "yesterday"
        - "next Monday", "next Friday"
        - "in 3 days", "in a week"
        - ISO format dates (passed through)

        Args:
            value: Natural language date expression

        Returns:
            ISO format date string (YYYY-MM-DD)
        """
        if value is None:
            return ""

        value_str = str(value).strip().lower()
        today = datetime.now().date()

        # Try direct ISO parsing first
        try:
            parsed = datetime.fromisoformat(value_str.upper() if "t" in value_str else value_str)
            return parsed.date().isoformat()
        except ValueError:
            pass

        # Handle relative dates
        relative_dates = {
            "today": today,
            "tomorrow": today + timedelta(days=1),
            "yesterday": today - timedelta(days=1),
            "day after tomorrow": today + timedelta(days=2),
        }

        if value_str in relative_dates:
            return relative_dates[value_str].isoformat()

        # Handle "next <weekday>"
        weekdays = ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"]
        for i, weekday in enumerate(weekdays):
            if f"next {weekday}" in value_str:
                days_ahead = i - today.weekday()
                if days_ahead <= 0:
                    days_ahead += 7
                return (today + timedelta(days=days_ahead)).isoformat()

        # Handle "in X days/weeks"
        if "in " in value_str:
            import re

            match = re.search(r"in\s+(\d+|a|an)\s+(day|days|week|weeks)", value_str)
            if match:
                amount = 1 if match.group(1) in ("a", "an") else int(match.group(1))
                unit = match.group(2)
                if "week" in unit:
                    amount *= 7
                return (today + timedelta(days=amount)).isoformat()

        # Fallback: use LLM for complex cases
        return await self._llm_date_parsing(value_str)

    async def _llm_date_parsing(self, value: str) -> str:
        """Use LLM to parse complex date expressions.

        Args:
            value: Date expression to parse

        Returns:
            ISO format date string
        """
        today_str = datetime.now().date().isoformat()
        prompt = f"""Convert the following date expression to ISO format (YYYY-MM-DD).
Today's date is {today_str}.

Date expression: "{value}"

Return ONLY the date in YYYY-MM-DD format, nothing else."""

        try:
            response = await self.llm.acall(prompt)
            response_str = str(response) if response is not None else ""
            date_str = response_str.strip().strip('"').strip("'")

            # Validate the result
            datetime.fromisoformat(date_str)
            logger.info(f"LLM parsed date '{value}' -> '{date_str}'")
            return date_str

        except (RuntimeError, ValueError, TypeError, AttributeError) as e:
            logger.warning(f"Failed to parse date '{value}': {e}")
            # Return original value - validator will catch it
            return value

    async def _llm_correction(
        self,
        value: Any,
        entity_config: dict[str, Any],
    ) -> str:
        """Use LLM to correct/normalize value.

        Args:
            value: Raw value to correct
            entity_config: Entity configuration with examples/constraints

        Returns:
            Corrected value
        """
        entity_name = entity_config.get("name", "value")
        entity_type = entity_config.get("type", "string")
        examples = entity_config.get("examples", [])

        # Build prompt for LLM correction
        examples_str = ", ".join(str(ex) for ex in examples[:5]) if examples else "N/A"
        prompt = f"""Normalize the following {entity_type} value for entity '{entity_name}'.

Examples of valid values: {examples_str}

Input value: "{value}"

Return only the normalized value, nothing else."""

        try:
            # Call LLM for correction
            response = await self.llm.acall(prompt)
            # Ensure response is a string
            response_str = str(response) if response is not None else ""
            corrected = response_str.strip().strip('"').strip("'")

            logger.info(f"LLM corrected '{value}' -> '{corrected}' for entity '{entity_name}'")
            return corrected

        except (RuntimeError, ValueError, TypeError, AttributeError) as e:
            # Errores esperados de LLM correction
            logger.error(
                f"LLM correction failed for '{value}': {e}",
                extra={"entity_name": entity_name, "error_type": type(e).__name__},
            )
            # Fallback to trim
            return self._trim(value)
        except Exception as e:
            # Errores inesperados
            logger.error(
                f"Unexpected error in LLM correction for '{value}': {e}",
                exc_info=True,
                extra={"entity_name": entity_name},
            )
            # Fallback to trim
            return self._trim(value)

    def _get_cache_key(self, value: Any, entity_config: dict[str, Any]) -> str:
        """Generate cache key for value and entity config."""
        strategy = entity_config.get("normalization", {}).get("strategy", "none")
        entity_name = entity_config.get("name", "unknown")
        value_str = str(value).lower().strip() if value is not None else ""

        # Create hash for cache key
        return generate_cache_key(strategy, entity_name, value_str)

    async def normalize_slot(
        self,
        slot_name: str,
        value: Any,
    ) -> Any:
        """Normalize a slot value using its configuration.

        Args:
            slot_name: Name of the slot to normalize
            value: Raw value to normalize

        Returns:
            Normalized value
        """
        # Get slot configuration
        slot_config = self.slots_config.get(slot_name, {})

        # Handle both dict and SlotConfig object
        if hasattr(slot_config, "model_dump"):
            slot_config_dict = slot_config.model_dump()
        elif isinstance(slot_config, dict):
            slot_config_dict = slot_config
        else:
            slot_config_dict = {}

        entity_config = {
            "name": slot_name,
            "type": slot_config_dict.get("type", "string"),
            "normalization": slot_config_dict.get("normalization", {"strategy": "trim"}),
            "examples": slot_config_dict.get("examples", []),
        }

        return await self.normalize(value, entity_config)

    async def process(self, slots: dict[str, Any]) -> dict[str, Any]:
        """Normalize multiple slots using their configurations.

        Args:
            slots: Dictionary of slot_name -> raw_value

        Returns:
            Dictionary of slot_name -> normalized_value
        """
        normalized: dict[str, Any] = {}

        for slot_name, raw_value in slots.items():
            normalized[slot_name] = await self.normalize_slot(slot_name, raw_value)

        return normalized
