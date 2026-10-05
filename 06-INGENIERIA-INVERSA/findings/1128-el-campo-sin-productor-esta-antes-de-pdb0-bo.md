# 1128 — el campo sin productor está en la última línea de caché justo antes de `pdb0_bo`: el layout lo coloca donde el GART lo lee

```text
AGENCIA=RX550-INVESTIGACION · WORK_CLASS=AGENT-RE-TOOLING
GENERADO=2026-10-04 · MEDIDO=EN ESTA HOST
CIERRA PARCIALMENTE=1127-vmid0-page-table-block-size-no-se-asigna-en-gfx8.md
         (el valor sigue NOT_DETERMINED; lo que se cierra es el LAYOUT y la
          lectura de que el valor no se pierde por el camino)
AFECTADO=/sys/kernel/btf/amdgpu  (BTF VIVA del modulo cargado, 3882770 B)
         amdgpu_gmc.h:223 (struct amdgpu_gmc)
         gfxhub_v1_0.c:226-227 (el unico consumidor en GFX8)
ESTADO=PROVEN-LAYOUT · nivel 2, lectura de /sys · sin root · sin GPU · sin sudo
```

## 0 · LO QUE ESTE HALLAZGO HACE Y LO QUE NO

`1127` dejó abierto qué valor recibe el hardware en
`PAGE_TABLE_BLOCK_SIZE` en GFX8. **Eso no lo cierra este documento** y no se
intenta: sigue siendo `NOT_DETERMINED` y cerrar una lectura de `/sys` requiere
leer el registro, que es del nodo de runtime.

Lo que sí cierra es la pregunta **previa** que `1127` no se había hecho:

> ¿El valor llega al registro, o se pierde por el camino?

Y la respuesta es que **llega**, y que el layout da la razón por la que llega.

## 1 · LA MEDICIÓN, Y CÓMO SE HIZO

La vía correcta ya estaba documentada en este árbol por `revkit/btfsnap.py`:

> *`pahole` sobre el `.ko` no sirve de alternativa — la seccion `.BTF` del `.ko`
> esta partida y pahole falla. Lo que se guarda NO es la BTF sino los LAYOUTS ya
> resueltos.*

Y la fuente viva es `/sys/kernel/btf/amdgpu`, que en esta máquina es de
**hoy a las 08:50**, más reciente que el `btf-amdgpu-layouts.txt` guardado el 2
de octubre. **O sea que el layout guardado está viejo**, y para este campo
—que no estaba en él— había que ir a la fuente.

```
  /sys/kernel/btf/amdgpu                    3882770 B   [LE]
  pahole -C amdgpu_gmc /sys/kernel/btf/amdgpu          [LE, 164 lineas]
```

## 2 · EL RESULTADO, Y POR QUÉ ES EL DATO QUE IMPORTABA

```
  u64                        mc_mask;                            /*  136   8 */
  uint64_t                   pte_addr_mask;                      /*  144   8 */
  ...
  int                        noretry;                            /* 8624   4 */
  uint32_t                   xnack_flags;                        /* 8628   4 */
  uint32_t                   vmid0_page_table_block_size;        /* 8632   4 */
  uint32_t                   vmid0_page_table_depth;             /* 8636   4 */
  /* --- cacheline 135 boundary (8640 bytes) --- */
  struct amdgpu_bo *         pdb0_bo;                            /* 8640   8 */
  void *                     ptr_pdb0;                           /* 8648   8 */
```

**Tres cosas, y las tres importan:**

1. **El campo existe en la struct del módulo cargado.** No es un campo de
   fuente que se quedó sin compilar: está en el binario que está corriendo ahora
   mismo en esta máquina. Eso **descarta** la hipótesis de que el campo sea un
   resto de una versión anterior del driver.

2. **Está en el offset 8632, y no en el 136** como `mc_mask`. O sea que está en
   un **sub-bloque distinto** de la struct, muy lejos del bloque de la
   configuration de VRAM. Importa porque un campo «sin productor» en un struct
   grande puede estar en una zona que nadie inicializa —y por tanto vale
   basura— o en una zona que `kzalloc` deja a cero. **La posición no decide el
   valor, pero sí dice en qué zona vive.**

3. **Está inmediatamente antes de `pdb0_bo` y `ptr_pdb0`**, los dos punteros
   del PDB0, y termina en el **límite de caché 135**. Es decir: **el campo está
   agrupado con el PDB0, que es lo único que lo usa.**

> La tercera es la que da la cadena. `1127` mostró que `gfxhub_v1_0.c:227` lo
> lee y que nadie lo escribe; y ahora se ve que **el campo está en
> el grupo de PDB0**, o sea que el driver lo mantiene vivo para el GART. No es un
> campo muerto: es un campo que **GFX8 lee sin usar**, porque el GART de GFX8 no
> lo consulta.

## 3 · LO QUE ESO CAMBIA EN 1127

`1127` dejó dos cosas abiertas. Esta cierra una y mantiene la otra:

| pregunta | estado antes | estado ahora |
|---|---|---|
| ¿el campo existe en el binario que corre? | `NOT_DETERMINED` | **`PROVEN`** — offset 8632 en la BTF viva |
| ¿llega al registro? | `NOT_DETERMINED` | **`PROVEN`** — `gfxhub_v1_0.c:226` lo escribe, y el campo existe |
| ¿qué valor lleva? | `NOT_DETERMINED` | **`NOT_DETERMINED`** — falta leer el registro |

La fila que importa es la tercera, y **no se toca**:

> Que el valor sea `PROVEN` para dos de tres eslabones no hace que la tercera sea
> deducible. Un campo que existe y se escribe en un registro puede llevar
> cualquier cosa, y la única forma de saberlo es leerlo.

Y aquí está el matiz que hace que este hallazgo no cierre la puerta por error:
el hecho de que `pdb0_bo` y `ptr_pdb0` sean punteros **y estén también sin
inicializar claro en GFX8 antes de `amdgpu_gart_init`** significa que el sub-bloque
es del GART. Y `amdgpu_gart_init` **sí** se llama para GFX8. O sea: **hay un
productor para el bloque, aunque no para el campo.**

Eso es `PARTIAL`, no `PROVEN`. Y se dice así.

## 4 · POR QUÉ EL LAYOUT GUARDADO NO TENÍA ESTE CAMPO, Y ESO ES UN HALLAZGO

`revkit/btf-amdgpu-layouts.txt` es del **2 de octubre** y **no contiene**
`vmid0_page_table_block_size`. La BTF viva es de **hoy** y sí lo contiene.

Dos explicaciones posibles:

- el fichero guarda solo los structs que alguien pidió, y este no se pidió;
- el campo apareció en el driver después del 2 de octubre.

**MEDIDO que no se puede distinguir** con lo que hay: el fichero es una
selección, no un volcado, y no lleva el inventario de lo que se pidió. Así que es
`NOT_DETERMINED`.

Y la consecuencia es práctica y no trivial:

> **Un layout guardado es una foto, y este proyecto ya tiene el caso documentado
> de una foto que envejecía en silencio.** `R4-VERIF` se construyó exactamente
> para eso —una puerta de deriva sobre lo que miden las otras herramientas— y
> este campo es un ejemplo de lo que se le escapa: **no es una medida que nadie
> vuelva a mirar, es un fichero que nadie vuelve a pedir.**

Eso no se arregla aquí. Se registra.

## 5 · LO QUE NO SE HACE

- **No se lee el registro.** Requiere MMIO, que es del nodo de runtime, y esta
  sesión no abre la GPU.
- **No se escribe un decodificador de BTF.** `pahole` funciona sobre la fuente
  viva; escribir uno sería un ciclo entero para repetir lo que ya hay instalado.
  Y `btfsnap.py` ya resolvió esa ruta.
- **No se toca `revkit/btfsnap.py` ni el layout guardado**, que son de otra
  sesión.

## 6 · ESTADO

```
  campo en la struct del modulo que corre    offset 8632     PROVEN (BTF viva)
  agrupado con pdb0_bo / ptr_pdb0            si              PROVEN
 limite de cacheline                           135 (8640 B)   PROVEN
  llego al registro                           si             PROVEN (gfxhub_v1_0.c:226)
  que valor lleva                            NOT_DETERMINED -> leer el registro
  bloque con productor (el GART)             PARCIAL        -> amdgpu_gart_init, no el campo

  BTF viva     /sys/kernel/btf/amdgpu  3882770 B  hoy 08:50
  layout guardado  revkit/btf-amdgpu-layouts.txt  2 oct, sin este campo

  GPU     INTACTA
  sudo    NO usado
  MMIO    NO tocado
```