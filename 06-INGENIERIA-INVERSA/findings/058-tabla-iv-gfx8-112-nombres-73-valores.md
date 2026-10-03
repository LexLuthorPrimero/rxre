# 058 · La tabla de IV de GFX8: 112 nombres, 73 valores, y 8 alias que el hardware no puede distinguir

`CLASSIFICATION=DOCUMENTATION` · `TRACK=STATIC` · `CORPUS=RESEARCH/working/linux-7.1.3`
`HARDWARE_SCOPE=HOST-C/RX550` · `WORK_CLASS=READ_ONLY/EVIDENCE`
`WRITE_EXECUTION=SCOPED(findings)` · `RUNTIME=NOT_RUN` · `GPU INTACTA`
`CONTINUES=051 §2, 052 §5` · `CUBRE=el hueco que queda en §D`

## CUDA principal

`052 §5` decía que hay 112 vectores y lo dejó como cifra a cataloguear.
Al cataloguearlos sale algo que **cambia la interpretación**: **112 son nombres,
73 son valores.** Ocho valores tienen alias, y uno de ellos tiene doce nombres
para lo mismo.

El que importa: los tres `VERTICAL_INTERRUPT` de un display **comparten un único
SRCID con los `EXT_TIMING_SYNC_LOSS`**. Eso significa que un anillo no puede
distinguir por el IV entre "vblank" y "sync lost". No es una limitación del
decodificador del driver: es granularidad del propio evento en hardware.

Y de paso, un defecto en el header de AMD: `CP_ECC_ERROR` está declarado **dos
veces** con el mismo nombre y el mismo valor.

## 1 · El inventario, con los 8 alias

Parseados los 112 `#define VISLANDS30_IV_SRCID_*` de
`include/ivsrcid/ivsrcid_vislands30.h`, normalizando a decimal:

```
112 defines · 73 valores distintos · 8 valores con alias
```

| valor | nº de nombres | alias |
|---|---|---|
| `0x13` (19) | **6** | `D1_VERTICAL_INTERRUPT{0,1,2}` · `D1_EXT_TIMING_SYNC_LOSS` · `D1_EXT_TIMING_SYNC` · `D1_EXT_TIMING_SIGNAL` |
| `0x14` (20) | **6** | ídem para D2 |
| `0x15` (21) | **6** | ídem para D3 |
| `0x16` (22) | **6** | ídem para D4 |
| `0x17` (23) | **6** | ídem para D5 |
| `0x18` (24) | 3 | `D6_VERTICAL_INTERRUPT{0,1,2}` |
| `0x2a` (42) | **12** | `HOTPLUG_DETECT_A..F` · `HPD_RX_A..F` |
| `0xc5` (197) | 2 | `CP_ECC_ERROR`, **duplicado con el mismo nombre** |

## 2 · Lo que esto significa para un ring

El IV entrega un `src_id` de 8 bits (`tonga_ih.c:262`, ver `051 §2`). No entrega
un nombre. Por tanto:

- **`0x13` no distingue** entre `D1_VERTICAL_INTERRUPT0`, `…1`, `…2`,
  `D1_EXT_TIMING_SYNC_LOSS`, `D1_EXT_TIMING_SYNC` ni `D1_EXT_TIMING_SIGNAL`.
  Seis eventos distintos, un SRCID.
- **`0x2a` no distingue** entre los doce alias de hotplug. `HOTPLUG_DETECT_A` y
  `HPD_RX_A` son el mismo evento visto desde dos Convenciones de nomenclatura:
  seis líneas de detección TX y seis de recepción RX colapsadas en un vector.
- **`0xc5` está declarado dos veces** con idéntico nombre y valor. En C el segundo
  `#define` es redundante y no rompe nada, pero es evidencia de que el fichero es
  **generado y no está revisado**. Cualquier herramienta que derive código o
  tablas desde este header hereda la duplicación.

**El rango real de `src_id` que el hardware puede emitir es 73, no 112.** La
cifra 112 cuenta nombres.

## 3 · El hueco que queda en §D

`AGENTS.md:612-626` pide separar orden de emisión, orden de ejecución y orden de
completación. Con esta tabla hay una precisión que no estaba:

**Un paquete que espera por vertical interrupt y wake por `EXT_TIMING_SYNC_LOSS`
no puede distinguir ambos por el IV.** La información que los separa no está en
el vector. Las tres rutas que quedan son:

1. otro registro con el detalle del evento — **no identificado**
2. el `src_data[0]` de 28 bits (`tonga_ih.c:263`), que para estos eventos podría
   llevar el identificador de línea. **No verificado**
3. estado del propio hardware de display (registro de estado de scanout)
   — **no rastreado**

Esto es `NOT_DETERMINED` con las tres candidatas nombradas. No lo marco como
ausencia: no he buscado lo suficiente.

## 4 · Clasificación

| afirmación | clase | estado |
|---|---|---|
| 112 nombres, 73 valores distintos | DERIVATION | **PROVEN_DERIVED** |
| 8 valores con alias, uno con 12 nombres | DERIVATION | **PROVEN_DERIVED** |
| D1..D5 vertical_interrupt comparten SRCID con sync_loss | FACT | **PROVEN** |
| `CP_ECC_ERROR` declarado dos veces idéntico | FACT | **PROVEN** |
| rango real de src_id = 73 | DERIVATION | **PROVEN_DERIVED** |
| por dónde llega la información que el IV no da | — | **NOT_DETERMINED**, 3 candidatas |

## 5 · Corrección a `052 §5`

`193` decía "la tabla tiene **112** vectores declarados". El número es correcto
como número de `#define`, pero induce a leer 112 como rango de valores posibles.
La cifra correcta para el rango es **73**. No he editado `193`: su scope lo tiene
otro proceso. Este documento lo deja corregido.

## Nota de proceso

Mi primer grep exigía formato `0x…` y devolvió **54**. Leí ese 54 como número de
vectores durante un comando antes de comprobar que los otros 58 declaran el valor
en decimal. Es la **misma clase de error que `block_size` 13-vs-10** — un valor
con un formato distinto del que asumí, leído como si fuera el valor del dominio —
y van cuatro veces en la sesión.

También es la segunda vez que casi corrijo un documento ya escrito sin
comprobar el resultado antes: si hubiera dado 54 por bueno, este hallazgo sería
falso. La normalización a decimal antes de contar es lo que lo evitó.