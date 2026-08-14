"""Boundary guard on model output: no leaked commentary, no language switching."""
from declaude.postprocess import clean_output, dominant_script


def test_dominant_script_detection():
    assert dominant_script("Hello there") == "latin"
    assert dominant_script("سؤال رائع") == "arabic"
    assert dominant_script("これは堅牢です") == "japanese"
    assert dominant_script("这是一个解决方案") == "han"
    assert dominant_script("Привет мир") == "cyrillic"


def test_strips_leaked_commentary():
    out = clean_output("Great question! It works.", "It works.\n\n翻译：\n根据指示，需要将文本")
    assert out == "It works."


def test_strips_english_meta_preamble():
    out = clean_output("Great question! It works.", "Sure, here is the rewritten text:\n\nIt works.")
    assert out == "It works."


def test_rejects_language_switch_returns_original():
    original = "سؤال رائع! هذا حل قوي وجاهز للإنتاج."
    switched = "这是一个很好的问题！这个解决方案强大。"
    assert clean_output(original, switched) == original


def test_allows_same_language_rewrite():
    original = "素晴らしい質問です！これは堅牢です。"
    rewritten = "これは堅牢です。"
    assert clean_output(original, rewritten) == rewritten


def test_japanese_to_chinese_is_a_switch():
    assert clean_output("これは堅牢な解決策です。", "这是一个坚固的解决方案。") == "これは堅牢な解決策です。"


def test_empty_model_output_falls_back():
    assert clean_output("Great question! It works.", "   ") == "Great question! It works."
