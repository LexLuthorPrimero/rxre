# 1124 — tres comentarios del mismo driver sobre el PTE de GFX8, y los tres no pueden ser ciertos a la vez

```text
AGENCIA=RX550-INVESTIGACION · WORK_CLASS=AGENT-RE-TOOLING
GENERADO=2026-10-04 · MEDIDO=EN ESTA HOST · CORPUS=rx550-upstream-7.2.8
AFECTADO=gmc_v8_0.c:686-700           (comentario del formato del PTE y del PDE)
         amdgpu_vm_pt.c:730-733       (comentario del campo fragment)
         amdgpu_vm_pt.c:749-754       (max_frag: 31 vs fragment_size)
         amdgpu_vm.h:73-133           (tabla de flags)
ESTADO=PROVEN-CONTRADICCION-EN-CORPUS · GPU INTACTA
       *** CERRADO POR 1125-el-campo-fragment-esta-en-11-7-confirmado-por-la-macro.md
       La macro `AMDGPU_PTE_FRAG(x) = ((x & 0x1fULL) << 7)` (amdgpu_vm.h:70)
       localiza el campo en 11:7.  Este documento queda como el que PLANTEA la
       contradiccion y explica por que es tentador el comentario equivocado. ***
```

> **Nota de estado.** Este hallazgo se escribió antes de encontrar la macro, y su
> §3 dice «no se elige cuál de los tres comentarios es el bueno». Eso ya se
> respondió: **gana `gmc_v8_0.c`**, y la respuesta está en `1125`. Se conserva el
> texto sin corregir porque el valor de este documento es **mostrar el
>.descubrimiento**, y un hallazgo reescrito como si siempre hubiera sabido la
> respuesta es una rehearsal.

## 0 · EL HECHO, Y POR QUÉ NO PUEDE SER

Hay tres afirmaciones sobre la misma estructura de datos —el PTE de GFX8— en tres
sitios del mismo driver, y **son mutuamente incompatibles**.

**A · El formato del PTE, en `gmc_v8_0.c:686`:**

```
 * PTE format on VI:
 * 63:40 reserved
 * 39:12 4k physical page base address
 * 11:7 fragment
 * 6 write
 * 5 read
 * 4 exe
 * 3 reserved
 * 2 snooped
 * 1 system
 * 0 valid
```

**B · El campo fragment, en `amdgpu_vm_pt.c:732`:**

```
 * The MC L1 TLB supports variable sized pages, based on a fragment
 * field in the PTE. When this field is set to a non-zero value, page
 * granularity is increased from 4KB to (1 << (12 + frag)).
```

**C · El rango del campo fragment, en `amdgpu_vm_pt.c:749-754`:**

```c
if (params->adev->asic_type < CHIP_VEGA10)
    max_frag = params->adev->vm_manager.fragment_size;
else
    max_frag = 31;
```

Las tres **no pueden ser ciertas a la vez**:

| afirmación | dice |
|---|---|
| A | el campo fragment ocupa los bits **11:7**, es decir 5 bits → rango 0–31 |
| B | el campo vale `frag` y la granularidad es `1 << (12 + frag)` → el campo está **en el bit 12**, y por tanto los bits por debajo son de granularidad, no de flags |
| A | los bits **6:0** son `write/read/exe/reserved/snooped/system/valid` |

**B es incompatible con A.** Si el campo fragment estuviera en `11:7` como dice A,
el valor `frag = 1` daría una granularidad `1 << 13 = 8 KiB`, y los bits 11:8
—que A declara parte del campo fragment— tendrían que significar granularidad
y no fragmento a la vez. Y A **no puede estar bien**: `63:40 reserved` más
`39:12` dirección más `11:7` fragment son campos que se solapan en el bit 11.

> La aritmética lo dice en una línea: `39:12` son **28 bits** y `11:7` son
> **5 bits**, y `11` está **dentro** de `39:12`. Dos campos no pueden escribirse
> sobre el mismo bit.

## 1 · LO QUE RESUELVE `094`, Y LO QUE NO

El hallazgo `094-gfx8-solo-escribe-los-bits-0-11-del-pte.md` cierra la
**segunda parte** del formato del PTE —que los flags por encima del bit 11 son de
GFX9 en adelante— usando el discriminante correcto: leer quién escribe qué.

Y ese hallazgo **apoya la lectura de B**, sin decirlo: si en GFX8 los únicos
flags que el driver escribe están **por debajo del bit 12**, entonces el campo
`11:7` del comentario A no lo escribe nadie, y el fragmento —que sí se escribe—
tiene que estar en otro sitio.

`1121-el-bit-prt-se-borra-en-gfx8-y-se-pone-en-gfx9.md` refuerza lo mismo por
otro lado: `gmc_v8_0.c` **borra** el bit 51 y no escribe ningún flag alto.

## 2 · EL DATO DEL ASIC QUE HACE ARREGLABLE LA CONTRADICCIÓN

`fragment_size = 9` para esta GPU, que es un hecho ya establecido del target. Y
`adev->vm_manager.fragment_size` es lo que C mete en `max_frag` cuando
`asic_type < CHIP_VEGA10`, que es el caso de Polaris12.

Con `max_frag = 9`:

```
  B:  1 << (12 + frag)  con frag ∈ [0, 9]
        => granularidad de 4 KiB a 2 MiB, en pasos de potencia de dos
  A:  el campo fragment en 11:7 admitiria frag ∈ [0, 31]
        => granularidad hasta 4 GiB, que es absurdo para una GPU con 2 GiB
```

**El comentario A admite una granularidad de 4 GiB. Esta GPU tiene 2 GiB de
VRAM.** El comentario es imposible para el hardware de este target, y eso es un
descartes independiente de la aritmética de solapamiento.

> Es el mismo patrón que `094`: **el comentario de un fichero describe la
> generación que el fichero recortó, no la generación del ASIC.** Aquí el
> comentario de `gmc_v8_0.c` es de otro formato, y el de `amdgpu_vm_pt.c` —que es
> el fichero que **calcula** el valor— es el que coincide con lo que el hardware
> puede hacer.

## 3 · LO QUE ESTE HALLAZGO NO RESUELVE, Y ES LO IMPORTANTE

**No dice cuál de los tres comentarios es el bueno.** Dice que no pueden ser los
tres, y que el de `amdgpu_vm_pt.c` es el único compatible con `fragment_size = 9`
y con 2 GiB de VRAM.

Y hay un cuarto dato que **tampoco** cierra la puerta, y por eso no se elige:

```
if (params->adev->asic_type < CHIP_VEGA10)
    max_frag = params->adev->vm_manager.fragment_size;
else
    max_frag = 31;
```

En GFX8 sale `fragment_size = 9`. En Vega10 y posteriores sale **31**, y con B eso
da `1 << (12 + 31) = 8 GiB` de granularidad, lo que es coherente con una GPU
con 8+ GiB. **O sea que el 31 de C no es arbitrario**: es el valor que
necesita una generación con más memoria. Eso **debilita** la lectura de que A sea
un comentario de GFX9 por accidente, porque A y C son consistentes entre sí en
cuanto a magnitudes.

> Con lo que la contradicción queda acotada a **dónde está el campo** —`11:7`
> frente a bit 12— y no en si el campo existe ni cuál es su rango.

Para cerrarla harían falta los registros de la guía de hardware de Polaris12, que
**no están en este corpus**. Con lo que hay aquí es `NOT_DETERMINED`, y se dice.

## 4 · POR QUÉ IMPEDE TRABAJAR, Y POR QUÉ NO ES COSMÉTICO

Un PTE con el campo fragment en el sitio equivocado no es un error de
documentación: es **un descriptor de página que el TLB de la GPU interpreta con
una granularidad distinta de la que el driver cree**.

Consecuencia práctica, y es la razón por la que esto importa:

- Si el hardware lee el fragment en `11:7` y el driver lo escribe en el bit 12,
  el valor `9` acaba en un campo que el hardware interpreta como otro valor, y la
  granularidad efectiva es `1 << (12 + valor_leído)`.
- El driver lo **optimiza**: el comentario de C dice que *"the large fragment
  cache is significantly larger. Thus, we try to use large fragments wherever
  possible"*. O sea que **el rendimiento del page walker depende de que ese
  campo se lea bien**.

Y este proyecto tiene un objetivo declarado de **máximo rendimiento práctico de
la GPU**. Si el campo se resuelve mal, el L1 TLB pierde su cache de fragmentos
grandes, y eso es una pérdida de rendimiento que ningún benchmark de cómputo
vería: saldría en forma de TLB miss, no de error.

## 5 · LOS TRES COMENTARIOS, CON SU FICHERO Y SU LÍNEA

| afirmación | fichero:línea | qué afirma |
|---|---|---|
| A | `gmc_v8_0.c:686-696` | el campo fragment está en **11:7** |
| A′ | `gmc_v8_0.c:697-703` | el PDE: `63:59` block fragment size, `39:1` dirección de PTE |
| B | `amdgpu_vm_pt.c:730-733` | granularidad `1 << (12 + frag)` → campo en el **bit 12** |
| C | `amdgpu_vm_pt.c:749-754` | `max_frag = 9` en GFX8, `31` en Vega10+ |

### Y el PDE tiene el MISMO defecto, que es lo que hace esto transferible

MEDIDO al recontar el formato del PDE, que está en el mismo bloque de comentarios:

```
 * PDE format on VI:
 * 63:59 block fragment size
 * 58:40 reserved
 * 39:1 physical base address of PTE
 * bits 5:1 must be 0.
 * 0 valid
```

**`63:59` y `39:1` se solapan**, exactamente igual que `39:12` y `11:7` en el
PTE. Los dos formatos del mismo bloque de comentarios tienen la misma aritmética
imposible.

O sea: **el defecto no es del campo fragment del PTE. Es del patrón de
declarar campos en este bloque de comentarios**, que numera un campo sin
reservar los que le sobran. Y eso es lo que hace que valga registrarlo: un
comentario con `39:1` no puede describir un campo de 39 bits si el bit 59 ya
está usado.

Y el dato de contraste: **`gmc_v8_0.c:707-710`**, la función que valida el PDE:

```c
static void gmc_v8_0_get_vm_pde(struct amdgpu_device *adev, int level,
				uint64_t *addr, uint64_t *flags)
{
	BUG_ON(*addr & 0xFFFFFF0000000FFFULL);
}
```

MEDIDO la máscara, que es donde está la segunda contradicción:

```
  0xFFFFFF0000000FFF  ->  reserva los bits 63:12
  comentario, linea 701  ->  "58:40 reserved" y "39:1 physical base address"
```

El `BUG_ON` reserva **`63:12`**. El comentario reserva **`58:40`** y dice que
el campo de dirección **empieza en el bit 1**.

**Discrepan en dos sitios**, y el segundo es el grave: el comentario da por
usados los bits `58:40` para el block fragment size, y el `BUG_ON` los declara
inválidos. Y el comentario dice que la dirección empieza en el bit 1, mientras
el `BUG_ON` exige que los bits `11:0` sean cero.

> Es más fuerte de lo que parecía: no es que el comentario describa otra
> generación. Es que **el comentario y el código que lo acompaña están en el
> mismo bloque, a doce líneas de distancia, y dicen cosas distintas sobre los
> mismos bits.**

> De cinco afirmaciones sobre el formato de las page tables de GFX8, **la única
> que el driver hace cumplir con un `BUG_ON` es la del PDE**, y es la única que
> contradice a su propio comentario. Las tres del PTE son comentarios sin nadie
> que las compruebe. Un `BUG_ON` es una hipótesis que el autor considera rota si
> se viola; un comentario no.

## 6 · LO QUE PROPONGO, Y POR QUÉ NO LO HAGO

La pregunta que cierra esto es de runtime y es **de lectura de registro**:

> ¿dónde lee el hardware de esta GPU el campo fragment del PTE: en el bit 12 o
> en `11:7`?

Eso exige leer `mmVM_L2_CNTL3` con el ASIC real y construir una página con
fragmento conocido, y ver qué hace el TLB. **Es del nodo de runtime, no de
este**, y no se responde leyendo el corpus: la guía de hardware no está aquí.

Lo que sí se puede, y es lo que este hallazgo hace, es **dejar la contradicción
escrita con las tres líneas exactas**, para que cuando alguien tenga el manual
sepa exactamente qué buscar y en qué tres sitios el driver discrepa consigo
mismo.

## 7 · ESTADO

```
  afirmacion      que dice                     como se cierra
  ------------------------------------------------------------------
  A  fragment en 11:7        CONTRADICE con B   manual de hardware
  B  fragment en bit 12      COMPATIBLE con    manual de hardware
                               fragment_size=9
  C  max_frag 9 / 31         CONSISTENTE con   ya medido
                               capacidad de memoria
  fragment_size = 9          PROVEN del target ya establecido
  ubicacion del campo        NOT_DETERMINED    falta la guia de HW

  GPU     INTACTA
  sudo    NO usado
  corpus  solo lectura
```