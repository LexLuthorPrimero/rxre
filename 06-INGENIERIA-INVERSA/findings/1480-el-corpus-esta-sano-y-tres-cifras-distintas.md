# 1480 — El corpus está sano: 5 de 1000 ficheros con un include sin resolver, ninguno en la ruta de la RX550. Y el mismo error de instrumento me dio 819 y 524 antes de darme 5

```text
AGENCIA=RX550-INVESTIGACION · WORK_CLASS=AGENT-RE-TOOLING
GENERADO=2026-10-05 · MEDIDO=EN ESTA HOST

PREGUNTA QUE CIERRA   el NOT_DETERMINED de 1479: "que otras carpetas del
                      corpus faltan ademas de include/drm/"
RESPUESTA             ninguna que afecte.  5 ficheros de 1000, en ASICs que
                      no son GFX8 o cabeceras del kernel generico.
ESTADO               PROVEN.  Y el camino para llegar a el quedo en tres
                      cifras distintas, todas error mio.

CORRIGE, mio          1479 leia esto como si el arbol estuviese roto de mas
                      widespread.  No lo estaba, y el unico hueco real sigue
                      siendo include/drm/, que es UN fichero.
```

## 0 · LA MEDICIÓN, Y SUS TRES VERSIONES

Mismo corpus, misma pregunta, tres conjuntos de rutas de búsqueda:

```text
  version                                        ficheros .c con include roto
  -------------------------------------------    ---------------------------
  1.  4 rutas fijas (las que yo supuse)                   819 de 1000
  2.  338 directorios que contienen algun .h             524 de 1000
  3.  TODOS los directorios del arbol (370)                5 de 1000
```

**El número cambió por 164 veces sin tocar el corpus.** Lo único que cambió fue
la ruta de búsqueda.

Y las tres versiones eran Wrong en un sentido distinto:

- **v1, 819**: `dm_services.h` no resolvía. Existe, en
  `display/dc/dm_services.h`. Mi lista de cuatro rutas no incluía ese
  directorio.
- **v2, 524**: `gmc/gmc_8_1_d.h` no resolvía. **Ese fichero lo leí entero en
  `1471`.** El directorio `drivers/gpu/drm/amd/include/` no tiene `.h` propio
  —solo subdirectorios— y mi regla exigía `.h` para admitir un directorio como
  ruta de búsqueda.
- **v3, 5**: todos los directorios. Aquí `0x0`.

**v3 es la correcta, y por un argumento que no es "salió bien":** un
superconjunto de las rutas de búsqueda no puede producir falsos negativos. Solo
puede resolver de más. Un falso positivo —dar por resuelto algo que el Makefile
no resolvería— se declara y se contrasta aparte; un falso negativo es invisible.

## 1 · LOS 5, UNO A UNO

```text
  FICHERO                        INCLUDE SIN RESOLVER            CLASE
  ci_smumgr.c                    linux/delay.h                   kernel generico
  amdgpu_dm_plane.c              drm/drm_framebuffer.h           kernel generico
  dcn401_dccg.c                  dmub_common.h, dmub401_common.h  ASIC RDNA3+
                                 dmub401_regs.h, dmub401_dccg.h,
                                 dmcub_reg_access_helper.h
  link_hwss_hpo_frl.c            virtual/virtual_link_hwss.h     DC interno
  dml2_top_legacy.c              dml2_top_legacy.h               DML2, DC interno
```

**Clase 1 — cabeceras del kernel genérico.** `linux/delay.h` y
`drm/drm_framebuffer.h` no pertenecen al árbol de AMD: pertenecen a
`include/linux/` y `include/drm/` **de Linux**. El corte del corpus se hizo por
`drivers/gpu/drm/amd/`, así que no los trajo. Confirmado: `delay.h` está en
`/usr/src/kernels/6.18.2-200.nobara.fc43.x86_64/include/linux/delay.h`.

**Clase 2 — ASICs que no son GFX8.** `dcn401_dccg.c` es DCN 4.0.1, que es
RDNA3. Los cuatro ficheros `dmub401_*` no existen en ninguna parte, ni en el
corpus ni en `RESEARCH/kernelref/linux-7.1.3/`. **No es que falten: es que no
existen en ninguna version que tengamos.** Es código de una generación posterior a
este driver.

**Clase 3 — DC interno.** `virtual_link_hwss.h` y `dml2_top_legacy.h` son
privados del subsistema DC.

## 2 · NINGUNO TOCA LA RUTA DE LA RX550

```text
  MEDIDO: menciones a POLARIS12 en los 5 ficheros = 0 en los 5.
```

Ninguno se compila, o se compila sin condición, para esta tarjeta. Y para el más
cercano —`amdgpu_dm_plane.c`, que sí contiene `adev->asic_type >= CHIP_RAVEN`—
la línea que falla es un `#include` de una cabecera **del kernel genérico**, que
en el Makefile real viene de `include/drm/`, no de este árbol.

```text
  VEREDICTO   el corpus 7.2.8 esta integro para el target.
              995 de 1000 .c compilan sin una sola cabecera ausente de su
              dominio.  Y los 5 restantes no son de este ASIC.
```

## 3 · CORRECCIÓN A 1479

`1479` §6 dejó abierto:

```text
  ABRE  2. Que otras carpetas faltan del mismo modo.  No solo include/drm/: si
        esa falta, ¿que mas?  Es un census del arbol.
```

**Respuesta: ninguna carpeta más falta.** El único hueco es `include/drm/`, y
dentro de él solo importa `amd_asic_type.h`.

Y esto **rebaja la gravedad de 1479**, que escribí como si el árbol estuviese
"a medias". La formulación correcta es más estrecha y más fuerte:

```text
  1479, RETOCADO
    ANTES (mio, exagerado):  "el corpus esta incompleto"
    AHORA (medido):          "falta UN fichero, include/drm/amd_asic_type.h, y
                              por eso 38 identificadores CHIP_* no tienen
                              definicion.  El resto del arbol esta integro:
                              995 de 1000 .c sin cabeceras ausentes de su dominio."
```

Lo que **no** cambia: el enum sigue faltando, y eso sigue bloqueando
`trace_path.py`. Lo que cambia es que ya no hay un segundo hueco escondido
detrás.

## 4 · LA LECCIÓN, Y ES LA SEGUNDA VEZ CON EL MISMO FALLO

`1473` lo dijo y lo escribí: *un recuento grande y negativo casi nunca es un
hallazgo: es un include path*. Me pasó dos veces en **la misma tarde**, con dos
herramientas distintas y el mismo error:

```text
  1473   el verificador de procedencia dio 126 huecos reales donde habia 2
  1480   el census de includes dio 819 huecos reales donde habia 5

  Los dos tenian la misma forma: un "0" o un "muchos" que salia de una
  instrumentacion incompleta, y la respuesta correcta era "no se, y esto no
  lo se".
```

La regla que sale, y que es la que hay que aplicar:

```text
  UN RECUENTO NEGATIVO GRANDE NO ES UN HALLAZGO HASTA QUE SE SEPARE:

    ¿los elementos ausentes son REALMENTE ausentes, o es que mi instrumentacion
     no los alcanzo?

  Y el discriminante es siempre el mismo, y es barato:
    cambiar SOLO la instrumentacion y ver si el numero se mueve.
    Si se mueve, el numero era de la instrumentacion.

  En 1480: 819 -> 524 -> 5, cambiando solo la ruta de busqueda.
  En 1473: 126 -> 63 -> 2, cambiando solo el regex.
```

Y la variante positiva: **el `PROVEN_ABSENT` necesita el superconjunto.** Para
afirmar que algo falta, hay que haber buscado en todas partes. Un conjunto
restringido de rutas solo permite afirmar *"no lo encontré donde miré"*, que es
`NOT_FOUND`, no `PROVEN_ABSENT`. `§16 READ SCOPE GATE` ya lo pedía; lo que
toca es dejar de confundir los dos verbos al escribir el número.

## 5 · LO QUE ESTO ABRE PARA LA API

Con esto medido, el estado de las capacidades queda:

```text
  OPERACION                       ESTADO      BLOQUEO
  reg_writers(reg)                FUNCIONA    ninguno   (reg_census 1.1.0)
  reg_lookup(addr)                FUNCIONA    ninguno   (regalias 1.0.0)
  struct_layout(struct)           FUNCIONA    ninguno
  pm4_adjudicate()                FUNCIONA    ninguno
  find_chip(chip)                 MUDO        include/drm/amd_asic_type.h
  callers(sym) via AST            MUDO        cabeceras generadas por make
```

**Cinco de seis operativas.** La API se puede construir, y una de las dos
mudas tiene un bloqueo identificado de un solo fichero.

Y hay un dato de diseño que sale de aquí: **`amdgpu_dm_plane.c` usa
`adev->asic_type >= CHIP_BONAIRE`.** Una comparación *ordinal*. Eso no la
resuelve ningún enum de otro árbol: necesita que el símbolo exista, y con un
valor que dependa del orden de las declaraciones —y §4B de `1479` yainko midió
que solo `CHIP_TAHITI` tiene valor explícito, el resto es implícito.

```text
  ABIERTO, y con riesgo real
    una comparacion ordinal con un enum importado de otra version puede dar
    un ASIC distinto sin dar error, porque el valor cambia con el ORDEN de las
    declaraciones y nadie lo comprueba.  esto NO es como el caso de igualdad,
    donde el simbolo basta.

    Y por eso 1479 §4B esta PARCIAL y no PROVEN: es valido para las 38
    comparaciones de IGUALDAD medidas y NO para las ordinales.  Corrijo.
```

## 6 · ESTADO

```text
PROVEN           5 de 1000 .c tienen un include que no resuelve dentro del
                 dominio de AMD.  Ninguno se compila para POLARIS12.
PROVEN           las tres cifras 819 / 524 / 5 son la MISMA medicion con
                 tres instrumentos, y solo la tercera es valida.
CORRIGE a 1479   el corpus no esta "a medias": falta UN fichero.  Y el
                 enum importado sirve para igualdad, NO para las comparaciones
                 ordinales que el driver si usa (>= CHIP_BONAIRE).
REFUTADO, mio    dos veces el mismo error de instrumentacion, y las dos veces
                 en la misma tarde.  El numero era mio, no del corpus.
NO HECHO         el censo no se guardo como herramienta.  Se puede repetir
                 con el codigo de §0, y es de tres lineas de diferencia entre
                 una version y otra.  Quizá no merezca un fichero.
```
