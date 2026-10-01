#!/usr/bin/env python3"
# CONTRACT: name=next_work
# CONTRACT: READONLY=yes
# CONTRACT: WRITES_FILES=no
# CONTRACT: WRITES_SYSFS=no
# CONTRACT: MUTATES_CORPUS=no
# CONTRACT: WRITES_GPU=no
r"""NEXT WORK -- que hay que hacer despues, deducido del estado del proyecto.

POR QUE EXISTE. La forma en que este proyecto ha funcionado es: una ronda,
encuentro un hueco, lo documento. Eso funciona mientras quien lee tenga el
contexto entero en la cabeza, y deja de funcionar en cuanto hay 14
herramientas, 41 hallazgos y tres sesiones escribiendo a la vez.

Una herramienta que responda "que hago ahora" tiene que mirar:

  1. QUE ESTA ABIERTO. Los NOT_DETERMINED de los hallazgos, agrupados por
     entidad. No todos valen igual: un NOT_DETERMINED que solo se cierra con
     hardware y otro que se cierra releyendo el codigo son trabajo distinto.

  2. QUE ESTA SIN MAPA. Las entidades del dominio con menos afirmaciones
     fuertes, segun causal_map.

  3. QUE ESTA SIN RESOLVER POR CONTRADICCION. Si el detector encuentra dos
     valores fuertes para el mismo sujeto, eso es trabajo INMEDIATO: resolverlo
     o descartarlo.

  4. QUE SE PUEDE AUTOMATIZAR AUN. Las entidades cuya evidencia se produce
     con una herramienta que ya existe pero no se ha corrido sobre ellas.

Y un quinto, el mas util de todos:

  5. QUE NO SE HA VISTO. Los registros y paquetes que el camino alcanza y que
     ningun hallazgo menciona. Ese es el borde nuevo: el codigo tiene N
     registros, y los documentos hablan de M de ellos. Los N-M son
     trabajo pendiente que nadie ha decidido todavia.

Uso:
  python3 next_work.py            ranking de trabajo pendiente
  python3 next_work.py --why ID   por que ese candidato
  python3 next_work.py --json
"""
import os
import re
import sys
import json
from collections import defaultdict

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

ROOT = ("/home/lucas/Escritorio/RX550-INVESTIGACION")
FIND = f"{ROOT}/06-INGENIERIA-INVERSA/findings"

# Coste de resolver cada clase de frontera. Es un juicio explicito, no un
# numero magico: lo que lo hace util es que ESTA DECLARADO y se puede
# discutir, no que sea preciso.
COSTE = {
    "hardware": 100,      # necesita medir la placa
    "lectura": 20,        # se cierra releyendo el codigo
    "automatizable": 5,   # hay herramienta, solo hay que correrla
    "contradiccion": 1,   # alguien tiene que decidir; es lo mas rapido
}

# Que registros ya menciona cada hallazgo. Se calcula del texto real, no de
# una lista a mano.
REG_RE = re.compile(r"\b(mm[A-Z][A-Z0-9_]{2,})\b")


def registros_mencionados():
    """{registro: documentos que lo mencionan}"""
    out = defaultdict(set)
    for f in sorted(os.listdir(FIND)):
        if not f.endswith(".md"):
            continue
        try:
            txt = open(os.path.join(FIND, f), errors="replace").read()
        except OSError:
            continue
        for m in REG_RE.finditer(txt):
            out[m.group(1)].add(f)
    return out


def not_determined():
    """[(doc, linea, texto)] de todo NOT_DETERMINED."""
    out = []
    for f in sorted(os.listdir(FIND)):
        if not f.endswith(".md"):
            continue
        try:
            lines = open(os.path.join(FIND, f), errors="replace").read().split("\n")
        except OSError:
            continue
        for i, l in enumerate(lines, 1):
            if "NOT_DETERMINED" in l or "NOT_OBSERVED" in l:
                out.append((f, i, l.strip()[:110]))
    return out


def candidatos():
    """Ranking de trabajo. Cada candidato tiene su por que."""
    cands = []

    # --- 1. contradicciones sin resolver: lo mas rapido de todo
    try:
        import causal_map as CM
        contras = CM.contradicciones(CM.build())
        for c in contras:
            cands.append(dict(
                tipo="contradiccion", coste=COSTE["contradiccion"],
                titulo=f"{c['sujeto']}: valores en conflicto",
                por_que="dos afirmaciones con estado fuerte sobre el mismo "
                        "sujeto. Resolverlo o descartarlo es trabajo de "
                        "minutos y desbloquea lo que dependa de el.",
                valores=[v for v, n, f in c["valores"]],
                detalle=f"{c['sujeto']} aparece con "
                        f"{len(c['valores'])} valores distintos"))
    except Exception as e:
        pass

    # --- 2. registros que el codigo alcanza y nadie ha mirado
    try:
        import causal_chain as CC
        idx, live, nodes, edges = CC.build(2)
        tocados = set(e["dst"] for e in edges
                      if e["tipo"] in ("REG_WRITE", "REG_READ"))
        mencionados = registros_mencionados()
        sin = sorted(tocados - set(mencionados))
        if sin:
            cands.append(dict(
                tipo="sin_ver", coste=COSTE["automatizable"] * 2,
                titulo=f"{len(sin)} registros que el camino alcanza y "
                       f"ningun hallazgo menciona",
                por_que="el codigo los toca y los documentos no los nombran. "
                        "O son irrelevantes y hay que decirlo, o son el "
                        "siguiente hallazgo. Decidir cual es trabajo de una "
                        "tarde automatizada.",
                registros=sin[:40],
                detalle=f"{len(sin)} de {len(tocados)} registros sin "
                        f"mencion documental"))
    except Exception:
        pass

    # --- 3. fronteras de hardware: caras pero unicas
    nd = not_determined()
    hw = [x for x in nd if re.search(r"hardware|RUNTIME|experimento",
                                     x[2], re.I)]
    if hw:
        cands.append(dict(
            tipo="hardware", coste=COSTE["hardware"],
            titulo=f"{len(hw)} fronteras que solo se cierran midiendo",
            por_que="estas NO se cierran leyendo codigo. Requieren un "
                    "experimento con autorizacion de escritura. Conviene "
                    "agruparlas: un solo experimento puede cerrar varias.",
            documentos=len(set(x[0] for x in hw)),
            detalle=", ".join(sorted(set(x[0] for x in hw))[:6])))

    # --- 4. fronteras de lectura: baratas
    rd = [x for x in nd if not re.search(r"hardware|RUNTIME|experimento",
                                         x[2], re.I)]
    if rd:
        cands.append(dict(
            tipo="lectura", coste=COSTE["lectura"],
            titulo=f"{len(rd)} fronteras que se cierran releyendo codigo",
            por_que="estas son las MAS BARATAS: no necesitan hardware, solo "
                    "mas lectura. Si el tiempo es el recurso escaso, aqui es "
                    "donde se rinde mas.",
            documentos=len(set(x[0] for x in rd)),
            detalle=", ".join(sorted(set(x[0] for x in rd))[:6])))

    return sorted(cands, key=lambda c: c["coste"])


def main():
    args = sys.argv[1:]
    c = candidatos()
    if "--json" in args:
        print(json.dumps(c, indent=1, default=str))
        return 0

    print("=" * 76)
    print("NEXT WORK -- trabajo pendiente, deducido del estado del proyecto")
    print("=" * 76)
    print(f"candidatos: {len(c)}   (ordenados por coste estimado)")
    print()
    for i, x in enumerate(c):
        print(f"[{i}] {x['titulo']}")
        print(f"    tipo={x['tipo']}  coste~{x['coste']}")
        print(f"    por que: {x['por_que']}")
        if x.get("detalle"):
            print(f"    detalle: {x['detalle']}")
        if x.get("valores"):
            print(f"    valores: {x['valores']}")
        print()

    if "--why" in args:
        i = int(args[args.index("--why") + 1])
        if 0 <= i < len(c):
            print(json.dumps(c[i], indent=1, default=str))

    print("-" * 76)
    print("LIMITE: los costes son JUICIOS mios, no medidas. Lo que hace util")
    print("el ranking es que estan DECLARADOS y se pueden discutir. Un")
    print("coste de 20 no significa que lleve 20 minutos.")
    print()
    print("Y esta herramienta NO decide cual hacer. Decide cual es el mas")
    print("barato de empezar, que no es lo mismo.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())