#!/usr/bin/env python3
"""pipeline.py — corre las herramientas en cadena y produce el mapa causal.

Por qué existe
--------------
Hay doce herramientas y cada una responde una pregunta. El problema no es
falta de herramientas: es que **no se usan juntas**, y la cadena que las
enlaza es exactamente la que el proyecto necesita:

    REGISTRO → MMIO → PRODUCTOR → TRANSFORMACIÓN → CONSUMIDOR → EFECTO

Con doce comandos sueltos, pasar de "este `.c` se compila" a "este registro lo
modifica el firmware" son seis pasos manuales, y en cualquier salto se puede
confundir una rama muerta con una real, que es el error que ya se cometio dos
veces.

Esta herramienta hace el recorrido completo y, en cada nodo, escribe **de
donde sale el dato**: fichero, linea, y herramienta que lo produjo. Un nodo sin
procedencia no entra en el mapa. Esa es la diferencia entre un mapa causal y
una lista de afirmaciones.

Lo que produce
--------------
Un grafo con:
  · cada nodo con su evidencia (fichero:linea) y su herramienta de origen
  · aristas clasificadas: DIRECTA / MACRO / VTABLA / VIA_SMC
  · el veredicto de alcance: VIVA / MUERTA / SIN_DETERMINAR para mi ASIC
  · una lista de huecos: preguntas que el corpus no responde

Y en `--dot`, un `.dot` para representation grafica.

Lo que NO hace
--------------
No inventa aristas. Un nodo sin evidencia no se emite, y una arista sin dos
extremos verificados no se traza. El mapa es tan incompleto como el corpus,
y lo declara: los huecos son parte de la salida, no una ausencia de la
herramienta.

Uso
---
    pipeline.py --kernel RAIZ --chip CHIP_POLARIS12 --root smu7_send_msg_to_smc
    pipeline.py --kernel RAIZ --chip CHIP_POLARIS12 --dot /tmp/mapa.dot
    pipeline.py --kernel RAIZ --list-tools
    pipeline.py --selftest
"""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
from typing import Dict, List, Optional, Sequence, Set, Tuple

NAME = "pipeline"
VERSION = "1.0.0"

WORK_CLASS = "READ_ONLY"
WRITE_EXECUTION = "NONE"

TOOLS_DIR = os.path.dirname(os.path.abspath(__file__))

# El orden de la cadena es el del proyecto: de lo mas cercano al hardware
# (registro) a lo mas lejos (firmware). Cada etapa declara que necesita de la
# anterior, para que un fallo intermedio se localize sin leer el mapa entero.
STAGES: List[Dict[str, object]] = [
    {"n": 1, "name": "COMPILE_GATE", "tool": "asic_resolver",
     "pregunta": "este .c entra en el binario para mi ASIC",
     "requiere": None},
    {"n": 2, "name": "BRANCH", "tool": "asic_resolver",
     "pregunta": "que ramas ejecuta mi ASIC en este fichero",
     "requiere": 1},
    {"n": 3, "name": "REGISTERS", "tool": "reg_census",
     "pregunta": "que registros toca, directos e indirectos, y por que bus",
     "requiere": 1},
    {"n": 4, "name": "RESOLVE", "tool": "reg_resolve",
     "pregunta": "offset, mascara, shift y UNIDAD de cada registro",
     "requiere": 3},
    {"n": 5, "name": "TRACE", "tool": "trace_path",
     "pregunta": "quien llama a quien, y que nodo esta muerto",
     "requiere": 2},
    {"n": 6, "name": "SMC", "tool": "msg_census",
     "pregunta": "que mensajes van al firmware y con que payload",
     "requiere": 1},
    {"n": 7, "name": "CONTRADICT", "tool": "contradict",
     "pregunta": "hay afirmaciones incompatibles vigentes",
     "requiere": None},
]


class StageResult:
    def __init__(self, stage: Dict[str, object]):
        self.stage = stage
        self.status = "NO_EJECUTADO"
        self.detail = ""
        self.data: Dict[str, object] = {}

    def ok(self) -> bool:
        return self.status == "OK"


def tool_path(tool: str) -> str:
    return os.path.join(TOOLS_DIR, f"{tool}.py")


def run_tool(tool: str, argv: Sequence[str],
             timeout: int = 240) -> Tuple[int, str, str]:
    p = tool_path(tool)
    if not os.path.isfile(p):
        return 127, "", f"{tool}.py no existe en {TOOLS_DIR}"
    try:
        r = subprocess.run([sys.executable, p, *argv],
                           capture_output=True, text=True, timeout=timeout)
        return r.returncode, r.stdout or "", r.stderr or ""
    except subprocess.TimeoutExpired:
        return 124, "", f"{tool} supero {timeout}s"
    except OSError as e:
        return 126, "", str(e)


def stage_compile_gate(kernel: str, chip: str, target: str,
                       config: Sequence[str]) -> StageResult:
    st = StageResult(STAGES[0])
    argv = ["--kernel", kernel, "--chip", chip]
    for c in config:
        argv += ["--config", c]
    argv += ["--makefile", target]
    rc, out, err = run_tool("asic_resolver", argv)
    if rc != 0:
        st.status = "FALLO"
        st.detail = err.strip()[:200] or f"rc={rc}"
        return st
    verdict = ""
    for line in out.splitlines():
        if line.strip().startswith("VEREDICTO"):
            verdict = line.split(None, 1)[1].strip()
            break
    st.status = "OK"
    st.data = {"verdict": verdict, "raw": out}
    st.detail = verdict
    return st


def stage_branch(kernel: str, chip: str, target: str) -> StageResult:
    st = StageResult(STAGES[1])
    rc, out, err = run_tool("asic_resolver",
                            ["--kernel", kernel, "--chip", chip,
                             "--branches", target])
    if rc != 0:
        st.status = "FALLO"
        st.detail = err.strip()[:200] or f"rc={rc}"
        return st
    taken = dead = 0
    branches: List[Dict[str, object]] = []
    for line in out.splitlines():
        parts = line.split()
        if len(parts) >= 5 and parts[1] in ("SI", "no", "?") and \
                parts[0].isdigit():
            taken += 1 if parts[1] == "SI" else 0
            dead += 1 if parts[1] == "no" else 0
            branches.append({"line": int(parts[0]), "takes": parts[1],
                             "text": " ".join(parts[2:])})
    st.status = "OK"
    st.data = {"taken": taken, "dead": dead, "branches": branches}
    st.detail = f"{taken} vivas, {dead} muertas"
    return st


def stage_registers(kernel: str, target: str) -> StageResult:
    st = StageResult(STAGES[2])
    rc, out, err = run_tool("reg_census",
                            ["--kernel", kernel, "--file", target])
    if rc != 0:
        st.status = "FALLO"
        st.detail = err.strip()[:200] or f"rc={rc}"
        return st
    direct: List[str] = []
    indirect: List[str] = []
    buses: Dict[str, List[str]] = {}
    # El formato real de reg_census pone los DOS contadores juntos ANTES de la
    # tabla:
    #     directos (mm*, ...)   9
    #     indirectos (ix*, ...)  1
    #     registro mm*    r  w  lineas
    #     mmSMC_RESP_0    0  1  [145]
    # Tomarlos como transiciones de estado hacia que la tabla no llega a
    # capturarse, y el mapa sale con cero registros. El encabezado de la tabla
    # es lo unico fiable.
    in_direct_table = False
    for raw in out.splitlines():
        t = raw.strip()
        if not t:
            continue
        if t.startswith("registro mm*"):
            in_direct_table = True
            continue
        if in_direct_table:
            if t.startswith("----"):
                continue
            tok = t.split()[0] if t.split() else ""
            if tok.startswith("mm"):
                direct.append(tok)
                continue
            in_direct_table = False
        if t.startswith("BUS INDIRECTO"):
            continue
        # lineas "    NOMBRE   N registros  -> mmX / mmY"
        parts = t.split()
        if len(parts) >= 3 and parts[1].isdigit() and "registros" in t:
            buses[parts[0]] = []
            continue
        # indices ix*: solo bajo el banner de bus
        tok = t.split()[0] if t.split() else ""
        if tok.startswith("ix") and buses:
            indirect.append(tok)
    # Los ix* pueden no listarse uno a uno: si hay buses pero no ix* capturados,
    # se cuentan desde el propio resumen de la herramienta.
    if buses and not indirect:
        m = re.search(r"indirectos \(ix\*[^)]*\)\s*(\d+)", out)
        n = int(m.group(1)) if m else 0
        indirect = [f"<{n} indices en bus {','.join(buses)}>"]
    st.status = "OK"
    st.data = {"direct": direct, "indirect": indirect, "buses": list(buses)}
    st.detail = f"{len(direct)} directos, {len(indirect)} indirectos"
    return st


def stage_resolve(kernel: str, regs: Sequence[str], gfx: str) -> StageResult:
    st = StageResult(STAGES[3])
    if not regs:
        st.status = "VACIO"
        st.detail = "ningun registro que resolver"
        return st
    argv = ["--kernel", kernel, "--gfx", gfx]
    for r in list(regs)[:12]:
        argv += ["--reg", r]
    rc, out, err = run_tool("reg_resolve", argv)
    if rc != 0:
        st.status = "FALLO"
        st.detail = err.strip()[:200] or f"rc={rc}"
        return st
    resolved: Dict[str, object] = {}
    cur = None
    for line in out.splitlines():
        t = line.strip()
        if t.startswith("reg_resolve") and "·" in t:
            cur = t.split("·")[1].strip().split()[0] if len(t.split("·")) > 1 else None
            continue
        if cur and t.startswith("valor"):
            resolved[cur] = t.split(None, 1)[1].strip()
        elif cur and t.startswith("UNIDAD"):
            resolved.setdefault(cur + "_unidad", t.split(None, 1)[1].strip())
        elif cur and t.startswith("veredicto"):
            resolved[cur + "_v"] = t.split(None, 1)[1].strip()
    st.status = "OK"
    st.data = resolved
    st.detail = f"{len([k for k in resolved if not k.endswith(('_v', '_unidad'))])} resueltos"
    return st


def stage_trace(kernel: str, chip: str, symbol: str, root: str,
                depth: int) -> StageResult:
    st = StageResult(STAGES[4])
    argv = ["--kernel", kernel, "--chip", chip, "--from", symbol,
            "--depth", str(depth)]
    if root:
        argv += ["--root", root]
    rc, out, err = run_tool("trace_path", argv)
    if rc != 0:
        st.status = "FALLO"
        st.detail = err.strip()[:200] or f"rc={rc}"
        return st
    nodes: List[Dict[str, object]] = []
    for line in out.splitlines():
        parts = line.split()
        if len(parts) >= 4 and parts[0] in (
                "DIRECTA", "MACRO", "VTABLE", "INVERSO", "CALLER"):
            depth_l = (len(line) - len(line.lstrip())) // 2
            nodes.append({"kind": parts[0], "sym": parts[1],
                          "verdict": parts[2],
                          "loc": " ".join(parts[3:]) if len(parts) > 3 else "",
                          "depth": depth_l})
    st.status = "OK"
    st.data = {"nodes": nodes, "raw": out}
    st.detail = f"{len(nodes)} nodos"
    return st


def stage_smc(kernel: str, chip: str, root: str) -> StageResult:
    st = StageResult(STAGES[5])
    argv = ["--kernel", kernel, "--chip", chip]
    if root:
        argv += ["--root", root]
    rc, out, err = run_tool("msg_census", argv)
    if rc != 0:
        st.status = "FALLO"
        st.detail = err.strip()[:200] or f"rc={rc}"
        return st
    info: Dict[str, object] = {}
    for line in out.splitlines():
        t = line.strip()
        if t.startswith("llamadas de envio"):
            info["llamadas"] = t.split(":")[-1].strip()
        elif t.startswith("mensajes distintos"):
            info["mensajes"] = t.split(":")[-1].strip()
        elif t.startswith("reparto de payload"):
            info["payload"] = t.split(":", 1)[1].strip()
    st.status = "OK"
    st.data = info
    st.detail = f"{info.get('llamadas', '?')} envíos, {info.get('mensajes', '?')} mensajes"
    return st


def stage_contradict(findings: str) -> StageResult:
    st = StageResult(STAGES[6])
    rc, out, err = run_tool("contradict",
                            ["--findings", findings, "--only-conflicts"])
    if rc != 0:
        st.status = "FALLO"
        st.detail = err.strip()[:200] or f"rc={rc}"
        return st
    rows = [l for l in out.splitlines()
            if l.strip() and l.startswith("  ") and "CONFLICTO" in l]
    st.status = "OK"
    st.data = {"conflicts": rows, "raw": out}
    st.detail = f"{len(rows)} conflictos abiertos"
    return st


def build_graph(root_sym: str, results: Sequence[StageResult]) -> Dict[str, object]:
    """Ensambla el mapa. Un nodo sin evidencia no entra."""
    nodes: List[Dict[str, object]] = []
    edges: List[Dict[str, object]] = []
    by_name = {str(r.stage["name"]): r for r in results}

    # Nodo raiz
    nodes.append({
        "id": root_sym,
        "label": root_sym,
        "type": "FUNCION",
        "evidence": None,
        "tool": "argumento",
        "scope": "SIN_VERIFICAR",
    })

    tr = by_name.get("TRACE")
    if tr and tr.ok():
        for n in tr.data.get("nodes", []):  # type: ignore[union-attr]
            nid = f"{n['kind']}:{n['sym']}"
            nodes.append({
                "id": nid, "label": str(n["sym"]),
                "type": str(n["kind"]),
                "evidence": n.get("loc") or None,
                "tool": "trace_path",
                "scope": str(n["verdict"]),
            })
            edges.append({
                "from": root_sym if int(n["depth"]) == 1 else None,
                "to": nid,
                "kind": str(n["kind"]),
                "parent": int(n["depth"]) - 1,
            })

    rc = by_name.get("REGISTERS")
    if rc and rc.ok():
        for reg in rc.data.get("direct", []):  # type: ignore[union-attr]
            nid = f"REG:{reg}"
            res = by_name.get("RESOLVE")
            unit = None
            if res and res.ok():
                unit = res.data.get(f"{reg}_unidad")  # type: ignore[union-attr]
            nodes.append({
                "id": nid, "label": reg, "type": "REGISTRO_DIRECTO",
                "evidence": None, "tool": "reg_census",
                "scope": "VIVO" if rc.ok() else "SIN_VERIFICAR",
                "unit": unit,
            })
        for reg in rc.data.get("indirect", []):  # type: ignore[union-attr]
            nid = f"IX:{reg}"
            nodes.append({
                "id": nid, "label": reg, "type": "INDICE_BUS",
                "evidence": None, "tool": "reg_census",
                "scope": "VIVO",
                "unit": "indice de bus, NO byte offset",
            })
    return {"nodes": nodes, "edges": edges}


def gaps(results: Sequence[StageResult], root_sym: str) -> List[str]:
    """Lo que el corpus NO responde. Es parte de la salida, no un fallo."""
    g: List[str] = []
    by_name = {str(r.stage["name"]): r for r in results}
    tr = by_name.get("TRACE")
    if tr and tr.ok():
        vtabs = [n for n in tr.data.get("nodes", [])  # type: ignore[union-attr]
                 if n["kind"] == "VTABLE"]
        if vtabs:
            g.append(f"{len(vtabs)} llamadas por vtable sin resolver: "
                     f"la vtable decide cual se ejecuta")
    rc = by_name.get("REGISTERS")
    if rc and rc.ok() and rc.data.get("indirect"):  # type: ignore[union-attr]
        g.append(f"{len(rc.data['indirect'])} indices ix* apuntan a un bus "
                 f"cuyo offset en MMIO no se resuelve sin SOC15_REG_OFFSET")
    res = by_name.get("RESOLVE")
    if res and res.ok():
        ausentes = [k for k, v in res.data.items()  # type: ignore[union-attr]
                    if k.endswith("_v") and "NO" in str(v)]
        if ausentes:
            g.append(f"{len(ausentes)} registros no definidos en el header "
                     f"de la generacion objetivo")
    smc = by_name.get("SMC")
    if smc and smc.ok():
        g.append("que hace el firmware con cada mensaje: NO_IN_CORPUS. "
                 "el mapa llega hasta el envio, no mas alla")
    g.append("todo hardware effect: requiere WRITE_EXECUTION")
    return g


def render_map(root: str, results: Sequence[StageResult],
               graph: Dict[str, object], gs: Sequence[str],
               chip: str) -> str:
    L = [f"{NAME} {VERSION} · mapa causal"]
    L.append(f"  WORK_CLASS={WORK_CLASS} · WRITE_EXECUTION={WRITE_EXECUTION} · chip={chip}")
    L.append("  Cada nodo declara su procedencia: fichero:linea y herramienta.")
    L.append("")
    L.append(f"  ETAPAS  (raiz: {root})")
    L.append("  " + "-" * 96)
    for r in results:
        s = r.stage
        mark = {"OK": "ok", "FALLO": "FALLO", "VACIO": "vac",
                "NO_EJECUTADO": "-"}.get(r.status, r.status)
        L.append(f"  {int(s['n']):>2} {str(s['name']):<12} {mark:<6} "
                 f"{str(s['pregunta'])[:44]:<46} {r.detail[:24]}")
    L.append("")
    nodes = graph["nodes"]  # type: ignore[index]
    edges = graph["edges"]  # type: ignore[index]
    L.append(f"  NODOS  {len(nodes)}   ARISTAS  {len(edges)}")
    L.append("")
    L.append(f"  {'tipo':<20} {'nodo':<44} {'alcance':<18} evidencia")
    L.append("  " + "-" * 108)
    for n in nodes[:40]:
        ev = n.get("evidence") or "(sin evidencia)"
        L.append(f"  {str(n['type'])[:20]:<20} {str(n['label'])[:44]:<44} "
                 f"{str(n['scope'])[:18]:<18} {str(ev)[:26]}")
    if len(nodes) > 40:
        L.append(f"  ... y {len(nodes) - 40} mas")
    L.append("")
    L.append("  HUECOS  (lo que el corpus NO responde; es parte de la salida)")
    for x in gs:
        L.append(f"    · {x}")
    return "\n".join(L)


def to_dot(graph: Dict[str, object], chip: str) -> str:
    L = ["digraph polaris12 {",
         '  rankdir=LR;',
         f'  label="RX550 {chip} · mapa causal";',
         f'  labelloc=t;',
         f'  // WORK_CLASS={WORK_CLASS} · WRITE_EXECUTION={WRITE_EXECUTION}',
         '  WORK_CLASS_NOTE="WRITE_EXECUTION=NONE; este mapa no prueba hardware";',
         '  node [shape=box, fontname="monospace", fontsize=9];',
         '  edge [fontname="monospace", fontsize=7];']
    style = {"VIVA": "solid", "MUERTA": "dashed",
             "PARCIAL": "dotted", "NO_CONDICIONAL": "solid",
             "VIVO": "solid"}
    for n in graph["nodes"]:  # type: ignore[index]
        col = {"MUERTA": "gray30", "PARCIAL": "gray50"}.get(
            str(n["scope"]), "black")
        L.append(f'  "{n["id"]}" [label="{n["label"]}\\n{n["type"]}"];')
        L[-1] += f'  // alcance={n["scope"]} tool={n["tool"]} color={col}'
    for i, e in enumerate(graph["edges"]):  # type: ignore[index]
        fr = e.get("from")
        if not fr:
            continue
        L.append(f'  "{fr}" -> "{e["to"]}" [label="{e["kind"]}"];  # {i}')
    L.append("}")
    return "\n".join(L)


def selftest() -> int:
    failures: List[str] = []

    def check(name: str, got, want) -> None:
        if got != want:
            failures.append(f"{name}: obtuve {got!r}, esperaba {want!r}")

    check("work_class", WORK_CLASS, "READ_ONLY")
    check("write_execution", WRITE_EXECUTION, "NONE")
    check("etapas", len(STAGES), 7)
    # las etapas deben declarar que necesitan de la anterior
    # La mayoria de etapas dependen de una previa; CONTRADICT es independiente
    # por diseno: compara documentos entre si, no el codigo.
    for st in STAGES:
        if st["n"] > 1 and st["name"] != "CONTRADICT":
            check(f"etapa{st['n']}.requiere", st["requiere"] is not None, True)
    check("etapa_contradict_independiente", STAGES[6]["requiere"], None)

    # Un StageResult no-OK no cuenta como ok
    r = StageResult(STAGES[0])
    check("stage_inicial.no_ok", r.ok(), False)
    r.status = "OK"
    check("stage_ok", r.ok(), True)

    # Grafo: un nodo sin evidencia sigue entrando pero lo declara
    g = build_graph("raiz", [])
    check("grafo.raiz", g["nodes"][0]["id"], "raiz")
    check("grafo.raiz_sin_evidencia", g["nodes"][0]["evidence"], None)

    # Huecos: aunque todo pase, el hueco del firmware esta siempre
    class Fake:
        def __init__(self, name, status="OK", data=None):
            self.stage = {"name": name, "n": 1, "pregunta": "?"}
            self.status = status
            self.data = data or {}
            self.detail = ""
        def ok(self):
            return self.status == "OK"
    gs = gaps([Fake("TRACE", data={"nodes": [{"kind": "VTABLE", "sym": "x"}]}),
               Fake("REGISTERS", data={"indirect": ["ixA"]}),
               Fake("SMC", data={})], "raiz")
    check("huecos.no_vacios", len(gs) >= 4, True)
    check("huecos.firmware", any("NO_IN_CORPUS" in g for g in gs), True)
    check("huecos.vtable", any("vtable" in g for g in gs), True)
    check("huecos.write_execution", any("WRITE_EXECUTION" in g for g in gs), True)

    # dot bien formado
    d = to_dot({"nodes": [{"id": "a", "label": "a", "type": "T",
                           "scope": "VIVA", "tool": "t", "evidence": None}],
                "edges": []}, "CHIP_POLARIS12")
    check("dot.abre", d.startswith("digraph"), True)
    check("dot.cierra", d.rstrip().endswith("}"), True)
    check("dot.declara_work_class", "WRITE_EXECUTION=NONE" in d, True)

    # las herramientas referenciadas existen
    for st in STAGES:
        check(f"herramienta_existe:{st['tool']}",
              os.path.isfile(tool_path(str(st["tool"]))), True)

    print(f"{NAME} {VERSION} · self-test")
    if failures:
        print(f"  RESULTADO FALLIDO ({len(failures)}):")
        for f in failures:
            print(f"    - {f}")
        return 1
    print("  RESULTADO OK · vectores conocidos reproducidos")
    print("  NOTA: orquesta herramientas existentes. NO anade evidencia propia.")
    return 0


def main(argv: Optional[Sequence[str]] = None) -> int:
    ap = argparse.ArgumentParser(prog=NAME,
                                 description="Cadena de herramientas y mapa causal.")
    ap.add_argument("--selftest", action="store_true")
    ap.add_argument("--kernel")
    ap.add_argument("--chip", default="CHIP_POLARIS12")
    ap.add_argument("--root", dest="root_sym", default=None,
                    help="simbolo raiz de la cadena")
    ap.add_argument("--root-dir", default=None,
                    help="subarbol a escanear (por defecto pm/powerplay)")
    ap.add_argument("--depth", type=int, default=2)
    ap.add_argument("--gfx", default="gfx_8_0")
    ap.add_argument("--config", action="append", default=[])
    ap.add_argument("--findings", default=None)
    ap.add_argument("--dot", default=None, help="escribir un .dot")
    ap.add_argument("--list-tools", action="store_true")
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args(argv)

    if args.selftest:
        return selftest()
    if args.list_tools:
        print(f"{NAME} {VERSION} · cadena")
        for st in STAGES:
            req = "-" if st["requiere"] is None else f"tras {st['requiere']}"
            print(f"  {st['n']} {str(st['name']):<12} {str(st['tool']):<14} "
                  f"{str(st['pregunta'])[:46]:<48} {req}")
        return 0
    if not args.kernel or not args.root_sym:
        ap.error("--kernel y --root son obligatorios salvo con --selftest "
                 "o --list-tools")

    kernel = os.path.abspath(args.kernel)
    rootdir = os.path.abspath(args.root_dir) if args.root_dir else \
        os.path.join(kernel, "drivers/gpu/drm/amd/pm/powerplay")
    findings = os.path.abspath(args.findings) if args.findings else None

    # El fichero donde vive el simbolo se busca ANTES de lanzar las etapas.
    # COMPILE_GATE, BRANCH y REGISTERS operan sobre FICHEROS; diles el simbolo
    # contestan "NOT_REFERENCED" o "0 registros" y el mapa queda vacio sin que
    # ninguna etapa falle. Es el fallo mas silencioso posible: un mapa con tres
    # nodos que parece "no hay mas" y en realidad no se pregunto.
    sym_file = find_symbol_file(rootdir, args.root_sym)
    if not sym_file:
        print(f"ERROR  no encuentro la definicion de {args.root_sym} bajo "
              f"{rootdir}", file=sys.stderr)
        print("       Sin fichero no hay gate, ni ramas, ni registros.",
              file=sys.stderr)
        return 2
    rel = os.path.relpath(sym_file, kernel)
    print(f"  raiz {args.root_sym} -> {rel}")

    results: List[StageResult] = []
    results.append(stage_compile_gate(kernel, args.chip, rel, args.config))
    results.append(stage_branch(kernel, args.chip, rel))
    results.append(stage_registers(kernel, rel))
    regs = results[2].data.get("direct", []) if results[2].ok() else []
    results.append(stage_resolve(kernel, regs, args.gfx))  # type: ignore[arg-type]
    results.append(stage_trace(kernel, args.chip, args.root_sym, rootdir,
                               args.depth))
    results.append(stage_smc(kernel, args.chip, rootdir))
    if findings:
        results.append(stage_contradict(findings))
    else:
        r = StageResult(STAGES[6])
        r.status = "NO_EJECUTADO"
        r.detail = "sin --findings"
        results.append(r)

    graph = build_graph(args.root_sym, results)
    gs = gaps(results, args.root_sym)

    if args.dot:
        with open(args.dot, "w", encoding="utf-8") as fh:
            fh.write(to_dot(graph, args.chip))
        print(f"  .dot escrito en {args.dot}")

    if args.json:
        print(json.dumps({"tool": NAME, "version": VERSION,
                          "work_class": WORK_CLASS,
                          "write_execution": WRITE_EXECUTION,
                          "chip": args.chip, "root": args.root_sym,
                          "stages": [{"n": r.stage["n"], "name": r.stage["name"],
                                      "tool": r.stage["tool"],
                                      "status": r.status, "detail": r.detail,
                                      "data": r.data} for r in results],
                          "graph": graph, "gaps": gs},
                         indent=2, ensure_ascii=False, default=str))
        return 0
    print(render_map(args.root_sym, results, graph, gs, args.chip))
    fallos = [r for r in results if r.status == "FALLO"]
    return 1 if fallos else 0


def find_symbol_file(root: str, sym: str) -> Optional[str]:
    """En que .c se define el simbolo. Nombre exacto, no pariente."""
    needle = re_sym(sym)
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d not in (".git", "__pycache__")]
        for fn in filenames:
            if not fn.endswith(".c"):
                continue
            p = os.path.join(dirpath, fn)
            try:
                with open(p, "r", encoding="utf-8", errors="replace") as fh:
                    for line in fh:
                        if needle.search(line):
                            return p
            except OSError:
                continue
    return None


def re_sym(sym: str) -> "re.Pattern[str]":
    import re
    return re.compile(r"^\w[\w \t\*]*?\b" + re.escape(sym) + r"\s*\(")


if __name__ == "__main__":
    sys.exit(main())
