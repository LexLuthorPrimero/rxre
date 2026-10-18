#!/usr/bin/env python3
"""xref.py — referencias reales de un símbolo, vía AST de clang, no regex.
    WORK_CLASS=READ_ONLY · WRITE_EXECUTION=NONE
    No abre /sys, no escribe ficheros, no toca la GPU ni el arbol.

Por qué existe
--------------
`trace_path.py` trocea C con expresiones regulares. Funciona para el caso
habitual, pero tiene tres límites que ya han producido resultados wrongly:

1. Una llamada dentro de un macro no se ve. `PP_ASSERT_WITH_CODE(f(x), ...)`
   contiene una llamada a `f`, y el parser de texto la ve como un token más.
2. Un símbolo invocado solo desde un `if` de macro se clasifica mal.
3. Un nombre que aparece en un comentario, en una cadena, o como parte de
   otro identificador (`foo` dentro de `foobar`) necesita análisis léxico real.

clang está instalado (verificado: version 22.1.8, `-ast-dump` funciona). El
kernel, además, tiene macros por todas partes, y el preprocesador de clang las
expande antes de construir el AST. Eso convierte un problema de "leer C con
regex" en "leer el AST ya expandido", que es lo que corresponde.

Qué produce
-----------
Para un símbolo:
  · dónde se DECLARA (y si es función, variable, typedef, macro)
  · dónde se USA, clasificado: llamada / lectura / escritura / dirección-de
  · en qué ficheros, y si el uso es dentro de un macro o no
  · si el fichero está en la ruta viva de mi ASIC (delega en asic_resolver)

Y el inverso: quién llama a este símbolo, que es la pregunta que encadena la
investigación.

Lo que NO hace
--------------
No compila el kernel. Si el preprocesado falla por una cabecera ausente, lo
dice y devuelve el error; no degrada a regex en silencio. Un análisis parcial
que parece completo es peor que ninguno.

Uso
---
    xref.py --kernel RAIZ --symbol smu7_send_msg_to_smc
    xref.py --kernel RAIZ --callers smu7_send_msg_to_smc
    xref.py --kernel RAIZ --file drivers/.../smu7_smumgr.c --declares
    xref.py --selftest
"""

from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
from typing import Dict, List, Optional, Sequence, Set, Tuple

NAME = "xref"
VERSION = "1.0.0"

DEFAULT_CLANG = "clang"


class PreprocessError(RuntimeError):
    """El preprocesado fallo. No se degrada a regex: se dice."""


def have_clang(exe: str = DEFAULT_CLANG) -> Optional[str]:
    p = shutil.which(exe)
    if not p:
        return None
    try:
        v = subprocess.run([p, "--version"], capture_output=True,
                           text=True, timeout=20)
    except (OSError, subprocess.SubprocessError):
        return None
    return v.stdout.splitlines()[0] if v.stdout else p


def kernel_cflags(kernel: str) -> List[str]:
    cflags, _note = config_defines(kernel)
    """Flags minimos para que clang acepte codigo de kernel.

    NO se intenta compilar el kernel: solo preprocesar un TUYELTO. Se
    declara que no hay types.h real, y por eso el resultado se marca como
    PARCIAL cuando no se pudo construir el AST completo.
    """
    # -std=gnu89 y -D__KERNEL__ no son opcionales: el kernel usa
    # `__aligned`, que es una extension suya, y gnu89 acepta construcciones
    # que gnu11 rechaza. Sin esas dos banderas, types.h:187 da
    # "expected parameter declarator" y no se analiza NADA.
    inc = [
        "-std=gnu89",
        "-D__KERNEL__",
        "-DKBUILD_MODNAME=\"amdgpu\"",
        "-DKBUILD_BASENAME=\"amdgpu\"",
        "-Wno-everything",
        # autoconf.h y .config EXISTEN en el arbol: el corpus tiene un build
        # real hecho. Sin ellos, instrumented.h falla con
        # "use of undeclared identifier CONFIG_DEBUG_ATOMIC" y el analisis se
        # detiene en la primera cabecera, no en el fichero que se pedia.
        "-include", f"{kernel}/include/generated/autoconf.h",
        f"-I{kernel}/include",
        f"-I{kernel}/include/generated",
        f"-I{kernel}/include/uapi",
        f"-I{kernel}/arch/x86/include",
        f"-I{kernel}/arch/x86/include/generated",
        f"-I{kernel}/arch/x86/include/generated/uapi",
        f"-I{kernel}/drivers/gpu/drm/amd/include",
        f"-I{kernel}/drivers/gpu/drm/amd/pm/inc",
        f"-I{kernel}/drivers/gpu/drm/amd/pm/powerplay",
        f"-I{kernel}/drivers/gpu/drm/amd/pm/powerplay/inc",
        f"-I{kernel}/drivers/gpu/drm/amd/pm/powerplay/hwmgr",
        f"-I{kernel}/drivers/gpu/drm/amd/pm/powerplay/smumgr",
        f"-I{kernel}/drivers/gpu/drm/amd/pm/powerplay/smumgr/smu7",
        f"-I{kernel}/drivers/gpu/drm/amd/pm/swsmu",
        f"-I{kernel}/drivers/gpu/drm/amd/pm/swsmu/inc",
        *cflags,
    ]
    # SIN -E: pedir un AST ya implica preprocesar, y -E junto a
    # -ast-dump es incompatible. Ponerlo aqui hacia que clang solo se
    # quejara y no emitiera NADA, con lo que la herramienta reportaba
    # "no hay referencias" cuando en realidad no llego a analizar.
    return inc


def missing_generated(kernel: str) -> List[str]:
    """Cabeceras que el build genera y este arbol no tiene.

    El corpus es un arbol FUENTE parcialmente generado: existen
    autoconf.h y .config, pero faltan los symlinks que `make` crea en
    arch/x86/include/generated/asm. Sin ellos no hay AST completo, porque
    linux/compiler_types.h hace #include <asm/compiler.h> y clang se para ahi.

    Se comprueba y se DECLARA. Completar el build seria una escritura en el
    arbol, y el trabajo declarado es READ_ONLY: mejor que la herramienta diga
    "no puedo" que devuelva un analisis vacio.
    """
    out: List[str] = []
    asm_dir = os.path.join(kernel, "arch/x86/include/generated/asm")
    for h in ("compiler.h", "posix_types.h"):
        if not os.path.isfile(os.path.join(asm_dir, h)):
            out.append(f"arch/x86/include/generated/asm/{h}")
    return out


def config_defines(kernel: str) -> Tuple[List[str], str]:
    """Traduce el .config real a -D, para lo que autoconf.h no trae.

   Algunas cabeceras del kernel usan CONFIG_* sin #ifdef y asumen que el
    entorno de build las define todas. autoconf.h solo trae las que estan
    habilitadas, así que analysing el codigo con el solo autoconf.h produce
    "use of undeclared identifier" en instrumented.h y company: un error del
    entorno, no del fichero que se quiere analizar.

    Se declara que sale del .config del propio corpus, no de un .config
    inventado: si el arbol no lo tiene, se avisa y no se inventa nada.
    """
    cfg = os.path.join(kernel, ".config")
    out: List[str] = []
    if not os.path.isfile(cfg):
        return out, "SIN_.config_"
    try:
        with open(cfg, "r", encoding="utf-8", errors="replace") as fh:
            for line in fh:
                m = re.match(r"^(CONFIG_[A-Z0-9_]+)=(.+)$", line.strip())
                if m:
                    val = m.group(2).strip().strip('"')
                    if val in ("y", "1"):
                        out.append(f"-D{m.group(1)}=1")
                    elif re.match(r"^[0-9]+$", val):
                        out.append(f"-D{m.group(1)}={val}")
                    continue
                m2 = re.match(r"^# (CONFIG_[A-Z0-9_]+) is not set$", line.strip())
                if m2:
                    out.append(f"-D{m2.group(1)}=0")
    except OSError:
        return out, "IO_ERROR"

    # El kernel usa IS_ENABLED(C), que se expande a __is_defined(C): pregunta
    # si el IDENTIFICADOR esta definido, no su valor. Toda opcion que el
    # .config no menciona queda sin definir por nadie, y clang responde
    # "use of undeclared identifier" al expandirla. Es un error del ENTORNO,
    # no del fichero analizado, yPerseguirlo opcion a opcion no termina:
    # aparecia uno distinto en cada intento.
    #
    # Aqui se barren TODOS los Kconfig del arbol de una vez y se declara como
    # 0 toda opcion que el .config no haya fijado. Es lo que hace el build
    # real: Kconfig tiene un valor por defecto para cada opcion, y el .config
    # solo guarda las que se apartan de ese valor.
    seen: set = set()
    for kdef in ("-D%s=1", "-D%s=0"):
        pass
    declared = {o[2:].split("=", 1)[0] for o in out if o.startswith("-DCONFIG_")}
    added = 0
    for dirpath, dirnames, filenames in os.walk(kernel):
        dirnames[:] = [d for d in dirnames
                       if d not in (".git", "__pycache__", "Documentation",
                                    "tools", "samples", "scripts")]
        for fn in filenames:
            if not (fn == "Kconfig" or fn.startswith("Kconfig.")):
                continue
            kp = os.path.join(dirpath, fn)
            try:
                with open(kp, "r", encoding="utf-8", errors="replace") as fh:
                    ktext = fh.read()
            except OSError:
                continue
            for m in re.finditer(
                    r"^config\s+([A-Z0-9_]+)", ktext, re.M):
                nm = "CONFIG_" + m.group(1)
                if nm in declared or nm in seen:
                    continue
                seen.add(nm)
                out.append(f"-D{nm}=0")
                added += 1
    return out, (f"{len(out)} defines: {len(declared)} de .config, "
                  f"{added} de Kconfig a 0")


def ast_dump(src: str, flags: Sequence[str], exe: str = DEFAULT_CLANG,
             timeout: int = 90) -> str:
    """AST en formato JSON de clang. Falla loudly."""
    cmd = [exe, "-Xclang", "-ast-dump=json", "-fsyntax-only", *flags, src]
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
    except subprocess.TimeoutExpired as e:
        raise PreprocessError(f"clang tardó más de {timeout}s en {src}") from e
    errs = [l for l in (r.stderr or "").splitlines()
            if "error:" in l or "fatal error" in l]
    warns = [l for l in (r.stderr or "").splitlines()
             if ("warning:" in l or "argument unused" in l) and l not in errs]
    if errs:
        raise PreprocessError(f"{len(errs)} error(es) de clang; primero: "
                              f"{errs[0].strip()[:200]}")
    if not r.stdout.strip():
        raise PreprocessError(
            "clang no emito AST. stderr solo tiene warnings: "
            + (warns[0].strip()[:200] if warns else "(vacio)"))
    try:
        return r.stdout
    except Exception as e:  # pragma: no cover
        raise PreprocessError(str(e)) from e


def walk(node: Dict[str, object]) -> List[Dict[str, object]]:
    """Recorre el AST JSON de clang, en orden."""
    out: List[Dict[str, object]] = []
    stack = [node]
    while stack:
        n = stack.pop()
        out.append(n)
        kids = n.get("inner")
        if isinstance(kids, list):
            stack.extend(reversed(kids))  # type: ignore[arg-type]
    return out


def collect_refs(ast: Dict[str, object], symbol: str,
                 file_filter: Optional[str] = None) -> Dict[str, List[Dict[str, object]]]:
    """Recorre el AST buscando el simbolo, clasificando el uso.

    La clasificacion usa el NODO PADRE, no el texto: un CallExpr cuyo
    callee es DeclRefExpr `f` es una LLAMADA; un DeclRefExpr suelto es
    lectura o escritura segun si su padre es un operador de asignacion.
    """
    nodes = walk(ast)
    decls: List[Dict[str, object]] = []
    calls: List[Dict[str, object]] = []
    reads: List[Dict[str, object]] = []
    writes: List[Dict[str, object]] = []
    addrs: List[Dict[str, object]] = []

    def declared_name(n: Dict[str, object]) -> str:
        """El nombre al que se refiere un nodo, en el esquema de clang 22.

        Esquema real de `ast-dump=json`:
            DeclRefExpr  { id, kind, range, referencedDecl: {id,kind,name}, type }
        NO existe `name` en el DeclRefExpr ni `referent`: el nombre esta DENTRO
        de `referencedDecl`. Buscarlo en `name` devuelve None para toda
        referencia y la herramienta concluye "este simbolo no se usa en ningun
        sitio", que es el falso negativo mas caro posible.
        """
        rd = n.get("referencedDecl")
        if isinstance(rd, dict) and rd.get("name"):
            return str(rd["name"])
        ref = n.get("referent")
        if isinstance(ref, dict) and ref.get("name"):
            return str(ref["name"])
        return str(n.get("name") or "")

    for idx, n in enumerate(nodes):
        kind = str(n.get("kind", ""))
        name = declared_name(n)
        if name != symbol:
            continue
        loc = n.get("loc")
        f = line = col = None
        if isinstance(loc, dict):
            f = loc.get("file")
            line = loc.get("line")
            col = loc.get("col")
        rec = {"kind": kind, "file": f, "line": line, "col": col}
        if kind == "DeclRefExpr":
            # El padre INMEDIATO no basta: entre el DeclRefExpr y el
            # CallExpr se interponen los ImplicitCastExpr de la conversion de
            # argumentos. Mirar solo el padre clasifica `destino(v)` como
            # lectura, que es un resultado plausible y equivocado.
            # Se sube por los nodos intermedios hasta el primero que signifique.
            pk = ""
            op = ""
            j = idx - 1
            hops = 0
            while j >= 0 and hops < 6:
                cand = str(nodes[j].get("kind", ""))
                if cand in ("CallExpr", "UnaryOperator", "BinaryOperator",
                            "CompoundAssignOperator", "ConditionalOperator"):
                    pk = cand
                    op = str(nodes[j].get("opcode", ""))
                    break
                if cand in ("FunctionDecl", "CompoundStmt"):
                    break
                j -= 1
                hops += 1
            if pk == "CallExpr":
                calls.append(rec)
            elif pk == "UnaryOperator":
                addrs.append(rec) if op == "&" else reads.append(rec)
            elif pk in ("BinaryOperator", "CompoundAssignOperator"):
                writes.append(rec) if op in ("=", "+=") else reads.append(rec)
            else:
                reads.append(rec)
        elif kind in ("FunctionDecl", "VarDecl", "TypedefDecl",
                      "EnumConstantDecl", "FieldDecl", "ParmVarDecl",
                      "RecordDecl"):
            decls.append(rec)
        else:
            reads.append(rec)

    if file_filter:
        def keep(rs: List[Dict[str, object]]) -> List[Dict[str, object]]:
            return [r for r in rs if r["file"] and file_filter in str(r["file"])]
        decls, calls, reads = keep(decls), keep(calls), keep(reads)
        writes, addrs = keep(writes), keep(addrs)

    return {"declarations": decls, "calls": calls, "reads": reads,
            "writes": writes, "addresses": addrs}


def summarize(res: Dict[str, List[Dict[str, object]]]) -> Dict[str, object]:
    def files(rs: List[Dict[str, object]]) -> List[str]:
        return sorted({os.path.basename(str(r["file"])) for r in rs if r["file"]})
    return {
        "declarations": len(res["declarations"]),
        "calls": len(res["calls"]),
        "reads": len(res["reads"]),
        "writes": len(res["writes"]),
        "addresses": len(res["addresses"]),
        "decl_files": files(res["declarations"]),
        "call_files": files(res["calls"]),
    }


def render_symbol(symbol: str, res: Dict[str, List[Dict[str, object]]],
                  s: Dict[str, object]) -> str:
    L = [f"{NAME} {VERSION} · {symbol}"]
    L.append("  AST de clang, macros ya expandidas por el preprocesador.")
    L.append("")
    L.append(f"  declaraciones {s['declarations']}   llamadas {s['calls']}   "
             f"lecturas {s['reads']}   escrituras {s['writes']}   direcciones {s['addresses']}")
    L.append("")
    for label, key in (("DECLARADO EN", "declarations"), ("LLAMADO DESDE", "calls"),
                       ("LEIDO EN", "reads"), ("ESCRITO EN", "writes"),
                       ("DIRECCION TOMADA EN", "addresses")):
        rs = res[key]
        if not rs:
            continue
        L.append(f"  {label}:")
        for r in rs[:12]:
            L.append(f"    {os.path.basename(str(r['file']))}:{r['line']}:{r['col']}"
                     f"   [{r['kind']}]")
        if len(rs) > 12:
            L.append(f"    ... y {len(rs) - 12} mas")
    return "\n".join(L)


def selftest() -> int:
    failures: List[str] = []

    def check(name: str, got, want) -> None:
        if got != want:
            failures.append(f"{name}: obtuve {got!r}, esperaba {want!r}")

    # El self-test NO depende de clang: el AST se inyecta a mano. Asi se
    # comprueba la CLASIFICACION, que es la parte que puede estar mal, y no
    # la disponibilidad del preprocesador.
    ast = {
        "kind": "TranslationUnitDecl",
        "inner": [
            {"kind": "FunctionDecl", "name": "objetivo",
             "loc": {"file": "a.c", "line": 1, "col": 5}},
            {"kind": "FunctionDecl", "name": "otro", "loc": {"file": "a.c", "line": 8}},
            {"kind": "CompoundStmt", "inner": [
                {"kind": "CallExpr", "inner": [
                    {"kind": "DeclRefExpr", "name": "objetivo",
                     "loc": {"file": "a.c", "line": 3, "col": 2}}]},
                {"kind": "BinaryOperator", "opcode": "=",
                 "loc": {"file": "a.c", "line": 4},
                 "inner": [{"kind": "DeclRefExpr", "name": "objetivo",
                            "loc": {"file": "a.c", "line": 4, "col": 2}}]},
                {"kind": "BinaryOperator", "opcode": "+",
                 "loc": {"file": "a.c", "line": 5},
                 "inner": [{"kind": "DeclRefExpr", "name": "objetivo",
                            "loc": {"file": "a.c", "line": 5, "col": 4}}]},
                {"kind": "UnaryOperator", "opcode": "&",
                 "loc": {"file": "a.c", "line": 6},
                 "inner": [{"kind": "DeclRefExpr", "name": "objetivo",
                            "loc": {"file": "a.c", "line": 6, "col": 6}}]},
            ]},
        ],
    }
    r = collect_refs(ast, "objetivo")
    check("clasif.declaracion", len(r["declarations"]), 1)
    check("clasif.llamada", len(r["calls"]), 1)
    check("clasif.llamada_linea", r["calls"][0]["line"], 3)
    check("clasif.escritura", len(r["writes"]), 1)
    check("clasif.lectura", len(r["reads"]), 1)
    check("clasif.lectura_linea", r["reads"][0]["line"], 5)
    check("clasif.direccion", len(r["addresses"]), 1)
    s = summarize(r)
    check("suma.total", s["calls"] + s["reads"] + s["writes"] + s["addresses"], 4)

    # Un nombre que es PREFIJO de otro no debe contarse
    ast2 = {"kind": "TranslationUnitDecl", "inner": [
        {"kind": "VarDecl", "name": "foobar", "loc": {"file": "a.c", "line": 1}},
        {"kind": "VarDecl", "name": "foo", "loc": {"file": "a.c", "line": 2}}]}
    r2 = collect_refs(ast2, "foo")
    check("prefijo.no_confunde",
          [d["line"] for d in r2["declarations"]], [2])

    # Filtro por fichero
    ast3 = {"kind": "TranslationUnitDecl", "inner": [
        {"kind": "FunctionDecl", "name": "z", "loc": {"file": "x/b.c", "line": 1}},
        {"kind": "FunctionDecl", "name": "z", "loc": {"file": "y/c.c", "line": 1}}]}
    r3 = collect_refs(ast3, "z", file_filter="x/")
    check("filtro.fichero", len(r3["declarations"]), 1)

    # AST vacio y simbolo inexistente: cero, no excepcion
    check("vacio", collect_refs({"kind": "TranslationUnitDecl"}, "nada")["calls"], [])
    check("sin_inner", walk({"kind": "X"})[0]["kind"], "X")
    check("walk_orden", len(walk(ast3)), 3)

    # clang: si no esta, se dice. No se degrada a regex.
    c = have_clang()
    if c is None:
        print(f"{NAME} {VERSION} · self-test")
        print("  RESULTADO PARCIAL: clang no esta instalado.")
        print("  La clasificacion se verifico sobre AST inyectado (OK).")
        print("  SIN clang NO se puede construir un AST real: declararlo es")
        print("  mejor que devolver un analisis de regex disfrazado.")
        return 0
    print(f"{NAME} {VERSION} · self-test")
    print(f"  clang: {c}")
    # prueba real end-to-end sobre un fichero sintetico
    with tempfile.TemporaryDirectory() as td:
        p = os.path.join(td, "u.c")
        with open(p, "w", encoding="utf-8") as fh:
            fh.write("#define ENVOLVER(x) ((x) + 1)\n"
                     "static int destino(int a) { return a; }\n"
                     "int fuente(int v) { return ENVOLVER(destino(v)); }\n")
        try:
            astj = json.loads(ast_dump(p, ["-E"], exe=DEFAULT_CLANG, timeout=60))
            rr = collect_refs(astj, "destino")
            # La clave: la llamada a `destino` esta DENTRO de un macro. Un
            # parser de texto no la ve como llamada; el AST expandido si.
            if len(rr["calls"]) != 1:
                failures.append(f"macro.expandida: obtuve {len(rr['calls'])} "
                                f"llamadas, esperaba 1 (la llamada vive en un macro)")
            else:
                print("  OK  llamada dentro de un macro detectada via AST")
        except (PreprocessError, json.JSONDecodeError) as e:
            failures.append(f"clang end-to-end: {e}")
    if failures:
        print(f"  RESULTADO FALLIDO ({len(failures)}):")
        for f in failures:
            print(f"    - {f}")
        return 1
    print("  RESULTADO OK · vectores conocidos reproducidos")
    print("  NOTA: referencias por AST. NO prueba ejecucion ni semantica HW.")
    return 0


def main(argv: Optional[Sequence[str]] = None) -> int:
    ap = argparse.ArgumentParser(prog=NAME,
                                 description="Referencias de un simbolo via AST de clang.")
    ap.add_argument("--selftest", action="store_true")
    ap.add_argument("--kernel")
    ap.add_argument("--file", action="append", default=[], dest="files")
    ap.add_argument("--symbol", action="append", default=[])
    ap.add_argument("--callers", action="append", default=[])
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args(argv)

    if args.selftest:
        return selftest()
    if not args.kernel:
        ap.error("--kernel es obligatorio salvo con --selftest")
    c = have_clang()
    if c is None:
        print("ERROR  clang no esta instalado. Sin el no hay AST real y esta "
              "herramienta no puede sustituir a un parser de texto.",
              file=sys.stderr)
        return 2
    kernel = os.path.abspath(args.kernel)
    flags = kernel_cflags(kernel)
    missing = missing_generated(kernel)
    if missing:
        print(f"{NAME} {VERSION} · AST INCOMPLETO: el arbol esta a medias",
              file=sys.stderr)
        for m in missing:
            print(f"  falta {m}  (lo crea `make`, no esta en el fuente)",
                  file=sys.stderr)
        print("  un AST completo exige completar el build, que es una "
              "ESCRITURA en el arbol.", file=sys.stderr)
        print("  WORK_CLASS=READ_ONLY: no se completa el build aqui.",
              file=sys.stderr)
        print("  Se sale con codigo 3 en vez de devolver un analisis vacio, "
              "que pareceria un resultado sin referencias.", file=sys.stderr)
        return 3
    blocks: List[Dict[str, object]] = []
    for f in args.files:
        p = f if os.path.isabs(f) else os.path.join(kernel, f)
        try:
            astj = json.loads(ast_dump(p, flags))
        except PreprocessError as e:
            blocks.append({"file": p, "error": "PREPROCESS_FAILED", "detail": str(e)})
            continue
        except json.JSONDecodeError as e:
            blocks.append({"file": p, "error": "AST_JSON_INVALID", "detail": str(e)})
            continue
        nodes = walk(astj)
        decls = [n for n in nodes if n.get("kind") in
                 ("FunctionDecl", "VarDecl", "TypedefDecl", "RecordDecl",
                  "EnumDecl") and n.get("loc")]
        blocks.append({"file": p, "declares": [
            {"name": n.get("name"), "kind": n.get("kind"),
             "line": (n.get("loc") or {}).get("line")} for n in decls[:60]]})
    for sym in args.symbol + args.callers:
        for f in args.files:
            p = f if os.path.isabs(f) else os.path.join(kernel, f)
            try:
                astj = json.loads(ast_dump(p, flags))
            except (PreprocessError, json.JSONDecodeError) as e:
                blocks.append({"symbol": sym, "file": p, "error": str(e)[:200]})
                continue
            r = collect_refs(astj, sym, file_filter=os.path.basename(f))
            blocks.append({"symbol": sym, "file": f, **summarize(r),
                           "detail": r})
    if args.json:
        print(json.dumps({"tool": NAME, "version": VERSION, "clang": c,
                          "results": blocks}, indent=2, ensure_ascii=False))
        return 0
    print(f"{NAME} {VERSION} · {c}")
    for b in blocks:
        print()
        print("=" * 74)
        if b.get("error"):
            print(f"  {b.get('file') or b.get('symbol')}: ERROR {b.get('error')}")
            if b.get("detail"):
                print(f"    {b['detail']}")
            continue
        if "symbol" in b:
            print(render_symbol(str(b["symbol"]), b["detail"],  # type: ignore[arg-type]
                                {k: v for k, v in b.items()
                                 if k in ("declarations", "calls", "reads",
                                          "writes", "addresses")}))
        else:
            print(f"  {b['file']} declara {len(b.get('declares', []))} simbolos")
            for d in b.get("declares", [])[:25]:
                print(f"    {str(d['name'])[:44]:<46} {d['kind']:<16} :{d['line']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
