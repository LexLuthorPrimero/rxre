# OPEN-FRONTIERS — preguntas abiertas, no tareas

> Una frontera tiene una pregunta técnicamente concreta, evidencia conocida, evidencia
> faltante, y un test que la discrimina. "Investigar más" no es una frontera.
> `NOT_DETERMINED` sin causa nombrada es `UNKNOWN`: no entra aquí.
>
> `LAST_SCAN: 2026-10-02 - revkit/`

## F12 · La PTE de esta GPU, observada

```
PREGUNTA      Para una VA concreta que el hardware está usando, ¿qué entrada de
              page table la traduce y a qué página física apunta?
ESTADO        NOT_DETERMINED, y ahora con la cadena completa hasta el borde
LO QUE SE SABE
  la operación está cerrada hasta el último paso (EV-20):
    addr = vram_base + cursor.start     amdgpu_vm.c:1228
    vram_base = 0                       gmc_v8_0.c:1176
    value = addr & 0x000000FFFFFFF000    amdgpu_gmc.c:173 + gmc_v8_0.c:1134
  y hay 8 VA reales observadas en el anillo, con vmid=7 (EV-21)
LO QUE FALTA
  el contenido de la tabla. Ni qué PTE corresponde a 0x1_0025_8000, ni si
  hay PDE o solo PTE, ni qué flags de acceso lleva
POR QUÉ NO SE PUEDE EN ESTA RONDA
  `amdgpu_vm_info` en 7.1.3 lista BOs y no vuelca entradas; `amdgpu_gart` no
  existe en este driver (NR-2026-10-02-b). Con root tampoco: es
  `NOT_AVAILABLE` por esta vía, no `PROVEN_ABSENT`
QUÉ LO DISCRIMINARÍA
  un observador de la memoria de la GPU. Con eso, la VA 0x1_0025_8000 y su
  PTE se leen en cadena, y se cierra la frontera F2b
VALOR
  alto: es el último eslabón de la traducción, y con él se puede
  implementar el page walker sin suposición
```

## F12b · El `count` de PM4: payload menos uno, y una excepción sin resolver

```
ACTUALIZADO 2026-10-02. CERRADA en su mayor parte por EV-30, con una pregunta
derivada que queda abierta y es más pequeña que la original.

LO QUE SE CIERRA
  el campo `count` de un paquete PM4 cuenta el payload MENOS UNO. Lo demuestra
  el test del anillo, que es el unico sitio donde la pregunta se responde desde
  el hardware y no desde el codigo:

  gfx_v8_0_ring_test_ring (gfx_v8_0.c:838-864) reserva 3 dwords y escribe
  PACKET3(SET_UCONFIG_REG, 1) + 0x40 + 0xDEADBEEF. count declara 1, se
  escriben 2. Los bytes del anillo de compute cuadran al dword: opcode 0x79,
  0xc040 - 0xc000 = 0x40, y 0xDEADBEEF

  si el hardware leyera exactamente 1 payload, el 0xDEADBEEF no se ejecutaria,
  el sondeo de mmSCRATCH_REG0 nunca leeria 0xDEADBEEF, el test daria ETIMEDOUT,
  y amdgpu_ring_test_helper (amdgpu_ring.c:756-768) pondria sched.ready = 0.
  El anillo de compute esta usado: luego el test paso y el hardware consumio 3

  y el test no se puede saltar: amdgpu_ring_test_ring es una macro a
  funcs->test_ring (amdgpu_ring.h:432), sin condiciones

LO QUE SE RETIRA DE ESTA FRONTERA
  que el anillo de GFX no distingue count de count+1. No distinguió: los dos
  modelos dan 11 paquetes y 0 espurias, porque el dword sobrante siempre va
  seguido de una cabecera valida. Era EV-27, ya retirada

LO QUE QUEDA ABIERTO, Y ES MAS PEQUEÑA

PREGUNTA
  ¿es la regla `count = payload - 1` universal, entre opcodes y entre ASICs?
ESTADO
  `CORROBORATED`, no `PROVEN`. Con dos limitaciones que conviene tener separadas
LO QUE YA NO HACE FALTA MIRAR
  la pregunta que se DERIVO de aqui, "si `vm_flush` es la excepcion", ya NO es
  una pregunta. EV-28 queda RETIRADA: `gfx_v8_0_ring_emit_vm_flush` escribe
  SEIS payload con count=5, como los otros dos emisores de WAIT_REG_MEM. Yo
  habia contado cinco por un volcado de codigo numerado a ojo
  `tools/pm4census.py` ya lo tenia medido y da seis en los tres sitios. Ese
  fallo es la novena vez del patron de F11, y aqui la forma es nueva: no fue
  un ambito de busqueda corto, fue leer numeros de linea de un volcado en vez
  de de `grep -n`. Una herramienta ya existia y la contradije a mano
  el discriminante que habia propuesto (un anillo con un vm_flush) hizo falta
  solo para convencerme: la cuenta de seis la resuelve el censo, sin hardware
  y sin captura
LO QUE QUEDA

  NADA sobre la regla, para el fichero de esta GPU.

  Las 7 emisiones que `pm4census` dejaba sin reconciliar (5 `SIN MEDIR` y 2
  `LIMITE`) se han mirado una a una y **las 7 cumplen `payload = count + 1`**.
  El veredicto pasa de 43 de 50 a **50 de 50 emisiones de `gfx_v8_0.c`**

  Las dos causas por las que estaban sin reconciliar, ambas de la herramienta y
  ambas con comportamiento correcto:

    1. su patrón de escritura es `\bamdgpu_ring_write\s*\(\s*ring\b`, que solo
       reconoce escrituras a una variable llamada `ring`. Las emisiones de
       4331, 4345 y 4773 escriben en `kiq_ring`
    2. su patrón de opcode casa con `PACKET3_UNMAP_QUEUES` dentro del nombre de
       la macro `PACKET3_UNMAP_QUEUES_DOORBELL_OFFSET0` y toma un dword de
       payload por una cabecera

  La herramienta reporta `SIN MEDIR` en vez de devolver un numero inventado, que
  es justo lo que hay que pedirle. Falló estrechas y a la vista. Quien sea dueño
  de `tools/pm4census.py` puede arreglar los dos patrones; aqui no se toca

LO QUE SE PUDO DEJAR ASI, Y ES DECIRLO
  la universalidad entre **ASICs**, no dentro de este fichero. `pm4census` tiene
  modo de comparar generaciones y `findings/023` ya lo aplico sobre seis, como
  evidencia de contraste. La distincion que 023 fue a hacer sigue en pie: lo
  que corre en esta GPU es lo que prueba el ASIC de esta GPU

  Y para los otros 24 paquetes de GFX8, la prueba de hardware sigue siendo solo
  uno (`SET_UCONFIG_REG`, EV-30). Para el resto el argumento es de forma: count
  declarado una unidad menor que el payload escrito, en un buffer que el driver
  rellena con el valor. Con 50 de 50 emisiones de acuerdo, ese argumento es
  fuerte; sigue sin ser una medicion del hardware para esos 24
VALOR
  ninguno para construir el driver: la regla esta cerrada para el ASIC de esta
  GPU y es trivial de implementar (`count = payload - 1`)

  ALTO como metodo, y es la segunda vez que paga en esta sesion: las dos
  preguntas de esta frontera se cerraron con una herramienta que ya estaba en el
  arbol (`tools/pm4census.py`), sin hardware, sin captura y sin runtime. La
  primera la cerre contradictedola con una tabla hecha a mano; la segunda,
  siguiendo sus indications de "exige mirarlas"
```

## F13 · Qué son los `0x20` de `protected by` en `amdgpu_sa_info`

```
PREGUNTA      `amdgpu_sa_info` vuelca 137 valores distintos en el campo
              `protected by`. ¿Qué es ese número?
ESTADO        NOT_IN_CORPUS, no NOT_DETERMINED. La diferencia importa: no es
              que no se sepa por análisis, es que el código no está
LO QUE SE SABE
  que es un contador incremental, no una máscara de bits. Se creyó lo
  segundo porque los tres primeros valores (1, 3, 2) parecían una rotación
  de protección. Hay 138 valores, del 1 al 0x8A
POR QUÉ ES NOT_IN_CORPUS
  `amdgpu_sa_bo_dump_debug_info` se LLAMA desde `amdgpu_ib.c:491` y no está
  DEFINIDO en ninguna de las tres raíces del corpus (EV-24). El nodo existe
  en el driver cargado; su implementación no
QUÉ LO CERRARÍA
  el fichero que lo define, o una versión del driver con esa función
VALOR
  medio. No es hardware, pero explica el ciclo de vida de los buffers de IB
  que usa el scheduler
```

## F14 · Cuánta RAM del sistema puede direccionar esta GPU

```
PREGUNTA      Con GART de 256 MiB, ¿cuánta RAM del sistema puede la GPU
              direccionar a la vez, y qué pasa cuando se pasa?
ESTADO        NOT_DETERMINED
LO QUE SE SABE
  GART 256 MiB, con su razón en el propio código (EV-23): todos los motores
  de Polaris12 soportan GPUVM. Y el límite no es la GART, sino que la
  traducción pasa por las page tables, que son de 64 entradas
  (`num_level = 1`, `fragment = 9`, ya cerrado)
LO QUE FALTA
  el tamaño total direccionable, y si hay más de una región
QUÉ LO DISCRIMINARÍA
  el contenido de las PTE, que es F12
CUIDADO
  `vram_base_offset = 0` con un FB en 4 GiB está sin conciliar (EV-21). No
  usar ese 0 para calcular nada hasta entender a qué se refiere
```

---

## F1 · Orden de ejecución real del invalidate respecto al siguiente IB
`PARCIALMENTE CERRADA POR RE-18 EL 2026-10-01 11:38 — sigue abierta en su núcleo`

```
PREGUNTA      Cuando gfx_v8_0_ring_emit_vm_flush() ha escrito
              VM_INVALIDATE_REQUEST y el WAIT_REG_MEM sin predicado, ¿el hardware ha
              YA aplicado la invalidación cuando empieza a ejecutar el IB siguiente?
              ¿O el intervalo de 0x20 paquetes es sólo un delay fijo, sin relación con
              el invalidate?
ESTADO        NOT_DETERMINED
CERRADO       El path de RING no puede observar completion: no hay ack, y el
              WAIT_REG_MEM con FUNCTION=always y mask=0 no espera nada  [RE-01, RE-02]
              La ruta GART sí tiene completion, por sincronía de CPU  [RE-13]
LO QUE NO SE HA RESUELTO  Ni el orden ni el intervalo. Son cosas distintas y "not
              implementable" se ha estado confundiendo con "no investigado"

EVIDENCIA CONOCIDA
  gfx_v8_0.c:6199-6207   WAIT_REG_MEM, payload 6, poll interval 0x20
  gmc_v8_0.c:678,681     2 emit_wreg; el segundo es INVALIDATE_REQUEST = 1 << vmid
  017 §5                 el discriminante ya está redactado por la sesión que cerró el
                         caso: escribir un WAIT_REG_MEM always y un RREG32 de
                         INVALIDATE_REQUEST ENTRE dos IBs, con un VMID cuyo invalidate
                         se retrase artificialmente
EVIDENCIA QUE FALTA
  Una lectura de INVALIDATE_REQUEST observada desde software DESPUÉS de un wait, en un
  ring real, con el invalidate deliberadamente retardado. Nada de eso existe en el
  corpus: es un dato de hardware y el corpus es de software
TEST DISCRIMINANTE
  1. IB_A: escribe VM_CONTEXTn_PTBA, luego VM_INVALIDATE_REQUEST
  2. WAIT_REG_MEM(FUNCTION=always, poll=0x20) sobre INVALIDATE_REQUEST
  3. RREG32(INVALIDATE_REQUEST) -> si ya está a 0, el wait lo sincronizó
  4. Repetir con poll=0x0 y con poll=0xFF: si el resultado cambia con el poll, el
     wait espera algo; si no cambia, es un delay ciego y el ring depende del invariante
DEPENDENCIAS  RE-01, RE-02, RE-03, RE-08
BLOQUEOS      BLOCKED_BY_AUTHORIZATION  (requiere carga del driver propio + MMIO write)
              Y por una segunda vía: la ruta de recuperación independiente está en
              PARTIAL. SSH-RECOVERY-PATH-2026-10-01.md declara 1 de 3 condiciones
CONFOUNDERS   TLB preexistente · NO_INVALIDATION en ATC_VMID{n}_PASID_MAPPING bit 30 ·
              reset_domain sem en down_read_trylock · VMID reuse · power state
RELEVANTE     017, 018, 019, 025, gfx_v8_0.c, amdgpu_gart.c
VALOR         Cierra N1 y N2 de golpe, y es el único dato de ordenamiento que falta
              en toda la línea de ejecución.Sin él, la seguridad del vm-flush del
              driver propio descansa en un invariante no verificado
```

## F2 · AD-12: ¿el sampler del Polaris 12 redondea o trunca la rampa alfa?

```
PREGUNTA      ¿El hardware decodifica la interpolación de los canales alfa de BC3 con
              redondeo +3/+2 (especificación Microsoft D3D9) o con truncamiento?
ESTADO        NOT_DETERMINED  — la ÚNICA frontera abierta de la línea BC3
POR QUÉ ES LA MÁS IMPORTANTE DEL PROYECTO
  Este proyecto entrega un ENCODER. El consumidor del encoder es el hardware. Si el
  sampler trunca, rx550_compress.c emitiría bloques que la RX 550 decodifica distinto
  de como predice rx550_decompress_block().
  El error NO aparecería en un informe: viajaría DENTRO del payload del bloque, de
  forma sistemática, en el 82.9 % de los pares de endpoints. Un round-trip contra el
  decodificador propio lo ocultaría POR CONSTRUCCIÓN — y eso es exactamente el test que
  hoy pasa con 0/4096.
LO YA CERRADO
  AD-11  la interpolación de +3/+2 es correcta  [PROVEN, dos transcripciones
         independientes de la spec + mutante rechazado]
  AD-12  el comportamiento del HARDWARE es otra pregunta. Ver F4-AD-12: "no está
         bloqueada por unbind"; vkcube renderiza en RADV
EVIDENCIA CONOCIDA
  El proyecto entrega el lado del sampler, no del encoder, luego la pregunta es de
  lectura del hardware. En este repo:
    04-IMPLEMENTACION/compressor/test_alpha_ramp_independent.c   las dos
      transcripciones de la referencia
    test_alpha_ramp_mutation.c    el mutante que demuestra que el test discrimina
  CORROBORACIÓN EXTERNA (SECONDARY, no primaria): bcdec v0.985 trunca; la referencia
  pasó a ser la spec de Microsoft porque trunca. Eso es un indicio de que el
  truncamiento es el comportamiento histórico, y por tanto que AD-11 podría ser
  incorrecto para esta GPU. NO es prueba: bcdec no es el hardware de esta placa
EVIDENCIA QUE FALTA
  La lectura del sampler de ESTA GPU. Nada en el corpus o en el repo la contiene
TEST DISCRIMINANTE  (escrito y NO ejecutado)
  Adjuntar una textura DXT5 directamente como color attachment de un FBO y leer con
  glReadPixels. Sin shader, sin quad, sin dibujar. Evita por diseño la ruta de cómputo
  Vulkan.
    Cobertura: 65536 pares de endpoints x 8 índices = 1048576 observaciones
    Autovalidación en 4 puntos, el último de los cuales es que los índices 0 y 1
    decodifiquen exactamente a a0/a1 — que no interpolan, luego prueban el CAMINO, no
    la RAMPA
    DISCRIMINANTE porque los dos resultados posibles dan números distintos y ambos
    preexistentes: redondeo -> +3/+2 exacto; truncamiento -> 0..7 sin redondeo
DEPENDENCIAS  AD-11 (si el hardware trunca, AD-11 se REVIERTE y se reabre la
              divergencia contra bcdec)
BLOQUEOS      ninguno técnico. Es el experimento más preparado del proyecto y el
              único que queda sin hacer en la línea B
CONFOUNDERS   MSAA · sRGB · filtrado de textura · ROP write masking
              masking. Por eso el método es "sin shader, sin dibujar"
RELEVANTE     DECISIONS.md AD-11, AD-12, AD-15, AD-20 · PROYECTO_STATUS.md §AD-12 ·
              compressor/README.md
VALOR         Es la única frontera cuya respuesta pueda obligar a DESHACER una decisión
              ya tomada y medida. Todas las demás aclaran; ésta puede refutar
ACCIÓN        EJECUTAR. No requiere autorización de hardware: es un experimento de
              usuario vía Mesa, como los que ya se ejecutaron el 2026-09-29
```

## F2b · Semántica de hardware de cada bit de PTE

```
ACTUALIZADO 2026-10-02. La parte de ALCANCE estaba cerrada desde antes por
`revkit/pte.py para-gfx8`, una herramienta de este mismo revkit que no se
había ejecutado nunca. Lo que queda es la parte de SEMÁNTICA, que esa
herramienta no puede cerrar y no pretende cerrar

LO QUE YA ESTABA RESUELTO, Y NO SE CONSULTÓ
  `revkit/pte.py para-gfx8` interseca los flags `AMDGPU_PTE_*` definidos con lo
  que GFX8 alcanza, y separa lo que aplica de lo que no:

    con alcance demostrado (15)
      bit 54 AMDGPU_PDE_PTE          amdgpu_vm.h
      bit  4 AMDGPU_PTE_EXECUTABLE   amdgpu_vm.c, amdgpu_vm.h, amdgpu_vm_pt.c
      bit 51 AMDGPU_PTE_PRT          amdgpu_vm.h, gmc_v8_0.c
      bit  5 AMDGPU_PTE_READABLE     amdgpu_ttm.c, amdgpu_vm.c, amdgpu_vm.h
      bit  2 AMDGPU_PTE_SNOOPED      amdgpu_ttm.c, amdgpu_vm.c, amdgpu_vm.h
      bit  1 AMDGPU_PTE_SYSTEM       amdgpu_gart.c, amdgpu_ttm.c, amdgpu_vm.c
      bit  3 AMDGPU_PTE_TMZ          amdgpu_ttm.c, amdgpu_vm.c
      bit  0 AMDGPU_PTE_VALID        amdgpu_ttm.c, amdgpu_vm.c, amdgpu_vm_pt.c
      bit  6 AMDGPU_PTE_WRITEABLE    amdgpu_ttm.c, amdgpu_vm.c, amdgpu_vm.h
      (+ 5 mas con el mismo criterio)

    definidos pero SIN consumidor alcanzable (4)
      bit 59 AMDGPU_PTE_BUS_ATOMICS  solo gmc_v12_1.c
      bit 58 AMDGPU_PTE_DCC          solo gmc_v12_0.c
      bit 55 AMDGPU_PTE_LOG          solo gmc_v10_0.c, gmc_v11_0.c
      bit 58 AMDGPU_PTE_NOALLOC      solo gmc_v10_0.c, gmc_v11_0.c

  los cuatro últimos son `NOT_APPLICABLE` para GFX8, no `PROVEN_ABSENT`: el
  corpus define los flags de todas las generaciones

  el criterio de la herramienta es el que hay que usar, y está escrito en su
  cabecera: "Un flag que un fichero DEFINE no significa que GFX8 lo USE. Solo
  cuenta si lo consume un fichero alcanzable desde gfx_v8_0"

LO QUE SIGUE ABIERTO, Y ES OTRA COSA
  esto responde QUÉ bits existen para GFX8. No responde QUÉ hace el hardware con
  cada uno. `VALID`, `WRITEABLE`, `READABLE`, `EXECUTABLE` y `SYSTEM` tienen
  nombre y productor, y su efecto en la page walker sigue sin observar
ESTADO
  alcance: `PROVEN` (15 flags)
  semantica: `NOT_OBSERVED`. No hay forma de observar una PTE real por debugfs
  en 7.1.3: `amdgpu_vm_info` lista BOs y no vuelca entradas (NR-2026-10-02-b)
QUÉ LO CERRARÍA
  un observador de la memoria de la GPU, igual que para F12. Con el, una PTE
  real se decodifica con `pte.py dump` y el alcance ya cerrado da la semántica

DATO NUEVO DE ESTA RONDA, Y QUE AFECTA A ESTA FRONTERA
  `pte.py dump` tenía el layout de campos HARDCODEADO, sin filtro de ASIC:
  decía `bit 47..12 ADDR_BA`, 36 bits. Para GFX8 el campo acaba en el bit 39
  (`gmc_v8_0.c:1134`, `pte_addr_mask = 0x000000FFFFFFF000`), o sea 28 bits y una
  ventana de 256 MiB. Diferencia de 8 bits
  corregir eso cambia el tamaño de la ventana que cubre un nivel de page table,
  que es la magnitud con la que hay que dimensionar un page walker propio. Ver
  NR-2026-10-02-h
VALOR
  medio para el driver propio: el juego de flags ya está y es pequeño. Alto
  como aviso, porque la herramienta que lo mide tenía el layout equivocado y eso
  es justo lo que hace un page walker mal dimensionado
```

## F3 · Significado de `PAGE_TABLE_DEPTH = 0` frente a `= 1`

```
PREGUNTA      El mismo campo de 2 bits recibe 0 para el contexto 0 (GART) y 1 para los
              contextos 1-15 (userspace). ¿Qué significa cada valor? En particular,
              ¿"0" significa "GART plano, sin page table" y "1" "VM con page table"?
ESTADO        NOT_DETERMINED  con causa nombrada
LO QUE ES PROVEN  Que son valores distintos en el mismo campo, escritos por el mismo
              driver en la misma función (gmc_v8_0.c:895 y :925), y que
              PAGE_TABLE_BLOCK_SIZE no se escribe para el contexto 0
LO QUE ES HYPOTHESIS  Que el 0 sea "plano" y el 1 "con page table": es coherente con el
              contexto de cada llamada, y eso es todo
EVIDENCIA QUE FALTA
  Enumeración del campo, comentario, o documentación. NO EXISTE en gmc_8_2_sh_mask.h
  (MASK 0x6, SHIFT 1, sin nota), ni en ninguna otra cabecera, ni en el árbol.
  La búsqueda fue completa: por eso es NOT_DETERMINED y no NOT_FOUND-d accidentally
TEST DISCRIMINANTE
  No hay discriminante estático. La spec PM4 de GFX8 es la vía; sin ella, un
  experimento runtime que programe profundidad 0 con una tabla válida detrás y vea si
  la traducción ocurre. Es RUNTIME y es destructivo
 BLOQUEOS      **RECLASIFICADO 2026-10-01.** Ya no es "falta la especificación, no la
              hemos encontrado". La fuente existe: *Reference Guide — Graphics Core Next
              Architecture, Generation 3*, rev. 1.0 (2015-03), 637 páginas, PRIMARY, y se
              CONTÓ: cero apariciones de PACKET3, PKT3, RELEASE_MEM, COND_EXEC,
              VM_INVALIDATE, INT_SEL, WRITE_AT, GRBM, mmCP. AMD nunca publicó el framing
              PM4 para GCN3
              -> `BLOCKED_BY_NEGATIVE_RESULT`. La evidencia no está en ningún documento:
              hay que MEDIRLA. Ver RE-29
EVIDENCIA QUE FALTA  enumeración o comentario del campo. No existe en
              gmc_8_2_sh_mask.h ni en ninguna otra cabecera aplicable a GFX8
VALOR         Es el punto exacto donde el modelo plano del kernel y el de
              userspace divergen en el mismo ASIC. Localizada y sin explicar
```

## F3b · La línea H empieza: el SMU es firmware, no registros

```
ESTADO        NOT_DETERMINED  ·  **Y EL ENCUADRE CAMBIÓ ENTERO el 2026-10-01**
REVISADO POR  046, que se autoclasifica CORRECTION sobre 040, 041, 042, 043, 044 y 045

PREGUNTA      Si el driver no escribe los registros de reloj y es el firmware SMU quien
              los aplica, ¿qué es exactamente el contrato entre el host y ese firmware?
              ¿Qué mensajes existen, con qué formato, en qué SRAM, y qué respuesta da?
              SE MANTIENE, pero sobre la ruta correcta
LO QUE HAY, Y CORREGIDO
  040  el Concepto del canal de mensajes sigue VIVO, reubicado en la función real
         smu7_send_msg_to_smc_offset / smum_send_msg_to_smc_with_parameter
         (polaris10_smumgr.c:230, :102)   escritura en 0x94, poll a 0x95
  041  la curva A-T y la banda de histéresis  NO EXISTE en la ruta activa
  042  el formato de wire A-T                      NO EXISTE
  043  PLL, bsp, r600_calculate_u_and_p            NO EXISTE
  044  xclk como divisor de PLL                     NO EXISTE
  045  la "cadena completa del reloj"                CADENA EQUIVOCADA
LA RUTA REAL, verificada
  legacy-dpm/Makefile:28   si_dpm.o si_smc.o SOLO bajo CONFIG_DRM_AMDGPU_SI
  Kconfig:42-51            DRM_AMDGPU_SI = "SI (Southern Islands) are FIRST generation
                           GCN". Polaris12 es Volcanic Islands. Y DRM_AMDGPU_VI NO EXISTE
  -> SI_DPM_COMPILED_FOR_POLARIS12 = PROVEN_ABSENT, y no es un negativo por búsqueda:
     es el gate de compilación explícito
  hwmgr.c:122              smu7_init_function_pointers(hwmgr)
  hwmgr.c:154-158          case POLARIS11/10/12: smumgr_funcs = &polaris10_smu_funcs
  smu7_hwmgr.c             calculate_at 0 · calculate_u_and_p 0 · bsp 0
                           ClockVoltageDependency 0 · xclk 1 (para TIMING DE DISPLAY)
  polaris10_smumgr.c:664/691/716   populate_smc_{mvdd,vddc,vddci}_table
  el modelo real son TABLAS DE VOLTAJE POR DOMINIO, no curvas de histéresis
LO QUE ESTA ABIERTO
  · el resto de 040 (sólo se leyó su §CUDA) y de 041
  · el firmware en sí. Es firmware, no fuente. Vive en el blob de firmware,
    y el blob no está en el árbol del repo: el de 008-firmware-blob.md
POR QUÉ LA ABRO COMO FRONTERA Y NO COMO NOTA
  `AGENTS.md` §"H · PERFORMANCE CONTROL" decía: "investigar únicamente cuando las
  dependencias del core estén suficientemente cerradas". Geometría cerrada, productor de
  PTE cerrado, censo de flags cerrado, fence con completion, frame medido. La condición
  se cumple, y 040 es la prueba
  Y cambia la naturaleza del trabajo: "cambiar un reloj" no es escribir un registro. Es
  construir un mensaje, serializarlo con el protocolo del SMC, y escribirlo en la SRAM
  correcta. El reloj no es un registro: es un mensaje, y el destinatario es firmware
LO QUE NO SE SABE AÚN
  el nivel de confianza. 040 y 041 declaran `WORK_CLASS=READ_ONLY/EVIDENCE`,
  `RUNTIME=NOT_RUN`, `GPU INTACTA`. Se ha leído el §CUDA de 040 y la cabecera de 041
TEST DISCRIMINANTE  por_STATIC: enumerar los mensajes del host al SMU **por la ruta
  activa** —smum_send_msg_to_smc_with_parameter y las tablas de voltaje— y fechar cada
  uno con el fuente. Es la técnica que funcionó en las líneas A y B, aplicada al fichero
  correcto
LA REGLA QUE FALTÓ, y que 046 escribe para este caso
  COMPILE_GATE_BEFORE_TRACE_GATE
    verificar en el Makefile y el Kconfig que el .c que se va a trazar SE COMPILA para el
    ASIC objetivo, ANTES de gastar N hallazgos en él
    Trazar un fichero correcto, con toda la evidencia correcta, sobre un fichero que no
    entra en el build produce documentos internamente consistentes y operacionalmente
    inútiles. Eso es exactamente lo que pasó con 040-045: cinco hallazgos, todos bien
    fundamentados, sobre código muerto para esta GPU
BLOQUEOS      ninguno para la parte estática, pero el trabajo DEBE empezar por el gate
RELEVANTE     040, 041, y el blob de firmware de 008-firmware-blob.md
VALOR         MEDIO ahora. ALTO después: es la línea H entera, y H es la última del
  objetivo de investigación
```

## F3c · El payload de los paquetes PM4: hay que medirlo, no leerlo

```
PREGUNTA      Para cada paquete PACKET3 cuyo framing ya está cerrado pero cuyo PAYLOAD no
              está documentado en ninguna parte -- `COND_EXEC`, `RELEASE_MEM`,
              `VM_INVALIDATE_RESPONSE`, `INT_SEL=2` -- ¿qué hace el hardware con sus
              campos?
ESTADO        NOT_DETERMINED, y con la causa ACABADA DE CAMBIAR
LO QUE CAMBIÓ  2026-10-01. Estas preguntas estaban `BLOCKED_BY_CORPUS` con la frase
              "falta la especificación PM4 de GFX8". La fuente existe, se ha medido, y no
              contiene PM4: AMD nunca publicó el framing para GCN3. RE-29
              -> la categoría de bloqueo pasa a BLOCKED_BY_NEGATIVE_RESULT
LO QUE SÍ ESTÁ CERRADO, y por tanto no hay que buscar
  el framing completo. La fórmula es  F = datos − 1,  paquete = F + 2 dwords,
  PROVEN_DERIVED contra tres casos del corpus (RE-30). Los 74 opcodes PACKET3 de GFX8,
  con su rango. Las cabeceras TYPE0/2/3/4/7. El NOP unitario en 0x3FFF
LO QUE SIGUE ABIERTO, con nombre
  · los campos de `COND_EXEC` -- el opcode 0x22, cero bitfields, cero comentario, cero
    documentación en todo el árbol. Es el más grande de los cuatro
  · el dword extra que `RELEASE_MEM` tiene en GFX9 y no en GFX8
  · `VM_INVALIDATE_RESPONSE`, que existe en gmc_8_1_d.h a 0x51f, y `INT_SEL = 2`
TEST DISCRIMINANTE
  los cuatro necesitan runtime. Para COND_EXEC el experimento ya está diseñado en
  `022 §5`: reproducir el parche dword a dword y decidir entre las dos lecturas de
  `num_skip`. Es la misma carrera que F1, y puede ir en la MISMA: quien escriba un disco
  puede medir el invalidate y el COND_EXEC en unasubmission
LO QUE ESTO CAMBIA EN LA PLANIFICACIÓN
  Estas cuatro dejan de ser "buscar el documento" y pasan a ser "diseñar la medición".
  Es una frontera de diseño de experimento, no de búsqueda documental. Y se puede
  agrupar con F1: son el mismo bloqueo doble (autorización + recovery) y el mismo
  hardware
BLOQUEOS      BLOCKED_BY_AUTHORIZATION (falta la ruta de recuperación demostrada)
RELEVANTE     RE-29, RE-30, RE-31, 022, 023, 029, 033-pm4-spec
VALOR         ALTO. Son las cuatro preguntas que la línea A no puede responder sola, y
              ahora está demostrado que no hay atajo documental
```

## F3d · ~~El emisor de PTE del driver propio escribe `count - 1` y este ASIC espera `count`~~ — **CORRECTED 2026-10-02**

```
PREGUNTA      Nada que preguntar: ya se sabe. La pregunta es si alguien lo arregla, y
              mientras tanto: ¿qué otro error de la misma clase hay ya compilado?
ESTADO        ~~**CONFIRMADO**~~  →  **CORRECTED 2026-10-02**.  El defecto EXISTIÓ y
              ya no existe.  Ver abajo la medición que lo cierra.  Se conserva el
              hallazgo entero porque la regla del proyecto es que la historia
              científica no se borra: se marca con fecha
LA MEDICIÓN QUE LO CIERRA, y es un control negativo character a character
  `revkit/PTEPDE-GFX8.md` dejaba escrita una pregunta que nadie había respondido:
      «No sé si `036` en `rx550_pm4.c` replica esta secuencia. Eso se comprueba
        leyendo ese fichero, no el corpus.»
  Es exactamente el discriminante que esta frontera pedía.  Leído:
      rx550_pm4.c:280   void rx550_sdma_vm_set_pte_pde(...)
      rx550_pm4.c:298   ib->buf[ib->length_dw++] = count;
  NO hay ningún `count - 1` en el código.  Las diez apariciones de esa cadena en
  `07-DRIVER/` están en COMENTARIOS y TESTS que documentan el error:
      rx550_pm4.c:239, 248, 257   el comentario que explica por qué se corrigió
      test_pm4.c:327-397          los tests que lo afirman
      rx550pm4_emit.c:10          la nota de la herramienta de pruebas
  y `test_pm4.c:375` dice literalmente: «findings/034 said this field was count-1.
  It is not, on this ASIC»
  POR DÓNDE ESTÁ MAL Y POR QUÉ ESTABA MAL, que es la parte transferible
      sdma_v3_0.c:986-996    escribe `count`        <- ESTE ASIC LO EJECUTA
      sdma_v4_0.c:1649-1658  escribe `count - 1`    <- no lo ejecuta
  dos oscillators de la MISMA cadena de código que el propio driver documenta, y el
  proyecto los cruzó dos veces en direcciones opuestas
ORIGEN        036 implementó 035, que corrigió a 023 por leer `sdma_v3_0.c` en vez de
              `sdma_v4_0.c`. El ASIC es el contrario de lo que 035 afirmó
EL HECHO, en tres líneas
  vi.c:2113                CHIP_POLARIS12 -> sdma_v3_1_ip_block
  sdma_v3_0.c:1699         .funcs = &sdma_v3_0_ip_funcs      (alias, sin fichero propio)
  sdma_v3_0.c:996          último dword = count
  host, hoy                "detected ip block number 4 <sdma_v3_1_0> (sdma_v3_0)"
LO QUE HACE MAL
  rx550_pm4.c:277          ib->buf[ib->length_dw++] = count - 1;
  rx550_pm4.h:195          #define RX550_SDMA_PTEPDE_DW 10  /* sdma_v4_0.c:1649-1658 */
CONSECUENCIA  un PTE por encima del final del rango. Corrupción silenciosa de memoria
POR QUÉ 036 NO LO ATRAPÓ, que es la parte transferible
  036 declara 5 mutaciones, todas detectadas. Ninguna puede ser esta: la suite lee
  RX550_SDMA_PTEPDE_DW del MISMO header que el .c. Es coherencia, no validación
  Un control negativo contra el emisor del driver de REFERENCIA, carácter a carácter sobre
  los dos últimos dwords, lo habría atrapado. Un control contra la propia constante no
  puede: sólo confirma que el .c usa el .h
LO QUE ESTA FRONTERA PIDE, y es lo más caro de aquí
  no una corrección: un PASADO DE CONTROL NEGATIVO sobre todo el driver propio contra el
  corpus. Cada constante de rx550_pm4.h debería citar su fichero y su línea del driver de
  referencia, y un script debería comparar. Es lo que este repo ha pagado cuatro veces
  en la línea A y nunca ha automatizado en la implementación

LO QUE DE ESA Petición YA ESTÁ HECHO, y acota esta frontera
  las constantes YA citaban su línea, y `tools/constmap.py` las compara.  Ejecutado:
      43 constantes · con testigo 32 · sin testigo 11
      AGREE 15 · AGREE_DISCRIMINATING 8 · AGREE_COMMENT 4
      WITNESS_USAGE 3 · NOT_COMPARABLE 2 · UNCITED 11
      DISAGREE 0
  los 32 con testigo quedan cuadrados: ninguna constante contradice a su testigo.  Ver
  `TL-41`, `R-26`, `RE-51`
  CONSECUENCIA PARA ESTA FRONTERA:  el defecto de `rx550_pm4.c:277` NO es un error de
  constantes.  Es un error SIMBÓLICO en el `.c`: el `.h` está bien y el `.c` llama a la
  cosa equivocada.  Eso parte F3d en dos:
      cerrada    la capa de constantes.  Medida, sin contradicciones
      abierta    el `.c`: qué función debe emitir, y con qué argumento
  Y deja una observación que explica por qué 036 no podía atraparlo: el error es de
  SÍMBOLO, y una comparación de valores no lo ve.  El control negativo que esta
  frontera pedía es necesario y no suficiente
LO QUE SIGUE PIDIENDO ESTA FRONTERA, y es distinto de lo que pedía
  1 · el control negativo sobre el `.c`, no sobre el `.h`.  Byte a byte contra el
     driver de referencia sobre los últimos dwords, como ya dice más arriba
  2 · un control de SÍMBOLOS: qué función llama el `.c` y cuál debería.  `constmap.py`
     mide valores y no puede ver esto, y esta frontera ya no puede cerrarse con una
     herramienta de valores
  3 · 11 constantes sin testigo, 2 con expresión, 3 cuyo testigo no lleva el valor.
     Las 2 con expresión se resuelven con `gcc -E`, que es la respuesta correcta y no
     una expresión regular

Y POR QUÉ NO SE PUEDE PEDIR TAL CUAL, que es la parte que nadie ha dicho
  HAY DOS HERRAMIENTAS NUEVAS QUE PARECEN CUBRIRLO, Y NINGUNA DE LAS DOS LLEGA
  `tools/asic_resolver.py`  (053, self-test OK, rc=0, medido por mí a las 13:2x)
      resuelve EXACTAMENTE la primera mitad: ¿este .c entra en el binario para mi ASIC?
      Veredictos COMPILED_UNGATED / GATED_UNDECLARED / COMPILED_GATED_ON /
      NOT_COMPILED_GATED_OFF / NOT_REFERENCED
      y fija la regla COMPILE_GATE_BEFORE_TRACE_GATE como COMANDO, no como consejo
      MEDIDO: `grep -c ip_block tools/asic_resolver.py` -> **0**
      No conoce el concepto de bloque de IP. No puede resolver C-011
  `tools/rx550pm4val.c`  (038)
      valida ESTRUCTURA de un flujo de comandos sin acceso al corpus
      y DECLARA su salida: acepta `count` donde espera `count-1`
      Y explica por qué no puede alcanzar PTEPDE: para sDMA la longitud es implícita en el
      OPCODE, no en un campo count. Es una limitación estructural, no un descuido
  LO QUE FALTA ES UN TERCER GATE, mecánicamente distinto de los dos anteriores:
      RESOLVE_IP_BLOCK_DISPATCH_GATE
      ¿qué fichero de implementación ejecuta ESTE chip, siguiendo el puntero .funcs?
      Pregunta de DOS SALTOS y con indirección por un const struct:
          vi.c:2107            case CHIP_POLARIS12: sdma_v3_1_ip_block
          sdma_v3_0.c:1693      sdma_v3_1_ip_block { .funcs = &sdma_v3_0_ip_funcs }
          sdma_v3_0.c:1112      ... &sdma_v3_0_vm_pte_funcs  -> .set_pte_pde
      Los dos saltos sonCOSA DISTINTA de un `chip_id ==` dentro de un fichero, que es lo
      que `--branches` sí resuelve
  LA PRUEBA DE QUE EL GATE FALTA, y es una sola línea
      grep -c ip_block tools/asic_resolver.py  ->  0
      grep -c ip_block tools/rx550pm4val.c     ->  hay uno, pero como OPCODE, no como
                                                  mecanismo de despacho
  Si el gate existiera, C-011 se habría cerrado ANTES de que 036 escribiera el código.
  Eso es la medida del valor de un gate: no lo que evita, sino lo que llega a evitar

  ACTUALIZACIÓN 2026-10-01, y ESTA FRONTERA SE CERRÓ POR LA PARTE DEL GATE
  `tools/ipsolve.py` (TL-11) ya resuelve el gate, y su `--expect` ES la puerta de CI:
      ipsolve.py --kernel <raiz> --chip CHIP_POLARIS12 \
                 --block sdma_v3_1_ip_block --expect sdma_v3_0.c
      rc=0 si acierta · rc=4 si no · rc=3 si no resuelve
  Y hay algo más valioso que el gate: `--bootlog` cruza los nueve bloques que el
  kernel declaró al arrancar contra lo que el corpus dice que implementa cada uno.
  9 de 9, sin una sola expectativa escrita a mano
  LO QUE QUEDA ABIERTO DE ESTA FRONTERA, y es distinto de lo que estaba
  · sigue sin arreglar `rx550_pm4.c:277`. Eso NO lo puede hacer esta documentación: es
    implementación viva de otra sesión
  · y lo que `ipsolve` NO cubre: NO comprueba que el código resuelto sea correcto. Dice
    cuál elige el despacho; no lo califica. El error de 036 era un VALOR, no un
    despacho equivocado: el despacho ya era el correcto, el dword estaba mal. Un gate
    de despacho no habría detectado eso
  · así que el hueco REAL que queda es un cuarto gate, y es el más difícil de los
    cuatro:
        DRIVER_CONSTANT_VS_REFERENCE_DIFF
        comparar cada constante de rx550_pm4.h contra la del driver de REFERENCIA, y
        además exigir que el fichero que se cita exista y tenga la línea citada
    `038` construyó algo de esa forma (rx550pm4val.c) y declaró su propio límite: valida
    ESTRUCTURA, y acepta `count` donde espera `count-1`. Para sDMA la longitud es
    implícita en el OPCODE, así que una regla de PACKET3 no alcanza a PTEPDE
    Éste sí lo alcanzaría, porque compara contra el fichero del corpus y no contra una
    constante propia
BLOQUEOS      implementación viva de otra sesión. COORDINACION.md:184
VALOR         ALTO. Es el único punto de este árbol donde un número documentado MAL está
              en instrucción de máquina compilable, y donde la suite verde no dice nada
ESTADO 2026-10-01, PARCIALMENTE CERRADO, y conviene separar las dos mitades
  CERRADO: el GATE.  `ipsolve --expect` convierte la comprobación en una línea de CI, y
    `toolreg` la ejecuta como parte del registro
  ABIERTO: el error en sí.  `rx550_pm4.c:277` sigue escribiendo `count - 1`
  Y AHORA, un segundo hueco de la misma clase, medido en RE-43
    `msg_census` dice 503 mensajes SMC donde la respuesta es 14.  La diferencia entre los
    dos casos es que aquél está en código y éste en un titular, pero el modo de fallo es
    el mismo: un número plausible, produced por una herramienta con self-test verde, que
    nadie verificó porque el self-test pasa
  LA REGLA QUE DE LOS DOS, y es lo que hay que incorporar al proyecto
    un self-test que verifica el PARSER no verifica la AFIRMACIÓN
    `msg_census` comprueba que reproduce vectores conocidos; no comprueba que el censo esté
    acotado a mi ASIC, que es la propiedad que falló
    `rx550pm4val` valida estructura; el error era de valor
    Y una herramienta que escribe un titular debería publicar el titular FILTRADO junto
    al crudo, no sólo el crudo.  El dato correcto estaba DENTRO de su propia salida: el
    veredicto VIVA por uso existe, y no se aplicaba al número que se lee
```

## F11 · Un número plausible de una herramienta con self-test verde

```
ACTUALIZADO 2026-10-02. Esta frontera se materialize SEIS veces en una sesion, y
las seis por el mismo mecanismo: un numero que salio bien, de una herramienta
con todos sus controles en verde, y que era falso por un factor, por un
supuesto o por su ambito. La leccion ya no es hipotetica

LOS CINCO CASOS, con su numero real
  1. `atomrom` leia `usMemorySize` en +26 en vez de +20: `24832 MB` en lugar de
     `2048`. Se vio al contrastar con el kernel, no al mirar el numero
  2. La unidad de los clocks del VBIOS: `(/10)/1000` daba `2.1 MHz` para el
     reloj de motor, y luego `(/100)/1000` daba `0.2 MHz`. Los dos con
     decimales, los dos con aspecto de frecuencia
  3. `pm4dec` leia un dword tipo 0 como cabecera `PKT0` con `count=43` y
     sacaba `42 escrituras de registro` con direcciones como `0x0000`
  4. `ibpools` reconocia 687 de 689 lineas y no decia nada de las 2 que no:
     el pool seguia con 654 entradas, los numeros grandes seguian ciertos, y
     solo faltaba el IB en uso
  5. `huerfanos` con una raiz inexistente imprimia `NINGUNO: todos los
     simbolos tienen definicion`. Un corpus no recorrido se leia como un
     corpus completo
  6. `integro.py` desde `revkit/` imprimia `0 ficheros de texto sin
     seguimiento`. Cierto, y sin significado: su `--raiz` por defecto es
     relativo al CWD, asi que escaneaba 48 ficheros de `revkit`, no los 272
     del proyecto. Se veio porque en el mismo momento `git` decia 297

LO QUE LOS SEIS TIENEN EN COMUN
  un self-test verde NO es una garantia. En los seis casos la herramienta
  pasaba todos sus controles y estaba equivocada. Lo que los distingue es
  que en cinco habia un dato EXTERNO con el que contrastar, y ese contraste
  no estaba en el self-test

LO QUE EL CASO 6 ENSENA Y LOS OTROS CINCO NO
  los cinco anteriores fueron errores de calculo: un offset, una unidad, una
  regex, una unidad mal, un arbol mal. Este es distinto: el numero era
  correcto y el AMBITO era el equivocado
  un 0 es el resultado mas peligroso que puede dar una herramienta, porque
  se lee como "todo bien" y no dispara ninguna pregunta. Un numero mal
  grande se nota; un 0 no
  la regla que sale de ahi: un 0 tiene que poder distinguirse de "no se ha
  recorrido nada", y una herramienta que recorta directorios tiene que
  IMPRIMIR cuantos ha saltado, no solo cuantos ha recorrido. `integro.py` ya
  lo imprimia ("directorios saltados: .git, RESEARCH, ...") y bastaba mirar

EL CAMBIO DE FUENTE, POR CASO
  1. contraste con `amdgpu_vram_mm` (el kernel dice 2048 MiB)
  2. contraste con `amdgpu_pm_info` (SCLK 214, MCLK 300)
  3. contraste con el codigo: `PKT0` no aparece en el driver
  4. el rango `[lo,hi)` tiene que medir lo que dice `size`
  5. distinguir `0 ficheros leidos` de `0 huecos`
  6. distinguir `0 sin seguimiento en revkit/` de `0 sin seguimiento en el
     proyecto`, y para eso hay que mirar el ambito, no el resultado

LA REGLA QUE SE ADOPTA
  una herramienta que afirma un numero tiene que poder contrastarlo contra
  algo que no sea ella misma, y el contraste va DENTRO, con codigo de
  salida propio. Un self-test que solo comprueba que el programa no
  revienta no controla nada: controla que no haya excepción, no que el
  numero sea cierto

PREGUNTA      ¿De cuántas herramientas de este árbol se ha leído alguna vez la SALIDA, y
              no su cabecera?
ESTADO        NOT_DETERMINED, y con la primera medición ya hecha
LO QUE SE MEDIDO
  44 herramientas fuente en dos directorios
  5 NO LAS CITA NINGÚN HALLAZGO ni documento: citegen, contradict, msg_census,
  toolcheck, toolreg
  para un árbol documental eso significa que su salida no consta.  Y hay dos casos
  distintos detrás, indistinguibles desde el árbol:
    · la herramienta no se usó
    · se usó y el resultado no se escribió en ninguna parte
  El segundo caso es el que cuesta: evidencia producida y descartada
LO QUE YA COBRÓ UNA VEZ, y está documentado antes de esta tarde
  la cabecera de toolcheck.py describe el incidente de msg_census: «devolvió durante una
  tanda 503 números de mensaje, la mayoría de la generación equivocada, sin avisar.  El
  número era plausible; sólo se detectó porque alguien comprobó a mano qué cabecera se
  estaba usando»
  Ese 503 es el mismo 503.  Sigue vivo.  RE-43
LO QUE SE NECESITA, y es barato
  para cada herramienta con titular numérico: publicar el titular CRUDO y el FILTRADO, y
  que el filtrado sea el que se lee por defecto
  y una comprobación de que el self-test falla cuando la propiedad que importa se rompe.
  No hace falta más: `msg_census` habría detectado que su número cambia si se le acotase
  al ASIC activo
TEST DISCRIMINANTE  para cada titular: reproducirlo a mano y comparar.  Es lo que se hizo
  con msg_census, y de 503 se pasó a 14 en cuatro comandos
BLOQUEOS      ninguno.  Es trabajo de documentación y de herramientas, no de hardware
VALOR         ALTO, y sube con el número de herramientas: hoy es un titular de una
              herramienta; con 44 herramientas es una probabilidad
Y LO QUE NO ES
  no es una crítica a quienes construyeron msg_census.  Construyeron una herramienta útil
  con un titular malo, y su propia salida contiene el dato bueno.  Lo que falla es que no
  hay nadie obligado a mirar el dato bueno, y un self-test que verifica el parser no obliga a nada
```

## F4 · Cierre de Stage 1 del driver propio

```
PREGUNTA      ¿Se retira rx550.ko (char device) del Makefile, o se mantiene como
              biblioteca de código más la suite de pruebas que depende de él?
ESTADO        DEFERRED — decisión de diseño, no de investigación
LO QUE YA ESTÁ HECHO
  rx550_drv.ko existe, compila, y check-drivers verifica por nm que SÍ es driver PCI
    (presencia de __pci_register_driver, pci_enable_device, pci_request_regions,
     y el símbolo d rx550_pci_driver)
  y que rx550.ko NO lo es (0 símbolos pci) — con control negativo explícito
  y que la etapa 1 NO mapea MMIO — también con control negativo
  La propiedad que lo hace creíble: cada comprobación falla si el símbolo ENCONTRADO.
  Sin control contrario, "no encontré X" y "no hay X" son la misma frase
LO QUE FALTA
  Una decisión. El propio Makefile la documenta ("ya no es el camino principal") pero
  no la ejecuta. El argumento de mantenerlo (que rx550_pm4.c tiene una suite que
  depende de él) es real y está escrito
EVIDENCIA QUE FALTA  ninguna. Es una decisión
TEST DISCRIMINANTE  no aplica
BLOQUEOS      ninguno
RELEVANTE     07-DRIVER/kernel/Makefile, STAGE1-SUBSYSTEMS.md, kernel/README.md,
              04-IMPLEMENTACION/rx550-driver/
VALOR         Desbloquea Stage 2 sin tocar hardware. Es la acción con mejor relación
              esfuerzo/valor de la lista, y es la que ninguno de los dos tracks está
              tocando
```

## F5 · Marcas de precedencia en ficheros de otras sesiones

```
PREGUNTA      ¿Dónde van las notas de enmienda que corresponden a sesiones ajenas?
ESTADO        OPEN — y la respuesta es "en un registro central, no en el fichero ajeno"
LO QUE YA SE HIZO
  Las 4 limitaciones contradictorias de PROYECTO_STATUS.md se marcaron ahí mismo, con
  el commit y la hora que las deja obsoletas, conservando el texto literal  [C-001]
LO QUE NO SE HIZO, Y POR QUÉ
  29⁄9⁄26.md          lleva una afirmación REFUTADA (C-002) sin marca. COORDINACION.md:184
                      es "informa, no arregles": no es mío
  DRIVER-MISSION-STATE.md  dice "plano por necesidad", mitad refutada (C-006). Sin marca
  00-INDICE/MASTER-RESEARCH-STATUS.md  se autodescribe "punto único de entrada" y es
                      parcial (C-007)
  AGENTS.md         su lista "NO reabrir" es correcta pero no menciona la línea A (F8)
TEST DISCRIMINANTE  no aplica
BLOQUEOS      ninguno. Es trabajo de una línea cada uno
RELEVANTE     COORDINACION.md:184, CONTRADICTIONS.md
VALOR         Cada nota es de 2-3 líneas y evita que un agente se lleve un error.
              El coste de hacerlo es casi nulo; el de no hacerlo es el que ya se ha
              pagado dos veces en este repo
```

## F6 · Reejecutar el agreement test BC3 y versionar su log

```
PREGUNTA      ¿El agreement test GPU == CPU sigue pasando hoy, con este árbol?
ESTADO        NOT_RECHECKED  — no REFUTED
LO QUE SE AFIRMA
  Fase 2 COMPLETE: 0 de 64 bloques, 0 de 4096 bytes, 3 corridas (commit 7ed1eca,
  2026-09-29 01:17)
LO QUE RESPALDA ESA AFIRMACIÓN
  El texto del commit. Eso es testimony, no artefacto
  Y 04-IMPLEMENTACION/work/*.decompress.log  con "0 de 16384 bytes discrepantes" en 3
  imágenes — PERO .gitignore:78 ignora 04-IMPLEMENTACION/work/ en bloque. La mejor
  evidencia persistente del proyecto está fuera de git
  Y la cifra "[ OK ] 4005 de 4096 bytes no nulos" NO aparece en ningún log persistido
EVIDENCIA QUE FALTA
  El log del agreement test de 64 bloques, versionado
TEST DISCRIMINANTE  no es un discriminante: es una re-verificación. Su valor es
  distinto: convierte un testimony en artefacto
BLOQUEOS      ninguno. Es un binario que ya está compilado
RELEVANTE     04-IMPLEMENTACION/decompressor/, .gitignore:78, 7ed1eca
VALOR         Convierte la afirmación más citada de la línea BC3 en evidencia
              versionada. Y de paso responde si la limitación #3 de PROYECTO_STATUS
              (rc=0 con [FAIL]) sigue viva
SEGUNDO EFECTO, NO PREVISTO
  Los .log ignorados hacen que un `git clean -x` borre lo único que sostiene la Fase
  2 sin dejar rastro. Eso no es una preferencia de versionado: es pérdida de evidencia
```

## F7 · Versionar lo que no está en git

```
PREGUNTA      ¿Por qué hay evidencia en disco que un `git clean` destruiría?
ESTADO        OPEN
LO QUE NO ESTÁ VERSIONADO  (medido el 2026-10-01)
  FINDINGS      5 de 28:
                017-vm-invalidate-gfx8-function-always
                018-execution-order-invalidacion-gfx8
                019-atc-l2-invalidation-gfx8
                021-write-lock-scoped-subdir-does-not-block
                023-pte-productor-sdma-gfx8
                Los cinco son fuente de afirmaciones PROVEN: RE-01, RE-02, RE-03, RE-04,
                RE-05 y RE-13 dependen de ellos. RE-04 y RE-05 sólo de 023-pte
  HERRAMIENTAS   tools/evidence_search.py, tools/pm4dw.c,
                08-ARQUITECTURA/tools/semref/semref  (el script, no los tests)
  COMPONENTES   04-IMPLEMENTACION/rx550-mem/  completo, 13 ficheros
                04-IMPLEMENTACION/rx550-pm4/  completo, 5 ficheros
                07-DRIVER/driver/                2 fuentes + test
  MODIFICADOS SIN COMMIT   07-DRIVER/kernel/Makefile, AGENTS.md (1434 líneas de diff),
                ideas3.md, opencode.json
POR QUÉ IMPORTA MÁS DE LO QUE PARECE
  COORDINACION.md:9-12 documenta DOS pérdidas reales de trabajo en este proyecto, y
  ambas fueron de trabajo sin commitear. La regla 2 del protocolo dice "commitea antes
  de liberar" por exactamente eso
  pm4dw.c cambió a las 10:46, 10:48, 10:53 y 11:14 mientras esta ronda trabajaba:
  hay sesión activa y su trabajo está sin versionar
LO QUE NO SE HACE AQUÍ  git add es de las sesiones propietarias. Este trabajo no hace
  commits ajenos ni versiona ficheros de otras sesiones
BLOQUEOS      ninguno
VALOR         Alto. Es la acción con más probabilidad de prevenir una pérdida real
```

## F8 · `AGENTS.md` no conoce la línea A

```
PREGUNTA      ¿Un agente que lea AGENTS.md y su lista "NO reabrir" (líneas 107-149)
              sabrá que el writer de page tables es un paquete SDMA y que la geometría
              está cerrada numéricamente?
ESTADO        NO  — verificado por lectura
LO QUE DICE LA LISTA  "NO reabrir estas cuestiones salvo que aparezca nueva evidencia
              contradictoria": Polaris12/GFX8, 8 CUs, fragment_size=9, geometría GART
              cerrada, BAR/full-visible FALSE, SDMA es el writer efectivo, root.bo real,
              PTBA software production cerrada, VM flush software emission cerrada,
              WAIT_REG_MEM encoding cerrada, FUNCTION(0)=always probado, PFP_SYNC_ME,
              hardware execution ordering NOT_PROVEN, PTBA+invalidate atomicity
              NOT_PROVEN, hardware PTE visibility NOT_DETERMINED, runtime takeover NO
              EJECUTADO, GPU INTACTA, WRITE_EXECUTION NONE
LO QUE LE FALTA
  que hay un driver propio en Stage 1 con dos .ko verificados por nm
  que la geometría está CERRADA con valores numéricos, no "estructuralmente cerrada"
  que page_size es 10 y no 9, que contradice lo que 014 decía
  que lacompletion del invalidate es NOT_IMPLEMENTABLE, no pendiente
  que la ruta GART sí tiene completion
  que existe tools/ con cuatro herramientas que auditan el código
  que hay un segundo corpus (7.2.8) y que las conclusiones se cruzaron entre versiones
LO QUE SE HIZO, y es lo máximo que se podía sin escribir encima
  docs/AGENTS-ADDENDA.md: la addenda REDACTADA y VERIFICADA contra el árbol, con
    · qué de la lista "NO reabrir" sigue en pie
    · DOS líneas de esa lista que hay que matizar o refutar
    · todo lo que falta, con su RE
    · el texto listo para pegar en AGENTS.md
    · una tabla de verificación: cada afirmación, con cómo se comprobó
  Adoptarla es pegar un enlace. Eso lo hace quien tenga el turno
LO QUE NO SE TOCÓ
  AGENTS.md. Está modificado sin commitear desde las 10:24 y no hay cerrojo que lo
  declare. La ausencia de cerrojo NO es permiso: COORDINACION.md:88-90 exige /proc/$pid
  y el PID registrado es el del shell, no el del agente (NR-10)
TEST DISCRIMINANTE  no aplica
BLOQUEOS      una línea de escritura, de quien tenga el turno
VALOR         Alto: AGENTS.md es el primer fichero que lee cualquier agente, y su lista
              de "ya conocido" es la que evita repetir trabajo. Con la addenda escrita,
              el coste de adoptarla bajó de horas a un minuto
ESTADO        REDACTADO. La frontera queda reducida a la adopción
```

## F9 · Reinstalar Coccinelle fuera de `/tmp`

```
PREGUNTA      ¿Puede `semref` volver a funcionar sin depender de un directorio efímero?
ESTADO        INVALID  [NR-03, NR-04]
LO QUE PASÓ  La instalación vivía en /tmp/opencode/tools. Ese directorio ya no existe.
  /tmp no sobrevive a un reinicio, y el propio README de semref lo dice: "efímero"
LO QUE HAY QUE HACER  Extraer los RPM en un prefijo persistente (/opt o $HOME) y
  exportar LD_LIBRARY_PATH y COCCINELLE desde ahí. spatch necesita libpcre.so.1, que
  no está en el sistema base
LO QUE ESTÁ BIEN EN EL DISEÑO  El runner devuelve NOT_RUN y exit 3 cuando falta un
  motor; nunca un PASS vacío. Un tool que devuelve vacío cuando le falta una
  dependencia es peor que uno que falla
LO QUE ESTÁ MAL  El gate exige AMBOS motores para enable refs y chain, así que con
  la instalación actual semref no hace nada, ni con ctags disponible
NO SE HACE AQUÍ  Es instalación de software. Fuera del alcance de este trabajo
BLOQUEOS      ninguno
RELEVANTE     08-ARQUITECTURA/tools/semref/README.md, TOOLS-STATUS.md
VALOR         Bajo para el conocimiento (los findings que lo citan conservan su valor),
  alto para no volver a tropezar: quien intente usarlo debe saber que sale rc=3
```

## F10 · La corrección de `COORDINACION.md` que hace falta y no se aplica

```
PREGUNTA      ¿Cómo se evita que dos sesiones con cerrojos de ámbito distintos
              escriban en el mismo fichero?
ESTADO        OPEN. `021-write-lock` ya tiene la respuesta escrita y probada
LA PRUEBA     mkdir .write-lock           -> rc=0
              mkdir .write-lock/findings  -> rc=0, CON LA RAÍZ YA TOMADA  [NR-10]
LA CONSECUENCIA REAL  Dos veces el 2026-10-01, y la segunda el ÍNDICE NUMÉRICO
              también colisionó: dos sesiones eligieron 022 y dos eligieron 021
LA CORRECCIÓN  Antes de mkdir .write-lock/<ámbito>, comprobar que .write-lock no
              existe y que .write-lock/owner no es nuestro. Si existe y no es
              nuestro -> QUEUE_ENTRY_BLOCKED. Una comprobación extra.
  Y un segundo arreglo, independiente y más barato: hacer que el owner que escribe el
  protocolo contenga el token pid= que el preflight busca. Hoy el formato que genera
  no es el que lee. [C-008]
POR QUÉ NO SE APLICA  COORDINACION.md es ley operativa ("Este fichero es ley
  operativa para cualquier agente que trabaje en este repositorio") y cambiarlo
  requiere decisión humana. 021-write-lock lo dice explícitamente y no lo aplica.
LO QUE NO SE PROPONE  Un fichero de "intención" dentro del lock: introduce una
  ventana de carrera entre escribir la intención y tomar el lock, peor que el problema
  que resuelve
BLOQUEOS      decisión humana
VALOR         Es la acción más barata de arreglar y la más cara de no arreglar. Ya
  costó dos veces
```

---

## Fronteiras por valor informativo, ordenadas

El orden no es por valor científico, es por **urgencia de daño ya presente**. Lo primero
es lo que puede corromper memoria; lo último es lo que aún se puede decidir con calma.

| # | Frontera | Cierra | Bloqueo |
|---|---|---|---|
| F3d | ~~`rx550_pm4.c` escribe `count - 1`~~ **CORRECTED 2026-10-02**: ver la ficha | Cerrado: el código escribe `count` |memoria en código ya compilable | sesión propietaria |
| F2 | AD-12: redondeo o truncamiento del sampler | La única de la línea B; puede **revertir** `AD-11` | **ninguno** |
| F2b | Semántica de hardware de cada bit de PTE (8 bits) | La última capa entre el modelo y el silicio para memoria | **la spec no existe** + autorización |
| F7 | Versionar lo que no está en git | Previene pérdida real de evidencia | ninguno (acción de `git add`) |
| F6 | Reejecutar y versionar el agreement test | Convierte testimony en artefacto | ninguno |
| F4 | Decidir el destino de `rx550.ko` | Desbloquea Stage 2 sin hardware | ninguno (decisión) |
| F8 | `AGENTS.md` no conoce la línea A | El primer fichero que lee un agente | sesión activa |
| F1 | Orden de ejecución del invalidate | N1 + N2 de golpe | **autorización + recovery** |
| F5 | Marcas de precedencia en ficheros ajenos | 4 errores que un agente puede copiar | ninguno |
| F3 | Significado de `PAGE_TABLE_DEPTH` | El punto de divergencia kernel/userspace | **la spec no existe** (`BLOCKED_BY_NEGATIVE_RESULT`) |
| F3b | El contrato host ↔ firmware SMU | Abre la línea H entera: el reloj es un mensaje, no un registro. **Reencuadrada por `046`**: la ruta activa es PowerPlay/`smu7`, no legacy-dpm | ninguno, **pero el gate de compilación va primero** |
| F10 | El guard que falta en `COORDINACION.md` | Previene colisiones | decisión humana |
| F9 | Coccinelle fuera de `/tmp` | Devuelve `semref` | ninguno (instalar) |
| F3c | El payload de los paquetes PM4 | 4 preguntas de silicio sin documento | medición + autorización |

`F3d` va primera porque **era** el único punto donde un número documentado mal está en
instrucción de máquina compilable**, y porque la suite verde dice `75 checks OK` mientras
el código escribe un PTE de más. Una frontera que describe un daño ya presente vale más
que una que promete conocimiento nuevo.

`F2`, `F6` y `F7` no tocan hardware y no requieren autorización. `F1` es la de más valor
científico y la única bloqueada dos veces (autorización **y** una ruta de recuperación que
hoy está en `PARTIAL`).