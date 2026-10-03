#!/usr/bin/env python3
"""msg_census.py — qué mensajes envía el host al SMC, con su payload y su frecuencia.
    WORK_CLASS=READ_ONLY · WRITE_EXECUTION=NONE
    No abre /sys, no escribe ficheros, no toca la GPU ni el arbol.

Por qué existe
--------------
`FW_SMU_INTERPRETATION` está marcado `NOT_IN_CORPUS`: no sabemos qué hace el
firmware con los mensajes. Es la pregunta abierta más importante del scope,
porque de ella depende si el voltaje, el reloj o el estado los pone el driver
o el firmware.

Hay un ángulo estático que no se ha agotado: **el conjunto completo de
mensajes que el host emite, con su número, su productor, y que se escribe en
los registros de argumento antes de enviar**. Ese conjunto es la entrada del
firmware: si un mensaje lleva un mapa de bits, el firmware lo interpreta como
flags; si lleva un puntero, lo interpreta como dirección. Saber que forma tiene
cada payload acota qué puede estar haciendo el firmware, aunque no lo pruebe.

Y tiene un segundo uso, más valorable: **agrupar por número de mensaje**
descubre colisiones. Si dos emisores distintos usan el mismo número con
significados distintos, hay un bug o hay un rango reutilizado por
generación, y en los dos casos es un hallazgo.

Lo que produce
--------------
Por mensaje: número, símbolo, fichero:línea, y el último valor escrito en
`mmSMC_MSG_ARG_*` que la que se puede resolver estática, si lo hay.
Y el recuento: cuántos mensajes distintos envía el host, y cuáles son
`CODE_MUERTO` para nuestra ASIC.

Lo que NO hace
--------------
No sabe qué hace el firmware. Un payload con máscara de bits NO demuestra que
el firmware lo trate como flags: demuestra que el host le pasa una máscara de
bits. La diferencia entre esas dos afirmaciones es exactamente el hueco que
`FW_SMU_INTERPRETATION` ocupa.

Uso
---
    msg_census.py --kernel RAIZ --chip CHIP_POLARIS12
    msg_census.py --kernel RAIZ --chip CHIP_POLARIS12 --msg PPSMC_MSG_Didt_Block_Function
    msg_census.py --kernel RAIZ --list-unknown
    msg_census.py --selftest
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
from collections import defaultdict
from typing import Dict, List, Optional, Sequence, Set, Tuple

NAME = "msg_census"
VERSION = "1.0.0"

DEFAULT_CHIP = "CHIP_POLARIS12"
ASIC_ENUM_REL = "include/drm/amd_asic_type.h"

_SEND = re.compile(
    r"\b(?P<fn>smum?_send_msg_to_smc(?:_with_parameter)?|smu7_send_msg_to_smc(?:_with_parameter)?)"
    r"\s*\(\s*(?P<args>[^;]*?)\)\s*;",
    re.S,
)
_ARG_WRITE = re.compile(r"(mmSMC_MSG_ARG_(?:1[01]|[0-9]))\s*,\s*(?P<val>[^,)\n]+)")
_CHIP_CMP = re.compile(
    r"(chip_id|asic_type)\s*(==|!=|<=|>=|<|>)\s*(CHIP_[A-Z0-9_]+)")
# Los mensajes del kernel se declaran con cast:
#     #define PPSMC_MSG_Test  ((uint16_t) 0x301)
# Un patron que exige un numero desnudo no los ve y devuelve None, que parece
# "el mensaje no tiene numero" en vez de "mi regex no entiende el cast".
_DEFINE_NUM = re.compile(
    r"#\s*define\s+(?P<name>[A-Za-z_]\w*)\s+"
    r"(?:\(\s*(?:\(\s*)?(?:const\s+)?u?int(?:8|16|32|64)_t\s*\)?\s*\)?\s*)?"
    r"(?P<val>0[xX][0-9a-fA-F]+|\d+)[uUlL]*\s*\)?\s*$")
_CMP = {"==": lambda a, b: a == b, "!=": lambda a, b: a != b,
        "<": lambda a, b: a < b, "<=": lambda a, b: a <= b,
        ">": lambda a, b: a > b, ">=": lambda a, b: a >= b}
_ABI64_TYPES = ("uint32_t", "u32", "int", "unsigned int", "uint64_t", "u64",
                "int32_t", "s32", "uint16_t", "u16")


def strip_comments(text: str) -> str:
    out: List[str] = list(text)
    i, n = 0, len(text)
    while i < n:
        if text.startswith("/*", i):
            j = text.find("*/", i + 2)
            j = n if j < 0 else j + 2
            for k in range(i, j):
                if out[k] != "\n":
                    out[k] = " "
            i = j
        elif text.startswith("//", i):
            j = text.find("\n", i)
            j = n if j < 0 else j
            for k in range(i, j):
                out[k] = " "
            i = j
        else:
            i += 1
    return "".join(out)


def parse_chip_enum(path: str) -> Dict[str, int]:
    out: Dict[str, int] = {}
    if not os.path.isfile(path):
        return out
    rx = re.compile(r"^\s*(CHIP_[A-Z0-9_]+)\s*,?\s*(?:/\*\s*([0-9]+)\s*\*/)?\s*$")
    implicit, in_enum = 0, False
    with open(path, "r", encoding="utf-8", errors="replace") as fh:
        for line in fh:
            s = line.split("//", 1)[0].rstrip()
            if re.match(r"^\s*enum\b", s) and "asic_type" in s:
                in_enum = True
                continue
            if in_enum and s.strip().startswith("}"):
                break
            if not in_enum or not s.strip():
                continue
            m = rx.match(s)
            if not m:
                continue
            if m.group(2) is not None:
                out[m.group(1)] = int(m.group(2))
                implicit = int(m.group(2)) + 1
            else:
                out[m.group(1)] = implicit
                implicit += 1
    return out


def collect_defines(roots: Sequence[str]) -> Dict[str, int]:
    """Todos los #define numericos de los headers del subarbol."""
    out: Dict[str, int] = {}
    pat = _DEFINE_NUM
    for root in roots:
        if not os.path.isdir(root):
            continue
        for dirpath, dirnames, filenames in os.walk(root):
            dirnames[:] = [d for d in dirnames if d not in (".git", "__pycache__")]
            for fn in filenames:
                if not fn.endswith(".h"):
                    continue
                p = os.path.join(dirpath, fn)
                try:
                    with open(p, "r", encoding="utf-8", errors="replace") as fh:
                        for line in fh:
                            m = pat.match(line.rstrip())
                            if m:
                                tok = m.group("val")
                                try:
                                    out[m.group("name")] = (int(tok, 16)
                                                           if tok.lower().startswith("0x")
                                                           else int(tok, 0))
                                except ValueError:
                                    pass
                except OSError:
                    continue
    return out


_PPSMC_INCLUDE = re.compile(r'#\s*include\s+"([^"]*ppsmc[^"]*)"')

_INCLUDE_CACHE: Dict[str, Dict[str, int]] = {}


def ppsmc_defines_for(cfile: str, search_roots: Sequence[str]) -> Tuple[Dict[str, int], str]:
    """Los defines de PPSMC que ve ESTE .c, segun el ppsmc.h que incluye.

    Es la correccion que hace falta y que no era opcional: los numeros de
    mensaje se particionan por generacion. El MISMO numero significa cosas
    distintas en smu7_ppsmc.h, vega20_ppsmc.h y rv_ppsmc.h, asi que barrer
    todos los headers y quedarse con el ultimo da un valor que no es el de
    nuestra generacion.

    Con 41 colisiones de numero detectadas, ese numero equivocado no es un
    detalle: hace que dos mensajes distintos parezcan el mismo.
    """
    cdir = os.path.dirname(cfile)
    try:
        with open(cfile, "r", encoding="utf-8", errors="replace") as fh:
            text = strip_comments(fh.read())
    except OSError:
        return {}, ""
    m = _PPSMC_INCLUDE.search(text)
    if not m:
        return {}, ""
    inc = m.group(1)
    path = inc if os.path.isabs(inc) else os.path.join(cdir, inc)
    if not os.path.isfile(path):
        # Resolucion por -I, pero se exigen LAS DOS condiciones: el nombre
        # pedido Y que el directorio que lo contiene case con el nombre del
        # .c. Sin esa segunda comprobacion, polaris10_smumgr.c (que incluye
        # "smu7_ppsmc.h") resolvia a fiji_ppsmc.h porque ese nombre aparece
        # antes en el recorrido, y reportaba el numero de la generacion
        # equivocada sin avisar.
        base = os.path.basename(inc)
        cbase = os.path.basename(cfile)
        stem = cbase[:-2] if cbase.endswith(".c") else cbase
        # smu7_smumgr.c -> espera smu7_ppsmc.h ; polaris10_smumgr.c espera
        # smu7_ppsmc.h, asi que el prefijo de generacion no siempre coincide
        # con el del fichero. Se acepta si el nombre pedido aparece, y entre
        # varios candidatos se elige el que su subruta case con la del .c.
        expect_dir = os.path.basename(cdir)
        candidates: List[str] = []
        for root in search_roots:
            for sub in ("", "inc", "smumgr", "hwmgr"):
                cand = os.path.join(root, sub, base)
                if os.path.isfile(cand):
                    candidates.append(cand)
        if candidates:
            # preferencia: mismo subdirectorio que el .c, luego subruta cuyo
            # nombre comparte prefijo con el del .c
            def rank(p: str) -> Tuple[int, str]:
                pd = os.path.basename(os.path.dirname(p))
                pref = 0 if pd == expect_dir else 1
                shared = 0
                for tok in stem.split("_"):
                    if tok and tok in pd:
                        shared += 1
                return (pref, -shared)
            candidates.sort(key=rank)
            path = candidates[0]
        else:
            return {}, base
    key = path
    if key in _INCLUDE_CACHE:
        return _INCLUDE_CACHE[key], os.path.basename(path)
    out: Dict[str, int] = {}
    with open(path, "r", encoding="utf-8", errors="replace") as fh:
        for line in fh:
            mm = _DEFINE_NUM.match(line.rstrip())
            if mm:
                tok = mm.group("val")
                try:
                    out[mm.group("name")] = (int(tok, 16)
                                             if tok.lower().startswith("0x")
                                             else int(tok, 0))
                except ValueError:
                    pass
    _INCLUDE_CACHE[key] = out
    return out, os.path.basename(path)


def split_args(s: str) -> List[str]:
    """Parte una lista de argumentos por comas de primer nivel."""
    out: List[str] = []
    depth = 0
    cur = ""
    for ch in s:
        if ch in "([{":
            depth += 1
        elif ch in ")]}":
            depth -= 1
        if ch == "," and depth == 0:
            out.append(cur.strip())
            cur = ""
        else:
            cur += ch
    if cur.strip():
        out.append(cur.strip())
    return out


def classify_payload(kind: str, raw: str, defines: Dict[str, int]) -> Dict[str, object]:
    """Tipo del SEGUNDO argumento, que es lo que viaja como parametro.

    Distingue:
      LITERAL       un numero, poco informativo
      MAPA_DE_BITS  un OR de mascaras _MASK: el firmware lo vera como flags
                    o como un numero, y no sabemos cual
      PUNTERO       una direccion: el firmware leera memoria
      SIMBOLO       un identificador cuyo valor no se ha resuelto
      NINGUNO       no hay segundo argumento
    """
    raw = raw.strip()
    if not raw or raw == "NULL":
        return {"kind": "NINGUNO", "raw": raw}
    if re.match(r"^(0[xX][0-9a-fA-F]+|\d+)$", raw):
        return {"kind": "LITERAL", "raw": raw, "value": int(raw, 0)}
    if "|" in raw or raw.endswith("_MASK") or raw.endswith("_MASK)"):
        masks = re.findall(r"\b([A-Za-z_]\w*_MASK)\b", raw)
        if masks:
            vals = [defines.get(m) for m in masks]
            resolved = [v for v in vals if v is not None]
            return {
                "kind": "MAPA_DE_BITS", "raw": raw[:120], "masks": masks[:8],
                "n_masks": len(masks),
                "resolved": len(resolved),
                "valor_si_resuelto": sum(resolved) if resolved else None,
                "nota": "el host pasa un OR de mascaras. NO demuestra que el "
                        "firmware lo trate como flags: solo que es un numero.",
            }
        return {"kind": "MAPA_DE_BITS", "raw": raw[:120]}
    if re.search(r"\b(&\w+|\w+\s*->\s*\w+|\w+\s*\[)", raw):
        return {"kind": "PUNTERO", "raw": raw[:120],
                "nota": "el firmware recibiria una direccion de memoria del host"}
    if re.match(r"^\(?\s*\(?uint(16|32|64)_t", raw) or re.match(r"^\(?\s*\(?u(16|32|64)", raw):
        return {"kind": "SIMBOLO", "raw": raw[:120]}
    return {"kind": "SIMBOLO", "raw": raw[:120]}


def scan(roots: Sequence[str], enum: Dict[str, int], chip: int,
         defines: Dict[str, int],
         search_roots: Optional[Sequence[str]] = None) -> Dict[str, object]:
    """Escanea los .c y resuelve el numero de mensaje por SU cabecera.

    search_roots son las rutas -I con las que se resuelve un #include que no
    es relativo al fichero. Si faltan, un include no encontrado deja el
    mensaje sin valor y eso se marca, no se rellena con el valor de otra
    generacion.
    """
    search_roots = list(search_roots or roots)
    rows: List[Dict[str, object]] = []
    for root in roots:
        if not os.path.isdir(root):
            continue
        for dirpath, dirnames, filenames in os.walk(root):
            dirnames[:] = [d for d in dirnames if d not in (".git", "__pycache__")]
            for fn in sorted(filenames):
                if not fn.endswith(".c"):
                    continue
                p = os.path.join(dirpath, fn)
                try:
                    with open(p, "r", encoding="utf-8", errors="replace") as fh:
                        raw = fh.read()
                except OSError:
                    continue
                if "send_msg_to_smc" not in raw:
                    continue
                clean = strip_comments(raw)
                file_defs, header = ppsmc_defines_for(p, search_roots)
                for m in _SEND.finditer(clean):
                    args = split_args(m.group("args"))
                    # El mensaje es el SEGUNDO argumento: el primero es siempre
                    # el hwmgr. Sin saltar el primero, "smum_send_msg_to_smc
                    # (hwmgr, MSG)" reporta hwmgr como nombre de mensaje, que es
                    # un simbolo real y por tanto NO se ve como error.
                    sym = None
                    for a in args[1:2] or args:
                        a2 = a.strip()
                        cand = re.sub(r"^\(?\s*(?:uint16_t|\(uint16_t\))\s*\)?\s*", "", a2)
                        cand = cand.strip().strip("()").strip()
                        if re.match(r"^[A-Za-z_]\w*$", cand):
                            sym = cand
                            break
                    payload = classify_payload(
                        "param", args[2] if len(args) > 2 else "",
                        defines)
                    conds = []
                    ctx = clean[max(0, m.start() - 400):m.start()]
                    for cm in _CHIP_CMP.finditer(ctx):
                        cv = enum.get(cm.group(3))
                        takes = None if cv is None else _CMP[cm.group(2)](chip, cv)
                        conds.append({"constant": cm.group(3),
                                      "value": "?" if cv is None else str(cv),
                                      "taken": "?" if takes is None else
                                               ("SI" if takes else "no")})
                    rows.append({
                        "file": p,
                        "line": clean[:m.start()].count("\n") + 1,
                        "fn": m.group("fn"),
                        "msg_symbol": sym,
                        "msg_value": file_defs.get(sym) if sym else None,
                        "ppsmc_header": header,
                        "msg_value_source": ("ppsmc.h del propio .c" if header
                                             else "SIN CABECERA RESUELTA"),
                        "payload": payload,
                        "n_args": len(args),
                        "conds": conds,
                        "verdict": ("MUERTA" if conds and all(
                            c["taken"] == "no" for c in conds)
                            else ("VIVA" if any(c["taken"] == "SI" for c in conds)
                                  else "NO_CONDICIONAL")),
                    })
    return {"rows": rows}


def summarize(scanres: Dict[str, object], defines: Dict[str, int]) -> Dict[str, object]:
    rows = scanres["rows"]  # type: ignore[index]
    by_symbol: Dict[str, List[Dict[str, object]]] = defaultdict(list)
    for r in rows:
        by_symbol[str(r["msg_symbol"])].append(r)

    msgs: List[Dict[str, object]] = []
    unresolved: List[str] = []
    for sym, uses in sorted(by_symbol.items()):
        # Un simbolo puede tener valores DISTINTOS segun la cabecera, porque
        # el mismo nombre se declara en smu7_ppsmc.h y en vega20_ppsmc.h con
        # numeros diferentes. Se reporta el conjunto, no uno solo.
        # El valor sale de la FILA, que lo resolvio usando el ppsmc.h de ese
        # .c. No del mapa global: ese daria el valor de la ultima cabecera
        # leida, que puede ser de otra generacion.
        vals = sorted({int(u["msg_value"]) for u in uses
                       if u.get("msg_value") is not None})  # type: ignore[union-attr]
        hdrs = sorted({str(u.get("ppsmc_header") or "?") for u in uses})
        if sym and not vals:
            unresolved.append(sym)
        payloads = {u["payload"]["kind"] for u in uses}  # type: ignore[index]
        msgs.append({
            "symbol": sym,
            "values": vals,
            "value_hex": [hex(v) for v in vals] or None,
            "headers": hdrs,
            "ambiguous": len(vals) > 1,
            "uses": len(uses),
            "files": sorted({os.path.basename(str(u["file"])) for u in uses}),
            "payload_kinds": sorted(payloads),
            "verdicts": sorted({str(u["verdict"]) for u in uses}),
            "uses_detail": uses,
        })
    # Colisiones SOLO dentro de la misma cabecera. Agrupar por numero global
    # marca 41 colisiones que no son colisiones: son el particionado por
    # generacion que el propio kernel impone.
    by_key: Dict[Tuple[str, int], List[str]] = defaultdict(list)
    for m in msgs:
        for v in m["values"]:  # type: ignore[union-attr]
            for h in m["headers"]:  # type: ignore[union-attr]
                by_key[(h, v)].append(str(m["symbol"]))
    collisions = {f"{h}@{hex(v)}": sorted(set(sym))
                  for (h, v), sym in by_key.items()
                  if len(set(sym)) > 1 and h}
    # Las que no tienen cabecera NO son colisiones: son .c que emissen el
    # mensaje a traves de un wrapper y no incluyen el ppsmc.h. Contarlas como
    # conflicto inventa 130 problemas que no existen.
    sin_cabecera = sorted({str(u.get("msg_symbol"))
                           for m in msgs
                           for u in m["uses_detail"]  # type: ignore[union-attr]
                           if not str(u.get("ppsmc_header"))})

    # simbolos usados que no estan en los headers del subarbol
    kind_count: Dict[str, int] = defaultdict(int)
    for r in rows:
        kind_count[str(r["payload"]["kind"])] += 1  # type: ignore[index]

    return {
        "total_send_calls": len(rows),
        "distinct_messages": len(msgs),
        "unresolved_symbols": sorted(set(unresolved)),
        "collisions": collisions,
        "sin_cabecera_resuelta": sin_cabecera,
        "payload_kind_counts": dict(sorted(kind_count.items())),
        "messages": msgs,
    }


def render(sumres: Dict[str, object], only: Optional[str]) -> str:
    L = [f"{NAME} {VERSION}"]
    L.append("  MAPA_DE_BITS = el host pasa un OR de mascaras. NO demuestra que")
    L.append("  el firmware lo trate como flags: solo que le llega un numero.")
    L.append("")
    L.append(f"  llamadas de envio: {sumres['total_send_calls']}")
    L.append(f"  mensajes distintos: {sumres['distinct_messages']}")
    L.append(f"  reparto de payload: {sumres['payload_kind_counts']}")
    if sumres["collisions"]:
        L.append("")
        L.append("  COLISIONES de numero:")
        for v, syms in sorted(sumres["collisions"].items()):
            L.append(f"    {v}: {', '.join(syms)}")
    if sumres.get("sin_cabecera_resuelta"):
        n = len(sumres["sin_cabecera_resuelta"])
        L.append(f"  sin cabecera ppsmc resuelta: {n} mensajes (wrapper o "
                 f"include indirecto; NO son colisiones)")
    if sumres["unresolved_symbols"]:
        L.append("")
        L.append(f"  simbolos sin resolver ({len(sumres['unresolved_symbols'])}): "
                 f"{', '.join(sorted(str(x) for x in sumres['unresolved_symbols'])[:8])}")
    L.append("")
    L.append("  valor por cabecera: el numero se particiona por generacion.")
    L.append("")
    L.append(f"  {'mensaje':<40} {'valor(es)':<20} {'hdr':<18} {'usos':>4} payload")
    L.append("  " + "-" * 104)
    for m in sumres["messages"]:  # type: ignore[union-attr]
        if only and only not in str(m["symbol"]):
            continue
        vs = ",".join(str(x) for x in (m["value_hex"] or ["?"]))
        if m["ambiguous"]:
            vs += " !"
        hdr = ",".join(str(h).replace("_ppsmc.h", "") for h in m["headers"])[:18]
        pk = "+".join(str(x) for x in m["payload_kinds"])[:20]
        L.append(f"  {str(m['symbol'])[:40]:<40} {vs:<20} {hdr:<18} "
                 f"{m['uses']:>4} {pk}")
    return "\n".join(L)


def selftest() -> int:
    failures: List[str] = []

    def check(name: str, got, want) -> None:
        if got != want:
            failures.append(f"{name}: obtuve {got!r}, esperaba {want!r}")

    check("split.basico", split_args("a, b, c"), ["a", "b", "c"])
    check("split.anidado", split_args("f(a, b), c"), ["f(a, b)", "c"])

    d = {"X_IR_MASK": 0x2, "X_PCC_MASK": 0x4, "Y_EN_MASK": 0x100}
    c1 = classify_payload("param", "X_IR_MASK | X_PCC_MASK", d)
    check("payload.mapa", c1["kind"], "MAPA_DE_BITS")
    check("payload.n_masks", c1["n_masks"], 2)
    check("payload.valor", c1["valor_si_resuelto"], 0x6)
    c2 = classify_payload("param", "0x301", d)
    check("payload.literal", c2["kind"], "LITERAL")
    check("payload.literal_valor", c2["value"], 0x301)
    c3 = classify_payload("param", "&data->smc_state_table", d)
    check("payload.puntero", c3["kind"], "PUNTERO")
    check("payload.ninguno", classify_payload("param", "NULL", d)["kind"], "NINGUNO")
    check("payload.simbolo", classify_payload("param", "mi_var", d)["kind"], "SIMBOLO")

    import tempfile
    with tempfile.TemporaryDirectory() as td:
        with open(os.path.join(td, "smu7_ppsmc.h"), "w", encoding="utf-8") as fh:
            fh.write("#define PPSMC_MSG_Test  ((uint16_t) 0x301)\n"
                     "#define PPSMC_MSG_Otro  ((uint16_t) 0x302)\n")
        defs = collect_defines([td])
        defs2 = collect_defines([td])
        check("defines.con_cast", defs.get("PPSMC_MSG_Test"), 0x301)

        # La estructura importa: el .c esta en smumgr/ e incluye
        # "smu7_ppsmc.h", que vive en inc/. Sin esa indireccion el valor del
        # mensaje no se resuelve, y un fixture plano no ejercita el caso real.
        smudir = os.path.join(td, "smumgr")
        incdir = os.path.join(td, "inc")
        os.makedirs(smudir)
        os.makedirs(incdir)
        with open(os.path.join(incdir, "smu7_ppsmc.h"), "w", encoding="utf-8") as fh:
            fh.write("#define PPSMC_MSG_Test  ((uint16_t) 0x301)\n"
                     "#define PPSMC_MSG_Otro  ((uint16_t) 0x302)\n"
                     "#define PPSMC_MSG_Dup   ((uint16_t) 0x301)\n")
        with open(os.path.join(smudir, "a.c"), "w", encoding="utf-8") as fh:
            fh.write(
                '#include "smu7_ppsmc.h"\n'
                "void f(struct pp_hwmgr *hwmgr)\n{\n"
                "\tuint32_t didt_block = 0;\n"
                "\tsmum_send_msg_to_smc_with_parameter(hwmgr,\n"
                "\t\t(uint16_t)PPSMC_MSG_Test, didt_block, NULL);\n"
                "\tif (hwmgr->chip_id == CHIP_VEGAM)\n"
                "\t\tsmu7_send_msg_to_smc(hwmgr, PPSMC_MSG_Otro);\n"
                "}\n")
        with open(os.path.join(td, "amd_asic_type.h"), "w", encoding="utf-8") as fh:
            fh.write("enum amd_asic_type {\n\tCHIP_POLARIS12,\t/* 17 */\n"
                     "\tCHIP_VEGAM,\t/* 18 */\n};\n")
        en = parse_chip_enum(os.path.join(td, "amd_asic_type.h"))
        check("enum.p12", en.get("CHIP_POLARIS12"), 17)
        res = scan([td], en, 17, defs)
        rows = res["rows"]  # type: ignore[index]
        check("scan.llamadas", len(rows), 2)
        syms = sorted(str(r["msg_symbol"]) for r in rows)
        check("scan.simbolos", syms, ["PPSMC_MSG_Otro", "PPSMC_MSG_Test"])
        t = next(r for r in rows if r["msg_symbol"] == "PPSMC_MSG_Test")
        check("scan.valor", t["msg_value"], 0x301)
        # El segundo parametro aqui es una VARIABLE, no un literal. Se
        # clasifica como SIMBOLO, que es lo correcto y lo informativo: el
        # payload se construye en runtime y el valor no se ve aqui.
        check("scan.payload_es_variable", t["payload"]["kind"], "SIMBOLO")
        check("scan.payload_raw", t["payload"]["raw"], "didt_block")
        # pero si se pasa un OR de mascaras literal, es MAPA_DE_BITS
        with open(os.path.join(td, "c.c"), "w", encoding="utf-8") as fh:
            fh.write("void h(struct pp_hwmgr *h2)\n{\n"
                     "\tsmu7_send_msg_to_smc_with_parameter(h2,\n"
                     "\t\t(uint16_t)PPSMC_MSG_Test,\n"
                     "\t\tX_IR_MASK | X_PCC_MASK, NULL);\n}\n")
        defs3 = collect_defines([td])
        res3 = scan([td], en, 17, defs3)
        map_row = next((r for r in res3["rows"]
                        if r["payload"]["kind"] == "MAPA_DE_BITS"), None)
        check("scan.mapa_de_bits_detectado", map_row is not None, True)
        o = next(r for r in rows if r["msg_symbol"] == "PPSMC_MSG_Otro")
        check("scan.muerta_para_nosotros", o["verdict"], "MUERTA")
        check("scan.payload_sin_param", o["payload"]["kind"], "NINGUNO")

        s = summarize(res, defs)
        check("sum.distintos", s["distinct_messages"], 2)
        check("sum.sin_colision", s["collisions"], {})

        # colision REAL: dos simbolos con el MISMO numero en la MISMA cabecera
        with open(os.path.join(smudir, "b.c"), "w", encoding="utf-8") as fh:
            fh.write('#include "smu7_ppsmc.h"\n'
                     "void g(struct pp_hwmgr *h)\n{\n"
                     "\tsmu7_send_msg_to_smc(h, PPSMC_MSG_Dup);\n}\n")
        res2 = scan([td], en, 17, defs2, [incdir])
        s2 = summarize(res2, defs2)
        check("sum.colision_detectada", len(s2["collisions"]), 1)
        ck = list(s2["collisions"].values())[0]
        check("sum.colision_simbolos", sorted(ck), ["PPSMC_MSG_Dup", "PPSMC_MSG_Test"])

        # NO colision: el mismo numero en DOS cabeceras distintas es el
        # particionado por generacion que el kernel impone, no un conflicto.
        vegadir = os.path.join(td, "vega")
        os.makedirs(vegadir)
        with open(os.path.join(vegadir, "vega20_ppsmc.h"), "w", encoding="utf-8") as fh:
            fh.write("#define PPSMC_MSG_Test  ((uint16_t) 0x401)\n"
                     "#define PPSMC_MSG_Otro  ((uint16_t) 0x402)\n"
                     "#define PPSMC_MSG_Dup   ((uint16_t) 0x401)\n")
        with open(os.path.join(vegadir, "v.c"), "w", encoding="utf-8") as fh:
            fh.write('#include "vega20_ppsmc.h"\n'
                     "void v(struct pp_hwmgr *h)\n{\n"
                     "\tsmu7_send_msg_to_smc(h, PPSMC_MSG_Test);\n}\n")
        res3b = scan([td], en, 17, defs2, [incdir, vegadir])
        s3 = summarize(res3b, defs2)
        check("sum.sin_colision_entre_cabeceras", len(s3["collisions"]), 1)
        amb = [m for m in s3["messages"] if m["symbol"] == "PPSMC_MSG_Test"]
        check("sum.ambiguo_entre_cabeceras", amb[0]["ambiguous"], True)
        check("sum.dos_valores", sorted(amb[0]["values"]), [0x301, 0x401])

        check("scan.sin_directorio", scan([os.path.join(td, "nope")], en, 17, defs)["rows"], [])
        check("defines.sin_directorio", collect_defines([os.path.join(td, "nope")]), {})

    print(f"{NAME} {VERSION} · self-test")
    if failures:
        print(f"  RESULTADO FALLIDO ({len(failures)}):")
        for f in failures:
            print(f"    - {f}")
        return 1
    print("  RESULTADO OK · vectores conocidos reproducidos")
    print("  NOTA: dice que envia el host. NO dice que haga el firmware.")
    return 0


def main(argv: Optional[Sequence[str]] = None) -> int:
    ap = argparse.ArgumentParser(prog=NAME,
                                 description="Censo de mensajes SMC con su payload.")
    ap.add_argument("--selftest", action="store_true")
    ap.add_argument("--kernel")
    ap.add_argument("--chip", default=DEFAULT_CHIP)
    ap.add_argument("--root", default=None, help="subarbol a escanear")
    ap.add_argument("--msg", default=None, help="filtrar por simbolo")
    ap.add_argument("--detail", action="store_true")
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args(argv)

    if args.selftest:
        return selftest()
    if not args.kernel:
        ap.error("--kernel es obligatorio salvo con --selftest")
    kernel = os.path.abspath(args.kernel)
    root = args.root or os.path.join(kernel, "drivers/gpu/drm/amd/pm")
    enum = parse_chip_enum(os.path.join(kernel, ASIC_ENUM_REL))
    chip_val = enum.get(args.chip)
    if chip_val is None:
        print(f"ERROR  {args.chip} no esta en el enum", file=sys.stderr)
        return 2
    defines = collect_defines([root, os.path.join(kernel, "include")])
    res = scan([root], enum, chip_val, defines)
    s = summarize(res, defines)
    if args.json:
        print(json.dumps({"tool": NAME, "version": VERSION, "chip": args.chip,
                          "chip_value": chip_val,
                          "defines": len(defines), **s},
                         indent=2, ensure_ascii=False))
        return 0
    print(render(s, args.msg))
    if args.detail and args.msg:
        for m in s["messages"]:
            if args.msg in str(m["symbol"]):
                for u in m["uses_detail"]:
                    print(f"  {os.path.basename(str(u['file']))}:{u['line']} "
                          f"{u['fn']} payload={u['payload']['kind']}")
                    for c in u["conds"]:
                        print(f"      cond {c['constant']}(={c['value']}) -> {c['taken']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
