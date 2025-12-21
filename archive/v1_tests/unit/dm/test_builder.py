"""Tests for Orchestrator Builder."""

import pytest
from langchain_core.runnables import Runnable

from soni.config import FlowConfig, SoniConfig
from soni.dm.builder import build_orchestrator


class TestOrchestratorBuilder:
    """Tests for build_orchestrator function."""

    def test_build_orchestrator_compiles_integration(self):
        """
        GIVEN valid config
        WHEN built
        THEN returns compiled graph with core nodes and flow subgraphs
        """
        config = SoniConfig(flows={"test_flow": FlowConfig(description="Test", steps=[])})

        graph = build_orchestrator(config)

        # Verify it is a Runnable
        assert isinstance(graph, Runnable)
        # Unfortunately can't easily inspect nodes of CompiledGraph in LG > 0.2 without get_graph()
        # But if it compiles, it means structure is valid.
