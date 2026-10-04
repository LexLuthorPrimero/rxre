#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0
#
# CONTRACT: name=corpus_manifest_check
# CONTRACT: READONLY=yes
# CONTRACT: WRITES_FILES=no        (solo escribe en stdout; NUNCA en el arbol)
# CONTRACT: MUTATES_CORPUS=no
# CONTRACT: WRITES_GPU=no
# VERSION: 1.0.0
"""
corpus_manifest_check -- comprueba el manifiesto de identidad del corpus.

QUE ES
    Dado el manifiesto 06-INGENIERIA-INVERSA/register-maps/
    corpus-amdgpu-sha256-linux-7.1.3.txt (sha256 de cada fichero del corpus
    linux-7.1.3 que CITA el componente de driver), comprueba cada entrada contra
    un arbol del disco y dice, POR SEPARADO:

        CUADAN      el fichero esta y su sha256 es el del manifiesto
        NO_CUADAN   el fichero esta y su sha256 es OTRO        <- FALLO RUIDOSO
        NO_SE_ENCUENTRA  el fichero no esta en el arbol         <- corpus incompleto

    Las tres son distintoes porque tienen distinto diagnóstico y distinto
    arreglo, y un contador único no puede separarlas.

POR QUE UN HASH QUE NO CUADDA ES UN FALLO Y NO UN AVISO
    El manifiesto es lo que permite afirmar, en otra maquina y sin el corpus,
    que un arbol de fuentes es ESTE corpus.  Si un hash no cuadra y la tool
    devuelve 0, esa afirmacion queda sin sustain: el consumidor que solo mira
    el exit status recibe un "todo bien" que es falso.  Por eso NO_CUADAN es
    codigo de salida 1 y no una linea de warning.

    Un mismatch en un fichero que el manifiesto marca instrumented=YES no se
    perdona: lo que se perdona es el codigo de salida SI y solo SI el manifiesto
    se esta comprobando contra un arbol que NO es el de referencia
    (--allow-instrumented, off por defecto).

    MEDIDO y por eso existe la opcion: working/ y baseline/ guardan la version
    OFICIAL de amdgpu_vm.c y amdgpu_vm_pt.c; solo kernelbuild tiene las
    instrumentadas.  Contra working/ esta tool da 38 CUADAN, 2 NO_CUADAN
    (los dos instrumented=YES) y 21 NO_SE_ENCUENTRA.  Los tres numeros son
    ciertos y los tres son diagnosis distintos.

POR QUE NO SE USA `sha256sum -c` PARA LEER EL RESULTADO
    MEDIDO en esta maquina: con LANG=es_AR.utf8, sha256sum imprime
    "La suma coincide" y "FAILED open or read" no aparece literally -- el
    mensaje esta traducido.  Parsear ese texto es parsear el idioma del
    operador.  Este script calcula los sha256 y compara bytes, y usa el exit
    status de sha256sum solo como control, nunca como parser.

QUE NO CONTIENE, POR CONSTRUCCION
    No decide si un fichero esta "instrumentado".  Eso ya esta MEDIDO y
    escrito en el manifiesto hermano corpus-amdgpu-instrumented-linux-7.1.3.txt.
    Aqui solo se comprueba que el disco dice lo que el manifiesto dice.

SOBRE EL USO CON OTROS ARBOLES
    working/ y baseline/ NO son extractos completos del kernel: MEDIDO, les
    faltan 21 de las 61 entradas del manifiesto (todas las cabeceras genericas
    include/linux/*.h y drivers/pci/*).  Comprobarlos dara NO_SE_ENCUENTRA, y
    eso es informacion correcta, no un fallo de la tool.

SALIDA
    TSV por entrada, y despues un resumen:
        ESTADO <TAB> RUTA <TAB> ESPERADO <TAB> VISTO
        RESUMEN <TAB> total <TAB> cuadran <TAB> no_cuadran <TAB> no_se_encuentra

CODIGO DE SALIDA (distinto del contenido, para que sea componible)
    0  todas las entradas existen y todos los hashes cuadran
    1  al menos una entrada NO CUADRA  (fallo ruidoso)
    2  ningun mismatch, pero al menos una entrada NO SE ENCUENTRA
    3  el manifiesto no se pudo usar (no existe, vacio, o linea mal formada)
    "hubo salida" nunca significa "todo bien": hay que leer el codigo.

USO
    tools/corpus_manifest_check.py [--tree DIR] [--manifest F]
                                   [--allow-instrumented] [--quiet]
"""
import argparse
import hashlib
import os
import sys

REPO = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                    "..", "..", ".."))
DEF_MANIFEST = os.path.join(REPO, "06-INGENIERIA-INVERSA", "register-maps",
                            "corpus-amdgpu-sha256-linux-7.1.3.txt")
DEF_SIDE = os.path.join(REPO, "06-INGENIERIA-INVERSA", "register-maps",
                        "corpus-amdgpu-instrumented-linux-7.1.3.txt")
DEF_TREE = os.path.join(REPO, "RESEARCH", "kernelbuild", "linux-7.1.3")

HEX = set("0123456789abcdef")


def sha256_of(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def parse_manifest(path):
    """Devuelve (entradas, instrumented) o lanza ValueError con el motivo.

    Formato, identico al de asic_reg-sha256-linux-7.1.3.txt:
        <sha64><2 espacios><ruta>
    Las lineas que empiezan por '#' son de provenance y se saltan.
    """
    if not os.path.isfile(path):
        raise ValueError("no existe el manifiesto: %s" % path)
    entries, seen, bad = [], {}, []
    with open(path, "r", encoding="utf-8", errors="replace") as f:
        for n, raw in enumerate(f, 1):
            line = raw.rstrip("\n").rstrip("\r")
            if not line.strip() or line.lstrip().startswith("#"):
                continue
            if len(line) < 67 or line[64:66] != "  ":
                bad.append((n, "no son 64 hex + 2 espacios + ruta", line[:80]))
                continue
            digest, rel = line[:64], line[66:]
            if not set(digest) <= HEX:
                bad.append((n, "el digest no es hexadecimal", line[:80]))
                continue
            if not rel or rel.startswith("/") or ".." in rel.split("/"):
                bad.append((n, "ruta vacia, absoluta o con '..'", rel[:80]))
                continue
            if rel in seen:
                bad.append((n, "ruta duplicada (ya estaba en la linea %d)" % seen[rel], rel[:80]))
                continue
            seen[rel] = n
            entries.append((rel, digest))
    if bad:
        raise ValueError("manifiesto mal formado: %d linea(s) -- %s"
                         % (len(bad), "; ".join("L%d: %s" % (b[0], b[1]) for b in bad[:5])))
    if not entries:
        raise ValueError("el manifiesto no tiene ninguna entrada de datos")
    return entries


def load_instrumented(path):
    """Mapa ruta -> (verdict, delta). El hermano es opcional: si no esta, no
    se inventa nada y se devuelve {} (--allow-instrumented no tendra efecto)."""
    out = {}
    if not path or not os.path.isfile(path):
        return out
    with open(path, "r", encoding="utf-8", errors="replace") as f:
        for raw in f:
            line = raw.rstrip("\n").rstrip("\r")
            if not line.strip() or line.lstrip().startswith("#"):
                continue
            parts = line.split("\t")
            if len(parts) < 3:
                continue
            out[parts[1]] = parts[2]
    return out


def main(argv):
    ap = argparse.ArgumentParser(add_help=True)
    ap.add_argument("--tree", default=DEF_TREE,
                    help="arbol del corpus a comprobar (def: kernelbuild)")
    ap.add_argument("--manifest", default=DEF_MANIFEST)
    ap.add_argument("--sidecar", default=DEF_SIDE,
                    help="manifiesto hermano con la columna instrumented (opcional)")
    ap.add_argument("--allow-instrumented", action="store_true",
                    help="NO_DOWNGRADE_MISMATCH: un mismatch en un fichero marcado "
                         "instrumented=YES pasa a exit 0. OFF por defecto: piense en "
                         "ello antes de activarlo.")
    ap.add_argument("--quiet", action="store_true")
    args = ap.parse_args(argv)

    try:
        entries = parse_manifest(args.manifest)
    except ValueError as e:
        sys.stderr.write("ERROR: %s\n" % e)
        return 3

    inst = load_instrumented(args.sidecar)
    if not os.path.isdir(args.tree):
        sys.stderr.write("ERROR: no existe el arbol: %s\n" % args.tree)
        return 3

    ok = mism = missing = 0
    excused = 0
    if not args.quiet:
        sys.stdout.write("ESTADO\tRUTA\tESPERADO\tVISTO\n")
    for rel, digest in entries:
        full = os.path.join(args.tree, rel)
        if os.path.islink(full) or not os.path.isfile(full):
            missing += 1
            if not args.quiet:
                sys.stdout.write("NO_SE_ENCUENTRA\t%s\t%s\t-\n" % (rel, digest))
            continue
        try:
            seen = sha256_of(full)
        except OSError as e:
            sys.stderr.write("ERROR: no se pudo leer %s: %s\n" % (full, e))
            return 3
        if seen == digest:
            ok += 1
            if not args.quiet:
                sys.stdout.write("CUADAN\t%s\t%s\t%s\n" % (rel, digest, seen))
            continue
        verdict = inst.get(rel, "NOT_DETERMINED")
        tag = "instrumented=%s" % verdict
        if verdict == "yes" and args.allow_instrumented:
            excused += 1
            tag += " (PERDONADO por --allow-instrumented: no cuenta como mismatch)"
        else:
            mism += 1
        if not args.quiet:
            sys.stdout.write("NO_CUADAN\t%s\t%s\t%s\t<- %s\n"
                             % (rel, digest, seen, tag))
    sys.stdout.write("RESUMEN\t%d\t%d\t%d\t%d\n"
                     % (len(entries), ok, mism, missing))
    if excused:
        sys.stdout.write("PERDONADOS\t%d\t(solo con --allow-instrumented)\n" % excused)
    if not inst:
        sys.stderr.write("AVISO: no se encontro el manifiesto hermano %s; "
                         "la columna instrumented queda NOT_DETERMINED.\n" % args.sidecar)

    if mism:
        return 1
    if missing:
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))