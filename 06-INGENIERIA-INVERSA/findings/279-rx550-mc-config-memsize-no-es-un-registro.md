# 279 · `RX550_MC_CONFIG_MEMSIZE` no es un registro y no lo usa nadie

`CLASSIFICATION=DOCUMENTATION` · `TRACK=STATIC` · `WORK_CLASS=READ_ONLY/EVIDENCE`
`WRITE_EXECUTION=NONE` · `MODIFICATIONS=0` · `RUNTIME=NOT_RUN` · `GPU INTACTA`
`HARDWARE_SCOPE=HOST-C/RX550/0000:01:00.0`
`DESARROLLA=la ultima capa sin cotejar del contrato de hardware del driver`

## Cuestión principal

`07-DRIVER/kernel/rx550_mc.h:73` declara:

```c
#define RX550_MC_CONFIG_MEMSIZE		0x150a
```

El nombre tiene la forma de un registro de controlador de memoria, y el valor
parece un offset como los otros dos de la misma cabecera. **Ninguna de las dos
cosas es cierta.**

## Criterio de terminación

Cotejar cada constante del driver con la ISA. **Cumplido: 1 de 3 no tiene
referente, y eso es un defecto del driver.**

## Las tres constantes de `07-DRIVER/kernel/rx550_mc.h`

| constante | valor | veredicto |
|---|---|---|
| `RX550_MC_FB_LOCATION` | `0x809` | **CONFIRMADO** = `mmMC_VM_FB_LOCATION` |
| `RX550_MC_CONFIG_MEMSIZE` | `0x150a` | **NO EXISTE** |
| `RX550_MC_MEMSIZE_MAX_MiB` | `16ULL*1024` | límite propio del driver, no un registro |

## Aviso sobre las citas a `07-DRIVER/`

`doclint` avisa de que las citas a `07-DRIVER/kernel/rx550_mc.h` **no se
resuelven**, y tiene razón en el aviso: **no indexa `07-DRIVER/`, solo el corpus**.
La cita es verificable a mano —yo leí esa línea— pero eso no es lo mismo que
resoluble, y el proyecto llama a lo segundo "verificable".

No lo presento como si el linter lo confirmara. Lo que sostengo aquí es:

- El contenido de `rx550_mc.h:73` está leído y copiado arriba.
- Los tres `grep` de la sección de evidencia corren sobre rutas completas.

**El hueco es real y no lo he cerrado**: `doclint` no cubre el árbol del driver, así
que **ninguna cita a `07-DRIVER/` pasa por él**. Eso afecta a todos los hallazgos
que citen el driver, no solo a este. Extender el índice de `doclint` a `07-DRIVER/`
es el arreglo, y queda pendiente.

## Los dos fallos, por separado

**El nombre no existe.** `CONFIG_MEMSIZE` no aparece en ningún `.c` ni `.h` de
amdgpu, y tampoco en `asic_reg/gmc/`. No es un registro de GCN8 con otro nombre:
no está.

**El valor pertenece a otro bloque.** Busqué `0x150a` en **todo** `asic_reg` y sale
en:

```
bif/bif_5_1_d.h          <- BIF, no GMC
dcn/dcn_2_0_0_offset.h
dcn/dcn_2_1_0_offset.h
dcn/dcn_3_0_0_offset.h
```

`0x150a` es un offset válido **de otra cosa**. Es el peor tipo de coincidencia: el
número existe, así que una comprobación floja lo daría por bueno.

**Y no lo usa nadie.** `grep` en los `.c` del driver: **0 usos**. La función que
decide el tamaño, `rx550_mc_memsize_mib()`, recibe `config_memsize` como
**parámetro**:

```c
int rx550_mc_memsize_mib(__u32 config_memsize, __u32 *mib_out)
```

No lee el registro, no lo escribe y no lo necesita.

## Por qué el tamaño de VRAM no viene de un registro

Porque **no hay registro para eso**. En amdgpu, `real_vram_size` se calcula desde
la **tabla de segmentos de ATOMBIOS**:

```c
u64 vram_size = adev->gmc.xgmi.node_segment_size *
                adev->gmc.xgmi.num_physical_nodes;
```

y el camino completo es `amdgpu_gmc_get_vram_info()` →
`amdgpu_atomfirmware_get_vram_info()`, que ya está registrado: la rama `default:`
del switch de IP version de `190`, donde **no cae ningún caso** para GFX8.

**El tamaño de VRAM lo dice el firmware, no el hardware.** Un controlador de
memoria no tiene un registro que le diga al host cuánto tiene: eso lo sabe quien
la fabricó y quien la mapeó.

## Por qué importa más de lo que parece

`RX550_MC_FB_LOCATION` **sí** es real y **sí** se usa. Es la clase de constante
que hace que alguien confíe en la cabecera entera. Y junto a una constante que
**parece** un registro y no lo es, el efecto es peor que si no estuviera:

- Quien lea `07-DRIVER/kernel/rx550_mc.h` concluirá que hay un registro de tamaño de VRAM que leer.
- El número `0x150a` es plausible, así que **un cotejo automático que solo compruebe
  "el offset existe en algún header" lo daría por bueno**.
- Y un día alguien lo usará, en una placa donde no significa nada.

Es el patrón que el proyecto ya ha visto con los nombres de bloque: **una etiqueta
que parece authoritative y no lo es**. Aquí es una constante, y es más fácil que
un nombre de fichero porque *un número no tiene contexto*.

## Qué no he hecho

**No he borrado la constante.** Es código de otra sesión, y quitar una `#define`
aunque esté muerta cambia un fichero que no es mío. Lo que hago es dejarlo medido
y escrito.

## Clasificación

| afirmación | estado |
|---|---|
| `0x150a` no es un offset de GMC/GFX8 | `PROVEN` — búsqueda en todo `asic_reg` |
| `0x150a` sí existe, en BIF y DCN | `PROVEN` |
| `CONFIG_MEMSIZE` no existe en amdgpu | `PROVEN` — grep en `.c` y `.h` |
| La constante no la usa ningún `.c` | `PROVEN` — 0 usos |
| `real_vram_size` sale de ATOMBIOS | `PROVEN` — `amdgpu_gmc.c` |
| `mmMC_VM_FB_LOCATION = 0x809` | `PROVEN` |
| Que la constante llegue a usarse por error | `HYPOTHESIS` |
| Que `RX550_MC_FB_LOCATION` se lea del ASIC | `NOT_DETERMINED` — no verificado |

## Confounders

- **No he construido el driver**, así que un `#define` muerto podría quedar
  eliminado por el compilador sin que nadie lo note. Eso no lo convierte en
  correcto: el defecto es que el *contrato* dice algo falso, y el contrato se lee.
- **No he comprobado si `07-DRIVER/kernel/rx550_mc.h` se incluye desde `userspace/`**, donde un
  `#define` muerto sí podría estar usándose. No lo miré.
- **No he verificado el valor de `MEMSIZE_MAX_MiB`**: 16 GiB es un límite propio del
  driver, no una propiedad medida del ASIC, así que no lo cotejo. Si el objetivo es
  "no" esta placa, 16 GiB es holgado pero no falso.

## Desfalsificación

- **(a)** `0x150a` no es de GMC → refutable grepeando `0x150a` en `asic_reg`: sale
  BIF y DCN, nunca GMC. **Verificado.**
- **(b)** `CONFIG_MEMSIZE` no existe → refutable grepeando en `amdgpu/*.c *.h`.
  **Verificado.**
- **(c)** 0 usos → refutable grepeando en `07-DRIVER/kernel/*.c`. **Verificado.**
- **(d)** El tamaño viene de ATOMBIOS → refutable con `amdgpu_gmc.c`.
- **(e)** Que la cabecera se lea desde userspace → **no comprobado**.

## UNLOCKS

- **Una constante muerta con forma de registro.** Es el patrón de "nombre que parece
  autoritativo sin serlo" reducido a su forma más fácil de propagar: un número.
- **Un punto ciego de validación**: un cotejo que compruebe "el offset existe en
  algún header" **aprobaría esta constante**, porque `0x150a` existe en BIF.
  El alcance del cotejo es lo que decide, no el número.
- **`190` queda cerrado por el otro lado**: el tamaño de VRAM viene de ATOMBIOS, lo
  que confirma que el `default:` del switch de IP version es la ruta correcta para
  GFX8 — no es solo que "no cae ningún caso", es que **no debe caer ninguno**.
- **Siguiente paso**: `RX550_MC_FB_LOCATION` es real pero **no he verificado que el
  driver lo lea del ASIC y no lo invente**, y es el único camino del driver hacia
  la base de VRAM.

## Evidencia

```
grep -c CONFIG_MEMSIZE  07-DRIVER/kernel/*.c        -> 0
grep -rn "MC_CONFIG_MEMSIZE" amdgpu/*.c amdgpu/*.h    -> nada
grep -rlE "0x0*150a\b"   asic_reg/                   -> bif_5_1_d.h, dcn/*_offset.h
grep -E "^#define\s+mmMC_VM_FB_LOCATION" gmc/*_d.h   -> 0x809
amdgpu_gmc.c:61          vram_size = node_segment_size * num_physical_nodes
```

`WRITE_EXECUTION=NONE`. `MODIFICATIONS=0`. `GPU INTACTA`.