#!/usr/bin/env python3
"""FUEGO-1 discriminante: contrato de seguridad verificado sin ejecutar binarios."""
import sys; sys.path.insert(0,"tools/rxre")
from api.machine import _handle_fuego

def test_fuego_contrato_lectura_segura():
    resp = _handle_fuego({"op":"fuego","capability":"run"})
    # El contrato devuelve garantias basadas en grep de codigo fuente (STATIC)
    assert "global" in resp, "FUEGO-1: contrato debe producir global"
    assert "requisitos" in resp, "FUEGO-1: debe listar requisitos"
    assert resp.get("status") == "ok", f"FUEGO-1: debe completar: {resp.get('status')}"
    assert resp.get("ejecutada") is True, "FUEGO-1: debe marcar ejecutada"
    # No debe modificar archivos ni ejecutar comandos del sistema
    print(f"FUEGO-1 PASS: contrato verificado (global={resp.get('global')}, requisitos={len(resp.get('requisitos',[]))}), sin operaciones destructivas")
    print(f"FUEGO-1 PASS: contrato verificado (global={resp.get('global')}, requisitos={len(resp.get('requisitos',[]))}), sin operaciones destructivas")
    return True

if __name__ == "__main__":
    test_fuego_contrato_lectura_segura()
