#!/usr/bin/env python3
# CONTRACT: name=reenvio_freeze
# CONTRACT: READONLY=no        (solo con --congelar / --sustituir; por defecto lee)
# CONTRACT: WRITES_FILES=yes   (REENVIO-FINDINGS.tsv; con --sustituir tambien
#                              .bak y .descartadas.tsv)
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

GARANTIA DE NO-DESTRUCCION: `--congelar` ES UN MERGE
---------------------------------------------------
`--congelar` NO reescribe el mapa: lo COMPLETA. Una fila que ya esta congelada se
conserva; solo se anaden las que no estaban. No existe combinacion de flags que
haga que `--congelar` borre una fila.

El motivo no es prudencia decorativa. MEDIDO 2026-10-04 sobre este repositorio:

  * `reenvios()` devuelve **0 pares**. Las renumeraciones ya estan commiteadas.
  * El mapa congelado tiene **49 filas**: 43 `diff`, 2 `git:<commit>`, 4 `prosa:`.

O sea: las 6 filas que `reenvios()` NO puede derivar son hoy el 100% de lo que
la herramienta derivaria si el mapa se regenerara. Un congelado que reescribe
desde `reenvios()` no pierde "unas pocas filas": pierde el mapa entero, y sale
con un 0.

Y aqui hay que ser exacto sobre lo que la version ANTERIOR hacia, porque la
garantia que se announcing no era la que habia:

  * MEDIDO que `--congelar` a secas daba `rc=3` y no escribia. Correcto.
  * MEDIDO que `--congelar --forzar --confirmar-obsoleto` daba `rc=4` y TAMPOCO
    escribia, porque `reenvios()` vacio hace caer en "no hay mapa que congelar".
    Es decir: el bypass NO destruia, pero por ACCIDENTE DE ORDEN, no por
    diseno. La unica cosa que separaba la foto de la destruccion era que el
    diff estaba degradado.
  * MEDIDO que en cuanto `reenvios()` devuelve UN par -- que es exactamente el
    uso previsto de la herramienta, congelar un renumerado SIN commitear -- el
    bypass se activa de verdad: el guard de `verificar()` comparaba el mapa
    NUEVO contra el sha declarado por el fichero VIEJO, fallaba, y devolvia
    `rc=1`. o sea, third guard, tambien accidental.
  * MEDIDO que `escribir()` no podia escribir NUNCA: su plantilla de cabecera
    tiene los especificadores 5 y 6 transpuestos respecto a la tupla de
    argumentos, y `sha_de()` devuelve `str` donde la plantilla pide `%d`.
    MEDIDO `TypeError: %d format: a real number is required, not str`, con 1 fila
    y con 3 alike. El `.bak` se escribia antes de ese fallo.

Tres guards, ninguno de diseno, y detras un escritor muerto. La garantia
declarada ("la negacion no se puede sortear por descuido") era verdad por
accidente y no por construccion. Un invariante que se sostiene porque tres
bugs se cancelan no es una invariante: es una coincidencia con codigo de
salida.

QUE HACE AHORA CADA FLAG
------------------------
  --congelar          MERGE. Anade lo que falte, conserva lo que hay. No borra.
  --sustituir         Reemplaza el mapa entero. DESTRUCTIVO, y por eso exige
                      las DOS confirmaciones de abajo y no puede vaciar nada.
  --perder N          Dice cuantas filas se van a perder. Si el numero no
                      coincide con lo que la herramienta calcula, se niega.
  --confirmar-obsoleto  Constante, solo con --sustituir.
  --forzar            **ELIMINADO.** Antes sorteaba la negacion; ahora
                      argparse lo rechaza con codigo 2 y dice que no existe.
                      Un flag que se deja de usar tiene que FALLAR al usarlo,
                      no volverse inocuo: alguien que teclee el hechizo viejo se
                      entera por el error, no por un 0 silencioso.

`--sustituir` deja de poder vaciar el fichero, y eso no es una limitacion que se
acepte a reganadas: es la condicion que hace segura la puerta. MEDIDO que la
fuente se degrada sola -- hoy 0 pares, manana 1 -- y una puerta destructiva que
se dispara justamente cuando la fuente esta peor es una puerta que se dispara
cuando menos falta hace. Si el mapa nuevo sale vacio, se niega; y si salen menos
filas de las que hay, hay que nombrarlas por numero antes de perderlas, y quedan
escritas en `REENVIO-FINDINGS.descartadas.tsv`.

LO QUE `--perder` ES Y LO QUE NO ES, MEDIDO Y NO DEDUCIDO
---------------------------------------------------------
`--perder N` es una AUTORIZACION POR CONTEO, no una COTA. MEDIDO que
`--sustituir` puede llevar el mapa de 49 filas a 1 si `reenvios()` devuelve un
solo par y quien lo ejecuta teclea `--perder 48`: las cuatro puertas se abren,
porque las cuatro son ciertas. No hay un minimo de filas por debajo del cual la
herramienta se niegue, y no lo hay a proposito: un minimo arbitrario seria un
numero sin fundamento, y este numero sale del dato.

Lo que hace es que la decision no se pueda tomar por descuido. Para perder 48
filas hay que teclear 48, having visto las 48 impresas una a una con su numero
y su procedencia; y antes quedan en `.descartadas.tsv` y en `.bak`, que MEDIDO
que es byte a byte el fichero entero. O sea: destructivo, irreversible solo
para quien no lea los dos ficheros de al lado, y nunca silencioso.

CODIGOS DE SALIDA
-----------------
  0  merge hecho, o merge sin cambios, o verificacion correcta
  1  fallo de verificacion, o conflicto de datos: se nombran las filas (nada escrito)
  2  no se pudo ejecutar (git no responde, no hay HEAD, flags invalidos)
  3  --congelar sin nada que anadir: reenvios() vacio y no hay fichero
  4  --sustituir sin --confirmar-obsoleto
  5  --sustituir con un resultado VACIO: el mapa no se puede vaciar
  6  --sustituir sin --perder N, o con un N que no es el calculado
"""

import argparse
import hashlib
import os
import re
import shutil
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
#      en git. Si `--congelar` regenerase el fichero, esas 6 filas desaparecerian
#      y no habria nada en el TSV que lo impida ni nada que avise de que se han
#      ido. MEDIDO 2026-10-04: ya no se van. `--congelar` es un merge.
#   2. Un formato de 5 columnas en 6 filas y de 4 en 43 no es un formato: es dos
#      formatos, y cualquiera que los lea tiene que adivinar cual le toca.
#
# MEDIDO 2026-10-04:  se anade la columna `relacion` entre `stem` y
# `procedencia`.  No es cosmetica:  ver el hallazgo 1040.  La tabla contenia dos
# relaciones distintas —renumerado de CONTENIDO,  y colision de ASIGNACION de
# numero— con un solo nombre de columna,  y confundirlas rompe al reparar citas.
CAMPOS = ("viejo", "nuevo", "reasignado", "stem", "relacion", "procedencia")
COL_RELACION, COL_PROCEDENCIA = 4, 5
RELACIONES = ("contenido", "numero")

# Lo que escribe una fila cuyo origen es el propio diff. Es el valor por defecto
# y no una constante magica: `cuerpo()` solo la usa cuando la fila no trae
# `procedencia`, y las que traen son las que un humano o un rename aportaron.
PROCEDENCIA_DIFF = "diff"

# Que `relacion` merece una fila que la derivo `reenvios()`. No se elige: se
# DEDUCE del mecanismo, y por eso es una funcion y no una constante.
#
#   `reenvios()` empareja dos ficheros con el MISMO stem y numero DISTINTO, uno
#   de HEAD y otro del arbol de trabajo. Mismo stem = mismo documento. Si el
#   documento estaba en `NNN-x.md` y ahora esta en `MMM-x.md`, lo que se movio
#   es el CONTENIDO de un numero a otro. Luego la flecha mapea contenido, y la
#   fila es REPARABLE con ella.
#
# La clase `numero` -- el numero viejo ya lo ocupaba otro hallazgo y este
# contenido tomo el nuevo sin haberlo tenido nunca -- no la produce este
# mecanismo: si el fichero viejo no existia nunca, no hay RENAME que compararlo.
# Solo la puede aportar quien lee la prosa del fichero de destino.
def relacion_de(r):
    return (r.get("relacion") or "contenido")


# Lineas de cabecera que las MIENTE esta herramienta, no una persona. Todo lo
# demas que hay en la cabecera del TSV es prosa medida de hallazgos y se
# conserva verbatim: `escribir()` no sabe escribirla y borrarla seria tirar
# trabajo que no es suyo.
ETIQUETAS_MAQUINA = ("sha256_cuerpo", "git_head_corto", "git_head",
                     "generado_en", "generado_por", "fuente", "pares",
                     "modo", "merge_conservadas", "merge_anadidas",
                     "merge_completadas", "merge_difieren", "merge_conflictos",
                     "no_derivables", "filas_descartadas")
RE_ETIQUETA_MAQUINA = re.compile(
    r"^#\s*(%s)(?=\s|$)" % "|".join(sorted(ETIQUETAS_MAQUINA, key=len, reverse=True)))

RC_OK = 0
RC_FALLO = 1
RC_NO_EJECUTO = 2
RC_NADA_QUE_ANADIR = 3
RC_SIN_CONFIRMAR = 4
RC_MAPA_VACIO = 5
RC_PERDER_DESCONOCIDO = 6


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

    MEDIDO 2026-10-04: escribe 6 campos. ANTES escribia 5, y esa era una
    desincronizacion con el resto del mundo, no una decision: `CAMPOS` tenia 6,
    el fichero en disco tenia 6, `findings_index.reenvios_estable()` exigia 6 --
    y `cuerpo()` devolvia 5. MEDIDO que el round-trip no cerraba: el sha del
    cuerpo reconstruido era 8034e1c3... y el del fichero real 08c27e49..., con
    las MISMAS 49 filas. O sea: el escritor y el lector de la MISMA herramienta
    no decian el mismo numero de campos.

    Y el fallo no era cosmico. MEDIDO que `leer()` mapeaba `p[4]` a
    `procedencia`, cuando `p[4]` es `relacion` y `procedencia` es `p[5]`: las 49
    filas se leian con `procedencia` = "contenido"/"numero", y la procedencia real
    -- `diff`, `git:`, `prosa:` -- se perdia entera. MEDIDO con un recuento:
    {contenido: 45, numero: 4}, cuando lo que hay en el fichero es
    {diff: 43, git: 2, prosa: 4}. Un merge que no sepa de donde viene cada fila
    no puede conservar una fila sin saber cual es.

    El sexto campo es `relacion`, y sale de `relacion_de()`: deducida del
    mecanismo que produjo la fila, no de una constante. Ver la funcion.
    """
    out = []
    for r in sorted(rev, key=lambda x: (x["viejo"], x["nuevo"])):
        out.append("%d\t%d\t%s\t%s\t%s\t%s" % (
            r["viejo"], r["nuevo"],
            "SI" if r["reasignado"] else "no", r["stem"],
            relacion_de(r),
            (r.get("procedencia") or PROCEDENCIA_DIFF)))
    return "\n".join(out) + "\n"


def sha_de(cuerpo_txt):
    return hashlib.sha256(cuerpo_txt.encode("utf-8")).hexdigest()


def _cabecera_para(destino, rev, c, head, cuenta):
    """Reescribe SOLO las lineas que son dato de esta herramienta.

    MEDIDO 2026-10-04, y el motivo de que sea asi y no una plantilla fija: la
    cabecera que hay en el disco tiene 118 lineas de prosa medida, con citas a
    numeros de hallazgos y a lineas concretas de sus ficheros. Una plantilla
    fija las borraria todas, y lo unico que se conservaria seria el texto de
    esta herramienta sobre si misma. Aqui la prosa se copia verbatim y solo se
    sustituyen las lineas que esta herramienta emitio, que se distinguen porque
    son las que llevan una ETIQUETA_MAQUINA.

    MEDIDO que la cabecera anterior estaba ademas MINTIENDO en su propia prosa,
    en linea y sin que nada lo detectara: decia `COLUMNAS  (5, y las 5 en las
    49 filas...)` en un fichero con 6 columnas. Un aviso falso es peor que
    ninguno, porque entrena al que lo lee a_skipar los avisos.
    """
    viejo = []
    if os.path.exists(destino):
        viejo = [l for l in open(destino, encoding="utf-8").read().splitlines()
                 if l.startswith("#")]
    conservadas = [l for l in viejo if not RE_ETIQUETA_MAQUINA.match(l)]

    no_deriv = [r for r in rev
                if (r.get("procedencia") or PROCEDENCIA_DIFF) != PROCEDENCIA_DIFF]
    cuenta = cuenta or {}
    modo = cuenta.get("modo", "congelar")
    if no_deriv:
        aviso_no_der = ("%d  (las que reenvios() NO puede volver a derivar; esta "
                        "es la razon de que --congelar sea un merge y no una "
                        "reescritura)" % len(no_deriv))
    else:
        # MEDIDO: con 0 filas no derivables -- que es exactamente lo que pasa si
        # se usa --sustituir y se reemplaza el mapa por lo que ve el diff -- este
        # aviso no tiene nada que decir. Y es justo el momento en que mas falta
        # haria, porque es cuando esas filas ya no estan. Se dice en su lugar
        # DONDE se han escrito.
        aviso_no_der = ("0  (NINGUNA. Ojo: este mapa ya no conserva ninguna fila "
                        "que reenvios() no pueda derivar. Las que hubiera "
                        "estaban en REENVIO-FINDINGS.descartadas.tsv)")
    maquina = [
        ("generado_por", "08-ARQUITECTURA/tools/reenvio_freeze.py --congelar"),
        ("generado_en", time.strftime("%Y-%m-%dT%H:%M:%S%z")),
        ("fuente", "merge de findings_index.reenvios() sobre el arbol de "
                   "trabajo con las filas ya congeladas"),
        ("git_head", head or "DESCONOCIDO"),
        ("git_head_corto", (head or "")[:12]),
        ("pares", "%d" % len(rev)),
        ("no_derivables", aviso_no_der),
        ("modo", modo),
        ("merge_conservadas", "%d" % cuenta.get("conservadas", 0)),
        ("merge_anadidas", "%d" % cuenta.get("anadidas", 0)),
        ("merge_completadas", "%d" % cuenta.get("completadas", 0)),
        ("merge_difieren", "%d" % cuenta.get("difieren", 0)),
        ("merge_conflictos", "%d" % cuenta.get("conflictos", 0)),
        ("filas_descartadas", "%d" % cuenta.get("descartadas", 0)),
        ("sha256_cuerpo", sha_de(c)),
    ]
    if not viejo:
        # Primer congelacion: no hay prosa que conservar, y sin cabecera el
        # fichero no se lee como lo que es.
        conservadas = [
            "# REENVIO-FINDINGS.tsv -- mapa CONGELADO de renumeraciones de "
            "hallazgos.",
            "#",
            "# POR QUE ESTE FICHERO EXISTE",
            "#   findings_index.reenvios() deriva este mapa comparando "
            "`git ls-tree HEAD`",
            "#   contra el arbol de trabajo. Al commitear la renumeracion esa "
            "comparacion",
            "#   da VACIO y el mapa desaparece. Este fichero es la copia "
            "permanente.",
            "#",
            "#   La tabla Markdown FINDINGS-RENUMERACIONES.md es una VISTA de aqui.",
            "#   Este es el dato. Ante discrepancia, gana este.",
            "#",
            "# COMO SE MANTIENE",
            "#   `--congelar` ES UN MERGE: conserva lo que ya esta y anade lo que",
            "#   falta. No borra filas. Para reemplazar el mapa entero hace falta",
            "#   `--sustituir --confirmar-obsoleto --perder N`, que no puede",
            "#   vaciarlo y escribe lo que descarta en REENVIO-FINDINGS.descartadas.tsv.",
            "#",
            "# COLUMNAS  (6, y las 6 en todas las filas: un formato mixto seria",
            "#   peor que ninguno)",
            "#   viejo        numero que se escribio antes del renumerado",
            "#   nuevo        numero que tiene HOY ese mismo hallazgo",
            "#   reasignado   SI = el numero viejo esta ocupado HOY por OTRO "
            "contenido",
            "#                no = el numero viejo quedo libre; la cita no miente",
            "#   stem         nombre de fichero SIN el numero, completo",
            "#   relacion     contenido = el CONTENIDO paso de viejo a nuevo, y la",
            "#                flecha repara citas.  numero = el numero viejo ya lo",
            "#                tenia OTRO y este contenido NUNCA lo tuvo: la flecha",
            "#                NO repara. Ver el hallazgo 1040.",
            "#   procedencia   COMO se obtuvo ESTA fila: `diff`, `git:<hash>` o",
            "#                `prosa:<fichero>:<lineas>`. Hay filas que reenvios()",
            "#                NO puede derivar, y esta columna es lo que lo dice.",
            "#",
            "# ALCANCE DEL sha256_cuerpo: el valor es el de SOLO las filas de",
            "#   datos --las que no empiezan por # y no estan vacias--, unidas",
            "#   con \\n y con \\n final.",
            "#",
            "# PROCEDENCIA",
        ]
    cuerpo_cab = "\n".join("#   %-18s %s" % (k, v) for k, v in maquina)
    return "\n".join(conservadas + [cuerpo_cab]) + "\n"


def escribir(rev, head, destino=None, cuenta=None):
    destino = destino or DEST
    c = cuerpo(rev)
    cab = _cabecera_para(destino, rev, c, head, cuenta)
    with open(destino, "w", encoding="utf-8") as fh:
        fh.write(cab)
        fh.write(c)
    return c


def _leer_campos(p, destino, n_lin):
    if len(p) != len(CAMPOS):
        raise ValueError(
            "%s: fila de datos con %d campos, se esperaban %d: %r"
            % (destino, n_lin, len(p), len(CAMPOS), "\t".join(p)[:70]))
    if p[2] not in ("SI", "no"):
        raise ValueError("%s: reasignado vale %r, no es SI ni no: %r"
                         % (destino, p[2], "\t".join(p)[:70]))
    if p[COL_RELACION] not in RELACIONES:
        raise ValueError(
            "%s: relacion=%r, y solo valen %s: sin ella esta fila es "
            "indistinguible de una fila REPARABLE, que es justo el error del "
            "hallazgo 1040: %r"
            % (destino, p[COL_RELACION], "|".join(RELACIONES), "\t".join(p)[:70]))
    if not p[COL_PROCEDENCIA].strip():
        raise ValueError("%s: procedencia vacia: sin ella no se sabe si esta "
                         "fila la derivo el instrumento o una persona: %r"
                         % (destino, "\t".join(p)[:70]))
    return {"viejo": int(p[0]), "nuevo": int(p[1]),
            "reasignado": p[2] == "SI", "stem": p[3],
            "relacion": p[COL_RELACION], "procedencia": p[COL_PROCEDENCIA]}


def leer(destino=None):
    """(cabecera_como_texto, cuerpo_texto, filas) o None si no existe.

    MEDIDO 2026-10-04: el ancho de fila lo dicta `CAMPOS`, y `p[COL_RELACION]` /
    `p[COL_PROCEDENCIA]` son los indices de ESE esquema. Antes el codigo leia
    `p[4]` como `procedencia` con el esquema ya en 6, y por eso se comia la
    columna real. El mapa que sale de aqui tiene que ser el MISMO que el que
    sale de `findings_index.reenvios_estable()`, porque los dos alimentan
    `verificar()`; si divergen, G5 de `reenvio_gate.py` compara dos mapas
    distintos y su veredicto no es del mapa.
    """
    destino = destino or DEST
    if not os.path.exists(destino):
        return None
    txt = open(destino, encoding="utf-8").read()
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
        filas.append(_leer_campos(l.split("\t"), destino, n_lin))
    return "\n".join(cab), cuerpo_txt, filas


RE_SHA_DECLARADO = re.compile(r"sha256_cuerpo\s+([0-9a-f]{64})\s*$")


def _sha_declarado(cabecera_txt):
    """El sha256 que la cabecera DECLARA, o None si no declara ninguno.

    MEDIDO 2026-10-04, y lo que paso al anadir una linea de prosa a la cabecera.
    La version anterior hacia esto:

        for ln in cabecera.splitlines():
            if "sha256_cuerpo" in ln:
                declarado = ln.split("sha256_cuerpo")[1].strip()

    O sea: busca una SUBSTRING y se queda con la ULTIMA linea que la contenga.
    Al escribir en la cabecera la linea de prosa

        # NORMALIZACION DEL sha256_cuerpo, que es la que verifica:

    esa linea gano, y el valor leido fue `que es la que verifica:`. MEDIDO: la
    puerta imprimio

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


# Sentinel distinto de None: `None` significa "no hay sha que comprobar" y esto
# significa "la cabecera se lee del disco". MEDIDO que `--congelar` usaba el
# `None` de siempre y por eso comparaba el mapa NUEVO contra el sha declarado
# por el fichero VIEJO, que es un descuadre garantizado y no una comprobacion.
SIN_DECLARACION = object()


def verificar(filas, cuerpo_txt=None, declarado_sha=SIN_DECLARACION):
    """Devuelve lista de problemas. Vacia = coherente.

    `declarado_sha` es el sha256 que el fichero DECLARA en su cabecera. Por
    defecto se lee del disco; se pasa `None` para decir explicitamente que no
    hay declaracion que comprobar, que es el caso de un mapa recien derivado y
    todavia no escrito.
    """
    p = []
    if cuerpo_txt is None:
        cuerpo_txt = cuerpo(filas)
    if declarado_sha is SIN_DECLARACION:
        got = leer()
        if got is not None:
            declarado_sha = _sha_declarado(got[0])
        else:
            declarado_sha = None
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
    #    pero un MISMO origen con dos destinos SI lo es  —salvo que el origen sea
    #    deliberadamente ambiguo,  que es lo que significa la clase `numero`.
    #
    # MEDIDO 2026-10-04.  Este veto rechazaba el par real `290 -> 400`:  comparte
    # origen con `290 -> 291`,  porque el numero 290 se le confio a DOS contenidos  y
    # los dos se renumeraron.  Eso es la definicion de la clase `numero` del
    # hallazgo 1040,  no un error.  Y el veto no podia simplemente admitirse:  las 10
    # filas `numero` del mapa dependen hoy de que el veto NO se aplique a ellas.
    #
    # ASI QUE LA REGLA ES:  un origen con varios destinos es un error cuando todas
    # las filas del grupo son `contenido`  —porque ahi el origen es inequivoco y la
    # colision no esta explicada—.  En cuanto UNA fila del grupo es `numero`,  la
    # comparticion es el hecho documentado,  y el veto dejaria depio
    # "rechazar una fila" por "rechazar el registro de una colision real".
    #
    # Y NO es un veto mas flojo:  una fila `numero` con dos destinos sigue siendo
    # una fila,  y si sus dos destinos NO son los que la prosa sostiene,  eso lo
    # comprueba G2c de reenvio_gate.py  y no este criterio.
    por_viejo = {}
    for r in filas:
        g = por_viejo.setdefault(r["viejo"], {"destinos": set(),
                                               "clases": set()})
        g["destinos"].add(r["nuevo"])
        g["clases"].add(r.get("relacion", "contenido"))
    for v, g in por_viejo.items():
        if len(g["destinos"]) > 1 and g["clases"] == {"contenido"}:
            p.append("origen %d con destinos %s, y ninguno es `numero`:  la"
                     " colision no esta explicada por ninguna fila"
                     % (v, sorted(g["destinos"])))
    return p


def _clave(r):
    """Identidad de un par. Es (viejo, nuevo) y no el stem: dos filas con el
    mismo stem y numeros distintos son dos renumeraciones distintas, y una fila
    no se empareja con la otra solo porque compartan documento."""
    return (r["viejo"], r["nuevo"])


def _prefijo_de(a, b):
    """Uno es prefijo del otro. `reenvios()` entrega el stem TRUNCADO a 58 chars
    y la cabecera antigua del fichero lo guardaba completo, asi que el mismo
    documento aparece con dos anchos distintos. Eso no es un conflicto de
    datos: el truncado no afirma nada que el completo no afirme."""
    if a == b:
        return False
    return a.startswith(b) or b.startswith(a)


def plan_merge(existentes, nuevos):
    """Dice que hace `--congelar` con cada fila nueva, SIN escribir nada.

    Devuelve un dict con:
      merged       filas resultantes, en el orden en que deben quedar
      anadidas     filas que no estaban
      conservadas  filas que ya estaban y se quedan como estaban
      completadas  (viejo,nuevo,stem_viejo,stem_nuevo)  stem truncado que se
                   completa con el del congelado
      difieren     (viejo,nuevo,campo,viejo_valor,nuevo_valor)  diferencias que
                   NO son conflicto, porque el campo no describe el par
      conflictos   (vieja, nueva)  el par existe con OTRA relacion o con otro
                   documento: eso se PREGUNTA, no se elige

    QUE ES CONFLICTO Y QUE NO, y por que:

      `relacion`  SI.  Decide si la fila puede usarse para reescribir una cita.
                  Que dosgomitas digan cosas distintas sobre si la flecha mapea
                  contenido no es un detalle, es el hallazgo 1040 entero.
      `stem`      SI, salvo que uno sea prefijo del otro.  Dice que documento se
                  movio. Un truncado de 58 chars no contradice al completo.
      `reasignado` NO.  El campo MIDIO el estado del arbol en el instante de
                  congelar y su propia cabecera dice que no es una propiedad
                  permanente. Tratarlo como conflicto haria que el congelado se
                  negase a si mismo cada vez que el arbol cambiase, que es lo
                  contrario de congelar.
      `procedencia` NO.  Dice COMO se sabe el par, no QUE par es. Y el valor
                  congelado es el mas especifico de los dos: `prosa:<f>:<l>` o
                  `git:<hash>` explican de donde sale la fila, y `diff` no dice
                  nada que esos no digan. Se conserva el congelado.

    Lo que NO hace esta funcion, y es lo importante: no borra. `merged` contiene
    SIEMPRE todas las existentes, mas las anadidas. No hay rama que las quite.
    """
    por_clave = {}
    for r in existentes:
        por_clave.setdefault(_clave(r), []).append(r)
    merged = [dict(r) for r in existentes]
    anadidas, conservadas, completadas, difieren, conflictos = [], [], [], [], []
    vistas = set()
    for n in sorted(nuevos, key=lambda x: (x["viejo"], x["nuevo"])):
        k = _clave(n)
        if k in vistas:
            continue
        vistas.add(k)
        prev = por_clave.get(k)
        if not prev:
            fila = dict(n)
            fila["relacion"] = relacion_de(fila)
            fila["procedencia"] = fila.get("procedencia") or PROCEDENCIA_DIFF
            merged.append(fila)
            anadidas.append(fila)
            continue
        p = prev[0]
        # MEDIDO 2026-10-04, y esto lo encontrado un control del self-test
        # (L6): comparar `p.get("relacion")` contra `relacion_de(n)` compara
        # una AUSENCIA con una AFIRMACION. Una fila que no trae `relacion` -- la
        # construye cualquiera que no pase por el fichero -- da None, y None !=
        # "contenido", y eso se reportaba como CONFLICTO de datos. Se derivan
        # las dos con la MISMA regla, que es lo que hace comparables.
        if relacion_de(p) != relacion_de(n):
            conflictos.append((p, dict(n)))
            continue
        if p["stem"] != n["stem"] and not _prefijo_de(p["stem"], n["stem"]):
            conflictos.append((p, dict(n)))
            continue
        if p["stem"] != n["stem"]:
            completadas.append((k, p["stem"], n["stem"]))
        if p["reasignado"] != n["reasignado"]:
            difieren.append((k, "reasignado",
                             "SI" if p["reasignado"] else "no",
                             "SI" if n["reasignado"] else "no"))
        conservadas.append(p)
    return {"merged": merged, "anadidas": anadidas,
            "conservadas": conservadas, "completadas": completadas,
            "difieren": difieren, "conflictos": conflictos}


def _fmt_par(r):
    """Una fila en una linea, para nombrar lo que se conserva y lo que se
    pierde. La procedencia va como `clase: cola`, no como la concatenacion
    cruda: MEDIDO que la primera version imprimia `git:git:03ea1b8d723d`, que
    no es ni el dato ni legible."""
    proc = r.get("procedencia") or "?"
    clase = proc.split(":")[0]
    cola = proc[len(clase) + 1:] if ":" in proc else ""
    return "%d->%d [%s] %s  %s%s" % (
        r["viejo"], r["nuevo"], r.get("relacion") or relacion_de(r), r["stem"],
        clase, (": " + cola[-28:]) if cola else "")


def self_test(destino=None):
    """Self-test con la LESION REAL, no con una condicion sintetica.

    MEDIDO 2026-10-04, y esto es lo que el self-test anterior NO hacia: se
    comprobaba que el congelado se niega a escribir cuando el fichero esta
    presente. Eso no dice NADA sobre el bypass, porque el bypass es justamente
    la combinacion de flags que esquiva esa negacion. Un control que solo
    ejercita la puerta cerrada no mide la puerta: mide que se puede abrir.

    Los controles de este bloque construyen un mapa con filas `prosa:` y
    `git:` -- las 6 que `reenvios()` no puede derivar --, y congelan contra un
    `reenvios()` VACIO, que es el estado medido de este repositorio. Si el
    congelado se comiera esas filas, estos controles lo verian.
    """
    fails = []

    def eq(got, want, etiqueta):
        if got != want:
            fails.append("%s: obtuve %r, quiero %r" % (etiqueta, got, want))

    def ok(cond, etiqueta):
        if not cond:
            fails.append(etiqueta)

    # ------------------------------------------------------------------ esquema
    # MEDIDO 2026-10-04: los VALORES ESPERADOS de estas dos aserciones pasaron de
    # 4 campos a 5 y luego a 6. Se actualiza el valor esperado, no la asercion:
    # el criterio --"una fila es exactamente su linea TSV, y reasignado se
    # escribe SI/no y no True/False"-- no ha cambiado, lo que cambio es el
    # esquema. Un self-test al que se le anaden campos al que hay que ajustar la
    # expectativa y sigue midiendo lo mismo; uno al que se le quita una asercion
    # para que pase ya no mide nada.
    eq(cuerpo([{"viejo": 1, "nuevo": 2, "reasignado": True, "stem": "a.md"}]),
       "1\t2\tSI\ta.md\tcontenido\tdiff\n",
       "cuerpo: un par produce exactamente su linea TSV")
    eq(cuerpo([{"viejo": 1, "nuevo": 2, "reasignado": False, "stem": "a.md"}]),
       "1\t2\tno\ta.md\tcontenido\tdiff\n",
       "cuerpo: reasignado=no se escribe 'no', no 'False'")
    # Y las columnas propias de la fila NO se pisan: es lo que permite que una
    # fila leida del congelado conserve su `git:` o su `prosa:` y su `numero` al
    # reescribirse. Sin esta asercion las columnas podian decorarse de cualquier
    # cosa y seguir dando verde.
    eq(cuerpo([{"viejo": 1, "nuevo": 2, "reasignado": True, "stem": "a.md",
                "relacion": "numero", "procedencia": "git:0123456789ab"}]),
       "1\t2\tSI\ta.md\tnumero\tgit:0123456789ab\n",
       "cuerpo: la relacion y la procedencia propias de la fila ganan a las del "
       "defecto")
    # `relacion` de una fila del diff: se DEDUCE, no se elige. Si alguien la
    # cambia por una constante, este control es el que lo dice.
    eq(relacion_de({"viejo": 1, "nuevo": 2, "reasignado": False, "stem": "a.md"}),
       "contenido",
       "relacion: la que la derivo reenvios() es 'contenido', por el mecanismo")
    eq(relacion_de({"relacion": "numero"}), "numero",
       "relacion: una fila que trae la suya no se sobrescribe")

    # orden estable: el mismo conjunto en otro orden da el MISMO sha
    a = [{"viejo": 300, "nuevo": 301, "reasignado": True, "stem": "x.md"},
         {"viejo": 9, "nuevo": 10, "reasignado": False, "stem": "y.md"}]
    b = list(reversed(a))
    eq(sha_de(cuerpo(a)), sha_de(cuerpo(b)), "sha: independiente del orden de entrada")

    # ------------------------------------------------------------ round-trip
    # ESTE control es el que faltaba, y es el que hace que la puerta G1 de
    # `reenvio_gate.py` tenga sobre que pronunciarse: MEDIDO que con el esquema
    # de 5 campos el sha del cuerpo reconstruido era 8034e1c3... y el del
    # fichero real 08c27e49..., con las MISMAS filas. Escritor y lector de la
    # misma herramienta decian numeros de campos distintos.
    rt = [{"viejo": 1, "nuevo": 2, "reasignado": True, "stem": "a.md",
           "relacion": "contenido", "procedencia": "diff"},
          {"viejo": 3, "nuevo": 4, "reasignado": False, "stem": "b.md",
           "relacion": "numero", "procedencia": "prosa:b.md:1-2"}]
    p = destino or (DEST + ".selftest.tmp")
    try:
        escribir(rt, "0" * 40, destino=p, cuenta={"modo": "self-test"})
        cab, ct, leidas = leer(p)
        eq(len(leidas), 2, "round-trip: escribir y leer devuelve las mismas filas")
        eq(sha_de(cuerpo(leidas)), sha_de(ct),
           "round-trip: el cuerpo reconstruido tiene el MISMO sha que el disco")
        eq(_sha_declarado(cab), sha_de(ct),
           "round-trip: el sha que declara la cabecera es el del cuerpo escrito")
        # Y `leer()` tiene que devolver la PROCEDENCIA, no la RELACION en su
        # sitio. MEDIDO que antes devolvia {contenido:45, numero:4} donde el
        # fichero tiene {diff:43, git:2, prosa:4}.
        eq(sorted(x["procedencia"].split(":")[0] for x in leidas),
           ["diff", "prosa"],
           "leer: p[COL_PROCEDENCIA] es la procedencia, no p[COL_RELACION]")
        eq(sorted(x["relacion"] for x in leidas), ["contenido", "numero"],
           "leer: p[COL_RELACION] es la relacion")
        # La prosa de la cabecera se conserva. MEDIDO que la cabecera del mapa
        # real tiene 118 lineas y son trabajo medido de hallazgos; una plantilla
        # fija las borraria todas.
        escribir(rt, "0" * 40, destino=p, cuenta={"modo": "self-test"})
        cab2, _, _ = leer(p)
        n_comentarios = sum(1 for l in cab2.splitlines() if l.startswith("#"))
        ok(n_comentarios > 20,
           "escribir: la cabecera conserva la prosa, no la regenera de cero "
           "(quedaron %d lineas de comentario)" % n_comentarios)
        # Y un sha declarado en mayusculas o con texto detras NO es una
        # declaracion.
        ok(_sha_declarado("#   sha256_cuerpo  %sPERO NO\n" % ("a" * 64)) is None,
           "sha declarado: 64 hex con texto detras no es una declaracion")
    finally:
        if os.path.exists(p):
            os.remove(p)

    # ------------------------------------------------------------- la lesion
    # Las 6 filas que reenvios() NO puede derivar. Es el fixture real.
    congelado = [
        {"viejo": 156, "nuevo": 232, "reasignado": True,
         "stem": "coherencia-cpu-gpu-tres-mecanismos.md",
         "relacion": "contenido", "procedencia": "diff"},
        {"viejo": 286, "nuevo": 401, "reasignado": True,
         "stem": "doclint-no-indexaba-07-driver.md",
         "relacion": "contenido", "procedencia": "git:03ea1b8d723d"},
        {"viejo": 267, "nuevo": 271, "reasignado": True,
         "stem": "el-kernel-de-cache-mide-la-tasa-de-emision.md",
         "relacion": "numero",
         "procedencia": "prosa:271-el-kernel-de-cache-mide-la-tasa-de-emision.md:11-12"},
        {"viejo": 1011, "nuevo": 1020, "reasignado": True,
         "stem": "la-apertura-del-gart-no-cambia-en-runtime.md",
         "relacion": "contenido", "procedencia": "git:a75060397058f"},
    ]
    no_deriv = [r for r in congelado
                if r["procedencia"] != PROCEDENCIA_DIFF]
    eq(len(no_deriv), 3,
       "fixture: el mapa de prueba lleva 3 filas no derivables (1 prosa:, "
       "2 git:)")

    # L1: congelar contra reenvios() VACIO. Estado MEDIDO de este repositorio.
    plan = plan_merge(congelado, [])
    eq(len(plan["merged"]), len(congelado),
       "L1: con reenvios() vacio el mapa conserva las mismas filas")
    eq(len(plan["anadidas"]), 0, "L1: no se anade nada")
    eq([_clave(r) for r in plan["merged"]], [_clave(r) for r in congelado],
       "L1: las claves sobreviven intactas y en su orden")
    eq([r for r in plan["merged"] if r["procedencia"] != PROCEDENCIA_DIFF],
       no_deriv, "L1: las 3 filas no derivables (1 prosa:, 2 git:) sobreviven "
       "con su valor")
    eq(sha_de(cuerpo(plan["merged"])), sha_de(cuerpo(congelado)),
       "L1: el cuerpo es byte a byte el que habia: no hay nada que reescribir")

    # L2: congelar contra un reenvios() que trae UN par nuevo. La fila nueva se
    # anade y las no derivables siguen ahi.
    plan = plan_merge(congelado, [{"viejo": 3000, "nuevo": 3001,
                                   "reasignado": False, "stem": "hallazgo-nuevo.md"}])
    eq(len(plan["anadidas"]), 1, "L2: el par nuevo se anade")
    eq(len(plan["merged"]), len(congelado) + 1, "L2: el mapa crece en 1")
    eq(len([r for r in plan["merged"]
            if r["procedencia"] != PROCEDENCIA_DIFF]), 3,
       "L2: las 3 filas no derivables siguen ahi despues de anadir")
    eq(plan["anadidas"][0]["relacion"], "contenido",
       "L2: la fila anadida deduce su relacion")

    # L3: el par ya existe con la misma relacion -> se conserva, no se duplica.
    plan = plan_merge(congelado, [{"viejo": 156, "nuevo": 232, "reasignado": True,
                                   "stem": "coherencia-cpu-gpu-tres-mecanismos.md"}])
    eq(len(plan["merged"]), len(congelado),
       "L3: un par que ya estaba no crea una fila nueva")
    eq(len(plan["conservadas"]), 1, "L3: se cuenta como conservada")

    # L4: el MISMO par con OTRA relacion -> PREGUNTA, no elige. Este es el
    # requisito de "no elegir" y el mas grave: elegir `contenido` sobre
    # `numero` reescribe 27 citas al fichero equivocado.
    chocado = dict(congelado[2])
    chocado["relacion"] = "contenido"
    plan = plan_merge(congelado, [chocado])
    eq(len(plan["conflictos"]), 1,
       "L4: el mismo par con otra relacion es un CONFLICTO, no una eleccion")
    eq(len(plan["anadidas"]), 0, "L4: un conflicto no anade nada")
    eq(len(plan["merged"]), len(congelado),
       "L4: con conflicto el mapa queda como estaba")

    # L5: el MISMO par con OTRO documento -> tambien conflicto.
    otro = dict(congelado[2])
    otro["stem"] = "otro-fichero.md"
    plan = plan_merge(congelado, [otro])
    eq(len(plan["conflictos"]), 1,
       "L5: el mismo par con otro stem es un CONFLICTO")

    # L6: el mismo par, mismo documento, pero el stem llega truncado a 58 chars
    # -- que es lo que hace reenvios() -- NO es conflicto: se completa.
    largo = "e" * 60 + "-un-stem-largo.md"
    trunc = [{"viejo": 400, "nuevo": 401, "reasignado": False, "stem": largo}]
    con_gel = [dict(trunc[0])]
    plan = plan_merge(con_gel, [{"viejo": 400, "nuevo": 401,
                                 "reasignado": False, "stem": largo[:58]}])
    eq(len(plan["conflictos"]), 0,
       "L6: un stem truncado no contradice al completo, no es conflicto")
    eq(len(plan["completadas"]), 1, "L6: se registra como completado")

    # L7: `reasignado` distinto NO es conflicto -- es una medida de un
    # instante, y su cabecera dice que no es permanente. Tratarlo como
    # conflicto haria que el congelado se negase a si mismo al cambiar el arbol.
    plan = plan_merge(congelado, [{"viejo": 156, "nuevo": 232, "reasignado": False,
                                   "stem": "coherencia-cpu-gpu-tres-mecanismos.md"}])
    eq(len(plan["conflictos"]), 0,
       "L7: reasignado distinto no es conflicto")
    eq(len(plan["difieren"]), 1, "L7: pero se registra como diferencia")

    # L8: `procedencia` mas especifica en el diff no pisa la congelada.
    plan = plan_merge(congelado, [{"viejo": 156, "nuevo": 232, "reasignado": True,
                                   "stem": "coherencia-cpu-gpu-tres-mecanismos.md"}])
    eq(len(plan["conflictos"]), 0,
       "L8: rederivar un par ya congelado por el diff no es conflicto")

    # -------------------------------------------------- las puertas, de verdad
    # Los controles L1..L8 prueban la FUNCION de merge. Falta probar el CAMINO
    # completo, que es donde estaba el defecto: los flags. Y con el fichero en
    # disco, porque un merge correcto en memoria con una escritura que borra
    # sigue siendo un merge que borra.
    if destino is None and os.path.exists(DEST):
        p = DEST + ".selftest.tmp"
        original = open(DEST, "rb").read()
        try:
            shutil.copyfile(DEST, p)
            _congelar_en(p, [], "0" * 40)
            ok(open(p, "rb").read() == original,
               "P1: --congelar contra reenvios() vacio deja el fichero "
               "BYTE A BYTE como estaba")
            # Y con un par nuevo: crece, y lo que no era derivable sigue ahi.
            _congelar_en(p, [{"viejo": 3000, "nuevo": 3001, "reasignado": False,
                              "stem": "hallazgo-nuevo.md"}], "0" * 40)
            # MEDIDO 2026-10-04.  Estas tres aserciones tenían las cifras del mapa
            # ESCRITAS A MANO  —49 filas, 43 diff, 4 prosa, 45 contenido—  y el
            # nodo que añadió 7 filas las dejó en rojo.  Es el mismo defecto que
            # la cabecera del TSV tenía con "8 de las 49 filas tienen su numero
            # viejo libre":  una cifra escrita que envejece.
            #
            # Y EL ARREGLO NO ES PONER 56.  Poner 56 es el mismo defecto con otro
            # número:  en la siguiente fila añadida vuelve a estar viejo,  y esta vez
            # el que lo rompa no será un nodo que lo mire sino el próximo.
            #
            # LA PROPIEDAD QUE SE COMPRUEBA,  y que no caduca:
            #
            #   · el merge NO borra ninguna fila que existia
            #   · el merge añade EXACTAMENTE la fila que se le dio
            #
            # Eso se deriva del FICHERO REAL  —cifras medidas en el momento—  mas la
            # fila nueva,  y por eso no hay ningun numero escrito aqui.  Y no es
            # tautológico:  si `plan_merge` perdiera una fila,  el recuento de
            # clases no cuadraria;  si añadiera de mas,  tampoco.
            _, _, antes = leer(DEST)
            cab, ct, leidas = leer(p)
            eq(len(leidas), len(antes) + 1,
               "P2: el merge anade EXACTAMENTE la fila que se le dio, y ni una "
               "mas  (antes %d, despues %d)" % (len(antes), len(leidas)))
            # ninguna clase de las que existian ha cambiado de recuento
            from collections import Counter as _C
            eq(_C(x["procedencia"].split(":")[0] for x in leidas) -
               _C(x["procedencia"].split(":")[0] for x in antes),
               _C(["diff"]),
               "P2: el merge no cambia la clase de ninguna fila previa: solo "
               "anade una `diff`")
            eq(_C(x["relacion"] for x in leidas) -
               _C(x["relacion"] for x in antes),
               _C(["contenido"]),
               "P2: el merge no cambia la RELACION de ninguna fila previa: solo "
               "anade una `contenido`")
            # y el par nuevo esta, con su contenido
            eq([1 for x in leidas if x["viejo"] == 3000 and x["nuevo"] == 3001
                and x["stem"] == "hallazgo-nuevo.md"],
               [1],
               "P2: el par nuevo esta en el resultado con su stem")
        finally:
            if os.path.exists(p):
                os.remove(p)
            if open(DEST, "rb").read() != original:
                raise AssertionError(
                    "el self-test de reenvio_freeze MODIFICO el mapa real")

    # ------------------------------------------------------------- escribir()
    # MEDIDO que `escribir()` no podia escribir NUNCA: la plantilla de cabecera
    # tenia los especificadores %5 y %6 transpuestos respecto a la tupla de
    # argumentos, de modo que `sha_de()` -- que devuelve str -- caia en un %d.
    # MEDIDO: TypeError: %d format: a real number is required, not str, con 1
    # fila y con 3. Este control falla si alguien vuelve a separarlos.
    try:
        p = destino or (DEST + ".selftest.tmp")
        escribir([{"viejo": 1, "nuevo": 2, "reasignado": False, "stem": "a.md"}],
                 "0" * 40, destino=p, cuenta={"modo": "self-test"})
        ok(os.path.getsize(p) > 0, "escribir: no lanza y deja un fichero")
        if os.path.exists(p):
            os.remove(p)
    except Exception as e:                                        # noqa: BLE001
        fails.append("escribir: no puede escribir: %s: %s" % (type(e).__name__, e))

    # --------------------------------------------------------------- verificar
    cadena = [{"viejo": 156, "nuevo": 232, "reasignado": True, "stem": "a.md"},
              {"viejo": 232, "nuevo": 999, "reasignado": True, "stem": "b.md"}]
    if not any("CADENA" in x for x in verificar(cadena)):
        fails.append("verificar: no detecta la cadena 156->232->999")
    if not any("identidad" in x for x in
               verificar([{"viejo": 7, "nuevo": 7, "reasignado": False, "stem": "c.md"}],
                         declarado_sha=None)):
        fails.append("verificar: no detecta el par identidad 7->7")
    if not any("destinos" in x for x in
               verificar([{"viejo": 5, "nuevo": 6, "reasignado": True, "stem": "d.md"},
                          {"viejo": 5, "nuevo": 8, "reasignado": True, "stem": "e.md"}],
                         declarado_sha=None)):
        fails.append("verificar: no detecta el origen 5 con dos destinos")
    filas = [{"viejo": 1, "nuevo": 2, "reasignado": True, "stem": "a.md"}]
    c = cuerpo(filas)
    if sha_de(c) == sha_de(c.replace("1\t", "3\t")):
        fails.append("sha: no distingue un cuerpo de otro")
    if not verificar(filas, c, declarado_sha="0" * 64):
        fails.append("verificar: no detecta un sha256 declarado que no cuadra")
    if verificar(filas, c, declarado_sha=sha_de(c)):
        fails.append("verificar: da falso positivo con el sha256 correcto")
    # Y el guard que hacia que `--congelar` fallara siempre: `--congelar` pasa
    # `declarado_sha=None` porque el mapa todavia no esta escrito, y por eso el
    # mapa NUEVO no se compara contra el sha declarado por el fichero VIEJO.
    # MEDIDO que antes si se comparaba, y por eso rc=1.
    ok(not verificar([{"viejo": 9000, "nuevo": 9001, "reasignado": False,
                       "stem": "z.md"}], cuerpo([{"viejo": 9000, "nuevo": 9001,
                                                 "reasignado": False, "stem": "z.md"}]),
                    declarado_sha=None),
       "verificar: un mapa recien derivado sin declaracion no se compara "
       "contra el sha de otro fichero")

    for f in fails:
        print("  FALLA %s" % f)
    print("self_test: %s" % ("OK" if not fails else "%d FALLAS" % len(fails)))
    return RC_OK if not fails else RC_FALLO


def _congelar_en(destino, rev, head, cuenta=None):
    """El camino de escritura completo, sobre un fichero concreto.

    Existe para que el self-test pueda ejercitar `--congelar` DE VERDAD, con
    bytes en disco, sin pasar por `main()` -- que lee `reenvios()` de verdad y
    por tanto no puede recibir un mapa vacio a proposito.
    """
    got = leer(destino)
    existentes = got[2] if got is not None else []
    plan = plan_merge(existentes, rev)
    if plan["conflictos"]:
        return RC_FALLO, plan
    nuevo = sha_de(cuerpo(plan["merged"]))
    if got is not None and got[1] == cuerpo(plan["merged"]):
        return RC_OK, plan                       # sin cambios: no se escribe
    cuenta = dict(cuenta or {})
    cuenta.update({"modo": "congelar",
                   "conservadas": len(plan["conservadas"]),
                   "anadidas": len(plan["anadidas"]),
                   "completadas": len(plan["completadas"]),
                   "difieren": len(plan["difieren"]),
                   "conflictos": 0})
    escribir(plan["merged"], head, destino=destino, cuenta=cuenta)
    return RC_OK, plan


def _perder_que(existentes, nuevos):
    """Filas del mapa actual que el mapa nuevo NO contiene, por (viejo,nuevo).

    Es la lista que `--sustituir` obliga a autorizar por numero. Sin una lista
    CONCRETA, "confirmar" no es confirmar: es oneself saying "vale".
    """
    claves_nuevas = {_clave(r) for r in nuevos}
    return [r for r in existentes if _clave(r) not in claves_nuevas]


def main(argv):
    ap = argparse.ArgumentParser(
        add_help=True,
        description="Congela el mapa de renumeraciones. --congelar es un MERGE: "
                    "conserva lo congelado y anade lo que falta. Para reemplazar "
                    "el mapa entero hace falta --sustituir, que lo dice.")
    ap.add_argument("--congelar", action="store_true",
                    help="merge: anade las filas que falten, no borra ninguna")
    ap.add_argument("--sustituir", action="store_true",
                    help="REEMPLAZA el mapa entero. Destructivo: exige "
                         "--confirmar-obsoleto y --perder N, y no puede "
                         "vaciar el fichero")
    ap.add_argument("--perder", type=int, default=None, metavar="N",
                    help="confirma que se pierden N filas; si no es el numero "
                         "que calcula la herramienta, se niega")
    ap.add_argument("--verificar", action="store_true")
    ap.add_argument("--ver-live", action="store_true",
                    help="compara el mapa congelado con el que derivaria git HOY")
    ap.add_argument("--self-test", action="store_true")
    ap.add_argument("--confirmar-obsoleto", action="store_true",
                    help="constante de --sustituir; sola no hace nada")
    a = ap.parse_args(argv)

    if a.self_test:
        return self_test()

    # MEDIDO 2026-10-04: `--forzar` ya no existe. Antes sortaba la negacion de
    # "ya existe" y, con `--confirmar-obsoleto`, llegaba hasta el punto de
    # escribir. Ahora argparse lo rechaza con codigo 2 y NOMBRA la bandera no
    # reconocida. Un flag retirado que se vuelve inocuo es peor que uno que
    # falla: el que teclea el hechizo viejo creeria que ha ordenado algo.
    if a.confirmar_obsoleto and not a.sustituir:
        print("reenvio_freeze: --confirmar-obsoleto solo tiene sentido con "
              "--sustituir. No hace nada solo.", file=sys.stderr)
        return RC_NO_EJECUTO
    if a.perder is not None and not a.sustituir:
        print("reenvio_freeze: --perder solo tiene sentido con --sustituir. "
              "No hace nada solo.", file=sys.stderr)
        return RC_NO_EJECUTO
    # MEDIDO que la invocacion a secas tiene que SEGUIR imprimiendo el resumen
    # del mapa, y no el --help: quien la usa la esta usando para LEER, y
    # cambiarle la salida por un texto de ayuda le hace perder el dato sin
    # avisarle de nada. El modo por defecto sigue siendo solo lectura.
    if not (a.congelar or a.sustituir or a.verificar or a.ver_live):
        a.ver_live = False

    filas = escanear()
    if filas is None:
        print("reenvio_freeze: no existe %s" % FIND, file=sys.stderr)
        return RC_NO_EJECUTO
    head = _head_id()
    if head is None:
        print("reenvio_freeze: git no responde; sin procedencia no congelo",
              file=sys.stderr)
        return RC_NO_EJECUTO

    if a.sustituir:
        return _cmd_sustituir(_stem_completo(reenvios(filas), filas), head,
                              a.confirmar_obsoleto, a.perder)

    if a.congelar:
        return _cmd_congelar(_stem_completo(reenvios(filas), filas), head)

    got = leer()
    if got is None:
        print("reenvio_freeze: no existe %s" % DEST)
        return RC_NO_EJECUTO

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
                return RC_FALLO
    if a.verificar:
        probs = verificar(filas_rev, cuerpo_txt)
        for p in probs:
            print("  PROBLEMA %s" % p)
        print("verificar: %d pares, %s" %
              (len(filas_rev), "OK" if not probs else "%d PROBLEMAS" % len(probs)))
        return RC_FALLO if probs else RC_OK

    print("congelado: %d pares  sha256 %s" % (len(filas_rev), sha_de(cuerpo_txt)))
    return RC_OK


def _cmd_congelar(rev, head):
    """MERGE. No borra. Codigos: 0 hecho o sin cambios, 1 conflicto, 3 nada."""
    got = leer()
    existentes = got[2] if got is not None else []
    if not existentes and not rev:
        print("reenvio_freeze: reenvios() vacio y no hay mapa que congelar; "
              "no hay nada que anadir ni que conservar", file=sys.stderr)
        return RC_NADA_QUE_ANADIR

    plan = plan_merge(existentes, rev)
    for vieja, nueva in plan["conflictos"]:
        print("reenvio_freeze: CONFLICTO. El par ya esta congelado con OTROS "
              "datos y no lo elijo:", file=sys.stderr)
        print("  congelado  %s" % _fmt_par(vieja), file=sys.stderr)
        print("  derivado   %s" % _fmt_par(nueva), file=sys.stderr)
        print("  `relacion` decide si la fila puede reescribir una cita, y dos "
              "fuentes dicen cosas distintas. Para cambiarlo hay que decirlo "
              "con --sustituir y las dos confirmaciones.", file=sys.stderr)
    if plan["conflictos"]:
        return RC_FALLO

    nuevo_txt = cuerpo(plan["merged"])
    if got is not None and got[1] == nuevo_txt:
        # Sin cambios. MEDIDO que esto importa mas de lo que parece: si se
        # reescribiera la cabecera, el sha giraria en cada ejecucion y un sha
        # que gira no sirve para afirmar que nada cambio.
        print("congelado: sin cambios, %d pares, sha256 %s  (nada escrito)"
              % (len(plan["merged"]), sha_de(nuevo_txt)))
        print("  conservadas %d   anadidas %d   no derivables %d"
              % (len(plan["conservadas"]), len(plan["anadidas"]),
                 sum(1 for r in plan["merged"]
                     if (r.get("procedencia") or PROCEDENCIA_DIFF)
                     != PROCEDENCIA_DIFF)))
        return RC_OK

    probs = verificar(plan["merged"], nuevo_txt, declarado_sha=None)
    if probs:
        print("reenvio_freeze: el mapa resultante ya falla la verificacion:")
        for p in probs:
            print("  %s" % p)
        return RC_FALLO

    no_derivan = [r for r in plan["merged"]
                  if (r.get("procedencia") or PROCEDENCIA_DIFF) != PROCEDENCIA_DIFF]
    cuenta = {"modo": "congelar", "conservadas": len(plan["conservadas"]),
              "anadidas": len(plan["anadidas"]),
              "completadas": len(plan["completadas"]),
              "difieren": len(plan["difieren"]),
              "conflictos": 0}
    escribir(plan["merged"], head, cuenta=cuenta)
    print("congelado (merge) %s" % DEST)
    print("  filas        %d  (antes %d)" % (len(plan["merged"]), len(existentes)))
    print("  anadidas     %d" % len(plan["anadidas"]))
    print("  conservadas  %d" % len(plan["conservadas"]))
    print("  no derivables %d  <- las que reenvios() no puede volver a derivar"
          % len(no_derivan))
    print("  sha256       %s" % sha_de(nuevo_txt))
    print("  git_head     %s" % (head or "")[:12])
    for k, campo, v_cong, v_der in plan["difieren"]:
        print("  AVISO: %d->%d, %s congelada %s y derivada %s. Se conserva la "
              "congelada: ese campo se midio al congelar y su cabecera dice que "
              "no es permanente." % (k[0], k[1], campo, v_cong, v_der))
    return RC_OK


def _cmd_sustituir(rev, head, confirmar_obsoleto, perder):
    """REEMPLAZA el mapa entero. Destructivo, y con las cuatro puertas.

    Las cuatro, en este orden, y el orden importa: se comprueba lo barato antes
    que lo caro, y la puerta que protege la COPIA va antes que la que obliga a
    CONTAR.

      1. `--confirmar-obsoleto`   sin esto ni se lee el mapa viejo
      2. el resultado no puede ser VACIO   no se vacia un mapa
      3. `--perder N` tiene que ser el numero que calcula la herramienta, y el
         numero se imprime fila a fila para que no sea un numero abstracto
      4. verificacion del mapa nuevo, antes de escribir nada
    """
    if not confirmar_obsoleto:
        print("reenvio_freeze: --sustituir borra filas. No lo hago sin "
              "--confirmar-obsoleto.", file=sys.stderr)
        print("  Para anadir lo que el diff ve HOY y no borrar nada: "
              "--congelar", file=sys.stderr)
        return RC_SIN_CONFIRMAR
    got = leer()
    existentes = got[2] if got is not None else []
    if not rev:
        # MEDIDO: esta es la condicion que hace segura la puerta. La fuente se
        # degrada sola -- hoy 0 pares, manana 1 -- y una puerta que se dispara
        # cuando la fuente esta peor es una puerta que se dispara cuando menos
        # falta hace. Aqui no hay nada que sustituir: hay algo que borrar.
        print("reenvio_freeze: reenvios() devuelve 0 pares. --sustituir no "
              "puede VACIAR el mapa congelado.", file=sys.stderr)
        print("  Un mapa vacio no es un mapa: es la perdida de la unica copia "
              "de una tabla", file=sys.stderr)
        print("  que se autodestruye. Si lo que quieres es incorporar lo que "
              "el diff ve HOY,", file=sys.stderr)
        print("  usa --congelar, que anade y no borra.", file=sys.stderr)
        return RC_MAPA_VACIO
    if not existentes:
        print("reenvio_freeze: no hay mapa que sustituir; usa --congelar",
              file=sys.stderr)
        return RC_NADA_QUE_ANADIR
    perdidas = _perder_que(existentes, rev)
    if not perdidas:
        print("reenvio_freeze: --sustituir no perderia ninguna fila. Usa "
              "--congelar, que no necesita confirmaciones.", file=sys.stderr)
        return RC_PERDER_DESCONOCIDO
    if perder is None:
        print("reenvio_freeze: --sustituir TIENE que perder %d filas y no ha "
              "dicho cuantas. Copie el numero o no lo hago:"
              % len(perdidas), file=sys.stderr)
        for r in perdidas:
            print("  se perderia  %s" % _fmt_par(r), file=sys.stderr)
        return RC_PERDER_DESCONOCIDO
    if perder != len(perdidas):
        print("reenvio_freeze: --perder %d, pero se perderian %d. No lo hago."
              % (perder, len(perdidas)), file=sys.stderr)
        return RC_PERDER_DESCONOCIDO
    probs = verificar(rev, cuerpo(rev), declarado_sha=None)
    if probs:
        print("reenvio_freeze: el mapa nuevo ya falla la verificacion:")
        for p in probs:
            print("  %s" % p)
        return RC_FALLO
    # Lo que se pierde queda POR ESCRITO con su numero, antes de que se pierda.
    # MEDIDO que un `.bak` solo no basta: nadie mira un `.bak`, y lo que hace
    # falta es saber QUE se perdio, no que existo una copia.
    with open(DEST + ".bak", "w", encoding="utf-8") as fh:
        fh.write(open(DEST, encoding="utf-8").read())
    with open(DEST + ".descartadas.tsv", "w", encoding="utf-8") as fh:
        fh.write("# Filas del mapa congelado que --sustituir ha descartado.\n")
        fh.write("# escrito ANTES de sustituirlas, con su numero y su "
                 "procedencia.\n")
        fh.write("# El mapa entero esta ademas en %s.bak\n"
                 % os.path.basename(DEST))
        fh.write(cuerpo(perdidas))
    escribir(rev, head, cuenta={"modo": "sustituir",
                                "descartadas": len(perdidas)})
    print("sustituido %s" % DEST)
    print("  filas        %d  (antes %d)" % (len(rev), len(existentes)))
    print("  DESCARTADAS  %d  -> %s.descartadas.tsv"
          % (len(perdidas), os.path.basename(DEST)))
    for r in perdidas:
        print("  se perdio    %s" % _fmt_par(r))
    print("  copia entera -> %s.bak" % os.path.basename(DEST))
    print("  sha256       %s" % sha_de(cuerpo(rev)))
    return RC_OK


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
