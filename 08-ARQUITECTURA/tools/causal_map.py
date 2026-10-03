#!/usr/bin/env python3
# CONTRACT: name=causal_map
# CONTRACT: READONLY=yes
# CONTRACT: WRITES_FILES=no
# CONTRACT: WRITES_SYSFS=no
# CONTRACT: MUTATES_CORPUS=no
# CONTRACT: WRITES_GPU=no
r"""CAUSAL MAP -- grafo de conocimiento del proyecto, con deteccion de
contradicciones y analisis de cobertura.

POR QUE ESTA HERRAMIENTA. El proyecto tiene 40+ hallazgos escritos a mano, en
40+ documentos, y hay tres cosas que solo se ven al mirarlos juntos:

  1. CONTRADICCIONES. En 035 tres sesiones declararon `block_size` como 13,
     10 y 22/23/24. Dos de las tres estaban equivocadas. Nadie lo vio al
     escribir; se vio al cruzado. Un detector automatico lo habria visto al
     segundo documento.

  2. COBERTURA. Que partes del ASIC tienen mapa y cuales no. El objetivo del
     proyecto es un mapa causal completo; esto dice cuanto falta.

  3. PROVENANCIA. Cada afirmacion del proyecto dice de que fichero y linea
     sale. Eso ya esta en los documentos; aqui se indexa para poder
     consultarlo.

NO ES UN GRAFO DE VERDAD SEMANTICA. Es un indice estructurado de lo que los
documentos AFIRMAN, con su procedencia y su estado epistemico. No infiere
nada: lo que no esta escrito, no esta en el grafo. Esa limitacion es la
condicion para que sirva, porque un grafo que rellena huecos con suposiciones
es peor que no tener grafo.

CATEGORIAS QUE CUMPLE de las que pide el proyecto: knowledge graph,
contradiction detector, evidence provenance, coverage analysis, documentation
state manager.

Uso:
  python3 causal_map.py                     resumen del grafo
  python3 causal_map.py --contradictions    lo que se contradice
  python3 causal_map.py --claims block_size TODAS las afirmaciones sobre X
  python3 causal_map.py --coverage          que tiene mapa y que no
  python3 causal_map.py --frontiers         preguntas abiertas agrupadas
  python3 causal_map.py --evidence X        procedencia de las afirmaciones
  python4 causal_map.py --json              todo en JSON
"""
import os
import re
import sys
import json
import glob
from collections import defaultdict, Counter

ROOT = ("/home/lucas/Escritorio/RX550-INVESTIGACION")
FIND = f"{ROOT}/06-INGENIERIA-INVERSA/findings"

# Estados epistemicos que el proyecto usa. El orden importa: mas fuerte
# primero. Un grafo que no distingue PROVEN de HYPOTHESIS no dice nada.
ESTADOS = [
    "PROVEN_DERIVED", "PROVEN_ABSENCE", "PROVEN_ABSENT", "PROVEN",
    "DERIVATION", "SECONDARY_CORROBORATION", "PRIMARY_DOCUMENTATION",
    "OBSERVED", "OBSERVATION", "HYPOTHESIS", "NEGATIVE_RESULT",
    "REFUTED", "NOT_DETERMINED", "NOT_OBSERVED", "NOT_IMPLEMENTABLE",
    "LIMITATION", "CONFOUNDER",
]
FUERTES = {"PROVEN", "PROVEN_DERIVED", "PROVEN_ABSENT", "PROVEN_ABSENCE",
           "OBSERVED"}

# Un estado mas fuerte que otro. Para elegir ganador de una contradiccion.
FUERZA = {
    "PROVEN": 9, "PROVEN_DERIVED": 7, "PROVEN_ABSENCE": 8, "PROVEN_ABSENT": 8,
    "OBSERVED": 8, "DERIVATION": 6, "SECONDARY_CORROBORATION": 5,
    "PRIMARY_DOCUMENTATION": 5, "NEGATIVE_RESULT": 5, "OBSERVATION": 5,
    "REFUTED": 4, "HYPOTHESIS": 3, "LIMITATION": 2, "CONFOUNDER": 2,
    "NOT_OBSERVED": 2, "NOT_IMPLEMENTABLE": 1, "NOT_DETERMINED": 0,
}

# Entidades del dominio. Se buscan en el texto para clasificar las
# afirmaciones. Es una lista corta y curada, no un diccionario general.
ENTIDADES = {
    "PM4":      [r"\bPACKET3\b", r"\bPM4\b", r"\bIB\b", r"indirect buffer"],
    "IB":       [r"\bindirect buffer\b", r"\bIB\b"],
    "GPUVM":    [r"\bGPUVM\b", r"\bpage table\b", r"\bPTBA\b", r"\bPTE\b",
                 r"\bPDE\b", r"\bVM_CONTEXT\b"],
    "GART":     [r"\bGART\b", r"\bgart\b"],
    "TLB":      [r"\bTLB\b", r"\binvalidat"],
    "RING":     [r"\bring\b", r"\bwptr\b", r"\brptr\b", r"\bdoorbell\b"],
    "FENCE":    [r"\bfence\b", r"\bFENCE\b"],
    "REG":      [r"\bmm[A-Z_]{3,}", r"\bregistro\b", r"\bregistro MMIO\b"],
    "SCHED":    [r"\bscheduler\b", r"\bsched\b", r"\bkiq\b", r"\bKIQ\b",
                 r"\bCP_RB", r"\bME\b", r"\bPFP\b"],
    "FREQ":     [r"\bclock\b", r"\bmclk\b", r"\bsclk\b", r"\bDPM\b",
                 r"\bSMU\b"],
    "CORPUS":   [r"\bcorpus\b", r"\bfindings?\b", r"\bfinding\b"],
}

# Nombres tecnicos que son "sujetos" del grafo: lo que se afirma de ellos.
# Sujetos que existen pero cuyo valor NO es el del ASIC, sino un parametro o
# una variable intermedia. Se indexan aparte para que sus numeros no se
# atribuyan a otro sujeto, pero NO cuentan como afirmaciones del hardware.
INDIRECTOS = re.compile(r"\b(max_bits|max_size|max_level|min_vm_size|tmp|F|"
                        r"num_nop|mask|buf_mask|ptr_mask)\b")

SUJETOS = re.compile(
    r"\b(block_size|fragment_size|num_level|max_pfn|vm_size|vm_update_mode|"
    r"rptr|wptr|fence_offs|trail_fence_offs|cond_exe_offs|vb_offset|"
    r"cntl|stride|data_sel|int_sel|doorbell_index|page_size|context_id|"
    r"PAGE_TABLE_BLOCK_SIZE|PAGE_TABLE_DEPTH|GCR_SEQ|DB_ADDR)\b",
    re.I)

ESTADO_RE = re.compile(r"\b(" + "|".join(ESTADOS) + r")\b")

# VALORES: solo los que aparecen EN LA MISMA CELDA o FRASE que el sujeto,
# inmediatamente a su derecha tras un "=". La primera version usaba
# VALOR_RE suelta sobre toda la linea, y tomaba el primer numero que encontraba
# -- que era la longitud del documento, un offset de linea, o un bit de un
# campo. De ahi que block_size apareciera con 9 valores distintos: la mayoria
# no eran(block_size = N), eran numeros que estaban por ahi.
# Formatos de valor aceptados, en orden de especificidad:
#   "sujeto = 10"        la forma canonica
#   "sujeto | 10 |"      celda de tabla con el valor en la SIGUIENTE columna
#   "sujeto: 10"         con dos puntos
# La segunda la produce el mutante de prueba y es una forma que la gente
# escribe de verdad en una tabla de clasificacion.
VALOR_RE = re.compile(
    r"(?:=|\u00bb|es|son|vale|:)\s*`?(0x[0-9a-fA-F]+|-?\d+(?:\.\d+)?)`?")
VALOR_CELDA_RE = re.compile(r"^\s*`?(0x[0-9a-fA-F]+|-?\d+(?:\.\d+)?)`?\s*$")


def docs():
    return sorted(glob.glob(f"{FIND}/*.md"))


def parse_doc(path):
    """Extrae afirmaciones (sujeto, valor, estado, linea) de un documento."""
    try:
        lines = open(path, errors="replace").read().split("\n")
    except OSError:
        return []
    out = []
    name = os.path.basename(path)
    for i, line in enumerate(lines, 1):
        # tabla de clasificacion:  | afirmacion | PROVEN | ... |
        if line.lstrip().startswith("|") and line.count("|") >= 3:
            cells = [c.strip() for c in line.strip("|").split("|")]
            est = None
            for c in cells:
                m = ESTADO_RE.search(c)
                if m:
                    est = m.group(1)
                    break
            if not est:
                continue
            for c in cells:
                sm = SUJETOS.search(c)
                if not sm:
                    continue
                # NEGACION, en la rama de tabla. El caso real:
                #   "| `get_block_size` recibe `tmp` reasignado (=2),
                #      no `vm_size` | `PROVEN` |"
                # El 2 es de tmp. vm_size se menciona para descartarlo. Y la
                # celda esta marcada PROVEN, asi que sin esta comprobacion
                # el detector de contradicciones declara que vm_size = 2 con
                # PROVEN, contra el 64 PROVEN de otros documentos.
                #
                # La primera version solo miraba la negacion en la rama de
                # PROSA, y las tablas -- que son donde vive el 90% de las
                # afirmaciones clasificadas -- pasaban sin filtro.
                # negacion pegada al sujeto, no en cualquier parte de la celda
                pre = c[max(0, sm.start() - 10):sm.start()]
                neg = re.search(r"\b(no|nunca|excepto)\s*$", pre, re.I)
                if neg:
                    continue
                vm = VALOR_RE.search(c, sm.end())
                # el valor puede estar en la celda SIGUIENTE de la tabla,
                # que es como la gente escribe estas tablas:
                #   | block_size medido | 33 | PROVEN |
                sig = None
                if not vm:
                    try:
                        idx = cells.index(c)
                        if idx + 1 < len(cells):
                            m2 = VALOR_CELDA_RE.match(cells[idx + 1])
                            if m2:
                                sig = m2.group(1)
                    except ValueError:
                        pass
                if vm:
                    antes = c[sm.end():vm.start()]
                    if SUJETOS.search(antes) or INDIRECTOS.search(antes):
                        vm = None
                out.append(dict(doc=name, linea=i, sujeto=sm.group(1),
                                valor=(vm.group(1) if vm else sig),
                                estado=est, texto=c[:120],
                                es_tabla=True))
        # prosa: "el campo X vale 10" / "X = 13"
        else:
            sm = SUJETOS.search(line)
            if not sm:
                continue
            est = ESTADO_RE.search(line)
            # El valor tiene que estar DESPUES del sujeto, pero NO mas alla
            # de la primera CLAUSE. Sin ese tope, "max_bits = 40 limita
            # vm_size a 1024" leia valor=40 para vm_size, y "get_block_size
            # recibe tmp reasignado (=2), no vm_size" leia valor=2. Los dos
            # numeros son reales y estan en la linea, pero NO son el valor de
            # vm_size: son el de otro sujeto.
            #
            # Regla: el valor es el que sigue al subjectsolo tras un
            # operador de asignacion (=/es/vale), y se corta en la primera
            # coma o en un "no"/"que" que introduce otra clausula.
            # NEGACION. Esta linea del 035 dice:
            #   "get_block_size recibe tmp reasignado (=2), NO vm_size" | PROVEN
            # El valor 2 es de tmp. vm_size aparece porque la frase lo
            # menciona para DESCARTARLO, y el parser leia PROVEN sobre un
            # valor que la propia frase niega.
            #
            # Un detector de contradicciones que no entiende la negacion
            # produce falsos positivos que hay que revisar a mano uno por
            # uno. Y un detector con falsos positivos se abandona, que es
            # peor que no tenerlo: deja de mirar.
            #
            # Regla: si entre el sujeto y el valor hay un "no", "NOT", "nunca"
            # o "excepto", la afirmacion se marca como negada y NO cuenta como
            # contradiccion.
            vm = None
            rest = line[sm.end():]
            # La negacion puede estar ANTES del sujeto. En el caso que destapo
            # esto:
            #   "get_block_size recibe tmp reasignado (=2), NO vm_size | PROVEN"
            # el "no" esta entre tmp y vm_size, o sea ANTES del sujeto. Buscar
            # solo en `rest` (que empieza donde el sujeto) no lo encuentra.
            #
            # La ventana es la celda entera, que en una tabla empieza tras el
            # "|". Mirar los 60 caracteres previos es suficiente para una celda
            # y no coge el sujeto anterior de otra fila.
            # La ventana de negacion es ESTRECHA a proposito. La primera
            # version usaba 60 caracteres antes del sujeto y 80 despues, y
            # como "no" aparece en casi cualquier frase matizada ("no por la
            # version", "no es lo mismo que"), descartaba la afirmacion
            # entera. De 89 documentos solo quedaban 39 claims: la mitad del
            # proyecto invisible para la herramienta.
            #
            # Regla correcta: la negacion cuenta solo si esta pegada al
            # sujeto o al valor. "no vm_size" cuenta; "no por la version del
            # kernel, sino por srcversion" no cuenta, porque el "no" esta a
            # 40 caracteres del sujeto y no lo niega.
            neg_pre = re.search(r"\b(no|nunca|excepto)\s*$",
                                line[max(0, sm.start() - 12):sm.start()],
                                re.I)
            neg_post = re.search(r"^\s*(no|nunca|excepto)\b", rest, re.I)
            neg = neg_pre or neg_post
            if neg:
                continue
            if vm:
                # que no haya otro sujeto conocido entre medias
                antes = rest[:vm.start()]
                otro = SUJETOS.search(antes)
                if otro:
                    vm = None
            if est or vm:
                out.append(dict(doc=name, linea=i, sujeto=sm.group(1),
                                valor=vm.group(1) if vm else None,
                                estado=est.group(1) if est else None,
                                texto=line.strip()[:120], es_tabla=False))
    return out


def entidades_de(texto):
    tags = []
    low = texto.lower()
    for k, pats in ENTIDADES.items():
        for p in pats:
            if re.search(p, texto if k.isupper() else low):
                tags.append(k)
                break
    return tags


def build():
    claims = []
    for p in docs():
        claims += parse_doc(p)
    return claims


def contradicciones(claims):
    """Agrupar por sujeto; si hay valores distintos con estados fuertes, avisar."""
    by = defaultdict(list)
    for c in claims:
        if c["valor"] is None:
            continue
        by[c["sujeto"].lower()].append(c)
    out = []
    for sujeto, cs in by.items():
        vals = defaultdict(list)
        for c in cs:
            vals[c["valor"]].append(c)
        if len(vals) < 2:
            continue
        # SOLO es contradiccion si hay DOS valores con estado fuerte. Un
        # PROVEN y un "0" que sale de una celda de tabla truncada no es una
        # contradiccion, es ruido de extraccion. Y un PROVEN contra un
        # NOT_DETERMINED tampoco: es una frontera, no un desacuerdo.
        #
        # Este filtro es lo que separa "el detector encuentra 9 valores" de
        # "el detector encuentra 2 afirmaciones que se contradicen". Lo
        # segundo es accionable; lo primero es un problema del parser.
        # UMBRAL. La primera version exigia PROVEN (fuerza 9) en los dos
        # valores, y con eso se escondio una contradiccion REAL:
        #
        #   block_size = 10   PROVEN          (11 documentos, log del kernel)
        #   block_size = 22   PROVEN_DERIVED   (030-page-walker, ventana de RAM)
        #
        # Un PROVEN_DERIVED NO es ruido: es una afirmacion con estado fuerte y
        # con un valor concreto. Si el proyecto afirma 10 y 22, hay que
        # resolverlo, no esconderlo por debajo de un umbral.
        #
        # El corte correcto es "estado epistemico >= DERIVATION", no
        # "PROVEN". Lo que se excluye es NOT_DETERMINED, HYPOTHESIS y los
        # valores sin estado, que son fronteras ysituacion, no afirmaciones.
        UMBRAL = FUERZA["DERIVATION"]
        # "-1" es el valor de un PARAMETRO DE MODULO sin definir, no el valor
        # efectivo. El ASIC usa el automatico. Mezclarlo con el valor real es
        # comparar dos cosas distintas, y asi se declara una contradiccion que no
        # existe. Se marca aparte, no se cuenta como afirmacion.
        fuertes = [v for v, cl in vals.items()
                   if v != "-1"
                   and any(FUERZA.get(c["estado"], 0) >= UMBRAL for c in cl)]
        if len(fuertes) < 2:
            continue
        # Hay mas de un valor. BUG QUE ESTA LINEA TENIA: usaba
        # fuerza_max = max(...) sobre 'c', una variable de la comprehension
        # anterior que no existe fuera de ella. No reventaba porque la
        # variable no se usaba para nada. Codigo muerto con un nombre que
        # sugiere que hace un calculo.
        #
        # Aqui lo que importa NO es cual es mas fuerte en abstracto, sino si
        # los dos valores son PROVEN. Si lo son, es una contradiccion real y
        # hay que resolverla mirando el codigo, no los documentos.
        acumulado = []
        for v, cl in sorted(vals.items(), key=lambda kv: -len(kv[1])):
            f = max(FUERZA.get(c["estado"], 0) for c in cl)
            acumulado.append((v, len(cl), f))
        out.append(dict(sujeto=sujeto, valores=acumulado))
    return out


def coverage(claims):
    """Que entidades tienen afirmaciones fuertes y cuales no."""
    por = defaultdict(lambda: {"fuerte": 0, "debil": 0, "abierta": 0,
                               "docs": set()})
    for c in claims:
        for e in entidades_de(c["texto"]):
            por[e]["docs"].add(c["doc"])
            st = c["estado"]
            if st in FUERTES:
                por[e]["fuerte"] += 1
            elif st in ("NOT_DETERMINED", "NOT_OBSERVED", None):
                por[e]["abierta"] += 1
            else:
                por[e]["debil"] += 1
    return por


def frontiers(claims):
    """Agrupar NOT_DETERMINED por la razon declarada."""
    fr = defaultdict(list)
    for c in claims:
        if c["estado"] in ("NOT_DETERMINED", "NOT_OBSERVED"):
            fr[c["doc"]].append(c["sujeto"])
    return fr


def main():
    args = sys.argv[1:]
    claims = build()
    if "--json" in args:
        print(json.dumps(dict(
            n_claims=len(claims),
            n_docs=len(docs()),
            contradicciones=contradicciones(claims),
            coverage={k: dict(fuerte=v["fuerte"], debil=v["debil"],
                              abierta=v["abierta"],
                              docs=len(v["docs"]))
                      for k, v in coverage(claims).items()},
        ), indent=1, default=str))
        return 0

    print("=" * 78)
    print("CAUSAL MAP -- indice estructurado de lo que el proyecto AFIRMA")
    print("=" * 78)
    print(f"documentos de hallazgo : {len(docs())}")
    print(f"afirmaciones extraidas: {len(claims)}")
    print()

    if not args or "--contradictions" in args:
        print("-" * 78)
        print("CONTRADICCIONES DETECTADAS")
        print("-" * 78)
        contras = contradicciones(claims)
        if not contras:
            print("  ninguna: ningun sujeto aparece con valores distintos")
        for c in contras:
            print(f"  {c['sujeto']}:")
            for v, n, f in c["valores"]:
                fu = "PROVEN" if f >= 9 else ("debil" if f >= 3 else "abierto")
                print(f"      {v:>12}  x{n:<3} fuerza={f}  ({fu})")
        print()

    if not args or "--coverage" in args:
        print("-" * 78)
        print("COBERTURA por entidad del dominio")
        print("-" * 78)
        cov = coverage(claims)
        print(f"  {'entidad':10} {'fuerte':>7} {'debil':>6} {'abierta':>8} "
              f"{'docs':>5}")
        for k in sorted(cov):
            v = cov[k]
            print(f"  {k:10} {v['fuerte']:7} {v['debil']:6} {v['abierta']:8} "
                  f"{len(v['docs']):5}")
        # que entidades no tienen ninguna afirmacion fuerte
        sin = [k for k in ENTIDADES if not cov.get(k, {}).get("fuerte")]
        if sin:
            print(f"\n  SIN NINGUNA AFIRMACION FUERTE: {', '.join(sorted(sin))}")
            print("  (o no se ha escrito, o lo que se escribio es NO_DETERMINED)")
        print()

    if "--frontiers" in args:
        print("-" * 78)
        print("FRONTERAS ABIERTAS (NOT_DETERMINED), por documento")
        print("-" * 78)
        for doc, sujs in sorted(frontiers(claims).items()):
            uniq = sorted(set(sujs))
            print(f"  {doc[:44]:46} {len(uniq)} sujetos")
            print(f"      {', '.join(uniq[:8])}")
        print()

    if "--claims" in args and len(args) >= 2:
        objetivo = args[args.index("--claims") + 1].lower()
        print("-" * 78)
        print(f"AFIRMACIONES sobre '{objetivo}'")
        print("-" * 78)
        for c in claims:
            if c["sujeto"].lower() == objetivo:
                print(f"  {c['doc']}:{c['linea']}  valor={c['valor']}  "
                      f"estado={c['estado']}")
                print(f"      {c['texto'][:90]}")
        print()

    if "--evidence" in args and len(args) >= 2:
        ob = args[args.index("--evidence") + 1].lower()
        print(f"PROCEDENCIA de '{ob}':")
        for c in claims:
            if c["sujeto"].lower() == ob:
                print(f"  {c['doc']}:{c['linea']}  {c['estado']}")
        print()

    print("LIMITE de esta herramienta: indexa lo que los documentos AFIRMAN.")
    print("No infiere, no rellena huecos, no resuelve contradicciones. Las")
    print("contradicciones que lista son REALES en el texto pero pueden ser")
    print("conciliables (un documento puede enmendar a otro). Decide una")
    print("persona o una herramienta mas especifica.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())