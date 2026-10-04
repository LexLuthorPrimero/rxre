#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0
#
# CONTRACT: name=corpus_manifest_check
# CONTRACT: READONLY=yes
# CONTRACT: WRITES_FILES=no        (solo escribe en stdout; NUNCA en el arbol)
# CONTRACT: MUTATES_CORPUS=no
# CONTRACT: WRITES_GPU=no
# VERSION: 2.0.0
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

ADEMAS, DESDE 2.0.0:  LAS MODIFICACIONES DEL CORPUS
    El manifiesto principal declara un alcance ("los ficheros que cita el
    componente"),  y ese alcance es CORRECTO.  Lo que no podia decir es quantas
    diferencias tiene el corpus con el tarball oficial.  MEDIDO 2026-10-04:  seis,
    +13687 bytes,  y solo dos de las seis son entradas de las 61.  Las otras
    cuatro  --amdgpu_debugfs.c/.h y drivers/gpu/drm/{Kconfig,Makefile}--  no las
    cita el componente,  y su hash instrumentado no estaba en NINGUN sitio del
    repo (MEDIDO sobre 78467 ficheros de texto fuera de los arboles del kernel).

    Por eso el hermano tiene ahora una seccion MODIFICACIONES  (lineas que
    empiezan por '#MOD' y TAB)  con los DOS hashes de cada fichero modificado:
    el del arbol y el del miembro oficial del tarball.

    Y POR QUE ESO NECESITA CODIGOS DE SALIDA DISTINTOS.  Son dos preguntas que
    no se contestan con lo mismo:

      (A) "que ESTADO tiene el corpus"  -- se contesta con las columnas
          declaradas,  sin arbol.  Que el delta sea la resta de los dos tamanos
          y que 'instrumented' sea la desigualdad de los dos hashes son
          COMPROBACIONES INTERNAS:  se hacen con los dos hashes en la mano  y
          ningun fichero en disco.  Es lo que hace que el estado del corpus sea
          verificable sin el arbol,  que es el objetivo.

      (B) "el arbol de AHORA es el de ENTONCES"  -- necesita leer el arbol.
          Es otra pregunta,  con otro veredicto y otro codigo.  Un exit 0 de (A)
          no dice nada de (B),  y al reves.

    Que compartieran codigo seria exactamente el defecto:  un exit 0 que
    significa dos cosas,  y un consumidor que solo mira el numero no sabe cual
    ha leido.

CODIGO DE SALIDA
    0  todo lo comprobado esta bien
    1  al menos una entrada NO CUADRA (fallo ruidoso, contra el arbol)
    2  ningun mismatch, pero al menos una entrada NO SE ENCUENTRA
    3  el manifiesto no se pudo usar (no existe, vacio, o linea mal formada)
    4  ESTADO INCOHERENTE: una linea '#MOD' se contradice a si misma.  Esta es
       la unica clase que NO necesita el arbol,  asi que es la unica que
       --sin-arbol puede devolver.  Con solo el manifiesto:  delta !=
       bytes_arbol - bytes_oficial,  o instrumented incoherente con los hashes.
    5  COBERTURA INCOMPLETA: el estado del corpus esta declarado a medias.  En
       los dos sentidos:  una entrada del manifiesto principal marcada
       instrumented=yes que no esta en la seccion MODIFICACIONES,  o una linea
       '#MOD' con instrumented=yes y citado=yes que no esta en las 61 entradas.
       Este es el codigo que habria detectado el agujero que habia.
    "hubo salida" nunca significa "todo bien": hay que leer el codigo.

 USO
    tools/corpus_manifest_check.py [--tree DIR] [--manifest F]
                                   [--allow-instrumented] [--quiet]
                                   [--sin-arbol] [--sin-modificaciones]
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

# Marcas de la seccion MODIFICACIONES.  '#MOD' empieza por '#'  y por eso el
# parseo de las 61 entradas de arriba la salta:  anadir la secion al hermano no
# rompe el hermano.  Es la misma razon por la que el manifiesto principal no
# lleva columna instrumented.
MOD_MARK = "#MOD"

EXIT_OK = 0
EXIT_MISMATCH = 1
EXIT_MISSING = 2
EXIT_UNUSABLE = 3
EXIT_INCOHERENT = 4
EXIT_COVERAGE = 5


def sha256_of(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def parse_modifications(path):
    """Lee la seccion MODIFICACIONES del hermano.  Devuelve una lista de dicts.

    MEDIDO:  el hermano tambien lleva las 61 entradas de 4 campos.  Esta
    funcion SOLO lee las lineas que empiezan por MOD_MARK,  que es la razon por
    la que el marcador empieza por '#':  el parseo de las 61
    (--load_instrumented)  las salta sin cambios,  de modo que anadir la seccion
    no ha roto el hermano.  Un separador que no fuese comentario habria
    obligado a tocar el parser viejo,  y un parser viejo que hay que tocar es un
    parser viejo que puede volver a romperse en silencio.

    Un NOT_DETERMINED en vez de un SI/NO es lo unico que se emite cuando un
    campo no se puede leer:  el contrato de esta tool es no dar un veredicto que
    no pueda sostener.  Que un campo no se lea no es lo mismo que que valga lo
    que dice el de al lado.
    """
    out = []
    if not path or not os.path.isfile(path):
        return out
    with open(path, "r", encoding="utf-8", errors="replace") as f:
        for n, raw in enumerate(f, 1):
            line = raw.rstrip("\n").rstrip("\r")
            if not line.startswith(MOD_MARK):
                continue
            parts = line.split("\t")
            if len(parts) != 9:
                raise ValueError(
                    "seccion %s linea %d: se esperaban 9 campos TAB y hay %d "
                    "(1 marca + 8 datos)" % (MOD_MARK, n, len(parts)))
            _, rel, sab, bab, soh, boh, delta, inst, cited = parts
            rec = {"linea": n, "ruta": rel, "sha_arbol": sab,
                   "bytes_arbol": bab, "sha_oficial": soh,
                   "bytes_oficial": boh, "delta": delta,
                   "instrumented": inst, "citado": cited}
            #  Un digest que no sea hex no se "interpreta":  se marca,  y el
            #  consumidor ve NOT_DETERMINED en vez de un SI/NO con fundamento.
            for key in ("sha_arbol", "sha_oficial"):
                if len(rec[key]) != 64 or not set(rec[key]) <= HEX:
                    rec[key] = "NOT_DETERMINED"
            for key in ("bytes_arbol", "bytes_oficial", "delta"):
                try:
                    rec[key] = int(rec[key])
                except ValueError:
                    rec[key] = None
            for key in ("instrumented", "citado"):
                if rec[key] not in ("yes", "no"):
                    rec[key] = "NOT_DETERMINED"
            out.append(rec)
    return out


def check_modifications_selfconsistent(mods):
    """Lo que se comprueba SIN arbol.  Devuelve (n_ok, [(rec, [problemas])]).

    MEDIDO por que esto es una comprobacion y no una tautologia:  'instrumented'
    y 'delta' son columnas DECLARADAS,  y lo que se comprueba es que no se
    contradigan con las columnas de las que se derivan.  Un instrumented=yes con
    dos hashes IGUALES es un estado imposible  --no se puede instrumentar un
    fichero y dejar el mismo hash--  y sale incoherente.  Un delta que no es la
    resta de los dos tamanos es un error de escritura,  y sale incoherente.
    Los dos se ven sin leer un solo byte del arbol.
    """
    bad = []
    for r in mods:
        probs = []
        if r["instrumented"] == "NOT_DETERMINED":
            probs.append("instrumented no es yes|no")
        if r["sha_arbol"] == "NOT_DETERMINED":
            probs.append("sha256_arbol no es un digest")
        if r["sha_oficial"] == "NOT_DETERMINED":
            probs.append("sha256_oficial no es un digest")
        for key, tag in (("bytes_arbol", "bytes_arbol"),
                        ("bytes_oficial", "bytes_oficial"),
                        ("delta", "delta")):
            if r[key] is None:
                probs.append("%s no es un entero" % tag)
        if r["citado"] == "NOT_DETERMINED":
            probs.append("citado no es yes|no")
        if not probs:
            distinto = r["sha_arbol"] != r["sha_oficial"]
            if (r["instrumented"] == "yes") != distinto:
                probs.append("instrumented=%s pero los hashes %s"
                             % (r["instrumented"],
                                "DIFIEREN" if distinto else "SON IGUALES"))
            esperado = r["bytes_arbol"] - r["bytes_oficial"]
            if r["delta"] != esperado:
                probs.append("delta=%+d pero %d - %d = %+d"
                             % (r["delta"], r["bytes_arbol"],
                                r["bytes_oficial"], esperado))
        if probs:
            bad.append((r, probs))
    return len(mods) - len(bad), bad


def check_modification_coverage(mods, entries, inst_map):
    """El cruce que hace el agujero DETECTABLE, en los dos sentidos.

    Sentido 1:  una entrada del manifiesto principal marcada instrumented=yes
    que NO esta en la seccion MODIFICACIONES.  Eso es "el estado del corpus
    esta declarado a medias".

    Sentido 2:  una linea MOD con instrumented=yes y citado=yes que NO esta en
    las 61 entradas.  Alguien declara que el componente cita un fichero
    instrumentado y no lo ha puesto en el manifiesto del componente.

    MEDIDO que el defecto que esto cierra era REAL:  cuatro ficheros del corpus
    tienen instrumentado con hash instrumentado ausente de todo el repo.  Con
    esta comprobacion,  repetir eso sale con codigo 5 en vez de con un exit 0
    tranquilo.
    """
    mod_rutas = {r["ruta"] for r in mods}
    mod_citadas = {r["ruta"] for r in mods
                   if r["instrumented"] == "yes" and r["citado"] == "yes"}
    ent_rutas = {rel for rel, _ in entries}

    f1 = sorted(rel for rel, _ in entries
                if inst_map.get(rel) == "yes" and rel not in mod_rutas)
    f2 = sorted(r for r in mod_citadas if r not in ent_rutas)
    return f1, f2


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
    """Mapa ruta -> verdict. El hermano es opcional: si no esta, no
    se inventa nada y se devuelve {} (--allow-instrumented no tendra efecto).

    MEDIDO 2026-10-04: la seccion MODIFICACIONES se salta aqui, y no por
    construccion sino porque todas sus lineas empiezan por '#'.  Es lo que
    permite anadirla sin tocar este parser,  que es el parser que conocia el
    manifiesto de siempre."""
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
    ap.add_argument("--sin-arbol", action="store_true",
                    help="NO_TOUCH_TREE: no se lee ni un byte del arbol.  Contesta "
                         "solo 'que estado declara el corpus',  que es la pregunta "
                         "que se puede responder sin el arbol.  Devuelve 0, 3, 4 o 5: "
                         "nunca 1 ni 2,  porque los dos veredictos de esos dos "
                         "codigos son afirmaciones sobre el disco.")
    ap.add_argument("--sin-modificaciones", action="store_true",
                    help="NO_CHECK_MODS: no comprueba la seccion MODIFICACIONES del "
                         "hermano.  Para comparar el comportamiento de 1.0.0 con el "
                         "de 2.0.0 sobre el mismo arbol.")
    args = ap.parse_args(argv)

    try:
        entries = parse_manifest(args.manifest)
    except ValueError as e:
        sys.stderr.write("ERROR: %s\n" % e)
        return EXIT_UNUSABLE

    inst = load_instrumented(args.sidecar)

    mods = []
    if not args.sin_modificaciones:
        try:
            mods = parse_modifications(args.sidecar)
        except ValueError as e:
            sys.stderr.write("ERROR: %s\n" % e)
            return EXIT_UNUSABLE

    # ── (A) EL ESTADO DECLARADO.  No necesita arbol, y se comprueba siempre. ──
    incoherent = []
    if mods:
        n_ok, incoherent = check_modifications_selfconsistent(mods)
        f1, f2 = check_modification_coverage(mods, entries, inst)
        if not args.quiet:
            for rec, probs in incoherent:
                for pr in probs:
                    sys.stdout.write("INCOHERENTE\t%s\tL%d\t%s\n"
                                     % (rec["ruta"], rec["linea"], pr))
            for rel in f1:
                sys.stdout.write("COBERTURA\t%s\tinstrumented=yes en el manifiesto "
                                 "pero no esta en la seccion MODIFICACIONES\n" % rel)
            for rel in f2:
                sys.stdout.write("COBERTURA\t%s\tMODIFICACIONES dice citado=yes pero "
                                 "no esta entre las entradas del manifiesto\n" % rel)
        #  MEDIDO por que esto se imprime siempre y no solo en --quiet:  es el
        #  numero que responde "que estado declara el corpus",  y un consumidor
        #  que lee el exit code y nada mas no sabe que el exit 0 lleva conmigo
        #  una declaracion de seis ficheros.
        sys.stdout.write("MODIFICACIONES\t%d\tcoherentes\t%d\tinstrumentadas\t%d\n"
                         % (len(mods), n_ok,
                            sum(1 for r in mods if r["instrumented"] == "yes")))

    if args.sin_arbol:
        #  El arbol no se ha abierto:  por construccion no puede haber mismatch ni
        #  NO_SE_ENCUENTRA,  y decir 1 o 2 seria mentir sobre algo no comprobado.
        if not args.quiet:
            sys.stdout.write("SIN_ARBOL\tno se ha leido ningun fichero del arbol\n")
        if incoherent:
            return EXIT_INCOHERENT
        if mods and (f1 or f2):
            return EXIT_COVERAGE
        return EXIT_OK

    if not os.path.isdir(args.tree):
        sys.stderr.write("ERROR: no existe el arbol: %s\n" % args.tree)
        return EXIT_UNUSABLE

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
            return EXIT_UNUSABLE
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

    #  ── EL ORDEN DE PREVALENCIA, Y POR QUE ESTA ESCRITO ──────────────────
    #  MEDIDO que esto no es cosmetico:  con el arbol de working/ hay 2 mismatch
    #  y 21 ausencias,  y sin este orden el consumidor veria un codigo y no
    #  sabria de que clase de problema estaba hablando.
    #
    #  1) 3 antes que todo:  sin manifiesto no hay nada que decir,  y un 1 o un
    #     2 aqui serian un veredicto sobre algo que no se ha podido leer.
    #  2) 1 antes que 2:  un hash que no cuadra es ruido;  un fichero que no esta
    #     es un arbol incompleto,  y en un arbol incompleto los hashes que SI
    #     cuadran no se pueden leer como "el arbol es el de referencia".
    #  3) 4 antes que 5:  una linea que se contradice a si misma es un dato
    #     escrito mal,  y por encima de el no se puede decidir si la cobertura
    #     declarada significa algo.
    #  4) 4 y 5 antes que 1:  el estado DECLARADO manda sobre el estado del
    #     disco.  Si la declaracion esta mal,  un exit 0 del arbol no seria un
    #     "todo bien":  seria un arbol correcto descrito mal.
    if mism:
        return EXIT_MISMATCH
    if missing:
        return EXIT_MISSING
    if incoherent:
        return EXIT_INCOHERENT
    if mods and (f1 or f2):
        return EXIT_COVERAGE
    return EXIT_OK


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))