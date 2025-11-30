"""Integration tests for linear step compiler"""

import pytest
from langgraph.graph import StateGraph

from soni.compiler.builder import StepCompiler
from soni.compiler.parser import StepParser
from soni.core.config import SoniConfig, StepConfig
from soni.core.state import DialogueState


@pytest.fixture
def booking_config() -> SoniConfig:
    """Create flight booking configuration for testing."""
    config_dict = {
        "version": "1.0",
        "settings": {
            "models": {
                "nlu": {
                    "provider": "openai",
                    "model": "gpt-4o-mini",
                    "temperature": 0.1,
                },
            },
        },
        "flows": {
            "book_flight": {
                "description": "Book a flight",
                "steps": [
                    {"step": "collect_origin", "type": "collect", "slot": "origin"},
                    {"step": "collect_destination", "type": "collect", "slot": "destination"},
                    {"step": "collect_date", "type": "collect", "slot": "departure_date"},
                    {
                        "step": "search_flights",
                        "type": "action",
                        "call": "search_available_flights",
                    },
                ],
            }
        },
        "slots": {
            "origin": {
                "type": "string",
                "prompt": "What is your origin?",
            },
            "destination": {
                "type": "string",
                "prompt": "What is your destination?",
            },
            "departure_date": {
                "type": "date",
                "prompt": "When do you want to depart?",
            },
        },
        "actions": {"search_available_flights": {"inputs": [], "outputs": []}},
    }
    return SoniConfig(**config_dict)


def test_parse_and_compile_linear_flow(booking_config: SoniConfig):
    """Test parsing and compiling a complete linear flow"""
    # Arrange
    parser = StepParser()
    compiler = StepCompiler(config=booking_config)
    flow_config = booking_config.flows["book_flight"]

    # Act
    parsed_steps = parser.parse(flow_config.steps)
    graph = compiler.compile("book_flight", parsed_steps)

    # Assert
    assert len(parsed_steps) == 4
    assert isinstance(graph, StateGraph)
    # Verify all steps were parsed correctly
    assert parsed_steps[0].step_id == "collect_origin"
    assert parsed_steps[1].step_id == "collect_destination"
    assert parsed_steps[2].step_id == "collect_date"
    assert parsed_steps[3].step_id == "search_flights"


def test_compiler_generates_correct_node_sequence(booking_config: SoniConfig):
    """Test compiler generates nodes in correct sequence"""
    # Arrange
    parser = StepParser()
    compiler = StepCompiler(config=booking_config)
    flow_config = booking_config.flows["book_flight"]
    parsed_steps = parser.parse(flow_config.steps)

    # Act
    dag = compiler._generate_dag("book_flight", parsed_steps)

    # Assert
    assert len(dag.nodes) == 5  # understand + 4 steps
    assert dag.nodes[0].id == "understand"
    assert dag.nodes[1].id == "collect_origin"
    assert dag.nodes[2].id == "collect_destination"
    assert dag.nodes[3].id == "collect_date"
    assert dag.nodes[4].id == "search_flights"


def test_compiler_generates_sequential_edges(booking_config: SoniConfig):
    """Test compiler generates sequential edges correctly"""
    # Arrange
    parser = StepParser()
    compiler = StepCompiler(config=booking_config)
    flow_config = booking_config.flows["book_flight"]
    parsed_steps = parser.parse(flow_config.steps)

    # Act
    dag = compiler._generate_dag("book_flight", parsed_steps)

    # Assert
    # Should have: START->understand, understand->collect_origin,
    # collect_origin->collect_destination, collect_destination->collect_date,
    # collect_date->search_flights, search_flights->END
    assert len(dag.edges) == 6

    # Verify edge sequence
    assert dag.edges[0].source == "__start__"
    assert dag.edges[0].target == "understand"
    assert dag.edges[1].source == "understand"
    assert dag.edges[1].target == "collect_origin"
    assert dag.edges[2].source == "collect_origin"
    assert dag.edges[2].target == "collect_destination"
    assert dag.edges[3].source == "collect_destination"
    assert dag.edges[3].target == "collect_date"
    assert dag.edges[4].source == "collect_date"
    assert dag.edges[4].target == "search_flights"
    assert dag.edges[5].source == "search_flights"
    assert dag.edges[5].target == "__end__"


def test_compiler_handles_action_with_map_outputs(booking_config: SoniConfig):
    """Test compiler handles action steps with map_outputs"""
    # Arrange
    config_dict = {
        "version": "1.0",
        "settings": {
            "models": {
                "nlu": {
                    "provider": "openai",
                    "model": "gpt-4o-mini",
                    "temperature": 0.1,
                },
            },
        },
        "flows": {
            "test_flow": {
                "description": "Test flow",
                "steps": [
                    {
                        "step": "search",
                        "type": "action",
                        "call": "search_flights",
                        "map_outputs": {
                            "flights": "api_flights",
                            "price": "api_price",
                        },
                    },
                ],
            }
        },
        "slots": {},
        "actions": {"search_flights": {"inputs": [], "outputs": []}},
    }
    config = SoniConfig(**config_dict)
    parser = StepParser()
    compiler = StepCompiler(config=config)
    flow_config = config.flows["test_flow"]
    parsed_steps = parser.parse(flow_config.steps)

    # Act
    dag = compiler._generate_dag("test_flow", parsed_steps)

    # Assert
    action_node = next(node for node in dag.nodes if node.id == "search")
    assert action_node.config["map_outputs"] == {
        "flights": "api_flights",
        "price": "api_price",
    }
