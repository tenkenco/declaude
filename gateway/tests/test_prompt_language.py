"""The rewriter must never switch human languages (dogfood finding: Japanese came back Chinese)."""
from declaude.prompts import SYSTEM_PROMPT


def test_prompt_pins_output_language():
    lowered = SYSTEM_PROMPT.lower()
    assert "same language" in lowered
    assert "never translate between human languages" in lowered


def test_prompt_still_targets_assistant_tics():
    assert "Great question!" in SYSTEM_PROMPT
    assert "Preserve all facts" in SYSTEM_PROMPT


def test_prompt_targets_structural_tics():
    """Sycophancy is the obvious half; these survive most edits and were being missed."""
    lowered = SYSTEM_PROMPT.lower()
    for tic in ["throat-clearing", "antithesis", "rule-of-three", "em-dash joins",
                "closing offers"]:
        assert tic in lowered, f"prompt no longer targets {tic}"


def test_prompt_forbids_acknowledgment_openers():
    """'Certainly!' survived in production despite being listed as a tic: make it a hard rule."""
    lowered = SYSTEM_PROMPT.lower()
    assert "never begin" in lowered
    assert "certainly" in lowered
    assert "rich tapestry" in lowered or "flourish" in lowered
