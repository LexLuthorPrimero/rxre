#!/usr/bin/env python3
"""Cobertura de descubrimiento de RXRE sobre el diccionario de registros de GFX8.

El DENOMINADOR no lo elige este script:  es "los #define mm* de
include/asic_reg/gca/gfx_8_0_d.h",  que es el diccionario NATIVO de GFX8
(1546 lo confirmo:  en gca/,  no prestado).  2633 entradas,  medidas.

El ORACULO tampoco lo elige este script:  el valor se lee del propio #define,
  con una regex distinta de la que usa rxre.  Si las dos no coinciden,  el
  fallo es de rxre.  Si las dos fallan,  es de la regex  y se dice.

Se ejecuta en proceso,  reusando cli.main(),  porque el indice de rxre se
reconstruye en cada invocacion.  No acelera nada;  evita el arranque del
interprete.  El coste real son ~1.8 s por registro.

Salida:  un JSONL,  una linea por registro,  con el veredicto  y el motivo.
Sale de forma incremental,  para que un corte no tire el trabajo hecho.

ESTADO DE LA HERRAMIENTA:  SELF_TESTED,  no VALIDATED.
  Se valida contra si mismo en los dos modos de fallo:
    --mutacion   cambia el valor del #define  y exige que el veredicto cambie
    --muestra N  prueba sobre una submuestra y declara el metodo de seleccion
"""
import io
import json
import re
import sys
import time
import contextlib

RAIZ = "/home/lucas/Escritorio/RX550-INVESTIGACION"
DICC = ("RESEARCH/working/linux-7.1.3/drivers/gpu/drm/amd/include/asic_reg/"
        "gca/gfx_8_0_d.h")
sys.path.insert(0, RAIZ + "/tools/rxre")

# El patron del oraculo.  Distinto del de rxre a proposito:  siCoinciden las dos
# lecturas,  el valor no depende de una sola regex.
ORACULO = re.compile(r'^#define\s+(mm[A-Za-z0-9_]+)\s+(0[xX][0-9a-fA-F]+|\d+)\s*$')


def diccionario():
    """{nombre: valor} del diccionario, leido linea a linea.  Sin redondeos."""
    vals = {}
    with open(RAIZ + "/" + DICC, encoding="utf-8", errors="replace") as f:
        for ln in f:
            m = ORACULO.match(ln.rstrip("\n"))
            if m:
                vals[m.group(1)] = int(m.group(2), 0)
    return vals


def consulta_rxre(nombre):
    """(valor_elegido, n_definiciones, estado, nota)  para un registro.

    Devuelve el valor que rxre DECLARA elegido,  no el que yo espere:  el
    proposito es comparar,  no forzar.
    """
    import cli
    buf = io.StringIO()
    argv = ["register", nombre, "--gfx", "gfx_8_0", "--json-only"]
    try:
        with contextlib.redirect_stdout(buf):
            try:
                cli.main(argv)
            except SystemExit:
                pass
    except Exception as e:                      # noqa: BLE001
        return None, 0, "ERROR", type(e).__name__
    crudo = buf.getvalue()
    if not crudo.strip():
        return None, 0, "VACIO", "sin salida"
    try:
        j = json.loads(crudo)
    except Exception:                            # noqa: BLE001
        return None, 0, "NO_JSON", "salida no parseable"
    st = j.get("status")
    res = j.get("results") or []
    if st != "ok":
        return None, len(res), st or "SIN_STATUS", ""
    if not res:
        return None, 0, "NOT_FOUND", "sin resultados"
    r = res[0]
    defs = r.get("definitions") or []
    elegido = r.get("chosen")
    if elegido is None:
        return None, len(defs), "SIN_CHOSEN", "%d definiciones sin elegir" % len(defs)
    if isinstance(elegido, dict):
        elegido = elegido.get("value", elegido.get("byte_offset"))
    return elegido, len(defs), "ok", ""


def veredicto(nombre, esperado):
    elegido, ndef, estado, nota = consulta_rxre(nombre)
    if estado != "ok":
        return {"registro": nombre, "esperado": esperado, "estado": estado,
                "n_definiciones": ndef, "nota": nota}
    if elegido != esperado:
        return {"registro": nombre, "esperado": esperado, "estado": "DIVERGE",
                "elegido": elegido, "n_definiciones": ndef,
                "delta": (elegido - esperado) if isinstance(elegido, int) else None}
    return {"registro": nombre, "esperado": esperado, "estado": "ok",
            "elegido": elegido, "n_definiciones": ndef}


def main():
    muta = "--mutacion" in sys.argv
    muestra = None
    for a in sys.argv:
        if a.startswith("--muestra"):
            muestra = int(a.split("=")[1])
    salida = None
    for a in sys.argv:
        if a.startswith("--salida="):
            salida = a.split("=", 1)[1]

    vals = diccionario()
    print("DENOMINADOR  %d entradas en %s" % (len(vals), DICC.split("/")[-1]),
          file=sys.stderr)

    nombres = sorted(vals)
    if muestra:
        # Seleccion declarada, no elegida por resultado:  elijo starting index
        # uniforme sobre la lista ORDENADA de nombres.  Reproducible.
        paso = max(1, len(nombres) // muestra)
        nombres = nombres[::paso][:muestra]
        print("MUESTRA      %d de %d,  paso uniforme sobre la lista ordenada"
              % (len(nombres), len(vals)), file=sys.stderr)

    destino = open(salida, "w", encoding="utf-8") if salida else sys.stdout
    t0 = time.time()
    tally = {}
    for i, n in enumerate(nombres, 1):
        esp = vals[n]
        if muta:
            esp = esp ^ 0x10          # el oraculo cambia;  rxre no
        r = veredicto(n, esp)
        tally[r["estado"]] = tally.get(r["estado"], 0) + 1
        destino.write(json.dumps(r, sort_keys=True) + "\n")
        destino.flush()
        if i % 50 == 0:
            print("  %4d/%d  %.0f s  %s" % (i, len(nombres), time.time() - t0,
                                              json.dumps(tally, sort_keys=True)),
                  file=sys.stderr)
    destino.close()
    print("FIN", json.dumps(tally, sort_keys=True), file=sys.stderr)


if __name__ == "__main__":
    main()