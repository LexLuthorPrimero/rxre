#!/usr/bin/env python3
# CONTRACT: name=reenvio_freeze
# CONTRACT: READONLY=no        (solo con --congelar; por defecto solo lee)
# CONTRACT: WRITES_FILES=yes   (un unico fichero: REENVIO-FINDINGS.tsv)
# CONTRACT: MUTATES_CORPUS=no
# CONTRACT: WRITES_SYSFS=no
# CONTRACT: WRITES_GPU=no

"""Congela el mapa de renumeraciones ANTES de que la renumeracion se commitee.

POR QUE EXISTE Y POR QUE HAY QUE CORERLO ANTES DEL COMMIT
-------------------------------------------------------
`findings_index.reenvios()` NO LEE UNA TABLA: deriva los pares (viejo, nuevo)
comparando `git ls-tree HEAD` contra el arbol de trabajo. Es la unica fuente, y
es una fuente que se autodestruye:

    HEAD tiene 156-coherencia-cpu-gpu-tres-mecanismos.md
    el arbol tiene 232-coherencia-cpu-gpu-tres-mecanismos.md
    mismo stem, numeros distintos  ->  par (156, 232)

En cuanto se commitea el renumerado, HEAD y el arbol coinciden, la comparacion
da VACIO, `reenvios()` devuelve `[]`, y con ella desaparecen:

  - la tabla de reenvios,
  - `refs_colgadas()`, que sin `rev` no puede detectar una cita colgando,
  - `refs_repair.py --aplicar`, que se queda sin mapa.

Es decir: la deteccion de referencias colgando depende de un diff que va a
desaparecer en el mismo commit que lo arregla. Si se commitea sin congelar
primero, la reparacion no es solo dificil: es IRREPETIBLE y no auditable.

Por eso el mapa se congela en un fichero DE DATOS, versionado, con su
procedencia. El mapa deja de depender de un diff.

LO QUE NO ES
------------
No es un renumerador. No cambia numeros. No reescribe citas. Solo copia el mapa
que la deteccion produce y lo vuelve permanente. Las citas las repara
`refs_repair.py --ambito todos`, que LEE este fichero.

GARANTIA DE NO-DESTRUCCION
-------------------------
Si el fichero ya existe, `--congelar` NO lo sobreescribe: se niega y sale con
codigo 3. Un mapa congelado es la unica copia de una tabla que se autodestruye;
sobrescribirlo con una reejecucion posterior que por cualquier motivo devuelva
vacio la borraria. La negacion no se puede sortear por descuido.

`--congelar --forzar` existe, exige `--confirmar-obsoleto` y aun asi escribe el
mapa viejo a `.bak` antes de sustituirlo.

CODIGOS DE SALIDA
-----------------
  0  mapa congelado, o ya existia y es coherente, o verificacion correcta
  1  fallo de verificacion (integridad, cadena, colision de destino)
  2  no se pudo ejecutar (git no responde, no hay HEAD)
  3  --congelar sobre un mapa que ya existe (nada escrito)
  4  --congelar sin mapa que congelar (reenvios() vacio y no hay fichero)
"""

import argparse
import hashlib
import os
import re
import subprocess
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
FIND = os.path.join(ROOT, "06-INGENIERIA-INVERSA", "findings")
DEST = os.path.join(HERE, "REENVIO-FINDINGS.tsv")

sys.path.insert(0, HERE)
from findings_index import escanear, reenvios, _stem  # noqa: E402

# MEDIDO 2026-10-04: se anadio `procedencia`. Antes eran 4 campos y el mapa
# tiene 49 filas; la quinta dice COMO se obtuvo cada una, y hay tres clases que
# no son la misma cosa:
#
#   `diff`          la derivo reenvios() del arbol contra HEAD. 43 filas.
#   `git:<hash>`    la prueba un RENAME de git. 2 filas.
#   `prosa:<f>:<l>` la unica fuente es la prosa del fichero de destino. 4 filas.
#
# POR QUE LA QUINTA COLUMNA NO ES DECORACION, y por que tiene que ir en las 49:
#
#   1. Una fila sin procedencia es indistinguible de una fila que el instrumento
#      puede volver a derivar. Las 4 `prosa:` NO se pueden derivar: el numero
#      viejo ya lo tenia otro hallazgo, asi que el fichero viejo nunca existio
#      en git. Si `--congelar` regenera el fichero, esas 6 filas desaparecen y
#      no hay nada en el TSV que lo impida ni nada que avise de que se han ido.
#   2. Un formato de 5 columnas en 6 filas y de 4 en 43 no es un formato: es dos
#      formatos, y cualquiera que los lea tiene que adivinar cual le toca.
#
# MEDIDO 2026-10-04:  se anade la columna `relacion` entre `stem` y
# `procedencia`.  No es cosmetica:  ver el hallazgo 1040.  La tabla contenia dos
# relaciones distintas —renumerado de CONTENIDO,  y colision de ASIGNACION de
# numero— con un solo nombre de columna,  y confundirlas rompe al reparar citas.
#
# Y EL DEFECTO QUE ESTO NO ARREGLA, dicho aqui para que no se lea como que si:
# `--congelar` sigue siendo DESTRUCTIVO para esas 6 filas. Este fichero las
# reescribe enteras desde reenvios(). Lo que se anade es la columna que DICE que
# se van a ir, no un modo de conservarlas. Arreglar eso es otra cosa y no esta
# hecha; ver la cabecera del TSV.
CAMPOS = ("viejo", "nuevo", "reasignado", "stem", "relacion", "procedencia")

# Lo que escribe una fila cuyo origen es el propio diff. Es el valor por defecto
# y no una constante magica: `cuerpo()` solo la usa cuando la fila no trae
# `procedencia`, y las que trae son las que un humano o un rename aportaron.
PROCEDENCIA_DIFF = "diff"


def _head_id():
    """HEAD corto, o None si git no responde."""
    try:
        p = subprocess.run(["git", "-C", ROOT, "rev-parse", "HEAD"],
                           capture_output=True, text=True, timeout=30)
    except (OSError, subprocess.SubprocessError):
        return None
    if p.returncode != 0:
        return None
    return p.stdout.strip()


def _stem_completo(rev, filas):
    """`rev["stem"]` viene TRUNCADO a 58 chars (cabecera de tabla). Para un
    fichero de datos hace falta completo: dos truncados pueden coincidir."""
    por_stem = {}
    for f in filas:
        por_stem.setdefault(_stem(f["fichero"]), set()).add(f["num"])
    for r in rev:
        # el stem completo es el unico <prefijo> que produce exactamente esos
        # numeros en el arbol actual
        for st, nums in por_stem.items():
            if st.startswith(r["stem"]) and r["nuevo"] in nums:
                r["stem"] = st
                break
    return rev


def cuerpo(rev):
    """Cuerpo TSV, orden estable, sin cabecera. Es lo que se hashea.

    MEDIDO 2026-10-04: escribe 5 campos. El quinto sale de `r["procedencia"]` y,
    si la fila no lo trae, es `diff` -- que es la verdad para todo lo que produce
    `reenvios()`. Las filas que traen su propia procedencia no la pisan: por eso
    una fila leida del fichero congelado y reescrita conserva su `git:` o su
    `prosa:`. Antes no habia quinto campo y esa informacion no existia.
    """
    out = []
    for r in sorted(rev, key=lambda x: (x["viejo"], x["nuevo"])):
        out.append("%d\t%d\t%s\t%s\t%s" % (
            r["viejo"], r["nuevo"],
            "SI" if r["reasignado"] else "no", r["stem"],
            (r.get("procedencia") or PROCEDENCIA_DIFF)))
    return "\n".join(out) + "\n"


def sha_de(cuerpo_txt):
    return hashlib.sha256(cuerpo_txt.encode("utf-8")).hexdigest()


def escribir(rev, head):
    c = cuerpo(rev)
    cab = (
        "# REENVIO-FINDINGS.tsv -- mapa CONGELADO de renumeraciones de hallazgos.\n"
        "#\n"
        "# POR QUE ESTE FICHERO EXISTE\n"
        "#   findings_index.reenvios() deriva este mapa comparando `git ls-tree HEAD`\n"
        "#   contra el arbol de trabajo. Al commitear la renumeracion esa comparacion\n"
        "#   da VACIO y el mapa desaparece. Este fichero es la copia permanente.\n"
        "#\n"
        "#   La tabla Markdown FINDINGS-RENUMERACIONES.md es una VISTA de aqui.\n"
        "#   Este es el dato. Ante discrepancia, gana este.\n"
        "#\n"
        "# CONSUMIDORES\n"
        "#   findings_index.reenvios_estable()  -- lee el mapa congelado\n"
        "#   08-ARQUITECTURA/tools/refs_repair.py -- repara citas colgando\n"
        "#\n"
        "# COLUMNAS  (5, y las 5 en todas las filas: un formato mixto seria\n"
        "#   peor que ninguno)\n"
        "#   viejo        numero que se escribio antes del renumerado\n"
        "#   nuevo        numero que tiene HOY ese mismo hallazgo\n"
        "#   reasignado   SI = el numero viejo esta ocupado HOY por OTRO contenido\n"
        "#                no = el numero viejo quedo libre; la cita no miente\n"
        "#   stem         nombre de fichero SIN el numero, completo\n"
        "#   procedencia   COMO se obtuvo ESTA fila: `diff`, `git:<hash>` o\n"
        "#                `prosa:<fichero>:<lineas>`. Hay filas que reenvios()\n"
        "#                NO puede derivar, y esta columna es lo que lo dice.\n"
        "#\n"
        "# NOTA SOBRE `reasignado=no`: si vale `no`, una cita `` `viejo` `` no apunta a\n"
        "#   un hallazgo equivocado, sino a que ese numero ya no existe. Es un caso\n"
        "#   distinto, y mas barato. Ver 075 -> 975/976 en la tabla.\n"
        "#\n"
        "# PROCEDENCIA\n"
        "#   generado_por  08-ARQUITECTURA/tools/reenvio_freeze.py --congelar\n"
        "#   generado_en    %s\n"
        "#   fuente         findings_index.reenvios() sobre el arbol de trabajo\n"
        "#   git_head       %s\n"
        "#   git_head_corto %s\n"
        "#   pares          %d\n"
        "#   sha256_cuerpo  %s\n"
        "#\n"
        "# NO EDITAR A MANO. Para cambiarlo: borrarlo y volver a congelar ANTES de que\n"
        "#   el renumerado este commiteado, o usar\n"
        "#   reenvio_freeze.py --congelar --forzar --confirmar-obsoleto\n"
        "#\n"
        "# MEDIDO 2026-10-04, Y ESTO ES LO QUE HACE INSUFICIENTE EL AVISO DE ARRIBA:\n"
        "#   `--congelar` REGENERA este fichero entero desde reenvios(), y solo ve\n"
        "#   las renumeraciones NO commiteadas. Por eso BORRA cualquier fila cuya\n"
        "#   procedencia no sea `diff`. Y no avisa: sale con un 0.\n"
        "#   MEDIDO que hoy hay %d filas que no son `diff`, y que ninguna se puede\n"
        "#   recuperar por la via del diff: 2 se commitearon antes del sellado, y 4\n"
        "#   tienen la unica fuente en la prosa de su fichero de destino porque el\n"
        "#   numero viejo ya lo tenia otro hallazgo.\n"
        "#   Antes de re-congelar, exportar esas filas. La puerta de integridad es\n"
        "#   08-ARQUITECTURA/tools/reenvio_gate.py y 08-ARQUITECTURA/tools/reenvio_freeze.py --verificar\n"
        "#\n"
    ) % (
        time.strftime("%Y-%m-%dT%H:%M:%S%z"),
        head or "DESCONOCIDO",
        (head or "")[:12],
        len(rev),
        sum(1 for r in rev if (r.get("procedencia") or PROCEDENCIA_DIFF)
            != PROCEDENCIA_DIFF),
        sha_de(c),
    )
    with open(DEST, "w", encoding="utf-8") as fh:
        fh.write(cab)
        fh.write(c)
    return c


def leer():
    """(cabecera_como_texto, cuerpo_texto, filas) o None si no existe."""
    if not os.path.exists(DEST):
        return None
    txt = open(DEST, encoding="utf-8").read()
    lineas = txt.splitlines()
    cab, cuesco = [], []
    en_cuerpo = False
    for ln in lineas:
        if not en_cuerpo and ln.startswith("#"):
            cab.append(ln)
            continue
        en_cuerpo = True          # la primera linea no-comentario inicia el cuerpo
        cuesco.append(ln)
    cuerpo_txt = "\n".join(l for l in cuesco if l.strip()) + "\n"
    filas = []
    for n_lin, l in enumerate(cuesco, 1):
        if not l.strip() or l.startswith("#"):
            continue
        p = l.split("\t")
        # MEDIDO 2026-10-04: esto era `if len(p) != 4: continue`. Con 5 columnas
        # se comia el mapa entero sin decir nada, y `leer()` devolvia (cab, txt,
        # []) -- indistinguible de "no hay mapa". Un `continue` que descarta el
        # dato y no deja rastro no es robustez: es la causa de que este mapa
        # pareciera completo cuando no lo era.
        if len(p) != len(CAMPOS):
            raise ValueError(
                "%s: fila de datos con %d campos, se esperaban %d: %r"
                % (DEST, n_lin, len(p), len(CAMPOS), l[:70]))
        if p[2] not in ("SI", "no"):
            raise ValueError("%s: reasignado vale %r, no es SI ni no: %r"
                             % (DEST, p[2], l[:70]))
        if not p[4].strip():
            raise ValueError("%s: procedencia vacia: %r" % (DEST, l[:70]))
        filas.append({"viejo": int(p[0]), "nuevo": int(p[1]),
                      "reasignado": p[2] == "SI", "stem": p[3],
                      "procedencia": p[4]})
    return "\n".join(cab), cuerpo_txt, filas


RE_SHA_DECLARADO = re.compile(r"sha256_cuerpo\s+([0-9a-f]{64})\s*$")


def _sha_declarado(cabecera_txt):
    """El sha256 que la cabecera DECLARA, o None si no declara ninguno.

    MEDIDO 2026-10-04, y looring al anadir una linea de prosa a la cabecera. La
    version anterior hacia esto:

        for ln in cabecera.splitlines():
            if "sha256_cuerpo" in ln:
                declarado = ln.split("sha256_cuerpo")[1].strip()

    O sea: busca una SUBSTRING y se queda con la ULTIMA linea que la contenga.
    Al escribir en la cabecera la linea de prosa

        # NORMALIZACION DEL sha256_cuerpo, que es la que verifica:

    esa linea gano, y el valor leido fue `que es la que verifica:`. MEDIDO: la
    puerta imprimió

        PROBLEMA sha256 declarado , que es la que  != real f5de7808a59a9e21

    con un sha de 49 filas que SI cuadraba. O sea que el fallo no era un
    descuadre del dato: era un descuadre del LECTOR, y se presenta como si
    fuera del dato. Un verificador de integridad que se rompe al escribir un
    comentario no puede usarse para afirmar que el dato esta intacto.

    El criterio ahora es la FORMA, no la presencia: la linea que cuenta es la
    que termina en 64 hexadecimales. Una linea de prosa que mencione la clave
    no puede pasar por declaracion, y si no hay ninguna, se dice que no hay
    ninguna en vez de comparar contra una cadena vacia.
    """
    m = None
    for ln in cabecera_txt.splitlines():
        mm = RE_SHA_DECLARADO.search(ln)
        if mm:
            m = mm.group(1)
    return m


def verificar(filas, cuerpo_txt=None, declarado_sha=None):
    """Devuelve lista de problemas. Vacia = coherente.

    `declarado_sha` es el sha256 que el fichero DECLARA en su cabecera. Si es
    None se lee del disco, y si no hay disco la comprobacion se omite: el
    self-test construye mapas en memoria y no debe depender de que exista un
    fichero congelado.
    """
    p = []
    if cuerpo_txt is None:
        cuerpo_txt = cuerpo(filas)
    if declarado_sha is None:
        got = leer()
        if got is not None:
            declarado_sha = _sha_declarado(got[0])
    if declarado_sha is not None:
        real = sha_de(cuerpo_txt)
        if declarado_sha != real:
            p.append("sha256 declarado %s != real %s"
                     % (declarado_sha[:16], real[:16]))
    # 2. identidad: un par consigo mismo no renumera nada
    for r in filas:
        if r["viejo"] == r["nuevo"]:
            p.append("par identidad %d->%d" % (r["viejo"], r["nuevo"]))
    # 3. CADENA: si `viejo` es a su vez un `nuevo`, reparar a el deja la cita
    #    colgando en el siguiente salto. Esto es el fallo que hace que una
    #    reparacion "correcta" siga rota.
    nuevos = {r["nuevo"] for r in filas}
    for r in filas:
        if r["viejo"] in nuevos:
            p.append("CADENA: %d -> %d, y %d es a su vez destino de otra"
                     % (r["viejo"], r["nuevo"], r["viejo"]))
    # 4. dos pares distintos con el mismo destino y distinto origen no es error,
    #    pero un MISMO origen con dos destinos si lo es
    por_viejo = {}
    for r in filas:
        por_viejo.setdefault(r["viejo"], set()).add(r["nuevo"])
    for v, ns in por_viejo.items():
        if len(ns) > 1:
            p.append("origen %d con destinos %s" % (v, sorted(ns)))
    return p


def self_test():
    fails = []

    def eq(got, want, etiqueta):
        if got != want:
            fails.append("%s: obtuve %r, quiero %r" % (etiqueta, got, want))

    # MEDIDO 2026-10-04: los VALORES ESPERADOS de estas dos aserciones
    # pasaron de 4 campos a 5. Se actualiza el valor esperado, no la
    # asercion: el criterio --"una fila es exactamente su linea TSV, y
    # reasignado se escribe SI/no y no True/False"-- no ha cambiado, lo que
    # cambio es el esquema. Un self-test al que se le anaden campos al
    #que hay que ajustar la expectativa y sigue midiendo lo mismo; uno al que se
    # le quita una asercion para que pase ya no mide nada.
    eq(cuerpo([{"viejo": 1, "nuevo": 2, "reasignado": True, "stem": "a.md"}]),
       "1\t2\tSI\ta.md\tdiff\n",
       "cuerpo: un par produce exactamente su linea TSV")
    eq(cuerpo([{"viejo": 1, "nuevo": 2, "reasignado": False, "stem": "a.md"}]),
       "1\t2\tno\ta.md\tdiff\n",
       "cuerpo: reasignado=no se escribe 'no', no 'False'")
    # Y la quinta columna NO se pisa cuando la fila trae la suya: es lo que
    # permite que una fila leida del congelado conserve `git:` o `prosa:` al
    # reescribirse. Sin esta asercion, la columna podia decorarse de
    # cualquier cosa y seguir dando verde.
    eq(cuerpo([{"viejo": 1, "nuevo": 2, "reasignado": True, "stem": "a.md",
                "procedencia": "git:0123456789ab"}]),
       "1\t2\tSI\ta.md\tgit:0123456789ab\n",
       "cuerpo: la procedencia propia de la fila gana a la del defecto")
    # orden estable: el mismo conjunto en otro orden da el MISMO sha
    a = [{"viejo": 300, "nuevo": 301, "reasignado": True, "stem": "x.md"},
         {"viejo": 9, "nuevo": 10, "reasignado": False, "stem": "y.md"}]
    b = list(reversed(a))
    eq(sha_de(cuerpo(a)), sha_de(cuerpo(b)), "sha: independiente del orden de entrada")
    # deteccion de cadena: 156->232 y 232->999 debe FALLAR
    cadena = [{"viejo": 156, "nuevo": 232, "reasignado": True, "stem": "a.md"},
              {"viejo": 232, "nuevo": 999, "reasignado": True, "stem": "b.md"}]
    if not any("CADENA" in x for x in verificar(cadena)):
        fails.append("verificar: no detecta la cadena 156->232->999")
    # par identidad
    if not any("identidad" in x for x in
               verificar([{"viejo": 7, "nuevo": 7, "reasignado": False, "stem": "c.md"}])):
        fails.append("verificar: no detecta el par identidad 7->7")
    # origen con dos destinos
    if not any("dos destinos" in x or "destinos" in x for x in
               verificar([{"viejo": 5, "nuevo": 6, "reasignado": True, "stem": "d.md"},
                          {"viejo": 5, "nuevo": 8, "reasignado": True, "stem": "e.md"}])):
        fails.append("verificar: no detecta el origen 5 con dos destinos")
    # sha tamper: un sha declarado que no es el del cuerpo debe FALLAR.
    # Antes esto no se comprobaba, y por eso el bug de leer() de arriba tardo
    # en aparecer: un criterio que solo puede fallar si uno se equivoca al
    # invocarlo no es un criterio.
    filas = [{"viejo": 1, "nuevo": 2, "reasignado": True, "stem": "a.md"}]
    c = cuerpo(filas)
    if sha_de(c) == sha_de(c.replace("1\t", "3\t")):
        fails.append("sha: no distingue un cuerpo de otro")
    if not verificar(filas, c, declarado_sha="0" * 64):
        fails.append("verificar: no detecta un sha256 declarado que no cuadra")
    if verificar(filas, c, declarado_sha=sha_de(c)):
        fails.append("verificar: da falso positivo con el sha256 correcto")

    # EL LECTOR DEL sha DECLARADO. Este control existe porque el criterio viejo
    # se rompió al escribir una linea de prosa en la cabecera, y se rompió
    # PRESENTANDOSE COMO UN DESCUADRE DEL DATO: la puerta dijo que el sha no
    # cuadraba cuando el sha cuadraba y lo que estaba roto era la busqueda. Sin
    # este control, un rotulo en prosa en la cabecera puede volver a tumbar la
    # garantia de integridad en cualquier momento y nadie lo distinguiria de un
    # fichero manipulado.
    #
    # Se comprueba la REGLA sobre un caso construido, porque un caso real de este
    # defecto ya no existe en la cabecera: la prosa se escribio UNA vez y el
    # criterio viejo ya no esta.
    bueno = "a" * 64
    cab_con_prosa = (
        "# REENVIO-FINDINGS.tsv\n"
        "#\n"
        "# NORMALIZACION DEL sha256_cuerpo, que es la que verifica:\n"
        "#   solo las filas de datos\n"
        "#   pares          2\n"
        "#   sha256_cuerpo  %s\n" % bueno)
    eq(_sha_declarado(cab_con_prosa), bueno,
       "sha declarado: una linea de prosa que menciona la clave no es la "
       "declaracion")
    eq(_sha_declarado("# nada aqui\n"), None,
       "sha declarado: sin declaracion devuelve None, no una cadena vacia")
    # Y un valor que NO es un sha de 64 hex no es una declaracion: se trunca en
    # el mismo criterio que antes, y por eso un sha pegado a medias no se lee
    # como sha y se compara contra algo. Esto puede fallar si alguien relaja el
    # criterio a "cualquier cosa al final de la linea".
    eq(_sha_declarado("#   sha256_cuerpo  %s\n" % ("a" * 63)), None,
       "sha declarado: 63 hex no son un sha256")
    eq(_sha_declarado("#   sha256_cuerpo  %sPERO NO\n" % ("a" * 64)), None,
       "sha declarado: 64 hex con texto detras no es una declaracion")
    # Y el criterio NO es "la ultima linea que menciona la clave": si lo fuera,
    # la primera asercion de este bloque fallaria. Se deja dicho, porque un
    # control cuyo negativo no se nombra se lee como si no lo tuviera.

    for f in fails:
        print("  FALLA %s" % f)
    print("self_test: %s" % ("OK" if not fails else "%d FALLAS" % len(fails)))
    return 0 if not fails else 1


def main(argv):
    ap = argparse.ArgumentParser(add_help=True)
    ap.add_argument("--congelar", action="store_true")
    ap.add_argument("--verificar", action="store_true")
    ap.add_argument("--ver-live", action="store_true",
                    help="compara el mapa congelado con el que derivaria git HOY")
    ap.add_argument("--self-test", action="store_true")
    ap.add_argument("--forzar", action="store_true")
    ap.add_argument("--confirmar-obsoleto", action="store_true")
    a = ap.parse_args(argv)

    if a.self_test:
        return self_test()

    filas = escanear()
    if filas is None:
        print("reenvio_freeze: no existe %s" % FIND, file=sys.stderr)
        return 2
    head = _head_id()
    if head is None:
        print("reenvio_freeze: git no responde; sin procedencia no congelo",
              file=sys.stderr)
        return 2

    if a.congelar:
        if os.path.exists(DEST) and not (a.forzar and a.confirmar_obsoleto):
            print("reenvio_freeze: YA EXISTE %s" % DEST)
            print("  un mapa congelado es la unica copia de una tabla que se")
            print("  autodestruye. No se sobreescribe por descuido.")
            print("  para reemplazarlo: --forzar --confirmar-obsoleto")
            return 3
        rev = _stem_completo(reenvios(filas), filas)
        if not rev:
            print("reenvio_freeze: reenvios() vacio; no hay mapa que congelar",
                  file=sys.stderr)
            return 4
        probs = verificar(rev)
        if probs:
            print("reenvio_freeze: el mapa vivo ya falla la verificacion:")
            for p in probs:
                print("  %s" % p)
            return 1
        if os.path.exists(DEST):
            with open(DEST + ".bak", "w", encoding="utf-8") as fh:
                fh.write(open(DEST, encoding="utf-8").read())
        c = escribir(rev, head)
        print("congelado %s" % DEST)
        print("  pares      %d" % len(rev))
        print("  sha256     %s" % sha_de(c))
        print("  git_head   %s" % head[:12])
        return 0

    got = leer()
    if got is None:
        if a.verificar or a.ver_live:
            print("reenvio_freeze: no existe %s" % DEST)
            return 2
        print("reenvio_freeze: no existe %s" % DEST)
        return 2

    cab, cuerpo_txt, filas_rev = got
    if a.ver_live:
        rev_vivo = _stem_completo(reenvios(filas), filas)
        if not rev_vivo:
            print("  ver-live: git HOY ya no ve ninguna renumeracion.")
            print("  Esto es lo ESPERADO si la renumeracion ya esta commiteada:")
            print("  el mapa congelado es la unica copia que queda.")
        else:
            h1, h2 = sha_de(cuerpo(filas_rev)), sha_de(cuerpo(rev_vivo))
            if h1 == h2:
                print("  ver-live: congelado == vivo   (%s)" % h1[:16])
            else:
                print("  ver-live: DIFIEREN")
                print("    congelado %s  %d pares" % (h1[:16], len(filas_rev)))
                print("    vivo      %s  %d pares" % (h2[:16], len(rev_vivo)))
                return 1
    if a.verificar:
        probs = verificar(filas_rev, cuerpo_txt)
        for p in probs:
            print("  PROBLEMA %s" % p)
        print("verificar: %d pares, %s" %
              (len(filas_rev), "OK" if not probs else "%d PROBLEMAS" % len(probs)))
        return 1 if probs else 0

    print("congelado: %d pares  sha256 %s" % (len(filas_rev), sha_de(cuerpo_txt)))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))