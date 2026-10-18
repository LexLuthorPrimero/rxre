#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0
"""RXRE-ECO-001. Lecciones persistentes que CAMBIAN decisiones futuras.

POR QUE UN FICHERO Y NO UN PARRAFO EN UN HALLAZGO.

Porque una leccion en un hallazgo se lee una vez. Una leccion en un modulo
que se IMPORTA se ejecuta cada vez que se toma la misma decision. Este
modulo se importa desde `ts_ast.py` y desde el propio CLI: si alguien
reescribe el parser sin mirar aqui, las lecciones no se pierden, se ejecutan.

## LAS TRES LECCIONES QUE MAS COSTARON

### 1. "COMPROBAR QUE EXISTE" NO ES "COMPROBAR QUE ES LO QUE PENSABAS"

Medido 2026-10-15. `git ls-remote` contra `github.com/tomstdenis/umr` responde
`Repository not found`, y el `registry.py` del proyecto declara ese mismo repo
para el backend `umr`. Un registro puede apuntar a un upstream que ya no
existe, y seguir pareciendo verificable porque el campo esta lleno.

Regla que sale de ahi: `commit=local:rpm-umr-1.0.0` NO es un upstream, es una
disculpa. Se acepta SOLO con la razon escrita al lado.

### 2. UN PATH MAL RESUELTO SE PARECE A UN ARTEFACTO AUSENTE

Medido 2026-10-15. El venv aislado se resolvia con
`os.path.join(PKG, "..", "..")`, y `PKG` era `tools/`, no la raiz del repo: el
resultado era `/home/lucas/Escritorio/rxre/tools/../../.venv`, que no existe.
El sintoma era `blocked: no existe el venv`, que se lee como "el venv no esta
instalado" cuando en realidad estaba instalado y mal apuntado.

Regla: cuando una ruta falle, se imprime la ruta ABSOLUTA que se comprobo y se
dice si existe. "No existe" sin decir QUE no existe, es una afirmacion que no
se puede refutar.

### 3. UN RENDIMIENTO EXPRESO ESTA DENTRO DE LOS LIMITES MEDIDOS

Medido 2026-10-15. tree-sitter parseaba un `.py` con la gramatica de C y
devolvia `ok`. El adapter solo miraba `nodos > 1`, y un Python de 2 lineas da
15 nodos. Un producer que no puede decir "esto NO es lo que pediste" declara
confianza sobre algo que no ha mirado.

Regla: todo producer que acepte un TIPO tiene que poder rechazar ese tipo. Y
el umbral con el que rechaza tiene que ser un hueco MEDIDO entre las clases,
no un numero que suena razonable.

## COMO SE USA ESTE MODULO

No se lee: se importa. `leccion(1)` devuelve la leccion con su evidencia, y el
sitio que lafterra el prepender. Si el codigo hace algo que la leccion
prohibe, quien lo lee tiene la medida antes de decidir.
"""
from __future__ import annotations

from typing import Any, Dict

#: Las lecciones. Cada una con su NUMERO (para citarla), su REGLA (que hacer)
#: y su MEDIDA (por que se escribe, no "es buena practica").
LECCIONES: Dict[int, Dict[str, Any]] = {
    1: {
        "titulo": "un upstream declarado puede no existir",
        "regla": "un `repo=`/`commit=` de un producer tiene que responder a "
                 "`git ls-remote` en el momento de escribirlo. Un "
                 "`local:rpm-*` es una EXCEPCION declarada, no un upstream.",
        "medida": "git ls-remote https://github.com/tomstdenis/umr -> "
                  "Repository not found, mientras `registry.py` declara ese "
                  "repo para el backend `umr`.",
        "aplicacion": "vendor_manifest.py marca umr como BLOQUEADO con la "
                      "prueba, en vez de darlo por clonado.",
        "costo_si_se_ignora": "una IA que quiera verificar el producer de "
                              "registros de la RX550 pierde una tarde, y no "
                              "sabe si el repo cambio o si fue un error.",
    },
    2: {
        "titulo": "un path mal resuelto parece un artefacto ausente",
        "regla": "toda comprobacion de existencia imprime la ruta ABSOLUTA "
                 "que comprobo. `no existe` sin el path es una afirmacion no "
                 "refutable.",
        "medida": "`os.path.join(PKG, '..', '..')` con PKG=`tools/` resolvio "
                  "a `/home/lucas/Escritorio/rxre/tools/../../.venv`; el "
                  "venv real estaba en `/home/lucas/Escritorio/rxre/.venv`. "
                  "El sintoma: `blocked: no existe el venv`.",
        "aplicacion": "ts_ast._raiz_del_repo() sube buscando una marca "
                      "(`tools/rxre` Y `.venv`) en vez de contar niveles.",
        "costo_si_se_ignora": "se reinstala lo que ya esta, o se diagnostica "
                              "unAbsent que no esta ausente.",
    },
    3: {
        "titulo": "un producer tiene que poder rechazar lo que pide",
        "regla": "todo producer que acepta un TIPO (lenguaje, formato, "
                 "arquitectura) tiene que poder rechazarlo, y el umbral con "
                 "el que rechaza es un hueco MEDIDO entre clases.",
        "medida": "parser C sobre un `.py`: 15 nodos, 1 ERROR, ratio 0.0667 "
                  "-> el adapter devolvia `ok`. Sobre `amdgpu.h`: 7066 "
                  "nodos, 10 ERROR, ratio 0.0014. El hueco medido esta entre "
                  "0.0014 y 0.0667; el umbral se puso en 0.01.",
        "aplicacion": "ts_ast.parsear() devuelve `unsupported` con el ratio "
                      "y el umbral en la limitacion, no solo el veredicto.",
        "costo_si_se_ignora": "una IA lee 'hay 15 nodos, 1 declaracion' "
                              "como una afirmacion sobre un fichero que no "
                              "se ha analizado en el lenguaje pedido.",
    },
    4: {
        "titulo": "'es una hoja' NO es 'es codigo' en tree-sitter",
        "regla": "en un AST, comentarios, cadenas literales y directivas de "
                 "preprocesador son hojas. Filtrar por `child_count == 0` "
                 "cuenta texto, no codigo.",
        "medida": "`/* MARCA */ const char *s = \"MARCA\"; int MARCA = 1;` -> "
                  "texto=3, filtro_por_hoja=3, filtro_por_tipo=1. Sobre "
                  "`amdgpu.h`, `ioctl` da texto=11 y AST=10: la diferencia "
                  "es el `#include <drm/drm_ioctl.h>` de la linea 54.",
        "aplicacion": "ts_ast.TIPOS_NO_CODIGO excluye por TIPO, no por forma.",
        "costo_si_se_ignora": "la capacidad se convierte en un grep con "
                              "pasos adicionales, y su valor diferencial "
                              "desaparece sin que nada falle.",
    },
    5: {
        "titulo": "un total truncado sin declarar es un error de magnitud",
        "regla": "si un producer publica una lista recortada, publica TAMBIEN "
                 "el total y un flag de truncado. Un consumidor debe poder "
                 "distinguir 'no hay' de 'hay mas de las que te enseño'.",
        "medida": "la primera version guardaba `coincidencias[:50]` y nada "
                  "mas. `n_coincidencias` no existia, asi que un consumidor "
                  "contaba 50 cuando el numero real era otro.",
        "aplicacion": "`raw.n_coincidencias`, `raw.coincidencias` y "
                      "`raw.coincidencias_truncadas` van los tres, y el "
                      "principio AIRE verifica que no se contradigan.",
        "costo_si_se_ignora": "un consumidor creyendo haber contado todo lo "
                              "que hay, sin ninguna señal de que le falta.",
    },
    6: {
        "titulo": "una asercion de test puede ser FALSA y no un bug del codigo",
        "regla": "antes de 'arreglar' el codigo porque falla un test, "
                 "comprobar que la EXPECTATIVA del test era correcta. Un test "
                 "que afirma algo falso hay que arreglarlo a el.",
        "medida": "el test afirmaba que el visitor de nodos daria MENOS que "
                  "`str.count` sobre `amdgpu.h`. Daba lo mismo (11 = 11), y "
                  "parecia que el caso sintetico demostraba lo contrario. "
                  "La verdad: las 11 apariciones de `ioctl` estan en "
                  "identificadores y un `#include`; no habia comentario que "
                  "excluir. El ADAPTER era el que estaba mal (leccion 4).",
        "aplicacion": "el caso sintetico y el fichero real se prueban los "
                      "dos, y cada uno cubre lo que el otro no.",
        "costo_si_se_ignora": "'arreglar' el codigo para satisfacer una "
                              "expectativa equivocada, dejando el defecto "
                              "real intacto Y anadiendo una restriccion "
                              "falsa al codigo.",
    },
    7: {
        "titulo": "un `ok` del producer no es una operacion cerrada",
        "regla": "`status: ok` dice que el producer respondio. No dice que el "
                 "resultado sea atribuible. La distincion es de otra capa.",
        "medida": "una operacion con `provenance` sin `input_hash` tiene "
                  "`status: ok` y es irrecuperable: nadie puede repetirla "
                  "sobre la misma entrada. TIERRA lo marca `violation`.",
        "aplicacion": "`ocho_principios.gate()` devuelve `operacion_cerrada`, "
                      "que es independiente del `status` del producer, y el "
                      "CLI lo expone como `./rxre audit`.",
        "costo_si_se_ignora": "resultados `ok` que nadie puede repetir ni "
                              "auditar, contados como trabajo hecho.",
    },
}


def leccion(n: int) -> Dict[str, Any]:
    """La leccion N, o un aviso si no existe. No falla en silencio."""
    if n not in LECCIONES:
        return {"error": "no existe la leccion %d" % n,
                "disponibles": sorted(LECCIONES)}
    d = dict(LECCIONES[n])
    d["numero"] = n
    return d


def citables() -> str:
    """Las lecciones en una linea cada una, para el docstring de un modulo."""
    return "\n".join("  L%d: %s" % (n, d["titulo"])
                     for n, d in sorted(LECCIONES.items()))


def contraviene(operacion: str) -> list:
    """Que lecciones prohiben explicitamente una operacion.

    Es la parte que hace que esto no sea prosa: una LEY, no una cita.

    MEDIDO 2026-10-15: la primera version buscaba el texto `[:50]` y el
    guard se disparo SOBRE EL PROPIO ADAPTER YA CORREGIDO, que contiene
    `coincidencias[:50]` justamente porque publica `n_coincidencias` al lado.
    30 tests en rojo por un guard que confundia MENCION con USO.

    El guard tiene que distinguir "esto recorta sin decir nada" de "esto
    recorta y lo dice". Por eso no busca el trocito de codigo: busca la
    ASIGNACION que recorta, y exige que al lado exista el total. Un modulo
    que recorta y publica `n_coincidencias` esta CUMPLIENDO.
    """
    o = (operacion or "").lower()
    if ("os.path.join" in o and ".." in o
            and "abspath" not in o and "dirname" not in o):
        return [2, "un path construido con `..` sin pasar por abspath/dirname: "
                  "es el fallo de la leccion 2"]
    # L4: un filtro por forma sin filtro por tipo. Se exige que el filtro por
    # tipo este AHORA MISMO en el modulo.
    if ("child_count" in o and ("== 0" in o or "!= 0" in o)
            and "no_codigo" not in o and "tipos_no_codigo" not in o):
        return [4, "un filtro por `child_count` sin filtro por tipo: cuenta "
                  "texto, no codigo (leccion 4)"]
    # L5: se recorta Y no se publica el total. Publicarlo es lo que
    # convierte el recorte en algo honesto.
    recorta = ("[:50]" in o or "[:20]" in o or "[:100]" in o)
    if recorta and "n_coincidencias" not in o:
        return [5, "una lista recortada sin publicar el total ni el flag "
                  "de truncado (leccion 5)"]
    return []


def todas() -> Dict[int, Dict[str, Any]]:
    return {n: dict(d, numero=n) for n, d in sorted(LECCIONES.items())}


if __name__ == "__main__":
    import json
    import sys
    print(json.dumps(todas(), indent=2, ensure_ascii=False))
