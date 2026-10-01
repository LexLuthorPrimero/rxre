# PTEPDE en POLARIS12: qué escribe el ASIC real, y qué implica

## Lo que ya se sabia por C-011

`docs/CONTRADICTIONS.md` tiene `C-011`, severidad **MUY ALTA**:

> El emisor de PTE correcto es `sdma_v3_0`, no `sdma_v4_0`. `035` y `036`
> escriben un PTE de más. Un driver propio que copie ese código escribe UN PTE
> POR ENCIMA del final del rango pedido, en el ASIC real. Es corrupción
> silenciosa de memoria.

El arbitraje dice «el kernel en ejecución zanja, a favor de `sdma_v3_0`».

## Qué resuelve la herramienta

`./ibtrace.py func sdma_v4_0.c::sdma_v4_0_vm_set_pte_pde`:

```
L1645  SDMA_PKT_HEADER_OP(SDMA_OP_PTEPDE)   header, opcode 12
L1646  lower_32_bits(pe)                    dst addr bajo
L1647  upper_32_bits(pe)                    dst addr alto
L1648  lower_32_bits(flags)                 mask bajo
L1649  upper_32_bits(flags)                 mask alto
L1650  lower_32_bits(addr)                  value bajo
L1651  upper_32_bits(addr)                  value alto
L1652  incr                                 increment size
L1653  0
L1654  count - 1                            <-- numero de entradas
--- 10 escrituras
```

Y la vtable lo confirma: `sdma_v4_0.c:1758` asigna
`.set_pte_pde = sdma_v4_0_vm_set_pte_pde`. Ese es el emisor del ASIC.

**El `count - 1` está en el fichero del ASIC de este proyecto.** No es una
conjetura sobre `sdma_v3_0`: es `sdma_v4_0.c`, línea 1654.

## Por qué `count - 1` es lo correcto (o por qué es peligroso)

El último dword del PTEPDE es el **número de entradas**, y el hardware espera
`count - 1`, es decir, un índice, no un número. Escribir `count` daría una
entrada de más.

Eso es exactamente lo que dice `C-011`: un PTE por encima del final del rango
es **corrupción silenciosa**, no un error visible.

Ahora bien: **que el hardware espere `count - 1` es lo que dice el comentario
del código**, no una medición. El comentario es documentación upstream:

```c
ib->ptr[ib->length_dw++] = count - 1; /* number of entries */
```

Que ese comentario sea correcto para `sdma_v4_0` no está demostrado por el
corpus: es la intención del autor. Si `C-011` tiene razón en que hay un
problema, el lugar a mirar es esta línea, no la elección entre ficheros.

## Lo que esto NO cierra

- **No sé si `count - 1` es correcto para POLARIS12.** Es lo que escribe el
  driver de referencia para este ASIC, y su comentario dice que es el número
  de entradas. Confirmarlo requiere runtime.
- **No sé si `036` en `rx550_pm4.c` replica esta secuencia.** Eso se comprueba
  leyendo ese fichero, no el corpus.
- **No arbitro `C-011`.** Puedo decir dónde está la línea y qué forma tiene.
  Decidir si el driver propio la replica bien o mal es trabajo de la
  implementación, con su propio control.

## Clasificación

| Afirmación | Estado |
|---|---|
| El emisor de PTEPDE de POLARIS12 es `sdma_v4_0_vm_set_pte_pde` | **PROVEN** — `sdma_v4_0.c:1758` |
| Emite 10 dwords | **PROVEN** |
| El último es `count - 1` | **PROVEN** — `sdma_v4_0.c:1654` |
| El opcode es 12 | **PROVEN** — el mismo en v6, v7 y vega10 |
| Que el hardware espere `count - 1` | **NOT_DETERMINED** — solo lo dice un comentario |
| Que `036` replique esto bien o mal | **NOT_OBSERVED** — hay que leer `rx550_pm4.c` |

## Reproducir

```sh
./ibtrace.py func sdma_v4_0.c::sdma_v4_0_vm_set_pte_pde
./cidx.py use SDMA_OP_PTEPDE        # opcode 12 en toda la familia
./cidx.py vtable set_pte_pde         # quien asigna el campo de vtable
```

Sin root. `GPU INTACTA`, `WRITE_EXECUTION NONE`.