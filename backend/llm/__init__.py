"""LLM runtime for SentinelHack.

Lazy-loaded singleton for meta-llama/Llama-3.2-1B-Instruct on Apple MPS.
Loads once on first use; subsequent calls reuse the cached model.
"""
