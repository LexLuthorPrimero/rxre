# 1021 · `test_mem` era un verde sobre un fuente que no compilaba, y el contrato de direcciones no lo comprobaba nadie

`CLASSIFICATION=MEASUREMENT` · `TRACK=BOTH` · `CORPUS=RESEARCH/kernelbuild/linux-7.1.3`
`WORK_CLASS=REPAIR/CONTROLLED` · `WRITE_EXECUTION=NONE` · `MODIFICATIONS=4`
`RUNTIME=NOT_RUN` · `GPU INTACTA`

---

## Qué se afirmaba

`04-IMPLEMENTACION/rx550-driver/tests/Makefile` excluía `test_mem` de la cola
de build por escrito, y el motivo estaba anotado con fecha y measurement:

```
# test_mem queda FUERA de la cola: Q2 lo esta escribiendo otra sesion en este
# mismo workspace y su test_mem.c esta a medio escribir (no incluye target_mem.h
# y target_mem_host.h duplica sus typedefs). No se bloquea la suite propia con
# trabajo ajeno en vuelo, y no se tocan sus ficheros.
# MEDIDO 2026-10-03: sigue sin compilar, por el mismo conflicto de typedef de
# `u64` entre target_mem_host.h y el propio test.  No es de esta sesion.
```

Es decir: la cobertura se declaraba incompleta **a sabiendas**, con el motivo
correcto en su mayor parte —el fuente no compilaba— y con una razón de fondo
equivocada —«es trabajo de otra sesión»—.

## Qué se midió

Con el árbol tal como estaba:

```
$ gcc -O2 -Wall -Wextra -Werror -I. -o /tmp/tm tests/test_mem.c
test_mem.c:20:18: error: conflicting types for 'u64'
./target_mem_host.h:19:33: note: previous declaration of 'u64'
./target_mem_host.h:22:33: error: 'bool' cannot be defined via 'typedef'
test_mem.c:37:15: error: 'TM_PAGE_SIZE' no se declaró aquí
$ echo $?
1
```

Cuatro errores, y **ninguno dependía de que otra sesión terminara nada**:

| # | Desacuerdo | Dónde |
|---|---|---|
| 1 | `test_mem.c` declara sus propios `u8/u32/u64`; `target_mem_host.h` también | `test_mem.c:18-20` vs `target_mem_host.h:16-19` |
| 2 | Usa los `TM_*` sin incluir `target_mem.h`, que es donde están | `test_mem.c:37` |
| 3 | `typedef int bool` es ilegal desde C23, y C23 es el estándar por defecto de este gcc 16.2 | `target_mem_host.h:22` |
| 4 | El binario `tests/test_mem` en el árbol estaba fechado **2026-09-29** y venía de otro fuente | `ls -la tests/test_mem` |

El punto 4 es el que importa. Ese binario **ejecutaba y daba 72 PASS en verde**
sobre código que ya no existía. La primera versión de la tool de contratos de
este trabajo lo ejecutó, vio 72 marcas `PASS`, 0 `FAIL`, salida 0, y lo
reportó como `pasa_pero_no_lo_ejecuta_nadie` — un veredicto que, sin leer el
Makefile, parecía un agujero de cobertura.

Sólo el comentario del Makefile contradiciendo el dato hizo aparecer el
problema. Un artefacto viejo que se consume como evidencia (§27, §82) es
exactamente la trampa, y estaba en verde.

## El agujero, demostrado y no arguido

Con el árbol **intacto** —nada modificado todavía— se mutó una constante del
contrato de direcciones y se ejecutó la puerta canónica:

```
$ sed -i 's/^#define TM_NR_DIR_LEVELS\t1u$/#define TM_NR_DIR_LEVELS\t2u/' target_mem.h
$ make -s -C tests run ; echo $?
0
```

**`make -C tests run` sale 0 con el contrato de geometría roto.**

Qué rompe esa mutación: `TM_VA_BITS = TM_LEVEL_BITS * (TM_NR_DIR_LEVELS + 1) + TM_PAGE_SHIFT`.
Con `TM_NR_DIR_LEVELS = 2` la GPUVA pasa de **30 bits (1 GiB)** a **39 bits
(512 GiB)**, y `TM_VA_SIZE` con ella. El único test que verifica esas constantes
es `test_mem`, y `test_mem` no estaba en la puerta.

Que el resto de la suite no lo detecte no es casualidad: no hay ningún otro
fichero del componente que compruebe un solo `TM_*`.

```
$ for s in TM_PAGE_SIZE TM_LEVEL_ENTRIES TM_VA_BITS TM_PN_MASK TM_PA_BITS \
           TM_NR_DIR_LEVELS; do
    printf '%-20s ' $s; grep -l "\b$s\b" tests/*.c | tr '\n' ' '; echo
  done
TM_PAGE_SIZE         test_mem.c
TM_LEVEL_ENTRIES     test_mem.c
TM_VA_BITS           test_mem.c
TM_PA_BITS           test_mem.c
TM_NR_DIR_LEVELS     test_mem.c
```

## Lo que se corrigió, y por qué cada corrección es mínima

**`tests/test_mem.c`** — se quitan los typedef duplicados y se incluye
`target_mem.h`, que es lo único que hace falta: `target_mem.h` ya arrastra
`target_mem_host.h` en userspace (línea 34-39). Siete líneas fuera, una dentro.

**`target_mem_host.h`** — el `typedef int bool` se condiciona a
`__STDC_VERSION__ < 202311L`. No se comprueba el compilador sino la versión del
estándar, para que el mismo fuente sirva en las dos ramas.

**`target_mem.h`** — dos añadidos, ambos materializaciones de algo que ya
existía:

- `TM_PN_MASK = (1ull << TM_PN_BITS) - 1ull`. No es un número nuevo: es
  `0x0FFFFFFF`, que es exactamente lo que `test_vm` ya verifica contra
  `gmc_8_2_sh_mask.h` (`PHYSICAL_PAGE_NUMBER mask == 0xfffffff`). El header
  sólo decía «28 bits» y quien quisiera la máscara tenía que reconstruirla.
- `tm_pde_is_valid(e)`, que devuelve `(e & TM_PTE_VALID) != 0`. No es semántica
  nueva: `tm_pde_make()` ya marca ese mismo bit, y `amdgpu_vm_pt.c` escribe
  `_PAGE_ENTRY_VALID` en PDE y en PTE alike. Lo que faltaba era el lector de un
  tipo de entrada que ya tenía escritor.

## Dos aserciones del test que eran falsas, y quién tenía razón

Al compilar por primera vez, `test_mem` dio **35 pass, 3 fail**. Ninguna era un
defecto del contrato; dos eran vectores de prueba mal construidos y una era una
relación que no existe.

### Las dos del índice de PTB — el test estaba mal, el corpus lo dice

El test afirmaba que el índice de PTB «se reinicia tras 2 MiB», y para
comprobarlo usaba `0x00100000`. Eso es **1 MiB**, no 2 MiB. A 1 MiB el índice
vale `(0x100 >> 0) & 511 == 256`, que es lo correcto, y el test pedía `0`.

El discriminante no es la opinión de nadie, es el corpus:

```
amdgpu_vm_pt.c:191:   idx = (cursor->pfn >> shift) & mask;
```

y en el nivel PTB `shift` es `TM_PAGE_SHIFT` (12) y `mask` es 511. El índice se
envuelve cuando `pfn` llega a 512, es decir a los 2 MiB. El contrato
`tm_ptb_index()` hace exactamente eso. Lo que estaba mal era el vector.

```
- tm_ptb_index(0x00100000) == 0    "se reinicia tras 2 MiB"   [1 MiB, no 2]
- tm_ptb_index(0x00101000) == 1    "correcto tras 2 MiB"       [encadenado]
+ tm_ptb_index(0x00100000) == 256  "a 1 MiB = 256, aun sin reinicio"
+ tm_ptb_index(0x00200000) == 0    "se reinicia a los 2 MiB"
+ tm_ptb_index(0x00201000) == 1    "correcto tras 2 MiB"
```

### La tercera — una identidad imposible, retirada con su motivo

```c
CHECK(TM_VA_SIZE == (1ull << (TM_PA_BITS - 30)), "VA y PA coherentes entre si");
```

Por definición `TM_VA_SIZE == 1 << TM_VA_BITS == 2^30`. El lado derecho es
`2^(TM_PA_BITS - 30)`. Para que coincidan haría falta `TM_PA_BITS == 60`. GFX8
tiene 40 bits de dirección física (`gmc_v8_0.c:1127`,
`amdgpu_vm_adjust_size(adev, 64, 9, 1, 40)`).

No es un valor mal puesto: es una **relación que no existe**. El espacio de VA y
el de PA son magnitudes independientes y ningún ASIC obliga a que uno sea función
del otro. Se retira la aserción y se deja escrito por qué, en el sitio, con la
aritmética. Arreglarla con una fórmula inventada sería fabricar una coherencia que
el hardware no impone (§65).

## El discriminante, después

La misma mutación, con `test_mem` en la cola:

```
$ sed -i 's/TM_NR_DIR_LEVELS\t1u$/TM_NR_DIR_LEVELS\t2u/' target_mem.h
$ make -s -C tests run ; echo $?
  FAIL  GFX8: un nivel de directorio + PTB
  FAIL  GPUVA de 30 bits
  FAIL  1 GiB de VA
  35 pass, 3 fail
1
```

**Mismo cambio, misma puerta, resultado opuesto: de 0 a 1.** El agujero está
cerrado y el cierre está medido, no declarado.

Estado final de la puerta: 17 suites invocadas, 0 problemas.

```
$ ./tools/contratos.sh ; echo $?
...
./test_mem   0  0  1489  38  0  OK   marcadores=38
# TOTAL  invocadas=17  con_problema=0  indirectas=1
0
```

## Herramienta que salió de esto

`tools/tu_compila.sh` y `tools/contratos.sh`, ambas con el error de la propia
autoría anotado donde se cometió, porque es la parte que no se puede recuperar
leyendo el código:

- **`grep -c ... || echo 0`** imprime *dos* líneas cuando no hay coincidencias
  (`grep` ya imprime `0` y sale con 1, así que también corre el `echo`). El
  contador salía partido y descuadraba la columna. Se usa `|| true` y luego un
  default.
- **Contar `PASS` en mayúscula** daba 0 sobre binarios que imprimen `passed:` en
  minúscula. Un test que pasa 1238 aserciones aparecía como el que no verifica
  nada.
- **Cruzar el `PASS` del resumen con el de los marcadores** dio 2 falsos
  positivos: `test_regs` imprime 12 líneas y resume 32, porque dentro de
  R02/R05b/R07 hay bucles sobre 10 entradas que suman sin imprimir línea por
  aserto. Unidades distintas; no se cruzan. El único número que tiene que valer
  0 por dos vías es el de fallos, y el exit code es la tercera.
- **Buscar `./test_target_match` en `test_static.sh`** no lo encuentra, porque
  ahí se invoca como `"$HERE/test_target_match"`. Ese falso positivo era peor
  que no mirar: inducía a «arreglar» algo que ya se ejecutaba.

Self-test de `contratos.sh`, con el árbol copiado a `/tmp` y la copia provista de
los tres componentes (las rutas del corpus son relativas y sólo resuelven desde
la ubicación canónica — otra limitación de reproducibilidad, §87):

| vector | resultado esperado | resultado |
|---|---|---|
| árbol intacto | 0 problemas | 0 |
| aserto invertido en `test_pdb0` | FALLO detectado | `ROTA(salida=1)`, exit 1 |
| binario ausente | detectado | `ROTA(salida=127)` |
| árbol reubicado sin corpus | detectado como degradación | 4 tests `ROTA`, y el recuento de aserciones cae de 79 a 65 |

## Estado de la afirmación

- `test_mem` **ya no es un artefacto viejo**: está en la cola de build, y un
  fuente que no compile es un fallo de build, no un verde falso.
- El contrato de direcciones de `target_mem.h` tiene verificador y está
  verificado por una puerta que se ejecuta.
- `TM_NR_DIR_LEVELS`, `TM_VA_BITS`, `TM_VA_SIZE`, `TM_PN_BITS`, `TM_PA_BITS`,
  `TM_PN_MASK`, `TM_PAGE_SIZE`, `TM_LEVEL_ENTRIES` quedan bajo aserción
  ejecutable.
- Lo que **no** se afirma: nada de esto dice que el hardware obedezca. Dice que
  las funciones del contrato son coherentes con la geometría declarada, y que la
  geometría declarada está fundamentada en el corpus. La obediencia sigue siendo
  `RUNTIME_REQUIRED`.
- El motivo del Makefile («trabajo de otra sesión») estaba caducado. Era una
  atribución a un actor que ya no existe; los cuatro desacuerdos eran concretos
  y estaban todos en este árbol.

## Lo que este hallazgo no arregla

`target_mem.h` sigue sin entrar en el `.ko`: `rx550_drv-objs` son sólo tres
objetos y el componente tiene once unidades de traducción. Eso es otra frontera,
con su propia medida (`tools/tu_compila.sh`), y no se mezcla aquí.

## Trazabilidad

- Fuente primaria del discriminante del índice: `amdgpu_vm_pt.c:191`
- Fuente primaria de los 40 bits de PA: `gmc_v8_0.c:1127`
- Fuente primaria de la máscara de PN: `gmc_8_2_sh_mask.h`, vía `test_vm` V1a
- Contrato verificado: `target_mem.h`, `tests/test_mem.c`
- Puerta: `tests/Makefile`, target `run`, 17 suites
- Herramientas: `tools/contratos.sh`, `tools/tu_compila.sh`
- Prefijo de numeración: 1021, reservado antes de escribir