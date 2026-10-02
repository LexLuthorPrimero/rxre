# 074 · F2b: el host NO compone el PTE — lo compone el hardware a partir de `addr` + `flags`

```
CLASSIFICATION=DOCUMENTATION · TRACK=STATIC · CORPUS=RESEARCH/working/linux-7.1.3
HARDWARE_SCOPE=HOST-C/RX550/0000:01:00.0 · WORK_CLASS=READ_ONLY/EVIDENCE
WRITE_EXECUTION=NONE · MODIFICATIONS=0 · RUNTIME=NOT_RUN · GPU INTACTA
```

## Qué resuelve, y por qué cambia la pregunta

F2b pregunta: *"para cada bit que el driver escribe en el PTE de GFX8 — VALID,
SYSTEM, permissions — ¿qué significa?"*. Y da por hecho que **el driver escribe
los bits**.

**No los escribe.** La operación `GEN_PTEPDE` no recibe un PTE armado: recibe la
dirección física y una máscara de flags, y **es el hardware el que compone la
entrada de page table**. Eso reescribe la frontera entera.

## La evidencia

```
sdma_v3_0.c:987   SDMA_PKT_HEADER_OP(SDMA_OP_GEN_PTEPDE)
sdma_v3_0.c:988   lower_32_bits(pe)      /* dst addr: DÓNDE escribir la tabla */
sdma_v3_0.c:990   lower_32_bits(flags)  /* mask:  qué bits activar           */
sdma_v3_0.c:992   lower_32_bits(addr)   /* value: la DIRECCIÓN FÍSICA       */
sdma_v3_0.c:994   incr                   /* incremento por entrada          */
sdma_v3_0.c:996   count                  /* número de entradas              */
```

Tres campos, y ninguno es "el PTE":

| campo | qué es |
|---|---|
| `addr` | **la dirección física de la página**. 28 bits útiles (el layout reserva 39:12). |
| `flags` | **una máscara**, no un valor. El host dice qué bits poner a 1, no qué número escribir. |
| `pe` | dónde se escribe la tabla resultante (la page table base) |

Y el valor recibido se llama `addr` porque es la dirección. **El host nunca
calcula `(addr & ~0xFFF) | (flags & mask) | valid`.** Eso lo hace el hardware.

Esto concuerda con `C-011`, que ya resolvió que el emisor correcto es
`sdma_v3_0`, y le añade la razón por la que la corrupción silenciosa de RE-04/RE-05
era posible: si el host no compone el PTE, **copiar el código del driver no
reproduce la construcción del PTE**, y un error en la máscara produce un PTE
plausible y erróneo.

## El layout está documentado, en el propio driver

```
gmc_v8_0.c:691    PTE format on VI:
gmc_v8_0.c:693      63:40 reserved
gmc_v8_0.c:694      39:12 4k physical page base address
gmc_v8_0.c:695      11:7  fragment
gmc_v8_0.c:696      6     write
gmc_v8_0.c:697      5     read
gmc_v8_0.c:698      4     exe
gmc_v8_0.c:699      3     reserved
gmc_v8_0.c:700      2     snooped
gmc_v8_0.c:701      1     system
gmc_v8_0.c:702      0     valid
gmc_v8_0.c:704    PDE format on VI:
gmc_v8_0.c:705      63:59 block fragment size
gmc_v8_0.c:707      39:1  physical base address of PTE
gmc_v8_0.c:709      0     valid
```

Nueve bits con nombre más dos reservados. **Del total de 64, el 88% es dirección
física y el 12% son 9 bits de control.** Esa proporción es la razón por la que
`block_size` (10 bits, en `PAGE_TABLE_BLOCK_SIZE` de `VM_CONTEXT*_CNTL`, según
`064`) tiene sentido: 10 bits de fragmentación sobre 22 de dirección.

**Y esto ya estaba escrito.** F2b dice "el censo está cerrado (RE-22)". El censo
de *qué bits existen* estaba cerrado; lo que faltaba era *quién los pone*, y es
el hardware.

## Lo que esto abre y lo que cierra

Cierra, en el sentido de que ya no es pregunta:

- ~~"¿qué bits escribe el driver?"~~ → ninguno. Manda una máscara.
- ~~"¿cómo se arma el PTE?"~~ → no se arma en el host.

Deja abierto, y con nombre:

| pregunta | estado |
|---|---|
| Qué máscara pasa el driver en cada caso | `NOT_DETERMINED` — hay que trazar `flags` en `amdgpu_vm.c` |
| Si el hardware añade bits que el host no pidió (p. ej. `valid`) | `NOT_DETERMINED` — es lo que la spec diría y no hay |
| Cómo traduce el hardware `addr` a bits 39:12 | `NOT_DETERMINED` |
| Si la máscara puede pedir un `valid=0` | `NOT_DETERMINED`, y es una pregunta de seguridad |
| Significado exacto de `fragment` (bits 11:7) | `NOT_DETERMINED` |

La cuarta es la que más importa para un driver propio: **si `valid` está en la
máscara que el host envía, entonces el host puede deshabilitar su propia
traducción**, y un round-trip que pase por el decodificador propio no lo
detectar porque el decodificador del proyecto ya asume que `valid=1`.

## Por qué esto no se puede cerrar estáticamente

La composición del PTE ocurre en el hardware. El corpus da el layout y el
protocolo; **no da la circuitería**. Es el mismo caso que `F3c`: la spec de GCN3 no se
publicó nunca (RE-29), y el framing y los campos se deducen del corpus, pero la
semántica del bloque generador es hardware.

La ruta discriminante sería **leer un PTE que el hardware acaba de generar**:
poner un solo mapping conocido, forzar la traducción, y leer la tabla. Eso es un
`RREG32` sobre la page table base, que es lectura pura — **no requiere cargar un
módulo ni root**. Es la diferencia con F1 y F2, y no la he ejecutado porque
requiere crear un contexto de usuario con `LIBGPU_VM` yMappings, que es
implementación.

## Procedencia

- `CORPUS` — `sdma_v3_0.c:952-997`, `gmc_v8_0.c:691-710`.
- Relación con trabajo previo: `C-011` resolvió el emisor correcto; `023` y
  `036` escriben el emisor. Esta nota explica por qué `036`, que copia el
  emisor, no reproduce la construcción del PTE.
- Sin `RUNTIME`, sin lectura de la GPU, sin escrituras.
- No se editó `OPEN-FRONTIERS.md` ni `F2b`: son de otra sesión.