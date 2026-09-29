#!/usr/bin/env python3
"""
kbexpand.py - Expande un fichero kbuild (Makefile) contra un .config y devuelve
la lista de .o que kbuild construiria para el modulo `modname`.

MODELO Y LIMITES (declarados, no escondidos):
  * Reproduce:  obj-$(CONFIG_X) += / = ,  <mod>-y += ,  <mod>-objs += ,
                <mod>-$(CONFIG_X) += ,  ifneq/ifeq/ifdef/ifndef/else/endif ,
                include <ruta>,  y la resolucion de variables intermedias
                (p.ej. AMDKFD_FILES, AMD_POWERPLAY_FILES).
  * kbuild renombra <mod>-y y <mod>-m a <mod>-objs internamente; aqui se
    acepta cualquiera de los tres sufijos.
  * LIMITACION 1: no se evalua $(shell ...), $(wildcard ...) ni $(patsubst ...).
    Los tokens que empiezan por '$' se descartan y se avisa por stderr.
  * LIMITACION 2: `else ifeq (...)` se trata como `else` (no se modela el
    encadenamiento completo).
  * LIMITACION 3: un CONFIG_ ausente de .config se trata como cadena vacia
    (= no definido), que es lo que hace kbuild; NO se inventa un 'n'.

NO es un sustituto de `make`. Verificacion de confianza: contrastar siempre
el resultado con `modules.order`/`Module.symvers`/los simbolos del .ko.
"""
import os
import re
import sys

WARN = []


def load_config(path):
    cfg = {}
    with open(path, encoding="utf-8", errors="replace") as fh:
        for line in fh:
            s = line.strip()
            m = re.match(r"^# (CONFIG_\w+) is not set$", s)
            if m:
                cfg[m.group(1)] = "n"
                continue
            m = re.match(r"^(CONFIG_\w+)=(.*)$", s)
            if m:
                cfg[m.group(1)] = m.group(2).strip().strip('"')
    return cfg


def truthy(v):
    return v is not None and v not in ("", "n")


SUFFIX_RE = re.compile(r"^(?P<base>.*?)-(?:y|m|objs)$")


def split_args(s, delim=" "):
    """Divide argumentos de funcion make por `delim`, respetando parentesis."""
    args, depth, cur = [], 0, ""
    for ch in s:
        if ch == "(":
            depth += 1
        elif ch == ")":
            depth -= 1
        if ch == delim and depth == 0:
            if cur.strip():
                args.append(cur.strip())
            cur = ""
        else:
            cur += ch
    if cur.strip():
        args.append(cur.strip())
    return args


def join_continuations(lines):
    """Une lineas terminadas en '\\' en una sola linea logica.
    IMPORTANTE: el orden respecto al parseo de if/endif se preserva porque
    las continuaciones de kbuild nunca cortan una linea de control."""
    out, buf = [], ""
    for ln in lines:
        s = ln.rstrip()
        if s.endswith("\\"):
            buf += s[:-1] + " "
            continue
        out.append(buf + s)
        buf = ""
    if buf:
        out.append(buf)
    return out


FUNCS = ("addprefix", "addsuffix", "subst")


def expand_func(name, body, subst, lookup):
    """Resuelve las funciones make soportadas. Devuelve cadena."""
    if name == "addprefix" and len(split_args(body, ",")) == 2:
        p, lst = split_args(body, ",")
        return " ".join(subst(p) + t for t in subst(lst).split())
    if name == "addsuffix" and len(split_args(body, ",")) == 2:
        s, lst = split_args(body, ",")
        return " ".join(t + subst(s) for t in subst(lst).split())
    if name == "subst" and len(split_args(body, ",")) == 3:
        f, t, s = split_args(body, ",")
        return subst(s).replace(subst(f), subst(t))
    WARN.append("funcion make no soportada: $(%s ...)" % name)
    return ""


def expand_refs(text, subst, lookup):
    """Sustituye-balancedemente $(...) y ${...}, recursivo y acotado.

    `lookup` resuelve un NOMBRE de variable desnudo; `subst` resuelve una
    expresion arbitraria. Se distinguen porque `$(VAR)` sin argumentos no es
    una llamada a funcion y debe resolverse por nombre, no re-expandirse.
    """
    for _ in range(16):
        out, i, changed = [], 0, False
        while i < len(text):
            if text[i] == "$" and i + 1 < len(text) and text[i + 1] in "({":
                openc, closec = ("(", ")") if text[i + 1] == "(" else ("{", "}")
                depth, j = 0, i + 1
                while j < len(text):
                    if text[j] == openc:
                        depth += 1
                    elif text[j] == closec:
                        depth -= 1
                        if depth == 0:
                            break
                    j += 1
                if j >= len(text):
                    out.append(text[i])
                    i += 1
                    continue
                inner = text[i + 2:j]
                mm = re.match(r"^(\w+)\s+(.*)$", inner, re.S)
                if mm and mm.group(1) in FUNCS:
                    out.append(expand_func(mm.group(1), mm.group(2),
                                           subst, lookup))
                elif re.match(r"^[\w.]+$", inner.strip()):
                    out.append(lookup(inner.strip()))
                else:
                    out.append(subst(inner.strip()))
                i = j + 1
                changed = True
            else:
                out.append(text[i])
                i += 1
        new = "".join(out)
        if not changed or new == text:
            return new
        text = new
    return text


def parse(path, cfg, srcdir, vars_, seen, depth=0):
    """Procesa un kbuild file, acumulando en vars_."""
    if depth > 24:
        return
    ap = os.path.realpath(path)
    if ap in seen:
        return
    seen.add(ap)
    here = os.path.dirname(ap)

    def cfgval(name):
        return cfg.get(name, "")

    def subst(text):
        """Sustitucion de $(VAR)/${VAR} con parentesis balanceados."""
        return expand_refs(text, subst, _lookup)

    def _lookup(name):
        if name.startswith("CONFIG_"):
            return cfgval(name)
        if name in vars_:
            return vars_[name]
        if name in ("src", "obj"):
            return here
        if name == "FULL_AMD_PATH":
            return os.path.normpath(os.path.join(here, ".."))
        if name == "DISPLAY_FOLDER_NAME":
            return "display"
        WARN.append("variable no resuelta: $(%s) en %s" % (name, ap))
        return ""

    with open(ap, encoding="utf-8", errors="replace") as fh:
        raw_lines = join_continuations(fh.read().splitlines())

    stack = []  # [activo, ya_visto_else]

    def active():
        return all(c[0] for c in stack)

    for raw in raw_lines:
        s = raw.strip()

        m = re.match(r"^ifn?eq\s*\(\s*(\S+?)\s*(?:,\s*(\S*?)\s*)?\)\s*$", s)
        if m:
            lhs, rhs = m.group(1), m.group(2)
            if rhs is None:                      # ifeq(X)  -> "¿X es no vacío?"
                v = truthy(lhs if lhs.startswith("CONFIG_")
                           else subst(lhs))
            else:                                 # ifeq(A,B) -> igualdad
                a = lhs if lhs.startswith("CONFIG_") else subst(lhs)
                b = rhs if rhs.startswith("CONFIG_") else subst(rhs)
                v = (a == b)
            stack.append([v, False])
            continue
        m = re.match(r"^ifn?def\s+(\S+)$", s)
        if m:
            v = bool(cfgval(m.group(1))) if m.group(1).startswith("CONFIG_") \
                else bool(subst(m.group(1)))
            stack.append([v, False])
            continue
        if s == "else":
            if stack:
                t = stack[-1]
                t[0] = not t[1]
                t[1] = True
            continue
        if s == "endif":
            if stack:
                stack.pop()
            continue

        if not active():
            continue

        m = re.match(r"^\s*include\s+(.+?)\s*$", raw)
        if m:
            # `include` acepta una LISTA de rutas separada por espacios.
            for p in subst(m.group(1)).split():
                cand = p if os.path.isabs(p) else os.path.normpath(
                    os.path.join(here, p))
                if os.path.isfile(cand):
                    parse(cand, cfg, srcdir, vars_, seen, depth + 1)
                else:
                    WARN.append("include no encontrado: %s" % cand)
            continue

        # asignacion:  VAR[+]= valor
        m = re.match(r"^\s*(?P<var>[A-Za-z0-9_.\-]*?)"
                     r"(?P<cfg>\$\(CONFIG_\w+\))?"
                     r"\s*(?P<op>\+=|:=|=)\s*(?P<rest>.*)$", raw)
        if not m:
            continue
        var = m.group("var")
        cfgexpr = m.group("cfg")
        op = m.group("op")
        rest = m.group("rest")
        rest = re.sub(r"\s*\\$", "", rest)      # continuacion de linea
        rest = rest.split("#")[0].strip()

        if cfgexpr and not truthy(cfgval(cfgexpr[2:-1])):
            continue                             # rama CONFIG_ no satisfecha
        val = subst(rest)
        base = var
        sm = SUFFIX_RE.match(base)
        if sm:
            base = sm.group("base")
        if base.endswith("-"):        # p.ej. "amdgpu-" en amdgpu-$(CONFIG_X)+=
            base = base[:-1]
        key = base
        if op in ("=", ":="):
            vars_[key] = val
        else:
            vars_[key] = (vars_.get(key, "") + " " + val).strip()


def tokens(text):
    out = []
    for t in text.split():
        if t.startswith("$"):
            WARN.append("token no resuelto (posible $(shell)/$(wildcard)): %s" % t)
            continue
        if t.endswith((".o", ".a")):
            out.append(t)
    return out


def main():
    if len(sys.argv) < 4:
        sys.exit(__doc__)
    makefile, config, modname = sys.argv[1], sys.argv[2], sys.argv[3]
    cfg = load_config(config)
    vars_ = {}
    parse(makefile, cfg, os.path.dirname(os.path.abspath(makefile)),
          vars_, set())
    key = modname
    if key not in vars_ and SUFFIX_RE.match(modname):
        key = SUFFIX_RE.match(modname).group("base")
    val = vars_.get(key, "")
    objs = sorted(set(tokens(val)))
    for o in objs:
        print(o)
    for w in sorted(set(WARN)):
        sys.stderr.write("AVISO: %s\n" % w)


if __name__ == "__main__":
    main()
