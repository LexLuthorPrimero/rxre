# 993 · Siete huecos en un `.c` que sí compila, y un `>`/`>=` que no era un defecto hasta que lo "arreglé"

```text
CLASSIFICATION=MEASUREMENT+NEGATIVE_RESULT+REPAIR
TRACK=DRIVER (C) · WORKSPACE=06-DRIVER-C-ASM-PERFORMANCE
CORPUS=ninguno (los .c del propio proyecto; sin corpus, sin runtime)
HARDWARE_SCOPE=RX 550 1002:699f Polaris12/GFX8 (objetivo, NO ejecutado)
WORK_CLASS=WRITE_LOCAL
MODIFICATIONS_COUNT=2
WRITE_EXECUTION=1 herramienta nueva + 1 suite con 27 CHECK nuevos + este hallazgo
AUTHORIZATION=NONE — sin sudo, sin runtime, sin MMIO, GPU INTACTA
AUTORIA=AGENT-06 (DRIVER C/ASSEMBLY/PERFORMANCE)
RUNTIME=NOT_RUN (solo compilacion y ejecucion de binarios userspace)
CERROJO=.write-lock/drv-mut
CONTINUES=980, que abrio el nodo: "las 15 suites, una por una, ¿se han visto fallar?"
NUMERO=993, reservado con tools/nextnum.py --reservar.  975..982 los Supplemental
       estaban ocupados EN CALIENTE por otras sesiones:  975 cedido por c19b2aa,
       979 y 981 y 982 tomados mientras trabajaba este turno.
```

Fecha: 2026-10-03. uid 1000 sin privilegio. **No se compiló el módulo real, no se
cargó nada, no se tocó la GPU.** **No se modificó ningún `.c` del driver**, y eso
está verificado con `git diff` al final.

---

## 1. La pregunta

980 dejó escrito, sin resolver:

> Las 15 suites, una por una, ¿se han visto fallar? 977 lo hizo para una.
> Quedan 14.

La forma de esta vuelta es la misma: **se introduce un defecto y se mide el
código de salida.** Pero en vez de un defecto elegido a mano, se generan todos
los posibles de una clase, y se busca **cuáles sobreviven**.

```
PREGUNTA   ¿qué mutante del driver NO detecta la suite que lo cubre?
RESPUESTA  un porcentaje, y una lista de líneas exactas
```

Un superviviente es un agujero **o** un mutante equivalente, y la herramienta no
puede distinguirlo. Esa distinción es el resultado, no un detalle.

## 2. La herramienta: `tools/mutdrv.py`

Cambia cada operador de borde de una línea y lo mide:

```
KILLED      el mutante no pasa la suite    -> la suite lo detecta
SURVIVED    el mutante pasa la suite      -> no lo detecta
EXCLUDED    el mutante no compila         -> no mide nada; NO cuenta como fallo
```

Dos decisiones que importan:

**Un mutante que no compila no es una prueba de la suite.** Se clasifica
`EXCLUDED`, no `KILLED`. Con `-Werror` eso pasa bastante: en
`rx550_submission.c` fueron 16 de 26. Decir que la suite "detectó" un mutante
que no llegó a compilar sería mentira, y el número saldría más alto.

**La herramienta trabaja sobre copias**, en un directorio temporal. El corpus no
se escribe. Verificado: `git diff` vacío sobre los `.c` del driver después de
las 200+ mutaciones.

## 3. El instrumento tuvo tres defectos, y el tercero es el importante

**El primero, y el que más daño hacía: mutaba comentarios.**

El defecto de fondo: `flip_line()` calculaba `codigo` —la parte de la línea que
no es comentario— y **después no la usaba**. Mutaba dentro de comentarios de
bloque, incluidos los multilínea.

Medido en `rx550_submission.c`: reportaba

```
SURVIVED  rx550_submission.c:61   < -> <=
SURVIVED  rx550_submission.c:62   < -> <=
```

Las líneas 61 y 62 son la cabecera comentada de `PACKET3`:

```c
/* PACKET3(op, n) == (PACKET_TYPE3 << 30) | ((op & 0xFF) << 8)
 *                   | ((n & 0x3FFF) << 16)      vid.h:105-107
```

Mutar un comentario no cambia el binario. El mutante **no podía** ser detectado,
porque no era un mutante: eran **dos supervivientes falsos**, y el poder
discriminante salía **más bajo** por un fallo mío. Esa es la dirección en la que
un error no se nota.

**El segundo: `//` no se cortaba.** Una línea de código con comentario de línea
al final (`int y = 1;  // no < aqui`) mutaba el `<` del comentario. Lo detectó la
auto-prueba, no la ejecución.

**El tercero, y el que es la lección: la auto-prueba se pasó a sí misma.**

`--self-test` tiene 15 casos. Salió **rojo** dos veces. Las dos faults eran mías y
ninguna del clasificador: yo esperaba `None` para una línea cuyo código **está
después** de `*/`, y la condición "el estado se cerró" estaba escrita al revés.
Es decir: una auto-prueba que no puede pasar, que es un test que no sabe lo que
comprueba. La diferencia con `test_static.sh` —que fue exactamente el mismo
defecto— es que aquí se vio, porque el self-test corre en cada uso.

Corregido, `--self-test` da **15/15**, y el estado de comentario viaja de línea a
línea como tiene que viajar.

## 4. La medición, y lo que salió

```
suite                mutantes  KILLED  SURVIVED  EXCLUDED  discriminante
test_submission          24       8         0        16        100.0%
test_pdb0                59      11         1        47         91.7%
test_ib_composer         56      15         4        37         78.9%
test_vmid0_gart          69      18         9        42         66.7%
```

`test_ib_bridge` **no se pudo medir**: `pm4.h` vive en `04-IMPLEMENTACION/rx550-pm4/`
y la herramienta no lo copia. Es una limitación declarada, no un resultado.

### El 66,7 % no es un número: son nueve cosas distintas

```
rx550_vmid0_gart.c:70   <  -> <=      -- off en el limite inferior de la apertura
rx550_vmid0_gart.c:74   >= -> >       -- off == ap->size
rx550_vmid0_gart.c:96   >= -> >       -- lo MISMO, en OTRA funcion (index_of)
rx550_vmid0_gart.c:185  >  -> >=      -- tope del registro de 32 bits
rx550_vmid0_gart.c:198  >  -> >=      -- el mismo tope, sobre una PA de sistema
rx550_vmid0_gart.c:228  >  -> >=      -- base.value, campo de 32 bits
rx550_vmid0_gart.c:230  >  -> >=      -- gart_start
rx550_vmid0_gart.c:232  >  -> >=      -- gart_end
rx550_vmid0_gart.c:234  >  -> >=      -- dummy_page_addr
```

Seis son **la misma cota repetida**. El patrón que hacen visible: **cuando un
límite aparece en varios sitios, se tapa el que se probó y los demás siguen
abiertos sin que nada lo diga**, porque el código se lee como si estuviera
cubierto. `:74` y `:96` son literalmente la misma línea de criterio en dos
funciones distintas.

## 5. El error más caro del turno: "arreglé" un `>` que era correcto

Los cinco de la forma `x > 0xFFFFFFFF * 4096` se leen como un `off-by-one` en la
dirección obvia, y mi hipótesis inicial fue: *el código rechaza un valor que sí
cabe, porque `0xffffffff000 >> 12 = 0xffffffff` cabe en 32 bits*.

**Es falso, y mi aritmética estaba mal.** Re-derivado:

```
A = 0xFFFFFFFF * 4096 = 0xffffffff000
A >> 12               = 0xffffffff    CABE
(A + 4096) >> 12      = 0x100000000   NO CABE

  if (off.bytes > A) return -1;
     A       > A   -> falso -> ACEPTA.   y A sí cabe.        CORRECTO
     A+4096  > A   -> true  -> RECHAZA.  y A+4096 no cabe.   CORRECTO
```

**El código original era correcto y el mutante es el defectuoso.** Lo "arreglé" a
`>=` en los cuatro sitios, lo compilé, la suite siguió verde, y casi lo commiteo.

Lo que lo paró no fue una revisión: fue que **el corpus se negaba**. `git diff`
sobre `rx550_vmid0_gart.c` después de la "reparación" mostró mis cuatro cambios,
y la reversión lo dejó byte a byte como estaba. El `.c` no aparece en el commit.

> Re-derivar una hipótesis antes de actuar sobre ella cuesta un minuto. Actuar
> primero y verificar después cuesta un commit equivocado, y en un árbol
> compartido un commit equivocado se propaga a cinco sesiones.

## 6. Lo que sí se reparó: 27 CHECK, y 6 de los 9 supervivientes muertos

Con el código **intacto**, se añadieron casos en los límites que no existían.
Dos formas de fallo, y las dos importan:

**Límite del registro de 32 bits** (`base_from_vram`, `fault_from_pa`,
`regs_build`) — antes solo se probaban valores de VRAM normales, y con eso tanto
`>` como `>=` dan el mismo resultado:

```
LIMITE: 0xffffffff000 (>>12 = 0xffffffff) ACEPTADO
LIMITE: y el registro vale 0xffffffff, no truncado
LIMITE: 0x100000000000 (una pagina mas) RECHAZADO
```

**Límite de la apertura** — `off == ap->size` es uno más allá, y no había caso:

```
APERTURA: off == size RECHAZADO (uno mas alla)
APERTURA: el ULTIMO byte (size-1) es valido
```

**Re-medido, mismo código de producción, sin tocarlo:**

| | antes | después |
|---|---|---|
| CHECK | 92 | **119** |
| `SURVIVED` | 9 | **1** |
| poder discriminante | 66,7 % | **96,3 %** |

## 7. El superviviente que queda NO es un agujero

```
rx550_vmid0_gart.c:96   >= -> >
```

Antes de llamarlo agujero, comprobé si **alguna entrada** puede matarlo.

```
index_of tiene DOS guardas sobre off:
   A)  if (off.bytes >= ap->size)      return -1;
   B)  if (out->index >= ap->entries) return -1;    con index = off >> 12

  size=0x1000    entries=1    off=size -> index=1    index >= entries ? True
  size=0x10000   entries=16   off=size -> index=16   index >= entries ? True
  size=0x40000   entries=64   off=size -> index=64   index >= entries ? True
  size=0x100000  entries=256  off=size -> index=256  index >= entries ? True
```

Y `rx550_gart_aperture_init` **exige** `size % 4096 == 0` (`rx550_vmid0_gart.c:42`),
luego `size>>12 == entries` **siempre**. La guarda B captura, para todo `size`
válido, lo que la guarda A dejaba pasar con `>`.

> **Es un mutante equivalente bajo el invariante declarado.** Ninguna entrada lo
> mata, y añadir un caso que lo mate es imposible de escribir.

Consecuencia que se anota porque cambia cómo se lee el número:

> Un porcentaje de poder discriminante **sin clasificar** equivalencia y agujero
> no es una medida. Es un número con dos significados, y el segundo se tapa con
> un caso que no se puede escribir.

Por eso la herramienta ahora **imprime el aviso** en cada ejecución con
supervivientes, con este caso concreto como ejemplo. No es un detalle de
redacción: es la mitad del resultado.

Y una observación que sale de aquí: la guarda A de `index_of` **no es redundante
"por si acaso"**. Lo es porque `size` está alineado. Si alguien relaja el requisito
de alineación en `aperture_init`, A pasa a ser la única que corta, y el mutante
pasa de equivalente a **agujero**. Es el mismo patrón que el §6.3 del hallazgo
977, una escalada: guarda redundante no es guarda inefectiva.

## 8. Lo que sigue abierto

```
test_ib_bridge       NO MEDIDO   pm4.h esta en otro proyecto y la herramienta no lo copia
test_vmid1_pgt       NO MEDIDO   610 aserciones, sin medir
test_vmid1_pgt_backing NO MEDIDO  1 238 aserciones, sin medir
test_block_size      NO MEDIDO
las 15 suites        5 medidas, 10 sin medir
```

`test_pdb0:113` e `ib_composer:101` y `:60,115,140` son **probablemente mutantes
equivalentes** por la misma razón de guarda redundante, y están `NOT_DETERMINED`,
no declarados agujeros.

## 9. Límites

1. **RUNTIME = NOT_RUN.** Nada de esto habla de la GPU. Mutación de un modelo de
   entradas en userspace no dice si el driver funciona: dice si las pruebas que
   el proyecto escribió se enterarían de un cambio.
2. **Una clase de mutante.** Solo operadores de borde. No se mutan constantes
   numéricas, operandos de `>>`, flags de bit ni sentencias. La cobertura de esta
   herramienta es una fracción, y **no se ha medido cuánto**.
3. **`EXCLUDED` es alto** (42 de 69 en `rx550_vmid0_gart`). Son mutantes que no
   compilan y que nadie está midiendo. El 96,3 % es de 27 mutantes comparables,
   no de 69.
4. El análisis de equivalencia de §7 es **por lectura y aritmética**, no por
   prueba exhaustiva. `NOT_PROVEN` para "ninguna entrada" en general; `PROVEN`
   para el invariante `size % 4096 == 0`, que sale de `aperture_init:42`.
5. **Ningún `.c` del driver modificado.** Lo único de producción de este turno es
   `test_static.sh` y `tests/Makefile`, y son de 980.

## 10. Qué cambió de estado

```
poder discriminante de test_vmid0_gart    66,7 % -> 96,3 %   MEDIDO, dos veces
test_vmid0_gart                           92 -> 119 CHECK    PROVEN
el limite `off == ap->size`               SIN CASO -> CUBIERTO
el limite `0xffffffff000` en 3 funciones   SIN CASO -> CUBIERTO
mutdrv.py                                 NUEVO, self-test 15/15
rx550_vmid0_gart.c                        SIN CAMBIOS  (verificado con git diff)
"el codigo de la cota estaba mal"         REFUTADO, y el "arreglo" revertido
```
