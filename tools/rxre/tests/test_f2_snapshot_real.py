#!/usr/bin/env python3
"""F2 — snapshot real de GPU (gap documentado sin autorización)."""
import pytest, os
from pathlib import Path

def test_f2_snapshot_existe():
    snap = Path(".rxre/gpu0/original/register_0.bin")
    if not snap.exists():
        pytest.skip("F2 PARTIAL: .rxre/gpu0/original NO EXISTE (requiere sudo + /dev/mem + script crear_snapshot_gpu.py; autorización previa fue solo para coccinelle, no para snapshot)")
    assert snap.stat().st_size > 0

def test_f2_revertir_con_snapshot_real():
    snap = Path(".rxre/gpu0/original/register_0.bin")
    if not snap.exists():
        pytest.skip("F2 PARTIAL: sin snapshot real (sin autorización root para /dev/mem)")
    from rxre.core.fuego import revertir
    r = revertir("gpu0")
    assert r is not None
