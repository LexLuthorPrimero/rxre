# 1121 — el mismo bit de PTE significa cosas opuestas en GFX8 y en GFX9: GFX8 lo borra, GFX9 lo pone

```text
AGENCIA=RX550-INVESTIGACION · WORK_CLASS=AGENT-RE-TOOLING
GENERADO=2026-10-04 · MEDIDO=EN ESTA HOST · CORPUS=rx550-upstream-7.2.8
AFECTADO=amdgpu_vm.h:73 (AMDGPU_PTE_PRT = 1ULL << 51)
         gmc_v6_0.c:385 · gmc_v7_0.c:507 · gmc_v8_0.c:722   <- BORRAN
         gmc_v9_0.c:1193 · gmc_v10_0.c:511 · gmc_v11_0.c:502 <- PONEN
         gmc_v12_0.c:537 (usa AMDGPU_PTE_PRT_GFX12 = 1ULL << 56)
ESTADO=PROVEN-PARTICION-EXACTA · lectura de corpus · GPU INTACTA
ALCANCE=este hallazgo COMPLEMENTA al 094-gfx8-solo-escribe-los-bits-0-11-del-pte,
         no lo contradice
```

## 0 · SOBRE LA CITA POR NÚMERO, QUE EN ESTE ÁRBOL NO ES ÚNICA

MEDIDO: el número `094` está **repartido entre tres ficheros** del proyecto.

```
094-arranque-y-escritura-de-4-bytes-en-campo-de-1.md
094-gfx8-solo-escribe-los-bits-0-11-del-pte.md     <- el que se cita aquí
094-sd-presupuesto-del-frame-dos-cifras-viejas.md
```

Es una de las 74 colisiones que registra `tools/check_num_unico.py`, y es la
razón por la que **este hallazgo cita por nombre de fichero y no por número**:
`094` a secas es ambiguo en este árbol.

Y no es un detalle menor: el hallazgo `1054` del proyecto llega a una conclusión
parecida sobre la forma de las referencias. **Citar un número que no identifica
un hallazgo es una cita que no se puede verificar**, y una cita que no se puede
verificar es exactamente lo que hace inservible un documento de evidencia.

## 0 bis · LO QUE `094` AFIRMÓ, Y LO QUE NO CERRÓ

El hallazgo `094-gfx8-solo-escribe-los-bits-0-11-del-pte.md` dice, y con razón:

> *GFX8 sólo escribe los bits 0-11 del PTE: el resto de la tabla de flags es de
> GFX9 en adelante.*

Su discriminante fue correcto: **leer quién escribe qué**, no leer el registro.
Y su resultado es que `gmc_v8_0.c` no escribe ningún flag de PTE por encima del
bit 40.

Lo que `094` **no** miró es que `gmc_v8_0.c` **menciona** el bit 51, y que lo
menciona para **borrarlo**:

```c
gmc_v8_0.c:722
  *flags &= ~AMDGPU_PTE_PRT;
```

Eso no es escribir un flag. Y es exactamente por eso que el resultado de `094`
sigue siendo correcto **y** al mismo tiempo está incompleto: la afirmación
"no escribe" es cierta, y la conclusión "el resto de la tabla es de GFX9 en
adelante" necesita una columna más.

## 1 · LA MEDICIÓN: LA PARTICIÓN ES EXACTA

Todos los usos de `AMDGPU_PTE_PRT` (bit 51) en el árbol, ordenados por
generación:

| fichero | generación | qué hace con el bit 51 |
|---|---|---|
| `gmc_v6_0.c:385` | GCN1 | **`*flags &= ~`** lo borra |
| `gmc_v7_0.c:507` | GCN3 | **`*flags &= ~`** lo borra |
| **`gmc_v8_0.c:722`** | **GFX8 — ESTA GPU** | **`*flags &= ~`** lo borra |
| `gmc_v9_0.c:1193` | GFX9 | `*flags \|=` lo pone |
| `gmc_v10_0.c:511` | GFX10 | `*flags \|=` lo pone |
| `gmc_v11_0.c:502` | GFX11 | `*flags \|=` lo pone |
| `gmc_v12_0.c:537` | GFX12 | usa `PRT_GFX12`, que es **bit 56**, no 51 |

**Siete de siete. Cero excepciones.** Y la partición no es arbitraria: cae
exactamente entre GFX8 y GFX9.

## 2 · POR QUÉ EL BIT 51 ES "NO-RETRY" Y POR QUÉ ESO EXPLICA LA PARTICIÓN

`amdgpu_vm.h:93-95`:

```c
/* Flag combination to set no-retry with TF enabled */
#define AMDGPU_VM_NORETRY_FLAGS_TF (AMDGPU_PTE_VALID | AMDGPU_PTE_SYSTEM | \
				   AMDGPU_PTE_PRT)
```

**PRT es "no retry"**: cuando el page walker encuentra un fault, en vez de
reintentar, lo marca y sigue. Su lectura como **software** está en
`amdgpu_vm.c:1211`:

```c
} else if (flags & (AMDGPU_PTE_VALID | AMDGPU_PTE_PRT_FLAG(adev))) {
```

Es decir: el software **lee el PTE de la tabla de page tables** y decide qué
hacer según ese bit. No es un campo que solo importe al hardware.

Y esa es la clave de la partición: **para GFX8 y anteriores, un PTE con el bit
51 puesto significa algo que el driver no quiere que ocurra, así que lo borra
explícitamente.** Para GFX9 y posteriores, la semántica del hardware cambió y el
bit pasa a ser parte del protocolo de no-retry que el driver quiere activar, así
que lo pone.

> **GFX8 limpia un bit que las generaciones más nuevas usan. Copiar la tabla de
> flags de GFX9 a GFX8 no es conservadurismo: es un cambio de comportamiento.**

## 3 · LA CADENA COMPLETA, Y CADA ENLACE CON SU FICHERO

Esto es lo que el hallazgo cierra, y `094` no lo tenía:

```
  bo_va / mapping->flags                     [amdgpu_vm.c:1362]
      |
      v  update_flags = flags; y se filtran READABLE/WRITEABLE
        contra mapping->flags                 [amdgpu_vm.c:1357-1364]
      |
      v  "Apply ASIC specific mapping flags"
        amdgpu_gmc_get_vm_pte(adev, vm, bo,
                              mapping->flags,
                              &update_flags) [amdgpu_vm.c:1367]
      |
      v  puntero a gmc_v8_0_get_vm_pte()     [tabla de gmc_v8_0.c]
         |
         v  if (vm_flags & AMDGPU_VM_PAGE_EXECUTABLE)
              *flags |=  AMDGPU_PTE_EXECUTABLE
            else
              *flags &= ~AMDGPU_PTE_EXECUTABLE
            *flags &= ~AMDGPU_PTE_PRT        [gmc_v8_0.c:719-722]
      |
      v  amdgpu_vm_update_range(..., update_flags, ...)
                                                   [amdgpu_vm.c:1371]
      |
      v  la tabla de page tables, en VRAM
```

**El punto donde el ASIC propio decide es `gmc_v8_0.c:722`, y no antes.** Todo
lo anterior es común a todas las generaciones.

Y hay un segundo punto de lectura, que es donde el software consume el bit que
el hardwarehonró:

```
  la tabla de page tables  ->  amdgpu_vm.c:1211  (flags & PRT_FLAG(adev))
```

## 4 · POR QUÉ `AMDGPU_PTE_PRT_FLAG(adev)` ES LA PIEZA QUE FALTABA

En `amdgpu_vm.c:1211` el software no lee `AMDGPU_PTE_PRT` directamente sino
`AMDGPU_PTE_PRT_FLAG(adev)`. Eso es una función, y una función **por generación**
es precisamente lo que hace posible que el mismo software funcione en GFX8 —donde
el bit 51 se borra— y en GFX12 —donde el bit de no-retry es el 56.

| generación | bit que significa "no retry" |
|---|---|
| GFX8 y anteriores | **ninguno**: el driver borra el 51 explícitamente |
| GFX9 / 10 / 11 | **51** (`AMDGPU_PTE_PRT`) |
| GFX12 | **56** (`AMDGPU_PTE_PRT_GFX12`) |

> **Un software que leyera `AMDGPU_PTE_PRT` a pelo leería un campo que en GFX8
> el propio driver se asegura de poner a cero.** Esa es la clase de bug que esta
> partición hace visible, y que una tabla de flags copiada de otra generación
> no muestra.

## 5 · LO QUE ESTO NO AFIRMA

- **No dice qué hace el hardware de esta RX550 con el bit 51.** Dice qué hace el
  **software** con él. Que el driver lo borre es `PROVEN`; que el hardware lo
  interpretaría de tal modo es `NOT_DETERMINED` y no se infobox.
- **No dice que el borrado sea necesario.** Que GFX8 lo haga y GFX9 no puede
  significar que sobra en GFX8, o que GFX9 lo mismo cambió el protocolo.
  **La diferencia está medida; el porqué no está medido y no se inventa.**
- **No toca el ASIC fuera de GFX8.** Las siete filas son de lectura de corpus.
  Lo único que es de nuestra GPU es la fila de `gmc_v8_0.c` y el hecho de que
  sea el fichero que la tabla de punteros de `adev->gmc` resuelve para esta ASIC.

## 6 · POR QUÉ ESTE HALLAZGO EXISTE Y NO ESTABA

Porque un motor de RE que deduce el bit 51 "usado por GFX9 en adelante" —que es lo
que se lee en la tabla de `amdgpu_vm.h`— y construya sobre eso un PTE de GFX8,
**hereda unaasignación que el driver de GFX8 borra expresamente**. El error no
es de Flags: es de **atribución generacional de un campo que existe en el
software de todas las generaciones y significa cosas distintas**.

Y la forma de encontrarlo fue la que `094` estableció y que conviene repetir:
**no leer el registro, leer quién escribe qué, y distinguir `|=` de `&= ~`.**
Esa distinción —**escribir un bit** frente a **limpiarlo**— es la que separa
estos dos hallazgos, y es la que no aparece en ninguna tabla.