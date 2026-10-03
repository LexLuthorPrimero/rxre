# 977 · Un `.c` de producción que no compilaba, invisible porque la puerta medía 7 de 16 suites — y el `65536` que lo rompía no era un máximo del hardware

```text
CLASSIFICATION=ERROR+MEASUREMENT+NEGATIVE_RESULT+REPAIR
TRACK=DRIVER (C) · WORKSPACE=06-DRIVER-C-ASM-PERFORMANCE
CORPUS=RESEARCH/kernelbuild/linux-7.1.3/drivers/gpu/drm/amd/
HARDWARE_SCOPE=RX 550 1002:699f Polaris12/GFX8 (objetivo, NO ejecutado)
WORK_CLASS=WRITE_LOCAL
WRITE_LOCAL=PROPIOS
MODIFICATIONS_COUNT=5 ficheros
WRITE_EXECUTION=3 reparados + 1 puerta (tests/Makefile) + este hallazgo
AUTHORIZATION=NONE — sin sudo, sin runtime, sin MMIO, GPU INTACTA
AUTORIA=AGENT-06 (DRIVER C/ASSEMBLY/PERFORMANCE)
RUNTIME=NOT_RUN (solo compilacion y ejecucion de binarios userspace)
CERROJO=.write-lock/drv-q8 (mkdir atomico; NO se toco el cerrojo raiz)
TARGETS=04-IMPLEMENTACION/rx550-driver/rx550_gart_write.c
        04-IMPLEMENTACION/rx550-driver/rx550_vmid0_gart.h
        04-IMPLEMENTACION/rx550-driver/tests/test_gart_write.c
        04-IMPLEMENTACION/rx550-driver/tests/Makefile
ARTEFACTO=08-ARQUITECTURA/artifacts/Q8-TEST-MATRIX/{gate-run-1.txt,gate-run-2.txt}
CONTINUES=Q8 TEST_MATRIX (015 §4: "6 suites sueltas sin mapa", nadie)
```

Fecha de la medición: 2026-10-03. Host Nobara 44, kernel `7.1.3-200.nobara.fc44.x86_64`,
uid 1000 **sin privilegio**. **No se compiló el módulo, no se cargó nada, no se
tocó la GPU.** Todo lo de abajo es compilación y ejecución de binarios userspace.

---

## 1. La pregunta, y por qué esta

`015-cobertura-y-de-duplicacion.md` §4 declara `Q8 TEST_MATRIX = OPEN` con el
detalle «hay 6 suites sueltas sin mapa». El detalle no cuadraba con el
directorio: en `04-IMPLEMENTACION/rx550-driver/tests/` hay **16** `test_*.c`.

La pregunta de este nodo era una, con respuesta binaria:

> **De las 16 suites C de la línea de driver, ¿cuáles compilan, cuáles se
> ejecutan y cuántas aserciones pasan?**

Discriminante: `gcc -O2 -Wall -Wextra -Werror` y el código de salida del binario.
No hay gradiente. Riesgo: cero — userspace, sin MMIO, sin ring, sin kernel.

## 2. Lo que mide el inventario

16 `test_*.c`. El `Makefile` de `tests/` ponía **7** en la cola de `run`.

| | suites | aserciones | rc |
|---|---|---|---|
| **en la puerta antes** | 7 | 469 | 0 |
| **compilan y pasan, SIN puerta** | 8 | 2 345 | 0 |
| **no compilan** | 1 | — | — |

Las 15 que compilan se ejecutaron **dos veces** con salida **idéntica** y `rc=0`
en ambas. Suma de la puerta ampliada: **2 814 aserciones C + 34 de la auditoría
estática = 2 848**, `make -s run` → `rc=0`.

Las nueve que la puerta **no** alcanzaba, con su número medido. Las ocho primeras
pasaban; la novena no compilaba, y por eso es el hallazgo:

```
test_block_size 79 PASS · test_ib_bridge 59 PASS · test_ib_composer 74 PASS
test_pdb0 75 PASS · test_submission 59 PASS · test_vmid0_gart 92 PASS
test_vmid1_pgt 610 PASS · test_vmid1_pgt_backing 1 238 PASS
test_gart_write            NO COMPILABA   ← §3
```

Ninguna estaba en la puerta antes. Las ocho que pasaban acumulaban **2 345**
aserciones que nadie ejecutaba.

## 3. El defecto: un `.c` de producción que no compilaba, y nadie lo veía

`rx550_gart_write.c:39` usaba `RX550_GART_ENTRY_COUNT`:

```c
	if (b->entries > RX550_GART_ENTRY_COUNT)
		return -1;
```

Ese identificador **ya no existe**. `rx550_vmid0_gart.h:69` lo retiró con un
motivo escrito:

> `RX550_GART_ENTRY_COUNT` y `RX550_GART_INDEX_MAX` se han retirado. Eran una
> segunda autoridad de rango global: un indexador que acota por 65536 acepta un
> offset que la apertura que el caller tiene delante rechazaría.

Cadena causal completa, y por qué nadie la vio:

```
rx550_vmid0_gart.h retira la constante (con motivo)
        ↓
rx550_gart_write.c:39 sigue usándola      → ESA UNIDAD DE TRADUCCION NO COMPILA
        ↓
tests/Makefile `obj` del modulo = rx550_target.o pci_resource.o
        rx550_mmio_access.o                  → rx550_gart_write.c NO esta en el modulo
        ↓
tests/Makefile `run` = 7 suites, y test_gart_write no era una de ellas
        ↓
NINGUNA puerta compila ese .c  →  el defecto no tiene por donde aparecer
```

`STATE = PROVEN` por compilación: `gcc` devuelve `‘RX550_GART_ENTRY_COUNT’ no se
declaró aquí`. El `tests/test_gart_write.c` usaba la misma constante 7 veces y
tampoco compilaba, así que esa suite —**59 aserciones sobre la política de
escritura del backing**— llevaba tiempo sin existir como binario.

## 4. Lo que la retirada acertó, y lo que la constante no era

Aquí es donde la lectura rápida se equivoca, y conviene dejarlo escrito porque
el error va en la dirección contraria al intuitivo.

**No** era un número inventado. 65 536 es correcto para la apertura por
defecto, y sale de una cuenta del corpus:

```
amdgpu_gart.c:533   adev->gart.num_gpu_pages = adev->gmc.gart_size / AMDGPU_GPU_PAGE_SIZE
amdgpu_gart.h:33    AMDGPU_GPU_PAGE_SIZE = 4096
gmc_v8_0.c:595      CHIP_POLARIS12 → adev->gmc.gart_size = 256ULL << 20

256 MiB / 4 KiB = 65 536 entradas          ← de aquí sale, y es DERIVED
```

**Lo que no era un hecho** es que 65 536 valiera *siempre*, porque `gart_size`
depende de un parámetro de módulo:

```
amdgpu_drv.c:154    int amdgpu_gart_size = -1;              /* auto */
amdgpu_drv.c:293    module_param_named(gartsize, amdgpu_gart_size, uint, 0600)
gmc_v8_0.c:604-605  adev->gmc.gart_size = (u64)amdgpu_gart_size << 20;
gmc_v8_0.c:608      adev->gmc.gart_size += adev->pm.smu_prv_buffer_size;
```

Contrafactual medido sobre la aritmética del propio corpus, en **esta** ASIC:

| `gartsize` | `gart_size` | entradas |
|---|---|---|
| `-1` (auto) | 256 MiB | **65 536** |
| `1024` | 1 GiB | **262 144** |

Con `gartsize=1024` — un parámetro `0600`, escribible por root, que el driver de
referencia acepta (`amdgpu_device.c:1556` solo rechaza valores `< 32`) — esta
misma tarjeta tiene una apertura de **262 144** entradas. La comprobación que se
quitaba habría **rechazado un backing legítimo**.

> La retirada fue CORRECTA. `RX550_GART_ENTRY_COUNT = 65536` era una decisión de
> configuración congelada en forma de constante, y una constante que depende de
> un parámetro de módulo no es una autoridad de rango. Lo que estaba mal no era
> la retirada: era que **la retirada se quedó a medias**, y en un fichero que
> nadie compilaba.

Corolario que se escribe para que no se repita: `PROVEN_ABSENT` habría sido la
etiqueta equivocada. La constante no era inventada; era *derivada de un
parámetro*. Reponerla —que es lo que hace el compilador cuando falla— habría
reintroducido un tope 4× por debajo de una apertura válida, y esta vez
compilando.

## 5. La reparación

Tres ficheros, y el tercero es la parte que hace que la reparación sea
comprobable.

**`rx550_gart_write.c`** — fuera la comprobación, con su motivo y **con lo que
se pierde** escrito dentro del código:

```
NO HAY AUTORIDAD DE RANGO GLOBAL AQUI, y no hay por qué ponerla.
  ... la cuenta es gart_size / 4096, y gart_size NO es una constante ...
LO QUE QUEDA, y basta para no escribir fuera del backing: la cota del CALLER,
  D (n <= entries), B (first <= entries) y E+F (first + n <= entries, por resta).
LO QUE SE PIERDE: este componente ya no detecta un backing que declare MÁS
  entradas de las que reservó. Eso lo detecta quien reserva.
```

La cota contra escritura fuera del backing **no se pierde**, y eso es
comprobable por lectura: de E+F (`n > b->entries - first.index`, con B ya
garantizando `first <= entries`) sale que todo índice escrito está en
`[0, entries-1]`, donde `entries` es la declaración del *caller*. Lo único que
desaparece es el rechazo del backing *mentiroso* — que era un bug del caller
enmascarado.

**`rx550_vmid0_gart.h:32`** — la línea `DERIVED` seguía anunciando
`ENTRY_COUNT = 65536` en el mismo fichero que la retiraba en la línea 69.
Contradicción interna de un solo fichero, y una pista falsa para quien lo lea.
Ahora dice la **fórmula** y de dónde sale.

**`tests/test_gart_write.c`** — 65 536 pasa a ser `TABLE_N`, constante local del
test, con el motivo en el propio `TABLE_N`. Y **un caso cambió de semántica**,
que es el contenido real del hallazgo:

| | antes | después |
|---|---|---|
| backing de 65 537 entradas | `RECHAZADO` | **`NO rechazado`** |
| motivo | `> RX550_GART_ENTRY_COUNT` | no hay cota global; el índice se acota contra `b->entries` |

Ese `CHECK` existe para que **volver a poner una cota global salga en rojo**, no
en verde. Es un `NEGATIVE_RESULT` convertido en puerta.

## 6. El instrumento no detectaba una guarda: resultado negativo propio

Antes de dar la reparación por buena había que comprobar que la suite **puede**
fallar. Con `make run` en verde no se sabe nada de eso, así que se reinsertó cada
defecto uno a uno, sobre **copias en `/tmp`**, sin tocar el corpus:

| mutación | rc | recuento | `CHECK` que se puso rojo |
|---|---|---|---|
| corpus, reparado | **0** | 59 / 0 | — |
| reintroducir la cota global (`entries > 65536`) | 1 | 58 / 1 | `5. backing de 65537 entradas: NO rechazado` |
| quitar la guarda `E+F` (la resta) | 1 | 37 / **65 538** | `5. y el centinela posterior NO fue sobrescrito` |
| cambiar `B` de `>` a `>=` | **0** | 59 / 0 | — ninguno |
| **quitar la guarda `B` entera** | **0** | 56 / 0 | — **ninguno** |

Dos filas de esa tabla son **resultado negativo**, y una de ellas es un defecto
de mi propio instrumento.

### 6.1 `B` de `>` a `>=`: mutación mal elegida, no resultado

`>=` es *más estricto* que `>` en ese predicado: rechaza también `first ==
entries`. Lo que se expulsaba es un rechazo que E+F ya producía. Mutación
equivocada, descartada, y dicho aquí para que no se lea como una guarda sin
dientes.

### 6.2 Quitar `B` entera: la suite daba verde con el componente mutilado

Ésta sí es una avería del instrumento, y la más útil de la tabla.

`B` es `first.index > b->entries`. `E+F` es `n > b->entries - first`. Cuando
`first > entries`, la **resta se va por debajo de cero en `unsigned` y da
`UINT64_MAX`**, luego `E+F` deja pasar cualquier `n`: **`B` es el único que puede
atrapar ese caso.** Y la suite tenía exactamente un caso así —`first=1000` sobre
un backing de 4— con los centinelas **pegados al array** (`small.lo`, `small.hi`,
a 0 y a 4). Una escritura 1 000 entradas más allá no toca ni `small.t[0..3]` ni
los centinelas: sus cuatro `CHECK` seguían en verde mientras el componente
escribía 1 000 palabras fuera del array.

> Un centinela pegado al array detecta el desbordamiento **pegado**. No detecta
> el lejano. El `PASS` no era mentira: era un `PASS` de menos.

Se añadió el caso **5b**, con la fuga cayendo **dentro** de la reserva: backing
de **una** entrada en `guard[1]` de un `uint64_t guard[4]`, canarios en
`guard[0]` y `guard[3]`, y `first.index = 2`. Con `B` no se escribe nada; sin
`B` la escritura cae exactamente sobre `guard[3]`. Cero comportamiento indefinido
en los dos lados.

**Re-medido:**

| | rc | recuento | `CHECK` rojo |
|---|---|---|---|
| corpus, reparado | 0 | **59 / 0** | — |
| reintroducir la cota global | 1 | 58 / 1 | `5. backing de 65537 … NO rechazado` |
| quitar la guarda `B` | 1 | 58 / 1 | `5b. y el canario al que CAERÍA la fuga, intacto` |

### 6.3 Un fallo mío, de los que la suite no perdona

Al meter el bloque 5b **en medio** del caso 5, los cuatro `CHECK` siguientes
(`5. first=0 con 4 entradas … válido`) se pusieron rojos: el bloque reasignaba
`b.base` y `b.entries`, y los casos siguientes escribían sobre el backing
equivocado. Restaurado al final del bloque, con la forma del fallo escrita en el
código. *Un caso nuevo que cambia el estado compartido rompe los casos viejos
aunque no los toque.*

## 7. La puerta, que era el otro mitad del defecto

Un `.c` que no compila y que nadie compila es invisible por construcción. La
mitad de la reparación es que **exista una puerta que lo alcance**.

`tests/Makefile`: la cola de `run` pasa de **7 a 15** suites. Los conjuntos de
ficheros de cada regla son **mínimos, medidos** quitando uno a uno hasta que el
enlazador se queja; una regla que lista de más construye un binario distinto del
que se midió, y entonces la puerta mide otra cosa. `test_ib_bridge` necesita un
`-I` aparte porque `pm4.h` vive en `04-IMPLEMENTACION/rx550-pm4/`, no en el
directorio del driver.

```
make -s run   →  rc 0
  15 suites C · 2 814 aserciones
  test_static.sh · 34 PASS (T1-T14 + auditorías de .ko)
```

**Reproducibilidad**: dos corridas de `make -s run`, salidas **byte a byte
idénticas**, `rc=0` ambas. Artefactos en
`08-ARQUITECTURA/artifacts/Q8-TEST-MATRIX/gate-run-{1,2}.txt`.

## 8. Lo que queda abierto, con su nombre

```
test_mem  NO COMPILA  ·  Q2, otra sesión, no es de este nodo
    target_mem_host.h:19  typedef unsigned long long u64;  →  conflicto de tipos
    con el u64 que el propio test_mem.c define.  El tests/Makefile ya lo excluye
    de la cola por esto, desde antes de hoy.  MEDIDO 2026-10-03: igual que
    entonces, mismo error, sin cambios.  NO SE TOCA: es trabajo ajeno en vuelo.

16 → 15 en la puerta.  El 16º es test_mem, y no por esta sesión.
```

## 9. Límites de este hallazgo

1. **RUNTIME = NOT_RUN.** Nada de esto habla de la GPU. Un `PASS` en userspace
   sobre un modelo de entradas **no** prueba que una entrada escrita llegue al
   hardware. `rx550_gart_write_is_executed()` sigue devolviendo `false` por
   construcción, y eso no ha cambiado.
2. El contrafactual de `gartsize=1024` es **aritmética sobre el corpus**, no una
   lectura de `/sys/module/amdgpu/parameters/gartsize` en esta máquina. La
   propiedad del parámetro (modo `0600`, rechazable si `< 32`) sí está leída del
   corpus. El valor **real** en esta placa sigue siendo `DEFERRED_RUNTIME`.
3. `smu_prv_buffer_size` (gmc_v8_0.c:608) se suma a `gart_size` y no se ha
   medido su valor. Refuerza la conclusión —el count no es constante— pero el
   número exacto de entradas de esta placa no se afirma aquí.
4. La retirada de la constante la hizo otra sesión y **no se revisa aquí si fue
   correcta en todo lo demás**: se constata que era correcta en el punto medido.
5. `Q8` no queda `CLOSED`. Queda `PARTIAL`: la puerta existe y mide 15 de 16,
   y la 16ª depende de trabajo ajeno.

## 10. Procedencia, para que esto sea reproducible sin este fichero

```
sha256  d784bb1638bf99b554b5fc31e358689080b8ed2ba3d1754492381c39aa7e0e23
        04-IMPLEMENTACION/rx550-driver/rx550_gart_write.c
sha256  ad2c595836b53d83701c10b4f0cc6630a0e30a4c02144ea2232d42f3052f9686
        04-IMPLEMENTACION/rx550-driver/rx550_vmid0_gart.h
sha256  e4f9b510b431e02042a703680ebf45af18cffbf62ca9f2684289bd37cf303fad
        04-IMPLEMENTACION/rx550-driver/tests/test_gart_write.c
sha256  28e3b58255916892149164335cd2148cc55ffeb50d28bfb8db94e5e06b6b0c8c
        04-IMPLEMENTACION/rx550-driver/tests/Makefile

las dos salidas de la puerta tienen el MISMO hash, que es la forma de decirlo:
sha256  0280d616a3dd774c93f4acf498aabf324a5b30fd8e250ffba357e56a90bbe4f7
        08-ARQUITECTURA/artifacts/Q8-TEST-MATRIX/gate-run-1.txt
sha256  0280d616a3dd774c93f4acf498aabf324a5b30fd8e250ffba357e56a90bbe4f7
        08-ARQUITECTURA/artifacts/Q8-TEST-MATRIX/gate-run-2.txt

FLAGS   -O2 -Wall -Wextra -Werror   ·  gcc $(gcc -dumpversion)   ·  userspace, uid 1000
COMPILAR cd 04-IMPLEMENTACION/rx550-driver/tests && make -s run
```

El fichero de la prueba de mutaciones (`5b`) no está en el repositorio: la
mutación se aplica sobre una copia en `/tmp/opencode/drv-q8/mut*/` y se tira. Lo
que queda es el caso `5b` en el test, que es lo que hay que poder reejecutar.

## 11. Un fallo mío, en la mecánica, que casi fue peor que el defecto

Lo dejo escrito porque `COORDINACION.md` § Regla 5 dice que un problema de otro es
de otro, y esto **me** pasó y casi no es de otro:

```
git commit --amend --no-edit -- <unpath>
```

Se usó para anexar el estado canónico a este turno. Pero entre mi commit y el
`--amend` **otra sesión commiteó** (978), así que el `HEAD` ya no era el mío y el
`--amend` **reescribió su commit**: mi fichero entró dentro de su commit `978`, con
su mensaje, que no dice nada de él. Firma del síntoma: el `git show --stat` de su
commit listaba dos ficheros y el suyo no los tenía antes.

Recuperado, y esto es lo que hay que copiar:

```
git reflog            →  el hash original: b18c465
git reset --soft <hash-original>
git commit -- <solo-mi-path>
```

`--soft` y no `--mixed` ni `--hard`, por una razón concreta: **el índice tenía
trabajo ajeno staged** —el borrado de `975-corregcion-a-974-…`, de la otra
sesión— y `--mixed` lo des-stagearía, `--hard` además le pisaría el árbol de
trabajo. Con `--soft` el índice queda idéntico y un `git commit -- <path>`
sube solo mi fichero.

Estado tras la recuperación, comprobado:

```
b18c465  978 del otro        1 fichero, identico al original
ba11b77  977 (bis) mio       1 fichero, DRIVER-MISSION-STATE.md
10a798d  977 mio             8 ficheros, el hallazgo y la reparacion
staged ajeno                 intacto
```

La lección, que es la generalización del §6.3 y más fuerte que él:

> **`--amend` no es "arreglar mi commit". Es "reescribir el commit que tenga
>HEAD ahora mismo".** En un árbol compartido donde seis sesiones commitean, entre
>el `git add` y el `git commit` el `HEAD` puede haber cambiado. Un `--amend` con
> pathspec **no** está protegido por el pathspec: reescribe la commit entera.

La defensa no es tener cuidado: es no usar `--amend` en un árbol compartido. Un
commit rehecho es otro commit, con su hash nuevo, y el hash viejo sigue
funcionando solo porque nadie lo había anotado todavía.

## 12. Qué cambió de estado

```
RX550_GART_ENTRY_COUNT como cota global de rango   REFUTED   (contrafactual gartsize=1024)
  antes: PROVEN en 3 ficheros, uno de ellos sin compilar
rx550_gart_write.c  compila                         PROVEN   (gcc -Werror, antes: no)
test_gart_write    ejecuta                         PROVEN   (59/0, antes: no compilaba)
guarda B del batch writer                           DETECTABLE  (antes: undetectable)
tests/Makefile run                                  7 → 15 suites, 2 848 aserciones, rc 0 ×2
Q8 TEST_MATRIX                                      OPEN → PARTIAL
```