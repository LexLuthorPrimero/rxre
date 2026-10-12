#!/usr/bin/env python3
"""RXRE-004. Registro de backends. Lo que la matriz justifico, y nada mas.

POR QUE ESTO NO ES UN CATALOGO NUEVO.

RXRE-002 prohibio el segundo catalogo de herramientas, y eso sigue vigente. Aqui
no hay catalogo de CAPACIDADES: hay un catalogo de BACKENDS, que es otra cosa --
un backend no es una capacidad, es un PRODUCTOR de evidencia para varias.

Y solo estan los dos que la matriz MEDIO. `angr` y `rz-ghidra` no estan, y su
ausencia esta declarada con su estado, no borrada:

    angr        NOT_DETERMINED   `import angr` funciona DENTRO del arbol del
                                 proyecto porque el directorio clonado se llama
                                 `angr` y Python lo toma como namespace package.
                                 Fuera: ModuleNotFoundError. No se comprobo que
                                 no pueda; se comprobo que no se puede
                                 VERIFICAR aqui.
    rz-ghidra   NOT_DETERMINED   requiere Ghidra + CMake + toolchain Java.
                                 Es la ruta de decompilacion y NO se declara
                                 ninguna capacidad de decompilacion.

`binary.decompile` NO esta en el registro. Es la capacidad que mas se querria
declarar y la que menos evidencia tiene. Declararla como `unsupported` en los
dos backends que corren, y `NOT_DETERMINED` en los que no se pueden verificar,
es la unica forma honesta de responderla hoy.
"""
from __future__ import annotations

import json
import os
import sys
from typing import Any, Dict, List

HERE = os.path.dirname(os.path.abspath(__file__))
PKG = os.path.abspath(os.path.join(HERE, "..", "..", ".."))
if PKG not in sys.path:
    sys.path.insert(0, PKG)

from backends.contract import (  # noqa: E402
    BK_UNSUPPORTED, Backend, contrato_de_backend,
)

#: Donde vive la matriz. La lectura es para la ficha del backend, no para el
#: plan: una capacidad que este aqui tiene producer, porque la matriz lo ejecuto.
MATRIX = os.path.join(PKG, "docs", "RXRE-004-BACKEND-MATRIX.md")

#: Estados con producer. Los dos unicos que permiten ejecutar; los otros dos no.
#: Vive aqui (y no en `dispatch`) porque es una propiedad del REGISTRO, no de la
#: capa que despacha: `dispatch` lo PREGUNTA.
ESTADOS_CON_PRODUCER = ("AVAILABLE", "PARTIAL")

#: La decision §18, machine-readable. En un fichero aparte para que una mutacion
#: pueda cambiarla sin tocar codigo, y para que `primary` se pueda COMPARAR
#: contra el recuento real del registro. En prosa no seria verificable.
DECISION = os.path.join(HERE, "decision.json")

#: MEDIDO 2026-10-06, `/bin/ls` ELF x86-64:
#:   rizin -qc 'aa; aflj'                  -> 112 funciones JSON
#:   rizin -qc 'aaa; axtj @ 0x00000a40'    -> 3 xrefs JSON
#:   rizin -qc 'aa; afbj @ entry0'         -> basic blocks JSON
#:   rizin -qc 'aaa; agf'                  -> ASCII, NO JSON
#:   rizin -qc 'aa; pdj 5'                 -> desensamblado JSON
#:   r2 -q -c 'aaa; agfj' / 'agCj'         -> JSON (84 nodos)
_ANALYSIS = "aa"

_BACKENDS: Dict[str, Dict[str, Any]] = {}


_BACKENDS: Dict[str, Dict[str, Any]] = {}


def _reg(b: Backend, *,
         caps: Dict[str, str],             # capacidad -> estado medido
         notas: List[str],
         no_medidas: List[str],
         unsuitable: List[str]) -> None:
    _BACKENDS[b.backend_id] = {"backend": b, "capacities": caps,
                               "notas": notas, "no_medidas": no_medidas,
                               "inadequate": unsuitable}


_reg(
    Backend("rizin", "rizin", ["-qc"], timeout=900,
            repo="https://github.com/rizinorg/rizin.git",
            commit="d14c3fac4126bc5fbe66e7f3d1660aeab22b01d8",
            env_extra={"RZ_NOPLUGINS": "1"}),
    caps={
        "binary.inspect": "AVAILABLE",       # rz-bin -Ij, dict de 30 claves
        "binary.sections": "AVAILABLE",     # rz-bin -Sj, 32
        "binary.symbols": "AVAILABLE",      # rz-bin -sj, 323
        "binary.imports": "AVAILABLE",      # rz-bin -ij, 121
        "binary.exports": "AVAILABLE",      # rz-bin -Ej, 16
        "binary.functions": "AVAILABLE",    # aflj, 112
        "binary.basic_blocks": "AVAILABLE",  # afbj
        "binary.disassemble": "AVAILABLE",  # pdj
        "binary.disassemble_func": "AVAILABLE",   # pdfj
        "binary.strings": "AVAILABLE",      # izj, 639
        "binary.xrefs": "AVAILABLE",        # axtj (con 'aaa', NO con 'aa')
        "binary.cfg": "PARTIAL",            # agf: ASCII/visual, no JSON
        "binary.callgraph": "PARTIAL",      # agC: ASCII/visual
        # B5: la etiqueta NO cambio, la RAZON si. Antes decia "PARTIAL: pdj es
        # desensamblado, no dataflow", y era FALSO: `pdj` no es un data-flow y
        # no se estaba usando como tal. El producer real existe y es otro.
        "binary.dataflow": "PARTIAL",      # afvxj: JSON MAL FORMADO (ver notas)
        "binary.decompile": "UNAVAILABLE",  # checked: no existe en 0.7.4
    },
    notas=[
        "RETRACCION (B5): antes esta capacidad figuraba como `PARTIAL` por "
        "la razon 'pdj es desensamblado, no dataflow'. ESA RAZON ERA FALSA: "
        "`pdj` produce desensamblado y no se estaba usando como data-flow; "
        "atribuirle un limite de formato era inventar un defecto en un "
        "producer que no era el. La etiqueta `PARTIAL` resulto correcta, pero "
        "por otro motivo: el producer real es `afvxj` y su JSON esta mal "
        "formado. Una razon correcta importa tanto como una etiqueta "
        "correcta: son cosas distintas y se pueden equivocar por separado.",
        "stdout trae ANSI y \\r por defecto: sin `-e scr.color=0` el JSON no "
        "parsea. MEDIDO. `limpieza` del contrato lo declara.",
        "los xrefs exigen `aaa`, no `aa`. MEDIDO: `aa; axtj` -> [] y "
        "`aaa; axtj` -> 3. Una llamada con el verbo de analisis corto da "
        "`empty` sin que falte nada.",
        "ORDEN DE FLAGS: `rizin -qc -e scr.color=0 'cmd'` NO funciona, porque "
        "`-qc` consume el argumento siguiente como comando y se come el `-e`. "
        "MEDIDO: sale vacio sin error. La forma correcta es "
        "`rizin -q -N -e scr.color=0 -c 'cmd'`. Es la MISMA clase de error que "
        "`aa` frente a `aaa`: un empty por invocacion incorrecta.",
        "DATAFLOW (B5): el producer real es `afvxj`, no `pdj`. MEDIDO sobre "
        "`campo`: emite JSON MAL FORMADO -- "
        "`{\"reads\":[{\"name\":\"arg1\",\"addrs\":[4194304]}],[],"
        "\"writes\":[{\"name\":\"arg1\",\"addrs\":[]}],[]}` -- con arrays "
        "sueltos intercalados, asi que `json.loads` falla. Por eso "
        "`binary.dataflow` es PARTIAL: el producer existe, el formato no "
        "cumple el contrato. `afvd`/`afv=`/`afvR`/`afvW` dan TEXTO.",
        "DATAFLOW: el conjunto de ESCRITURAS es demostrablemente INCOMPLETO. "
        "MEDIDO: `afvxj` sobre `campo` devuelve `writes: [{'name':'arg1',"
        "'addrs':[]}]` (vacio), pero la funcion TIENE un store en 0x400024 "
        "(`mov dword [edi - 0x30000000], edx`), confirmado por objdump y por "
        "el ESIL de rizin (`edx,0x30000000,edi,-,=[4]`). Consecuencia directa "
        "para este proyecto: `binary.dataflow` NO puede cerrar la frontera de "
        "las 24 aristas WRITES candidatas. Confiar en su conjunto de escrituras "
        "convertiria NOT_DETERMINED en PROVEN_ABSENT.",
        "en el repo 0.10-dev los verbos viven en librz/core/cmd_descs/*.yaml, "
        "no en un .c: un grep en librz/ da cero y parece que la capacidad no "
        "existe.",
        "version en runtime 0.7.4 (Fedora 43); el repo es v0.10.0-dev. NO son "
        "lo mismo y por eso `tool_version` y `repository_commit` son campos "
        "distintos del contrato.",
    ],
    no_medidas=["angr (no verificable)", "rz-ghidra (requiere Ghidra + Java)"],
    unsuitable=["binary.decompile", "binary.cfg en JSON", "binary.callgraph en JSON",
                "binary.dataflow: el conjunto de escrituras sale VACIO para "
                "una funcion con store probable (medido en B5)"],
)

_reg(
    Backend("radare2", "radare2", ["-q"], timeout=900,
            repo="https://github.com/radareorg/radare2.git",
            commit="008a7a6cd2e5acb8268f65f486760d080f3b107b",
            env_extra={"R2_NOPLUGINS": "1"}),
    caps={
        "binary.inspect": "AVAILABLE",       # rabin2 -Ij
        "binary.functions": "AVAILABLE",    # aflj, 201
        "binary.basic_blocks": "AVAILABLE",  # afbj
        "binary.disassemble": "AVAILABLE",  # pdj
        "binary.xrefs": "AVAILABLE",        # axtj, 3
        "binary.cfg": "AVAILABLE",          # agfj: JSON, a diferencia de rizin
        "binary.callgraph": "AVAILABLE",    # agCj: JSON, 84 nodos
        # B5: medido, no inferido. `afvxj` emite JSON VALIDO (a diferencia de
        # rizin, que lo emite mal formado), con conjuntos de lectura y escritura
        # por variable.
        "binary.dataflow": "AVAILABLE",     # afvxj, JSON valido
        "binary.decompile": "UNAVAILABLE",  # checked: no existe
    },
    notas=[
        "UNICO backend medido que da `binary.cfg` y `binary.callgraph` en JSON. "
        "Es su caso de uso, y es el unico motivo por el que se declara "
        "SECONDARY.",
        "version en runtime 5.9.8; el repo es master.",
        "tambien necesita `-e scr.color=0` para stdout parseable.",
        "DATAFLOW (B5): `afvxj` da JSON valido "
        "`{\"reads\":[{\"name\":\"arg1\",\"addrs\":[4194304]}],\"writes\":"
        "[{\"name\":\"arg1\",\"addrs\":[]}]}`. Producer verificado.",
        "DATAFLOW: pero su conjunto de escrituras tambien sale VACIO para "
        "`campo`, que tiene un store probable en 0x400024. El formato es "
        "correcto y el contenido es incompleto. Available NO significa "
        "completo, y esta capacidad no puede cerrar la frontera WRITES.",
        "ORDEN DE FLAGS: `r2 -q -e scr.color=0 -c 'cmd'`. Con `-c` antes de "
        "`-e` el `-e` se interpreta como comando y sale vacio sin error.",
    ],
    no_medidas=["angr (no verificable)", "rz-ghidra (requiere Ghidra + Java)"],
    unsuitable=["binary.decompile", "binary.strings (no medida)",
                "binary.dataflow: formato JSON valido pero el conjunto de "
                "escrituras sale VACIO para una funcion con store probable "
                "(medido en B5)"],
)



# --- Lote RXRE-BULK-2026-10-12. Solo lo MEDIDO en runtime. ---
#
# Estos NO estaban. Entran porque el binario esta, se pudo EJECUTAR, y la
# capacidad se midio sobre entradas reales. Un binario instalado sin
# producer medido no entra: entraria por su nombre.
#
# MEDIDO 2026-10-12, host Fedora 44 / x86-64:
#   ghidra      12.1.4, /usr/lib64/ghidra, headless OK, JDK 25.0.4.1
#   coccinelle  spatch 1.3.1, /usr/bin/spatch, OK

_reg(
    Backend("ghidra", "analyzeHeadless", [], timeout=1800,
            repo="https://github.com/NationalSecurityAgency/ghidra.git",
            commit="local:rpm-ghidra-12.1.4",
            env_extra={"GHIDRA_INSTALL_DIR": "/usr/lib64/ghidra"}),
    caps={
        "binary.decompile": "PARTIAL",
    },
    notas=[
        "MEDIDO: decompila. `/usr/bin/ls` (ET_DYN) -> 5 funciones, las 5 "
        "con `decompiled: true` y C real en el campo `c`. Producer real y "
        "verificado. Es la ruta de DECOMPILACION, y con esto `binary."
        "decompile` deja de ser `UNAVAILABLE` en todos los backends medidos.",
        "POR QUE ES `PARTIAL` Y NO `AVAILABLE`: el loader ELF de Ghidra 12.1.4 "
        "NO produce funciones para un ELF ET_REL. MEDIDO en dos entradas: "
        "`small.ko` (11 KB, 23 secciones segun readelf) y `amdgpu.ko` (37 MB) "
        "dan ambos 0 funciones, y el segundo ademas lanza `ElfException: "
        "Unable to read past EOF`. Ghidra imprime `REPORT: Import succeeded` "
        "en el caso pequeno. La capacidad existe y funciona; no cubre la "
        "clase de entrada ET_REL, que es exactamente la del driver del "
        "proyecto.",
        "MEDIDO y CLASIFICADO: para ET_REL con 0 funciones el estado es "
        "`unsupported`, NO `empty`. El producer se ejecuto, asi que no es "
        "un fallo; y no hay nada que mirar, porque readelf ve el fichero. "
        "Colapsar los dos diria que el driver no tiene funciones. Es la clase "
        "de error de los hallazgos 1569 y 1571.",
        "MEDIDO: el arranque headless cuesta MINUTOS. `amdgpu.ko`: 8m47s de "
        "reloj, 29m46s de CPU. El timeout del backend es 1800s por eso, no "
        "los 900s de los CLI. No es una herramienta de bucle cerrado: sirve "
        "para una decompilacion medida, no para un barrido.",
        "MEDIDO: Ghidra 12 NO compila scripts `.java` en caliente; sin "
        "`.class` precompilado da `ClassNotFoundException`. El clase esta "
        "en `backends/scripts/build/DumpDecomp.class` y el adaptador lo "
        "recompila si falta (`javac -cp <los 202 jars>`).",
        "IDENTIDAD: se verifica por BINARIO y por `Ghidra/"
        "application.properties`, no por import. No tiene el problema que "
        "tiene angr (hallazgo 1573).",
        "LIMITACION DE ALCANCE: Ghidra infiere tipos, parametros y control "
        "de flujo. Los nombres son heuristicos (`FUN_00100360` no es un "
        "nombre real) y su salida es DECOMPILATION, no VALIDATED_SEMANTICS "
        "sobre el hardware.",
        "rz-ghidra sigue NO_VERIFICABLE y sin cambiar: con Ghidra instalado "
        "el plugin de rizin es redundante para decompilar (el motor de Ghidra "
        "ya esta). Ver `RXRE-BULK-2026-10-12` en docs/ para la poda "
        "propuesta.",
    ],
    no_medidas=["strings, xrefs, callgraph de Ghidra (no se midieron: el "
                "script solo vuelca decompilacion)"],
    unsuitable=["binary.decompile sobre ELF ET_REL (MEDIDO: 0 funciones "
                "para modulos de kernel, con `Import succeeded`)"],
)


# Capstone: desensamblado con SEMANTICA de operando. MEDIDO 2026-10-12.
#
# Es el unico producer del catalogo que NO es un subproceso: se importa y
# se usa en el proceso del adapter. Por eso `exe` no es un binario externo
# sino el propio modulo, y `version_cmd` no aplica.
#
# Se registro porque cierra una capacidad que rizin y radare2 tienen
# declarada pero NO pueden cumplir: MEDIDO 2026-10-12,
#   rizin `aa; pdfj @ main`  -> NO emite JSON
#   r2    `agC` / `agf`      -> NO emiten JSON utilizable
# Capstone desensambla la funcion entera y da operandos CON TIPO, que es
# lo que permite construir un CFG sin depender de esos comandos.
_reg(
    Backend("capstone", None, None, timeout=0, modulo="capstone",
            repo="https://github.com/capstone-engine/capstone",
            commit="local:pip-capstone-5.0.7"),
    caps={
        "binary.disassemble": "AVAILABLE",
        "binary.disassemble_func": "AVAILABLE",
    },
    notas=[
        "MEDIDO 2026-10-12: version 5.0.7 (cs_version 5.0.1280), ya "
        "INSTALADO en /home/lucas/.local/lib/python3.14/site-packages/"
        "capstone. Adquirir esta capacidad costo cero: no hubo descarga ni "
        "compilacion. Se anota porque distinguir 'instalado' de 'integrado' "
        "importa: hasta este registro era un checkout de facto invisible.",
        "MEDIDO: ~158000 instrucciones/s en x86-64 con detail=True. En "
        "proceso, asi que no hay coste de arranque de subproceso.",
        "LA COBERTURA ES EL DATO, NO EL RECUENTO. MEDIDO: Capstone se "
        "DETIENE en el primer byte que no decodifica y no dice cual es. "
        "Sobre una funcion `sym` de 909 bytes cubre el 100 % (228 "
        "instrucciones); sobre una entrada con `type:'fcn'` y size 137 "
        "cubrío el 9,5 %. Por eso el adapter devuelve `huecos` y "
        "`primer_hueco`, y la limitacion viaja en cada respuesta: un "
        "recuento de instrucciones sin cobertura no es un resultado.",
        "ALCANCE: x86, x86_64 y arm64. NO cubre GFX8. Para el driver de la "
        "GPU haria falta otro producer: Capstone no sirve para el ISA de la "
        "GPU, aunque si para el modulo de kernel, que es x86-64 ET_REL.",
        "NO descubre funciones: el rango lo elige quien llama. Combinar con "
        "`binary.functions` (aflj) para los offsets.",
        "Un desensamblado NO es un descompilado. `DISASSEMBLY` queda por "
        "debajo de `FUNCTION_CANDIDATE` en la escalera y `puede_declarar` "
        "no lo deja ascender.",
    ],
    no_medidas=["GFX8 / AMDGPU (Capstone 5.0.7 no lo soporta: no es una "
                "limitacion del adaptador sino del producer)",
                "cobertura medida en binarios con datos intercalados "
                "dentro de una funcion (solo se midio en /bin/ls y "
                "/usr/bin/rizin)"],
    unsuitable=["cualquier pregunta sobre el ISA de la GPU (GFX8): Capstone "
                "no lo cubre"],
)


# Coccinelle: busqueda SEMANTICA sobre fuente. Namespace `source.` porque
# no opera sobre binario: necesita el texto, no el ELF.
_reg(
    Backend("coccinelle", "spatch", ["--version"], timeout=600,
            repo="https://github.com/coccinelle/coccinelle.git",
            commit="local:rpm-coccinelle-1.3.1"),
    caps={
        "source.semantic_search": "AVAILABLE",
    },
    notas=[
        "MEDIDO: aplica. `spatch --sp-file p.cocci f.c` reescribe la linea "
        "que casa con el patron. CONTROL NEGATIVO: el mismo patron sobre un "
        "fichero sin esa linea NO produce diff. El `empty` del producer es "
        "discriminante, no un fallo silencioso.",
        "MEDIDO: `spatch --spool` NO EXISTE en 1.3.1 (`unknown option`). La "
        "forma correcta es `--sp-file`.",
        "MEDIDO Y CLASIFICADO: `spatch` responde `No rules apply` con rc 255 "
        "tanto si el parche no aplica como si esta mal invocado. El adaptador "
        "comprueba ese texto y clasifica `invalid_input`, no `empty`: no es "
        "que no coincida, es que el parche no es usable sobre esa entrada. "
        "Sin esa comprobacion, un error de invocacion se lee como un "
        "resultado negativo del codigo examinado.",
        "ALCANCE: `source.` y no `binary.`. Coccinelle necesita FUENTES; no "
        "sirve sobre un `.ko` compilado. Es la capacidad para la pregunta "
        "que un grep no responde: 'todos los sitios donde se escribe un "
        "registro sin pasar por el helper'.",
        "LIMITE DE CORPUS: solo cubre lo que este en el corpus de fuente. "
        "El hallazgo 1556 midio que el corpus es una sola rama y hay 134 "
        "cabeceras fuera. Un `empty` aqui significa 'no coincide en ESTA "
        "rama', no 'no coincide en el driver'.",
    ],
    no_medidas=["Coccinelle sobre el corpus del kernel (requiere las fuentes "
                "completas; solo se midio sobre codigo sintetico)"],
    unsuitable=["cualquier pregunta sobre un binario (.ko): necesita fuente"],
)



def backends() -> Dict[str, Dict[str, Any]]:
    return _BACKENDS


def get(backend_id: str) -> Dict[str, Any]:
    if backend_id not in _BACKENDS:
        raise KeyError("backend desconocido: %s (hay: %s)"
                       % (backend_id, ", ".join(sorted(_BACKENDS))))
    return _BACKENDS[backend_id]


def ficha(backend_id: str) -> Dict[str, Any]:
    """Lo que se puede AFIRMAR de un backend. Verificado en runtime."""
    e = get(backend_id)
    b: Backend = e["backend"]
    d = dict(b.identidad())
    d.update({
        "capacities": e["capacities"],
        "capabilities_disponibles": sorted(k for k, v in e["capacities"].items()
                                           if v == "AVAILABLE"),
        "capabilities_parciales": sorted(k for k, v in e["capacities"].items()
                                        if v == "PARTIAL"),
        "capabilities_unsupported": sorted(k for k, v in e["capacities"].items()
                                           if v == "UNAVAILABLE"),
        "notas": e["notas"],
        "no_medido": e["no_medidas"],
        "inadequate_para": e["inadequate"],
        "matriz": os.path.relpath(MATRIX, PKG),
    })
    return d


def contrato() -> Dict[str, Any]:
    return contrato_de_backend(Backend("ejemplo", "true", []))


def decision() -> Dict[str, Any]:
    """La decision §18 leida del fichero. `NOT_DETERMINED` si no esta.

    No se "adivina" un PRIMARY si el fichero falta: se declara
    `NOT_DETERMINED` con el motivo. Un default escrito en el codigo seria una
    decision invisible, que es justo lo que §18 prohibe.
    """
    try:
        with open(DECISION, encoding="utf-8") as fh:
            return json.load(fh)
    except (OSError, ValueError) as e:
        return {"primary": "NOT_DETERMINED", "secondary": "NOT_DETERMINED",
                "analytical": "NOT_DETERMINED",
                "error": "no se pudo leer %s: %s" % (DECISION, e)}


def recuento_real() -> Dict[str, int]:
    """Cuantas capacidades cierra CADA backend con producer medido.

    MEDIDO: `AVAILABLE` y `PARTIAL` cuentan -- los dos tienen producer. Uno que
    emite ASCII cuenta igual que uno que emite JSON: cuenta como producer, y su
    limitacion vive en las notas. `UNAVAILABLE` y `NOT_DETERMINED` no cuentan.
    """
    return {bid: sum(1 for e in get(bid)["capacities"].values()
                     if e in ESTADOS_CON_PRODUCER)
            for bid in _BACKENDS}


def catalogo() -> List[Dict[str, Any]]:
    return [ficha(b) for b in sorted(_BACKENDS)]


#: Backends MEDIDOS que no se pueden verificar en esta maquina. Se declaran
#: para que su ausencia no parezca una conclusion.
NO_VERIFICABLES = [
    {"backend_id": "angr",
     "estado": "NOT_DETERMINED",
     "razon": "`import angr` funciona DENTRO del arbol porque el directorio "
              "clonado se llama `angr` y Python lo trata como namespace package "
              "(__file__ es None). Fuera del arbol: ModuleNotFoundError. No se "
              "comprobo que angr no sirva; se comprobo que no se puede "
              "VERIFICAR aqui.",
     "commit": "be995f52ee38a055d0f96d04f3e4d02192a3d743"},
    {"backend_id": "rz-ghidra",
     "estado": "NOT_DETERMINED",
     "razon": "requiere Ghidra + CMake + toolchain Java. Es la ruta de "
              "decompilacion y por eso NO se declara binary.decompile: "
              "declararla sin producer verificable seria exactamente el "
              "defecto que este contrato prohibe.",
     "commit": "64ea54a51c7f87983c9eba9cef8ee0c8cf2ac811"},
]