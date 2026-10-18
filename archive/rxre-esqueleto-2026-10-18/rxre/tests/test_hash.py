"""Las tres capas del hash, separadas.

El test que mas importa es `test_authenticity_not_determined`: sin ancla, la
respuesta correcta es NOT_DETERMINED. Si devolviera FAIL, el sistema
afirmaria "esto no es autentico" sin tener contra que compararlo, y si
devolviera PASS, afirmaria lo contrario con la misma falta de informacion.
"""
from __future__ import annotations

from pathlib import Path

from rxre import hash as h


def test_integrity_detects_change(tmp_path):
    """La unica capa que si tiene veredicto binario: el fichero esta o no."""
    art = tmp_path / "bin"
    art.write_bytes(b"contenido original")
    declarado = h.hash_file(art)
    assert h.verify_integrity(art, declarado) is True

    art.write_bytes(b"contenido MODIFICADO")
    assert h.verify_integrity(art, declarado) is False


def test_authenticity_not_determined(tmp_path):
    """Sin ancla -> NOT_DETERMINED. Ni PASS ni FAIL.

    FAIL seria afirmar "no es autentico" sin referencia; PASS seria afirmar
    "si lo es". Las dos cosas son afirmaciones que la funcion no puede hacer.
    """
    art = tmp_path / "bin"
    art.write_bytes(b"contenido")
    declarado = h.hash_file(art)

    assert h.verify_authenticity(declarado, None) == h.AUTH_NOT_DETERMINED
    assert h.verify_authenticity(declarado, None) != h.AUTH_FAIL


def test_authenticity_with_anchor(tmp_path):
    """Con ancla que coincide -> PASS; con ancla que no -> FAIL."""
    art = tmp_path / "bin"
    art.write_bytes(b"contenido")
    ancla = tmp_path / "ancla"
    ancla.write_bytes(b"contenido")
    declarado = h.hash_file(art)

    assert h.verify_authenticity(declarado, ancla) == h.AUTH_PASS
    ancla.write_bytes(b"otra cosa")
    assert h.verify_authenticity(declarado, ancla) == h.AUTH_FAIL


def test_semantics_never_passes(tmp_path):
    """[v3-6] La validez semantica NUNCA es PASS. Ni con artefacto y claim.

    Ni siquiera con el claim y el artefacto delante. Un hash que coincidiera no
    distinguiria un artefacto que dice la verdad de otro identico que miente
    con las mismas palabras.
    """
    art = tmp_path / "bin"
    art.write_bytes(b"contenido")
    for claim in ("afirmacion", None, {"statement": "x"}):
        assert h.verify_semantics(claim, art) == h.SEMANTICS_REQUIRES_TEST


def test_integrity_pass_does_not_imply_the_other_two(tmp_path):
    """Un hash integro NO autentica y NO valida.

    Este es el test que la v3-6 prohibe violar. Un artefacto integro con
   Integrity PASS, autenticidad NOT_DETERMINED y validez REQUIRES_TEST es el
    resultado correcto: tres preguntas, tres respuestas, ninguna prestada.
    """
    art = tmp_path / "bin"
    art.write_bytes(b"contenido")
    r = h.verify_all(art, h.hash_file(art), trust_anchor=None, claim="x")

    assert r["integridad"] == h.INTEGRITY_PASS
    assert r["autenticidad"] == h.AUTH_NOT_DETERMINED
    assert r["validez_semantica"] == h.SEMANTICS_REQUIRES_TEST
    # Y en ningun caso los tres coinciden en un unico PASS.
    assert len({*r.values()}) > 1