"""
src/agent_orchestration
-----------------------
Multi-agent orchestration layer for offline local LLM workflows.

Manages task queuing, prompt chunking, context-window budgets, and
structured result parsing for local AI models (e.g. DeepSeek, Llama)
running within a strict 16 GB VRAM envelope.
"""
