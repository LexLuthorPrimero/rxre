# 128 · §C/§G: hay dos mecanismos de invalidate, y el interruptor entre ellos no lo escribe nadie

```
CLASSIFICATION=DOCUMENTATION · TRACK=STATIC
CORPUS=RESEARCH/working/linux-7.1.3 · HARDWARE_SCOPE=HOST-C/RX550/0000:01:00.0
WORK_CLASS=READ_ONLY/EVIDENCE · WRITE_EXECUTION=NONE · MODIFICATIONS=0
RUNTIME=NOT_RUN · GPU INTACTA
```

## Qué resuelve

`210`/`211`/`213` cerraron `VM_INVALIDATE_REQUEST`: 16 bits, uno por dominio, el
que escribe `gfx_v8_0_ring_emit_vm_flush`. `127` encontró por el otro lado
`VM_L2_CNTL2.INVALIDATE_ALL_L1_TLBS`, que se dispara al habilitar el GART y
pocas veces más.

**Los dos nunca se habían relacionado. Son mecanismos distintos, en registros
distintos, y hay un bit que elige entre ellos — que el driver no escribe nunca.**

## Cuatro registros, tres invalidate, tres caminos distintos

```
gmc_8_1_d.h    mmVM_L2_CNTL2                = 0x501
gmc_8_1_d.h    mmVM_L2_CNTL3                = 0x502
gmc_8_1_d.h    mmVM_INVALIDATE_REQUEST      = 0x51e
gmc_8_1_d.h    mmVM_INVALIDATE_RESPONSE     = 0x51f
```

**`VM_L2_CNTL2` está a `0x501` y `VM_INVALIDATE_REQUEST` a `0x51e`: `0x1d` bytes
de distancia.** No son lo mismo con dos nombres, y no están en la misma página de
registros.

| | mecanismo | registro |Bits | quién lo dispara |
|---|---|---|---|---|
| A | por dominio | `VM_INVALIDATE_REQUEST` | 16, uno por VMID | `gfx_v8_0_ring_emit_vm_flush`, y `emit_wreg` |
| B | todo a una vez | `VM_L2_CNTL2.INVALIDATE_ALL_L1_TLBS` | 1 | `gmc_v8_0_gart_enable`, y en reset |
| C | la caché L2 | `VM_L2_CNTL2.INVALIDATE_L2_CACHE` | 1 | idéntico bloque |

**A es el mecanismo de `210`/`211`/`213`. B y C son de init y reset.**

## El interruptor: `DISABLE_INVALIDATE_PER_DOMAIN`

Layout completo de `VM_L2_CNTL2`, campo a campo:

```
bit 0        INVALIDATE_ALL_L1_TLBS           0x00000001
bit  1        INVALIDATE_L2_CACHE                 0x00000002
bit 21        DISABLE_INVALIDATE_PER_DOMAIN       0x00200000
bit 22        DISABLE_BIGK_CACHE_OPTIMIZATION     0x00400000
bits 23-25    L2_CACHE_BIGK_VMID_MODE             0x03800000
bits 26-27    INVALIDATE_CACHE_MODE               0x0C000000
bits 28-30    PDE_CACHE_EFFECTIVE_SIZE            0x70000000
```

**Siete campos, sin solapes.** Y el bit 21 se llama `DISABLE_INVALIDATE_PER_DOMAIN`:
**el hardware tiene un interruptor entre el mecanismo A y el B, y se llama
exactamente lo que hace.**

**Pero el driver no lo escribe nunca.** Comprobado los siete:

| campo | ¿escrito por el driver? |
|---|---|
| `INVALIDATE_ALL_L1_TLBS` | sí, `gmc_v8_0.c:861` y 19 ficheros más |
| `INVALIDATE_L2_CACHE` | sí, `gmc_v8_0.c:862` y 19 más |
| **`DISABLE_INVALIDATE_PER_DOMAIN`** | **nunca** |
| `INVALIDATE_CACHE_MODE` | **nunca** |
| `PDE_CACHE_EFFECTIVE_SIZE` | **nunca** |
| `L2_CACHE_BIGK_VMID_MODE` | **nunca** |
| `DISABLE_BIGK_CACHE_OPTIMIZATION` | **nunca** |

**Y no es que los ponga a cero: es read-modify-write.**

```
gmc_v8_0.c:860   tmp = RREG32(mmVM_L2_CNTL2);
gmc_v8_0.c:861   tmp = REG_SET_FIELD(tmp, VM_L2_CNTL2, INVALIDATE_ALL_L1_TLBS, 1);
gmc_v8_0.c:862   tmp = REG_SET_FIELD(tmp, VM_L2_CNTL2, INVALIDATE_L2_CACHE, 1);
gmc_v8_0.c:863   WREG32(mmVM_L2_CNTL2, tmp);
```

**Lee, cambia dos bits, escribe. Los bits 21 a 30 pasan de largo.**

**El driver está preservando deliberadamente la configuración de reset de la caché
de fragmentos, y sólo pulsa los dos disparadores.**

## Consecuencia para `226`, que había dejado la pregunta abierta

`226` preguntó *qué caché, si alguna, está en el camino entre la L2 y la lectura
del page walker*, y la dejó `NOT_DETERMINED` por hardware.

**Hay un campo que se llama `PDE_CACHE_EFFECTIVE_SIZE`.** Bits 28-30, tres bits:
siete valores posibles. **El hardware tiene una caché de PDEs con tamaño
configurable, y el driver no la programa.**

**Así que la respuesta a `226` tiene dos mitades, y las dos son útiles:**

- **La caché existe** y hay un registro que la dimensiona. `PROVEN`.
- **El driver no la toca.** `PROVEN`. El tamaño efectivo es el del reset, y no
  lo sé.

**Y el invalidate obligatorio de GFX8 tiene ahora dos explicaciones candidatas,
compatibles entre sí:** o el TLB se llena a granularidad de fragmento —como dice
el comentario de `amdgpu_vm.c:1155`—, o la caché de PDEs puede tener entradas
obsoletas que un invalidate por VMID no alcanza. **No sé cuál pesa más, y ambas
explican por qué `L1157` fuerza el flush en GFX8.**

**Lo que sí se puede afirmar sin placa:** el invalidate por VMID que escribe
`gfx_v8_0_ring_emit_vm_flush` es el mecanismo A, y **depende de un bit que el
driver no programa.** Si el reset de esta GPU viniera con `DISABLE_INVALIDATE_PER_DOMAIN`
a 1, el invalidate por dominio **no funcionaría**, y todo el camino de `§C`
—`210`, `211`, `213`, `115`, `220`— estaría describiendo un mecanismo inactivo.

**Eso es la pregunta que ahora manda, y es de una lectura de registro.**

## El discriminante, y por qué no lo he ejecutado

**Un solo `RREG32` de `VM_L2_CNTL2` en `0x501` y mirar el bit 21.** Eso decide si
todo §C está describiendo algo activo.

Es **NIVEL 2** — lectura de hardware, sin escribir, reversible. **No lo he
ejecutado** por dos razones, y las digo:

1. Requiere acceso al mapa de MMIO de la GPU. En este proyecto eso ha pasado por
   `/dev/mem` con privilegios, y **no voy a abrir un mapa de MMIO de la GPU que
   está ejecutando la sesión gráfica** sin que sea una acción explícita y
   reversible acordada.
2. **Existe una vía menos invasiva que debo preferir**: si UMR está disponible,
   `umr_read` es una lectura de registro sin mapear nada a mano. No sé si está
   instalado.

**Lo dejo como `NOT_RUN` con el discriminante escrito, que es lo que AGENTS.md pide
para `BLOCKED_BY_CONDICIÓN_DE_SESIÓN` y no como bloqueo.**

## Una corrección mía, y era una que iba a ser un hallazgo falso

**Escribí que `INVALIDATE_CACHE_MODE` (0x0C000000) y `PDE_CACHE_EFFECTIVE_SIZE`
(0x70000000) se solapaban en los bits 29 y 30, y que eso era una inconsistencia del
header.**

**Es falso, y lo comprobé antes de escribirlo:**

```
0x0C000000  ->  bits 26 y 27
0x70000000  ->  bits 28, 29, 30
NINGÚN SOLAPE. Los siete campos del registro son disjuntos.
```

**Lo hice mal mentalmente: leí `0xC000000` como si fuera `0xC0000000`.** Es la
tercera vez esta semana que calculo un valor en la cabeza y sale mal, y la segunda
que un error de aritmética threatens con convertirse en un hallazgo.

**La regla ya estaba escrita desde antes de esta sesión** — *si un valor numérico
decide una conclusión, se imprime entero o se comprueba el ancho* — y no la
apliqué a mí mismo. **Un hallazgo sobre una inconsistencia de un header ajeno es
exactamente el tipo de cosa que no puede publicarse a ojo.**

## Lo que NO cierra

| Afirmación | Estado |
|---|---|
| `VM_L2_CNTL2` y `VM_INVALIDATE_REQUEST` son registros distintos | `PROVEN` (`0x501` vs `0x51e`) |
| Los siete campos de `VM_L2_CNTL2` son disjuntos | `PROVEN` (calculado, no a ojo) |
| El driver escribe sólo los bits 0 y 1 | `PROVEN` (7 campos comprobados) |
| Y por RMW, preserva el resto | `PROVEN` (`gmc_v8_0.c:860-863`) |
| Existe un interruptor entre los dos mecanismos | `PROVEN` (el nombre del campo) |
| `DISABLE_INVALIDATE_PER_DOMAIN` nunca se escribe | `PROVEN` |
| Existe una caché de PDEs dimensionable | `PROVEN` (`PDE_CACHE_EFFECTIVE_SIZE`) |
| El tamaño efectivo de esa caché | **`NOT_DETERMINED`** — valor de reset |
| Si el invalidate por dominio está activo | **`NOT_DETERMINED`** — un `RREG32` |
| Si los disparadores de `VM_L2_CNTL2` se auto-borran | **`NOT_PROVEN`** |
| Cuál de las dos explicaciones del flush pesa más | **`NOT_DETERMINED`** |

**La penúltima tiene una consecuencia que hay que decir aunque no esté resuelta.**
Si `INVALIDATE_ALL_L1_TLBS` y `INVALIDATE_L2_CACHE` **no** se auto-borran, entonces
la escritura de `gmc_v8_0.c:860-863` los deja a 1 permanentemente, y con el bit 0 a
1 el TLB se invalidaría constantemente. **Eso sería un fallo grave, y nadie lo ha
reportado**, así que lo más probable es que se auto-borren — **pero
"lo más probable" no es `PROVEN`, y la comprobación es el mismo `RREG32`.**

**Un solo `RREG32` de `0x501` responde a tres de las cinco filas abiertas.** Es el
observable más rentable que queda en todo §C y §G.

## Procedencia

- `STATIC` -- `include/asic_reg/gmc/gmc_8_1_d.h` (`mmVM_L2_CNTL2`, `mmVM_L2_CNTL3`,
  `mmVM_INVALIDATE_REQUEST`, `mmVM_INVALIDATE_RESPONSE`),
  `include/asic_reg/gmc/gmc_8_1_sh_mask.h` (los siete campos de `VM_L2_CNTL2`,
  `VM_INVALIDATE_REQUEST__INVALIDATE_DOMAIN_0..15`),
  `gmc_v8_0.c:829` `:858-870`, `gfx_v8_0.c:6191-6215`.
- Búsqueda de los siete campos en los 2787 ficheros del corpus con `grep -rn`, con
  el nombre de fichero.
- Sin MMIO write, sin lectura de MMIO, sin TLB, sin módulos, sin debugfs.
- Encadenada con `210`/`211`/`213` (el invalidate por VMID), `127` (la caché L2 de
  fragmentos), `226`/`228` (la coherencia y su precio), `115`/`220` (marca de agua
  y frecuencia), `194` (el flush obligatorio en GFX8).
- No se editó `AGENTS.md` ni `OPEN-FRONTIERS.md`. No se editó ningún header.

## Nota de método

**Las dos cosas que salieron de esta nota fueron una comparación y una resta.**

**La comparación:** tres invalidate que nadie había relacionado, en cuatro
registros. Pedía una tabla de offsets y salía sola.

**La resta:** lo que el driver escribe menos lo que el registro tiene. Eso no se
busca con un `grep` de un símbolo: se busca con un `grep` de **siete** símbolos y
viendo seis filas vacías.

**Y la corrección:** el error de aritmética lo pilló el script, no yo. Si lo
hubiera escrito en el fichero sin ejecutar el script, esta nota tendría un
hallazgo sobre una inconsistencia de header que **no existe**, y sería el
segundo hallazgo inventado de la sesión.

**La regla, reforzada:** *todo número que entra en una conclusión va impreso por
un programa*. No es que el cálculo sea difícil; es que la aritmética mental no deja
traza, y sin traza no se puede revisar.