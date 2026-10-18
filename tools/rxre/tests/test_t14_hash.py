#!/usr/bin/env python3
"""T14: 3 capas del hash separadas.

    ESTADO: HIPOTESIS hasta que el audit lo confirme.

QUE COMPRUEBA
-------------
Las 3 capas del hash se devuelven separadas. La integridad es binaria.
La autenticidad es PASS/NOT_DETERMINED/FAIL. La validez semantica es
siempre REQUIRES_TEST.

CONTRASTE
---------
Antes: no existia core/hash.py.
Despues: las 3 funciones existen y se comportan distinto.
"""
from __future__ import annotations

import hashlib
from pathlib import Path

import pytest

import os, sys; HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, os.path.abspath(os.path.join(HERE, '..')))
from core import hash as H


def test_integrity_detects_change(tmp_path):
    """Capa 1: el hash actual == hash declarado?"""
    art = tmp_path / "bin"
    art.write_bytes(b"contenido original")
    declarado = H.hash_file(art)
    assert H.verify_integrity(art, declarado) is True

    art.write_bytes(b"contenido MODIFICADO")
    assert H.verify_integrity(art, declarado) is False


def test_authenticity_not_determined(tmp_path):
    """Capa 2: sin ancla → NOT_DETERMINED. Ni PASS ni FAIL."""
    art = tmp_path / "bin"
    art.write_bytes(b"contenido")
    declarado = H.hash_file(art)

    assert H.verify_authenticity(declared_hash=declarado,
                                 trust_anchor=None) == H.AUTH_NOT_DETERMINED


def test_authenticity_with_anchor(tmp_path):
    """Capa 2: con ancla que coincide → PASS; con ancla que no → FAIL."""
    art = tmp_path / "bin"
    art.write_bytes(b"contenido")
    ancla = tmp_path / "ancla"
    ancla.write_bytes(b"contenido")
    declarado = H.hash_file(art)

    assert H.verify_authenticity(declarado, ancla) == H.AUTH_PASS
    ancla.write_bytes(b"otra cosa")
    assert H.verify_authenticity(declarado, ancla) == H.AUTH_FAIL


def test_semantics_never_passes(tmp_path):
    """Capa 3: la validez semantica NUNCA es PASS."""
    art = tmp_path / "bin"
    art.write_bytes(b"contenido")
    for claim in ("afirmacion", None, {"statement": "x"}):
        assert H.verify_semantics(claim, art) == H.SEMANTICS_REQUIRES_TEST


def test_integrity_pass_does_not_imply_the_other_two(tmp_path):
    """Un hash integro NO autentica y NO valida.

    Este es el test que la v3-6 prohibe violar. Un artefacto integro con
    integridad PASS, autenticidad NOT_DETERMINED y validez REQUIRES_TEST es
    el resultado correcto: tres preguntas, tres respuestas, ninguna prestada.
    """
    art = tmp_path / "bin"
    art.write_bytes(b"contenido")
    r = H.verify_all(art, H.hash_file(art), trust_anchor=None, claim="x")

    assert r["integridad"] == H.INTEGRITY_PASS
    assert r["autenticidad"] == H.AUTH_NOT_DETERMINED
    assert r["validez_semantica"] == H.SEMANTICS_REQUIRES_TEST
    assert len({*r.values()}) > 1


if __name__ == "__main__":
    pytest.main([__file__, "-v"])