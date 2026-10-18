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
import os
import re
import sys
import time
import hashlib
import datetime
import subprocess
import contextlib

# ── RAIZ ────────────────────────────────────────────────────────────────────
# NO es una ruta absoluta escondida.  Se deriva de donde vive ESTE fichero, de
# modo que la medicion no pueda ejecutarse contra un arbol que no sea el que
# contiene la herramienta que la produce.  Se puede forzar de forma explicita
# con --raiz= o con RXRE_ROOT,  y si se fuerza queda en la procedencia.
#
# HISTORICO: esto estaba en otro arbol del proyecto, un
# arbol distinto con otro RXRE (sin core/relations.py,  y con el reg_resolve
# que inversaba la unidad).  El artefacto de esa corrida es
# ARTIFACT_INVALIDADO_PARA_SEMANTICA_VIGENTE.
RAIZ_DEFECTO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _raiz(argv):
    for a in argv:
        if a.startswith("--raiz="):
            return os.path.abspath(a.split("=", 1)[1]), "argv:--raiz"
    ent = os.environ.get("RXRE_ROOT")
    if ent:
        return os.path.abspath(ent), "env:RXRE_ROOT"
    return RAIZ_DEFECTO, "derivada_de___file__"


RAIZ, ORIGEN_RAIZ = _raiz(sys.argv)
DICC = ("RESEARCH/working/linux-7.1.3/drivers/gpu/drm/amd/include/asic_reg/"
        "gca/gfx_8_0_d.h")
sys.path.insert(0, RAIZ + "/tools/rxre")

# La UNIDAD que se compara.  No es una opinion de este script:  la declara
# reg_resolve y la confirma el accessor del kernel (amdgpu_reg_access.c:
# writel(v, rmmio + (reg * 4)),  @reg: dword aligned register offset).  El
# valor del #define ES el indice dword;  el byte offset se DERIVA por * 4.
# Prohibido >>2:  aplicado a un indice produce el indice de OTRO registro.
UNIDAD = "dword_register_index"
DERIVACION_BYTE = "byte_offset = valor * 4"
FUENTE_UNIDAD = ("drivers/gpu/drm/amd/amdgpu/amdgpu_reg_access.c",
                 "amdgpu_device_rreg/wreg", "writel(v, rmmio + (reg * 4))")

# El patron del oraculo.  Distinto del de rxre a proposito:  siCoinciden las dos
# lecturas,  el valor no depende de una sola regex.
ORACULO = re.compile(r'^#define\s+(mm[A-Za-z0-9_]+)\s+(0[xX][0-9a-fA-F]+|\d+)\s*$')

# Contador del fallback DEAD.  chosen es el HIT del #define
# {file, rel, line, value, text}:  byte_offset vive en el objeto out hermano y
# nunca estuvo dentro de chosen,  asi que el default no puede dispararse.
# Se cuenta igualmente para que la afirmacion "no se ejecuta" sea una
# MEDICION y no una lectura del codigo.
FALLBACK_DEAD = {"disparado": 0, "registros": 0}


def diccionario():
    """{nombre: valor} del diccionario, leido linea a linea.  Sin redondeos."""
    vals = {}
    with open(RAIZ + "/" + DICC, encoding="utf-8", errors="replace") as f:
        for ln in f:
            m = ORACULO.match(ln.rstrip("\n"))
            if m:
                vals[m.group(1)] = int(m.group(2), 0)
    return vals


def _sha256(path):
    if not os.path.isfile(path):
        return "NOT_FOUND"
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for bloque in iter(lambda: f.read(65536), b""):
            h.update(bloque)
    return h.hexdigest()


def _git_head(raiz):
    p = subprocess.run(["git", "-C", raiz, "rev-parse", "HEAD"],
                       capture_output=True, text=True)
    return p.stdout.strip() if p.returncode == 0 else "NO_ES_REPO_GIT"


def _git_dirty(raiz):
    p = subprocess.run(["git", "-C", raiz, "status", "--porcelain",
                        "--", "tools/reg_resolve.py", "tools/rxre/"],
                       capture_output=True, text=True)
    return bool(p.stdout.strip())


def huella_productor(raiz):
    """Identidad del PRODUCTOR en este instante.

    MEDIDO 2026-10-07: una corrida de 2.633 registros produjo 1.256 filas
    `error` seguidas,  desde la fila 1378 hasta el final,  porque otro autor
    estaba editando tools/reg_resolve.py mientras la corrida lo moria.  El
    sha se escribia UNA vez  y al FINAL  (api de meta),  asi que decia
    431b884b  --  que no era ni el de HEAD  ni el del disco.  La procedencia
    no podia detectslo porque se media despues de que el cambio ocurriera.

    Por eso la huella se toma ANTES de la primera consulta,  se comprueba cada
    50 filas  y se vuelve a tomar al final.  Si cambia,  la corrida se declara
    INVALIDADA y no se presenta un reparto como si fuera una medicion.
    """
    return {
        "reg_resolve": _sha256(os.path.join(raiz, "tools/reg_resolve.py")),
        "rxre": _arbol(raiz),
        "herramienta": _sha256(os.path.abspath(__file__)),
    }


def _arbol(raiz):
    """Digest barato del arbol de codigo que RXRE ejecuta:  ruta+tam+mtime."""
    h = hashlib.sha256()
    base = os.path.join(raiz, "tools/rxre")
    for dirpath, dirnames, filenames in os.walk(base):
        dirnames[:] = sorted(d for d in dirnames
                             if d not in ("__pycache__", "github", "storage"))
        for fn in sorted(filenames):
            if not fn.endswith(".py"):
                continue
            p = os.path.join(dirpath, fn)
            try:
                st = os.stat(p)
            except OSError:
                continue
            h.update(("%s|%d|%d\n" % (os.path.relpath(p, base), st.st_size,
                                     st.st_mtime_ns)).encode())
    return h.hexdigest()


DRIFT = {"detectado": False, "primera_fila": None, "inicio": None, "final": None}
NO_MEDIBLE = ("error", "ERROR", "NO_JSON", "VACIO", "SIN_STATUS")


def verifica_arbol():
    """El RXRE importado tiene que ser el de RAIZ.  Falla si no lo es.

    Sin esto, cambiar RAIZ no cambiaria el RXRE medido:  sys.path ya tenia
    entradas,  y el arbol equivocado Podia ganarle la resolucion de 'cli'.
    """
    esperado = os.path.abspath(os.path.join(RAIZ, "tools/rxre/cli.py"))
    if not os.path.isfile(esperado):
        raise SystemExit(
            "INVALID_TREE: bajo %s no hay tools/rxre/cli.py.\n"
            "No hay RXRE que medir:  medir aqui seria medir otro arbol."
            % RAIZ)
    if not os.path.isfile(os.path.join(RAIZ, DICC)):
        raise SystemExit(
            "INVALID_TREE: bajo %s no existe el diccionario %s.\n"
            "El denominador no lo elige esta herramienta:  si falta, no se "
            "mide." % (RAIZ, DICC))
    if not os.path.isfile(os.path.join(RAIZ, "tools/reg_resolve.py")):
        raise SystemExit(
            "INVALID_TREE: bajo %s no existe tools/reg_resolve.py.\n"
            "Es el productor que se esta midiendo:  sin el, la procedencia "
            "no se puede escribir y la cifra no tiene a quien atribuirse."
            % RAIZ)
    import cli
    aqui = os.path.abspath(cli.__file__)
    if aqui != esperado:
        raise SystemExit(
            "INVALID_TREE: el modulo 'cli' importado es\n  %s\nesperado\n  %s\n"
            "La medicion seria de otro arbol." % (aqui, esperado))
    import core.dispatch as _d
    return {
        "cli_importado": aqui,
        "dispatch_root": _d.ROOT,
        "dispatch_tools": _d.TOOLS,
    }


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
        if "value" in elegido:
            elegido = elegido["value"]          # indice dword del #define
        else:
            # Rama que no se ha ejecutado nunca.  Se deja el codigo,  se cuenta.
            FALLBACK_DEAD["disparado"] += 1
            elegido = elegido.get("byte_offset")
    FALLBACK_DEAD["registros"] += 1
    return elegido, len(defs), "ok", ""


def veredicto(nombre, esperado):
    elegido, ndef, estado, nota = consulta_rxre(nombre)
    if estado != "ok":
        return {"registro": nombre, "esperado": esperado, "estado": estado,
                "n_definiciones": ndef, "nota": nota, "unidad": UNIDAD}
    # La unidad se DECLARA por registro,  no se deduce del numero:  el mismo
    # entero significa otra cosa segun la unidad,  y el artefacto tiene que
    # poder distinguirlo sin mirar el codigo que lo produjo.
    fila = {"registro": nombre, "esperado": esperado, "estado": "ok",
            "elegido": elegido, "n_definiciones": ndef, "unidad": UNIDAD}
    if isinstance(elegido, int):
        fila["byte_offset_derivado"] = elegido * 4
        fila["derivacion"] = DERIVACION_BYTE
    else:
        return {"registro": nombre, "esperado": esperado, "estado": "DIVERGE",
                "elegido": elegido, "n_definiciones": ndef,
                "delta": None, "unidad": UNIDAD}
    if elegido != esperado:
        fila["estado"] = "DIVERGE"
        fila["delta"] = elegido - esperado
    return fila


def main():
    muta = "--mutacion" in sys.argv
    muestra = None
    for a in sys.argv:
        if a.startswith("--muestra"):
            muestra = int(a.split("=")[1])
    salida = None
    meta_salida = None
    for a in sys.argv:
        if a.startswith("--salida="):
            salida = a.split("=", 1)[1]
        if a.startswith("--meta="):
            meta_salida = a.split("=", 1)[1]

    arbol = verifica_arbol()

    vals = diccionario()
    print("DENOMINADOR  %d entradas en %s" % (len(vals), DICC.split("/")[-1]),
          file=sys.stderr)
    print("RAIZ         %s  (origen: %s)" % (RAIZ, ORIGEN_RAIZ), file=sys.stderr)
    print("RXRE         %s" % arbol["cli_importado"], file=sys.stderr)
    print("UNIDAD       %s   byte = valor * 4" % UNIDAD, file=sys.stderr)

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
    timestamp = datetime.datetime.now().astimezone().isoformat()
    t_call = sys.argv[:]
    DRIFT["inicio"] = huella_productor(RAIZ)
    print("PRODUCTOR   reg_resolve=%s  rxre=%s"
          % (DRIFT["inicio"]["reg_resolve"][:12], DRIFT["inicio"]["rxre"][:12]),
          file=sys.stderr)
    tally = {}
    no_medibles = 0
    for i, n in enumerate(nombres, 1):
        esp = vals[n]
        if muta:
            esp = esp ^ 0x10          # el oraculo cambia;  rxre no
        r = veredicto(n, esp)
        if r["estado"] in NO_MEDIBLE:
            no_medibles += 1
            r["no_medible"] = True
        tally[r["estado"]] = tally.get(r["estado"], 0) + 1
        destino.write(json.dumps(r, sort_keys=True) + "\n")
        destino.flush()
        if i % 50 == 0:
            ahora = huella_productor(RAIZ)
            if ahora != DRIFT["inicio"]:
                DRIFT["detectado"] = True
                DRIFT["primera_fila"] = i
                print("  !! PRODUCTOR CAMBIADO EN VUELO en la fila %d" % i,
                      file=sys.stderr)
                print("     inicio %s" % DRIFT["inicio"], file=sys.stderr)
                print("     ahora  %s" % ahora, file=sys.stderr)
            print("  %4d/%d  %.0f s  %s" % (i, len(nombres), time.time() - t0,
                                              json.dumps(tally, sort_keys=True)),
                  file=sys.stderr)
    destino.close()
    DRIFT["final"] = huella_productor(RAIZ)
    if DRIFT["final"] != DRIFT["inicio"]:
        DRIFT["detectado"] = True
    print("FIN", json.dumps(tally, sort_keys=True), file=sys.stderr)

    reg_resolve = os.path.join(RAIZ, "tools/reg_resolve.py")
    # El estado de una corrida es parte de la MEDICION,  no un comentario.
    # MEDIDO:  una corrida dio {ok:402, SIN_CHOSEN:975, error:1256}  y su
    # procedencia describia un productor que no era ninguno de los que
    # existen.  Sin este campo,  un reparto con 48 % de filas no medibles
    # se lee como una cifra de cobertura.
    invalidas = []
    if DRIFT["detectado"]:
        invalidas.append("PRODUCTOR_CAMBIO_DURANTE_LA_CORRIDA")
    if no_medibles:
        invalidas.append("FILAS_NO_MEDIBLES")
    if invalidas:
        print("INVALIDA    %s  ->  esta corrida NO es una medicion"
              % ", ".join(invalidas), file=sys.stderr)
    meta = {
        "artefacto": os.path.abspath(salida) if salida else "stdout",
        "timestamp": timestamp,
        "estado": "VALIDA" if not invalidas else "INVALIDADA",
        "motivos_de_invalidez": invalidas,
        "filas_no_medibles": no_medibles,
        "productor_al_inicio": DRIFT["inicio"],
        "productor_al_final": DRIFT["final"],
        "productor_cambio_en_fila": DRIFT["primera_fila"],
        "producer_command": " ".join([sys.executable, os.path.basename(__file__)]
                                     + t_call),
        "source_root": RAIZ,
        "source_root_origen": ORIGEN_RAIZ,
        "source_git_head": _git_head(RAIZ),
        "source_git_dirty_en_tools": _git_dirty(RAIZ),
        "rxre_importado": arbol["cli_importado"],
        "dispatch_root": arbol["dispatch_root"],
        "reg_resolve_path": reg_resolve,
        "reg_resolve_sha256": _sha256(reg_resolve),
        "producer_sha256": _sha256(os.path.abspath(__file__)),
        "unit_semantics": {
            "valor_#define": UNIDAD,
            "byte_offset": DERIVACION_BYTE,
            "prohibido": "valor >> 2  (produce el indice de OTRO registro)",
            "fuente": FUENTE_UNIDAD,
            "alcance": "DERIVED_FROM_ACCESSOR, no observado en hardware",
        },
        "generation": "gfx_8_0",
        "denominador": {"ruta": DICC, "entradas": len(vals), "elegido_por": "el diccionario"},
        "alcance_ejecutado": len(nombres),
        "muestra": bool(muestra),
        "mutacion_oraculo": muta,
        "segundos": round(time.time() - t0, 1),
        "reparto": tally,
        "fallback_byte_offset": {
            "runtime_path": "DEAD / NOT_REACHED",
            "disparado": FALLBACK_DEAD["disparado"],
            "registros_con_chosen_dict": FALLBACK_DEAD["registros"],
            "por_que": ("chosen es el HIT del #define {file, rel, line, value, "
                        "text};  byte_offset vive en el objeto out hermano y "
                        "nunca estuvo dentro de chosen"),
        },
        "estado_herramienta": "SELF_TESTED",
    }
    if meta_salida:
        with open(meta_salida, "w", encoding="utf-8") as f:
            json.dump(meta, f, indent=2, sort_keys=True, ensure_ascii=False)
            f.write("\n")
        print("META         %s" % meta_salida, file=sys.stderr)
    print("PROCEDENCIA  %s" % json.dumps(
        {k: meta[k] for k in ("source_root", "source_git_head",
                              "reg_resolve_sha256")}, sort_keys=True),
        file=sys.stderr)
    return meta


if __name__ == "__main__":
    main()