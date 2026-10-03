# PTEPDE en POLARIS12: qué escribe el ASIC real, y qué implica

> **v2 · 2026-10-03 · corrige claims `PROVEN` de la v1 con evidencia medida.**
> La v1 se conserva al final, con su estado. No se borra historia.

## Lo que había, y por qué se cayó

La v1 afirmaba, con etiqueta `PROVEN`:

```
El emisor de PTEPDE de POLARIS12 es sdma_v4_0_vm_set_pte_pde   PROVEN  sdma_v4_0.c:1758
El último dword es count - 1                                   PROVEN  sdma_v4_0.c:1654
```

Las dos son **`REFUTATED`**. La v1 llegó a ellas por dos vías que-now-funcionan, y
las dos están medidas:

1. **La herramienta que produjo las citas daba los números de línea 4 por debajo
   de los reales.** `./ibtrace.py func sdma_v4_0.c::sdma_v4_0_vm_set_pte_pde`
   imprimía `L1645` donde la escritura está en `L1649`. El conteo de escrituras y
   los opcodes eran correctos; solo los números mentían, y nada en la salida lo
   delata. Corregido y con oráculo (`ibtrace.py selftest`, 6791 escrituras, 0
   números incorrectos).

2. **La cadena del ASIC no llega a `sdma_v4_0`.** Escribí que la vtable asignaba
   `.set_pte_pde`; no es así, y esa frase era una suposición mía que la propia
   v1 decía no haber comprobado. La cadena real tiene **cinco** saltos, y el
   cuarto no es un campo: es una llamada.

## La cadena, medida

```
revkit/emitref.py chain
```

```
vi.c               brazo CHIP_POLARIS12 anade &sdma_v3_1_ip_block
sdma_v3_0.c        declarado en sdma_v3_0.c
sdma_v3_0.c        sdma_v3_1_ip_block.funcs = &sdma_v3_0_ip_funcs
sdma_v3_0.c        sdma_v3_0_ip_funcs.early_init = sdma_v3_0_early_init
sdma_v3_0.c        sdma_v3_0_early_init pasa &sdma_v3_0_vm_pte_funcs
sdma_v3_0.c        sdma_v3_0_vm_pte_funcs.set_pte_pde = sdma_v3_0_vm_set_pte_pde
                   EMISOR = sdma_v3_0_vm_set_pte_pde
```

Dos cosas que la v1 no vio y que son la substance del asunto:

- `.set_pte_pde` **no** está en `sdma_v3_0_ip_funcs`. Está en
  `sdma_v3_0_vm_pte_funcs`, de tipo `amdgpu_vm_pte_funcs`, y esa tabla se pasa
  por una llamada dentro de `early_init`. Un salto imaginado habría comparado el
  código propio contra la tabla equivocada y habría dado verde.
- `case CHIP_POLARIS12:` aparece **ocho veces** en `vi.c`, en ocho tablas
  distintas. Siete son tablas de capacidades. La regla no es "la primera
  etiqueta": es "el único brazo que añade bloques IP", y si hubiera más de uno
  sería una contradicción del corpus, no una elección.

## El campo `count`

`emitref.py comparar` lo dice sobre los diez dwords:

```
1  HEADER        2  LOW32(pe)     3  HIGH32(pe)
4  LOW32(flags)  5  HIGH32(flags) 6  LOW32(addr)   7  HIGH32(addr)
8  IDENT(incr)   9  CONST0       10 IDENT(count)

opcode: corpus 12, nuestro 12.   ancho: referencia 10, nuestro 10.
```

Los dos emisores coinciden **papel a papel** y opcode en **número**. El campo que
C-011 dio la vuelta dos veces es `IDENT(count)` en las dos fuentes, y el control
del selftest prueba que `count` y `count - 1` se separan en el dword 10.

## Clasificación vigente

| Afirmación | Estado | Evidencia |
|---|---|---|
| El emisor de PTEPDE de POLARIS12 es `sdma_v3_0_vm_set_pte_pde` | **PROVEN** | cadena de 5 saltos, `emitref.py chain` |
| `sdma_v4_0_vm_set_pte_pde` escribe `count - 1` | **PROVEN** | `sdma_v4_0.c:1658` |
| **pero no es el emisor de este ASIC** | **PROVEN** | el bloque de POLARIS12 es `sdma_v3_1_ip_block`, no v4_0 |
| El emisor de este ASIC escribe `count` plano | **PROVEN** | `sdma_v3_0.c:996` |
| Emite 10 dwords | **PROVEN** | contados en ambas fuentes |
| El opcode es 12 en las dos | **PROVEN** | `SDMA_OP_GEN_PTEPDE 12`, `RX550_SDMA_OP_GEN_PTEPDE 12` |
| Que el hardware espere `count` y no `count - 1` | **NOT_DETERMINED** | solo un comentario upstream lo dice; requiere runtime |
| Que `rx550_pm4.c` replica la secuencia bien | **PROVEN_DERIVED** | 10/10 papeles, opcode y ancho, contra la referencia correcta |
| Que `rx550_pm4.c` esté CORRECTO en runtime | **NOT_DETERMINED** | no se ejecuta, y no es de esta sesión |

## Sobre C-011

C-011 decía que `035`/`036` escriben un PTE de más. **Su premisa era correcta y su
conclusión no**: el código copió `sdma_v4_0`, que escribe `count - 1`, pero el
emisor de este ASIC es `sdma_v3_0`, que escribe `count`. El error estaba en el
**documento que arbitra**, no en el código que auditaba.

Y eso arrastra `docs/IMPLEMENTATION-STATUS.md` 2.1, que sigue diciendo *"EL NÚMERO
ESTÁ MAL"* y *"GRAVEDAD ALTA"* sobre un `rx550_pm4.c:298` que ya no existe como
emisor: la línea que emite es la 355. Ese fichero es de otra línea de trabajo y
**no se toca desde aquí**: se informa.

## Reproducir

```sh
./emitref.py chain       # que emisor corre, eslabon por eslabon
./emitref.py comparar    # los 10 dwords, campo a campo, con su origen
./emitref.py selftest    # 10 controles, con entrada buena y mala
./ibtrace.py selftest    # oraculo de numeros de linea sobre el corpus entero
```

`07-DRIVER/` se **lee**, no se escribe: es trabajo de otra sesión.

Sin root. `GPU INTACTA`, `WRITE_EXECUTION NONE`.

---

## v1 · 2026-10-03 antes de las 14:00 · conservada como historia

Afirmaba, con etiqueta `PROVEN`, que el emisor de POLARIS12 es
`sdma_v4_0_vm_set_pte_pde` y que su último dword es `count - 1`, y añadía que
*"el `count - 1` está en el fichero del ASIC de este proyecto. No es una
conjetura sobre `sdma_v3_0`: es `sdma_v4_0.c`, línea 1654"*.

Ese último enunciado es el que se cae: la cadena del ASIC no pasa por
`sdma_v4_0`, y está medida arriba. La v1 también cerraba con *"No arbitro
C-011"* y *"no sé si `count - 1` es correcto para POLARIS12"*. La v2 sí puede
arbitrar la primera mitad —qué fichero corre se lee estáticamente— y la segunda
sigue siendo `NOT_DETERMINED` porque depende de lo que espere el hardware.

Lo que la v2 **no** corrige, porque no puede: que el hardware espere `count`. Eso
requiere runtime, y el runtime no se ejecuta.