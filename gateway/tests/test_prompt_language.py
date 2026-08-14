"""The rewriter must never switch human languages (dogfood finding: Japanese came back Chinese)."""
from declaude.prompts import SYSTEM_PROMPT


def test_prompt_pins_output_language():
    lowered = SYSTEM_PROMPT.lower()
    assert "same language" in lowered
    assert "never translate between human languages" in lowered


def test_prompt_still_targets_assistant_tics():
    assert "Great question!" in SYSTEM_PROMPT
    assert "Preserve all facts" in SYSTEM_PROMPT
