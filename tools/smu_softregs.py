#!/usr/bin/env python3
"""smu_softregs.py — comprueba el invariante de los SoftRegisters de SMU7.

PREGUNTA
    Las copias per-generacion de la struct SoftRegisters  ( smu71.h .. smu75.h  y
    smu7_discrete.h  )  ponen sus campos comunes en el MISMO offset,  o divergen?

POR QUE IMPORTA
    MEDIDO 2026-10-06,  hallazgo 1558:  el bloque DRAM_LOG_* esta en el offset 80
    en smu72, smu73, smu74, smu75  y smu7_discrete,  y en 76 en smu71.  Cinco
    headers coinciden byte a byte  y NADA en el arbol lo comprueba.

    Y el peor caso medido es de 4 bytes,  que es UN uint32_t:  un offset equivocado
    no da fallo,  da una escritura en el campo vecino.  Ese modo de fallo ya
    existe una vez en el arbol  ( 7.1 contra 7.2  ).

METODO,  Y POR QUE ESTE
    DOS Productores INDEPENDIENTES,  y se comparan:

      1) PARSEO.  Se leen los campos de cada struct en orden,  con su tipo y su
         multiplicador de array,  y se calcula el offset sumando anchos.  Es
         barato y no necesita nada del sistema.
      2) COMPILACION.  Se genera una translation unit por header  que imprime
         offsetof() real,  y se ejecuta.  Es la verdad.

    Los headers son layouts ALTERNATIVOS y se redefinen si se incluyen juntos  --
    eso esta medido,  no supuesto  -- asi que una TU por generacion no es un
    capricho:  es la unica forma de compilar.

    Que los dos coincidan NO es decorativo:  el parseo es el que puede mentir
    sobre el ancho de un tipo,  y la compilacion no.  Si divergen,  el informe
    lo dice  en vez de elegir uno.

PARA QUE SIRVE
    No es un checksum de ficheros.  Es un invariante SEMANTICO:  que este codigo,
    hoy, pone DRAM_LOG_ADDR_H en el mismo sitio para toda la familia.  Si alguien
    anade un campo antes del bloque en uno solo de los cinco,  esto se pone rojo.

ESTADO
    SELF_TESTED.  No validado contra hardware,  y no lo necesita:  la afirmacion
    que hace  ("estos offsets coinciden")  es de compilacion,  no de siliconio.
"""

import os
import re
import subprocess
import sys
import tempfile

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
INC = os.path.join(RAIZ, "RESEARCH", "working", "linux-7.1.3", "drivers",
                   "gpu", "drm", "amd", "pm", "powerplay", "inc")

# (fichero, struct)  en orden de generacion.  El que usa la RX550 lo decide el
# smumgr  ( 1558: polaris10_get_offsetof  ->  SMU74_SoftRegisters  ),  no el
# nombre del ASIC.  Este checker no elige:  comprueba que todos coincidan.
COPIAS = [
    ("smu71.h",       "SMU71_SoftRegisters"),
    ("smu72.h",       "SMU72_SoftRegisters"),
    ("smu73.h",       "SMU73_SoftRegisters"),
    ("smu74.h",       "SMU74_SoftRegisters"),
    ("smu75.h",       "SMU75_SoftRegisters"),
    ("smu7_discrete.h", "SMU7_SoftRegisters"),
]

# Macros de tamano que smu7_discrete.h y smu7_fusion.h necesitan.  Sus VALORES
# no afectan a los offsets de SoftRegisters  -- MEDIDO:  compilar con 8/8/4  y con
# 3/2/1  da el mismo resultado  -- pero hay que definirlas para que compile.
MACROS = {
    "SMU__NUM_PCIE_DPM_LEVELS": 8,
    "SMU__NUM_SCLK_DPM_STATE": 8,
    "SMU__NUM_MCLK_DPM_LEVELS": 4,
    "SMU__NUM_LCLK_DPM_LEVELS": 8,
}

# Ancho en bytes de los tipos que aparecen en estos headers.  Se usa SOLO en el
# productor de parseo,  y su exactitud la decide el cruce con la compilacion.
ANCHOS = {
    "uint8_t": 1, "uint16_t": 2, "uint32_t": 4, "uint64_t": 8,
    "int8_t": 1, "int16_t": 2, "int32_t": 4, "int64_t": 8,
    "UCHAR": 1, "USHORT": 2, "ULONG": 4, "UINT": 4, "UCHAR": 1, "U8": 1,
    "U16": 2, "U32": 4, "U64": 8,
}

TIPO_RE = re.compile(r"^\s*(?P<tipo>[A-Za-z_][A-Za-z0-9_]*)\s+(?P<nombre>[A-Za-z_][A-Za-z0-9_]*)"
                     r"\s*(?:\[(?P<n>\d+)\])?\s*;\s*$")
ARRAY_RE = re.compile(r"\[(?P<n>\d+)\]")


def ruta(header):
    return os.path.join(INC, header)


# ---------------------------------------------------------------- 1) PARSEO ---
def campos_por_parseo(header, struct):
    """[(campo, offset_calculado)]  del struct, leyendo el fichero.

    NO es la verdad.  Es el segundo productor,  y existe para poder Comparar con
    la compilacion  y detectar que el parseo se equivoca  en vez de que su
    equivocacion pase por medida.
    """
    p = ruta(header)
    if not os.path.exists(p):
        return None
    dentro = False
    pendiente = False
    off = 0
    out = []
    for linea in open(p, encoding="utf-8", errors="replace"):
        s = linea.strip()
        if not dentro:
            #  MEDIDO 2026-10-06:  este regex exigia la LLAVE EN LA MISMA LINEA
            #  que el nombre.  smu7_discrete.h:38-39 parte los dos:
            #      38  struct SMU7_SoftRegisters
            #      39  {
            #  y el resultado era CERO CAMPOS para esa cabecera,  en silencio.
            #  Los otros cinco si la traen en la misma linea,  asi que el fallo
            #  parecia un dato  --  "este struct no declara campos"  --  y no un
            #  defecto.  Se/downloads lo Shakespeare's manifestaba el producto de
            #  la interseccion dando cero.
            if re.match(r"^\s*struct\s+%s\s*\{?\s*$" % re.escape(struct), linea):
                dentro = True
                off = 0
                pendiente = "{" not in linea
            continue
        if pendiente:
            if "{" in s:
                pendiente = False
            continue
        if s.startswith("}"):
            return out
        m = TIPO_RE.match(linea)
        if not m:
            continue
        tipo = m.group("tipo")
        if tipo not in ANCHOS:
            #  Tipo no sencillo:  no sé su ancho.  No lo invento y no lo salto en
            #  silencio:  lo marco,  porque a partir de aqui el offset acumulado
            #  deja de ser fiable.
            out.append((m.group("nombre"), None))
            continue
        ancho = ANCHOS[tipo]
        n = int(m.group("n")) if m.group("n") else 1
        out.append((m.group("nombre"), off))
        off += ancho * n
    return out


# --------------------------------------------------------- 2) COMPILACION ---
def offsets_por_compilacion(header, struct, campos, cc="gcc"):
    """{campo: offset_real}  compilando una TU por generacion.

    Si no compila  o  no ejecuta,  devuelve  (None, motivo)  y el informe lo dice.
    No devuelve un dict vacio  -- un {}  se confunde con "no hay divergencias".
    """
    if not os.path.exists(ruta(header)):
        return None, "no existe %s" % header
    cuerpo = ["#include <stdint.h>", "#include <stddef.h>", "#include <stdio.h>",
              "#pragma pack(push, 1)", '#include "%s"' % header, "#pragma pack(pop)",
              "int main(void) {"]
    for c in campos:
        cuerpo.append('\tprintf("%s %%zu\\n", offsetof(%s, %s));'
                      % (c, struct, c))
    cuerpo += ["\treturn 0;", "}"]
    with tempfile.TemporaryDirectory() as td:
        src = os.path.join(td, "p.c")
        binp = os.path.join(td, "p")
        with open(src, "w", encoding="utf-8") as f:
            f.write("\n".join(cuerpo) + "\n")
        flags = []
        for k, v in MACROS.items():
            flags.append("-D%s=%d" % (k, v))
        cmd = [cc, "-w", "-o", binp, src, "-I%s" % INC] + flags
        r = subprocess.run(cmd, capture_output=True, text=True)
        if r.returncode != 0:
            primera = [x for x in r.stderr.splitlines() if "error" in x]
            return None, (primera[0][:90] if primera else "gcc fallo")
        r = subprocess.run([binp], capture_output=True, text=True)
        if r.returncode != 0:
            return None, "la sonda no ejecuto"
        out = {}
        for linea in r.stdout.splitlines():
            k, _, v = linea.partition(" ")
            out[k] = int(v)
        return out, None


# ---------------------------------------------------------------- INFORME ---
def p4s(probs):
    return "\n".join(probs)


def recoge(campos):
    """Fila por copia,  con su offset real.  Sin interpretar nada."""
    filas = []
    for header, struct in COPIAS:
        off, motivo = offsets_por_compilacion(header, struct, campos)
        filas.append((header, struct, off, motivo))
    return filas


def compara(filas, campos):
    """LOS MISMOS FILTROS,  sin tocar la compilacion.

    MEDIDO 2026-10-06:  esto estaba dentro de  comprobacion()  junto con la
    recoleccion,  y no se podia ejercitar con filas inventadas.  La mutacion que
    importa --"¿detecta el checker una divergencia?"--  no se podia responder,  y
    un vector que dice "detecta una divergencia" sin poder plantarla  es un vector
    que no prueba nada.  Eso es el fallo de 1209 repetido.
    """
    problemas = []
    rotas = []
    for header, struct, off, motivo in filas:
        if off is None:
            rotas.append("%s / %s: %s" % (header, struct, motivo))
    #
    #  MEDIDO 2026-10-06:  la primera version elegia la PRIMERA fila que compilaba
    #  como base  y  nombraba la divergencia contra ella.  Con COPIAS[0] = smu71,
    #  eso reportaba  "smu72 tiene ADDR_H en 80 y smu71 en 76"  culpando a smu72,
    #  cuando smu71 es el raro.  EL BLAME DEPENDIA DEL ORDEN DE LA LISTA,  que es
    #  lo peor que puede tener una herramienta de verificacion:  el mismo hecho
    #  con la lista reordenada acusa a otro.
    #
    #  Ahora no hay base.  Se agrupa por valor  y se dice quien esta en cada grupo.
    #  Siete de ocho en un valor y uno en otro  se lee solo:  el raro es el minimo.
    #
    for c in campos:
        grupos = {}
        for header, struct, off, motivo in filas:
            if off is None or c not in off:
                continue
            grupos.setdefault(off[c], []).append(header)
        if len(grupos) > 1:
            desc = "   |   ".join(
                "offset %d:  %s" % (v, ", ".join(sorted(hs)))
                for v, hs in sorted(grupos.items()))
            problemas.append("%s  NO ES UNIFORME  ->  %s" % (c, desc))
    #
    #  Y si no compilo ninguna,  no se pierde el porque de cada una.
    if not any(off is not None for _, _, off, _ in filas):
        return rotas + ["ninguna copia compilo:  no hay nada que comparar"]
    return rotas + problemas


def comprobacion(campos):
    return recoge(campos), compara_recoge(campos)


def compara_recoge(campos):
    return compara(recoge(campos), campos)


def informe(campos):
    print("  INVARIANTE DE LOS SoftRegisters DE SMU7")
    print("  %d campos,  %d copias,  productor: compilacion con offsetof\n"
          % (len(campos), len(COPIAS)))
    filas, problemas = comprobacion(campos)
    cab = "  %-24s" % "campo"
    for h, _, _, _ in filas:
        cab += "%-10s" % h.replace("smu", "").replace("_discrete.h", "_disc").replace(".h", "")
    print(cab)
    for c in campos:
        linea = "  %-24s" % c
        vals = set()
        for h, s, off, mot in filas:
            if off is None:
                linea += "%-10s" % "?"
                continue
            linea += "%-10d" % off[c]
            vals.add(off[c])
        print(linea + ("   UNICO" if len(vals) == 1 else "   <-- DIVERGE"))
    print()
    if problemas:
        print("  DIVERGENCIAS / FALLOS:")
        for p in problemas:
            print("      %s" % p)
    else:
        print("  Sin divergencias entre las copias que compilaron.")
    return problemas


# --------------------------------------------------------------- SELFTEST ---
VECTORES = {
    "V0": 'los seis headers existen',
    "V1": 'el productor de compilacion devuelve offsets reales en las seis copias',
    "V2": 'el productor de parseo devuelve campos',
    "V3": 'los offsets del parseo coinciden con los de la compilacion',
    "V4": 'el checker DETECTA la divergencia real del arbol  (  SMU71 76 contra 80  )',
    "V5": 'una divergencia PLANTADA de 4 bytes se detecta',
    "V6": 'una fila que no compila se reporta como fallo,  no se ignora en silencio',
    "V7": 'el caso PARCIAL  (una copia rota  y las demas bien)  conserva el motivo Y la divergencia',
    "V8": "si no compila ninguna copia,  se dice y no se devuelve 'sin divergencias'",
    "V9": "los offsets NO dependen de SMU__NUM_*:  es una invariancia comprobada, no casual",
    "V11": "el modo --todos declara cuantos campos se preguntan  y cuantos hay",
}


def selftest():
    fallos = []
    total = [0]

    def chk(nombre, cond, detalle=""):
        total[0] += 1
        if not cond:
            fallos.append((nombre, str(detalle)[:110]))

    for h, s in COPIAS:
        chk(VECTORES["V0"] + "  (%s)" % h, os.path.exists(ruta(h)), ruta(h))

    campos = ["DRAM_LOG_ADDR_H", "DRAM_LOG_ADDR_L", "DRAM_LOG_PHY_ADDR_H",
              "DRAM_LOG_PHY_ADDR_L", "DRAM_LOG_BUFF_SIZE"]
    motivos = [offsets_por_compilacion(h, s, campos)[1] for h, s in COPIAS]
    chk(VECTORES["V1"], all(m is None for m in motivos), motivos)

    pp = campos_por_parseo("smu74.h", "SMU74_SoftRegisters") or []
    chk(VECTORES["V2"], len(pp) > 5, "el parseo devolvio %d campos" % len(pp))

    #  CRUCE DE LOS DOS PRODUCTORES.  El parseo calcula;  la compilacion mide.  Si
    #  no coinciden,  el parseo miente  y el informe tiene que decirlo.
    real = offsets_por_compilacion("smu74.h", "SMU74_SoftRegisters", campos)[0]
    dict_pp = {n: o for n, o in pp if o is not None}
    chk(VECTORES["V3"],
        all(c in dict_pp and dict_pp[c] == real.get(c) for c in campos),
        "parseo %s contra compilacion %s" % (dict_pp, real))

    filas = recoge(campos)
    probs = compara(filas, campos)
    #  El estado real TIENE una divergencia:  SMU71 pone el bloque en 76 y los
    #  otros cinco en 80.  Un checker que no la ve  no sirve para nada,  asi que
    #  el vector ES "la ve".
    no_unif = [p for p in probs if "NO ES UNIFORME" in p]
    con_smu71 = [p for p in no_unif if "smu71.h" in p and "smu7_discrete" in p]
    chk(VECTORES["V4"], len(no_unif) == len(campos) and len(con_smu71) == len(campos),
        "no uniformes: %d,  que separan smu71 del resto: %d  ->  %s"
        % (len(no_unif), len(con_smu71), no_unif[:1]))

    #  MUTACION PLANTADA.  Copio las filas de smu74  y le muevo un campo 4 bytes.
    #  Es el desplazamiento real entre 7.1 y 7.2,  y es el modo de fallo que mas
    #  importa porque 4 bytes  =  un uint32_t  y no da ningun fallo.
    plantado = []
    for h, s, off, mot in filas:
        if h == "smu74.h" and off is not None:
            off2 = dict(off)
            off2["DRAM_LOG_ADDR_H"] = off2["DRAM_LOG_ADDR_H"] + 4
            off = off2
        plantado.append((h, s, off, mot))
    probs2 = compara(plantado, campos)
    chk(VECTORES["V5"], any("smu74.h" in p and "DRAM_LOG_ADDR_H" in p for p in probs2),
        "la mutacion plantada no salio:  %s" % probs2[:2])

    rotas = [(h, s, None, "gcc fallo") for h, s, _, _ in filas]
    probs3 = compara(rotas, campos)
    chk(VECTORES["V6"], sum(1 for p in probs3 if "gcc fallo" in p) == len(COPIAS),
        "una copia rota debe aparecer como problema:  %s" % probs3[:2])

    #  CASO PARCIAL.  MEDIDO 2026-10-06:  este vector no existia  y lo revelo una
    #  mutacion que se quedaba en verde:  quitar  "rotas +"  del return de la via
    #  normal  no lo detectaba nadie,  porque el otro return  (  el de "ninguna
    #  copila"  )  si lo conservaba  y ahi si hay vector.  O sea:  la via de
    #  "todo compila"  y  la de "nada compila"  estaban cubiertas,  y la de "algo
    #  compila"  no.  Un fallo de compilacion de una sola cabecera de la familia es
    #  justo el caso que mas se va a dar,  y era el unico sin probar.
    #  MEDIDO 2026-10-06:  la primera version de este vector ponia  off = None
    #  y dejaba  mot  como estaba  —  que era None,  porque esa copia SI compilaba.
    #  Y el vector buscaba la cadena "gcc fallo",  que no aparecia.  O sea  el
    #  vector fallaba por como lo habia construido,  no por la herramienta.
    #  Pero alarlo sale algo real:  en  recoge()  un  off = None  SIEMPRE viene
    #  con un motivo real,  y eso es un invariante de los datos que no estaba
    #  escrito en ningun sitio.  Si alguna vez  off=None  con  motivo=None  llegara
    #  aqui,  el informe imprimiria  "None"  como si fuera una causa.
    #  Por eso el vector monta el caso como lo monta la vida real:  sin motivo.
    for h, s, off, mot in filas:
        if off is None and mot is None:
            chk("toda fila sin offsets trae un motivo real", False,
                "%s / %s:  off=None con motivo=None" % (h, s))
    parcial = []
    for h, s, off, mot in filas:
        if h == "smu73.h":
            off, mot = None, "gcc fallo plantado"
        parcial.append((h, s, off, mot))
    probs4 = compara(parcial, campos)
    rotas_contadas = sum(1 for p in probs4 if "gcc fallo" in p)
    rotas_contadas += 1 if "smu73.h" in p4s(probs4) else 0
    no_unif4 = sum(1 for p in probs4 if "NO ES UNIFORME" in p)
    chk(VECTORES["V7"],
        ("plantado" in "\n".join(probs4)) and no_unif4 == len(campos),
        "parcial:  motivo conservado=%s,  no uniformes=%d de %d esperados  ->  %s"
        % ("plantado" in "\n".join(probs4), no_unif4, len(campos), probs4[:2]))

    #  Se aserta la PROPIEDAD,  no la redaccion:  que el checker diga que no hay
    #  nada que comparar.  Una version anterior de este vector comparaba la frase
    #  literal,  y fallo solo porque habia cambiado el texto  --  o sea  estaba
    #  probando el mensaje,  no el comportamiento.
    todas_roto = compara([(h, s, None, "gcc fallo") for h, s, _, _ in filas], campos)
    dice_no_compara = any(("no hay nada que comparar" in p or "nada que comparar" in p)
                          for p in todas_roto)
    no_dice_sin_divergencias = not any("NO ES UNIFORME" in p for p in todas_roto)
    chk(VECTORES["V8"], dice_no_compara and no_dice_sin_divergencias
        and sum(1 for p in todas_roto if "gcc fallo" in p) == len(COPIAS),
        "sin copias debe decir que no puede comparar Y conservar los motivos:  %s"
        % todas_roto[:2])
    #  INVARIANCIA,  Y POR QUE ES UN VECTOR Y NO UNA SUERTE.
    #
    #  MEDIDO 2026-10-06:  mutar  SMU__NUM_MCLK_DPM_LEVELS  de 4 a 7  deja el
    #  selftest en VERDE.  Durante un momento  eso parece un hueco de cobertura.
    #  No lo es:  en 1558  ya se habia medido que 8/8/4  y 3/2/1  dan el mismo
    #  offset,  porque esas macros son tamanos de array que no van antes del bloque.
    #  O sea  la inmunidad es CORRECTA.  Pero correcta por casualidad  es una
    #  invariancia que se pierde en cuanto alguien compila el struct de otra forma,
    #  y este tool no lo notaria.  Convertirla en vector la deja vigilada.
    #  V11.  La reduccion por nombre tiene que ser VISIBLE  (  ver  --todos  ).
    declarados = min(len(campos_por_parseo(h, s) or []) for h, s in COPIAS)
    preguntados = len(campos_comunes())
    chk(VECTORES["V11"], preguntados > 0 and declarados >= preguntados,
        "declarados %d,  preguntados %d" % (declarados, preguntados))
    cod, txt = _main_capturado(["--todos"])
    chk("main(--todos) se ejecuta y termina",
        cod is not None, "main devolvio %s" % cod)
    chk("main(--todos) IMPRIME el aviso de reduccion,  no solo la cuenta",
        "AVISO" in txt and "deja fuera" in txt,
        "la salida no menciona la reduccion:  %s" % txt[:120])
    #  Aserto por NUMERO,  no por frase.  MEDIDO 2026-10-06:  un vector anterior
    #  comprobaba que la salida contenga las dos frases,  y una mutacion que
    #  imprimia el mismo numero dos veces  —  "40 preguntados por 40 declarados"  —
    #  lo dejaba EN VERDE.  Frase esta bien,  numero no:  una cuenta que miente
    #  sigue diciendo lo mismo.
    import re as _re
    mdecl = _re.search(r"copia mas pequena: (\d+)", txt)
    mpreg = _re.search(r"preguntados por nombre: (\d+)", txt)
    chk("main(--todos) dice las DOS CUENTAS,  y son distintas  (  reduccion real  )",
        mdecl is not None and mpreg is not None
        and int(mdecl.group(1)) == declarados
        and int(mpreg.group(1)) == preguntados
        and int(mdecl.group(1)) != int(mpreg.group(1)),
        "declarados %s  preguntados %s  (calculados %d y %d)"
        % (mdecl and mdecl.group(1), mpreg and mpreg.group(1), declarados, preguntados))
    chk("el modo --todos declara la reduccion  (  no la hace en silencio  )",
        declarados > preguntados,
        "si declarados == preguntados,  este vector dejaria de comprobar la "
        "reduccion:  habria que cambiarlo cuando el truncado se arregle")

    antes = offsets_por_compilacion("smu7_discrete.h", "SMU7_SoftRegisters", campos)[0]
    global MACROS
    guardado = dict(MACROS)
    try:
        MACROS = dict(MACROS, SMU__NUM_MCLK_DPM_LEVELS=7,
                      SMU__NUM_SCLK_DPM_STATE=3, SMU__NUM_PCIE_DPM_LEVELS=5)
        despues = offsets_por_compilacion("smu7_discrete.h", "SMU7_SoftRegisters",
                                          campos)[0]
    finally:
        MACROS = guardado
    chk(VECTORES["V9"], antes == despues,
        "cambiar SMU__NUM_* movio los offsets:  antes %s  despues %s" % (antes, despues))
    return total[0], fallos


def campos_comunes():
    """Los campos que declara TODAS las copias, por el productor de parseo."""
    por = []
    for h, s in COPIAS:
        pp = campos_por_parseo(h, s)
        if not pp:
            return []
        por.append({n for n, _ in pp})
    if not por:
        return []
    return sorted(set.intersection(*por))


def _main_capturado(argv):
    """Ejecuta main() con la salida capturada  y  devuelve  (codigo, texto).

    MEDIDO 2026-10-06:  el aviso de reduccion por nombre  (  --todos  )  vive en
    main(),  y el selftest no llamaba a main().  Mutar  "if declarados > len(campos)"
    a  "if False"  dejaba el selftest EN VERDE.  O sea:  un vector  ("la reduccion
    no se hace en silencio")  que solo comprobaba una aritmetica interna  y  no  que
    el aviso se imprima.  Es el fallo de 1209 por tercera vez  y el segundo en este
    tool:  un check que pasa mientras el codigo que importa no se ejecuta.
    """
    import contextlib
    import io
    buf = io.StringIO()
    try:
        with contextlib.redirect_stdout(buf):
            codigo = main(argv)
    except Exception:                                   # noqa: BLE001
        return None, ""
    return codigo, buf.getvalue()


def main(argv):
    if "--selftest" in argv:
        total, fallos = selftest()
        for n, d in fallos:
            print("  FALLA %s   %s" % (n, d))
        print("  SELFTEST: %d de %d" % (total - len(fallos), total))
        return 1 if fallos else 0
    campos = ["DRAM_LOG_ADDR_H", "DRAM_LOG_ADDR_L", "DRAM_LOG_PHY_ADDR_H",
              "DRAM_LOG_PHY_ADDR_L", "DRAM_LOG_BUFF_SIZE"]
    if "--todos" in argv:
        campos = campos_comunes()
        if not campos:
            print("  no hay campos comunes:  el parseo no vio las seis copias")
            return 2
        #  LA REDUCCION POR NOMBRE,  HECHA VISIBLE.
        #
        #  MEDIDO 2026-10-06:  smu7_discrete.h  TRUNCA cinco nombres largos
        #  (PmTimerPeriod -> PmTimerP,  AverageGraphicsActivity ->
        #  AverageGraphicsA,  y otros tres).  Las cinco truncaciones caen en el
        #  MISMO offset  y la MISMA posicion,  asi que el layout es identico y solo
        #  cambian los identificadores.  PERO  el corte por nombre no lo ve:  la
        #  interseccion se queda con 30 campos  cuando la copia mas pequena
        #  declara 40.
        #
        #  Y eso es peligroso por una razon concreta:  los campos truncados  NO
        #  aparecen en la tabla,  asi que tampoco pueden marcarse como
        #  divergentes.  El informe decia "todos unicos"  sobre una pregunta mas
        #  pequena de la que el lector creia.  Eso no es un numero malo:  es una
        #  pregunta mas pequena que PARECE una respuesta.
        #
        #  Por eso el modo --todos imprime las dos cifras:  lo que se declaro  y
        #  lo que se pregunto.  Si no coinciden,  el lector tiene que saberlo
        #  antes de leer la tabla.
        declarados = min(len(campos_por_parseo(h, s) or []) for h, s in COPIAS)
        print("  (modo --todos)  declarados por la copia mas pequena: %d   "
              "preguntados por nombre: %d" % (declarados, len(campos)))
        if declarados > len(campos):
            print("  AVISO  la interseccion por NOMBRE deja fuera %d campos.  "
                  "No es que no divergan:  es que no seestan preguntando."
                  % (declarados - len(campos)))
            print("          la causa medida es que smu7_discrete.h trunca cinco "
                  "nombres largos.  Para comparar por POSICION hace falta otro modo.\n")
        else:
            print()
    if "--campos" in argv:
        i = argv.index("--campos")
        campos = [x for x in argv[i + 1].split(",") if x]
    probs = informe(campos)
    return 1 if probs else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))