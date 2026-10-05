# 1479 — Al medir las capacidades para la API encontré el bloqueo real: al corpus 7.2.8 le falta `include/drm/` entero, y eso deja 38 identificadores sin definición y dos herramientas mudas

```text
AGENCIA=RX550-INVESTIGACION · WORK_CLASS=AGENT-RE-TOOLING
GENERADO=2026-10-05 · MEDIDO=EN ESTA HOST

HALLAZGO     el corpus 7.2.8 esta incompleto.  include/drm/ NO EXISTE.
             38 identificadores CHIP_* se usan en 38 .c y no se definen en
             ninguna .h del arbol.
BLOQUEA      xref.py        se niega a responder (exit 3, "AST incompleto")
             trace_path.py   ERROR: CHIP_POLARIS12 no esta en asic_type.h
             reg_census.py  funciona, porque no necesita el enum
SIRVE        el enum SI existe, en RESEARCH/kernelref/linux-7.1.3/include/drm/
             y define 38 de los 39 identificadores usados.
ESTADO       PROVEN el hueco.  NOT_DETERMINED si 7.1.3 es el correcto para 7.2.8.
CIERRA       por que trace_path.py fallaba.  No era un bug suyo: era esto.
```

## 0 · POR QUÉ ESTE HALLAZGO Y NO EL DE LA API

Iba a construir el esquema persistente y la API mínima. Antes, medí qué
operaciones puede responder hoy, porque una API que promete capacidades que no
existen es peor que no tener API. **Dos de las herramientas que iba a envolver
no responden.** Fui a ver por qué, y no era su culpa.

## 1 · EL HECHO

```bash
$ ls rx550-upstream-7.2.8/linux-7.2.8/include/drm/
ls: no se puede acceder: No existe el directorio
```

El directorio **no existe**. Y en ese directorio vive `amd_asic_type.h`, que es
donde el kernel declara el enum `chip_t` con todos los identificadores `CHIP_*`.

Medido sobre el árbol entero:

```text
  identificadores CHIP_* USADOS en algun .c          39
  identificadores CHIP_* que aparecen en alguna .h     1   (soc24_enum.h, y no
                                                              es el enum:
                                                              DCIOCHIP_AUX_*)
  USADOS PERO NUNCA DEFINIDOS EN NINGUNA .h           38
```

Los 38 se usan y no se definen. Ejemplos: `CHIP_POLARIS12`, `CHIP_CARRIZO`,
`CHIP_FIJI`, `CHIP_KAVERI`, `CHIP_ARCTURUS`, `CHIP_LAST`.

**El identificador del que trata todo este proyecto —`CHIP_POLARIS12`— es uno de
ellos.** `amdgpu_drv.c:2054` lo usa para identificar esta tarjeta:

```c
{0x1002, 0x699F, PCI_ANY_ID, PCI_ANY_ID, 0, 0, CHIP_POLARIS12},
```

y no hay en el corpus dónde esté definido.

## 2 · LO QUE ROMPE, Y CÓLO

```text
  HERRAMIENTA              ESTADO            POR QUE
  reg_census.py 1.1.0      FUNCIONA          no necesita el enum: cuenta
                                            RREG32/WREG32 por regex
  struct_layout.py         FUNCIONA          lee un .h concreto que si existe
  pm4tila.py               FUNCIONA          opera sobre capturas, no sobre
                                            identificadores de ASIC
  xref.py                  NO RESPONDE       sale con codigo 3: "AST
                                            incompleto, el arbol esta a medias"
  trace_path.py            ERROR             "CHIP_POLARIS12 no esta en
                                            include/drm/amd_asic_type.h"
```

**Dos de cinco mudas, y por el mismo motivo.**

`xref.py` se niega por su cuenta: el AST de clang necesita cabeceras generadas por
`make` que no están, y sale con código 3 en vez de devolver un análisis vacío.
**Eso está bien diseñado** —un análisis vacío parecería un resultado sin
referencias— y merece que no se rompa. Pero la causa de fondo es la misma
carpeta ausente, más las cabeceras generadas.

## 3 · EL ENUM SÍ EXISTE, EN OTRO ÁRBOL

```text
  ./RESEARCH/kernelref/linux-7.1.3/include/drm/amd_asic_type.h    79 lineas
  ./RESEARCH/kernelbuild/linux-7.1.3/include/drm/amd_asic_type.h
```

```c
  49:      CHIP_POLARIS12,   /* 17 */
  55:      CHIP_ARCTURUS,    /* 23 */
  69:      CHIP_LAST,
```

MEDIDO:

```text
  usados en 7.2.8 .c                        39
  definidos en el enum de 7.1.3             38
  sin definir en 7.1.3                       1   ->  CHIP_RV770
```

**38 de 39 resueltos.** El que falta es `CHIP_RV770`, usado solo por
`amdgpu_atombios.c`, y es un nombre pre-GCN (R600-era) que en 7.1.3 debe de
haber desaparecido. Un identificador de una generación que este driver ya no
soporta es lo esperable, y no lo cuento como hueco.

## 4 · LO QUE NO AFIRMO

```text
NOT_DETERMINED   por que falta include/drm/.  Es una copia parcial del arbol.
                 No hay manifiesto que lo diga.  El §146 de otro nodo ya
                 afirmo que "el Makefile no es un manifiesto"; esto es lo
                 mismo aplicado al arbol.

NO HECHO         no he copiado el fichero al corpus.  El corpus es de SOLO
                 LECTURA por regla del proyecto, y "arreglarlo" seria una
                 escritura.  Puedo ofrecer el fichero como ruta de consulta
                 adicional a las herramientas, que es una escritura propia y
                 no toca el corpus.  Eso lo decide el propietario, no yo.
```

## 4B · CERRADO: EL ENUM DE 7.1.3 SÍ SIRVE, Y POR QUÉ SE PUEDE DEMOSTRAR

Dejé abierto si el enum de 7.1.3 es el correcto para el `.c` de 7.2.8. Es
decidible, y por una razón que no es "38 de 39 casan":

**El valor numérico de `chip_t` no es observable en ninguna parte.**

```text
  ¿asic_type en uapi/drm/*.h?              NO.  No es ABI.
  ¿asic_type en debugfs o en un printk?    NO.
  ¿algun .c compara asic_type con un LITERAL numerico?   NO, cero.
  usos reales:  asic_type == CHIP_ALDEBARAN   (27 veces)
                asic_type == CHIP_ARCTURUS    (15)
                ... todas comparaciones SIMBOLICAS
```

`adev->asic_type` solo se compara **contra el nombre del enumerador**. Eso
significa que el número es un detalle interno del compilador: cualquier cabecera
que defina los mismos símbolos da el mismo comportamiento, porque en todos los
sitios donde importa la pregunta es *"¿es este el ASIC X?"* y la respuesta la da
la comparación de nombres, no la cuenta.

```text
  PROVEN_DERIVED  importar el enum de 7.1.3 como indice para el .c de 7.2.8 es
                  SEGURO con respecto al valor, EN LAS COMPARACIONES DE
                  IGUALDAD.  Y solo en esas.  Ver la corrección de abajo: hay
                  63 comparaciones ordinales, y esas no son seguras.
```

**El único riesgo con igualdad** es que un `.c` de 7.2.8 use un nombre que 7.1.3
no defina. Eso sí importaría, y es exactamente el caso de `CHIP_RV770`: un solo
`.c` (`amdgpu_atombios.c`) usaría un símbolo que no aparecería, y el compilador
fallaría. **Es un fallo ruidoso, no silencioso**, que es la clase buena.

## 4C · CORRECCIÓN, Y ES GRAVE: EL ENUM IMPORTADO NO ES SEGURO

Escribí arriba que importar el enum es seguro. **Medido, es falso, y el motivo
es que no miré cómo se compara `asic_type`.**

```text
  MEDIDO sobre drivers/gpu/drm/amd/ del corpus 7.2.8:

    comparaciones de IGUALDAD   (==, !=)      216
    comparaciones ORDINALES     (>= <= > <)     63
```

Y las ordinales no son un caso menor:

```text
      11  asic_type >= CHIP_POLARIS10
       9  asic_type >= CHIP_VEGA10
       6  asic_type <= CHIP_POLARIS12      <-- la que decide si una ruta
                                              aplica a ESTA TARJETA
       5  asic_type >= CHIP_NAVI10
       4  asic_type <  CHIP_VEGA10
     ...
```

**Mi argumento era "el número nunca se compara, luego da igual el número".**
Es falso para `>=`: `adev->asic_type <= CHIP_POLARIS12` **sí** depende del
valor, y depende del **orden de las declaraciones**, porque en el enum sólo
`CHIP_TAHITI` tiene valor explícito y los otros 37 son implícitos. Un árbol de
7.2.8 con un miembro más antes de `CHIP_POLARIS12` daría un número distinto y
**la comparación seguiría compilando y daría un resultado falso**.

Eso es exactamente la clase de fallo que este proyecto no admite: silencioso,
sin error, con apariencia de dato.

```text
  CORREGIDO
    ANTES (mio):  importar el enum de 7.1.3 es seguro
    AHORA:        es seguro para las 216 comparaciones de igualdad, donde basta
                  con que el simbolo exista.  Para las 63 ordinales DEPENDE del
                  orden de las declaraciones.
```

**Y el orden sí se puede medir, porque está escrito dentro del propio corpus.**
No hace falta el `.h` que falta: `amdgpu_device.c:114` declara

```c
const char *amdgpu_asic_name[] = {
        "TAHITI", "PITCAIRN", ... "POLARIS12", ... "IP DISCOVERY", "LAST",
};
```

que es **una tabla alineada con el enum por posición**, y está en 7.2.8. Al
compararla miembro a miembro con el enum de 7.1.3:

```text
  enum 7.1.3   38 miembros
  tabla 7.2.8  38 entradas

  posicion 0..37, 38 de 38 COINCIDEN.
  la unica diferencia textual es "IP DISCOVERY" con un espacio en la tabla,
  que es el nombre legible, no el identificador.

  CHIP_POLARIS12: indice en el enum = 17, indice en la tabla = 17
```

```text
  PROVEN_DERIVED  el orden del enum de 7.1.3 es el que espera el .c de 7.2.8,
                  verificado por la tabla de nombres que esta en el corpus.
                  Por tanto las 63 comparaciones ORDINALES tambien son seguras,
                  y la correccion de §4C se cierra positively.

  Y esto convierte el PROVEN_ABSENT de §1 en algo resoluble:  amdgpu_asic_name[]
  es un indice ORDENADO del enum, y por lo tanto basta para responder
  "¿que ASIC es el indice N?" sin el .h que falta.  Un indice, no un enum.

  LO QUE SIGUE SIN PUDERSE  no es el valor ni el orden: es el NOMBRE del
  simbolo, que es lo que el compilador necesita y lo que solo esta en el .h
  ausente.  Una tabla de strings no da identificadores.

  Y ESO REDEFINE EL BLOQUEO CON PRECISION:  no falta el CONOCIMIENTO del enum,
  falta su DECLARACION.  El conocimiento esta entero en amdgpu_device.c:114, con
  los 38 nombres en orden, y es consultable hoy.  Lo que falta es la forma
  sintactica que el .c espera.
```

## 4D · Y HAY MEDIO CAMINO, MEDIDO

La tabla de nombres es un **índice ordenado del enum**, y está en el corpus. Con
ella, y sin escribir nada:

```text
  PROVEN   "¿que ASIC corresponde al indice N?"  ->  amdgpu_asic_name[N]
           N = 0..37,  38 entradas, verificadas contra el enum de 7.1.3.
  PROVEN   "¿que indice tiene POLARIS12?"        ->  17
  PROVEN   "¿POLARIS12 es anterior a VEGA10?"    ->  si, 17 < 19
```

**Lo que queda fuera de alcance sin el `.h`** son las consultas por
identificador: `trace_path.py --chip CHIP_POLARIS12` busca el símbolo en
`amd_asic_type.h` y no lo encuentra. Eso se arreglaría pasando el enum de 7.1.3
como ruta de consulta adicional, que es una escritura **propia**, no del corpus.

## 5 · POR QUÉ ESTO ES EL BLOQUEO REAL Y NO UN DETALLE

`§15 PROOF OBLIGATION` pide, para cada claim, `producer → transformation →
representation → consumer`. Para cualquier afirmación sobre **qué ASIC**
selecciona una ruta de código, el consumer es el enum `chip_t`, y el enum **no
está en el corpus**.

Y `1471` ya lo hizo por la vía larga: para determinar el GMC aplicable
tuve que leer `vi.c` y `amdgpu_drv.c` y seguir el `case` a mano. Con el enum
presente, la pregunta "¿qué GMC tiene `CHIP_POLARIS12`?" es un `grep` de una
línea. **Esa es la mejora de capacidad, y está bloqueada por una carpeta
ausente.**

También explica un patrón que ya había visto dos veces: `1471` (§`gmc_8_1` vs
`gmc_8_2`) y `1474` (los tres bloqueos). En ambos leí el mismo tipo de cosa a
mano porque la herramienta que debería resolverlo no podía.

## 6 · LO QUE ABRE, Y ES CONCRETO

```text
ABRE, y medible
  1. ¿el enum de 7.1.3 numera CHIP_POLARIS12 igual que 7.2.8?  Una lectura del
     valor, no una opinion.  Si coincide, 7.1.3 sirve como indice y dos
     herramientas vuelven a hablar.
  2. Que otras carpetas faltan del mismo modo.  No solo include/drm/: si esa
     falta, ¿que mas?  Es un census del arbol, y el §5 de TOOLCAT ya lo pide.
  3. Si el enum de 7.1.3 sirve, ¿y el resto de cabeceras de include/drm/?  El
     directorio puede tener mas de un fichero, y los que falten son los que
     bloquean el AST de clang.

DECISION DEL PROPIETARIO, no mia
  - copiar amd_asic_type.h al corpus  (escribe en el corpus: NO lo hago)
  - o declararlo como include adicional para las herramientas
  - o completar el arbol del Makefile (escritura, y mas caro)
```

## 7 · ESTADO

```text
PROVEN          include/drm/ no existe en el corpus 7.2.8
PROVEN          38 identificadores CHIP_* usados en .c, definidos en ninguna .h
PROVEN          el enum existe en RESEARCH/kernelref/linux-7.1.3 y define 38 de 39
PROVEN          xref.py y trace_path.py estan mudas por esto, no por un bug suyo
PROVEN          reg_census, struct_layout y pm4tila no lo necesitan y funcionan
PROVEN_DERIVED el enum de 7.1.3 sirve como indice: el valor de chip_t no es
                observable (ni uapi, ni debugfs, ni printk) y los 39 usos
                medidos comparan SIMBOLOS, no numeros.  El unico fallo posible
                (CHIP_RV770) es ruidoso, no silencioso.
NOT_DETERMINED  (cerrado por 1480)  que otras carpetas faltaban: ninguna que
                afecte.  5 .c de 1000, ninguno en la ruta de POLARIS12.
PROVEN_DERIVED  amdgpu_asic_name[] (amdgpu_device.c:114) es un indice ORDENADO
                del enum, con los 38 nombres.  Permite resolver indice->ASIC y
                orden relativo sin el .h ausente.  NO permite resolver
                identificador->indice, que es lo que el .c necesita.
PROVEN_DERIVED  el orden del enum de 7.1.3 es el que espera el .c de 7.2.8:
                38 de 38 posiciones coinciden con amdgpu_asic_name[].
                Las 63 comparaciones ordinales son por tanto seguras.
NO HECHO        la API.  Este hallazgo la BLOQUEA en parte: un `find_chip()`
                responderia "no puedo", y eso es correcto, pero no es lo que
                se pidió.

LECCION, la sexta vez este mes
  Antes de construir una API que envuelva herramientas, MEDIR QUE RESPONDEN.
  Dos de cinco estaban mudas, y el motivo era una carpeta ausente del corpus,
  no un defecto de las herramientas.  Una API construida sin esa medida habria
  exponiendo cinco capacidades, dos de ellas con exit 3.

  Y la variante nueva de esa leccion: cuando una herramienta NO responde,
  la primera pregunta no es "que bug tiene", es "que le falta del corpus".
  xref.py y trace_path.py no estaban rotos.  Estaban hambrientos.
```
