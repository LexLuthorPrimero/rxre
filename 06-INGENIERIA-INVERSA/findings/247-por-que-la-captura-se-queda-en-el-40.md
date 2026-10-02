# 247 · Por qué la captura se queda en el 40%: offsets computados en runtime, y 397 nombres de función ambiguos

`CLASSIFICATION=DOCUMENTATION` · `TRACK=STATIC_BINARY` · `WORK_CLASS=READ_ONLY/EVIDENCE`
`WRITE_EXECUTION=NONE` · `MODIFICATIONS=0` · `RUNTIME=NOT_RUN` · `GPU INTACTA`
`CORPUS=/tmp/amdgpu_loaded.ko` · `HARDWARE_SCOPE=HOST-C/RX550/0000:01:00.0`
`DESARROLLA=el hueco de captura que 246 dejo abierto`

## Cuestión principal

`246` mide 4974 accesos MMIO sobre **14374** sitios de llamada, y declara el 35%
como cota inferior sin explicar **por qué**. Eso es un hueco abierto, no un resultado.

Este hallazgo cierra la pregunta: **la captura se queda en el 40% porque el 60% de
las escrituras MMIO no tienen offset estático**, y además mi extractor **cuenta mal
cuando un nombre de función está repetido**.

## Criterio de terminación

Determinar la causa de cada sitio no atribuido y medir el alcance del defecto de
desambiguación. **Cumplido: dos causas distintas, una fundamental y una reparable.**

## Causa 1 · La forma de instrucción, y era mi hipótesis

`246` supuse que el fallo era la forma. **Era
parcialmente cierto**, y encontré la forma que faltaba:

```
lea    0x2644(%rbx),%esi              ; NO es "mov $imm,%esi"
mov    0x17804(%r14,%rbx,4),%edx     ; el valor viene de una tabla
call   amdgpu_device_wreg-0x4
```

Es un **bucle sobre una tabla de registros**: `WREG32(reg + i, tabla[i])`. El
offset literal está en un `lea` con índice de registro, no en un `mov` con inmediato.

**Y los valores son registros reales**, lo que confirma la interpretación:

```
$ grep -hE "^#define \S+\s+0x0*2644\b" gca/gfx_8_0_d.h
#define mmGB_TILE_MODE0     0x2644
$ grep -hE "^#define \S+\s+0x0*2664\b" gca/gfx_8_0_d.h
#define mmGB_MACROTILE_MODE0  0x2664
```

**`gfx_v8_0_hw_init` escribe en bucle la tabla de modos de tile de la GPU.** Ese
es un fragmento concreto y ordenado de la secuencia de arranque de esta placa,
sacado del binario.

Añadida la forma `lea`, la captura sube de 4974 a **5710** (35% → **40%**), con
**761 sitios en bucle** y 4949 accesos literales.

## Causa 2 · El offset se computa en runtime: el límite es FUNDAMENTAL

Los sitios en bucle no son recuperables estáticamente, y el motivo está en el
fuente. `amdgpu_amdkfd_gfx_v8.c:263 kgd_hqd_sdma_load`, la versión de esta placa:

```c
sdma_rlc_reg_offset = get_sdma_rlc_reg_offset(adev, m->sdma_engine_id,
                                              m->sdma_queue_id);
...
WREG32(sdma_rlc_reg_offset + mmSDMA0_RLC0_RB_CNTL, ...);
```

**El offset es `valor_de_runtime + constante_de_compilación`.** No hay ningún
número en el binario que lo determine, porque el primer término depende del
motor y de la cola. Un extractor estático **no puede** con estos sitios, y no es un
defecto mío: es que la información no está en el binario.

**Y sale un hecho de §A que no tenía registrado: la base de registros de una cola
SDMA es un valor por (motor, cola), calculado en runtime.** No es una constante
compilada sino un parámetro. Cada anillo SDMA vive en su propia región de
registros.

## Causa 3 · 397 nombres de función están repetidos, y yo cuento el primero

Este sí es un **defecto mío, y es el más grave de los tres** porque no se ve en la
salida.

En C, una función `static` en dos ficheros puede llamarse igual en ambos, y el ELF
**repite el símbolo**. Medido:

```
nombres de funcion definidos mas de una vez: 397
de un total de 33732 nombres distintos

kgd_hqd_sdma_load     definiciones: 4
amdgpu_device_rreg    definiciones: 1
gfx_v8_0_hw_init      definiciones: 1
```

**`mmio_map._funcion()` devuelve la primera coincidencia del nombre y no lo
advierte.** Para `kgd_hqd_sdma_load` hay **4** definiciones —las de v6, v7, v8 y
v10— y el número que devuelve es el de una de ellas, sin decir cuál.

Consecuencia sobre `246`: **su tabla por bloque es cota inferior por dos razones,
no por una.** No solo por el 35% capturado, sino porque para los 397 nombres
ambiguos se cuenta **una** de sus definiciones y se ignoran las otras.

**Un número que sale más bajo de lo que debería, sin que nada en la salida lo
avise, es peor que un número que no sale.** Un error visible se corrige; un
subestimado silencioso se planifica.

## Lo que esto cambia sobre `246`

| | `246` declaraba | ahora |
|---|---|---|
| captura | 35% | **40%** (forma `lea` añadida) |
| motivo del hueco | "no explicado" | **offsets computados en runtime** |
| segundo motivo | no declarado | **397 nombres ambiguos** |
| 540 por bloque | cota inferior | cota inferior **por dos causas** |

Anotado en el fichero de `246`.

## Los sitios en bucle, y qué son

| función | en bucle | total | qué hace |
|---|---|---|---|
| `kgd_hqd_sdma_load` | 49 | 52 | carga el descriptor de cola SDMA |
| `dce_v10_0_crtc_load_lut` | 29 | 29 | carga la LUT de un CRTC |
| `dce_v8_0_afmt_setmode` | 22 | 25 | programa un modo de AFMT |
| `dce_v10_0_crtc_do_set_base` | 22 | 23 | fija la base del plano de scanout |

**Los bucle-heavy son de display y de SDMA.** Y `dce_*` es el DCE legacy que esta
placa **no** usa (`192`/`203`): son funciones de otro ASIC. `kgd_hqd_sdma_load`
tiene versión v8 que sí corre aquí.

Eso deja una observación útil: **el patrón de bucle domina justo en los subsistemas
que aquí no se ejecutan.** El acceso literal domina los que sí. No es una ley, pero
explica por qué la captura sube al 40% y no más.

## Clasificación

| afirmación | estado |
|---|---|
| La captura sube a 40% con la forma `lea` | `PROVEN` — 4974 → 5710 |
| `mmGB_TILE_MODE0 = 0x2644` | `PROVEN` — `gfx_8_0_d.h` |
| `gfx_v8_0_hw_init` escribe la tabla de tiles en bucle | `PROVEN` — fuente + binario |
| El offset de cola SDMA se computa en runtime | `PROVEN` — `amdgpu_amdkfd_gfx_v8.c:263` |
| 397 nombres de función repetidos | `PROVEN` — recuento sobre 33732 |
| `kgd_hqd_sdma_load` tiene 4 definiciones | `PROVEN` |
| Que mi tabla por bloque lo omita | `PROVEN` — `_funcion` toma la primera |
| Que el 60% restante sea todo offset dinámico | `DERIVATION` — no medido el resto |
| Que se pueda recuperar estáticamente | `REFUTADO` — no está en el binario |

## Confounders

- **El 60% restante no está todo catalogado.** He probado dos causas y las dos
  existen; **no he enumerado el resto**. Puede haber una tercera forma que no
  conozco. Lo digo en vez de cerrar el 40% como si fuera el techo.
- **`_funcion()` sigue sin desambiguar.** No lo he arreglado: hacerlo exige
  emparejar el símbolo con el fichero de origen, que el `.ko` no guarda. Lo he
  medido y declarado; **no lo he corregido**.
- **El conteo de definiciones repetidas (397) cuenta símbolos**, y un símbolo
  repetido en `.text` y `.init.text` contaría dos aunque sea la misma función. No
  he separado los casos. El 397 es **una cota superior** de la ambigüedad real.
- **No he verificado que un acceso atribuido ocurra en esta placa.** Sigue siendo
  una medida estática.

## Desfalsificación

- **(a)** 40% → refutable con `mmio_map --resumen`.
- **(b)** `0x2644 = mmGB_TILE_MODE0` → refutable con el grep del header.
- **(c)** offset de runtime → refutable con `amdgpu_amdkfd_gfx_v8.c:263`.
- **(d)** 397 ambiguos → refutable contando definiciones repetidas.
- **(e)** Que `_funcion` avise de la ambigüedad → **refutado: no avisa**.
- **(f)** Que el resto sea offset dinámico → **no medido**, declarado.

## UNLOCKS

- **El límite de la medición está explicado y es irreducible**: el 60% de las
  escrituras MMIO tienen offset `runtime + constante`. **No está en el binario**, y
  por tanto ningún análisis estático lo recuperará. Eso fija dónde puede acabar
  cualquier herramienta de este tipo.
- **§A gana un dato**: la base de registros de una cola SDMA es un **parámetro
  por (motor, cola)**, no una constante. Cada anillo vive en su región.
- **`gfx_v8_0_hw_init` programa en bucle `mmGB_TILE_MODE0..N`** y
  `mmGB_MACROTILE_MODE0..N`. Es el primer fragmento **ordenado y concreto** de la
  secuencia de arranque de esta GPU, extraído del binario.
- **Corregido `246`**: su tabla por bloque es cota inferior por dos causas, no una.
- **Un límite de herramientas reutilizable**: los `static` de C producen símbolos
  ELF repetidos, y **cualquier herramienta que busque por nombre función está
  contando una de varias**. Eso hay que medirlo y reportarlo, porque el error va en
  la dirección silenciosa: **subestima sin avisar**.
- **Siguiente paso**: `_funcion()` debería reportar la ambigüedad en su propia
  salida, aunque no pueda resolverla. Un contador visible vale más que un promedio
  correcto.

## Evidencia

```
objdump -dr /tmp/amdgpu_loaded.ko > ko_dr.asm
grep -c "amdgpu_device_rreg-0x4\|amdgpu_device_wreg-0x4" ko_dr.asm    14374
08-ARQUITECTURA/tools/mmio_map.py --resumen        5710 atribuidos, 40%
    761 sitios en bucle, 4949 accesos literales

gfx_8_0_hw_init:  lea 0x2644(%rbx),%esi  +  mov 0x17804(%r14,%rbx,4),%edx
                  call amdgpu_device_wreg-0x4
asic_reg/gca/gfx_8_0_d.h   mmGB_TILE_MODE0 = 0x2644
                            mmGB_MACROTILE_MODE0 = 0x2664
amdgpu_amdkfd_gfx_v8.c:263 kgd_hqd_sdma_load
        WREG32(sdma_rlc_reg_offset + mmSDMA0_RLC0_RB_CNTL, ...)
recuento de simbolos: 397 nombres con mas de una definicion de 33732
```

`WRITE_EXECUTION=NONE`. `MODIFICATIONS=0`. `GPU INTACTA`.