"""Agent Smith: autonomous reasoning, code generation and execution.

Package layout
--------------
smith.models      Pydantic contracts (task input, solution output, sandbox config)
smith.config      Environment / .env loading and agent run configuration
smith.llm         Provider abstraction, API-key rotation, retries, usage tracking
smith.sandbox     Isolated execution process + MCP bridge + interactive REPL
smith.agent       The Thought -> Code -> Observation loop, prompts, memory, extraction
smith.tools       Tool implementations used by the MCP servers (independent of the agent)
"""

__version__ = "1.0.0"
