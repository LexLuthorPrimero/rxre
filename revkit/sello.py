#!/usr/bin/env python3
"""
sello.py -- verifica el manifiesto de evidencia y lo mantiene al dia.

QUE ES ESTO
-----------
`docs/EVIDENCE-MANIFEST.sha256` sella 245 ficheros de los que depende
`docs/`. El proposito esta escrito en su primera linea: "la pregunta es si se
movio la EVIDENCIA". `docs/` NO se sella, precisamente porque se edita a
menudo; lo que no debe moverse sin querer es la evidencia.

Esta herramienta responde a tres preguntas distintas, que es donde suele
confundirse:

  1. ¿ALGUN fichero sello ya no esta?        -> ROTO
  2. ¿ALGUN fichero sello cambio?            -> MOVIDO
  3. ¿Hay evidencia NUEVA sin sellar?        -> SIN SELLAR

Las tres se contestan por separado porque significan cosas distintas. Un
fichero que falta y un fichero que cambio no se arreglan igual: el primero
puede ser un borrado, el segundo una edicion.

LO QUE ESTA FUERA DE ALCANCE, Y POR QUE
----------------------------------------
No decide si un cambio es legitimo. No puede: eso requiere saber si quien
lo escribo debia escribirlo. Lo que hace es DECIR QUE PASO, con la fecha y
el fichero, y no dejar que se entere por un documento que se contradiga
despues.

QUE NO HACE, Y ES LO IMPORTANTE
--------------------------------
No re-sella nada automaticamente. Volver a sellar un fichero que cambio sin
mirarlo convierte un detector de derivas en un detector de cambios: el
sello se actualiza y la perdida de historia desaparece.

Hay un `--actualizar` explicito, y escribe un fichero NUEVO, sin tocar el
anterior. Un sello que se sobrescribe a si mismo no recuerda nada.

TRES ESTADOS, Y POR QUE NO SE COLAPSAN EN UNO
---------------------------------------------
  OK        el fichero existe y su suma coincide
  MOVIDO    existe, pero la suma no coincide
  ROTO      no existe, o no se puede leer
  NUEVO     esta en el arbol, no estaba en el sello, y no es ruido

Un MOVIDO y un ROTO se distinguen porque el ROTO es el que obliga a
preguntarse si se perdio algo, y esa pregunta no se puede hacer despues si
todo se reduce a "el manifiesto no cuadra".
"""
import argparse
import datetime
import hashlib
import os
import sys

MANIFIESTO = "../docs/EVIDENCE-MANIFEST.sha256"

# Rutas cuyo cambio se espera y no es deriva. Se declaran de forma explicita
# y se pueden anadir, pero nunca se anaden a ciegas: cada una es una
# decision, y por eso esta en codigo y no en un parametro.
RUTAS_QUE_NO_SE_SELLAN = {
    ".git", "__pycache__", "node_modules",
    # el manifiesto mismo no se sella a si mismo
    "docs/EVIDENCE-MANIFEST.sha256",
    # artefactos de build
    "capturas",
}

# Extensiones que son datos binarios o ruido de build, no evidencia.
NO_EVIDENCIA_EXT = {
    ".o", ".ko", ".so", ".pyc", ".png", ".jpg", ".rgba", ".bin", ".spv",
    ".ninja_deps", ".modinfo",
}

# Ruido que se sabe que existe y que no es evidencia. Declarado, no
# deducido, para que la exclusion sea revisable.
RUIDO_CONOCIDO = {
    "research/working", "research/baseline", "research/kernelbuild",
    "rx550-upstream-7.2.8",
}


def sha256(path, bloque=1 << 20):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        while True:
            b = f.read(bloque)
            if not b:
                break
            h.update(b)
    return h.hexdigest()


def lee_manifiesto(ruta):
    """
    Devuelve [(sha_esperado, ruta_relativa), ...].

    Se ignoran las lineas de comentario y las vacias. Una linea malformada
    NO se descarta en silencio: es un dato sobre el manifiesto mismo.
    """
    entradas = []
    malformadas = []
    with open(ruta, errors="replace") as f:
        for i, ln in enumerate(f, 1):
            s = ln.strip()
            if not s or s.startswith("#"):
                continue
            partes = s.split(None, 1)
            if len(partes) != 2 or len(partes[0]) != 64:
                malformadas.append((i, s[:70]))
                continue
            entradas.append((partes[0], partes[1].strip()))
    return entradas, malformadas


def es_evidencia_candidata(ruta_rel):
    r = ruta_rel.lower()
    for ruido in RUIDO_CONOCIDO:
        if r.startswith(ruido + "/") or r == ruido:
            return False
    for no in RUTAS_QUE_NO_SE_SELLAN:
        if r == no.lower() or r.startswith(no.lower() + "/"):
            return False
    ext = os.path.splitext(r)[1].lower()
    if ext in NO_EVIDENCIA_EXT:
        return False
    return True


def main():
    ap = argparse.ArgumentParser(
        description="verifica el sello de evidencia")
    ap.add_argument("--raiz", default="..",
                    help="raiz del proyecto, relativo al script")
    ap.add_argument("--manifiesto", default=None)
    ap.add_argument("--nuevos", action="store_true",
                    help="lista tambien la evidencia sin sellar")
    ap.add_argument("--actualizar", default=None, metavar="FICHERO",
                    help="escribe un manifiesto NUEVO; no toca el anterior")
    a = ap.parse_args()

    aqui = os.path.dirname(os.path.abspath(__file__))
    # --raiz se resuelve DESDE EL SCRIPT, no desde el directorio de trabajo,
    # para que la herramienta sea componible y se pueda probar sobre un
    # arbol de mentira. Con rutas relativas al CWD, probarla sobre otro
    # arbol era imposible sin copiar el script.
    raiz = os.path.abspath(a.raiz) if os.path.isabs(a.raiz) else \
        os.path.abspath(os.path.join(aqui, a.raiz))
    # El manifiesto se busca en la raiz indicada, y si no esta, en docs/ de
    # esa raiz. Antes se resolvia siempre contra la raiz del script, con lo
    # que --raiz no servia para nada.
    if a.manifiesto:
        manifiesto = a.manifiesto
    else:
        manifiesto = os.path.join(raiz, "docs", "EVIDENCE-MANIFEST.sha256")
        if not os.path.exists(manifiesto):
            alt = os.path.join(raiz, "EVIDENCE-MANIFEST.sha256")
            if os.path.exists(alt):
                manifiesto = alt
    if not os.path.exists(manifiesto):
        print("no existe el manifiesto: %s" % manifiesto)
        return 2

    entradas, malformadas = lee_manifiesto(manifiesto)
    print("=" * 78)
    print("SELLO DE EVIDENCIA")
    print("=" * 78)
    print("manifiesto: %s" % manifiesto)
    print("entradas   : %d" % len(entradas))
    print("raiz       : %s" % raiz)
    print()

    ok = movidos = rotos = ilegibles = 0
    detalle_movidos = []
    detalle_roto = []
    for esperado, rel in entradas:
        p = os.path.join(raiz, rel)
        if not os.path.exists(p):
            rotos += 1
            detalle_roto.append((rel, "NO EXISTE"))
            continue
        try:
            got = sha256(p)
        except OSError as e:
            ilegibles += 1
            detalle_roto.append((rel, "ilegible: %s" % e))
            continue
        if got == esperado:
            ok += 1
        else:
            movidos += 1
            detalle_movidos.append((rel, esperado[:12], got[:12]))

    print("RESULTADO")
    print("  %-12s %d" % ("OK", ok))
    print("  %-12s %d" % ("MOVIDO", movidos))
    print("  %-12s %d" % ("ROTO", rotos))
    if ilegibles:
        print("  %-12s %d" % ("ILEGIBLE", ilegibles))
    print()

    if malformadas:
        print("LINEAS MALFORMADAS EN EL MANIFIESTO: %d" % len(malformadas))
        for i, s in malformadas[:5]:
            print("  linea %d: %r" % (i, s))
        print("  No se ignoran: un manifiesto con lineas rotas sella menos")
        print("  de lo que dice, y eso no se ve en el recuento.")
        print()

    if detalle_movidos:
        print("EVIDENCIA QUE SE MOVIO (%d):" % len(detalle_movidos))
        print("  %-64s %-14s %s" % ("fichero", "esperado", "obtenido"))
        for rel, esp, got in sorted(detalle_movidos):
            print("  %-64s %-14s %s" % (rel[:64], esp, got))
        print()
        print("  ESTO NO ES UN ERROR POR SÍ SOLO. Editar evidencia es")
        print("  legitimo si quien lo hace sabe lo que hace. Lo que no es")
        print("  legitimo es que no quede constancia.")
        print()

    if detalle_roto:
        print("EVIDENCIA ROTA (%d):" % len(detalle_roto))
        for rel, why in sorted(detalle_roto):
            print("  %-64s %s" % (rel[:64], why))
        print()
        print("  Esto es mas grave que MOVIDO: un fichero que no esta no se")
        print("  puede re-sellar, y el sello lo declaraba como evidencia.")
        print()

    # Evidencia nueva sin sellar
    nuevos = []
    if a.nuevos or a.actualizar:
        sellados = set(rel for _h, rel in entradas)
        for dp, dns, fns in os.walk(raiz):
            dns[:] = [d for d in dns if d not in (".git", "__pycache__",
                                                 "node_modules")]
            for fn in fns:
                p = os.path.join(dp, fn)
                rel = os.path.relpath(p, raiz)
                if rel in sellados:
                    continue
                if not es_evidencia_candidata(rel):
                    continue
                if not fn.endswith((".md", ".py", ".sh", ".c", ".h")):
                    continue
                nuevos.append(rel)
        if nuevos:
            print("EVIDENCIA SIN SELLAR: %d ficheros" % len(nuevos))
            for rel in sorted(nuevos)[:30]:
                print("  %s" % rel)
            if len(nuevos) > 30:
                print("  ... y %d mas" % (len(nuevos) - 30))
            print()

    # Actualizar: escribe un fichero NUEVO, nunca sobrescribe el anterior.
    if a.actualizar:
        if movidos or rotos:
            print()
            print("NO SE ESCRIBE EL SELLO NUEVO.")
            print()
            print("Hay %d ficheros MOVIDOS y %d ROTOS, y sellarlos ahora"
                  % (movidos, rotos))
            print("convertiria esto en un detector de cambios en vez de uno")
            print("de derivas: el sello se actualizaria y la perdida de")
            print("historia desapareceria.")
            print()
            print("Hay que decidir primero, fichero a fichero, si el cambio")
            print("es legitimo. Eso no lo puede hacer un script.")
            return 3
        with open(a.actualizar, "w") as f:
            f.write("# drift 1.0.0  -- sello de evidencia\n")
            f.write("# regenerado %s\n"
                    % datetime.datetime.now().isoformat(timespec="seconds"))
            f.write("# %d ficheros\n" % len(entradas))
            for esperado, rel in sorted(entradas, key=lambda x: x[1]):
                f.write("%s  %s\n" % (esperado, rel))
        print("Sello nuevo escrito en %s" % a.actualizar)
        print("El anterior NO se ha tocado.")
        return 0

    # Codigo de salida: distingue lo que obliga a preguntar de lo que no.
    if rotos:
        return 2
    if movidos:
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
