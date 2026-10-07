#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0
"""RXRE-015b · el productor no puede cambiar durante la medicion.

MEDIDO 2026-10-07: una corrida de 2.633 registros dio
    {ok:402, SIN_CHOSEN:975, error:1256}
y su procedencia decia
    reg_resolve_sha256 = 431b884b...
que no era ni el sha de HEAD (ec408d71...) ni el del disco cuando se
detecto (3952eb91...).  Otro autor estaba editando tools/reg_resolve.py
mientras la corrida lo media.  Los 1.256 `error` empiezan en la fila 1378 y
son consecutivos hasta el final:  no es ruido,  es una ventana.

La procedencia solo tomaba el sha UNA vez y AL FINAL,  de modo que describia
un estado del productor que no era el que produjo ninguna fila.  Eso es un
defecto mio de RXRE-013,  y se cierra aqui:

  · la huella se toma ANTES de la primera consulta
  · se comprueba cada 50 filas y otra vez al final
  · si cambia,  la corrida se marca INVALIDADA
  · si hay filas no medibles,  la corrida se marca INVALIDADA
  · `estado` y `motivos_de_invalidez` son parte de la MEDICION,  no un comentario

ORACLE INTERNO : una corrida con el productor mutado DEBE salir INVALIDADA.
ORACLE EXTERNO : una corrida limpia DEBE salir VALIDA,  y su reparto no debe
                 contener filas no medibles.
"""
import ast
import hashlib
import time
import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
TOOL_REL = "tools/rxre_cobertura_gfx8.py"
FUENTE = (ROOT / TOOL_REL).read_text(encoding="utf-8")


def _sha(p):
    return hashlib.sha256(open(p, "rb").read()).hexdigest()


def monta(dst: Path, fuente: str, tocar_productor: bool) -> None:
    """Arbol desechable.  `tocar_productor` edita reg_resolve.py a mitad."""
    shutil.copytree(ROOT / "tools/rxre", dst / "tools/rxre",
                    ignore=shutil.ignore_patterns("__pycache__", "github",
                                                  "storage"),
                    dirs_exist_ok=True)
    shutil.copy(ROOT / "tools/reg_resolve.py", dst / "tools/reg_resolve.py")
    (dst / "RESEARCH").symlink_to(ROOT / "RESEARCH")
    (dst / TOOL_REL).write_text(fuente, encoding="utf-8")
    if tocar_productor:
        # el productor cambia DESPUES de arrancar la corrida
        (dst / "GUION_CONCURRENTE.py").write_text("# marca de autor\n",
                                                  encoding="utf-8")
        p = dst / "tools/rxre/core/otro_autor.py"
        p.write_text("# el arbol de codigo cambio a mitad\n", encoding="utf-8")


def corre(fuente: str):
    ast.parse(fuente)
    with tempfile.TemporaryDirectory(dir="/tmp/opencode", prefix="cob13b-") as tmp:
        dst = Path(tmp)
        monta(dst, fuente, False)
        sal, met = dst / "c.jsonl", dst / "c.meta.json"
        p = subprocess.run(
            [sys.executable, "-B", str(dst / TOOL_REL), "--muestra=3",
             "--salida=" + str(sal), "--meta=" + str(met)],
            cwd=dst, capture_output=True, text=True, timeout=1200,
            env=dict(os.environ, PYTHONDONTWRITEBYTECODE="1"))
        meta = json.load(open(met, encoding="utf-8")) if met.is_file() else {}
        return p, meta


def main():
    print("=" * 74)
    print("RXRE-015b · el productor no puede cambiar durante la medicion")
    print("=" * 74)
    fallos = []
    n = 0

    def chk(nombre, ok, det=""):
        nonlocal n
        n += 1
        print("  [%s] %s" % ("OK " if ok else "NO ", nombre))
        if not ok:
            print("        %s" % str(det)[:400])
            fallos.append(nombre)

    # ── 1 · linea base: sin cambios, la corrida es VALIDA ───────────────
    p, meta = corre(FUENTE)
    chk("la corrida de linea base arranca", p.returncode == 0, p.stderr[-300:])
    chk("y se declara VALIDA", meta.get("estado") == "VALA"
        or meta.get("estado") == "VALIDA", meta.get("estado"))
    chk("sin filas no medibles", meta.get("filas_no_medibles") == 0,
        meta.get("filas_no_medibles"))
    chk("con motivo de invalidez vacio", not meta.get("motivos_de_invalidez"),
        meta.get("motivos_de_invalidez"))
    chk("la huella del productor se toma ANTES de consultar",
        "productor_al_inicio" in meta and "productor_al_final" in meta)
    chk("y las dos coinciden en una corrida limpia",
        meta.get("productor_al_inicio") == meta.get("productor_al_final"))
    chk("el sha del productor es el del fichero real de ese arbol",
        meta["productor_al_inicio"]["reg_resolve"] ==
        _sha(str(ROOT / "tools/reg_resolve.py")))
    chk("el reparto NO trae filas que no se puedan medir",
        not any(k in ("error", "ERROR", "NO_JSON", "VACIO", "SIN_STATUS")
                for k in (meta.get("reparto") or {})),
        meta.get("reparto"))

    # ── 2 · el productor cambia EN VUELO → INVALIDADA ────────────────────
    with tempfile.TemporaryDirectory(dir="/tmp/opencode", prefix="cob13d-") as tmp:
        dst = Path(tmp)
        monta(dst, FUENTE, False)
        sal, met = dst / "c.jsonl", dst / "c.meta.json"
        tool = str(dst / TOOL_REL)
        # se arranca con un productor,  y a los 1.5 s se edita el arbol
        proc = subprocess.Popen(
            [sys.executable, "-B", tool, "--muestra=3", "--salida=" + str(sal),
             "--meta=" + str(met)],
            cwd=dst, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True,
            env=dict(os.environ, PYTHONDONTWRITEBYTECODE="1"))
        import time
        time.sleep(1.5)
        (dst / "tools/rxre/core/otro_autor.py").write_text(
            "# el arbol cambio a mitad\n", encoding="utf-8")
        proc.wait(timeout=900)
        m2 = json.load(open(met, encoding="utf-8")) if met.is_file() else {}
        chk("con el productor cambiado en vuelo, la corrida se marca INVALIDADA",
            m2.get("estado") == "INVALIDADA", m2.get("estado"))
        chk("y nombra el motivo",
            "PRODUCTOR_CAMBIO_DURANTE_LA_CORRIDA" in
            (m2.get("motivos_de_invalidez") or []), m2.get("motivos_de_invalidez"))
        chk("las dos huellas son distintas y ambas quedan registradas",
            m2.get("productor_al_inicio") != m2.get("productor_al_final"),
            "%s vs %s" % (m2.get("productor_al_inicio", {}).get("rxre", "")[:10],
                          m2.get("productor_al_final", {}).get("rxre", "")[:10]))

    # ── 3 · mutaciones del guard,  una por una ──────────────────────────
    # Dos escenarios:  la corrida limpia y la corrida con el productor
    # cambiado EN VUELO.  Un mutante esta MUERTO si viola alguna asercion de
    # cualquiera de los dos.
    ASERCIONES_LIMPIA = [
        ("estado VALIDA", lambda m: m.get("estado") == "VALIDA"),
        ("sin motivos", lambda m: not m.get("motivos_de_invalidez")),
        ("sin filas no medibles", lambda m: m.get("filas_no_medibles") == 0),
        ("inicio == final", lambda m: m.get("productor_al_inicio") ==
         m.get("productor_al_final")),
        ("huella real", lambda m: m["productor_al_inicio"]["reg_resolve"] ==
         _sha(str(ROOT / "tools/reg_resolve.py"))),
        ("reparto medible", lambda m: not any(
            k in ("error", "ERROR", "NO_JSON", "VACIO", "SIN_STATUS")
            for k in (m.get("reparto") or {}))),
    ]
    ASERCIONES_DRIFT = [
        ("estado INVALIDADA", lambda m: m.get("estado") == "INVALIDADA"),
        ("motivo de drift", lambda m: "PRODUCTOR_CAMBIO_DURANTE_LA_CORRIDA"
         in (m.get("motivos_de_invalidez") or [])),
        ("fila del cambio localizada", lambda m:
         m.get("productor_cambio_en_fila") is not None),
        ("las dos huellas difieren", lambda m:
         m.get("productor_al_inicio") != m.get("productor_al_final")),
    ]

    MUT = {
        "M1_huella_inicial_falsa": (
            '    DRIFT["inicio"] = huella_productor(RAIZ)',
            '    DRIFT["inicio"] = {"reg_resolve": "x", "rxre": "x", '
            '"herramienta": "x"}'),
        "M2_comprobacion_periodica_suprimida": (
            '            ahora = huella_productor(RAIZ)\n'
            '            if ahora != DRIFT["inicio"]:',
            '            ahora = DRIFT["inicio"]\n'
            '            if False:'),
        "M3_invalidez_por_drift_suprimida": (
            '    if DRIFT["detectado"]:\n'
            '        invalidas.append("PRODUCTOR_CAMBIO_DURANTE_LA_CORRIDA")',
            '    if False:\n'
            '        invalidas.append("PRODUCTOR_CAMBIO_DURANTE_LA_CORRIDA")'),
        "M4_comprobacion_final_suprimida": (
            '    DRIFT["final"] = huella_productor(RAIZ)\n'
            '    if DRIFT["final"] != DRIFT["inicio"]:\n'
            '        DRIFT["detectado"] = True',
            '    DRIFT["final"] = DRIFT["inicio"]\n'
            '    if False:\n'
            '        DRIFT["detectado"] = True'),
        "M5_filas_no_medibles_no_invalidan": (
            '    if no_medibles:\n        invalidas.append("FILAS_NO_MEDIBLES")',
            '    if False:\n        invalidas.append("FILAS_NO_MEDIBLES")'),
        "M6_estado_siempre_valido": (
            '"estado": "VALIDA" if not invalidas else "INVALIDADA",',
            '"estado": "VALIDA",'),
        "M7_huella_del_productor_constante": (
            '"reg_resolve": _sha256(os.path.join(raiz, "tools/reg_resolve.py")),',
            '"reg_resolve": "NO_MEDIDO",'),
        "M8_arbol_rxre_no_se_mide": (
            '        "rxre": _arbol(raiz),',
            '        "rxre": "NO_MEDIDO",'),
        "M9_lineas_no_medibles_no_marcadas": (
            '        if r["estado"] in NO_MEDIBLE:\n'
            '            no_medibles += 1\n'
            '            r["no_medible"] = True',
            '        if False:\n'
            '            no_medibles += 1\n'
            '            r["no_medible"] = True'),
    }

    for nombre, (antes, despues) in MUT.items():
        n += 1
        c = FUENTE.count(antes)
        if c != 1:
            print("  INVALID %s: sitio count=%d" % (nombre, c))
            fallos.append(nombre)
            continue
        fuente = FUENTE.replace(antes, despues, 1)
        try:
            ast.parse(fuente)
        except SyntaxError as e:
            print("  KILLED   %-38s no compila (%s)" % (nombre, e.msg))
            continue
        violadas = []
        for etiqueta, aserciones, drift in (
                ("limpia", ASERCIONES_LIMPIA, False),
                ("drift", ASERCIONES_DRIFT, True)):
            with tempfile.TemporaryDirectory(dir="/tmp/opencode",
                                             prefix="mut13-") as tmp:
                dst = Path(tmp)
                monta(dst, fuente, False)
                sal, met = dst / "c.jsonl", dst / "c.meta.json"
                cmd = [sys.executable, "-B", str(dst / TOOL_REL), "--muestra=3",
                       "--salida=" + str(sal), "--meta=" + str(met)]
                env = dict(os.environ, PYTHONDONTWRITEBYTECODE="1")
                if drift:
                    proc = subprocess.Popen(cmd, cwd=dst,
                                            stdout=subprocess.PIPE,
                                            stderr=subprocess.PIPE, text=True,
                                            env=env)
                    time.sleep(1.5)
                    (dst / "tools/rxre/core/otro_autor.py").write_text(
                        "# cambio en vuelo\n", encoding="utf-8")
                    proc.wait(timeout=900)
                else:
                    subprocess.run(cmd, cwd=dst, capture_output=True,
                                   text=True, timeout=900, env=env)
                mm = json.load(open(met, encoding="utf-8")) \
                    if met.is_file() else {}
            for nombre_a, fn in aserciones:
                if not fn(mm):
                    violadas.append("%s/%s" % (etiqueta, nombre_a))
        if violadas:
            print("  KILLED   %-38s %s" % (nombre, ", ".join(violadas[:2])))
        else:
            print("  SURVIVED %-38s <-- hueco real del guard" % nombre)
            fallos.append(nombre)

    print("\n%d checks · %s" % (n, "TODO VERDE" if not fallos
                                else "%d FALLOS: %s" % (len(fallos),
                                                        ", ".join(fallos[:5]))))
    return 1 if fallos else 0


if __name__ == "__main__":
    sys.exit(main())