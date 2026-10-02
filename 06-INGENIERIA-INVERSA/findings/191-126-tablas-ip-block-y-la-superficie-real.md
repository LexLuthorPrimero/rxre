# 191 · Las 126 tablas `ip_block` del `.ko`, y la superficie real de los 9 bloques de esta placa

`CLASSIFICATION=DOCUMENTATION` · `TRACK=STATIC_BINARY` · `WORK_CLASS=READ_ONLY/EVIDENCE`
`WRITE_EXECUTION=NONE` · `MODIFICATIONS=0` · `RUNTIME=NOT_RUN` · `GPU INTACTA`
`CORPUS=RESEARCH/working/linux-7.1.3` + `/tmp/amdgpu_loaded.ko`
`HARDWARE_SCOPE=HOST-C/RX550/0000:01:00.0`
`DESARROLLA=los bloques DM/UVD/VCE que 190 destapo, y la pregunta abierta de 135`

## Cuestión principal

`190` Izzyó que el kernel registra **9** bloques IP, no 6, y que tres de ellos
—`dm`, `uvd_v6_3`, `vce_v3_4`— nunca se habían mirado. Eso abre bloques enteros
del hardware: decodificación de vídeo, codificación, y display.

La pregunta que había que responder no es "qué dice el fuente" —en el fuente todos
los bloques se ven iguales— sino **qué se registra de verdad en esta placa**, y
qué capacidades existen pero son inalcanzables.

## Criterio de terminación

Extraer del `.ko` cargado, sin desensamblar, la tabla de cada bloque registrado y
cuál de sus 24 campos está poblado. **Cumplido: 9/9, con dos anclas externas
independientes.**

## Herramienta

`08-ARQUITECTURA/tools/ip_surface.py`. Lee las **tablas constantes**, no código.

En un `.ko` (`ET_REL`) un puntero no es una dirección: es una **reubicación**.
Leer la struct cruda da ceros, que es indistinguible de "este ASIC no implementa
esa operación". La herramienta resuelve la reubicación hasta el símbolo destino, y
de ahí al nombre de la función.

## Las dos formas de puntero, y por qué la segunda es la mayoritaria

```
1. Reubicación contra un símbolo CON NOMBRE    -> el objetivo es ese símbolo
2. Reubicación contra un SÍMBOLO DE SECCIÓN    -> el objetivo es el símbolo que
   (nombre vacío) está en (sh_shndx, addend)
```

El caso 2 es el dominante: casi todas las tablas `ip_funcs` se referencian así,
con el offset en el addend. Verificado directamente:

```
.rela.rodata: sh_info=17 (.rodata)   entradas: 40372
  r_off=0x455e0  type=R_X86_64_64  sym=<vacio>  addend=0x45a60
```

Y `0x45a60` es exactamente el offset de `gfx_v8_0_ip_funcs` en `.rodata`. **El
addend es el puntero.**

## La superficie real de los 9 bloques

`struct amd_ip_funcs` (`amd_shared.h:454`) tiene 24 campos: `name` + 23 punteros.
Lo que sigue es qué punteros están **poblados** en esta placa:

| bloque | ver | n | campos implementados |
|---|---|---|---|
| `gfx_v8_0` | 8.0.0 | **17** | early_init late_init sw_init sw_fini hw_init hw_fini suspend resume is_idle wait_for_idle check_soft_reset pre_soft_reset soft_reset post_soft_reset set_clockgating_state set_powergating_state get_clockgating_state |
| `gmc_v8_1` | 8.1.0 | **17** | idéntica a la de gfx |
| `uvd_v6_3` | 6.3.0 | **17** | la anterior **+ prepare_suspend** |
| `sdma_v3_1` | 3.1.0 | 16 | sin `late_init` |
| `vce_v3_4` | 3.4.0 | 16 | sin `late_init` |
| `tonga_ih` | 3.0.0 | 15 | **sin `get_clockgating_state`** |
| `dm` | 1.0.0 | 15 | con `early_fini`, **sin `pre/post_soft_reset`** |
| `pp_smu` | 1.0.0 | 12 | **sin `wait_for_idle` ni `get_clockgating_state`** |
| `vi_common` | 1.0.0 | **11** | el mínimo |

### Tres regularidades que se ven sin buscar

- **`soft_reset` está implementado en los 9.** Los nueve bloques se pueden resetear
  por software. Es el suelo común de la arquitectura de IP.
- **`dump_ip_state` y `print_ip_state` no están en ninguno de los 9.** Esos dos
  campos son machinery de ASICs modernos para volcado de estado en crash; en GCN3
  no existen. **Un driver propio no puede apoyarse en ellos.**
- **`wait_for_idle` falta en `vi_common` y `pp_smu`**, y `get_clockgating_state`
  falta en `tonga_ih` y `pp_smu`. Cada bloque tiene una superficie propia; no hay
  una interfaz uniforme.

## La respuesta a la pregunta abierta de `135`

`135` preguntó cuál es la lista de capacidades por ASIC y quedó sin cerrar. **El
`.ko` la contiene entera: 126 tablas `*_ip_block`.**

```
126 bloques *_ip_block en el .ko
```

Y el grupo v8 tiene 10:

```
dce_v8_0  dce_v8_1  dce_v8_2  dce_v8_3  dce_v8_5
gfx_v8_0  gfx_v8_1
gmc_v8_0  gmc_v8_1  gmc_v8_5
```

De esos 10, **esta placa registra 2**: `gfx_v8_0` y `gmc_v8_1`.

**Eso separa las dos categorías que `135` no pudo separar**:
- **imposible aquí**: `gfx_v8_1` es de Fiji, `gmc_v8_0` de Tonga, `gmc_v8_5` de
  Fiji, y los cinco `dce_v8_*` son el DCE legacy que Polaris12 no usa (usa `dm`).
  Están en el binario y son inalcanzables.
- **117 tablas** en total son de otros ASIC.

**Para un driver propio esto es un mapa, no un misterio**: el hardware GCN3 de esta
placa es exactamente `gfx_v8_0` + `gmc_v8_1` + las siete de la lista, y nada más.

## Dos bugs de la herramienta, y por qué el self-test no los vio

**Bug 1 — índice de sección equivocado.** Indexaba las reubicaciones por el
índice de la sección RELA, no por `sh_info` (la sección a la que se aplican). Como
se buscaban con el índice de la sección de datos, **la búsqueda no encontraba
nada y todos los punteros parecían NULL**. Salía "funcs NULL en los 40 bloques".

**Bug 2 — filtro por sufijo.** `endswith("_ip_block")` también casa **funciones**:
`amdgpu_device_ip_get_ip_block` es código. Entraba como bloque con `type` y
`funcs` leídos de `.text`, y producía filas con basura que parecía dato. Lo
detecté porque una de ellas salía como `type=2425393296`.

**Bug 3 — solo símbolos de sección.** Resolvía la reubicación al símbolo, pero no
sabía seguir un símbolo de sección hasta su offset real. Faltaba el índice
inverso `(sección, valor) → nombre`.

### Y una debilidad real del self-test

Los tests 1-5 (layout, anclas, símbolos) **pasaban con el bug 1 presente**,
porque ninguno leía un puntero. Solo el test 6 —que exige que
`gfx_v8_0_ip_block.funcs` resuelva a `gfx_v8_0_ip_funcs`— lo cazó.

**Es la misma lección de `185`, por tercera vez**: el self-test tiene que
comprobar el dato **extraído**, no la estructura de quien lo extrae. Lo reescribí
para que el aserto sea sobre el valor final.

## Clasificación

| afirmación | estado |
|---|---|
| 126 tablas `*_ip_block` en el `.ko` | `PROVEN` — `ip_surface --todos` |
| Los 9 bloques de esta placa resuelven | `PROVEN` — 9/9 |
| Versiones coinciden con el log del kernel | `PROVEN_RUNTIME` — 9/9, dos fuentes |
| `soft_reset` en los 9 bloques | `PROVEN` — tabla de 24 campos |
| `dump_ip_state`/`print_ip_state` en ninguno | `PROVEN` |
| El grupo v8 tiene 10 tablas, se usan 2 | `PROVEN` — `ip_surface --generacion` |
| Las 8 restantes del grupo v8 son de otros ASIC | `DERIVATION` — del nombre del fichero fuente |
| `addend` = offset cuando el símbolo es de sección | `PROVEN` — lectura directa de `.rela.rodata` |
| El puntero NULL significa "el driver no lo implementó" | `LIMITE` — no implica nada del hardware |
| Las superficies por bloque son distintas entre sí | `PROVEN` — de 11 a 17 |

## Confounders

- **Un puntero NULL significa "el driver no lo implementó para este ASIC"**, NO
  "el hardware no lo puede hacer". `uvd_v6_3` sin `late_init` no implica que el
  UVD no necesite un teardown. Es un límite de la fuente y no lo cruzo.
- **Leo las tablas, no desensemblo.** No sé qué hace cada función, solo que existe.
- **`gfx_v8_0` y `gmc_v8_1` tienen superficies idénticas (17 campos)**, lo cual es
  una señal de que el orden de la tabla es un contrato entre bloques, no un hecho
  del hardware. Confunde un poco el conteo.
- **La atribución de las 8 tablas v8 no usadas a ASIC concretos la saqué del
  nombre del fichero fuente**, no de la tabla. Es `DERIVATION`.
- **El `.ko` es el de este host.** Si el driver se recompila, la herramienta hay
  que volver a correrla. No hay hash del `.ko` en el hallazgo.
- **No he verificado** que los 9 bloques se inicialicen todos con éxito; que estén
  *registrados* no es lo mismo que *funcionales*.

## Desfalsificación

- **(a)** 126 tablas → refutable con `ip_surface --todos`.
- **(b)** 9/9 versiones → refutable comparando con `journalctl -k`. **Verificado.**
- **(c)** `soft_reset` en los 9 → refutable con `--bloque gfx_v8_0_ip_block`.
- **(d)** Bug 1 → **verificado reintroduciéndolo**: el self-test falla con
  `gfx_v8_0_ip_block.funcs no se resolvio`.
- **(d2)** Bugs 2 y 3 → **detectados por inspección**, no por reintroducción.
  El 2 se vio porque una tabla salió con `type=2425393296`, y el 3 leyendo
  `.rela.rodata` a mano. **No los reintroduje**, así que no puedo afirmar que el
  self-test los cazaría: solo que los hallazgos que los delataron eran ciertos.
- **(e)** Las 8 tablas v8 no usadas → refutable en `vi.c:2065-2140`.
- **(f)** Que las superficies sean distintas → refutable con la tabla.

## UNLOCKS

- **`135` queda cerrado**: la lista de capacidades por ASIC son las **126 tablas**
  del `.ko`, extraídas mecánicamente.
- **La distinción imposible-aca / no explorada queda hecha**: de las 10 tablas
  v8, 2 son de esta placa y 8 son de otros ASIC.
- **§A/§E abren**: `uvd_v6_3` con `prepare_suspend` y 17 campos, y `dm` con
  `early_fini`, son hardware real de esta placa que nadie ha mirado.
- **Un límite de diseño del driver que hay que respetar**: no hay superficie
  uniforme entre bloques (de 11 a 17 campos), y `dump_ip_state` no existe. Un
  driver propio tiene que asumir NULL en todas partes.
- **La lección, por tercera vez**: un self-test tiene que comprobar el dato
  **extraído**, no la estructura de quien lo extrae. Los tests 1-5 pasaron con el
  bug de índice vivo.
- **El `.ko` cargado es una fuente de verdad más fiable que el fuente** para
  saber qué se ejecuta: distingue bloques que en el fuente son indistinguibles.

## Evidencia

```
08-ARQUITECTURA/tools/ip_surface.py --bloque N --todos --generacion --self-test
self-test: 4 vectores de layout, 2 anclas externas, 5 controles

amd_shared.h:454          struct amd_ip_funcs, 24 campos
amdgpu_ip.h:110-115       struct amdgpu_ip_block_version
vi.c:2103-2119            los 9 bloques de CHIP_POLARIS12
/tmp/amdgpu_loaded.ko     ET_REL, .symtab, .rela.rodata con 40372 entradas
journalctl -k             9x "detected ip block number" en orden
```

`WRITE_EXECUTION=NONE`. `MODIFICATIONS=0`. `GPU INTACTA`.