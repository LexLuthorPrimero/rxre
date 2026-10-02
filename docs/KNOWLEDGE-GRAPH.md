# KNOWLEDGE-GRAPH — qué depende de qué

> El propósito es que cambiar una afirmaciónlocalice automáticamente qué otras quedan
> afectadas. Por eso cada nodo lleva sus aristas de entrada, no sólo las de salida.
>
> `RE-xx` referencia a [`EVIDENCE-MATRIX.md`](EVIDENCE-MATRIX.md). `N-xx` a las fronteras
> de [`OPEN-FRONTIERS.md`](OPEN-FRONTIERS.md).
> `ACTUALIZADO 2026-10-02 - revkit/` · `LAST_VERIFIED: 2026-10-02`

---

## 1 · Cadena de GPUVM: producer → representation → consumer → hardware effect

Lo que el driver propio necesita para escribir un page table, de extremo a extremo:

```
SDMA packet builder (propio)
  │  opcode 12, 9 dwords
  │  flags: amdgpu_vm.h:57-88  (VALID/SYSTEM/SNOOPED/EXECUTABLE/READABLE/WRITEABLE,
  │                           FRAG bits 11:7)
  ▼
SDMA_OP_GEN_PTEPDE                              [RE-04]
  │  el hardware genera el PTE/PDE desde los operandos
  ▼
GMC_VM_FB_LOCATION → vram_start
  │  fragment_size = 9
  ▼
root.bo  (buffer de objetos, no parte de vm_manager)
  │
  ▼
table_addr >> 12
  │
  ▼
mmVM_CONTEXT{n}_PAGE_TABLE_BASE_ADDR.PHYSICAL_PAGE_NUMBER
  │  offset (gmc_8_1_d.h) · PHYSICAL_PAGE_NUMBER es el PFN; lo confirma
  │  TVM_MAX_PHYS_FROM_PN = 2^40  ->  coherente con max_bits = 40
  ▼
PAGE_TABLE_DEPTH = 1                            [RE-12]
  │  (0 para el contexto 0 / GART, 1 para 1-15)
  ▼
page walker del hardware
  │  NO se ha observado. Lo que hay: 0 registros mmVM_* en gca/gfx_8_0_d.h
  │  y gfx_8_1_d.h; 61 en gmc/gmc_8_2_d.h  -> PROVEN en el corpus
  ▼
GPUVA → physical
```

Aristas lateralessobre este camino:

```
SDMA_OP_GEN_PTEPDE ──VALIDATES──> RE-08 (n = payload − 1)
                            └─REQUIRES→ RE-10 (geometría: cuántas tablas y de qué tamaño)
amdgpu_vm_map_gart() ──UNREACHABLE (en esta ruta)──> RE-02 (BAR 256 MiB < VRAM 2 GiB)
mmVM_PRT_APERTURE*_HIGH_ADDR = max_pfn ──COUPLED──> block_size
   └── por construcción: cambiar block_size cambia dónde acaba la GART. No son libres
       (023-pte §5)
PTE bit 3 ──UNVERIFIED──> N4 (¿el hardware lo trata como reservado?)
```

## 2 · Cadena de invalidación: los DOS paths, y por qué se confundían

```
                    ┌──────────────── path de RING (017, 018) ───────────────┐
                    │                                                       │
  gfx_v8_0_ring_emit_vm_flush()                                          │
    ├─ PTBA(vmid) = pd_addr >> 12            ──> page walker empieza a leer
    ├─ VM_INVALIDATE_REQUEST = 1 << vmid     ──> hardware invalida (no observable)
    ├─ WAIT_REG_MEM  FUNCTION=always ref=0 mask=0   ──> NO ESPERA NADA   [RE-01]
    └─ PFP_SYNC_ME (sólo ring GFX)                     ──> fence de sync
                    │                                                       │
                    └──> NO HAY REGISTRO DE ACK  ──> RE-02 NOT_IMPLEMENTABLE
                        La seguridad depende de un invariante del propio ring.

                    ┌──────────────── path GART (025) ────────────────────────┐
  amdgpu_ttm_alloc_gart → gart_map
    └─ amdgpu_gart_invalidate_tlb()          [RE-13]
         ├─ mb()                              ──> orden de escritura
         ├─ flush_hdp (bajo down_read_trylock) ──> la escritura SALE
         └─ for_each vmhub: flush_gpu_tlb(0)  ──> WREG32(0x51e, 1<<0)
              ▲
              └── el RETORNO de la función ES la sincronización. No hay ack tampoco,
                  pero aquí la sincronización es de CPU, no del ASIC
```

```
RE-01 ──UNLOCKS──> RE-02 (NOT_IMPLEMENTABLE)  ──REQUIRES──> N1 (qué garantiza el
                                                          intervalo 0x20)
RE-13 ──DOES_NOT_CONTRADICT──> RE-02   (distintos paths; RE-02 acota "del path de ring")

AMBOS PATHS ──SHARED LIMIT──> RE-03: VM_INVALIDATE_REQUEST no tiene granularidad.
              Ninguno puede pedir "sólo L1".  flush_type y vmhub se descartan.
```

## 3 · Codificación PM4: la capa que sostiene casi todo

```
PACKET3(op, n)                     RE-08  n = payload − 1, 68/68 en el path GFX8
  │                                        (170/171 en el árbol amdgpu completo)
  ├──> gfx_v8_0_ring_emit_wreg      5 dw   (PACKET3_WRITE_DATA,3 + cmd + reg + 0 + val)
  ├──> WAIT_REG_MEM                 PACKET3(...,5) -> payload 6
  ├──> COND_EXEC                    PACKET3(...,3) -> payload 4
  └──> PFP_SYNC_ME                  payload APARTE: NO es payload del WAIT_REG_MEM
                                        ── esto confirma el conteo de RE-07
```

```
RE-08 ──CORRECTS──> 022 §4 (dw4 es payload, no un extra)     [C-009 abajo]
RE-08 ──CORROBORATES──> RE-07 (el conteo de 020)
RE-08 ──NO DICE──> N1. Encoding coherente ≠ semántica de hardware.
              Es el mismo patrón que RE-01, y por eso los dos están marcados igual.
pm4dw ──MEASURE──> RE-06 (172/109 declarados) + RE-07 (residual +5)
pm4dw ──NO EXPANDE──> ce_meta / de_meta (write_multiple)     [NR-07]
```

## 3b · El camino de envío, ya medido de extremo a extremo

Lo que `pm4dw --path` y `amdgpu_ib.c` cerraron durante esta misma mañana:

```
amdgpu_ring_alloc(ring, alloc_size)                    amdgpu_ib.c:197-198
  alloc_size = emit_frame_size + num_ibs * emit_ib_size
                ^^^^^^^^^^^^^^^^        ^^^^^^^^^^^^^^^^^
                RESERVA EN DOS SUMANDOS                    (NR-07c)
  |
  +-- emit_frame_size = 172 dw declarados  (--struct: cota superior)
  |     la ruta REAL del frame = 121 dw  (137 con chained IB)      [RE-16]
  |     holgura 51 dw
  |
  +-- emit_ib_size = 4 por IB
        gfx_v8_0_ring_emit_ib_gfx escribe exactamente 4     correcto
        PERO si amdgpu_sriov_vf && PREEMPT llama a de_meta (21 dw)
        -> el IB costaría 25. ~2 IBs antes de desbordar. NO APLICA al objetivo  [NR-07c]

  secuencia de amdgpu_ib_schedule (amdgpu_ib.c:124-331), en orden de emisión:
    1-8  amdgpu_vm_flush                    63 dw   <- ruta máxima, ALCANZABLE  [RE-14]
    9    emit_mem_sync                       5
    10   init_cond_exec                      5
    11   emit_cntxcntl                       32     (11 medidos -> 32 con cnt)
    12   emit_ib x num_ibs                    4 c/u  <- cuenta aparte
    13   emit_fence (fence de usuario)       12
    14   emit_fence (af)                     12

  SEIS RAMAS DE ESTE CAMINO NO EXISTEN EN GFX8. Eso reduce el espacio de diseño del
  driver propio más que cualquier dato de registro.
  emit_cleaner_shader es NULL en Polaris12: predicado PERMANENTEMENTE falso  [RE-22]
```

```
RE-14 (63 dw, alcanzable)  ──COMPONE CON──>  RE-16 (121 dw de frame)
RE-16 ──REQUIRES──> la fórmula de dos sumandos  [NR-07c]
RE-16 ──CORRIGE LA LECTURA DE──> RE-06 y RE-07: los residuales +98/+57 se comparaban
       contra un número que nunca incluía los IBs, y no hacía falta que los incluyera
```

## 3c · El fence: el único punto con completion real

```
GFX       EVENT_WRITE_EOP x2      uno con seq-1, otro con seq y EOP_EXEC
COMPUTE   RELEASE_MEM     x1
                                        [RE-18]

RELEASE_MEM   GFX8  PACKET3(...,5)  -> 6 payload, SIN campo de número
               GFX9  PACKET3(...,6)  -> 7 payload, CON un dw extra      [RE-21]
               -> por eso GFX8 no necesita seq-1: es ESTRUCTURAL, no paramétrico
```

```
RE-18 ──NO CONTRASTE──> RE-02 / RE-01.  El fence confirma el FIN DE UN TRABAJO;
        el invalidate sigue sin completion observable. Son dos preguntas y la
        separación es lo que aporta 028
RE-18 ──CIERRA PARCIALMENTE──> F1.  "¿cómo sé que lo anterior terminó?" tiene
        respuesta. "¿el invalidate se habrá aplicado?" NO
```

## 4 · Dependencias de implementación: qué se desbloquea con qué

```
RE-10 (geometría numérica)
  ├──UNLOCKS──> planificador de page tables del driver propio
  │              (16384 PDB0 de 128 KiB, 16384 PTB de 8 KiB, 128 MiB de tablas hoja)
  ├──UNLOCKS──> saber que cabe: 128 MiB de tablas contra 256 MiB de BAR → margen 2x,
  │              y ese margen depende de la RAM del host (research_log.md:496)
  └──REQUIRES──> nada. Es la afirmación más accionable de la línea A.

RE-04 (PTE es un paquete SDMA)
  ├──REPLACES──> "implementar un writer de page tables en CPU"  ──> no hace falta
  ├──REQUIRES──> RE-10 (para dimensionar)  +  RE-08 (para codificar bien)
  └──UNLOCKS──> el primer componente real del driver propio

RE-12 (PAGE_TABLE_DEPTH asimétrico)
  ├──UNLOCKS──> N3 (¿qué significa?)  ──> y N3 es BLOCKED_BY_CORPUS
  └──VALORA──> es el punto exacto donde el modelo del kernel y el de userspace
               divergen en el mismo ASIC. Localizada y sin explicar = buen blanco

RE-02 (sin ack)
  ├──BLOCKS──> "hacer el vm-flush seguro esperando"  ──> no hay cómo
  └──FORCES──> el invariante del ring como mecanismo de seguridad. Que sea
               suficiente está NOT_DETERMINED (N2)

RE-14 + RE-16 (63 dw + 121 dw, medidos)
  ├──UNLOCKS──> el número de reserva del driver propio, que ya no es "copiar N*5+9"
  │              del driver de referencia sino un número medido con dos sumandos
  ├──UNLOCKS──> saber que seis ramas del camino de envío NO existen, lo que reduce el
  │              espacio de diseño antes de escribir una línea
  └──REQUIRES──> nada más. Es la afirmación más barata de toda la línea A
```

## 5 · Grafo de la línea BC3

```
compresor CPU (Fase 1) ──PRODUCE──> bloques BC3
  │                                     │
  │                                     ├──CONSUMIDO POR──> sampler del hardware
  │                                     │        (OBJETIVO del proyecto)
  │                                     │        └──> AD-12  NOT_DETERMINED  [N7]
  │                                     │            ¿trunca o redondea?
  │                                     │            Si trunca: AD-11 se REVIERTE
  │                                     │            y se reabre la divergencia
  │                                     │            contra bcdec
  │                                     │
  │                                     └──CONSUMIDO POR──> shader propio (Fase 2)
  │                                                  round-trip con el decodificador
  │                                                  PROPIO: oculta AD-12 por
  │                                                  construcción. Por eso el agreement
  │                                                  test NO cierra AD-12
  └──AD-11 (redondeo +3/+2 según spec Microsoft) ──VALIDADO POR──> 2 transcripciones
                                                      independientes de la spec
                                                      + mutante que el test rechaza
```

```
Fase 1 ──VALIDATES──> el agreement test tiene capacidad de fallo
         (check-ramp-discriminates rechaza el mutante conocido, exit 1)
         Esa propiedad es lo que hace que "CONFORMA" signifique algo.

Fase 2 ──DEPENDES OF──> RADV funcional en RADV POLARIS12 (RADV sí renderiza;
         se comprobó que vkcube funciona)
         ──> si la ruta de cómputo Vulkan no funcionara, el agreement test no
             podría ejecutarse y no habría evidencia de hardware

PENDIENTE  AD-12 es la única frontera de toda la línea B, y la única cuya respuesta
           pueda obligar a DESHACER una decisión ya tomada y medida.
```

## 6 · Grafo de herramientas: quién produce qué evidencia

```
RESEARCH/working/linux-7.1.3 ──INPUT──┐
RESEARCH/kernelbuild/linux-7.1.3 ────┤
                                       ├──> pm4_count_census.py ──> RE-08
gfx_v8_0.c, gmc_v8_0.c, vi.h ──────────┤        (VALIDATED: mutante -> rc=1)
                                       ├──> pm4dw ───────────────> RE-06, RE-07
                                       │        (VALIDATED; requiere --struct por
                                       │         VARIABLE y --macro N=V)
                                       ├──> gfx8vmgeom ──────────> RE-10, C-005
                                       │        (VALIDATED: 37/0, 12/12 negativos;
                                       │         REQUIERE cwd = su directorio)
                                       └──> semref ──────────────> refs/chain
                                                INVALID: Coccinelle perdida con /tmp
semref ──ENFORCES──> evidence_search.py ──> evita NOT_FOUND falsos
                          SIN negative-test registrado  [NR-09]
validate_rx550_final.py ──> CURRENT-STATE.md §1-§2
                          (VALIDATED, writes_to_system=false)
```

```
pm4dw ──SUPERSEDES PARCIALMENTE──> count_vmflush_dw.py, frame_budget.py
       (los dos últimos son TRACKED y PARTIAL; pm4dw automatiza lo que hicieron a mano)
       NO se borran: 021-frame explica el "por qué" con la lectura manual, y pm4dw
       no puede explicar por qué CE_META reserva chained_ib
```

## 7 · Grafo de documentos: qué manda sobre qué

```
docs/MASTER-RESEARCH-STATUS.md ──PRECEDE──> todo lo demás
  │
  ├──leído POR──> docs/CURRENT-STATE.md      (el estado verificable, sin opinion)
  ├──leído POR──> docs/EVIDENCE-MATRIX.md    (claim → evidencia)
  ├──leído POR──> docs/OPEN-FRONTIERS.md     (lo que falta)
  ├──leído POR──> docs/CONTRADICTIONS.md     (dos versiones de un mismo hecho)
  ├──leído POR──> docs/NEGATIVE-RESULTS.md   (qué está descartado)
  ├──leído POR──> docs/TOOLS-STATUS.md
  ├──leído POR──> docs/IMPLEMENTATION-STATUS.md
  ├──leído POR──> docs/EXPERIMENTS.md, DECISIONS.md, CHANGELOG-RESEARCH.md
  │                FINDINGS-INDEX.md   (los 38 findings, con TRACKED/UNTRACKED)
  │                AGENTS-ADDENDA.md   (addenda verificada, lista para pegar)
  │
  └──SUPERSEDES──> 00-INDICE/MASTER-RESEARCH-STATUS.md  [C-007]
                    NO SE BORRA: contiene el histórico R-4B/D6 de septiembre.
                    Su texto dice "punto único de entrada"; ése sigue siendo un
                    defecto vivo de ese fichero, no resuelto aquí (F7).
```

```
PROYECTO_STATUS.md ──> línea BC3, CONTIENE una contradicción interna reconciliada
                       hoy [C-001]
README.md ──────────> Starkly obsoleto en §Host, marcado HISTÓRICO hoy
COORDINACION.md ───> ley operativa de concurrencia. NO lo modifica este trabajo.
                       CONTIENE un defecto conocido [C-008] cuya corrección propuesta
                       existe (021-write-lock §Corrección) y no está aplicada
AGENTS.md ─────────> método de investigación. Su lista "NO reabrir" (líneas 107-149)
                     es en su mayoría correcta, pero NO menciona la línea A:
                     ni rx550_drv, ni 017-025. Un agente que la lea no sabrá que
                     SDMA es el writer de PTE ni que la geometría está cerrada.
                     -> ACCIÓN (F8): añadir una addenda. NO hecha: AGENTS.md está
                        modificado sin commitear en el árbol (1434 líneas de diff),
                        luego hay una sesión en medio de editarlo
```

## 8 · Aristas de invalidación — "si esto cambia, mira aquello"

Para lo que un agente tiene que revisar cuando llega evidencia nueva:

| Si esto cambia | Revisa también |
|---|---|
| RE-10 (geometría, `block_size`) | C-003, C-005, RE-11, el planificador de page tables, el margen BAR (2x), `023-pte` §5, `024` §§2.3-2.5 |
| RE-02 (`NOT_IMPLEMENTABLE`) | RE-01, RE-13, N1, N2, la seguridad del path de ring |
| RE-04 (PTE es paquete SDMA) | el diseño del driver Stage 1 completo, RE-08, RE-10 |
| RE-08 (convención de encoding) | RE-06, RE-07, `022` §4, N1 |
| RE-03 (sin granularidad) | `flush_type` / `vmhub` en la interfaz del driver propio |
| El veredicto de AD-12 | AD-11 (revertir si trunca), la divergencia contra bcdec, el encoder |
| La observation del boot | RE-10, C-003, C-005, `014-q1` |
| Un parámetro de módulo distinto de `-1` | RE-22 (`vram_full_visible`), N4, toda la cadena de `vm_update_mode` |

## 9 · Nodos con más aristas entrantes = los que más valor tienen y los que más caro sale romper

```
RE-10 (geometría)          ── 8 entrantes. Es el nodo más dependiente del grafo.
RE-02 (no implementable)   ── 6 entrantes, y bloquea en vez de desbloquear.
RE-08 (convención PM4)     ── 5 entrantes. Sostiene el conteo de dwords Y la
                              enumeración de COND_EXEC; un error aquí se propaga a
                              ambos sin que ninguno lo detecte.
RE-04 (PTE vía SDMA)       ── 4 entrantes, y es el primero que se implementaría.
RE-03 (sin granularidad)   ── 3 entrantes. Todo lo que dependa de pedir "sólo L1"
                              está muerto de antemano.
RE-22 (censo de flags PTE) ── 3 entrantes. Cierra el QUÉ ESCRIBE y deja abierto el
                              QUÉ SIGNIFICA, que es la frontera más grande que queda
RE-18 (fence tiene completion) ── 2 entrantes. Y es el contraargumento de RE-02: dos
                              puntos de completion en el ASIC, no uno
```

**El grafo tiene ahora una forma que conviene ver**: el lado izquierdo (qué escribe el
software) está **cerrado y medido** — geometría `RE-10`, productor de PTE `RE-04`,
flags bit a bit `RE-22`,PTBA `RE-19`, frame `RE-16`. El lado derecho (qué hace el
silicio) tiene **tres agujeros** y ninguno se cierra leyendo código:

```
RE-22 flags de PTE  -> N4b   ¿qué significa cada bit?
RE-12 PAGE_TABLE_DEPTH -> N3 ¿qué significa 0 frente a 1?
RE-06/RE-16 dwords    ->  OK, aritmética cerrada. Esta capa sí se terminó
RE-02 sin ack         -> N1/N2 Runtime
```

Es el mismo patrón que la línea BC3, que tiene cerrada la aritmética y abierta la
pregunta del sampler. En los dos casos lo que falta es el silicio, y en los dos casos
no se va a conseguir leyendo más rápido.

## 9 · Cadena del count de PM4: regla cerrada el 2026-10-02

```
RE-30  count de un paquete PM4 = payload MENOS UNO            PROVEN
         ▲
         │ cornerstone: si esto fuera "payload", un driver propio se
         │ comeria un dword del paquete siguiente en cada paquete
         │
    ┌────┴───────────────┬──────────────────┬──────────────────┐
    │                    │                  │                  │
producer           consumidor           hardware           Validación
PACKET3(op,N)      payload = N+1        lee N+1 payload   RE-30: anillo de
el driver escribe  dwords               verificado con el  compute, el test
N+1 siempre                              TEST DEL RING,      del anillo, que
        │                                                     sin el DEADBEEF
        │                                                     no pasa y el
        ▼                                                     anillo no se usa
RE-28 (retirada)   la excepcion era
no habia ninguna   falsa: vm_flush
excepcion          escribe 6, no 5
        │
        ▼
todo lo que use count en PM4: WAIT_REG_MEM, WRITE_DATA, CONTEXT_CONTROL,
INDIRECT_BUFFER, COND_EXEC, COPY_DATA, EVENT_WRITE_EOP, ACQUIRE_MEM,
SET_CONTEXT_REG, SET_SH_REG, SET_UCONFIG_REG, SET_CONFIG_REG,
DISPATCH_DIRECT, PREAMBLE_CNTL, MAP_QUEUES, SET_RESOURCES, CLEAR_STATE
```

**50 de 50 emisiones de `gfx_v8_0.c` reconciled** (`tools/pm4census.py`), con
la confirmación de hardware en `SET_UCONFIG_REG` y el resto por forma. La
regla es de una línea y es lo primero que un driver propio tiene que respetar.

## 10 · Cadena de observación de la page table: el observador existe

```
N-12  el contenido de la PTE, observado          BLOCKED_BY_CREDENTIAL
        ▲
        │ YA NO es "no hay observador". Es "falta la credencial"
        │
   ┌────┴─────────────┬──────────────────┬────────────────────┐
   │                   │                  │                    │
productor           representación     consumidor        lo que falta
RE-30              RE-32              el page walker    un sudo dd de
pd_addr           tabla GART en       de la GPU         64 bytes en el
     │            VRAM offset 0x900000      │             offset 0x900000
     │                   │                  │                    │
     └──► VM_CONTEXT0_PAGE_TABLE_BASE_ADDR  │                    │
          + vmid, valor pd_addr >> 12       │                    │
                  │                         │                    │
                  └────────► RE-20: value = addr & 0x000000FFFFFFF000
                                            │                    │
                            bits 12..39 = 28 bits, ventana 256 MiB
                                    │                    │
                                    └──► N-2b: semántica de cada bit
                                         (alcance ya PROVEN, 15 flags)
                                                  │
                                                  └──► N-14: cuánta RAM
                                                       se puede direccionar
```

**Lo que cambió el 2026-10-02**: `N-12` estaba en `NOT_AVAILABLE` porque solo
se buscó por debugfs. El log de arranque da la dirección de la tabla GART, y
esa dirección cae **dentro de la ventana del BAR**, o sea que es legible por
CPU sin instrumentación nueva.

Y lo que sigue bloqueado es de otra naturaleza: `resource0` es root-only y este
proceso corre como uid 1000. Es una credencial, no una capacidad. Leer el BAR
es NIVEL 2 según el propio AGENTS.md.

**Los tres nodos que dependen de esto** — `N-2b` semántica, `N-14` RAM
direccionable, y el dimensionado del page walker propio — se abren con una sola
lectura de 64 bytes. Es el punto de mayor apalancamiento que queda en el
proyecto.

## 11 · Dependencias rotas que este grafo ahora refleja

```
RE-30  ──►  todo lo que emite PM4 en gfx_v8_0.c
  depende de: ninguna otra regla. Es una hoja del grafo.

N-12  ──►  N-2b, N-14, page walker propio
  depende de: una credencial (root), no de conocimiento

RE-26  ──►  la traducción VA->PA y el invalidate
  EV-26 (VMID -> bit n) es independiente de EV-30 (count). Se cruzaron en dos sitios esta
  sesion, porroutes distintas, y no hay arista real entre ellos: el invalidate lo produce
  gmc_v8_0_emit_flush_gpu_tlb, y ese codigo escribe REGISTERES, no paquetes.
  La unica arista real es el vm_flush, que escribe las dos cosas
```
