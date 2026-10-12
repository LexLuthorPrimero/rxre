# SPDX-License-Identifier: GPL-2.0
"""Adaptador de Ghidra (decompilacion headless). RXRE-BULK-2026-10-12.

## QUE ES Y QUE NO ES

Es un PRODUCTOR de evidencia de decompilacion (`DECOMPILATION`, no
`VALIDATED_SEMANTICS`). Ghidra es un motor de recuperacion de codigo C a
partir de binarios: su salida es una REPRESENTACION, y el contrato de
`contract.py` ya tiene la regla que lo impide convertir en verdad:

    un decompilador no demuestra la semantica del hardware

## LO QUE ESTA MEDIDO Y NO SE SUPOÑO

MEDIDO 2026-10-12, Ghidra 12.1.4 + OpenJDK 25.0.4.1:

  * `/usr/bin/ls` (ELF ET_DYN, x86-64)
      -> `n_functions_dumped = 5`, las 5 con `decompiled: true`,
         C real en el campo `c`.
  * `small.ko` (ELF ET_REL, 11 KB, 23 secciones, `readelf` lo ve bien)
      -> `n_functions_dumped = 0`, y Ghidra imprime
         `REPORT: Import succeeded`.
  * `amdgpu.ko` (ELF ET_REL, 37 MB)
      -> `ElfException: Unable to read past EOF` + 0 funciones.

La segunda y la tercera Mediciones son EL PUNTO DE ESTE ADAPTADOR:

    "Import succeeded" con 0 funciones NO es un exito y NO es un vacio

Para un binario de usuario, 0 funciones seria `empty` ("se ejecuto y no hay
nada"). Para un modulo ET_REL del kernel es otra cosa: el MISMO Ghidra, con
el MISMO loader, sobre el mismo fichero que `readelf` describe con 23
secciones, no produce ninguna. La diferencia esta en la clase de entrada,
no en el binario ni en el tool. Eso es `unsupported`, con nombre.

Por eso `_clasificar_elf_rel` decide por CLASE DE ENTRADA y no por
conteo: si `e_type == ET_REL` y salen 0 funciones, el estado es
`BK_UNSUPPORTED` con el motivo. Si `e_type != ET_REL` y salen 0
funciones, es `BK_EMPTY` de verdad.

Sin esa distincion, una IA que ejecutase esto sobre `amdgpu.ko` leeria
"empty" y concluiria que el driver no tiene funciones: es la clase de
error que el hallazgo 1569 ya denomino (exit cero con el ejecutable
equivocado) y que el hallazgo 1571 separo como estado propio.

## LO QUE ESTA MEDIDO Y ES UNA LIMITACION DE ESTE ADAPTADOR

  * Ghidra 12 NO compila scripts `.java` en caliente: sin `.class`
    precompilado da `ClassNotFoundException`. Se compila con
    `javac -cp <los jars de GHIDRA_INSTALL_DIR>`. `build/` esta en el
    arbol y `compilar()` lo rehace si falta.
  * El arranque de Ghidra headless cuesta MINUTOS (MEDIDO: 8m47s sobre
    `amdgpu.ko`, con 29m46s de CPU). El timeout por defecto del backend
    es de 1800s, no los 900s de los backends de CLI.
  * `import angr` funciona DENTRO del arbol (hallazgo 1573). Ghidra NO
    tiene ese problema: se verifica por BINARIO (`/usr/lib64/ghidra/
    support/analyzeHeadless`) y por version leida de
    `Ghidra/application.properties`, no por import.
"""
from __future__ import annotations

import json
import os
import struct
import subprocess
import sys
import tempfile
import time
from typing import Any, Dict, List, Optional

HERE = os.path.dirname(os.path.abspath(__file__))
PKG = os.path.abspath(os.path.join(HERE, "..", ".."))
if PKG not in sys.path:
    sys.path.insert(0, PKG)

from backends import registry  # noqa: E402
from backends.contract import (  # noqa: E402
    BK_BLOCKED, BK_EMPTY, BK_ERROR, BK_INVALID, BK_OK, BK_UNSUPPORTED,
    DECOMPILATION, Backend, sha256_de, sha256_texto,
)

SCRIPTS = os.path.join(PKG, "backends", "scripts")
CLASE = "DumpDecomp.class"
FUENTE = os.path.join(SCRIPTS, "DumpDecomp.java")
BUILD = os.path.join(SCRIPTS, "build")

#: Donde vive Ghidra. No se deduce del PATH: `ghidra` es un symlink a
#: `ghidraRun`, que es un launcher, y el launcher NO es el motor. El motor
#: headless vive en `$GHIDRA_INSTALL_DIR/support/analyzeHeadless`.
GHIDRA_HOME = os.environ.get("GHIDRA_INSTALL_DIR", "/usr/lib64/ghidra")


def _cola(texto: str, n: int = 400, cabeceras: int = 6) -> str:
    """LOS ULTIMOS `n` caracteres, no los primeros.

    MEDIDO 2026-10-12 (RXRE-1634): recortar stderr por la cabeza es peor
    que inútil con Ghidra. Su salida empieza con un banner de la JVM
    (version de openjdk, avisos de `sun.misc.Unsafe`, ...) que se come los
    primeros 400 caracteres, y el diagnostico -`Invalid script`,
    `java class not found for 'DumpDecomp'`- esta AL FINAL. Con el recorte
    por cabeza, un `error` sin motivo visible: el motivo es lo unico que
    dice por que no se pudo, y se estaba descartando.

    Se conservan las primeras lineas aparte para no perder el contexto de
    que producer habia.
    """
    t = (texto or "").strip()
    if len(t) <= n:
        return t
    cab = "\n".join(t.splitlines()[:cabeceras])
    return "%s\n... [%d caracteres omitidos] ...\n%s" % (
        cab, len(t) - n, t[-n:])


def _version_de_propiedades(home: str) -> str:
    """Version REAL del Ghidra instalado, leida de su fichero.

    No se usa la salida de `analyzeHeadless --help`: esa arranca la JVM y
    tarda. `application.properties` es la declaracion del propio producto.
    """
    p = os.path.join(home, "Ghidra", "application.properties")
    try:
        with open(p, encoding="utf-8", errors="replace") as fh:
            for linea in fh:
                if linea.startswith("application.version="):
                    return "Ghidra " + linea.split("=", 1)[1].strip()
    except OSError:
        return ""
    return ""


def disponible() -> Dict[str, Any]:
    """Disponibilidad REAL. No un `which` y ya."""
    hl = os.path.join(GHIDRA_HOME, "support", "analyzeHeadless")
    ok_exe = os.path.isfile(hl) and os.access(hl, os.X_OK)
    ver = _version_de_propiedades(GHIDRA_HOME) if ok_exe else ""
    return {
        "backend_id": "ghidra",
        "home": GHIDRA_HOME,
        "analyzeHeadless": hl,
        "existe": ok_exe,
        "version": ver,
        "version_verificada": bool(ver),
        "script_precompilado": os.path.isfile(
            os.path.join(BUILD, CLASE)),
        "java": _java_version(),
        "scripts_dir": SCRIPTS,
    }


def _java_version() -> str:
    try:
        p = subprocess.run(["java", "-version"], capture_output=True,
                           text=True, timeout=30)
        t = (p.stderr or "") + (p.stdout or "")
        for ln in t.splitlines():
            if "version" in ln:
                return ln.strip()[:120]
    except (OSError, subprocess.TimeoutExpired):
        pass
    return ""


def compilar(forzar: bool = False) -> Dict[str, Any]:
    """Compila `DumpDecomp.java` si hace falta.

    MEDIDO: Ghidra 12 da `ClassNotFoundException` con un `.java` sin
    compilar. Es un requisito de la version, no un fallo del adaptador.
    """
    destino = os.path.join(BUILD, CLASE)
    if os.path.isfile(destino) and not forzar:
        return {"estado": "ya_compilado", "clase": destino}
    if not os.path.isfile(FUENTE):
        return {"estado": "error", "motivo": "no esta el fuente %s" % FUENTE}
    jars: List[str] = []
    for raiz, _dirs, files in os.walk(GHIDRA_HOME):
        for f in files:
            if f.endswith(".jar"):
                jars.append(os.path.join(raiz, f))
    if not jars:
        return {"estado": "blocked",
                "motivo": "no hay jars bajo %s" % GHIDRA_HOME}
    os.makedirs(BUILD, exist_ok=True)
    cp = ":".join(jars)
    t0 = time.time()
    try:
        p = subprocess.run(["javac", "-nowarn", "-cp", cp, "-d", BUILD,
                            FUENTE], capture_output=True, text=True,
                           timeout=600)
    except (OSError, subprocess.TimeoutExpired) as e:
        return {"estado": "error", "motivo": str(e)}
    ok = os.path.isfile(destino)
    return {"estado": "compilado" if ok else "error",
            "clase": destino, "rc": p.returncode,
            "n_jars": len(jars),
            "stderr": _cola(p.stderr, 300),
            "duration_s": round(time.time() - t0, 2)}


def _elf_clase(artefacto: str) -> Dict[str, Any]:
    """Lee SOLO la cabecera ELF. Lo justo para clasificar la entrada.

    No se invoca `readelf` ni `file`: aqui no hace falta saber que hay
    dentro, solo de que clase es el objeto, y la cabecera lo dice sin
    arrancar otro proceso.
    """
    try:
        with open(artefacto, "rb") as fh:
            h = fh.read(64)
    except OSError as e:
        return {"ok": False, "motivo": str(e)}
    if len(h) < 20 or h[:4] != b"\x7fELF":
        return {"ok": False, "motivo": "no empieza por \\x7fELF"}
    ei_class = h[4]
    if ei_class not in (1, 2):
        return {"ok": False, "motivo": "EI_CLASS=%d inesperado" % ei_class}
    little = h[5] == 1
    end = "<" if little else ">"
    if ei_class == 2:  # 64 bits
        e_type, = struct.unpack_from(end + "H", h, 16)
        e_machine, = struct.unpack_from(end + "H", h, 18)
    else:              # 32 bits
        e_type, = struct.unpack_from(end + "H", h, 16)
        e_machine, = struct.unpack_from(end + "H", h, 18)
    nombres = {0: "ET_NONE", 1: "ET_REL", 2: "ET_EXEC", 3: "ET_DYN",
               4: "ET_CORE"}
    return {"ok": True, "ei_class": 64 if ei_class == 2 else 32,
            "little_endian": little, "e_type": e_type,
            "e_type_nombre": nombres.get(e_type, "ET_%d" % e_type),
            "e_machine": e_machine}


def _es_et_rel(artefacto: str) -> Optional[bool]:
    c = _elf_clase(artefacto)
    if not c.get("ok"):
        return None
    return c.get("e_type") == 1


def decompile(artefacto: str, backend_id: str = "ghidra",
              timeout: int = 1800, max_funcs: int = 5,
              filtro_nombre: str = "", project_dir: str = "",
              fixture_json: str = "") -> Dict[str, Any]:
    """La operacion. SIEMPRE los seis canales del contrato.

    `fixture_json` permite probar el adaptador SIN Ghidra: si se da, se lee
    ese fichero como si fuera la salida del producer. Es lo que permite que
    la suite de tests no dependa de una JVM ni de minutos de arranque.
    """
    ent = registry.get(backend_id)
    b: Backend = ent["backend"]
    disp = disponible()

    # --- PRE-EXECUTION CONTRACT CHECK (§15) -----------------------------
    pre = {"input_existe": os.path.isfile(artefacto),
           "input_es_elf": False, "input_hash": "",
           "elf_clase": {}, "backend_existe": disp["existe"],
           "script_precompilado": disp["script_precompilado"],
           "java_presente": bool(_java_version()),
           "usa_fixture": bool(fixture_json),
           "ok": False}
    if fixture_json:
        # Modo fixture: el ARTEFACTO no tiene que existir (asi se pueden
        # probar rutas de fallo sin binario). Pero si existe, se CLASIFICA
        # igual: si alguien pasa un .txt con un fixture de ET_REL, la
        # respuesta tiene que ser la misma que con el .ko de verdad.
        #
        # MEDIDO 2026-10-12: la primera version de esta rama hacia
        # `et_rel = bool(fixture_json) and False`, o sea SIEMPRE False. Con
        # eso los tres fixtures de 0 funciones daban `empty` y las pruebas
        # lo cazaron. El fixture no puede cambiar el estado del resultado:
        # cambia quien lo produjo, no que es la entrada.
        pre["input_existe"] = os.path.isfile(artefacto)
        if not os.path.isfile(fixture_json):
            return {"status": BK_INVALID, "precheck": pre,
                    "limitations": ["no existe el fixture: %s"
                                    % fixture_json]}
        if pre["input_existe"]:
            pre["input_es_elf"] = os.path.isfile(artefacto)
            pre["elf_clase"] = _elf_clase(artefacto)
            if not pre["elf_clase"].get("ok"):
                return {"status": BK_INVALID, "precheck": pre,
                        "limitations": [
                            "la entrada no es un ELF: %s" % artefacto,
                            "no se llego a ejecutar el producer"]}
        pre["ok"] = True
    else:
        if not pre["input_existe"]:
            return {"status": BK_INVALID, "precheck": pre,
                    "limitations": ["la entrada no existe: %s" % artefacto]}
        # MEDIDO 2026-10-12 (RXRE-1634): aqui habia `_es_elf(p)`, que NO
        # esta definida en este modulo. La funcion existe, pero en
        # `rz_inspect`, y no se importaba. Resultado: TODA llamada real
        # reventaba con `NameError` antes de llegar a Ghidra.
        #
        # No lo detectaron las pruebas porque solo usaban `fixture_json=`,
        # que se salta este bloque entero. Es decir: `binary.decompile`
        # figuraba como cerrada y VERIFICADA, y en la realidad nunca se
        # habia ejecutado sobre un ELF. Solo se conocia el camino del
        # fixture.
        #
        # Se usa `_elf_clase`, que es la funcion de ESTE modulo y ya hace
        # exactamente eso: leer la cabecera y decir si es ELF. Acoplarlo a
        # `rz_inspect` habria metido una dependencia entre adapters que no
        # existe por ninguna otra razon.
        _clase = _elf_clase(artefacto)
        if not _clase.get("ok"):
            return {"status": BK_INVALID, "precheck": pre,
                    "limitations": [
                        "la entrada no es un ELF utilizable: %s (%s)"
                        % (artefacto, _clase.get("motivo", "sin motivo")),
                        "no se invoco a Ghidra: sin ELF el loader no tiene "
                        "nada que importar"]}
        pre["input_es_elf"] = True
        pre["elf_clase"] = _clase
        pre["elf_clase"] = _elf_clase(artefacto)
        pre["input_hash"] = sha256_de(artefacto)
        if not pre["backend_existe"]:
            return {"status": BK_BLOCKED, "precheck": pre,
                    "limitations": [
                        "Ghidra no esta instalado en %s: no existe "
                        "support/analyzeHeadless" % GHIDRA_HOME]}
        if not pre["java_presente"]:
            return {"status": BK_BLOCKED, "precheck": pre,
                    "limitations": ["no hay JVM: Ghidra 12 requiere Java "
                                    "(MEDIDO: OpenJDK 25.0.4.1 funciona)"]}
        if not pre["script_precompilado"]:
            c = compilar()
            pre["compilacion"] = c
            if c.get("estado") not in ("compilado", "ya_compilado"):
                return {"status": BK_BLOCKED, "precheck": pre,
                        "limitations": ["el script de Ghidra no esta "
                                        "compilado y no se pudo compilar: %s"
                                        % c.get("motivo", c.get("stderr", ""))]}
            pre["script_precompilado"] = True
        pre["ok"] = True

    # --- EJECUCION ------------------------------------------------------
    tmpdir = tempfile.mkdtemp(prefix="rxre_ghidra_")
    out_json = os.path.join(tmpdir, "decomp.json")
    argv: List[str] = []
    rc: Optional[int] = None
    se = ""
    so = ""
    timedout = False
    dur = 0.0

    if fixture_json:
        with open(fixture_json, encoding="utf-8") as fh:
            contenido = fh.read()
        with open(out_json, "w", encoding="utf-8") as fh:
            fh.write(contenido)
        argv = ["<fixture>", fixture_json]
        rc, so, se = 0, "", "modo fixture: producer simulado"
        ejec_backend = "fixture"
    else:
        proj = project_dir or os.path.join(tmpdir, "proj")
        os.makedirs(proj, exist_ok=True)
        argv = [os.path.join(GHIDRA_HOME, "support", "analyzeHeadless"),
                proj, "rxre_gh",
                "-import", artefacto,
                "-scriptPath", SCRIPTS + os.pathsep + BUILD,
                "-postScript", CLASE, out_json, str(int(max_funcs)),
                str(filtro_nombre or ""),
                "-deleteProject"]
        env = dict(os.environ)
        env.setdefault("GHIDRA_INSTALL_DIR", GHIDRA_HOME)
        t0 = time.time()
        try:
            p = subprocess.run(argv, capture_output=True, text=True,
                               timeout=timeout, env=env)
            rc, so, se = p.returncode, p.stdout or "", p.stderr or ""
        except subprocess.TimeoutExpired:
            rc, so, se, timedout = None, "", "timeout a los %ds" % timeout, True
        except OSError as exc:
            rc, so, se = None, "", str(exc)
        dur = round(time.time() - t0, 2)
        ejec_backend = backend_id

    ejec = {
        "backend_id": ejec_backend,
        "operation": "binary.decompile",
        "command_or_api": "analyzeHeadless <proj> rxre_gh -import "
                          "<artefacto> -postScript DumpDecomp.class "
                          "<out.json> <max_funcs> <filtro>",
        "argv": argv,
        "exit_status": rc,
        # MEDIDO 2026-10-12 (RXRE-1634): se recorta por la COLA.
        # El banner de la JVM ocupa la cabeza y el diagnostico esta al
        # final; con recorte por cabeza el motivo no se ve.
        "stderr": _cola(se, 600),
        "timeout": timedout,
        "duration_s": dur,
        "timeout_s": timeout,
    }

    ident = b.identidad()
    ident["ghidra"] = disp

    if timedout:
        ejec.update({"status": BK_BLOCKED,
                     "limitations": ["timeout a los %ds: el arranque headless "
                                     "de Ghidra cuesta minutos (MEDIDO 8m47s "
                                     "sobre amdgpu.ko)" % timeout]})
        return {"status": BK_BLOCKED, "precheck": pre, "ejecucion": ejec,
                "backend": ident,
                "provenance": "PROVENANCE_INCOMPLETE: no hay salida"}

    # --- ¿SALIO EL ARTEFACTO? Antes de parsearlo. (§27) -----------------
    if not os.path.isfile(out_json):
        motivo = "el script no escribio el JSON"
        if "ElfException" in se or "Unable to read past EOF" in se:
            motivo = ("ElfException: Unable to read past EOF. MEDIDO en "
                      "amdgpu.ko (ET_REL, 37MB). Es la clase de entrada, "
                      "no un fallo del binario: readelf lo describe bien")
        ejec.update({"status": BK_ERROR,
                     "limitations": [motivo,
                                     "STDOUT (ultimos 400): %s"
                                     % _cola(so, 400),
                                     "STDERR (ultimos 300): %s"
                                     % _cola(se, 300)]})
        return {"status": BK_ERROR, "precheck": pre, "ejecucion": ejec,
                        "limitations": ejec.get("limitations", []),
                "backend": ident,
                "provenance": "PROVENANCE_INCOMPLETO: sin artefacto"}

    try:
        with open(out_json, encoding="utf-8") as fh:
            d = json.load(fh)
    except ValueError as exc:
        ejec.update({"status": BK_ERROR,
                     "limitations": ["el artefacto existe pero no es JSON "
                                     "valido: %s" % exc]})
        return {"status": BK_ERROR, "precheck": pre, "ejecucion": ejec,
                        "limitations": ejec.get("limitations", []),
                "backend": ident,
                "provenance": "PROVENANCE_INCOMPLETO: artefacto no parseable"}

    funcs = d.get("functions") or []
    n = len(funcs)
    decl = sum(1 for f in funcs if f.get("decompiled"))
    # La clase de la ENTRADA se lee del artefacto. Un fixture no la
    # cambia: cambia el productor, no el fichero que se somete al
    # clasificador.
    et_rel = pre.get("elf_clase", {}).get("e_type") == 1

    lim_base = [
        "una DECOMPILACION es una REPRESENTACION recuperada de forma "
        "automatica. NO demuestra la semantica del hardware "
        "(contract.puede_declarar).",
        "Ghidra infiere tipos, parametros y control de flujo que el binario "
        "no declara. Los nombres son heuristicos: `FUN_00100360` no es un "
        "nombre real.",
        "el arranque headless cuesta minutos; no es una herramienta de "
        "bucle cerrado.",
    ]

    if n == 0:
        if et_rel:
            # LA MEDICION QUE JUSTIFICA ESTA RAMA.
            ejec.update({"status": BK_UNSUPPORTED,
                         "limitations": lim_base + [
                             "SIN PRODUCTOR PARA ESTA CLASE DE ENTRADA. "
                             "MEDIDO: Ghidra 12.1.4 imprime `REPORT: Import "
                             "succeeded` y produce 0 funciones para un ELF "
                             "ET_REL (modulo de kernel). El MISMO Ghidra "
                             "produce 5/5 funciones sobre /usr/bin/ls "
                             "(ET_DYN). readelf describe el .ko con 23 "
                             "secciones, asi que el binario NO esta vacio: "
                             "el loader ELF de Ghidra no produce funciones "
                             "para ET_REL. Es `unsupported`, no `empty`.",
                             "via alternativa: rizin/radare2 SI leen ET_REL "
                             "(ver binary.functions), y el BTF de /sys/kernel/"
                             "btf/amdgpu da tipos y signedas sin descompilar."]})
            return {"status": BK_UNSUPPORTED, "precheck": pre,
                    "ejecucion": ejec, "backend": ident,
                    "raw_output": d, "results": [],
                    "n_functions": 0, "provenance": "completa"}
        ejec.update({"status": BK_EMPTY,
                     "limitations": lim_base + [
                         "0 funciones descomprimidas. Con entrada NO ET_REL "
                         "esto es `empty` de verdad: se ejecuto y no hay "
                         "nada. No se confunde con el caso ET_REL de arriba."]})
        return {"status": BK_EMPTY, "precheck": pre, "ejecucion": ejec,
                "backend": ident, "raw_output": d, "results": [],
                "n_functions": 0, "provenance": "completa"}

    if decl == 0:
        ejec.update({"status": BK_EMPTY,
                     "limitations": lim_base + [
                         "hay %d funciones pero NINGUNA se descompilo "
                         "(`decompileCompleted()` falso en las %d): el "
                         "productor existe y no produjo salida para ninguna. "
                         "Eso NO es lo mismo que no haya funciones."
                         % (n, n)]})
        return {"status": BK_EMPTY, "precheck": pre, "ejecucion": ejec,
                "backend": ident, "raw_output": d, "results": [],
                "n_functions": n, "n_decompiladas": 0,
                "provenance": "completa"}

    version = disp.get("version") or ""
    artefacto_ref = artefacto if not fixture_json else fixture_json
    results = []
    for f in funcs:
        if not f.get("decompiled"):
            continue
        c = f.get("c") or ""
        valor = {
            "name": f.get("name"),
            "address": f.get("address"),
            "size": f.get("size"),
            "nparams": f.get("nparams"),
            "calling_convention": f.get("calling_convention"),
            "c": c,
            "c_lineas": c.count("\n"),
            "c_bytes": len(c.encode("utf-8")),
        }
        rid = "res_decomp_" + sha256_texto(
            "%s|%s|%s|%s" % (artefacto_ref, f.get("name"),
                             f.get("address"), c))[:12]
        results.append({
            "result_id": rid,
            "type": DECOMPILATION,
            "value": valor,
            "source": artefacto_ref,
            "location": {"file": os.path.basename(artefacto_ref),
                         "funcion": f.get("name"),
                         "direccion": f.get("address")},
            "scope": "funcion",
            "tool": backend_id,
            "tool_version": version,
            "input": {"path": artefacto_ref,
                      "sha256": pre.get("input_hash", "")},
            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S"),
            "artifact": artefacto_ref,
            "artifact_hash": pre.get("input_hash", ""),
            "status": "declared",
            "limitations": lim_base,
        })

    ejec.update({"status": BK_OK})
    return {
        "status": BK_OK,
        "precheck": pre,
        "ejecucion": ejec,
        "backend": ident,
        "raw_output": d,
        "results": results,
        "n_functions": n,
        "n_decompiladas": decl,
        "limitations": lim_base,
        "provenance": "completa",
    }