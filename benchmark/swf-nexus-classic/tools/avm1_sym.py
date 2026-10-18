#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0
"""avm1_sym.py — Ejecutor simbolico lineal (interpretacion
abstracta ligera) del stream principal AVM1.

OBJETIVO (RXRE-SWF-049): recuperar la FORMULA de las
propiedades escritas via aritmetica en el stream
principal (Push/GetMember/Add/Multiply/SetMember),
dado que los CUERPOS de funcion son tokens nativos
(RXRE-SWF-048) y la formula NO esta en ellos.

Metodo: ejecucion lineal (ignora el flujo de control
por ahora — primera pasada) manteniendo una pila de
expresiones simbolicas.  Cuando un SetMember(0x4F)
escribe obj[clave]=valor, registra (objeto, clave,
expresion simbolica).

Semantica de opcodes usada:
  0x96 Push      : apila las constantes tipadas
  0x4E GetMember : pop clave, pop obj; push obj.clave
  0x4F SetMember : pop valor, pop clave, pop obj;
                   registra obj.clave = valor
  0x0A Add       : pop2 push (a+b)
  0x0B Subtract  : pop2 push (a-b)
  0x0C Multiply  : pop2 push (a*b)
  0x0D Divide    : pop2 push (a/b)
  0x12 Not       : pop1 push !(a)
  0x17 Pop       : pop1
  0x1C GetVariable: pop clave; push var.clave
  0x1D SetVariable: pop valor, pop clave; registra
  0x87 StoreRegister: pop valor; reg[n]=valor
  0x52 CallMethod : pop (args+met+obj); push call()
  0x9D BranchIf   : pop condicion (no se sigue)
  0x99 Jump       : sin efecto (no se sigue)
  netos CFG (0x40,0x49,0x3E,0x9F=-1; 0x42,0x81,0x8C=0)

LIMITACION: ejecucion LINEAL. Los merges de CFG no
se unen (una variable puede tener el valor de una
sola rama).  Las llamadas a metodos nativos (0x52)
producen un resultado opaco "?".  Esto es un
INSTRUMENTO DE INVESTIGACION, no un interprete
completo.
"""
import struct
import sys
import zlib

sys.path.insert(0, "tools")
import avm1_disasm as A


def _const_str(v):
    """Representacion de una constante Push."""
    if isinstance(v, bytes):
        return v.decode("latin1")
    if isinstance(v, tuple):
        # tipo 6: (float32, uint32)
        return "(%r,%r)" % v
    return repr(v)


class Sym:
    """Ejecutor simbolico lineal para un script.

    Seguimiento de profundidad de expresion (RXRE-SWF-049):
    expr_depth = profundidad de la pila DESPUES de la
    ultima accion TERMINADORA de sentencia
    (SetMember, SetVariable, Pop, StoreRegister,
    CallMethod, BranchIf, Jump).  En un CallMethod,
    el marco de llamada = profundidad_actual -
    expr_depth = args + objeto + metodo, porque los
    args se apilan justo despues de la terminadora
    anterior, luego el objeto se computa (GetMember,
    no terminadora) y luego el metodo (1 push).
    Esto recupera el # de args aunque sean
    computados via GetMember (que reinicia el
    contador de pushes consecutivos)."""

    TERMINATORS = {0x4F, 0x1D, 0x17, 0x87,
                   0x52, 0x9D, 0x99}

    def __init__(self, body, script_off, script_len, pool):
        self.body = body
        self.off = script_off
        self.end = script_off + script_len
        self.pool = pool
        self.stack = []
        self.regs = {}
        self.writes = []      # (obj, key, expr, action_idx)
        self.vars = {}
        self.expr_depth = 0
        self.corrupt = 0
        self.nip_count = 0
        self.actions, self.oend, self.valid = \
            A.walk_actions(body, script_off, self.end)

    def resolve(self, ptype, value):
        return A.resolve_constant(self.pool, ptype, value)

    def run(self):
        for idx, (code, doff, dlen) in enumerate(
                self.actions):
            data = self.body[doff:doff + dlen] \
                if dlen > 0 else b""
            self.step(code, data, idx)

    def push(self, v):
        self.stack.append(v)

    def pop(self):
        if self.stack:
            return self.stack.pop()
        self.corrupt += 1
        return "?"

    def _terminator(self):
        self.expr_depth = len(self.stack)

    def step(self, code, data, idx):
        if code == 0x96:        # Push
            parsed = A.parse_push_data(data)
            if parsed is None:
                return
            for t, v in parsed:
                if t == 4:        # Register
                    self.push("r%d" % v)
                elif t in (8, 9):  # Lookup / Const16
                    s = self.resolve(t, v)
                    self.push(s if s is not None
                              else "pool[%d]" % v)
                else:
                    self.push(_const_str(v))
        elif code == 0x4E:        # GetMember: pop key, pop obj
            key = self.pop()
            obj = self.pop()
            if isinstance(key, str) and not key.startswith(
                    ("pool[", "(", "r")):
                self.push("%s.%s" % (obj, key))
            else:
                self.push("%s[%s]" % (obj, key))
        elif code == 0x4F:        # SetMember: pop val,key,obj
            val = self.pop()
            key = self.pop()
            obj = self.pop()
            self.writes.append((obj, key, val, idx))
            self._terminator()
        elif code == 0x0A:        # Add
            b = self.pop()
            a = self.pop()
            self.push("(%s+%s)" % (a, b))
        elif code == 0x0B:        # Subtract
            b = self.pop()
            a = self.pop()
            self.push("(%s-%s)" % (a, b))
        elif code == 0x0C:        # Multiply
            b = self.pop()
            a = self.pop()
            self.push("(%s*%s)" % (a, b))
        elif code == 0x0D:        # Divide
            b = self.pop()
            a = self.pop()
            self.push("(%s/%s)" % (a, b))
        elif code == 0x12:        # Not
            a = self.pop()
            self.push("!(%s)" % a)
        elif code == 0x47:        # NIP (hipotesis RXRE-SWF-049):
            # elimina el elemento DEBAJO del tope.
            # En el patron de modificadores
            # (Push r1,"modX",1,r1,"statY" ->
            #  GetMember -> Push N -> Divide ->
            #  0x47 -> SetMember), la pila es
            #  [r1,"modX",1,(r1.statY/N)]; 0x47
            #  elimina el "1" -> [r1,"modX",
            #  (r1.statY/N)] -> SetMember:
            #  r1.modX = r1.statY/N.  Balance
            #  neto por sentencia: +5-1+1-1-1-3=0
            #  (con no-op seria +1, crecimiento
            #  no acotado).  0x47 es globalmente
            #  discordante (RXRE-SWF-046), asi que
            #  esto es una hipotesis local.
            if len(self.stack) >= 2:
                del self.stack[-2]
                self.nip_count += 1
            else:
                self.corrupt += 1
        elif code == 0x17:        # Pop
            self.pop()
            self._terminator()
        elif code == 0x1C:        # GetVariable: pop key
            key = self.pop()
            self.push("var.%s" % key)
        elif code == 0x1D:        # SetVariable: pop val,key
            val = self.pop()
            key = self.pop()
            self.writes.append(("var", key, val, idx))
            self._terminator()
        elif code == 0x87:        # StoreRegister
            if len(data) >= 1:
                val = self.pop()
                self.regs[data[0]] = val
            self._terminator()
        elif code == 0x52:        # CallMethod: marco
            # marco = profundidad - expr_depth
            # (args + objeto + metodo)
            frame = len(self.stack) - self.expr_depth
            if frame < 2:
                frame = 2        # minimo: objeto+metodo
            for _ in range(frame):
                self.pop()
            self.push("call()")
            self._terminator()
        elif code == 0x9D:        # BranchIf: pop cond
            self.pop()
            self._terminator()
        elif code == 0x99:        # Jump: sin efecto
            self._terminator()
        elif code in (0x40, 0x49, 0x3E, 0x9F):
            self.pop()              # neto -1 (CFG)
        elif code in (0x42, 0x81, 0x8C):
            pass                    # neto 0 (CFG)
        # else: opcode desconocido -> no-op


def analyze(swf_path):
    data = open(swf_path, "rb").read()
    body = zlib.decompress(data[8:])
    nbits = body[0] >> 3
    off = (5 + 4 * nbits + 7) // 8 + 4
    scripts = A.collect_scripts(body, off, len(body))
    for i, s in enumerate(scripts):
        s["_idx"] = i
    pools = A.build_script_pools(body, scripts)

    all_writes = []
    for s in scripts:
        if s["length"] <= 0:
            continue
        pool = pools.get(s["_idx"])
        sym = Sym(body, s["offset"], s["length"], pool)
        sym.run()
        for obj, key, val, idx in sym.writes:
            all_writes.append((s["_idx"], obj, key, val, idx))
    return all_writes


def main(swf_path):
    writes = analyze(swf_path)
    print("=== Ejecutor simbolico (RXRE-SWF-049) ===")
    print("escrituras recuperadas:", len(writes))
    print()
    # escrituras cuyo valor es una expresion aritmetica
    arith = [w for w in writes
             if any(op in str(w[3])
                    for op in ("+", "*", "-", "/"))]
    print("escrituras con expresion aritmetica:",
          len(arith))
    print()
    print("=== muestra de escrituras aritmeticas ===")
    for idx, obj, key, val, aidx in arith[:40]:
        print("  script=%d [%s].%s = %s" % (
            idx, obj, key, val))


if __name__ == "__main__":
    path = sys.argv[1] if len(sys.argv) > 1 else \
        "raw/original.swf"
    main(path)
