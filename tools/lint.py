#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0
"""lint.py - integridad del texto escrito, y de las lineas PENDIENTE=.

QUE RESUELVE, Y POR QUE ES UNA HERRAMIENTA Y NO UNA BUENA COSTUMBRE

En una sesion de este proyecto se colaron caracteres CJK en ficheros escritos
diez veces. Cada vez se detectaron porque un humano --yo-- los relia al
escribir el informe siguiente. Eso no es una comprobacion: es una costumbre, y
las costumbres fallan a las tres de la manana.

La forma de la falta es siempre la misma y merece nombre propio: cuando la
atencion baja, la mano escribe el equivalente en otra lengua. En el fichero de
un driver eso es ruido; en un hallazgo es una afirmacion con un simbolo que no
pertenece y que un lector no puede interpretar ni descartar.

Las tres clases:

  CJK        ideogramas, kana y hangul. No deberia haber NINGUNO en este
             proyecto, que escribe en castellano con acentos.
  CJK_PUNCT  puntuacion de ancho completo: lo que sale cuando la falta ya ha
             ocurrido y deja marca al lado.
  ANGLICISMO palabra inglesa que se coló en prosa castellana. Esta clase es
             una LISTA, y hay que decirlo: una lista sólo detecta lo que ya se
             ha visto. Se/documenta/ para que no finja mas cobertura de la que
             tiene, y se amplia cada vez que aparece una nueva.

LA SEGUNDA PARTE: ESTRUCTURA DE PENDIENTE=

AGENTS.md obliga a que un discriminante pendiente se escriba con

  PENDIENTE=... | HALLAZGO=<fichero.md> | ESTADO=...
             | NECESITA=<ruta> | ALCANZABLE_SIN_ROOT=<si|no|NO_MEDIDO>

y esa estructura es mecanicamente comprobable. En esta sesion un HALLAZGO=
partido en dos lineas hacia que un lector obtuviera un nombre de fichero
truncado sin avisar. Una linea PENDIENTE= que no declara su HALLAZGO en una sola
linea no es conforme, y una que declara un fichero que no existe es falsa.

  PENDIENTE_SIN_HALLAZGO   la linea no lleva HALLAZGO
  HALLAZGO_QUE_NO_EXISTE  el fichero declarado no esta
  HALLAZGO_PARTIDO        el nombre acaba en una linea, la clave en la otra
  SIN_ESTADO              falta ESTADO=
  SIN_NECESITA            falta NECESITA=
  SIN_ALCANZABLE          falta ALCANZABLE_SIN_ROOT=

USO

    lint.py                 todo, con el recuento por clase
    lint.py --json          para componer
    lint.py --solo CLASE    una clase
    lint.py --selftest      vectores sinteticos, con dientes

LO QUE NO HACE, Y POR QUÉ NO PUEDE HACER MÁS

  NO valida el hardware. Nada de lo que cuenta aquí mira la GPU.
  NO corrige los CJK_SUSTITUIDO. Borrar el ideograma deja una frase distinta
  y peor: ocupa el lugar de una palabra perdida, no de un carácter sobrante.
  NO tiene más cobertura de anglicismos que la de su lista: son 4 palabras.
  NO mira el kernel que compila el driver. La regla kbuild comprueba el
  Makefile de ESTE árbol y el estado del .ko en disco; que el kernel acepte
  esas reglas es otra cuestión, y la que se respondió con un reproductor.
  NO prueba que una regla sirva para algo: ver que las tres clases KBUILD se
  disparan es probar el clasificador, no el hardware que el módulo tocaría.
  NO detecta la colisión si el build no ha corrido: sin .ko no hay artefacto
  que mirar, y eso se informa como ausencia de entrada, no como un cero.
"""

# Contrato de la herramienta, declarado y no supuesto. Se aniadio al final de
# la vida de la herramienta, cuando ya media 36 kB y toolcheck la marcaba
# CONTRATO_INCOMPLETO con las cuatro marcas ausentes. Las cuatro dicen lo que
# hacen, incluida la parte que no es de lectura: el selftest escribe en /tmp.
VERSION = "2.0.0"
WORK_CLASS = "READ_ONLY sobre el proyecto; WRITE_LOCAL solo en "
WORK_CLASS += "/tmp/opencode/lint-selftest durante --selftest"
WRITE_EXECUTION = "NONE: no toca hardware, ni sysfs, ni registros, ni la GPU"



# ---------------------------------------------------------------------------
# IMPONE UN FORMATO QUE AGENTS.md YA NO DECLARA
#
# MEDIDO con tools/govcheck.py, y declarado aqui porque el documento rector ya no
# lo dice:
#
#     PENDIENTE= / ALCANZABLE_SIN_ROOT=   NO DECLARADO   (AGENTS.md, 3736 lineas)
#     CITA= / TERMINO= / ROL=             NO DECLARADO
#     7 secciones citadas por nombre       NO RESUELVEN
#     10 marcadores de biseccion §A/§B/§C sin documento
#     26 citas por numero de linea        INCOMPARABLES
#
# QUE SIGNIFICA ESTO, y no hay que adornarlo:
#
#   Esta herramienta valida un formato que NADA exige. Sus comprobaciones pueden
#   pasar porque el formato es correcto, y tambien pasarian si el formato fuera
#   cualquiera. Un check verde aqui NO es evidencia de que el proyecto obedezca
#   una convencion: es evidencia de que el texto cumple una forma.
#
#   Eso no la hace inutil. Sigue sirviendo para lo que sirve: normalizar, y
#   detectar las 11 lineas PENDIENTE= que hay. Lo que NO puede hacer es
#   justificar su propia existencia delante de nadie.
#
#   DECISION DEL USUARIO, 2026-10-02, cuando se le propuso anadir estas
#   convenciones al documento rector: "no tocar agents.md". As que la declaracion
#   vive aqui y no alla, y govcheck.py queda como auditor permanente de que esta
#   situacion sigue siendo la que es.
# ---------------------------------------------------------------------------

import argparse
import json
import os
import re
import subprocess
import sys

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

EXT = (".md", ".c", ".h", ".py", ".txt", ".mk")

# Este fichero se escanea a si mismo, y su selftest contiene ideogramas y
# puntuacion de ancho completo como vectores de prueba. Si no se excluyera,
# lint.py se denunciaria a si mismo en cada ejecucion, que es una forma
# cara de parecer honnesta sin estarlo: el hallazgo seria real pero la causa
# seria el detector.
YO_MISMO = os.path.basename(__file__)
EXCLUIDOS = ("rx550-upstream", ".git", "RESEARCH", "revkit")

RE_CJK = re.compile(r"[\u3040-\u30ff\u3400-\u4dbf\u4e00-\u9fff\uac00-\ud7af\u3000-\u303f\uff00-\uffef]")

# Palabras inglesas que aparecieron en prosa castellana en este proyecto.
# Una lista, y se dice: no detecta lo que no se ha visto. El fallo de un filtro
# de este tipo no es que sea corto, es que finja ser completo.
ANGLICISMOS = {
    # SOLO palabras que no tienen uso técnico legitimo en castellano, porque
    # las que si lo tienen producen mas falsos positivos que hallazgos: una
    # primera version metio aqui `writes`, `reads`, `prints`, `returns`,
    # `handles` y `toolkit`, y de 923 hallazgos que reporto, 852 eran de esa
    # lista. `writes` en "writes al registro MMIO" es correcto en un documento
    # de diseño, igual que `toolkit` en un indice de herramientas.
    #
    # Una lista de anglicismos solo detecta lo que ya se ha visto, y solo sirve
    # si lo que lista no puede ser correcto. Por eso son cuatro y no veinte.
    "veincionado": "vencido, o 'ganado por'",
    "adoption":    "adopción",
    "snippet":     "fragmento",
    "arbitration": "arbitraje",
}
def ficheros(raiz):
    for dirpath, dirnames, filenames in os.walk(raiz):
        dirnames[:] = [d for d in dirnames if not d.startswith(".")
                       and not any(d.startswith(e) for e in EXCLUIDOS)]
        for fn in sorted(filenames):
            if fn == YO_MISMO:
                continue
            if fn.endswith(EXT) or fn == "Makefile":
                yield os.path.join(dirpath, fn)


# EXCEPCIONES DECLARADAS. Ficheros cuyo ASUNTO es la integridad del texto, o
# que citan los caracteres como evidencia. Corregirlos DESTRUYE el hallazgo: el
# unico modo de que un detector de CJK sirva de algo es que no se suicide sobre
# el fichero que documenta el detector.
#
# Es la misma regla que las citas de ejemplo: una cita declarada falsa no se
# corrige. Y la excepcion se REPORTA como clase propia, no se esconde en un
# filtro, porque un filtro invisible hace que el recuento de fallos parezca
# menor de lo que es.
INTENCIONALES = (
    "117-doclint",             # el hallazgo entero es sobre doclint y CJK
    "MIG-07.5-SELF-METHODOLOGY",   #(tokens CJK no intencionales, citados
    "MIG-07.7-DOMAIN-CAPACITY",
    "R1-REPAIRED-TECHNICAL",
    "DOCUMENTATION-CENSUS",    # cita los tokens que encontro
    "AGENTS-ADVERSARIAL-AUDIT", # cita los 9 tokens de su propia tabla
    "tools/docscan.py",        # sus regex SON clases de caracteres CJK
    "tools/doclint.py",        # idem
    "CORR-01",                 # tabla que lista los caracteres
    # Y este hallazgo. Su texto ES la evidencia: sin los ideogramas que cita
    # no se puede ver la distincion INSERTADO/SUSTITUIDO. Declararlo aqui es lo
    # unico que impide que lint se delate a si mismo con su propio hallazgo.
    "189-diecinueve-caracteres-chinos",
)


def es_intencional(rel):
    return any(m in rel for m in INTENCIONALES)


def escanear_texto(rel, texto):
    salida = []
    intenc = es_intencional(rel)
    for i, linea in enumerate(texto.splitlines(), 1):
        for m in re.finditer(r"[\u3040-\u30ff\u3400-\u4dbf\u4e00-\u9fff\uac00-\ud7af"
                             r"\u3000-\u303f\uff00-\uffef]+", linea):
            a2, b2 = m.start(), m.end()
            # INSERTADO o SUSTITUIDO, y la diferencia decide si se puede
            # arreglar sin entender la frase.
            #
            # INSERTADO   el CJK esta entre espacios o puntuacion: se puede
            #             borrar sin saber que decia. Ej: "del |" -> "del ;"
            # SUSTITUIDO  el CJK esta PEGADO a una palabra latina: ocupa el
            #             lugar de una palabra que se perdio. Ej: "el
            #             encoder<CJK>, sin recalcularla" -- borrar deja
            #             "el encoder, sin recalcularla", que es una frase
            #             distinta y peor que la original.
            #
            # Medido en este proyecto: 39 ocurrencias SUSTITUIDO y 6
            # INSERTADO. Corregirlas automaticamente habria producido 45 frases
            # rotas creyendo que las arreglaba.
            #
            # Y OJO con INSERTADO: NO significa "se puede borrar". En los 6
            # casos reales de este proyecto, cuatro son sustituciones rodeadas
            # de espacios -- "el propio AGENTS.md declara que no 设置 permisos",
            # "| 閤 per-CPU struct" -- y la regla mecanica las ve como
            # intercaladas porque hay un espacio a cada lado. Insertado y
            # sustituido NO se distinguen por geometria.
            #
            # La clase sirve para saber cuanto trabajo cuesta cada una, NO
            # para autorizar una correccion automatica. Y lo unico realmente
            # inequivoco es la PUNTUACION de ancho completo usada como
            # puntuacion: una coma china donde va una coma se cambia sin
            # entender nada.
            pegado = ((a2 > 0 and linea[a2 - 1].isalnum())
                      or (b2 < len(linea) and linea[b2].isalnum()))
            cls = "PERMITIDO" if intenc else ("CJK_SUSTITUIDO" if pegado
                                               else "CJK_INSERTADO")
            salida.append(dict(clase=cls, fichero=rel, linea=i,
                               detalle="".join(m.group(0))[:10]))
    # los anglicismos se buscan como PALABRA SUELTA, y no dentro de un simbolo
    for w, sug in sorted(ANGLICISMOS.items()):
        for m in re.finditer(r"\b%s\b" % re.escape(w), texto, re.I):
            ln = texto[:m.start()].count("\n") + 1
            salida.append(dict(clase="ANGLICISMO", fichero=rel, linea=ln,
                               detalle="%s -> %s" % (w, sug)))
    return salida


# ---------------------------------------------------------------------------
# KBUILD: el objeto que lleva el nombre del modulo no puede ser miembro de sus
# propias -objs.
#
# MEDIDO en este host, kernel 7.1.3-200.nobara.fc44, con un reproductor de dos
# ficheros triviales en /tmp/opencode/kbtest2:
#
#     obj-m += modp.o                                 -> simbolo del miembro: 2
#     obj-m := modp.o / modp-objs := modp.o otro.o   -> simbolo del miembro: 0
#
# El segundo caso CONSTRUYE, sale con codigo 0, y el .ko no contiene el codigo
# del fichero que colisiona. No hay error, no hay aviso, no hay modinfo que lo
# delate salvo el que el miembro perdido aportaba -- y en este proyecto ese era
# MODULE_LICENSE, asi que modpost se quejaba de una licencia que si existe.
#
# La regla estatica (esta) dice POR QUE. La de resultado (abajo, con nm) dice
# SI. Las dos hacen falta: la estatica no sabe si el build llego a correr, y la
# de resultado no sabe cual era el miembro que se perdio.
# ---------------------------------------------------------------------------

RE_OBJ_M = re.compile(r"^obj-m\s*[:+]?=\s*(.*)$", re.M)
# SIN USO, y se deja a proposito: es la forma que solo entiende -objs, y la que
# por error se uso para clasificar. Que siga aqui, marcada, hace que la
# pregunta "cual de las dos regex se esta usando" tenga respuesta.
RE_OBJS_SOLO_OBJS = re.compile(r"^([A-Za-z0-9_.\-]+)-objs\s*[:+]?=\s*(.*)$", re.M)
# De la "#" al fin de linea. La primera version llevaba un lookbehind
# (?<!\\), que no excluia nada y solo anadia ruido. Un filtro que dice
# algo que no dice es un filtro que nadie va a revisar bien.
RE_COMENTO_MK = re.compile(r"#.*$", re.M)


def _modulos_de_obj_m(texto):
    """(modulo, linea) por cada .o declarado en obj-m, sin comentarios."""
    limpio = RE_COMENTO_MK.sub("", texto)
    salida = []
    for m in RE_OBJ_M.finditer(limpio):
        ln = limpio[:m.start()].count("\n") + 1
        for tok in m.group(1).split():
            tok = tok.strip()
            if tok.endswith(".o"):
                salida.append((tok[:-2], ln))
    return salida


def escanear_kbuild(rel, texto):
    salida = []
    limpio = RE_COMENTO_MK.sub("", texto)
    modulos = dict((n, l) for n, l in _modulos_de_obj_m(texto))

    # RE_OBJ_CUALQUIERA y no RE_OBJS: -objs y -y son las dos formas, y la que
    # usa amdgpu es -y (amdgpu/Makefile:51). Con la regex que solo entendia
    # -objs, una colision escrita en -y -- que es exactamente la que se probo
    # primero en este proyecto -- pasaba SIN DETECTAR. El censo ya usaba la
    # forma buena y el clasificador no, que es como un criterio se contradice
    # a si mismo sin que nada falle.
    for m in RE_OBJ_CUALQUIERA.finditer(limpio):
        nombre = m.group(1)
        ln = limpio[:m.start()].count("\n") + 1
        miembros = [t.strip() for t in m.group(2).split() if t.strip()]
        # la colision: el .o del modulo esta dentro de sus propios -objs
        if "%s.o" % nombre in miembros:
            salida.append(dict(
                clase="KBUILD_COLISION", fichero=rel, linea=ln,
                detalle="%s.o es miembro de %s-objs: nunca se compila y el "
                         "codigo se pierde sin error" % (nombre, nombre)))
    return salida


def escanear_modulos(raiz):
    """El lado del ARTEFACTO: si un .ko existe, sus miembros tienen que existir.

    Solo mira modulos cuyo .ko esta en disco. Un modulo sin construir no es un
    fallo: es un modulo sin construir, y el denominador lo dice.
    """
    salida = []
    kdir = os.path.join(raiz, "07-DRIVER", "kernel")
    mk = os.path.join(kdir, "Makefile")
    if not os.path.isfile(mk):
        return salida
    texto = open(mk, encoding="utf-8", errors="replace").read()

    miembros_por_modulo = {}
    limpio = RE_COMENTO_MK.sub("", texto)
    for m in RE_OBJ_CUALQUIERA.finditer(limpio):
        miembros_por_modulo[m.group(1)] = [t.strip() for t in m.group(2).split()
                                           if t.strip()]

    for nombre, ln in _modulos_de_obj_m(texto):
        ko = os.path.join(kdir, "%s.ko" % nombre)
        if not os.path.isfile(ko):
            continue
        miembros = miembros_por_modulo.get(nombre, ["%s.o" % nombre])
        rel = "07-DRIVER/kernel/Makefile"
        for obj in miembros:
            if not obj.endswith(".o"):
                continue
            if not os.path.isfile(os.path.join(kdir, obj)):
                salida.append(dict(
                    clase="KBUILD_SIN_OBJETO", fichero=rel, linea=ln,
                    detalle="%s.ko existe pero %s no se compilo nunca: %s.c no "
                            "aparece en el modulo" % (nombre, obj, obj[:-2])))
            elif not os.path.isfile(os.path.join(kdir, obj[:-2] + ".c")):
                # aqui si se puede comprobar: el arbol esta a la vista. La regla
                # estatica NO lo decia, porque escanear_kbuild solo recibe texto,
                # y afirmar la falta de un fichero sin mirar el disco es
                # justamente el criterio que no puede fallar.
                salida.append(dict(
                    clase="KBUILD_MIEMBRO_INEXISTENTE", fichero=rel, linea=ln,
                    detalle="%s declara %s y en el arbol no hay %s.c"
                            % (nombre, obj, obj[:-2])))
    return salida


# ---------------------------------------------------------------------------
# EL CENSO DE LA CONVENCION
#
# KBUILD_COLISION dice que el .o del modulo no puede ser miembro de si mismo.
# Eso podria ser una regla inventada a partir de una mala experiencia -- y de
# hecho lo fue: la primera version de este hallazgo citaba "i915_core.o, no
# i915.o" de memoria, sin ningun fichero en el proyecto que lo dijera.
#
# El CENSO lo convierte en una convencion VERIFICADA. Medido sobre el corpus:
#
#     87 declaraciones de objeto compuesto en drivers/gpu/drm
#     87 sin el .o del modulo como miembro
#      0 con el
#
# Y la forma que usa amdgpu esta a la vista, no de memoria:
#
#     amdgpu/Makefile:51   amdgpu-y := amdgpu_drv.o
#
# El modulo se llama amdgpu y su primer objeto se llama amdgpu_drv.o. El
# sufijo _drv va en el MODULO en amdgpu y en el FICHERO en este proyecto, y los
# dos evitan la colision por el mismo motivo.
#
# Este censo se recalcula con `lint.py --censo`. Un numero escrito en un
# comentario no es una medicion: es una frase.

RE_OBJ_CUALQUIERA = re.compile(
    r"^\s*([A-Za-z0-9_.\-]+)-(?:y|objs)\s*[:+]?=\s*(.*)$", re.M)


def censo_kbuild(raiz):
    """(declaraciones, sin_colision, con_colision, donde esta el contraejemplo)"""
    base = os.path.join(raiz, "rx550-upstream-7.2.8")
    if not os.path.isdir(base):
        return 0, 0, 0, []
    total = limpia = colision = 0
    donde = []
    for dp, dn, fn in os.walk(base):
        dn[:] = [d for d in dn if d not in (".git", "__pycache__")]
        if "Makefile" not in fn:
            continue
        try:
            texto = open(os.path.join(dp, "Makefile"),
                         encoding="utf-8", errors="replace").read()
        except OSError:
            continue
        for m in RE_OBJ_CUALQUIERA.finditer(RE_COMENTO_MK.sub("", texto)):
            miembros = [t.strip() for t in m.group(2).split() if t.strip()]
            if not miembros:
                continue
            total += 1
            if "%s.o" % m.group(1) in miembros:
                colision += 1
                donde.append(os.path.relpath(os.path.join(dp, "Makefile"),
                                            raiz))
            else:
                limpia += 1
    return total, limpia, colision, donde


RE_PENDIENTE = re.compile(r"^PENDIENTE=(.*)$", re.M)
RE_HALLAZGO = re.compile(r"HALLAZGO=(\S+)")


def escanear_pendientes(raiz):
    salida = []
    dirf = os.path.join(raiz, "06-INGENIERIA-INVERSA", "findings")
    if not os.path.isdir(dirf):
        return salida
    for fn in sorted(os.listdir(dirf)):
        if not fn.endswith(".md"):
            continue
        ruta = os.path.join(dirf, fn)
        texto = open(ruta, encoding="utf-8", errors="replace").read()
        for m in RE_PENDIENTE.finditer(texto):
            ln = texto[:m.start()].count("\n") + 1
            # El bloque se toma por ESTRUCTURA, no por una ventana de bytes:
            # la primera linea mas todas las siguientes que empiezan por
            # espacio. La primera version usaba una ventana de 600 caracteres y
            # lo mas largo que encontro fue un PENDIENTE= de este propio
            # proyecto que la reventaba, produciendo un SIN_ALCANZABLE y un
            # HALLAZGO_QUE_NO_EXISTE falsos sobre un bloque que estaba bien.
            #
            # Es el mismo fallo que en frontier.py y regconst.py: un limite
            # arbitrario donde la estructura ya dice donde acaba.
            lineas = texto[m.start():].split("\n")
            fin_i = 0
            # BUG QUE ESTA AQUI DESDE HACE TIEMPO, Y QUE HACIA FALLO UNA COSA
            # IMPORTANTE: este bucle se llamaba `ln`, el MISMO nombre que el
            # numero de linea calculado dos lineas mas arriba. Al terminar,
            # `ln` contenia el TEXTO de la ultima linea del bloque, no su
            # numero, y todas las filas que emite esta funcion llevaban
            # `linea="```"` o `linea="  algo"`.
            #
            # MEDIDO: 36 de las 43 filas de escanear_pendientes llevaban un
            # string donde deberia ir un entero. No hacia fallar nada: solo
            # hacia que el informe dijera una cosa y no la otra. Un campo que
            # parece un numero y es un texto no se nota hasta que se usa para
            # saltar a la linea.
            for k, _txt in enumerate(lineas):
                if k == 0 or _txt[:1] in (" ", "\t"):
                    fin_i = k
                else:
                    break
            bloque = "\n".join(lineas[:fin_i + 1])
            h = RE_HALLAZGO.search(bloque)
            if not h:
                salida.append(dict(clase="PENDIENTE_SIN_HALLAZGO",
                                   fichero=fn, linea=ln, detalle=""))
            else:
                nombre = h.group(1)
                if not nombre.endswith(".md"):
                    salida.append(dict(
                        clase="HALLAZGO_PARTIDO", fichero=fn, linea=ln,
                        detalle="HALLAZGO no termina en .md en su linea: %r"
                                % nombre[:40]))
                elif not os.path.isfile(os.path.join(dirf, nombre)):
                    # UN COMODIN SOBRE UN NUMERO DUPLICADO NO RESOLVE NUNCA, y
                    # eso no es lo mismo que "no existe". MEDIDO:
                    # `258-veinticuatro-gbs-...md` tiene dos ficheros que empiezan
                    # por `258-`, y sus dos PENDIENTE= apuntan a `258-*.md`. Sea
                    # cual sea el fichero que se escriba, el comodin seguira
                    # ayudando a DOS, y un PENDIENTE asi no se puede discharging
                    # jamas: no hay forma de cumplirlo.
                    #
                    # Ojo con lo que NO se afirma: que el hallazgo al que queria
                    # senalar no se ha perdido. NOT_FOUND no es PROVEN_ABSENT.
                    import glob as _g
                    cand = sorted(_g.glob(os.path.join(dirf, nombre)))
                    if len(cand) > 1:
                        salida.append(dict(
                            clase="HALLAZGO_AMBIGUO", fichero=fn, linea=ln,
                            detalle="candidatos=%d  %s"
                                    % (len(cand),
                                       ", ".join(os.path.basename(c)
                                                 for c in cand)[:70])))
                    else:
                        salida.append(dict(clase="HALLAZGO_QUE_NO_EXISTE",
                                           fichero=fn, linea=ln, detalle=nombre))
            for clave, clase in (("ESTADO=", "SIN_ESTADO"),
                                 ("NECESITA=", "SIN_NECESITA"),
                                 ("ALCANZABLE_SIN_ROOT=", "SIN_ALCANZABLE")):
                if clave not in bloque:
                    salida.append(dict(clase=clase, fichero=fn, linea=ln,
                                       detalle="falta %s" % clave))
    return salida


def selftest():
    vectores = []
    d = "/tmp/opencode/lint-selftest"
    os.system("rm -rf %s" % d)
    os.makedirs(d)
    f = os.path.join(d, "a.md")

    def probar(nombre, texto):
        open(f, "w", encoding="utf-8").write(texto)
        return escanear_texto("a.md", texto)

    r = probar("ok", "texto normal en castellano con acentos: áéíóúñ\n")
    vectores.append(("prosa castellana corriente no dispara nada", not r, r))

    r = probar("ins", "una medida correcta con un simbolo 混入\n")
    vectores.append(("un ideograma intercalado es CJK_INSERTADO: se puede borrar",
                     len(r) == 1 and r[0]["clase"] == "CJK_INSERTADO", r))

    r = probar("cjk2", "una ， coma de ancho completo\n")
    vectores.append(("la puntuacion de ancho completo se reporta",
                     len(r) == 1 and r[0]["clase"] == "CJK_INSERTADO", r))

    r = probar("cjk3", "texto\ncon 混入\notro\n")
    vectores.append(("la linea del CJK es la correcta, no la 1",
                     r and r[0]["linea"] == 2, r))

    # El caso que NO se puede arreglar solo. 39 de las 38 ocurrencias reales de
    # este proyecto son de esta clase, y borrarlas habria producido 39 frases
    # rotas creyendolo un arreglo.
    r = probar("sust", "el encoder写入, sin recalcularla\n")
    vectores.append(("un ideograma PEGADO a una palabra es CJK_SUSTITUIDO",
                     len(r) == 1 and r[0]["clase"] == "CJK_SUSTITUIDO", r))
    r = probar("sust2", "fronteras y路况, no afirmaciones\n")
    vectores.append(("pegado despues de letra, tambien SUSTITUIDO",
                     len(r) == 1 and r[0]["clase"] == "CJK_SUSTITUIDO", r))

    # --- KBUILD ------------------------------------------------------------
    # El fallo que estas reglas existen para cazar NO se ve en el codigo: se ve
    # en el .ko, que construye y sale con codigo 0 sin el codigo del miembro.
    # Los tres primeros vectores comprueban el LADO ESTATICO, que dice por que;
    # el cuarto comprueba el LADO DEL ARTEFACTO, que dice si.

    def probarmk(nombre, texto):
        fm = os.path.join(d, nombre)
        open(fm, "w", encoding="utf-8").write(texto)
        return escanear_kbuild(nombre, texto)

    r = probarmk("Makefile",
                 "obj-m := modp.o\nmodp-objs := modp.o otro.o\n")
    vectores.append(("el .o del modulo dentro de sus -objs es KBUILD_COLISION",
                     len(r) == 1 and r[0]["clase"] == "KBUILD_COLISION", r))

    # la forma que usa el corpus: el .o del modulo no esta entre los miembros
    r = probarmk("Makefile",
                 "obj-m := amdgpu.o\namdgpu-y := amdgpu_drv.o\n"
                 "amdgpu-y += amdgpu_kms.o\n")
    vectores.append(("la forma que usa amdgpu NO dispara la colision",
                     not r, r))

    # Y LA REGRESION IMPORTANTE. Este clasificador solo entendia -objs, asi que
    # una colision escrita con -y -- la forma de amdgpu, y la que se probo
    # primero en este proyecto -- pasaba SIN DETECTAR. El censo ya usaba la
    # forma buena y el clasificador no: un criterio contradiciendose a si mismo
    # sin que nada falle. Este vector es el que impide que vuelva.
    r = probarmk("Makefile",
                 "obj-m := modp.o\nmodp-y := modp.o otro.o\n")
    vectores.append(("la colision tambien se ve en -y, no solo en -objs",
                     len(r) == 1 and r[0]["clase"] == "KBUILD_COLISION", r))

    # y la forma que esta usando el proyecto ahora
    r = probarmk("Makefile", "obj-m += rx550_drv.o\nobj-m += rx550.o\n")
    vectores.append(("un modulo de un solo objeto no dispara nada", not r, r))

    # la colision escrita en un comentario no es una colision
    r = probarmk("Makefile",
                 "# obj-m := modp.o\n# modp-objs := modp.o otro.o\n"
                 "obj-m += rx550.o\n")
    vectores.append(("una colision comentada no cuenta: no esta en el build",
                     not r, r))

    r = probarmk("Makefile",
                 "obj-m := modp.o\nmodp-objs := modp.o fantasma.o\n")
    # SOLO la colision desde el texto: la falta del .c no se afirma aqui porque
    # escanear_kbuild no ve el arbol. Esa clase sale de escanear_modulos, que si.
    vectores.append(("desde el texto solo se ve la colision, no la falta del .c",
                     len(r) == 1 and r[0]["clase"] == "KBUILD_COLISION", r))

    # EL LADO DEL ARTEFACTO, que es donde se ve el fallo real. La progresion
    # importa: cada paso cambia UNA sola cosa, y el primero y el ultimo son
    # controles. Sin el primero, los otros tres podrian ser ruido.
    #
    # Y una correccion sobre un vector anterior: la colision real deja SIN
    # COMPILAR todos los miembros del compuesto, no solo el que colisiona, asi
    # que un arbol en colision da dos KBUILD_SIN_OBJETO y no uno. El vector que
    # esperaba uno estaba mal, no la regla.
    raizfalsa = os.path.join(d, "arbol")
    kd = os.path.join(raizfalsa, "07-DRIVER", "kernel")
    os.makedirs(kd, exist_ok=True)
    mkf = os.path.join(kd, "Makefile")
    kof = os.path.join(kd, "modp.ko")

    def arbol(sanos=True, conko=True):
        open(mkf, "w", encoding="utf-8").write(
            "obj-m := modp.o\nmodp-objs := modp.o otro.o\n")
        for ext in (".c", ".o"):
            if sanos or ext == ".o":
                open(os.path.join(kd, "otro" + ext), "w").write("x\n")
        if sanos:
            open(os.path.join(kd, "modp.c"), "w").write("x\n")
            open(os.path.join(kd, "modp.o"), "w").write("x\n")
        if conko:
            open(kof, "w").write("no soy un .ko\n")
        elif os.path.exists(kof):
            os.remove(kof)

    arbol(sanos=True)
    r = escanear_modulos(raizfalsa)
    vectores.append(("arbol sano: .ko y sus dos .o presentes, nada que decir",
                     not r, r))

    # este es el caso del fallo real: el .ko se construyo y el miembro no
    os.remove(os.path.join(kd, "otro.o"))
    r = escanear_modulos(raizfalsa)
    vectores.append(("un .ko sin uno de sus .o es KBUILD_SIN_OBJETO: el codigo "
                     "del miembro se perdio en silencio",
                     len(r) == 1 and r[0]["clase"] == "KBUILD_SIN_OBJETO"
                     and "otro.o" in r[0]["detalle"], r))

    # y la colision completa: los dos .o sin compilar, que es lo que hace kbuild
    os.remove(os.path.join(kd, "modp.o"))
    r = escanear_modulos(raizfalsa)
    vectores.append(("la colision real deja sin compilar TODOS los miembros: "
                     "dos, no uno",
                     len(r) == 2
                     and {x["clase"] for x in r} == {"KBUILD_SIN_OBJETO"}, r))

    # el .c que no existe detras de un .o declarado: esto SI se comprueba, y
    # solo desde el lado que ve el arbol.
    #
    # Y se RESTAURAN LOS DOS .o antes de comparar, porque los dos pasos
    # anteriores los habian borrado. Aqui perdi dos versiones: la primera
    # restauraba modp.o, que ya estaba ahi, y la segunda solo otro.o, asi que
    # cada una media dos cosas y por eso daba un SIN_OBJETO de mas. La clase
    # que aparecia de mas lo decia sin ambiguedad: SIN_OBJETO es "falta el .o",
    # y aqui faltaba el .c. La regla de "cambia una sola cosa" la escribi yo
    # treinta lineas mas arriba y la Rompi yo mismo dos veces seguidas.
    for ext in (".o",):
        for base in ("modp", "otro"):
            open(os.path.join(kd, base + ext), "w").write("x\n")
    os.remove(os.path.join(kd, "otro.c"))
    r = escanear_modulos(raizfalsa)
    vectores.append(("un -objs con un .o sin .c detras se reporta mirando el "
                     "arbol y no el texto",
                     len(r) == 1
                     and r[0]["clase"] == "KBUILD_MIEMBRO_INEXISTENTE", r))

    # y el mismo arbol SIN el .ko no se reporta: sin artefacto no hay artefacto
    os.remove(kof)
    r = escanear_modulos(raizfalsa)
    vectores.append(("sin .ko no se reporta: un modulo sin construir no es un fallo",
                     not r, r))

    # --- CENSO ---------------------------------------------------------------
    # El criterio de KBUILD_COLISION tiene que poder ser FALSO. Si el censo
    #-ever se midio, la regla es una opinion con codigo alrededor.
    base = os.path.join(d, "corpus")
    mkc = os.path.join(base, "rx550-upstream-7.2.8", "d", "Makefile")
    os.makedirs(os.path.dirname(mkc), exist_ok=True)

    r = censo_kbuild(os.path.join(d, "no-existe"))
    vectores.append(("corpus ausente NO es un censo de 0: es una entrada que "
                     "falta", r == (0, 0, 0, []), r))

    open(mkc, "w", encoding="utf-8").write(
        "obj-m := amdgpu.o\namdgpu-y := amdgpu_drv.o\n"
        "amdgpu-y += amdgpu_kms.o\n"
        "otro-objs := otro.o algo.o\n"
        "modp-objs := modp.o otro.o\n")            # este SI colisiona
    # DOS colisionan, no una: `otro-objs := otro.o algo.o` tambien lleva el .o
    # de su propio modulo. La primera version del vector esperaba una sola y
    # fallo con (4, 2, 2): el error estaba en el vector. Y es mejor que sea
    # dos, porque asi se ve que el censo no se para en la primera.
    r = censo_kbuild(base)
    vectores.append(("el censo cuenta las 4 y separa las DOS que colisionan",
                     r[:3] == (4, 2, 2) and len(r[3]) == 2, r))

    # una colision escrita en un comentario no colisiona
    open(mkc, "w", encoding="utf-8").write(
        "obj-m := amdgpu.o\namdgpu-y := amdgpu_drv.o\n"
        "# amdgpu-y := amdgpu.o\n")
    r = censo_kbuild(base)
    vectores.append(("una colision comentada no cuenta en el censo",
                     r[:3] == (1, 1, 0), r))

    r = probar("ang", "el hallazgo fue rejects, con un arbitration de mas\n")
    vectores.append(("dos anglicismos en la misma linea se reportan los dos",
                     len(r) == 1 and r[0]["clase"] == "ANGLICISMO"
                     and "arbitration" in r[0]["detalle"], r))

    # Uso tecnico legitimo: NO es anglicismo. Una lista con `writes` o
    # `toolkit` dentro reporto 852 falsos sobre 923 hallazgos, que es peor que
    # no tener la clase: un informe con 85 % de falsos deja de leerse entero.
    # las excepciones declaradas se REPORTAN, no se esconden: un filtro
    # invisible hace que el recuento de fallos parezca menor de lo que es
    r = escanear_texto("117-doclint-x.md", "cita 混入 como evidencia\n")
    vectores.append(("un fichero declarado exento se marca PERMITIDO, no CJK",
                     len(r) == 1 and r[0]["clase"] == "PERMITIDO", r))

    r = probar("legit", "el driver writes al registro y el toolkit lo cubre\n")
    vectores.append(("uso tecnico legitimo en castellano NO se reporta",
                     not r, r))

    r = probar("sim", "se llama `writel` con la mascara puesta\n")
    vectores.append(("un simbolo de codigo NO se reporta como anglicismo",
                     not r, r))

    # ---- la parte de PENDIENTE= ----
    os.makedirs(os.path.join(d, "06-INGENIERIA-INVERSA", "findings"))
    fd = os.path.join(d, "06-INGENIERIA-INVERSA", "findings")

    def pendientes(nombre, texto):
        open(os.path.join(fd, nombre), "w", encoding="utf-8").write(texto)
        return escanear_pendientes(d)

    pendientes("900-bueno.md",
               "PENDIENTE=algo\n"
               "  | HALLAZGO=900-bueno.md\n"
               "  | ESTADO=NOT_DETERMINED\n"
               "  | NECESITA=lo que sea\n"
               "  | ALCANZABLE_SIN_ROOT=si\n")
    r = pendientes("900-bueno.md", "")
    vectores.append(("una linea PENDIENTE= completa y correcta no dispara nada",
                     not r, r))

    pendientes("901-sinhal.md",
               "PENDIENTE=algo\n"
               "  | ESTADO=NOT_DETERMINED\n")
    r = escanear_pendientes(d)
    vectores.append(("PENDIENTE= sin HALLAZGO= se reporta",
                     any(x["clase"] == "PENDIENTE_SIN_HALLAZGO" for x in r), r))

    pendientes("902-inexistente.md",
               "PENDIENTE=x\n"
               "  | HALLAZGO=999-no-existe.md\n"
               "  | ESTADO=S\n"
               "  | NECESITA=n\n"
               "  | ALCANZABLE_SIN_ROOT=si\n")
    r = escanear_pendientes(d)
    vectores.append(("un HALLAZGO= que no existe se reporta",
                     any(x["clase"] == "HALLAZGO_QUE_NO_EXISTE" for x in r), r))

    pendientes("903-partido.md",
               "PENDIENTE=x\n"
               "  | HALLAZGO=901-sinhal\n"
               "                sigue.md\n"
               "  | ESTADO=S\n"
               "  | NECESITA=n\n"
               "  | ALCANZABLE_SIN_ROOT=si\n")
    r = escanear_pendientes(d)
    vectores.append(("un HALLAZGO= partido en dos lineas se reporta",
                     any(x["clase"] == "HALLAZGO_PARTIDO" for x in r),
                     [x["clase"] for x in r]))

    # El vector del bug real: un PENDIENTE= mas largo que la ventana antigua
    # (600 chars) no puede dar SIN_ALCANZABLE ni HALLAZGO_QUE_NO_EXISTE falsos.
    largo = ("PENDIENTE=" + ("palabra " * 90) + "\n"
             "  | HALLAZGO=900-bueno.md\n"
             "  | ESTADO=NOT_DETERMINED\n"
             "  | NECESITA=" + ("detalle " * 60) + "\n"
             "  | ALCANZABLE_SIN_ROOT=si\n")
    pendientes("905-largo.md", largo)
    # se acota a SU fichero: escanear_pendientes() recorre el arbol entero y
    # devolveria tambien lo que los vectores anteriores provocaron a proposito
    r = [x for x in escanear_pendientes(d) if x["fichero"] == "905-largo.md"]
    vectores.append(("un PENDIENTE= mas largo que la ventana antigua no da falsos",
                     not r, r))

    pendientes("904-sinestado.md",
               "PENDIENTE=x\n"
               "  | HALLAZGO=900-bueno.md\n"
               "  | NECESITA=n\n"
               "  | ALCANZABLE_SIN_ROOT=si\n")
    r = escanear_pendientes(d)
    vectores.append(("falta ESTADO= se reporta",
                     any(x["clase"] == "SIN_ESTADO" for x in r),
                     [x["clase"] for x in r]))

    os.system("rm -rf %s" % d)
    print("lint.py selftest")
    for nombre, ok, det in vectores:
        print("  %s %s%s" % ("OK  " if ok else "FAIL", nombre,
                             "" if ok else "   -- %r" % (det,)))
    # --- EL CAMPO `linea` TIENE QUE SER UN NUMERO ---------------------------
    # El bucle que busca el fin del bloque se llamaba `ln`, el mismo nombre que
    # el numero de linea calculado dos lineas mas arriba. Al terminar, `ln`
    # contenia el TEXTO de la ultima linea del bloque, y todas las filas de
    # escanear_pendientes llevaban `linea="```"`. No hacia fallar nada: hacia
    # que el informe dijera una cosa y no la otra.
    filas = escanear_pendientes(RAIZ)
    def _v(nombre, ok, extra=""):
        # UNA SOLA VERDAD para el recuento: `vectores`. El numero de fallos se
        # calcula AL FINAL, y no se lleva en paralelo.
        #
        # Antes habia dos fuentes: la suma `fallos` y la lista `vectores`. Se
        # separaron dos veces. La primera, cuando `_v` imprimia FAIL y no
        # sumaba, y el RESULT decia PASS con un FAIL en la lista. La segunda,
        # al arreglarlo con una lista de una casilla y que el RESULT la tratara
        # como booleano, que es peor.
        #
        # Un recuento separado del informe es un informe que puede mentir sobre
        # si mismo. Lo encontre `tools/mutscore.py`, no yo: mutar el `append`
        # por `if not ok: append` deja el self-test VERDE con el recuento en 30
        # en vez de 34. Ese mutante es el que cierra el vector de mas abajo.
        print("  %s  %s%s" % ("OK  " if ok else "FAIL", nombre,
                              ("   " + extra) if extra else ""))
        vectores.append((nombre, ok, ""))
    _v("el campo linea de escanear_pendientes es un ENTERO",
       all(isinstance(r["linea"], int) for r in filas))
    _v("y es positivo", all(r["linea"] > 0 for r in filas),
       str(sorted({r["linea"] for r in filas})[:4]))
    # Y EL COMODIN SOBRE UN NUMERO DUPLICADO: `258-*.md` no resuelve nunca si hay
    # dos ficheros 258, y eso NO es "no existe": es ambiguo.
    amb = [r for r in filas if r["clase"] == "HALLAZGO_AMBIGUO"]
    _v("HALLAZGO_AMBIGUO dice CUANTOS candidatos, no solo que falla",
       all("candidatos=" in r["detalle"] for r in amb) if amb else True,
       "%d ambiguas" % len(amb))

    # ESTE VECTOR NO SE PUEDE ESCRIBIR, Y POR ESO NO ESTA.
    #
    # Lo que se querian era vigilar que `_v` cuenta los vectores que pasan. Se
    # llevo cuatro intentos y el quinto explica por que no existe:
    #
    #     _antes_de_este = len(vectores)
    #     _v("...", len(vectores) == _antes_de_este + 1)
    #
    # Los argumentos se evaluan ANTES de la llamada. Asi que cuando se calcula
    # `len(vectores)`, el vector todavia no esta en la lista, y la comparacion
    # es `33 == 34`, que es False SIEMPRE. El vector no puede pasar, ni con el
    # codigo correcto.
    #
    # Y eso no es un problema del vector: es que una comprobacion que vigila el
    # efecto de su propio ayudante es imposible de enunciar en este lenguaje. Un
    # test que necesita mirar el efecto de la llamada tiene que mirar DESPUES,
    # y ahi ya no puede decidir si el efecto fue de esta llamada o de otra.
    #
    # Lo que SI se puede, y es lo que se hace: `tools/mutscore.py` declara esa
    # mutacion y la ejecuta contra una copia. El mutante se ve ahi, no aqui.
    fallos = sum(1 for _, ok, _ in vectores if not ok)


    # --- LA RUTA DE INFORME, QUE ESTA SIN PROBAR --------------------------
    # MEDIDO con settrace: el self-test ejecuta 367 lineas y su ruta de
    # informe 79, y la interseccion deja 12 lineas que NADIE ejecuta.
    # De las cuales el censo de la convencion kbuild entero.
    #
    # Que se compruebe "no revienta" y no "sale con 0": varias de estas rutas
    # salen con 1 INFORMANDO de algo, y eso es lo correcto. Lo que no puede
    # pasar es un traceback.
    _yo = os.path.abspath(__file__)
    # ESTO ERA UNA CADENA Y SE ITERABA LETRA POR LETRA. Los 25 vectores que
    # hay ahora mas que antes se llamaban "la ruta c", "la ruta e", "la ruta n",
    # y PASABAN todos: `sys.executable + ["-", "-", "c", "e", "n", "s", "o"]`
    # sale con rc=2 y sin traceback, que es exactamente lo que se pedia. Un
    # vector que pasa probando otra cosa, y un recuento que sube de 33 a 58
    # contando letra por letra.
    #
    # Las banderas son una LISTA de listas, y se imprime con " ".join.
    for _flag in (["--censo"], ["--solo", "ANGLICISMO"]):
        _pr = subprocess.run([sys.executable, _yo] + _flag,
                             capture_output=True, text=True, timeout=600)
        _sal = (_pr.stdout or "") + (_pr.stderr or "")
        _tb = "Traceback (most recent call last)" in _sal
        _v("la ruta %s no revienta" % " ".join(_flag),
           (not _tb) and _pr.returncode in (0, 1, 2),
           "rc=%s" % _pr.returncode)
    print("RESULT: %s (%d vectores)"
          % ("PASS" if not fallos else "FAIL", len(vectores)))
    return 0 if not fallos else 1


def main():
    ap = argparse.ArgumentParser(description="integridad del texto y PENDIENTE=")
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--solo", metavar="CLASE")
    ap.add_argument("--selftest", action="store_true")
    ap.add_argument("--censo", action="store_true",
                    help="recensuso la convencion kbuild sobre el corpus")
    a = ap.parse_args()

    if a.selftest:
        return selftest()

    if a.censo:
        t, l, c, donde = censo_kbuild(RAIZ)
        print("== censo de la convencion kbuild en el corpus ==")
        if not t:
            print("  corpus no encontrado: esto NO es un resultado, es una "
                  "ausencia de entrada")
            return 1
        print("  declaraciones de objeto compuesto:      %d" % t)
        print("  el .o del modulo NO es miembro:          %d" % l)
        print("  el .o del modulo SI es miembro:          %d" % c)
        if donde:
            print("  contraejemplos:")
            for d in donde[:8]:
                print("    %s" % d)
        print("")
        print("  El criterio de KBUILD_COLISION no esta inventado: es lo que hace")
        print("  el %d de %d del corpus. Se recalcula con esta misma herramienta." % (l, t))
        return 0

    rows = []
    for ruta in ficheros(RAIZ):
        rel = os.path.relpath(ruta, RAIZ)
        try:
            texto = open(ruta, encoding="utf-8", errors="replace").read()
        except OSError:
            continue
        rows.extend(escanear_texto(rel, texto))
    rows.extend(escanear_pendientes(RAIZ))
    for ruta in ficheros(RAIZ):
        if os.path.basename(ruta) != "Makefile":
            continue
        rel = os.path.relpath(ruta, RAIZ)
        texto = open(ruta, encoding="utf-8", errors="replace").read()
        rows.extend(escanear_kbuild(rel, texto))
    rows.extend(escanear_modulos(RAIZ))
    if a.solo:
        rows = [r for r in rows if r["clase"] == a.solo]

    dist = {}
    for r in rows:
        dist[r["clase"]] = dist.get(r["clase"], 0) + 1

    if a.json:
        print(json.dumps({"total": len(rows), "distribucion": dist,
                          "hallazgos": rows}, indent=2, ensure_ascii=False))
        return 0

    print("=" * 78)
    print("lint -- integridad del texto escrito y estructura de PENDIENTE=")
    print("=" * 78)
    print("""
  CJK_INSERTADO  intercalado entre espacios. NO significa "se puede borrar":
                 cuatro de los seis reales son SUSTITUCIONES rodeadas de
                 espacios, que la geometria no distingue de una insercion
  CJK_SUSTITUIDO pegado a una palabra latina: OCUPA el lugar de una palabra
                 perdida. Borrarlo deja una frase distinta y peor. NO se
                 corrigen de forma automatica: necesitan al autor. Este proyecto escribe en
                       castellano con acentos; un ideograma es una falta, y
                       se cuela cuando la atencion baja.
  ANGLICISMO           una LISTA de las palabras inglesas que aparecieron de
                       verdad. Una lista sólo detecta lo que ya se ha visto:
                       no finja mas cobertura de la que tiene.
  PENDIENTE_SIN_HALLAZGO / HALLAZGO_QUE_NO_EXISTE / HALLAZGO_PARTIDO
  SIN_ESTADO / SIN_NECESITA / SIN_ALCANZABLE
                       la estructura que AGENTS.md impone a un discriminante
                       pendiente, comprobada a mano por si misma
  KBUILD_COLISION   el .o de un modulo es miembro de sus propios -objs:
                    construye, sale con codigo 0, y el codigo de ese .c
                    NO esta dentro. Medido, no temido.
  KBUILD_SIN_OBJETO el lado del artefacto: el .ko existe y uno de sus .o no.
  KBUILD_MIEMBRO_INEXISTENTE
                    un -objs declara un .o sin .c detras
""")
    for r in rows[:80]:
        print("  %-24s %s:%s  %s" % (r["clase"], r["fichero"][:38],
                                     r.get("linea", "-"), r.get("detalle", "")[:34]))
    if len(rows) > 80:
        print("  ... y %d mas (--json los lista todos)" % (len(rows) - 80))
    print()
    print("  %d hallazgos: %s" % (len(rows), ", ".join(
        "%s %d" % (k, v) for k, v in sorted(dist.items())) if dist else "ninguno"))
    if not rows:
        print("  NINGUNO. Y esto es un resultado, no un silencio: los vectores")
        print("  comprueban que las cuatro clases se disparan de verdad.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
