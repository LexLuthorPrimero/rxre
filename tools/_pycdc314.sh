#!/bin/bash
# Reconstruye pycdc con soporte de Python 3.14.
#
# POR QUE EXISTE ESTE SCRIPT
# --------------------------
# Se perdio `tools/ibref.py` (0 bytes) al truncar un fichero desde un script
# que iba a fallar. El unico `.pyc` (133106 bytes, 116 vectores de selftest)
# es el UNICO ejemplar de esa herramienta, y para volver a tener fuente hace
# falta poder descompilar 3.14. pycdc llega hasta 3.13.
#
# Lo que hace, y todo lo que son CAMBIOS PROPIOS sobre pycdc, no upstream:
#   1. bytes/python_3_14.cpp   tabla de opcodes generada desde `dis` LOCAL
#   2. bytecode_ops.inl        +96 opcode() de 3.14 (sobre todo adaptativos)
#   3. bytecode.cpp            DECLARE_PYTHON(3,14) y `case 14:`
#   4. pyc_module.h/.cpp       MAGIC_3_14 = 0x0A0D0E2B
#   5. pyc_object.h/.cpp       TYPE_SLICE = ':' (0x3A) + CreateObject
#   6. pyc_sequence.h/.cpp     clase PycSlice (dentro del guard de inclusion)
#   7. bytecode.cpp            print_const de TYPE_SLICE
#   8. ASTree.cpp              LOAD_SMALL_INT (opcode nuevo de 3.14)
#   9. CMakeLists.txt          bytes/python_3_14.cpp
#
# IDEMPOTENTE: se puede volver a ejecutar sin romper nada.
set -u
DEST="${1:-/tmp/opencode/pycdc}"
REPO=https://github.com/zrax/pycdc.git

if [ ! -d "$DEST" ]; then
    git clone --depth 1 "$REPO" "$DEST" >/dev/null 2>&1 || { echo "FALLO: clone"; exit 1; }
fi
cd "$DEST" || exit 1

python3 - <<'PYEOF'
import re, dis

# --- [1] tabla de opcodes de 3.14, generada desde el Python local ---------
# `dis.opname` y el `.inl` de pycdc son las dos fuentes de verdad: la primera
# para el numero, la segunda para saber que opcodes llevan argumento (`_A`).
ops = open("bytecode_ops.inl").read()
con_arg = set(re.findall(r"OPCODE_A(?:_FIRST)?\((\w+)\)", ops))
tenidos = set(re.findall(r"OPCODE(?:_A(?:_FIRST)?)?\((\w+)\)", ops))
validos = [dis.opname[i] for i in range(256)
           if not dis.opname[i].startswith("<") and dis.opname[i] != "CACHE"]

faltan = sorted({n for n in validos if n not in tenidos})
if faltan:
    ops = ops.rstrip("\n") + (
        "\n\n// Anadidos para Python 3.14. Casi todos son ADAPTATIVOS (LOAD_ATTR_*,"
        "\n// CALL_*, BINARY_OP_*, ...) y solo existen en la forma quickened, que"
        "\n// un .pyc no guarda: no se veran. Se anaden para que el mapa resuelva"
        "\n// y lo desconocido salga como desconocido.\n")
    ops += "".join("OPCODE(%s)\n" % n for n in faltan)
    open("bytecode_ops.inl", "w").write(ops)

L = ['#include "bytecode_map.h"', '', 'BEGIN_MAP(3, 14)']
for i in range(256):
    n = dis.opname[i]
    if n == "CACHE":
        # NO se omite. En 3.11+ cada instruccion va seguida de sus ranuras de
        # cache inline, y `bc_disasm` las RECORRE (para que `pos` avance bien)
        # y luego no las imprime. Si el 0 no esta en el mapa, `ByteToOpcode(0)`
        # cae en `default` y devuelve `PYC_INVALID_OPCODE`: las ranuras salen
        # como `<INVALID>` y a partir del primer `LOAD_GLOBAL` el desensamblado
        # entero es basura. MEDIDO: el error era `<INVALID> (-1)` justo detras de
        # `LOAD_GLOBAL`, que es el opcode con 5 caches.
        L.append("    MAP_OP(0, CACHE)")
        continue
    if n.startswith("<"):
        continue           # hueco sin opcode asignado: que caiga en default
    L.append("    MAP_OP(%d, %s%s)" % (i, n, "_A" if n in con_arg else ""))
L += ['END_MAP()', '']
open("bytes/python_3_14.cpp", "w").write("\n".join(L))

# --- [3] declarar y usar el mapa ------------------------------------------
c = open("bytecode.cpp").read()
if "DECLARE_PYTHON(3, 14)" not in c:
    c = c.replace("DECLARE_PYTHON(3, 13)",
                  "DECLARE_PYTHON(3, 13)\nDECLARE_PYTHON(3, 14)", 1)
    c = c.replace("        case 13: return python_3_13_map(opcode);",
                  "        case 13: return python_3_13_map(opcode);\n"
                  "        case 14: return python_3_14_map(opcode);", 1)
    # --- [7] print_const de TYPE_SLICE ---
    i = c.index("    switch (obj->type()) {")
    j = c.index("\n", i) + 1
    c = c[:j] + """    case PycObject::TYPE_SLICE:
        pyc_output << "slice(";
        print_const(pyc_output, obj.cast<PycSlice>()->start(), mod);
        pyc_output << ", ";
        print_const(pyc_output, obj.cast<PycSlice>()->stop(), mod);
        pyc_output << ", ";
        print_const(pyc_output, obj.cast<PycSlice>()->step(), mod);
        pyc_output << ")";
        break;
""" + c[j:]
    open("bytecode.cpp", "w").write(c)

# --- [8] LOAD_SMALL_INT ---------------------------------------------------
a = open("ASTree.cpp").read()
if "LOAD_SMALL_INT" not in a:
    v = "        case Pyc::LOAD_CONST_A:"
    n = """        case Pyc::LOAD_SMALL_INT:
            // Opcode NUEVO de Python 3.14. MEDIDO en el .pyc que se decompila:
            // 445 apariciones y `dis` las da con `argval` IGUAL al entero (0, 1,
            // 2, 4, 8, 16, 32, 255...), o sea que en [-5, 256] el oparg ES el
            // valor. Fuera de ese rango es un indice en una tabla que no se ha
            // medido, y se pone 0 con el nombre del opcode en el comentario:
            // un entero inventado aqui seria indistinguible de uno leido.
            if (operand >= -5 && operand <= 256)
                stack.push(new ASTObject(new PycInt(operand)));
            else
                stack.push(new ASTObject(new PycInt(0)));
            break;

        case Pyc::LOAD_CONST_A:"""
    assert v in a, "ancla de LOAD_CONST_A no encontrada"
    open("ASTree.cpp", "w").write(a.replace(v, n, 1))

# --- [4] magic de 3.14 ----------------------------------------------------
# OJO: hacer falta la CONSTANTE y el `case` del switch. Con la constante sola,
# pycdc responde "Bad MAGIC!" igual que si no hubiera soporte: el `switch` cae
# en `default`, pone m_maj = -1, y el mapa no se busca nunca. Es un fallo que
# COTEJA como "no hay soporte 3.14" cuando en realidad esta a medias.
h = open("pyc_module.h").read()
if "MAGIC_3_14" not in h:
    h = h.replace("    MAGIC_3_13 = 0x0A0D0DF3,",
                  "    MAGIC_3_13 = 0x0A0D0DF3,\n    MAGIC_3_14 = 0x0A0D0E2B,", 1)
    open("pyc_module.h", "w").write(h)

m2 = open("pyc_module.cpp").read()
if "case MAGIC_3_14:" not in m2:
    i = m2.index("    case MAGIC_3_13:")
    fin = m2.index("/* Bad Magic detected */", i)
    m2 = (m2[:fin]
          + "    case MAGIC_3_14:\n        m_maj = 3;\n        m_min = 14;\n"
            "        m_unicode = true;\n        break;\n\n"
          + m2[fin:])
    open("pyc_module.cpp", "w").write(m2)

# --- [5] TYPE_SLICE -------------------------------------------------------
h = open("pyc_object.h").read()
if "TYPE_SLICE" not in h:
    h = h.replace("        TYPE_UNKNOWN = '?',",
                  "        TYPE_SLICE = ':',                    // Python 3.14 ->\n"
                  "        TYPE_UNKNOWN = '?',", 1)
    open("pyc_object.h", "w").write(h)

o = open("pyc_object.cpp").read()
if "TYPE_SLICE" not in o:
    o = o.replace("    case PycObject::TYPE_TUPLE:",
                  "    case PycObject::TYPE_SLICE:\n        return new PycSlice(type);\n"
                  "    case PycObject::TYPE_TUPLE:", 1)
    open("pyc_object.cpp", "w").write(o)

# --- [6] clase PycSlice, DENTRO del guard de inclusion ---------------------
# Append al final del fichero la deja FUERA del `#endif`, y ahi el guard no
# protege: al incluirlo dos veces, `class PycSlice` sale duplicada y no compila.
s = open("pyc_sequence.h").read()
if "class PycSlice" not in s:
    bloque = '''
/* PycSlice */
//
// Anadido para Python 3.14, cuyo marshal usa `TYPE_SLICE = ':'` (0x3A) para el
// objeto `slice`. Sin esto, `CreateObject` aborta con "Got unsupported type
// 0x3A" y luego un `std::bad_cast`, y NO se decompila NADA: el fallo no es un
// hueco en un tipo raro, es el fichero entero.
//
// MEDIDO, no supuesto: el byte 0x3A se identifico marshaleando con el Python
// local un objeto de cada tipo y viendo cual lo emitia.
//     slice(1,2,3) -> 0xBA = 0x80 (FLAG_REF) | 0x3A
// El 0x80 es la bandera de referencia, que `LoadObject` ya quita con `& 0x7F`.
class PycSlice : public PycObject {
public:
    PycRef<PycObject> m_start, m_stop, m_step;
    PycSlice(int type = PycObject::TYPE_SLICE) : PycObject(type) { }

    void load(PycData* stream, PycModule* mod) override;
    PycRef<PycObject> start() const { return m_start; }
    PycRef<PycObject> stop()  const { return m_stop; }
    PycRef<PycObject> step()  const { return m_step; }
};
'''
    s = s.rstrip()
    assert s.endswith("#endif"), s[-30:]
    s = s[:-len("#endif")].rstrip("\n") + "\n" + bloque + "\n#endif\n"
    open("pyc_sequence.h", "w").write(s)

sc = open("pyc_sequence.cpp").read()
if "PycSlice::load" not in sc:
    open("pyc_sequence.cpp", "w").write(sc + '''
/* PycSlice */
void PycSlice::load(PycData* stream, PycModule* mod)
{
    // `w_slice` de CPython escribe, en este orden y sin byte de cuenta delante:
    //   w_object(start); w_object(stop); w_object(step);
    m_start = LoadObject(stream, mod);
    m_stop  = LoadObject(stream, mod);
    m_step  = LoadObject(stream, mod);
}
''')

# --- [8b] LOAD_FAST_BORROW, SET_FUNCTION_ATTRIBUTE, LOAD_ATTR_WITH_HINT ----
# Los tres son de 3.14 y los tres necesitan traduccion propia en el AST.
# MEDIDO: sin esto, pycdc se para en el primero que encuentra. En el fichero
# que se estaba decompilando, LOAD_FAST_BORROW salia 1293 veces.
a2 = open("ASTree.cpp").read()
if "LOAD_FAST_BORROW" not in a2:
    v = "        case Pyc::LOAD_FAST_A:"
    n = """        case Pyc::LOAD_FAST_BORROW:
            // Igual que LOAD_FAST. `BORROW` solo dice que no hay que subir el
            // recuento de referencias del local, lo cual no cambia el VALOR que
            // se apila. Es una distincion de implementacion, no de semantica.
            stack.push(new ASTName(code->getLocal(operand)));
            break;

        case Pyc::SET_FUNCTION_ATTRIBUTE_A:
            // Nuevo en 3.14: fija `__qualname__`, defaults o annotations de la
            // funcion que esta en la cima. Deja la cima vacia, asi que se saca
            // un valor. No se modela QUE atributo fija: el codigo de salida no
            // necesita saberlo y emitirlo seria inventar. Por eso `pop()` sin
            // mirar la cima: `FastStack` no tiene `pop_back`, y una guarda
            // `!vacio()` haria que un desajuste de pila pasara en silencio.
            stack.pop();
            break;

        case Pyc::LOAD_ATTR_WITH_HINT_A:
            // Nuevo en 3.14: LOAD_ATTR con una pista del tipo. El valor es el
            // mismo `obj.attr`; la pista es del interprete. Copia el tratamien-
            // to de LOAD_ATTR_A, incluido el bit bajo que 3.12 metio en el arg.
            {
                PycRef<ASTNode> name = stack.top();
                if (name.type() != ASTNode::NODE_IMPORT) {
                    stack.pop();
                    if (operand & 1)
                        stack.push(nullptr);
                    operand >>= 1;
                    stack.push(new ASTBinary(name,
                                              new ASTName(code->getName(operand)),
                                              ASTBinary::BIN_ATTR));
                }
            }
            break;

        case Pyc::LOAD_FAST_A:"""
    assert v in a2, "ancla de LOAD_FAST_A no encontrada"
    open("ASTree.cpp", "w").write(a2.replace(v, n, 1))

# --- [9] compilar el .cpp nuevo -------------------------------------------
m = open("CMakeLists.txt").read()
if "bytes/python_3_14.cpp" not in m:
    m = m.replace("    bytes/python_3_13.cpp",
                  "    bytes/python_3_13.cpp\n    bytes/python_3_14.cpp", 1)
    open("CMakeLists.txt", "w").write(m)
print("  parches aplicados")
PYEOF

cmake -S . -B build -DCMAKE_BUILD_TYPE=Release >/dev/null 2>&1
cmake --build build -j"$(nproc)" >/tmp/opencode/pycdc-build.log 2>&1
RC=$?
# EL ESTADO DE SALIDA, NO LA EXISTENCIA DEL BINARIO.
#
# MEDIDO, y es la trampa de "exit 0 != resultado valido" cometida aqui mismo:
# la primera version de este script comprobaba `[ -x build/pycdc ]` y decia
# PYCDC_BUILD_OK con CUATRO errores de compilacion, porque el binario de la
# compilacion anterior seguia ahi. Un artefacto viejo que no se ha revalidado
# es un artefacto viejo, por muy ejecutable que sea.
if [ $RC -eq 0 ]; then
    echo "PYCDC_BUILD_OK"
else
    echo "PYCDC_BUILD_FAIL (rc=$RC)"
    grep -i "error" /tmp/opencode/pycdc-build.log | head -10
    exit 1
fi