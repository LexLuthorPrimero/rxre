# 1029 · La página de relleno de la GART: el parámetro que `rx550_vmid0_regs_build()` recibía y nadie producía

`CLASSIFICATION=MEASUREMENT` · `TRACK=STATIC`
`CORPUS=RESEARCH/kernelbuild/linux-7.1.3` · `HARDWARE_SCOPE=HOST-C/RX550/0000:01:00.0`
`WORK_CLASS=IMPLEMENTATION` · `WRITE_EXECUTION=NONE` · `MODIFICATIONS=3`
`RUNTIME=NOT_RUN` · `GPU INTACTA`

---

## El hueco, y por qué no se veía mirando los registros

`rx550_vmid0_regs_build()` —`rx550_vmid0_gart.c:217`— construye los seis valores
del contexto 0, **en el orden** de `gmc_v8_0.c:886-897`, y el orden está en el
struct para que sea verificable:

```c
struct rx550_vmid0_regs {
	uint32_t	page_table_base;		/* GART_GPU_PFN  */
	uint32_t	page_table_start;	/* PFN           */
	uint32_t	page_table_end;		/* PFN           */
	uint32_t	protection_fault_default;	/* PFN, de SISTEMA */
	uint32_t	cntl2;			/* literal 0     */
	uint32_t	cntl;			/* bitfield      */
	unsigned	order[7];			/* el orden      */
};
```

`test_vmid0_gart` lo verifica con 119 aserciones. La aritmética del contexto 0
está **completa**.

Y aun así la secuencia no se puede ejecutar, porque uno de los seis valores es
un parámetro que **nada en el componente produce**:

```c
int rx550_vmid0_regs_build(struct rx550_vmid0_regs *regs, ..., uint64_t dummy_page_addr);
```

`protection_fault_default` sale de `dummy_page_addr >> 12`, y `dummy_page_addr`
no lo fabrication nadie. Medido:

```
$ grep -rniE 'dummy|dma_map|dma_alloc' *.c *.h | grep -v PROTECTION
(ninguno)
```

Lo único que aparece es el nombre del campo en la tabla. **No hay ni una
llamada a `dma_map_page`, ni un `alloc_page`, ni un backend de página en todo el
componente.** El parámetro existe, se valida, se desplaza y se escribe en un
struct; el productor no existe.

## Qué hace la referencia

`amdgpu_gart.c:74-88`:

```c
static int amdgpu_gart_dummy_page_init(struct amdgpu_device *adev)
{
	struct page *dummy_page = ttm_glob.dummy_read_page;

	if (adev->dummy_page_addr)
		return 0;
	adev->dummy_page_addr = dma_map_page_attrs(&adev->pdev->dev, dummy_page, 0,
						   PAGE_SIZE, DMA_BIDIRECTIONAL,
						   DMA_ATTR_SKIP_CPU_SYNC);
	if (dma_mapping_error(&adev->pdev->dev, adev->dummy_page_addr)) {
		dev_err(&adev->dev, "Failed to DMA MAP the dummy page\n");
		adev->dummy_page_addr = 0;
		return -ENOMEM;
	}
	return 0;
}
```

Y se usa en los dos contextos, `gmc_v8_0.c:889` y `:921`:

```c
WREG32(mmVM_CONTEXT0_PROTECTION_FAULT_DEFAULT_ADDR, (u32)(adev->dummy_page_addr >> 12));
WREG32(mmVM_CONTEXT1_PROTECTION_FAULT_DEFAULT_ADDR, (u32)(adev->dummy_page_addr >> 12));
```

Tres cosas de ahí que no son opinables:

1. **TTM aporta el marco, el mapa DMA lo hace amdgpu.** `ttm_glob.dummy_read_page`
   es una `struct page *`; lo que se mapea es con `dma_map_page_attrs()` de amdgpu.
   Es decir, la página global de TTM es un convenience, no una dependencia
   técnica.
2. **`DMA_BIDIRECTIONAL`, no `DMA_TO_DEVICE`.** La página es origen y destino.
   Pedir menos sería cambiar el contrato.
3. **`>> 12`.** El registro lleva un `PHYSICAL_PAGE_NUMBER` de 28 bits, no una
   dirección.

## Lo que se añadió

`rx550_dummy_page.{h,c}`: una página del sistema, mapeada por DMA en las dos
direcciones, con su ciclo de vida.

**La HAL va inyectada**, con la misma forma que ya usa el componente
(`rx550_vram_alloc_fn`):

```c
typedef int  (*rx550_dummy_map_fn)(void *ctx, void **out_cpu_va, uint64_t *out_dma_pa);
typedef void (*rx550_dummy_unmap_fn)(void *ctx, void *cpu_va, uint64_t dma_pa);
```

No para hacer la cabecera portable: **para que el contrato se pueda probar sin
GPU**. `dma_map_page_attrs()` no se ejecuta fuera del kernel, y un contrato que
solo se puede probar con la GPU delante no llega a probarse nunca. Con la HAL
inyectada, el oráculo son los contadores de `map` y `unmap`.

La HAL de kernel es `alloc_page(GFP_KERNEL | __GFP_ZERO)` + `dma_map_page_attrs(
dev, page, 0, PAGE_SIZE, DMA_BIDIRECTIONAL, DMA_ATTR_SKIP_CPU_SYNC)`, y su
deshacer es `dma_unmap_page_attrs()` + `__free_page()`.

## Los tres errores que la firma del kernelFZó, y por qué están aquí

**El `ctx` es un `struct device *`, no un `struct pci_dev *`.** La API de DMA
toma device, y la referencia pasa exactamente eso (`amdgpu_gart.c:81`,
`&adev->pdev->dev`). La primera versión tomaba `pci_dev` y kbuild lo rechazó con
tres `-Wincompatible-pointer-types` y un `-Wint-conversion`.

**`dma_unmap_page_attrs()` lleva 5 argumentos en este kernel, no 6.**
`dma-mapping.h:164`:

```c
void dma_unmap_page_attrs(struct device *dev, dma_addr_t addr, size_t size,
			  enum dma_data_direction dir, unsigned long attrs);
```

No lleva `struct page *`. Se quita en 6.x y el corpus ya está en esa. Escribirlo
con la página, de memoria, es el error que da el `too many arguments` de kbuild.

**Y por lo mismo, la página se suelta DESPUÉS de deshacer el mapa.** En este
kernel el `unmap` no la necesita, pero si en otro si, liberarla antes seria usar
memoria ya devuelta. El orden no lo detecta ningún compilador.

## `have_ops`: un campo que escribía la implementación y no leía nadie

El `struct` que empezó con un `bool have_ops` que:
- `rx550_dummy_page_init` ponía a `true`
- `rx550_dummy_page_fini` y el camino de error lo ponían a `false`
- **y no lo leía nadie de la implementación.** El único lector era el test.

Lo detectó una mutación del self-test que no debería haber detectado nada:
borrar `p->have_ops = true;` dejaba el test **completamente verde**.

La respuesta correcta no es escribir un test que lo compruebe.  Es borrarlo, y invariante real es `state == RX550_DUMMY_HELD`, y ya está. Un segundo indicador
del mismo hecho, sin consumidor, es estado que **aparenta** guardar algo. Y si
alguien lo leyera creyendo que protege el mapa, creería que el mapa está
protegido cuando lo que se protege es un booleano.

## El test, y los negativos que importan

`tests/test_dummy_page.c`, 62 aserciones. Lo que no es exercises de camino feliz:

| caso | por qué existe |
|---|---|
| doble `init` sin `fini` | devolvería OK con el mapa de la llamada anterior, que no es del llamador de ahora |
| `map` devuelve error | el estado queda `ABSENT` y **no se guarda HAL**: alguien no puede deshacer un mapa que no existe |
| `map` "devuelve exito" con PA 0 | no es un mapa |
| `map` "devuelve exito" con VA nulo | no es un mapa |
| `fini` sobre `ABSENT` | `remove()` llama a `fini` también cuando `probe()` falló antes de la página; que eso sea un segundo fallo convierte un unwind en dos |
| `fini` dos veces | `unmap` sigue siendo una vez |
| `fini` sin `init` | **no llama a `unmap`** — el oráculo es el contador, no el código de salida |
| salida nula en `pfn`/`pa` | y la salida **no se toca**: un llamante que ignore el código no lee un número de la reserva |

Y el caso que es la trampa de esta pieza:

```
CHECK_EQ(v, (uint32_t)(0x123456789ULL >> 12), "D1 PFN == PA >> 12");
CHECK((uint32_t)(0x123456789ULL >> 12) != (uint32_t)(0x123456789ULL >> 16),
      "D1 >>12 y >>16 NO dan el mismo numero: el vector distingue");
```

El segundo vector existe porque `>> 16` también "cabe" en 28 bits y también
parece plausible. Un `shift` equivocado que dé un número de 28 bits no se detecta mirando el tamano.

## Self-test, seis mutaciones

| mutación | resultado |
|---|---|
| sin rechazo del doble `init` | 2 FAIL |
| `unmap` sin comprobar el estado | 2 FAIL |
| sin `p->have_ops = true` | **0 FAIL** <- el que descubre el campo muerto |
| `>> 12` cambiado por `>> 16` | 2 FAIL |
| borrar la `ops` guardada en el camino de error | **0 FAIL** ← mutante equivalente |
| sin validación de la HAL incompleta | 2 FAIL |

La quinta **no la detecta y no debe**: limpiar `ops` en el camino de error o no
limpiarlo es indistinguible, porque `state != HELD` ya bloquea el `fini`. Es un
mutante equivalente, no un hueco. Anotarlo es lo que separa «el test no cubre»
de «no hay nada que cubrir».

## Estado

- 20 suites en la puerta, `con_problema=0`, `make EXIT=0`
- 12 unidades de traducción, 9 compilando bajo la ABI del kernel (antes 8)
- `rx550_drv.ko`: 932536 bytes, 7 símbolos `rx550_dummy_*`, 27 sin resolver y
  **0 sin exportar**
- El contexto 0 sigue sin escribir en el hardware: falta la llamada desde
  `probe()` y falta el takeover

## Lo que este hallazgo NO dice

- **No dice que `dma_map_page_attrs()` funcione en esta placa.** No se ha
  ejecutado. Con 40 bits de mascara DMA (`gmc_v8_0.c:1138`:
  `dma_set_mask_and_coherent(adev->dev, DMA_BIT_MASK(40))`), debería, pero eso
  es `RUNTIME_REQUIRED`.
- **No dice que la página sirva para algo.** Que el hardware escriba en ella
  cuando una entrada de la GART se invalida es lo que la referencia supone al
  llamarla *dummy read page*. No verificado aquí.
- **No toca el hardware.** Cero escrituras.

## Trazabilidad

- Referencia: `amdgpu_gart.c:74-88` (`init`), `:99-106` (`fini`),
  `gmc_v8_0.c:889` y `:921` (los dos usos)
- Contrato del driver: `rx550_vmid0_gart.c:217-246`, campo
  `protection_fault_default`, `order[6] = 6` es el INVALIDATE que lo sigue
- API: `dma-mapping.h:161-165` de este kernel; máscara DMA en `gmc_v8_0.c:1138`
- Secuencia completa del contexto 0: finding `1028`
- Prefijo de numeración: 1029, reservado antes de escribir