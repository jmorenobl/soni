"""Base class for optimizable DSPy modules.

Provides shared functionality for:
- Automatic loading of optimized models
- Standard async/sync interfaces
- Consistent logging patterns
"""

import logging
from abc import abstractmethod
from pathlib import Path
from typing import ClassVar

import dspy

logger = logging.getLogger(__name__)


class OptimizableDSPyModule(dspy.Module):
    """Base class for DSPy modules that support optimization.

    Features:
    - Automatic loading of best available optimized model
    - Configurable ChainOfThought vs Predict
    - Standard async (.acall) and sync (.forward) interfaces

    Subclasses should:
    1. Set `optimized_files` class variable with priority-ordered filenames
    2. Override `_create_extractor()` to define the signature
    3. Implement `acall()` and `forward()` with appropriate I/O types
    """

    # Override in subclass with priority-ordered optimization filenames
    optimized_files: ClassVar[list[str]] = []

    # Default use_cot setting (can be overridden per subclass)
    default_use_cot: ClassVar[bool] = False

    def __init__(self, use_cot: bool | None = None):
        """Initialize module.

        Args:
            use_cot: If True, use ChainOfThought for reasoning.
                     If False, use simple Predict (faster, less tokens).
                     If None, use class default.
        """
        super().__init__()
        effective_cot = use_cot if use_cot is not None else self.default_use_cot
        self.extractor = self._create_extractor(effective_cot)

    @abstractmethod
    def _create_extractor(self, use_cot: bool) -> dspy.Module:
        """Create the DSPy predictor/chain for this module.

        Args:
            use_cot: Whether to use ChainOfThought.

        Returns:
            Configured dspy.Predict or dspy.ChainOfThought instance.
        """
        ...

    @classmethod
    def create_with_best_model(cls, use_cot: bool | None = None) -> "OptimizableDSPyModule":
        """Create instance with the best available optimized model.

        Automatically searches for optimization files in `optimized/` directory
        using the priority order defined in `optimized_files` class variable.

        Args:
            use_cot: Whether to use ChainOfThought reasoning.

        Returns:
            Instance with loaded optimization if available, else zero-shot.
        """
        instance = cls(use_cot=use_cot)
        instance._load_best_optimization()
        return instance

    def _load_best_optimization(self) -> bool:
        """Load best available optimization file.

        Returns:
            True if an optimization was loaded, False otherwise.
        """
        base_path = Path(__file__).parent / "optimized"

        for filename in self.optimized_files:
            file_path = base_path / filename
            if file_path.exists():
                logger.info(f"Loading optimized module from {file_path}")
                try:
                    self.load(str(file_path))
                    return True
                except Exception as e:
                    logger.warning(f"Failed to load optimized module {filename}: {e}")
            else:
                logger.debug(f"Optimized module not found: {filename}")

        logger.info(f"No optimized {self.__class__.__name__} found, using default zero-shot.")
        return False
