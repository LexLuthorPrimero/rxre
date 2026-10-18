#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0
"""RXRE-ECO-001. Registro canonico de repositorios externos vendorizados.

POR QUE UN MANIFEST Y NO UN `.txt`.

`REPOSITORIES.txt` (2026-10-06) solo guarda url/branch/commit/dirty. Eso basta
cuando la procedencia es *accessoria*. Aqui la procedencia es **estructural**:
el modulo §15 dice que una capacidad solo existe si su producer es
reproducible, y un producer clonado no es reproducible sin su commit exacto.

Por eso este manifest lleva, ademas del commit:

  *   `estrategia`   COMO se clonó. Un clon shallow y uno full NO son el mismo
                    artefacto: `git log` del shallow no alcanza al commit
                    anterior. Sin este campo, "reproducible" es falso.
  *   `alcance`      QUE hay. `linux` sparse no es el kernel.
  *   `verificado`   SI se comprobo que el contenido es el que se PIDIO.
                    Clonar no es verificar: un clon puede venir vacio, o con
                    otra rama, o sin el directorio que importa.
  *   `uso_rxre`     QUE capacidad lo consume, o `NINGUNO` si es referencia.

Y por que NO se declara `instalado`/`funciona` por haber clonado: §22 dice que
una herramienta no es valida porque ejecuta, y un clon es aun menos. El estado
real de cada uno lo establece `tools/rxre/tests/test_eco001.py`, que lo
COMPRUEBA, no lo Supone.

## USO

    python3 tools/rxre/vendor_manifest.py            # tabla legible
    python3 tools/rxre/vendor_manifest.py --json     # para maquinas
    python3 tools/rxre/vendor_manifest.py --verify   # comprueba en disco
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
from typing import Any, Dict, List

HERE = os.path.dirname(os.path.abspath(__file__))
RAIZ = os.path.dirname(os.path.dirname(HERE))
VENDORS = os.path.join(HERE, "github")

#: Clon = {url, estrategia, alcance, verificado, uso_rxre, categoria, por_que}
#:
#: `categoria` agrupa por NATURALEZA, no por fama. Determina si el repo puede
#: ser un `backend` (produce evidencia de una capacidad) o solo material de
#: estudio. Un orquestador de agentes NO es un producer de evidencia aunque
#: pueda ejecutarse: confundirlos es como declara una capacidad sin producer.
REPOS: List[Dict[str, Any]] = [
    # --- YA EXISTENTES ANTES DE ESTE TRABAJO (preservados, no reclonados) ---
    dict(nombre="rizin", url="https://github.com/rizinorg/rizin.git",
         commit="d14c3fac4126bc5fbe66e7f3d1660aeab22b01d8", rama="dev",
         estrategia="pre-existente (2026-10-06)", alcance="clon completo",
         verificado="si: usado por 6 adapters (rz_inspect, rz_functions, ...)",
         uso_rxre="binary.inspect, binary.functions, binary.xrefs, ...",
         categoria="backend", licencia="LGPL-3.0",
         por_que="ya era el backend primario de las capacidades binary.*"),
    dict(nombre="radare2", url="https://github.com/radareorg/radare2.git",
         commit="008a7a6cd2e5acb8268f65f486760d080f3b107b", rama="master",
         estrategia="pre-existente (2026-10-06)", alcance="clon completo",
         verificado="si: MEDIDO 201/202 funciones vs rizin 202 sobre /bin/ls",
         uso_rxre="comparador en binary.functions (control de cobertura)",
         categoria="backend", licencia="LGPL-3.0",
         por_que="el COMPARADOR: sin el, 'rizin funciona' no es una medida"),
    dict(nombre="angr", url="https://github.com/angr/angr.git",
         commit="be995f52ee38a055d0f96d04f3e4d02192a3d743", rama="master",
         estrategia="pre-existente (2026-10-06)", alcance="clon completo",
         verificado="NO: NOT_DETERMINED. Ver registry.py: `import angr` solo "
                    "funciona DENTRO del arbol (namespace package)",
         uso_rxre="NINGUNO (NOT_DETERMINED)",
         categoria="candidato-sin-producer", licencia="BSD-2",
         por_que="importable solo por accidente del path; no es un producer"),
    dict(nombre="rz-ghidra", url="https://github.com/rizinorg/rz-ghidra.git",
         commit="64ea54a51c7f87983c9eba9cef8ee0c8cf2ac811", rama="dev",
         estrategia="pre-existente (2026-10-06)", alcance="clon completo",
         verificado="NO: NOT_DETERMINED (requiere Ghidra + toolchain Java)",
         uso_rxre="NINGUNO (NOT_DETERMINED)",
         categoria="candidato-sin-producer", licencia="LGPL-3.0",
         por_que="la ruta de decompilacion; no hay producer verificado"),

    # --- NUEVOS: backends de analisis binario/fuente ------------------------
    dict(nombre="tree-sitter", url="https://github.com/tree-sitter/tree-sitter.git",
         commit="8ca548849fc8dbefd699edcec26546bb14112820", rama="master",
         estrategia="--depth 1 (shallow)", alcance="clon completo",
         verificado="si: 8.0M, CLI presente",
         uso_rxre="source.ast_parse (adapter ts_ast.py)",
         categoria="backend", licencia="MIT",
         por_que="AST real donde Coccinelle da diff: parseo, no coincidencia"),
    dict(nombre="semgrep", url="https://github.com/semgrep/semgrep.git",
         commit="51602ad27f09ef9342a5620601de5ef8f572fbc6", rama="develop",
         estrategia="--depth 1 (shallow)", alcance="clon completo",
         verificado="si: 621M, reglas en rules/",
         uso_rxre="source.semgrep_scan (adapter sg_scan.py)",
         categoria="backend", licencia="LGPL-2.1",
         por_que="SAST con interproceduralidad; un solo binario, sin build"),
    dict(nombre="scip", url="https://github.com/sourcegraph/scip.git",
         commit="e26a0b0fc83424dbfe6c703c0437d4703aec4aa0", rama="main",
         estrategia="--depth 1 (shallow)", alcance="clon completo",
         verificado="si: 2.0M, indice SCIP",
         uso_rxre="NINGUNO todavia (indice de referencia cruzada)",
         categoria="referencia", licencia="Apache-2.0",
         por_que="el formato de indice que un dia seria el grafo de llamadas"),
    dict(nombre="joern", url="https://github.com/joernio/joern.git",
         commit="f344c0f2ea45207452697e90a81870c219393339", rama="master",
         estrategia="--depth 1 (shallow)", alcance="clon completo",
         verificado="si: 104M, requiere JVM (Java 25 medido en este host)",
         uso_rxre="NINGUNO (CGP; debe verificarse antes de backend)",
         categoria="candidato", licencia="Apache-2.0",
         por_que="CPG: lo que rizin da como grafo de llamadas, joern da como "
                 "AST tipado. NO se integra sin producer medido"),

    # --- NUEVOS: referencia de hardware (NO son backends) ------------------
    dict(nombre="linux", url="https://github.com/torvalds/linux.git",
         commit="0fcb05b72344f40806cbe810de8872f1698bf053", rama="master",
         estrategia="sparse-checkout + --depth 1 (NO es el kernel completo)",
         alcance="drivers/gpu/drm/amd, include/uapi/drm, include/linux/drm",
         verificado="si: 641 ficheros en amdgpu/, 865M (no 3.3G)",
         uso_rxre="source.kernel_reference: UAPI amdgpu_drm.h, si_vrsd, GCash",
         categoria="referencia", licencia="GPL-2.0",
         por_que="la definicion de un registro en Linux es la SEMANTICA de "
                 "primer orden; umr da el valor, Linux da que significa"),
    dict(nombre="mesa", url="https://gitlab.freedesktop.org/mesa/mesa.git",
         commit="3c51dc0c602d6370e18ac1bfe7e6f6c68416fbbf", rama="main",
         estrategia="sparse-checkout + --depth 1", 
         alcance="src/gallium/drivers/radeonsi, include",
         verificado="si: CHIP_POLARIS12 presente (si_state_draw.cpp:887)",
         uso_rxre="source.kernel_reference: semantica GFX8 de registros",
         categoria="referencia", licencia="MIT",
         por_que="radeonsi SABE que significa cada registro GFX8. Es "
                 "diccionario semantico, no producer"),
    dict(nombre="drm", url="https://gitlab.freedesktop.org/mesa/drm.git",
         commit="b97cbde15c5c3abfe44d78e8f57139e50f612fec", rama="main",
         estrategia="--depth 1 (shallow)", alcance="clon completo",
         verificado="si: 4.4M, amdgpu_drm.h presente",
         uso_rxre="source.kernel_reference: UAPI oficial",
         categoria="referencia", licencia="MIT",
         por_que="la UAPI que el userspace puede usar sin nucleo"),
    dict(nombre="llvm-project",
         url="https://github.com/llvm/llvm-project.git",
         commit="1ac96b020a4ee54f36b4fcfc3ee3482e3ee72728", rama="main",
         estrategia="sparse-checkout + --depth 1 (NO es LLVM completo)",
         alcance="llvm/{include,lib/MC,tools/{objdump,llc}}, clang core",
         verificado="si: 416M (no 15G), headers presentes",
         uso_rxre="source.llvm_reference: MC layer para decodificar PM4",
         categoria="referencia", licencia="Apache-2.0-with-LLVM-exception",
         por_que="la capa MC de LLVM define la semantica de las "
                 "instrucciones que emite amdgpu, GFX8 incluido"),
    dict(nombre="piglit", url="https://gitlab.freedesktop.org/mesa/piglit.git",
         commit="54db23e", rama="master",
         estrategia="--depth 1 (shallow)", alcance="clon completo",
         verificado="NO: requiere compilacion con python + OpenGL ES",
         uso_rxre="NINGUNO (suite de validacion; NO ejecutada por ser GPU test)",
         categoria="validacion", licencia="MIT",
         por_que="NO se ejecuta: es prueba de hardware y el encargo prohibe "
                 "pruebas de hardware"),
    dict(nombre="VK-GL-CTS",
         url="https://github.com/KhronosGroup/VK-GL-CTS.git",
         commit="bee8372", rama="main",
         estrategia="--depth 1 (shallow)", alcance="clon completo",
         verificado="NO: requiere compilacion de ~1.8G con python",
         uso_rxre="NINGUNO (NO ejecutada: prueba de hardware)",
         categoria="validacion", licencia="Apache-2.0",
         por_que="referencia normativa. NO ejecutada: prueba de hardware"),

    # --- NUEVOS: orquestadores (NO son producers) --------------------------
    dict(nombre="openhands", url="https://github.com/All-Hands-AI/OpenHands.git",
         commit="5958302", rama="main",
         estrategia="--depth 1 (shallow)", alcance="clon completo",
         verificado="si: 38M",
         uso_rxre="NINGUNO (orquestador, no producer)",
         categoria="orquestador", licencia="MIT",
         por_que="arquetipo de agente con sandbox; util para comparar el "
                 "CICLO de RXRE, no para producir evidencia"),
    dict(nombre="swe-agent",
         url="https://github.com/SWE-agent/SWE-agent.git",
         commit="3ea751c", rama="main",
         estrategia="--depth 1 (shallow)", alcance="clon completo",
         verificado="si: 66M",
         uso_rxre="NINGUNO (orquestador)",
         categoria="orquestador", licencia="MIT",
         por_que="arquetipo de agente con LM y feedback loop"),
    dict(nombre="mini-swe-agent",
         url="https://github.com/SWE-agent/mini-swe-agent.git",
         commit="04d809c", rama="main",
         estrategia="--depth 1 (shallow)", alcance="clon completo",
         verificado="si: 3.2M",
         uso_rxre="NINGUNO (orquestador minimo)",
         categoria="orquestador", licencia="MIT",
         por_que="el minimo: 3.2M frente a 66M. El insight es la BREVEDAD"),
    dict(nombre="swe-rex", url="https://github.com/SWE-agent/SWE-ReX.git",
         commit="5c995c3", rama="main",
         estrategia="--depth 1 (shallow)", alcance="clon completo",
         verificado="si: 3.7M",
         uso_rxre="NINGUNO (orquestador)",
         categoria="orquestador", licencia="SEE LICENSE.txt",
         por_que="par de mini-swe; misma lineage"),
    dict(nombre="EvoAgent", url="https://github.com/mingbo-yang/EvoAgent.git",
         commit="377d014", rama="main",
         estrategia="--depth 1 (shallow)", alcance="clon completo",
         verificado="si: 2.7M",
         uso_rxre="NINGUNO (agente evolutivo)",
         categoria="orquestador", licencia="MIT",
         por_que="seleccion natural sobre agentes; NO es un producer"),

    # --- NUEVOS: infraestructura de evidencia ------------------------------
    dict(nombre="dvc", url="https://github.com/iterative/dvc.git",
         commit="56e5982", rama="main",
         estrategia="--depth 1 (shallow)", alcance="clon completo",
         verificado="si: 5.5M, `dvc` no instalado globalmente (a proposito)",
         uso_rxre="evidence.store_dvc (adapter ev_dvc.py) via venv aislado",
         categoria="evidencia", licencia="Apache-2.0",
         por_que="versionado de artefactos por CONTENIDO. RXRE guarda "
                 "resultados en sqlite: dvc daria el hash de verdad"),
    dict(nombre="mlflow", url="https://github.com/mlflow/mlflow.git",
         commit="60608bc", rama="master",
         estrategia="--depth 1 (shallow)", alcance="clon completo",
         verificado="si: 699M",
         uso_rxre="NINGUNO (tracking de métricas; RXRE mide distinto)",
         categoria="evidencia", licencia="Apache-2.0",
         por_que="el modelo de metricas NO encaja: RXRE evidencia rafistas, "
                 "no series de métricas de un experimento"),
    dict(nombre="openlineage",
         url="https://github.com/OpenLineage/OpenLineage.git",
         commit="f79de21", rama="main",
         estrategia="--depth 1 (shallow)", alcance="clon completo",
         verificado="si: 131M",
         uso_rxre="evidence.lineage (adapter ev_lineage.py): dataset lineage",
         categoria="evidencia", licencia="Apache-2.0",
         por_que="ENCADENA producer->artifact->consumer, que es literalmente "
                 "la cadena causal §14 de RXRE"),
    dict(nombre="beads", url="https://github.com/steveyegge/beads.git",
         commit="70b44da", rama="main",
         estrategia="--depth 1 (shallow)", alcance="clon completo",
         verificado="si: 77M",
         uso_rxre="NINGUNO (issue tracker con deps)",
         categoria="referencia", licencia="MIT",
         por_que="el grafo de dependencias de hallazgos, que RXRE hace a mano"),
    dict(nombre="Recuris", url="https://github.com/Gen-Verse/Recuris.git",
         commit="7d3745a", rama="main",
         estrategia="--depth 1 (shallow)", alcance="clon completo",
         verificado="si: 4.1M",
         uso_rxre="NINGUNO (framework de recursion)",
         categoria="referencia", licencia="MIT",
         por_que="iteracion autonoma; RXRE ya tiene el ciclo §105"),
    dict(nombre="reprocert",
         url="https://github.com/AETHERXGLOBAL/reprocert.git",
         commit="7ce802e", rama="main",
         estrategia="--depth 1 (shallow)", alcance="clon completo",
         verificado="si: 940K",
         uso_rxre="NINGUNO todavia (certificacion de reproducibilidad)",
         categoria="candidato", licencia="MIT",
         por_que="el concepto mas cercano al claim de RXRE: certificar que "
                 "un resultado se REPRODUCE"),
    dict(nombre="reproledger",
         url="https://github.com/Alqudimi/reproledger.git",
         commit="e0facb1", rama="main",
         estrategia="--depth 1 (shallow)", alcance="clon completo",
         verificado="si: 424K",
         uso_rxre="NINGUNO (ledger de reproducibilidad)",
         categoria="candidato", licencia="MIT",
         por_que="ledger: el mismo problema que RESERVAS.ledger de RXRE"),
    dict(nombre="research-evidence-agent",
         url="https://github.com/zxxasdfrty/research-evidence-agent.git",
         commit="c94b206", rama="main",
         estrategia="--depth 1 (shallow)", alcance="clon completo",
         verificado="si: 308K",
         uso_rxre="NINGUNO (agente de evidencia; MISMO objetivo que RXRE)",
         categoria="referencia", licencia="MIT",
         por_que="comparacion 1:1 del problema: agente que separa evidencia "
                 "de afirmacion"),
    dict(nombre="mem0", url="https://github.com/mem0ai/mem0.git",
         commit="0724291", rama="main",
         estrategia="--depth 1 (shallow)", alcance="clon completo",
         verificado="si: 59M",
         uso_rxre="NINGUNO (memoria para agentes)",
         categoria="referencia", licencia="Apache-2.0",
         por_que="memoria != evidencia: mem0 optimiza recall, RXRE.optimiza "
                 "Trazabilidad. No intercambiables"),
    dict(nombre="graphiti", url="https://github.com/getzep/graphiti.git",
         commit="aca3693", rama="main",
         estrategia="--depth 1 (shallow)", alcance="clon completo",
         verificado="si: 31M",
         uso_rxre="NINGUNO (memoria temporal con grafo)",
         categoria="referencia", licencia="Apache-2.0",
         por_que="grafo temporal de hallazgos; comparable a findings/"),
    dict(nombre="cognee", url="https://github.com/topoteretes/cognee.git",
         commit="f154b32", rama="main",
         estrategia="--depth 1 (shallow)", alcance="clon completo",
         verificado="si: 174M",
         uso_rxre="NINGUNO (memoria -> grafo de conocimiento)",
         categoria="referencia", licencia="Apache-2.0",
         por_que="el grafo que RXRE construye a mano en findings/"),
    dict(nombre="hindsight", url="https://github.com/vectorize-io/hindsight.git",
         commit="0794515", rama="main",
         estrategia="--depth 1 (shallow)", alcance="clon completo",
         verificado="si: 430M",
         uso_rxre="NINGUNO (memoria de agentes)",
         categoria="referencia", licencia="Apache-2.0",
         por_que="retencion a largo plazo de lo aprendido"),
    dict(nombre="langmem", url="https://github.com/langchain-ai/langmem.git",
         commit="48e3c11", rama="main",
         estrategia="--depth 1 (shallow)", alcance="clon completo",
         verificado="si: 4.2M",
         uso_rxre="NINGUNO (memoria para langchain)",
         categoria="referencia", licencia="MIT",
         por_que="dependencia de langchain; no aplica a RXRE"),
    dict(nombre="MemOS", url="https://github.com/MemTensor/MemOS.git",
         commit="a7367d0", rama="main",
         estrategia="--depth 1 (shallow)", alcance="clon completo",
         verificado="si: 47M",
         uso_rxre="NINGUNO (sistema operativo de memoria)",
         categoria="referencia", licencia="Apache-2.0",
         por_que="el mas cercano a 'memoria como infraestructura'"),

    # --- NUEVOS: benchmarks -------------------------------------------------
    dict(nombre="awesome-agentic-benchmarks",
         url="https://github.com/gray311/awesome-agentic-benchmarks.git",
         commit="9ddf444", rama="main",
         estrategia="--depth 1 (shallow)", alcance="clon completo",
         verificado="si: 1.5M, solo markdown",
         uso_rxre="NINGUNO (catalogo de benchmarks)",
         categoria="benchmark", licencia="CC0-1.0",
         por_que="NO son ejecutables: son una LISTA. Ninguna tarea es medible "
                 "aqui, y declararlas benchmark seria ficticio"),
    dict(nombre="awesome-agent-benchmarks",
         url="https://github.com/RDI-Foundation/awesome-agent-benchmarks.git",
         commit="47fb504", rama="main",
         estrategia="--depth 1 (shallow)", alcance="clon completo",
         verificado="si: 320K, solo markdown",
         uso_rxre="NINGUNO (catalogo de benchmarks)",
         categoria="benchmark", licencia="MIT",
         por_que="idem: catalogo, no suite ejecutable"),

    # --- BLOQUEOS: solicitados y NO clonables -------------------------------
    dict(nombre="umr", url="https://github.com/tomstdenis/umr.git",
         commit="", rama="",
         estrategia="NO CLONABLE (repository not found)",
         alcance="n/a",
         verificado="SI el bloqueo: git ls-remote dice 'Repository not found' "
                    "para tomstdenis/umr, umr-dev/umr y tomstdenis/umr-devel",
         uso_rxre="gpu.register_read usa /usr/bin/umr (paquete Fedora "
                  "umr-1.0.11-2.fc44.x86_64), NO el clon",
         categoria="BLOQUEADO", licencia="GPL-2.0 (del paquete)",
         por_que="el REPO desaparecio; el BINARIO esta. La procedencia del "
                 "producer de registros es el RPM, no git. Documentado para "
                 "que nadie lo busque en el arbol creyendolo disponible"),
]


def _git(repo: str, *args: str) -> str:
    d = os.path.join(VENDORS, repo)
    if not os.path.isdir(os.path.join(d, ".git")):
        return ""
    try:
        return subprocess.run(["git", "-C", d] + list(args),
                              capture_output=True, text=True, timeout=60
                              ).stdout.strip()
    except (OSError, subprocess.SubprocessError):
        return ""


def verificar() -> List[Dict[str, Any]]:
    """Comprueba en disco lo que el manifest AFIRMA. No lo re-deriva.

    Distingue tres cosas que un `git clone` seguido de exito mezcla:
      *   el commit del manifest es el de HEAD        (deriva)
      *   HEAD tiene el contenido que se promised   (verifica)
    """
    out = []
    for r in REPOS:
        d = os.path.join(VENDORS, r["nombre"])
        fila = {
            "nombre": r["nombre"], "categoria": r["categoria"],
            "manifest_commit": r["commit"],
            "head_commit": _git(r["nombre"], "rev-parse", "HEAD")[:40],
            "en_disco": os.path.isdir(d),
            "tiene_git": os.path.isdir(os.path.join(d, ".git")),
            "estrategia": r["estrategia"],
        }
        fila["commit_coincide"] = bool(
            fila["manifest_commit"] and
            fila["head_commit"].startswith(fila["manifest_commit"][:7]))
        if fila["en_disco"]:
            try:
                p = subprocess.run(["du", "-sh", d], capture_output=True,
                                   text=True, timeout=120)
                fila["size"] = p.stdout.split()[0] if p.stdout.strip() else "?"
            except (OSError, subprocess.SubprocessError):
                fila["size"] = "?"
        else:
            fila["size"] = "-"
        out.append(fila)
    return out


def tabla() -> str:
    filas = verificar()
    por_cat: Dict[str, int] = {}
    for f in filas:
        por_cat[f["categoria"]] = por_cat.get(f["categoria"], 0) + 1

    L = []
    L.append("RXRE-ECO-001 — registro canonico de repos externos")
    L.append("raiz de clones: %s" % VENDORS)
    L.append("")
    L.append("%-28s %-24s %-10s %-7s %s"
             % ("REPO", "CATEGORIA", "COMMIT", "SIZE", "COINCIDE"))
    L.append("-" * 84)
    for f in sorted(filas, key=lambda x: (x["categoria"], x["nombre"])):
        L.append("%-28s %-24s %-10s %-7s %s"
                 % (f["nombre"], f["categoria"],
                    (f["head_commit"] or "-")[:10], f["size"],
                    "si" if f["commit_coincide"] else
                    ("NO" if f["en_disco"] else "-")))
    L.append("-" * 84)
    L.append("total: %d repos" % len(filas))
    for c, n in sorted(por_cat.items()):
        L.append("  %-24s %d" % (c, n))
    return "\n".join(L)


def main() -> int:
    if "--verify" in sys.argv:
        filas = verificar()
        bad = [f for f in filas
               if f["categoria"] != "BLOQUEADO" and not f["commit_coincide"]]
        print(json.dumps({"verificacion": filas, "discrepancias": len(bad)},
                         indent=2, ensure_ascii=False))
        return 1 if bad else 0
    if "--json" in sys.argv:
        print(json.dumps({"repos": REPOS, "verificacion": verificar()},
                         indent=2, ensure_ascii=False))
        return 0
    print(tabla())
    return 0


if __name__ == "__main__":
    sys.exit(main())
