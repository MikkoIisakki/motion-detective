"""Shared pytest configuration.

Registers a deterministic hypothesis profile so property-based tests run
identically locally and in CI: fixed derandomized example generation, a
modest example budget to keep the suite fast, and no per-example deadline
(CI machines have noisy timing).
"""
from hypothesis import settings

settings.register_profile("motion-detective", max_examples=50, derandomize=True, deadline=None)
settings.load_profile("motion-detective")
