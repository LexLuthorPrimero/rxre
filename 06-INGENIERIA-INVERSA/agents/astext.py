#!/usr/bin/env python3
"""Extractor AST en streaming sobre el JSON de clang.

`json.load` no cabe: el AST de un .c de amdgpu son 1.0-1.2 GB.  El JSON de
clang sale indentado a 2 espacios, y se demuestra que la heuristica de
indentacion NO es fiable (los objetos de campo, p.ej. "loc", se cierran a la
MISMA indentacion que la linea "kind" de su nodo, no dos por debajo), asi que
el corte de bloques se hace contando LLAVES de verdad, con control de cadenas
y literales de caracter.  Se apila un marco por cada nodo pedido y se entrega
el bloque cuando la profundidad de llaves vuelve a su base.

Salida: {"file":..., "functions":[...], "calls":[...]} solo con lo del fichero
principal (clang omite "file" en las ubicaciones del MAIN FILE).
"""
import json
import re
import sys

KIND_RE = re.compile(r'^(\s*)"kind": "(\w+)",?$')
WANT = {"FunctionDecl", "CallExpr"}


def brace_delta(line):
    """Delta de llaves/llaves-angulares de una linea, ignorando cadenas,
    literales, comentarios de linea y comentarios de bloque multilinea."""
    global _IN_BLOCK_COMMENT
    d = 0
    i = 0
    n = len(line)
    while i < n:
        c = line[i]
        if _IN_BLOCK_COMMENT:
            if c == '*' and i + 1 < n and line[i + 1] == '/':
                _IN_BLOCK_COMMENT = False
                i += 2
                continue
            i += 1
            continue
        if c == '"' or c == "'":
            q = c
            i += 1
            while i < n:
                if line[i] == '\\':
                    i += 2
                    continue
                if line[i] == q:
                    i += 1
                    break
                i += 1
            continue
        if c == '/' and i + 1 < n and line[i + 1] == '/':
            break
        if c == '/' and i + 1 < n and line[i + 1] == '*':
            _IN_BLOCK_COMMENT = True
            i += 2
            continue
        if c in '{[':
            d += 1
        elif c in '}]':
            d -= 1
        i += 1
    return d


_IN_BLOCK_COMMENT = False


def stream_blocks(path):
    """(kind, texto) de cada nodo pedido, por conteo de llaves."""
    global _IN_BLOCK_COMMENT
    _IN_BLOCK_COMMENT = False
    buf = []            # lineas pendientes de emitir
    frames = []         # [base_depth, kind, start_index_en_buf]
    depth = 0
    prev = None         # linea anterior (la llave de apertura del nodo)
    with open(path, "r", encoding="utf-8", errors="replace") as fh:
        for line in fh:
            m = KIND_RE.match(line)
            if m is not None and m.group(2) in WANT:
                kind = m.group(2)
                base = depth - 1          # la linea previa abria el bloque
                assert prev is not None, "nodo sin llave de apertura"
                # clang imprime "id" ANTES que "kind": la llave de apertura
                # no es la linea anterior sino la anterior a esa.  Se busca de
                # verdad; si no aparece en 7 lineas, se sintetiza.
                start = None
                for j in range(len(buf) - 1, max(-1, len(buf) - 7), -1):
                    if buf[j].strip() == "{":
                        start = j
                        break
                synth = start is None
                if synth:
                    start = len(buf) - 1
                buf.append(line)
                frames.append([base, kind, start, synth])
            else:
                buf.append(line)
            depth += brace_delta(line)
            while frames and depth <= frames[-1][0]:
                base, kind, start, synth = frames.pop()
                txt_ = ("{\n" if synth else "") + "".join(buf[start:])
                if not frames:
                    buf = []
                yield kind, txt_
            prev = line
    while frames:
        base, kind, start, synth = frames.pop()
        yield kind, ("{\n" if synth else "") + "".join(buf[start:])


def txt(v):
    """Acepta el valor de "file" (cadena) o el dict de la ubicacion."""
    if isinstance(v, str):
        return v
    if isinstance(v, dict):
        return v.get("file") or v.get("filename") or ""
    return ""


def src(node):
    """(fichero_o_None, linea) de un nodo.

    Dos trampas medidas en este corpus, ambas por el hecho de que clang OMITE
    la clave "file" en algunas ubicaciones:

    1. Las EXPRESIONES no traen "loc", traen "range" con begin/end.
    2. Que falte "file" NO significa "fichero principal": en
       include/vdso/math64.h el `loc` dice file=...vdso/math64.h pero
       `range.begin` trae line=5 y NINGUN file.  Con la regla ingenua
       "sin file -> main file" entraian 5 600 funciones de cabeceras como si
       fueran de gfx_v8_0.c (contado: 139 gfx_v8_0_* correctas + 5 617 basura).

    Regla: se recorren las ubicaciones en orden de preferencia
    (expansionLoc -> spellingLoc -> loc/range.begin), se devuelve la primera
    que tenga linea, y su "file" explicito decide.  Sin "file" explicito, solo
    si NINGUNA de las ubicaciones del nodo lo trae, se asume main file.
    """
    loc = node.get("loc") or {}
    rng = node.get("range") or {}
    cands = [loc, rng.get("begin"), rng.get("end")]
    ordered = []
    for c in cands:
        if isinstance(c, dict):
            ordered.append(c.get("expansionLoc"))
            ordered.append(c.get("spellingLoc"))
    ordered.extend(cands)
    for c in ordered:
        if isinstance(c, dict) and c.get("line") is not None:
            return (txt(c.get("file")) or None, c.get("line"))
    return (None, None)


def callee_chain(node):
    """(nombre, [kinds]) del callee.

    Un DeclRefExpr de clang NO trae "name": trae "referencedDecl", que es el
    FunctionDecl con el nombre.  Un MemberExpr trae "member" (el FieldDecl con
    el nombre del miembro).  Sin esto, 3684 de 3713 llamadas salian con
    callee=None.
    """
    seen = []
    n = node
    for _ in range(12):
        kids = n.get("inner") or []
        if not kids:
            return None, seen
        c = kids[0]
        seen.append(c.get("kind"))
        if c.get("name"):
            return c.get("name"), seen
        rd = c.get("referencedDecl")
        if isinstance(rd, dict) and rd.get("name"):
            return rd["name"], seen
        mem = c.get("member")
        if isinstance(mem, dict) and mem.get("name"):
            return mem["name"], seen
        n = c
    return None, seen


def has_body(node):
    return any(c.get("kind") == "CompoundStmt" for c in (node.get("inner") or []))


def main():
    jsonpath, target_file, out_path = sys.argv[1], sys.argv[2], sys.argv[3]
    functions, calls = [], []
    nblocks = 0
    for kind, text in stream_blocks(jsonpath):
        nblocks += 1
        text = text.rstrip()
        if text.endswith(","):
            text = text[:-1]
        try:
            node = json.loads(text)
        except ValueError as e:
            sys.stderr.write("AVISO bloque ilegible %s: %s\n" % (kind, e))
            continue
        f, line = src(node)
        f = f or target_file       # clang omite "file" en el MAIN FILE
        # sin linea = decl implicita de clang (builtins, __loadsegment_*...):
        # no pertenece a ningun fichero fuente, se descarta
        if line is None or f != target_file:
            continue
        if kind == "FunctionDecl":
            if not has_body(node):
                continue
            rng = node.get("range") or {}
            functions.append({
                "name": node.get("name"),
                "static": node.get("storageClass") == "static",
                "storageClass": node.get("storageClass"),
                "inline": bool(node.get("inline")),
                "type": ((node.get("type") or {}).get("qualType") or "")[:200],
                "start": line,
                "end": (rng.get("end") or {}).get("line"),
            })
        else:
            name, chain = callee_chain(node)
            calls.append({"callee": name, "chain": chain,
                          "line": line,
                          "nargs": max(0, len(node.get("inner") or []) - 1)})
    functions.sort(key=lambda d: (d["start"] or 0))
    calls.sort(key=lambda d: (d["line"] or 0))
    json.dump({"file": target_file, "functions": functions, "calls": calls},
              open(out_path, "w"), indent=1)
    sys.stderr.write("%s -> %s : %d bloques, %d funciones con cuerpo, %d CallExpr\n"
                     % (jsonpath, out_path, nblocks, len(functions), len(calls)))


if __name__ == "__main__":
    main()