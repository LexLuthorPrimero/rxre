#!/usr/bin/env python3
"""RXRE-005. El FREEZE reproducible: que RXRE uso exactamente la IA.

POR QUE ESTE SCRIPT Y NO UN `git rev-parse` Y UN `sha256sum`.

Porque la pregunta del §4 es "¿QUE RXRE UTILIZO EXACTAMENTE LA IA?", y esa
pregunta tiene dos trampas:

1. **El arbol esta sucio y va a estarlo.** Hay 140 ficheros modificados, y una
   parte son de OTRA sesion. `git rev-parse HEAD` no identifica lo que se
   ejecuto: identifica el ultimo commit, y el codigo ejecutado no estaba en el.
   Un freeze por commit seria un freeze de otra cosa.

2. **El backend que corre no es el repo que se audito.** MEDIDO: el repo de
   rizin es `v0.10.0-dev` (commit d14c3fac) y el binario en PATH es 0.7.4. Un
   freeze que solo guarde el commit esta affirmando que se ejecuto codigo que
   no se ejecuto.

    la identidad de un freeze son dos cosas, no una

Asi que el freeze mide las DOS, por separado, y ademas mide lo que de verdad
determina el comportamiento: los ficheros de RXRE, no el arbol entero.

QUE SE ESCRIBE Y DONDE.

`docs/RXRE-005-FREEZE.json`, con un `freeze_id` derivado del contenido. Un
freeze cuyo hash no depende de sus propios datos no es un freeze: es una fecha.

Y el hash de un freeze calculado sobre si mismo no puede ser su propio hash.
Por eso `freeze_id` se calcula sobre el contenido SIN `freeze_id`, y por eso
`verificar()` recalcula del mismo modo. Es la misma disciplina que el
`result_id` de F6, aplicada a un artefacto que se describe a si mismo.
"""
from __future__ import annotations

import hashlib
import json
import os
import platform
import subprocess
import sys
import time
from typing import Any, Dict, List

HERE = os.path.dirname(os.path.abspath(__file__))
PKG = os.path.abspath(os.path.join(HERE, ".."))
ROOT = os.path.abspath(os.path.join(PKG, "..", ".."))
FREEZE = os.path.join(PKG, "docs", "RXRE-005-FREEZE.json")

#: Ficheros que DEFINEN el comportamiento de RXRE. No se hashea todo `tools/`:
#: ese directorio tiene 1600+ ficheros, la mitad corpus de terceros que no
#: participa. Hashear el arbol entero haria el freeze insensible a lo unico que
#: importa (el codigo de RXRE) y sensible a lo que no (un README de un backend).
FICHEROS_RXRE = [
    "api/machine.py", "api/request.py", "api/envelope.py",
    "backends/contract.py", "backends/registry.py", "backends/dispatch.py",
    "backends/decision.json", "backends/adapters/rz_inspect.py",
    "core/capabilities.py", "core/engine.py", "core/normalize.py",
    "core/store.py",
    "commands/query.py", "commands/handlers.py",
    "docs/RXRE_PUBLIC_CONTRACT.md", "docs/AI_QUICKSTART.md",
    "fixtures/bin/MANIFEST.json", "fixtures/bin/rxre_min.elf",
]

#: Suites. Un freeze sin suites no dice si el estado estaba verde.
SUITES = ["test_rxre", "test_rxre002", "test_fixtures", "test_rxre003",
          "test_backends004", "test_fixture004", "test_dispatch004",
          "test_field005", "test_mutations003"]

#: Los cuatro repositorios externos. Se miden por separado del runtime.
REPOS = ["rizin", "rz-ghidra", "angr", "radare2"]

#: Binarios que RXRE puede ejecutar. `tool_version` NO basta (ver cabecera).
BINARIOS = ["rizin", "rz-bin", "radare2", "rabin2"]


def _sha_de_fichero(ruta: str) -> str:
    h = hashlib.sha256()
    with open(ruta, "rb") as fh:
        for bloque in iter(lambda: fh.read(1 << 16), b""):
            h.update(bloque)
    return h.hexdigest()


def _git(*args, cwd: str = ROOT) -> str:
    try:
        p = subprocess.run(["git"] + list(args), cwd=cwd,
                           capture_output=True, text=True, timeout=60)
        return (p.stdout or "").strip()
    except (OSError, subprocess.TimeoutExpired):
        return ""


def _version_de(bin_: str) -> Dict[str, Any]:
    """La version REAL, ejecutando el binario. Un valor declarado no vale."""
    import shutil
    ruta = shutil.which(bin_)
    if not ruta:
        return {"disponible": False,
                "motivo": "no esta en PATH: el producer no se puede verificar"}
    ver = ""
    flag = ""
    for f in ("-v", "-V", "--version"):
        try:
            p = subprocess.run([ruta, f], capture_output=True, text=True,
                               timeout=30)
        except (OSError, subprocess.TimeoutExpired):
            continue
        txt = ((p.stdout or "") + (p.stderr or "")).strip()
        if txt:
            ver, flag = txt.splitlines()[0][:120], f
            break
    return {"disponible": True, "ruta": ruta,
            "tool_version": ver, "flag": flag,
            "verificada": bool(ver),
            "sha256_del_binario": _sha_de_fichero(ruta)}


def estado_git() -> Dict[str, Any]:
    """El commit NO identifica lo ejecutado. Se guardan los tres datos."""
    sucios = _git("status", "--porcelain").splitlines()
    mios = [x for x in sucios
            if x[3:].startswith("tools/rxre/") or "06-INGENIERIA-INVERSA" in x]
    otros = [x for x in sucios if x not in mios]
    return {
        "commit": _git("rev-parse", "HEAD"),
        "branch": _git("rev-parse", "--abbrev-ref", "HEAD"),
        "sucio": bool(sucios),
        "n_modificados": len(sucios),
        "n_modificados_de_rxre": len(mios),
        "n_modificados_de_otra_sesion": len(otros),
        "aviso": "el arbol esta SUCIO y el codigo ejecutado NO esta en el "
                 "commit. El commit NO identifica esta ejecucion; lo que la "
                 "identifica son los hashes de FICHEROS de mas abajo. Los "
                 "ficheros de otra sesion NO se tocan y NO forman parte de "
                 "RXRE.",
    }


def corpora() -> Dict[str, Any]:
    """El corpus sobre el que se investiga. Sin esto, el freeze no es una
    investigacion: es una ejecucion."""
    out = {}
    for nombre, rel in (("working", "RESEARCH/working/linux-7.1.3"),
                        ("kernelbuild", "RESEARCH/kernelbuild/linux-7.1.3")):
        ruta = os.path.join(ROOT, rel)
        if not os.path.isdir(ruta):
            out[nombre] = {"presente": False}
            continue
        n = 0
        newest = 0.0
        for dp, _dn, fn in os.walk(ruta):
            n += len(fn)
            for f in fn:
                try:
                    mt = os.path.getmtime(os.path.join(dp, f))
                    newest = max(newest, mt)
                except OSError:
                    pass
        out[nombre] = {"presente": True, "ruta": rel, "n_ficheros": n,
                       "mtime_mas_reciente": int(newest)}
    return out


def hardware() -> Dict[str, Any]:
    """Solo LECTURA. No se abre ningun dispositivo, no se escribe nada."""
    d = {"nota": "RXRE-005 es SOFTWARE/ESTATICO. No hay MMIO, no hay "
                "escrituras PCI, no se toca 0000:00:02.0."}
    try:
        with open("/proc/cpuinfo", encoding="utf-8") as fh:
            for ln in fh:
                if ln.startswith("model name"):
                    d["cpu"] = ln.split(":", 1)[1].strip()
                    break
    except OSError:
        d["cpu"] = "NOT_DETERMINED"
    fb = "/sys/class/graphics/fb0/device/uevent"
    if os.path.exists(fb):
        try:
            txt = open(fb, encoding="utf-8").read()
            for k in ("DRIVER", "PCI_SLOT_NAME"):
                for ln in txt.splitlines():
                    if ln.startswith(k + "="):
                        d["fb0_" + k.lower()] = ln.split("=", 1)[1]
        except OSError:
            pass
    d["frontera_dura"] = "0000:00:02.0 (Intel iGPU): NUNCA se toca"
    return d


def construir() -> Dict[str, Any]:
    ficheros = {}
    faltan = []
    for rel in FICHEROS_RXRE:
        ruta = os.path.join(PKG, rel)
        if not os.path.isfile(ruta):
            faltan.append(rel)
            continue
        ficheros[rel] = {"sha256": _sha_de_fichero(ruta),
                         "bytes": os.path.getsize(ruta)}
    suites = {}
    for s in SUITES:
        ruta = os.path.join(PKG, "tests", s + ".py")
        suites[s] = (_sha_de_fichero(ruta)
                     if os.path.isfile(ruta) else "AUSENTE")
    repos = {}
    for r in REPOS:
        ruta = os.path.join(PKG, "github", r)
        if not os.path.isdir(ruta):
            repos[r] = {"presente": False}
            continue
        repos[r] = {"presente": True,
                    "commit": _git("rev-parse", "HEAD", cwd=ruta),
                    "branch": _git("rev-parse", "--abbrev-ref", "HEAD", cwd=ruta),
                    "dirty": bool(_git("status", "--porcelain", cwd=ruta))}
    d = {
        "generado": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
        "que_es": "Identidad de UNA ejecucion de RXRE. No es un numero de "
                  "version: es el estado exacto del arbol y de los producers.",
        "entorno": {
            "python": sys.version.split()[0],
            "implementacion": platform.python_implementation(),
            "os": "%s %s" % (platform.system(), platform.release()),
            "arch": platform.machine(),
        },
        "git": estado_git(),
        "ficheros_rxre": ficheros,
        "ficheros_faltantes": faltan,
        "hash_ficheros": sha_de_mapa({k: v["sha256"]
                                      for k, v in ficheros.items()}),
        "suites": suites,
        "hash_suites": sha_de_mapa(suites),
        "repos_adquiridos": repos,
        "binarios_runtime": {b: _version_de(b) for b in BINARIOS},
        "corpus": corpora(),
        "hardware": hardware(),
        "notas_de_lectura": [
            "commit y hash de ficheros son cosas DISTINTAS: el arbol esta "
            "sucio y el commit no identifica lo ejecutado.",
            "repository_commit y tool_version son cosas DISTINTAS: el repo de "
            "rizin es v0.10.0-dev y el binario en PATH es 0.7.4.",
            "los ficheros modificados de otra sesion NO son parte de RXRE y no "
            "entran en hash_ficheros.",
        ],
    }
    d["freeze_id"] = sha_de_mapa(
        {k: d[k] for k in ("entorno", "git", "ficheros_rxre", "suites",
                           "repos_adquiridos", "binarios_runtime")})
    return d


def sha_de_mapa(m: Dict[str, Any]) -> str:
    """Hash de un mapa, ordenando las claves.

    Sin `sort_keys`, el hash depende del orden de insercion de un dict, y dos
    freezes del mismo estado podrian dar identificadores distintos. Un
    identificador que depende del orden no identifica.
    """
    return hashlib.sha256(
        json.dumps(m, sort_keys=True, default=str).encode("utf-8")
    ).hexdigest()


def verificar() -> Dict[str, Any]:
    """¿El freeze sigue describiendo el estado actual? Detecta DERIVA."""
    if not os.path.isfile(FREEZE):
        return {"estado": "SIN_FREEZE", "ruta": FREEZE}
    try:
        guardado = json.load(open(FREEZE, encoding="utf-8"))
    except (OSError, ValueError) as e:
        return {"estado": "FREEZE_ILEGIBLE", "error": str(e)}
    ahora = construir()
    deriva = []
    for rel, info in ahora["ficheros_rxre"].items():
        antes = (guardado.get("ficheros_rxre") or {}).get(rel, {})
        if antes.get("sha256") != info["sha256"]:
            deriva.append({"fichero": rel, "freeze": antes.get("sha256", "?")[:12],
                           "ahora": info["sha256"][:12]})
    nuevos = sorted(set(ahora["ficheros_rxre"]) - set(guardado.get("ficheros_rxre") or {}))
    binarios = {}
    for b, info in ahora["binarios_runtime"].items():
        a = ((guardado.get("binarios_runtime") or {}).get(b) or {})
        if a.get("sha256_del_binario") != info.get("sha256_del_binario"):
            binarios[b] = {"freeze": a.get("tool_version", "?")[:40],
                           "ahora": info.get("tool_version", "?")[:40]}
    return {
        "estado": "SIN_DERIVA" if not deriva and not nuevos and not binarios
        else "DERIVA_DETECTADA",
        "freeze_id": guardado.get("freeze_id"),
        "freeze_id_actual": ahora["freeze_id"],
        "ficheros_modificados": deriva,
        "ficheros_nuevos": nuevos,
        "binarios_cambiados": binarios,
        "nota": "DERIVA_DETECTADA no es un fallo del freeze: es el freeze "
                "funcionando. Significa que el codigo cambio DESPUES de "
                "congelar, y que por tanto una medida hecha ahora no es "
                "comparable con una medida hecha antes.",
    }


def escribir() -> str:
    d = construir()
    os.makedirs(os.path.dirname(FREEZE), exist_ok=True)
    with open(FREEZE, "w", encoding="utf-8") as fh:
        json.dump(d, fh, indent=2, sort_keys=True, ensure_ascii=False)
        fh.write("\n")
    return d["freeze_id"]


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else "verificar"
    if cmd == "escribir":
        fid = escribir()
        print("FREEZE ESCRITO  freeze_id=%s" % fid)
        d = json.load(open(FREEZE, encoding="utf-8"))
        print("  commit        : %s (SUCIO=%s, %d ficheros, %d de otra sesion)"
              % (d["git"]["commit"][:12], d["git"]["sucio"],
                 d["git"]["n_modificados"], d["git"]["n_modificados_de_otra_sesion"]))
        print("  hash ficheros : %s (%d ficheros de RXRE)"
              % (d["hash_ficheros"][:16], len(d["ficheros_rxre"])))
        print("  hash suites   : %s (%d suites)" % (d["hash_suites"][:16],
                                                   len(d["suites"])))
        print("  corpus        : %s" % {k: (v.get("n_ficheros")
                                           if v.get("presente") else "AUSENTE")
                                        for k, v in d["corpus"].items()})
        for b, i in d["binarios_runtime"].items():
            print("  %-9s : %s" % (b, i.get("tool_version", i.get("motivo"))[:52]))
    elif cmd == "verificar":
        r = verificar()
        print("FREEZE %s" % r["estado"])
        for k in ("ficheros_modificados", "ficheros_nuevos", "binarios_cambiados"):
            if r.get(k):
                print("  %s: %s" % (k, r[k]))
        print("  %s" % r.get("nota", ""))
    else:
        print(__doc__)
        sys.exit(2)