"""
Global fixtures for the Fourth test suite.

block_llm_network (autouse): stubs both LLM entry points so no test can
reach OpenRouter or Anthropic, regardless of what is in .env. Tests that
exercise LLM-path logic override by patching the same names inside the
test (an inner unittest.mock.patch wins over this fixture).

The pipeline modules are importable under two names — "src.X" (tests)
and bare "X" (agent.py's sys.path hack). Both module objects are patched
when present so no path is left live.
"""

import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

import outbound_generator as _outbound_flat  # noqa: E402
import src.outbound_generator as _outbound_pkg  # noqa: E402


@pytest.fixture(autouse=True)
def block_llm_network(monkeypatch):
    def _blocked(*_args, **_kwargs):
        raise RuntimeError("network disabled in tests")

    for module in (_outbound_pkg, _outbound_flat):
        monkeypatch.setattr(module, "_call_openrouter", _blocked)
        monkeypatch.setattr(module, "_call_anthropic", _blocked)
