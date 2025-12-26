from unittest.mock import AsyncMock, MagicMock, patch

import dspy
import pytest
from pydantic import BaseModel

from soni.du.base import OptimizableDSPyModule, safe_extract_result, validate_dspy_result
from soni.du.models import DialogueContext, NLUOutput
from soni.du.modules.extract_commands import CommandGenerator


class MockModel(BaseModel):
    name: str
    value: int


class TestDSPyValidation:
    """Tests for DSPy result validation and conversion."""

    def test_validate_dspy_result_success_types(self):
        """Should validate various DSPy return formats."""
        # Case 1: Already correct type
        obj = MockModel(name="test", value=1)
        assert validate_dspy_result(obj, MockModel) == obj

        # Case 2: Dict
        data = {"name": "test", "value": 1}
        result = validate_dspy_result(data, MockModel)
        assert result.name == "test"
        assert result.value == 1

        # Case 3: DSPy Prediction with _store
        mock_pred = MagicMock()
        mock_pred._store = {"name": "test", "value": 1}
        result = validate_dspy_result(mock_pred, MockModel)
        assert result.name == "test"

        # Case 4: Object with model_dump
        mock_dump = MagicMock()
        mock_dump.model_dump.return_value = {"name": "test", "value": 1}
        result = validate_dspy_result(mock_dump, MockModel)
        assert result.name == "test"

    def test_validate_dspy_result_failures(self):
        """Should raise TypeError for invalid results."""
        with pytest.raises(TypeError, match="Cannot validate None"):
            validate_dspy_result(None, MockModel)

        with pytest.raises(TypeError, match="Cannot convert result of type"):
            validate_dspy_result(123, MockModel)

    def test_safe_extract_result(self):
        """Should fallback to default on validation failure."""
        default = MockModel(name="default", value=0)

        # Success
        assert safe_extract_result(
            {"name": "ok", "value": 1}, MockModel, lambda: default
        ) == MockModel(name="ok", value=1)

        # Failure (ValidationError)
        assert safe_extract_result({"invalid": "data"}, MockModel, lambda: default) == default

        # Failure (TypeError)
        assert safe_extract_result(None, MockModel, lambda: default) == default


class ConcreteOptimizableModule(OptimizableDSPyModule):
    """Concrete implementation for testing base class."""

    optimized_files = ["test_opt.json"]

    def _create_extractor(self, use_cot: bool):
        if use_cot:
            return dspy.ChainOfThought("msg -> result")
        return dspy.Predict("msg -> result")


class TestOptimizableDSPyModule:
    """Tests for OptimizableDSPyModule base class."""

    def test_initialization(self):
        """Should initialize with or without CoT."""
        mod1 = ConcreteOptimizableModule(use_cot=True)
        assert isinstance(mod1.extractor, dspy.ChainOfThought)

        mod2 = ConcreteOptimizableModule(use_cot=False)
        # Note: dspy.Predict might be a class or a wrapper depending on version
        # but ChainOfThought should definitely be different.
        assert not isinstance(mod2.extractor, dspy.ChainOfThought)

    def test_load_best_optimization_found(self):
        """Should return True and load if file exists."""
        mod = ConcreteOptimizableModule()
        with patch("pathlib.Path.exists", return_value=True):
            with patch.object(mod, "load") as mock_load:
                assert mod._load_best_optimization() is True
                mock_load.assert_called_once()

    def test_load_best_optimization_not_found(self):
        """Should return False if no file exists."""
        mod = ConcreteOptimizableModule()
        with patch("pathlib.Path.exists", return_value=False):
            assert mod._load_best_optimization() is False

    def test_validate_dspy_result_fallback_vars(self):
        """Should try vars() fallback."""

        class SimpleObj:
            def __init__(self):
                self.name = "vars"
                self.value = 1

        assert validate_dspy_result(SimpleObj(), MockModel).name == "vars"

    def test_safe_extract_result_unexpected_error(self):
        """Should handle unexpected errors in safe_extract."""
        default = MockModel(name="def", value=0)
        # Force an error by passing something that makes model_validate blow up in an unexpected way
        # or mock validate_dspy_result to raise a generic Exception
        with patch("soni.du.base.validate_dspy_result", side_effect=RuntimeError("unexpected")):
            assert safe_extract_result({}, MockModel, lambda: default) == default

    def test_load_best_optimization_exception(self):
        """Should handle exceptions during load."""
        mod = ConcreteOptimizableModule()
        with patch("pathlib.Path.exists", return_value=True):
            with patch.object(mod, "load", side_effect=Exception("load error")):
                assert mod._load_best_optimization() is False


class TestCommandGenerator:
    """Tests for CommandGenerator specialized logic."""

    def test_convert_history(self):
        """Should convert various history formats."""
        gen = CommandGenerator()

        # Empty
        assert gen._convert_history([]) == []

        # Dicts
        h1 = [{"role": "user", "content": "hi"}]
        assert gen._convert_history(h1) == h1

        # LangChain style objects
        mock_msg = MagicMock()
        mock_msg.type = "human"
        mock_msg.content = "hello"
        assert gen._convert_history([mock_msg]) == [{"role": "user", "content": "hello"}]

        # Mixed/Fallback
        assert gen._convert_history(["random text"]) == [{"role": "user", "content": "random text"}]

    @pytest.mark.asyncio
    async def test_aforward_error_handling(self):
        """Should return default NLUOutput on failure."""
        gen = CommandGenerator()
        gen.extractor = AsyncMock(side_effect=Exception("api down"))
        ctx = DialogueContext(available_flows=[], available_commands=[])

        result = await gen.aforward("test", ctx)
        assert result.confidence == 0.0
        assert result.commands == []

    def test_sync_forward(self):
        """Should return raw Prediction result for optimization."""
        gen = CommandGenerator()
        gen.extractor = MagicMock()

        mock_pred = MagicMock()
        mock_pred.result = NLUOutput(commands=[], confidence=1.0)
        gen.extractor.return_value = mock_pred

        ctx = DialogueContext(available_flows=[], available_commands=[])
        result = gen.forward("test", ctx)
        assert result.confidence == 1.0

    def test_predict_mode(self):
        """Should use dspy.Predict if use_cot is False."""
        gen = CommandGenerator(use_cot=False)
        assert not isinstance(gen.extractor, dspy.ChainOfThought)

    def test_create_with_best_model(self):
        """Should call factory method correctly."""
        # Using a real subclass of OptimizableDSPyModule
        instance = CommandGenerator.create_with_best_model(use_cot=False)
        assert isinstance(instance, CommandGenerator)


class TestRephraseResponse:
    """Tests for ResponseRephraser specialized logic."""

    @pytest.mark.asyncio
    async def test_aforward_logic(self):
        """Should call extractor with correct arguments."""
        from soni.du.modules.rephrase_response import ResponseRephraser

        gen = ResponseRephraser(tone="professional")
        gen.extractor = AsyncMock()

        mock_res = MagicMock()
        mock_res.polished_response = "Hello Professional!"
        gen.extractor.acall.return_value = mock_res

        result = await gen.aforward("Hi", "Context")
        assert result == "Hello Professional!"

        # Verify call args
        args, kwargs = gen.extractor.acall.call_args
        assert kwargs["template_response"] == "Hi"
        assert kwargs["conversation_context"] == "Context"
        assert kwargs["tone"] == "professional"
