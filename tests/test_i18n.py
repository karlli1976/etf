import pytest
from i18n import t, LANGS


def test_langs_contains_zh_and_en():
    assert "zh" in LANGS
    assert "en" in LANGS


def test_known_key_zh():
    result = t("btn_run", "zh")
    assert result == "确认并运行回测"


def test_known_key_en():
    result = t("btn_run", "en")
    assert result == "Run Backtest"


def test_unknown_lang_falls_back_to_zh():
    result = t("btn_run", "fr")
    assert result == "确认并运行回测"


def test_missing_key_returns_bracket_key():
    result = t("nonexistent_key_xyz", "zh")
    assert result == "[nonexistent_key_xyz]"


def test_missing_key_unknown_lang_returns_bracket_key():
    result = t("nonexistent_key_xyz", "en")
    assert result == "[nonexistent_key_xyz]"


def test_format_kwargs_zh():
    result = t("weight_total", "zh", total=100)
    assert "100" in result


def test_format_kwargs_en():
    result = t("weight_total", "en", total=85)
    assert "85" in result


def test_sweep_caption_with_multiple_kwargs():
    result = t("sweep_caption", "en", n=45, start=30, end=250, step=5)
    assert "45" in result
    assert "30" in result
    assert "250" in result
    assert "5" in result


def test_sweep_caption_zh():
    result = t("sweep_caption", "zh", n=10, start=50, end=200, step=10)
    assert "10" in result
    assert "50" in result
    assert "200" in result


def test_format_kwargs_cost_fixed():
    result = t("cost_fixed", "en", pct=0.025)
    assert "0.025" in result


def test_format_kwargs_status_caption_zh():
    result = t("status_caption", "zh", lag=1, lag_label="无偏差", cost_label="不计成本")
    assert "1" in result
    assert "无偏差" in result


def test_all_keys_have_zh_entry():
    from i18n import _S
    for key, val in _S.items():
        assert "zh" in val, f"Key '{key}' missing 'zh' entry"


def test_all_keys_have_en_entry():
    from i18n import _S
    for key, val in _S.items():
        assert "en" in val, f"Key '{key}' missing 'en' entry"
