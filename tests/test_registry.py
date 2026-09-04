# tests/test_registry.py
from cleaners.registry import get_signature, list_sources

def test_gamma_signature_loads():
    sig = get_signature("gamma")
    assert sig["source"] == "gamma"
    assert sig["type"] in ("footer_band", "corner_badge", "overlay_text")
    assert "version_tested" in sig

def test_unknown_source_raises():
    import pytest
    with pytest.raises(KeyError):
        get_signature("yok-boyle-kaynak")

def test_list_sources_nonempty():
    assert "gamma" in list_sources()
