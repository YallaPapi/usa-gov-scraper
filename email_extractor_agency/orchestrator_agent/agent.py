from agency_swarm import Agent
from .tools import CoordinateExtraction, AggregateResults, PrioritizeTargets

class OrchestratorAgent(Agent):
    def __init__(self):
        super().__init__(
            name="Orchestrator",
            description="CEO agent that coordinates all email extraction operations",
            instructions="./instructions/orchestrator_instructions.md",
            tools=[CoordinateExtraction, AggregateResults, PrioritizeTargets],
            model="gpt-4o"
        )