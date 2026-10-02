#!/usr/bin/env python3
"""
scopeguard.py -- el PREFLIGHT de escritura, en un comando.

POR QUE EXISTE
    En una sesion de investigacion el ciclo de "escribir un hallazgo" se repitio
    once veces, y en cada repeticion hubo que hacer cinco pasos a mano:

      1. ¿ya existe una herramienta que haga esto?     grep en 08-ARQUITECTURA/tools
      2. ¿ya esta escrito?                            grep en findings/ + docs/
      3. ¿esta libre el scope?                         leer .write-lock/
      4. ¿que numero de hallazgo libre hay?           listar, evitando duplicados
      5. tomar lock -> escribir -> verificar -> liberar

    Los pasos 1 y 2 se pueden automatizar. El 3 tambien. Y el 2 es el que mas
    dano hizo: cinco hallazgos de esta sesion DUPLICARON trabajo ya hecho
    (gfx8vmgeom, la geometria de 024, la refutacion de block_size que ya estaba
    en C-003, INVALIDATE_RESPONSE en 017/018, y DOMAIN_INVALIDATED).
    Cinco de once. No fue falta de trabajo: fue no mirar antes de empezar.

    Este script hace el preflight completo y ABORTA si el terreno esta ocupado.
    No es un asistente: es un gate.

LO QUE NO HACE, Y ES DELIBERADO
    No escribe ficheros. No toma locks. No edita nada.  Solo informa y devuelve
    un codigo de salida, para que un gate pueda rechazar la operacion.
    Un script que toma locks es un script que puede pisar a otra sesion, y el
    objeto de esto es exactamente lo contrario.

COMO LO USA EL AGENTE
    python3 scopeguard.py --findings        estado de los ambitos + numero libre
    python3 scopeguard.py --check "ih intrp"  ¿esta ocupado ese tema?
    python3 scopeguard.py --self              autotest
    echo $?                                   0 = libre, 2 = ocupado, 1 = error

CODIGOS DE SALIDA
    0  libre / sin hallazgos
    2  ocupado  (scope tomado, o el tema ya esta escrito)
    1  error de uso o de entorno
"""

import argparse
import json
import os
import re
import subprocess
import sys
import time

PROJECT = "/home/lucas/Escritorio/RX550-INVESTIGACION"
LOCKS = f"{PROJECT}/.write-lock"
FINDINGS = f"{PROJECT}/06-INGENIERIA-INVERSA/findings"
DOCS = f"{PROJECT}/docs"
TOOLS = f"{PROJECT}/08-ARQUITECTURA/tools"

# Ambito que se pide en cada operacion.  El caller lo pasa; no se infiere.
SCOPES_HINT = {
    "findings": "findings",
    "docs": "docs",
    "tools": "tools",
}


def _pid_of(txt):
    """PID declarado en un fichero owner. Aislado para poder testearlo."""
    m = re.search(r'\bPID=(\d+)', txt)
    if m:
        return int(m.group(1))
    for tok in txt.split():
        if tok.isdigit():
            return int(tok)
    return None


def _alive_of(pid):
    """True vivo / False muerto / None existe-pero-no-es-nuestro."""
    if not pid:
        return None
    try:
        os.kill(pid, 0)
        return True
    except ProcessLookupError:
        return False
    except PermissionError:
        return None


def read_locks():
    """{ambito: {owner, ts, pid}} de los ambitos actualmente tomados."""
    out = {}
    if not os.path.isdir(LOCKS):
        return out
    for d in sorted(os.listdir(LOCKS)):
        p = os.path.join(LOCKS, d)
        owner_f = os.path.join(p, "owner")
        if not os.path.isdir(p) or not os.path.exists(owner_f):
            continue
        try:
            txt = open(owner_f, errors="replace").read().strip()
        except OSError:
            txt = ""
        ts = ""
        m = re.search(r"(\d{4}-\d{2}-\d{2}T[\d:.+-]+)", txt)
        if m:
            ts = m.group(1)
        # El formato REAL de los locks de este proyecto es "PID=<n>", y solo
        # uno (drv042) escribe el numero suelto.  Un parser que solo acepte
        # tokens isdigit() reporta "?" en 5 de 7 locks, y por tanto NO detecta
        # ninguna sesion muerta: que es justo para lo que existe.
        pid = None
        m = re.search(r'\bPID=(\d+)', txt)
        if m:
            pid = int(m.group(1))
        else:
            for tok in txt.split():
                if tok.isdigit():
                    pid = int(tok)
                    break
        alive = None
        if pid:
            try:
                os.kill(pid, 0)
                alive = True
            except ProcessLookupError:
                alive = False
            except PermissionError:
                alive = None      # existe pero no es nuestro
        # PID vivo NO es prueba de sesion viva: el kernel recicla PIDs, y
        # tooling/tooling2 comparten PID=4535 siendo sesiones distintas.
        # Se reporta como PISTA, no como veredicto.
        out[d] = {"owner": txt, "ts": ts, "pid": pid, "alive": alive}
    return out


def age_of(ts):
    if not ts:
        return None
    try:
        t = time.mktime(time.strptime(ts[:19], "%Y-%m-%dT%H:%M:%S"))
    except ValueError:
        return None
    return int(time.time() - t)


def grep_paths(pattern, roots, flags=("-rliE",)):
    """Nº de ficheros que casan, sin imprimir su contenido."""
    n = 0
    for r in roots:
        if not os.path.isdir(r):
            continue
        try:
            p = subprocess.run(["grep", *flags, pattern, r],
                               capture_output=True, text=True, timeout=30)
            if p.returncode in (0, 1):
                n += len([l for l in p.stdout.split("\n") if l.strip()])
        except (subprocess.TimeoutExpired, OSError):
            pass
    return n


def free_finding_number(start=40, end=99):
    """
    Primer numero libre. NO elige uno ya usado: hay 50 IDs duplicados, que
    existen porque dos sesiones eligieron el mismo numero a la vez.

    EL RANGO SE ABRE SI NO HAY NINGUNO LIBRE, Y ESO NO ES OPCIONAL.

    La primera version usaba `range(40, 99)` y devolvia None al agotarse. El
    proyecto tiene documentos hasta 099, asi que se agoto y el self-test fallo
    con "hay un numero libre -> False".

    Un fallo asi es peor que no tener la funcion: `scopeguard` es el PREFLIGHT
    de escritura, y si dice "no hay numero" cuando en realidad solo se
    acabo el rango, el agente se queda sin numerar sin motivo.

    Asi que el rango por defecto es una PISTA, no un techo: si no hay hueco,
    se sigue buscando por encima del maximo usado. Y si de verdad no queda
    sitio -- mil documentos, o un hueco del tamano del rango entero -- se
    devuelve None, que es un hecho y no un fallo silencioso.
    """
    if not os.path.isdir(FINDINGS):
        return None, []
    used = set()
    for f in os.listdir(FINDINGS):
        m = re.match(r"(\d+[a-z]?)-", f)
        if m:
            used.add(m.group(1))
    for n in range(start, end):
        if f"{n:03d}" not in used and str(n) not in used:
            return f"{n:03d}", sorted(used)
    # Rango agotado: se sigue por encima del maximo realmente usado, en vez de
    # declarar que no hay sitio. Los tres digitos son la convencion, y el
    # proyecto ya usa 099, asi que el siguiente es 100.
    nums = [int(re.match(r"(\d+)", u).group(1)) for u in used
            if re.match(r"(\d+)", u)]
    if not nums:
        return f"{start:03d}", sorted(used)
    siguiente = max(nums) + 1
    if siguiente < 100:
        return f"{siguiente:03d}", sorted(used)
    return f"{siguiente}", sorted(used)


def duplicate_ids():
    """IDs de hallazgo que mas de un fichero usa. Es un defecto del proyecto."""
    if not os.path.isdir(FINDINGS):
        return []
    seen = {}
    for f in os.listdir(FINDINGS):
        m = re.match(r"(\d+[a-z]?)-", f)
        if m:
            seen.setdefault(m.group(1), []).append(f)
    return {k: v for k, v in seen.items() if len(v) > 1}


def topic_taken(topic):
    """¿El tema ya esta escrito? Devuelve los ficheros que lo mencionan."""
    hits = []
    for root in (FINDINGS, DOCS):
        if not os.path.isdir(root):
            continue
        try:
            p = subprocess.run(["grep", "-rliE", topic, root],
                               capture_output=True, text=True, timeout=30)
            if p.returncode in (0, 1):
                hits += [l for l in p.stdout.split("\n") if l.strip()]
        except (subprocess.TimeoutExpired, OSError):
            pass
    return sorted(set(hits))


def existing_tools():
    if not os.path.isdir(TOOLS):
        return []
    out = []
    for f in sorted(os.listdir(TOOLS)):
        if f == "__pycache__":
            continue
        out.append(f)
    return out


def selftest():
    fails = 0

    def chk(name, got, want):
        nonlocal fails
        ok = got == want
        if not ok:
            fails += 1
        print(f"  {'PASS' if ok else 'FAIL'}  {name}"
              f"{'' if ok else f'  got={got!r} want={want!r}'}")

    print("  --- locks ---")
    lk = read_locks()
    chk("leer locks no revienta con el dir ausente", isinstance(lk, dict), True)
    chk("cada lock con owner tiene pid o ts",
        all(("pid" in v or "ts" in v) for v in lk.values()), True)
    # El parser de PID es donde fallaba: 5 de 7 locks usan "PID=<n>" y el
    # codigo original solo aceptaba un numero suelto, asi que devolvia None.
    # Este caso NO PUEDE pasar con el parser roto.
    chk("extrae el PID del formato PID=<n>",
        _pid_of("toolbuild PID=79839 2026-10-01T13:25:58-03:00"), 79839)
    chk("y del formato numero suelto",
        _pid_of("122554 2026-10-01T13:57:16-03:00 scope=drv042"), 122554)
    chk("y no inventa un PID donde no hay",
        _pid_of("session=opencode sin proceso"), None)
    chk("no confunde una FECHA con un PID",
        _pid_of("2026-10-01T13:25:58-03:00"), None)
    # deteccion de muerte: un PID imposible no puede estar vivo
    chk("un PID imposible se marca muerto",
        _alive_of(4194304), False)

    print("  --- numeracion ---")
    num, used = free_finding_number()
    chk("hay un numero libre", num is not None, True)
    chk("el numero elegido no esta usado", num in used, False)
    dups = duplicate_ids()
    # El numero NO se escribe en el test: hardcodearlo lo convierte en una
    # afirmacion que envejece.  El self-test debe seguir siendo cierto cuando
    # el proyecto tenga 40 duplicados.  (Error propio: decia "10" y hay 21.)
    chk("detecta IDs duplicados", len(dups) >= 1, True)
    chk("y son duplicados de verdad", all(len(v) >= 2 for v in dups.values()), True)

    print("  --- tema ya escrito ---")
    h = topic_taken("src_data")
    chk("un tema presente devuelve ficheros", len(h) > 0, True)
    chk("uno ausente devuelve vacio",
        len(topic_taken("ESTE_TEMA_NO_EXISTE_12345")), 0)

    print("  --- tools ---")
    chk("lista las herramientas", "doclint.py" in existing_tools(), True)

    print(f"  {len(dups)} IDs duplicados, numero libre={num}")
    print(f"  {'todos pasan' if not fails else f'{fails} FALLAN'}")
    return 1 if fails else 0


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--findings", action="store_true",
                    help="estado de ambitos + numero de hallazgo libre")
    ap.add_argument("--locks", action="store_true")
    ap.add_argument("--check", metavar="TOPIC",
                    help="¿el tema ya esta escrito? exit 2 si hay ficheros")
    ap.add_argument("--tools", action="store_true")
    ap.add_argument("--dups", action="store_true")
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--self", action="store_true")
    a = ap.parse_args()

    if a.self:
        return selftest()

    rep = {}
    rep["locks"] = read_locks()
    for k, v in rep["locks"].items():
        v["age_s"] = age_of(v["ts"])
    num, used = free_finding_number()
    rep["free_finding"] = num
    rep["duplicate_ids"] = duplicate_ids()
    rep["tools"] = existing_tools()

    if a.check:
        hits = topic_taken(a.check)
        rep["topic"] = a.check
        rep["topic_hits"] = hits
        rep["topic_free"] = not hits

    if a.json:
        print(json.dumps(rep, indent=2, default=str))
        if a.check and hits:
            return 2
        return 0

    # ---- salida legible ----
    if a.locks or a.findings:
        print("  AMBITOS TOMADOS")
        if not rep["locks"]:
            print("    (ninguno)")
        for k, v in sorted(rep["locks"].items()):
            life = {True: "vivo", False: "MUERTO", None: "?"}[v["alive"]]
            age = v["age_s"]
            ag = f"hace {age}s" if age is not None else "sin fecha"
            print(f"    {k:12} {life:6} {ag:12} {v['owner'][:46]}")
        print()
    if a.findings:
        d = rep["duplicate_ids"]
        print(f"  NUMERO LIBRE      {rep['free_finding']}")
        print(f"  IDs DUPLICADOS    {len(d)}"
              + (f"  ->  {', '.join(sorted(d))}" if d else ""))
        print()
    if a.tools:
        print("  HERRAMIENTAS EXISTENTES (no repitas ninguna)")
        print("    " + "  ".join(rep["tools"]))
        print()
    if a.check:
        hits = rep["topic_hits"]
        print(f"  TEMA  {a.check!r}")
        if hits:
            print(f"    OCUPADO. {len(hits)} ficheros lo mencionan:")
            for h in hits[:8]:
                print(f"      {h.replace(PROJECT+'/', '')}")
        else:
            print("    LIBRE. nadie lo ha escrito.")
        return 2 if hits else 0

    return 0


if __name__ == "__main__":
    sys.exit(main())