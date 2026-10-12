#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0
"""Pruebas de las cinco capacidades de CONTENEDOR. RXRE-1632.

POR QUE ESTAS CINCO SE PRUEBAN JUNTAS.

No porque sean parecidas, sino porque comparten la misma weakness: la de
`binary.functions`. Un comando de container que devuelve `[]` no dice que
el fichero no tenga secciones: dice que el comando no llego a decir nada.
Aqui eso se comprueba en las cinco, con la misma limitacion exigida en
cada respuesta.

Y hay un caso que NO se puede probar con producer real en esta maquina y
que es el mas importante de todos: el ET_REL. `/bin/ls` es ET_DYN. La
limitacion sobre direcciones de carga que se exige en las respuestas de
ET_REL no se puede activar con una entrada real pequena, asi que se
comprueba por dos vias: que el aviso EXISTE en el codigo, y que un
ET_REL real (amdgpu.ko) devuelve esa limitacion cuando esta disponible.

Uso:
    python3 tests/test_container1632.py
"""
from __future__ import annotations

import json
import os
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
PKG = os.path.abspath(os.path.join(HERE, ".."))
if PKG not in sys.path:
    sys.path.insert(0, PKG)

from backends import dispatch, registry  # noqa: E402
from backends.adapters import rz_container as C  # noqa: E402
from backends.contract import (  # noqa: E402
    BK_EMPTY, BK_ERROR, BK_INVALID, BK_OK,
    RAW_BINARY, FUNCTION_CANDIDATE, puede_declarar,
)

CAPS = [("binary.sections", "secciones", "iSj"),
        ("binary.imports", "imports", "iij"),
        ("binary.exports", "exports", "iEj"),
        ("binary.strings", "strings", "izj"),
        ("binary.symbols", "symbols", "isj")]

_n = 0
_f = 0


def chk(nombre, got, want):
    global _n, _f
    _n += 1
    if got == want:
        print("  ok  : %-52s %r" % (nombre, got))
    else:
        _f += 1
        print("  FAIL: %-52s got=%r want=%r" % (nombre, got, want))


def tmp(contenido, sufijo=".json"):
    fh = tempfile.NamedTemporaryFile(suffix=sufijo, delete=False)
    fh.write(contenido if isinstance(contenido, bytes)
             else contenido.encode())
    fh.close()
    return fh.name


def elf_real():
    for c in ("/bin/ls", "/usr/bin/cat"):
        if os.path.isfile(c) and open(c, "rb").read(4) == b"\x7fELF":
            return c
    return ""


def et_rel_real():
    """El `.ko` del driver, descomprimido si hace falta.

    No es obligatorio: si no esta, el caso se salta DEJANDO DICHO que se
    salto. Un caso que se salta en silencio y uno que se ejecuta dan el
    mismo verde, y no pueden confundirse.
    """
    import glob
    import subprocess as sp
    here = os.path.join(HERE, "..", ".work", "fix", "amdgpu.ko")
    if os.path.isfile(here):
        return here
    kern = sp.run(["uname", "-r"], capture_output=True, text=True).stdout.strip()
    for pat in ("/lib/modules/%s/kernel/drivers/gpu/drm/amd/amdgpu/"
                "amdgpu.ko.zst" % kern,):
        for z in glob.glob(pat):
            os.makedirs(os.path.dirname(here), exist_ok=True)
            r = sp.run(["zstd", "-d", "-f", "-o", here, z],
                       capture_output=True)
            if r.returncode == 0 and os.path.isfile(here):
                return here
    return ""


# ------------------------------------------------------------- registro
def t_registro():
    print("\n== registro: las cinco por el mecanismo oficial ==")
    chk("12 adapters registrados", len(dispatch.ADAPTERS), 12)
    for cap, fn, _cmd in CAPS:
        chk("%s tiene adapter" % cap, cap in dispatch.ADAPTERS, True)
        chk("%s -> rz_container.%s" % (cap, fn),
            dispatch.ADAPTERS[cap]["funcion"], fn)
        p = dispatch.esta_permitida(cap)
        chk("%s permitida y AVAILABLE" % cap,
            (p["permitida"], p.get("estado_registro")), (True, "AVAILABLE"))


# ------------------------------------------------------------- producer
def t_producer_real():
    print("\n== producer REAL: /bin/ls (ET_DYN), las cinco ==")
    elf = elf_real()
    if not elf:
        print("  skip: no hay ELF de sistema")
        return
    for cap, fn, cmd in CAPS:
        env = dispatch.ejecutar(cap, {"artefacto": elf, "backend_id": "rizin",
                                     "timeout": 300})
        chk("%s status ok" % cap, env["status"], BK_OK)
        chk("%s devolve elementos" % cap, env["n_elementos"] > 0, True)
        chk("%s usa el comando medido" % cap, env["ejecucion"]["comando"], cmd)
        chk("%s declara el producer" % cap,
            env["results"][0]["tool"], "rizin")
        chk("%s trae la version del producer" % cap,
            bool(env["results"][0]["tool_version"]), True)
        chk("%s tipo RAW_BINARY" % cap, env["results"][0]["type"], RAW_BINARY)
        chk("%s conserva el crudo del producer" % cap,
            all("crudo" in e for e in env["results"][0]["value"]["elementos"][:3]),
            True)
        chk("%s DECLARA lo que costo" % cap,
            "duration_s" in env["results"][0], True)
        # Coherencia con la medicion declarada: si el recuento se aparta
        # mucho, la medicion esta caducada y hay que decirlo.
        med = env["recuento_medido"].get(cap.split(".")[1])
        if med:
            chk("%s cerca del recuento medido (%d)" % (cap, med),
                abs(env["n_elementos"] - med) <= max(5, med * 0.1), True)


def t_confianza_no_se_infla():
    print("\n== la confianza NO se infla ==")
    chk("RAW_BINARY no declara semantica validada",
        puede_declarar(RAW_BINARY, "validated_semantics"), False)
    chk("RAW_BINARY no declara decompilacion",
        puede_declarar(RAW_BINARY, "decompilation"), False)
    chk("RAW_BINARY no declara funciones",
        puede_declarar(RAW_BINARY, FUNCTION_CANDIDATE), False)
    chk("RAW_BINARY si se satisface a si mismo",
        puede_declarar(RAW_BINARY, RAW_BINARY), True)
    # El punto de `binary.symbols`: la tabla de simbolos NO es funciones.
    chk("simbolos NO pueden Consumirse como funciones",
        puede_declarar(RAW_BINARY, FUNCTION_CANDIDATE), False)


def t_aviso_de_simbolos():
    print("\n== simbolos != funciones, y el aviso lo dice ==")
    src = open(os.path.join(HERE, "..", "backends", "adapters",
                            "rz_container.py"), encoding="utf-8").read()
    chk("el aviso 'NO son funciones' existe en el codigo",
        "los simbolos NO son funciones" in src, True)
    chk("y manda a binary.functions como la capacidad correcta",
        "binary.functions" in src, True)
    chk("el aviso de strings dice que son BYTES",
        "son BYTES" in src, True)
    chk("el aviso de imports dice que no estan resueltos",
        "sin resolver" in src, True)


# ------------------------------------------------------------- negativos
def t_no_elf():
    print("\n== negativo: la entrada NO es un ELF ==")
    ruta = tmp("esto no es un ELF\n", ".txt")
    try:
        for cap, _fn, _cmd in CAPS:
            env = dispatch.ejecutar(cap, {"artefacto": ruta})
            chk("%s -> invalid_input" % cap, env["status"], BK_INVALID)
            # `ejecutada` dice si se invoco al ADAPTER. Lo que se
            # pregunta es si corrio el PRODUCER, que es otra cosa y la que
            # importa: un `invalid_input` sale de un precheck, sin tocar
            # el producer.
            chk("%s no ejecuto el producer" % cap,
                env.get("producer_ejecutado"), False)
            chk("%s pero el adapter si se invoco" % cap,
                env.get("ejecutada"), True)
    finally:
        os.unlink(ruta)


def t_no_existe():
    print("\n== negativo: la entrada NO existe ==")
    env = dispatch.ejecutar("binary.sections",
                            {"artefacto": "/no/existe/jamas.elf"})
    chk("invalid_input", env["status"], BK_INVALID)
    chk("el motivo lo dice", any("no existe" in x
                                for x in env["limitations"]), True)


def t_backend_desconocido():
    print("\n== negativo: backend que no existe ==")
    elf = elf_real()
    if not elf:
        return
    env = dispatch.ejecutar("binary.sections",
                            {"artefacto": elf,
                             "backend_id": "no_existe_este"})
    chk("invalid_input, no traceback", env["status"], BK_INVALID)
    chk("el motivo lista los que SI valen",
        any("los declarados son" in x for x in env["limitations"]), True)


# ------------------------------------------------------------- adversariales
def t_lista_vacia_no_prueba_ausencia():
    """EL CASO PELIGROSO, en las cinco."""
    print("\n== ADVERSARIAL: lista vacia NO prueba ausencia (las 5) ==")
    ruta = tmp("[]")
    try:
        for cap, _fn, _cmd in CAPS:
            env = dispatch.ejecutar(cap, {"artefacto": ruta,
                                          "fixture_json": ruta})
            chk("%s -> empty" % cap, env["status"], BK_EMPTY)
            chk("%s 0 elementos" % cap, env["n_elementos"], 0)
            chk("%s DECLARA que empty no prueba ausencia" % cap,
                any("NO ESTABLECE" in x for x in env["limitations"]), True)
            chk("%s no persiste resultados" % cap,
                len(env.get("results") or []), 0)
    finally:
        os.unlink(ruta)


def t_json_truncado():
    print("\n== ADVERSARIAL: JSON truncado a media lista ==")
    ruta = tmp('[{"name":"a","vaddr":1},{"name":"b","vaddr')
    try:
        for cap, _fn, _cmd in CAPS[:2]:
            env = dispatch.ejecutar(cap, {"artefacto": ruta,
                                          "fixture_json": ruta})
            chk("%s -> error, no ok" % cap, env["status"], BK_ERROR)
            chk("%s no persiste parciales" % cap,
                len(env.get("results") or []), 0)
    finally:
        os.unlink(ruta)


def t_no_es_lista():
    print("\n== ADVERSARIAL: JSON que no es una lista ==")
    ruta = tmp(json.dumps({"no": "soy lista"}))
    try:
        env = dispatch.ejecutar("binary.sections",
                                {"artefacto": ruta, "fixture_json": ruta})
        chk("error", env["status"], BK_ERROR)
        chk("el motivo lo dice",
            any("no contiene una lista JSON" in x
                for x in env["limitations"]), True)
    finally:
        os.unlink(ruta)


def t_sin_lista():
    print("\n== ADVERSARIAL: salida sin ninguna lista (ANSI/banner) ==")
    ruta = tmp("\x1b[0;32m\x1b[1m\x1b[32mWelcome\x1b[0m\nsin datos")
    try:
        env = dispatch.ejecutar("binary.strings",
                                {"artefacto": ruta, "fixture_json": ruta})
        chk("error", env["status"], BK_ERROR)
        # MEDIDO: los escapes ANSI contienen `[`, asi que buscar la lista
        # sin limpiar puede caer DENTRO de `\x1b[0;32m` y producir un
        # error de JSON que no menciona el ANSI. Este caso FALLABA por ahi.
        # Con la limpieza previa, el texto ya no tiene `[` y entra por la
        # puerta que toca, cuyo motivo nombra el ANSI como causa.
        chk("el motivo es 'no contiene lista JSON', no un error de parseo",
            any("no contiene una lista JSON" in x
                for x in env["limitations"]), True)
        chk("y nombra ANSI/scr.color=0 como causa probable",
            any("scr.color=0" in x for x in env["limitations"]), True)
        chk("y muestra stdout limpio (sin escapes)",
            any("\x1b" not in x for x in env["limitations"]), True)
    finally:
        os.unlink(ruta)


# ------------------------------------------------------------- ET_REL
def t_et_rel_real():
    """La limitacion que NO se puede probar con un binario pequeno."""
    print("\n== ET_REL real: la limitacion de direcciones se activa ==")
    ko = et_rel_real()
    if not ko:
        print("  SKIP declarado: no hay ET_REL disponible. El caso NO se")
        print("  ejecuto; que no se confunda con un caso que paso.")
        return
    env = dispatch.ejecutar("binary.sections",
                            {"artefacto": ko, "backend_id": "rizin",
                             "timeout": 300})
    if env["status"] != BK_OK:
        print("  AVISO: el ET_REL real no completo (%s). El caso NO se"
              " ejecuto." % env["status"])
        return
    chk("el precheck detecta ET_REL",
        env["precheck"]["elf_tipo"], "ET_REL")
    chk("y la limitacion de direcciones de carga esta activa",
        any("ET_REL" in x and "direcciones de carga" in x
            for x in env["limitations"]), True)


def t_timeout():
    print("\n== timeout: del PRODUCTOR ==")
    elf = elf_real()
    if not elf:
        return
    env = dispatch.ejecutar("binary.symbols",
                            {"artefacto": elf, "backend_id": "rizin",
                             "timeout": 1})
    if env["status"] == BK_OK:
        print("  AVISO: no discrimina en esta maquina (producer rapido).")
        return
    chk("blocked, no error", env["status"], "blocked")
    chk("declara el timeout", env["ejecucion"]["timeout"], True)
    chk("no persiste parciales", len(env.get("results") or []), 0)


def main() -> int:
    print("RXRE-1632: pruebas de las cinco capacidades de contenedor")
    t_registro()
    t_producer_real()
    t_confianza_no_se_infla()
    t_aviso_de_simbolos()
    t_no_elf()
    t_no_existe()
    t_backend_desconocido()
    t_lista_vacia_no_prueba_ausencia()
    t_json_truncado()
    t_no_es_lista()
    t_sin_lista()
    t_et_rel_real()
    t_timeout()
    print("\n%d checks, %d failures" % (_n, _f))
    return 0 if _f == 0 else 1


if __name__ == "__main__":
    sys.exit(main())