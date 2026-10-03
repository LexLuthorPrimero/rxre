# 1027 · `RX550_GART_START = 0` es una colocación que el driver de referencia implementa y cuya condición se cumple en esta tarjeta

`CLASSIFICATION=DERIVATION` · `TRACK=STATIC + HOST_OBSERVATION`
`CORPUS=RESEARCH/kernelbuild/linux-7.1.3` · `HARDWARE_SCOPE=HOST-C/RX550/0000:01:00.0`
`WORK_CLASS=READ_ONLY/EVIDENCE` · `WRITE_EXECUTION=NONE` · `MODIFICATIONS=0`
`RUNTIME=OBSERVED_READ_ONLY` · `GPU INTACTA`

---

## La decisión de diseño que estaba sin cerrar

`rx550_spaces.h:49-52`, en el componente del driver propio:

```c
/* ── DESIGN_CHOICE ──────────────────────────────────────────────────────── */
#define RX550_GART_START	UINT64_C(0)
```

Y su justificación, línea 16-26 del mismo fichero:

> `GART_START = 0`.
> El driver de referencia puede elegirlo (`amdgpu_gmc.c:312-332`, tres ramas,
> siempre alineado a 4 GiB). Nuestro driver elige 0. Eso hace que
> `GART_ADDRESS == SYSTEM_PA`, que elimina una ambigüedad para el primer diseño.
> **ESTO NO ES UN REQUISITO DE HARDWARE. No se ha demostrado que el silicio
> acepte la configuración; eso se comprueba en runtime.**

Es decir: el propio texto dice que la elección **no está probada contra el
silicio**. Eso es honesto y correcto como estado. Lo que faltaba era la otra
mitad: **¿es siquiera una colocación que el hardware puede expresar?**

## Lo que hace el driver de referencia, y son tres ramas

`amdgpu_gmc.c:294-334`, `amdgpu_gmc_gart_location()`:

```c
u64 max_mc_address = min(adev->gmc.mc_mask, AMDGPU_GMC_HOLE_START - 1);

u64 size_bf = mc->fb_start;
u64 size_af = max_mc_address + 1 - ALIGN(mc->fb_end + 1, four_gb);

if (mc->gart_size > max(size_bf, size_af)) {     /* clampea, no llega aquí */
	dev_warn(adev->dev, "limiting GART\n");
	mc->gart_size = max(size_bf, size_af);
}

switch (gart_placement) {
case AMDGPU_GART_PLACEMENT_LOW:
	if (size_bf >= mc->gart_size)
		mc->gart_start = 0;                     /* ← lo que queremos */
	else
		mc->gart_start = ALIGN(mc->fb_end, four_gb);
	break;
case AMDGPU_GART_PLACEMENT_HIGH:
	mc->gart_start = max_mc_address - mc->gart_size + 1;
	break;
case AMDGPU_GART_PLACEMENT_BEST_FIT:
default:
	if ((size_bf >= mc->gart_size && size_bf < size_af) ||
	    (size_af < mc->gart_size))
		mc->gart_start = 0;
	else
		mc->gart_start = max_mc_address - mc->gart_size + 1;
	break;
}
mc->gart_start &= ~(four_gb - 1);
```

**Existe `AMDGPU_GART_PLACEMENT_LOW`, y su rama produce exactamente
`gart_start = 0`.** Eso es lo que faltaba comprobar, y no hace falta tocar el
silicio para comprobarlo: es software que se ejecuta en esta máquina.

## Las entradas, de esta tarjeta

Del log del kernel (`journalctl -k`, que sí expone esto sin root):

```
amdgpu 0000:01:00.0: VRAM: 2048M 0x000000F400000000 - 0x000000F47FFFFFFF (2048M used)
amdgpu 0000:01:00.0: GART: 256M 0x000000FF00000000 - 0x000000FF0FFFFFFF
amdgpu 0000:01:00.0: vm size is 64 GB, 2 levels, block size is 10-bit, fragment size is 9-bit
```

Del corpus:

| entrada | valor | fuente |
|---|---|---|
| `mc_mask` | `0xffffffffff` (40 bits) | `gmc_v8_0.c:1133` |
| `max_level` | 1 (el log dice «2 levels») | `amdgpu_vm_adjust_size(..., 1, 40)` en `gmc_v8_0.c:1127` |
| `AMDGPU_GMC_HOLE_START` | `0x0000800000000000` | `amdgpu_gmc.h:36-37`, rama `max_level != 4` |
| `four_gb` | `0x100000000` | alineación que el propio código exige |

Y `max_mc_address = min(0xffffffffff, 0x8000000000 - 1) = 0xffffffffff`: el
`min` se queda con `mc_mask`, porque el hueco está **por encima** de los 40 bits.
Ese detalle es el que hace que la aritmética cierre, y es fácil leerlo al revés.

## La aritmética, ejecutada

```
max_mc_address = min(0xffffffffff, 0x7fffffffff)      = 0xffffffffff
ALIGN(fb_end+1, 4 GiB) = ALIGN(0xf480000000, 0x100000000) = 0xf500000000

size_bf = fb_start = 0xf400000000 = 1047972020224
size_af = max_mc + 1 - 0xf500000000  =  0xb00000000 =   47244640256

gart_size = 0x10000000 (256 MiB)
¿clampea?  0x10000000 > max(size_bf, size_af)= 0xf400000000   ->  No
```

**Con `BEST_FIT`** (que es lo que se llama: `gmc_v8_0.c:422`):

```
(size_bf >= gart_size) && (size_bf < size_af)  ->  True && False  = False
(size_af < gart_size)                          ->  False
-> else:  gart_start = max_mc_address - gart_size + 1
                    = 0xffffffffff - 0x10000000 + 1 = 0xfff0000000
-> gart_start &= ~(four_gb - 1)                 = 0xff00000000
```

Y lo medido es **`0x000000FF00000000`**. Cuadra exactamente, con las tres
operaciones, incluido el redondeo a 4 GiB. Lo que `BEST_FIT` eligió fue `HIGH`,
no `LOW`, porque en esta geometría hay mucho más hueco **por debajo** de la VRAM
(`size_af` = 42 GiB) que **por encima** (`size_bf` = 953 GiB).

**Con `LOW`**, en la misma geometría:

```
size_bf (0xf400000000) >= gart_size (0x10000000)  ->  True
-> gart_start = 0
-> gart_start &= ~(four_gb - 1)                   -> 0
```

## Lo que queda establecido, y con qué estado

| afirmación | estado | por qué |
|---|---|---|
| `gart_start = 0` es una colocación que el driver de referencia **expresa** | **`PROVEN`** | `amdgpu_gmc.c:316-318`, rama `LOW`, código que corre en esta máquina |
| Su condición (`size_bf >= gart_size`) se cumple en esta tarjeta | **`PROVEN`** | `0xf400000000 >= 0x10000000`, de números medidos |
| La aritmética de `amdgpu_gmc_gart_location` reproduce el GART observado | **`PROVEN`** | `0xff00000000` por los tres pasos, con los valores del log |
| El silicio **acepta** un GART con base 0 | **`NOT_TESTED`** | requiere escribir y leer; nadie lo ha hecho |

La cuarta fila es la que importa y la que **no** se ha tocado. Lo que cambia con
este hallazgo es la tercera: antes no se sabía ni si la elección era programable;
ahora se sabe que lo es, por el camino que el propio driver de referencia usa.

## Por qué esto no es «copiar amdgpu»

`§5` es explícito: la pregunta no es cómo hacerlo portable, sino cómo hacerlo
correcto y rápido para esta tarjeta. Aquí la decisión `GART_START = 0` es
**nuestra**, y lo que se ha hecho es comprobar que la máquina la admite. La
referencia entra como **evidencia de qué es programable**, que es exactamente lo
que dice su propio valor: `DESIGN_CHOICE`.

Y hay una razón de fondo para querer 0, que `rx550_spaces.h:8-12` ya enunciaba:
con `GART_START = 0`, `GART_ADDRESS == SYSTEM_PA`, y `RX550_PDE_LEAF` /
`TM_PTE_VALID` codifican una dirección física que es directamente la que se
programa en el PTE. Sin esa coincidencia habría que distinguir dos espacios en
cada construcción de entrada, que es la clase de error que todo el componente
esta diseñado para hacer imposible.

## Lo que este hallazgo NO dice

- **No dice que base 0 funcione en el silicio.** Sigue siendo
  `RUNTIME_REQUIRED`, y el propio `rx550_spaces.h:25-26` ya lo decía antes de
  este hallazgo. Lo que se ha movido es `NOT_DETERMINED → CORROBORADO` en la
  *expresabilidad*, no en el comportamiento.
- **No dice que `0xff00000000` esté mal.** El GART que el sistema tiene ahora
  funciona, o el kernel no habr booted. Si base 0 resultara inválida, la
  alternativa es `ALIGN(fb_end, four_gb)`, que es la otra rama de `LOW` y el
  propio código la tiene.
- **No toca el hardware.** Ni un registro leído, ni uno escrito. La lectura del
  log del kernel es lo único de runtime, y es de lectura.

## El error que casi cometí, y que está en el Commit porque merece estarlo

La primera vez que hice esta aritmética a mano, alineé `fb_end + 1` a
`0xf480000000` en vez de `0xf500000000`, y con ese valor la cuenta daba
`gart_start = 0`, que contradecía el GART medido. La reacción fácil era ajustar
la constante hasta que cuadrara, o declarar que el log y el código no se
explican.

Lo correcto era ejecutarla. Con los valores exactos, `size_af` cae por debajo de
`size_bf`, las dos disjuntas de `BEST_FIT` son falsas, y el `else` produce
exactamente el número del log. **La contradicción no existía: la aritmética
manual estaba mal.** Un número que «no cuadra» porque lo calculé de memoria no es
una contradicción del hardware, y saltarse a la conclusión rival habría sido
inventar una.

## Trazabilidad

- Aritmética: `amdgpu_gmc.c:294-334`, con `four_gb`, `LOW`/`HIGH`/`BEST_FIT`
- `mc_mask`: `gmc_v8_0.c:1133`. `max_level`: `gmc_v8_0.c:1127`
- `AMDGPU_GMC_HOLE_START`: `amdgpu_gmc.h:36-37`
- Llamada: `gmc_v8_0.c:421-422` (`vram_location` antes que `gart_location`)
- Observación: `journalctl -k`, líneas `VRAM: 2048M 0xF400000000` y `GART: 256M
  0xFF00000000` del arranque del 2026-10-03 16:08
- Decisión de diseño: `rx550_spaces.h:16-26` y `:50`
- Hallazgo relacionado: `086` (de dónde sale `fb_start`), `1020` (que la apertura
  es constante de carga)
- Prefijo de numeración: 1027, reservado antes de escribir