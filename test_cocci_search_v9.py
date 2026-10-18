#!/usr/bin/env python3
"""Test for cocci_search V9 fix: explicit truncation declaration."""

import sys
sys.path.insert(0, '/home/lucas/Escritorio/rxre')

from tools.rxre.api.machine import _obs_completeness

def test_cocci_search_truncated_detection():
    """Test that truncated cocci_search results are detected as partial."""
    # Simulate cocci_search with 300 diff lines truncated to 200
    lineas_diff_original = [f"+line{i}" for i in range(300)]  # 300 lines
    lineas_diff_truncado = lineas_diff_original[:200]  # Truncated to 200
    
    cocci_obs = [{
        "result_id": "test_truncated",
        "type": "SEMANTIC_HYPOTHESIS",
        "value": {
            "n_coincidencias": 150,
            "diff": lineas_diff_truncado,  # Only 200 lines (truncated from 300)
            "patron": "test pattern",
            "ficheros": ["test.c"]
        },
        "source": "/path/to/test.c",
        "limitations": [
            "una coincidencia de Coccinelle es una SEMANTIC_HYPOTHESIS sobre el TEXTO fuente.",
            "Coccinelle necesita FUENTES. No sirve sobre un .ko ya compilado.",
        ],
        "status": "declared",
        "artifact": "/path/to/test.c",
        "artifact_hash": "abc123",
        "timestamp": "2026-10-17T10:00:00",
        "completitud": {
            "completo": False,  # 300 > 200
            "omitidos": 100,    # 300 - 200 = 100
            "limite": 200,
            "elemento": "lineas_diff",
        }
    }]
    
    result = _obs_completeness(cocci_obs)
    assert result == "partial", f"Expected 'partial' for truncated cocci_search, got {result}"
    print("✓ Test PASSED: Truncated cocci_search detected as partial")

def test_cocci_search_complete_under_limit():
    """Test that cocci_search results under limit are complete."""
    # Simulate cocci_search with 150 diff lines (under 200 limit)
    lineas_diff_completo = [f"+line{i}" for i in range(150)]  # 150 lines
    
    cocci_obs = [{
        "result_id": "test_complete",
        "type": "SEMANTIC_HYPOTHESIS",
        "value": {
            "n_coincidencias": 75,
            "diff": lineas_diff_completo,  # 150 lines (under 200 limit)
            "patron": "test pattern",
            "ficheros": ["test.c"]
        },
        "source": "/path/to/test.c",
        "limitations": [
            "una coincidencia de Coccinelle es una SEMANTIC_HYPOTHESIS sobre el TEXTO fuente.",
        ],
        "status": "declared",
        "artifact": "/path/to/test.c",
        "artifact_hash": "def456",
        "timestamp": "2026-10-17T10:00:00",
        "completitud": {
            "completo": True,   # 150 <= 200
            "omitidos": 0,
            "limite": 200,
            "elemento": "lineas_diff",
        }
    }]
    
    result = _obs_completeness(cocci_obs)
    assert result == "complete", f"Expected 'complete' for cocci_search under limit, got {result}"
    print("✓ Test PASSED: Cocci_search under limit detected as complete")

def test_cocci_search_exact_limit():
    """Test that cocci_search results at exact limit are complete."""
    # Simulate cocci_search with exactly 200 diff lines
    lineas_diff_exact = [f"+line{i}" for i in range(200)]  # 200 lines exactly
    
    cocci_obs = [{
        "result_id": "test_exact",
        "type": "SEMANTIC_HYPOTHESIS",
        "value": {
            "n_coincidencias": 100,
            "diff": lineas_diff_exact,  # Exactly 200 lines
            "patron": "test pattern",
            "ficheros": ["test.c"]
        },
        "source": "/path/to/test.c",
        "limitations": [
            "una coincidencia de Coccinelle es una SEMANTIC_HYPOTHESIS sobre el TEXTO fuente.",
        ],
        "status": "declared",
        "artifact": "/path/to/test.c",
        "artifact_hash": "ghi789",
        "timestamp": "2026-10-17T10:00:00",
        "completitud": {
            "completo": True,   # 200 <= 200
            "omitidos": 0,
            "limite": 200,
            "elemento": "lineas_diff",
        }
    }]
    
    result = _obs_completeness(cocci_obs)
    assert result == "complete", f"Expected 'complete' for cocci_search at exact limit, got {result}"
    print("✓ Test PASSED: Cocci_search at exact limit detected as complete")

def test_cocci_search_no_marker_backwards_compatibility():
    """Test that cocci_search without marker still works (backwards compatibility)."""
    # This simulates the old behavior for fixtures or legacy data
    lineas_diff = [f"+line{i}" for i in range(100)]  # 100 lines
    
    cocci_obs = [{
        "result_id": "test_no_marker",
        "type": "SEMANTIC_HYPOTHESIS",
        "value": {
            "n_coincidencias": 50,
            "diff": lineas_diff,
            "patron": "test pattern",
            "ficheros": ["test.c"]
        },
        "source": "/path/to/test.c",
        "limitations": [
            "una coincidencia de Coccinelle es una SEMANTIC_HYPOTHESIS sobre el TEXTO fuente.",
        ],
        "status": "declared",
        "artifact": "/path/to/test.c",
        "artifact_hash": "jkl000",
        "timestamp": "2026-10-17T10:00:00",
        # No completitud marker - should use old default logic
    }]
    
    result = _obs_completeness(cocci_obs)
    assert result == "complete", f"Expected 'complete' for cocci_search without marker, got {result}"
    print("✓ Test PASSED: Cocci_search without marker (backwards compatible)")

if __name__ == "__main__":
    print("Running cocci_search V9 verification tests...\n")
    
    test_cocci_search_truncated_detection()
    test_cocci_search_complete_under_limit()
    test_cocci_search_exact_limit()
    test_cocci_search_no_marker_backwards_compatibility()
    
    print("\n✅ ALL TESTS PASSED - V9 fix verified!")