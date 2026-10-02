# AGENTS-ADDENDA — propuesta de addenda para `AGENTS.md`

> **Por qué existe este fichero.** `AGENTS.md` es lo **primero** que lee cualquier
> agente en este repositorio. Su sección `ESTADO ACTUAL YA CONOCIDO` termina con
> *"NO reabrir estas cuestiones salvo que aparezca nueva evidencia contradictoria"*, y esa
> lista es en su mayor parte correcta — pero **no menciona la línea de trabajo que se
> está avanzando**, y en un punto dice algo que ya se sabe falso.
>
> `AGENTS.md` está **modificado sin commitear** (1434 líneas de diff) desde las 10:24.
> Añadir una sección ahí sería escribir encima de otra sesión. Por eso esto es un
> fichero aparte: **adoptarlo es pegar un enlace**. Frontera `F8`.
>
> `REDACTADO 2026-10-01 12:20 -03:00` · contrastado contra el árbol real

---

## 1 · Lo que `AGENTS.md` ya dice bien, y no hay que tocar

Verificado contra el árbol el 2026-10-01. Esta lista **se sostiene** y es lo más valioso
del fichero:

```
PROVEN_DERIVED    Polaris12/GFX8 · 2 SE · 1 SA por SE · 8 CU · CU mask 0x1e · 4 RB
PROVEN_DERIVED    fragment_size = 9
PROVEN            GART: placement BEST_FIT · hole vía max_mc_address · base alineado
                  a 4 GiB · gart_end derivado tras la alineación
OBSERVED          BAR/full-visible = FALSE · vm_update_mode = -1
PROVEN_DERIVED    política efectiva = vm_update_mode 0
PROVEN_DERIVED    el writer CPU de page tables es inalcanzable bajo esa política
PROVEN_DERIVED    amdgpu_vm_map_gart() inalcanzable en esta ruta
PROVEN            SDMA es el writer efectivo de page tables
PROVEN            root.bo real · vm_manager no contiene root · root_dir ausente
PROVEN            PTBA software production cerrada · VM flush emission cerrada
                  WAIT_REG_MEM encoding cerrada · PFP_SYNC_ME emission condition
OBSERVED          FUNCTION(0) = always probado a nivel de encoding
NOT_DETERMINED    hardware execution ordering · PTBA+invalidate atomicity
NOT_DETERMINED    hardware PTE visibility point
OBSERVED          runtime takeover NO EJECUTADO · GPU INTACTA · WRITE_EXECUTION NONE
```

**Cuidado con dos de esas líneas**, porque se han matizado o refutado, y el fichero no lo dice:

| Línea de AGENTS.md | Estado real | Dónde está el matiz |
|---|---|---|
| "`amdgpu_vm_map_gart()` inalcanzable en esta ruta" | **REFUTED como generalización.** El finding `023-pte` §6 dice: *"GART y GPUVM tienen reglas de inalcanzabilidad distintas. Documentar sólo la de GPUVM fue mi error de alcance."* La inalcanzabilidad probada es la del writer de PTE de GPUVM | `023-pte` §6 |
| "`FUNCTION(0) = always` … hardware trigger todavía NO_DETERMINED" | **REFORMULADO, nocerrado.** `017` §5: *"no es 'cuándo dispara el trigger' sino 'qué significa un wait sin predicado'"*, y `018` lo convierte en `NOT_IMPLEMENTABLE`: no hay registro de ack | `017` §5, `018` §CUDA |

---

## 2 · Lo que falta, y es lo que hace que un agente repita trabajo

Todo lo siguiente está `PROVEN` en el árbol y **no aparece en `AGENTS.md`**:

```
FASE              la línea A (GFX8 reverse engineering + driver propio) es la que se
                  trabaja. La línea de telemetría de septiembre está cerrada.

HARDWARE          block_size = 10, NO 9. Y la razón: max_level = 1 da num_level = 1, y
                  con num_level == 1 el driver pasa `tmp` (=2) a get_block_size, no
                  `vm_size` (=64). get_block_size(2) = 10. La rama que da 9 NO CORRE.
                  014-q1 declaró 9 / 30 bits / 2 MiB como PROVEN. Los tres están mal.
                  Contraste: el host imprimió "block size is 10-bit" en el boot
                  -> 2599c65, RE-10, C-005

HARDWARE          geometría completa: num_level 1 · root_level PDB0 · max_pfn 16777216
                  · block_size 10 · PTB 1024 entradas (8 KiB) · PDB0 16384 (128 KiB)
                  · GPUVA 36 bits · unidad mínima 4 MiB
                  -> RE-10, validado con 37 aserciones y 12 controles negativos

HARDWARE          el productor de PTE es un PAQUETE SDMA de 9 dwords,
                  SDMA_OP_GEN_PTEPDE (opcode 12), no una función de CPU.
                  El writer CPU existe y es correcto, y está cerrado por diseño.
                  CONSECUENCIA: el driver propio emite un paquete, no escribe memoria
                  -> RE-04

HARDWARE          el path de RING no puede observar completion del invalidate: no hay
                  registro de ack, y WAIT_REG_MEM se emite con FUNCTION=0 (always),
                  ref=0, mask=0. Ningún bit se compara
                  CONSECUENCIA: esperar completion es NOT_IMPLEMENTABLE, no pendiente
                  -> RE-01, RE-02

HARDWARE          hay un SEGUNDO path, la ruta GART, que sí tiene completion, porque
                  la ejecuta la CPU (mb() + flush_hdp). Son dos, no uno
                  -> RE-13

HARDWARE          el fence es el ÚNICO punto del path de submit donde el hardware
                  confirma que el trabajo anterior terminó. GFX emite EVENT_WRITE_EOP x2,
                  COMPUTE RELEASE_MEM x1. Cambia en cada generación
                  -> RE-18

HARDWARE          VM_INVALIDATE_REQUEST no tiene granularidad en GFX8: 16 bits, un bit
                  por VMID. flush_type y vmhub son PARÁMETROS MUERTOS
                  -> RE-03

HARDWARE          PRT (bit 51) no es un tipo de entrada en GFX8: NADIE lo pone y el
                  único que lo menciona lo borra. El mecanismo equivalente es el
                  aperture de rango mmVM_PRT_APERTURE*
                  -> RE-05, RE-22

HARDWARE          PAGE_TABLE_DEPTH recibe 0 para el contexto 0 (GART) y 1 para los
                  contextos 1-15. El corpus NO declara qué significan
                  -> RE-12

PRESUPUESTOS      frame GFX8 = 121 dw (137 con chained IB). La reserva de un envío son
                  DOS SUMANDOS: emit_frame_size + num_ibs * emit_ib_size.
                  La ruta máxima de amdgpu_vm_flush = 63 dw, y es ALCANZABLE.
                  Ningún ring infra-reservado
                  -> RE-14, RE-16, NR-07c

CORPUS            hay un SEGUNDO corpus, 7.2.8. Y el árbol "local" de rx550-upstream
                  es upstream prístimo: local.sha256 == upstream.sha256. Nadie ha
                  parcheado el driver de referencia en este repo

HERRAMIENTAS      tools/ tiene seis herramientas validadas con capacidad de fallo
                  demostrada: pm4_count_census.py · pm4dw.c · gfx8vmgeom · pteflags ·
                  validate_rx550_final.py · (frame_budget, count_vmflush_dw)
                  Y UNA INVALIDA: semref, porque Coccinelle vivía en /tmp y se perdió
                  -> TOOLS-STATUS.md

IMPLANTACIÓN      Stage 1 del driver propio: rx550_drv.ko SÍ es driver PCI y rx550.ko
                  NO lo es, verificado con nm, con control negativo. NINGUNO está
                  cargado. nhwa tampoco
                  -> IMPLEMENTATION-STATUS.md

HOST              el host es Nobara 44, kernel 7.1.3-fc44, Mesa 26.2.3, y la RX550 es
                  card1 en 0000:01:00.0. El README dice 43 / 6.18.2 / card2: obsoleto
                  -> CURRENT-STATE.md
```

---

## 3 · El texto de la addenda, listo para pegar

Si una sesión con permiso escribe en `AGENTS.md`, esto va al final de
`ESTADO ACTUAL YA CONOCIDO`:

```markdown
---

## ADDENDA — línea GFX8 / driver propio (2026-10-01)

La sección anterior describe la línea de investigación de septiembre. Esta describe la
que se trabaja ahora. **El estado completo, con evidencia, está en `docs/`.**

Empieza por `docs/MASTER-RESEARCH-STATUS.md`. No reconstruyas el estado leyendo otros
ficheros.

### Cifras que sustituyen a otras de arriba

- `block_size = 10`, no 9. `num_level = 1` porque `max_level = 1`, y con `num_level == 1`
  el driver pasa `tmp` (=2) a `amdgpu_vm_get_block_size`, no `vm_size` (=64).
  `get_block_size(2) = 10`; la rama que da 9 no se ejecuta. El host imprimió
  "block size is 10-bit" en el boot.
- Geometría completa: `num_level 1` · `root_level AMDGPU_VM_PDB0` · `max_pfn 16777216` ·
  `block_size 10` · `fragment_size 9` · PTB 1024 entradas (8 KiB) · PDB0 16384 (128 KiB)
  · GPUVA 36 bits · unidad mínima 4 MiB.
- `GPUVA_WIDTH_BITS` NO es 30. Es 36.

### Dos de las líneas anteriores se corrigen

- "`amdgpu_vm_map_gart()` inalcanzable en esta ruta" se debe leer como **el writer de
  PTE de GPUVM**. GART tiene una regla de inalcanzabilidad distinta, y el error
  documentado fue tratar la de GPUVM como si fuera la única. Ver `023-pte` §6.
- "`FUNCTION(0) = always`, trigger `NOT_DETERMINED`" ya no se pregunta "cuándo dispara
  el trigger" sino **"qué significa un wait sin predicado"**, y la respuesta es
  `NOT_IMPLEMENTABLE`: GFX8 no expone registro de acknowledgement, y con
  `mask = 0` ninguna lectura del paquete puede discriminar completion. Ver `017` §5,
  `018`.

### Lo que ya está cerrado y no hay que volver a abrir

- El productor de PTE es un **paquete SDMA de 9 dwords**, `SDMA_OP_GEN_PTEPDE`
  (opcode 12). El driver propio **emite un paquete**, no escribe page tables.
- `PRT` (bit 51) no es un tipo de entrada en GFX8: nadie lo pone y el único que lo
  menciona lo borra. El equivalente es `mmVM_PRT_APERTURE*`.
- `VM_INVALIDATE_REQUEST` no tiene granularidad: 16 bits, un bit por VMID.
  `flush_type` y `vmhub` son parámetros muertos en GFX8.
- El path de ring **no** puede observar completion del invalidate. La ruta **GART sí**,
  porque la ejecuta la CPU. Son dos paths, no uno.
- El fence es el único punto del path de submit donde el hardware confirma que el
  trabajo anterior terminó.
- Presupuestos: frame 121 dw (137 con chained IB); `amdgpu_vm_flush` 63 dw, alcanzable;
  la reserva son dos sumandos (`emit_frame_size + num_ibs * emit_ib_size`).

### Lo que sigue abierto, con la causa nombrada

- **Semántica de hardware de cada bit de PTE.** El *censo* está cerrado —qué productor
  escribe qué bit, con estado `WRITTEN` / `CLEARED_NOT_SET` / `OTHER_GEN`—, la
  *semántica* no. Falta la especificación primaria. Es `NOT_DETERMINED` y no se cierra
  leyendo más código.
- **Qué significa `PAGE_TABLE_DEPTH` 0 frente a 1.** Misma causa: falta la spec.
- **El intervalo de `0x20` de un `WAIT_REG_MEM` sin predicado.** Requiere runtime.
- **Orden del invalidate respecto al siguiente IB.** Requiere runtime y una ruta de
  recuperación independiente demostrada.

### Dos reglas que este repo ya aprendió por el camino

1. **No dar por hecho el `cwd`.** Las herramientas de análisis usan rutas relativas al
   directorio de la herramienta, y desde la raíz del repo fallan con un mensaje que
   nombra la causa equivocada. Ejecutar desde el propio directorio.
2. **Una herramienta que marca `NOT_FOUND` o `ABSENT` no ha demostrado que no exista.**
   En `pm4dw` un cap heurístico hizo desaparecer una función real. Buscar con
   `tools/evidence_search.py`, que obliga a declarar el universo de búsqueda y clasifica
   sin hits como `NOT_DETERMINED`, nunca como ausencia.
```

---

## 4 · Por qué está redactado como fichero aparte y no aplicado

```
AGENTS.md         modificado sin commitear desde las 10:24 (1434 líneas de diff)
                  mtime sin cambios desde entonces -> probablemente sesión inactiva,
                  pero sin preuve de que lo esté
CERROJO           no hay .write-lock para AGENTS.md. Su ausencia NO es permiso:
                  COORDINACION.md:88-90 exige /proc/$pid, y el PID registrado es el del
                  shell que hizo el mkdir, no el del agente (NR-10)
REGLA DE LA CASA  COORDINACION.md:184  "No reescribas trabajo ajeno sin coordinarte"
                  "Si tu versión de un fichero compila y la de otra no, el problema es
                   de ellos: informa, no lo arregles"
DECISIÓN          no escribir. Adoptar la addenda es una línea, y esa línea la pone
                  quien tenga el turno
```

Lo que sí hice, y es lo permitido: marcar `README.md` para que apunte a `docs/`, y
dejar la addenda escrita y verificada para que no haya que volver a construirla.

## 5 · Verificación de esta addenda

Todo lo afirmado aquí se comprobó contra el árbol el 2026-10-01:

| Afirmación | Cómo se verificó |
|---|---|
| `block_size = 10` y no 13 | `amdgpu_vm.c:2454` lee `amdgpu_vm_get_block_size(tmp)`; `tmp` = 2 tras la línea 2427, barrido de 2427-2454 sin reasignación. El host imprimió "block size is 10-bit" |
| geometría completa | `gfx8vmgeom make test`: 37 aserciones, 0 fallos, 12/12 controles negativos, y la cadena derivada coincide con la línea del boot |
| productor de PTE | `023-pte` §CUDA; `SDMA_OP_GEN_PTEPDE = 12` en `tonga_sdma_pkt_open.h:37` |
| sin ack de invalidate | `017` §3 con `mask = 0`; barrido de ATC/L1/L2 en `019` |
| fence con completion | `028` §1, las tres formas fechadas con el fuente |
| 121 dw y 63 dw | `026-frame` §CUDA y `025-vm-flush` §CUDA, con `pm4dw --path` |
| MTZ / PRT | `pteflags` ejecutado: 19 aserciones, 0 fallos, 5/5 controles negativos |
| corpus "local" prístino | `cmp local.sha256 upstream.sha256` → idénticos |
| Stage 1 por `nm` | `07-DRIVER/kernel/Makefile` target `check-drivers`, con control negativo |
| host real | `uname -r`, `os-release`, `glxinfo -B`, `readlink /sys/class/drm/*/device` |
| `semref` inválida | `./semref engines` → `ENGINE-NOT-AVAILABLE`; `refs` → rc=3 |