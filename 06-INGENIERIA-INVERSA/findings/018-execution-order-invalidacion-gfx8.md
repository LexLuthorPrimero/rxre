# 018 · Orden de ejecución GFX8: el hardware no tiene handshake de invalidación

```text
PENDIENTE=D-ORDEN-EJECUCION-INVALIDACION | HALLAZGO=018-execution-order-invalidacion-gfx8.md | ESTADO=NOT_DETERMINED | NECESITA=INYECCION_PM4_EN_ANILLO | ALCANZABLE_SIN_ROOT=no
```

## DISCORDANTE. Requiere escribir paquetes PM4 en el anillo vivo y medir el
orden de ejecucion: eso es NIVEL 3 y ademas depende de un modulo propio
cargado, que es NIVEL 4. Hoy es BLOCKED_BY_AUTHORIZATION, no pendiente de
investigacion. La ruta existe; lo que falta es autorizacion.


`CLASSIFICATION=DOCUMENTATION` · `TRACK=STATIC` · `CORPUS=rx550-upstream-7.2.8/linux-7.2.8`
`WORK_CLASS=READ_ONLY/EVIDENCE` · `WRITE_EXECUTION=NONE` · `MODIFICATIONS=0`
`CONTINUES=017-vm-invalidate-gfx8-function-always.md`

## CUDA principal

El `WAIT_REG_MEM` sin predicado de GFX8 no es un descuido del driver: **es la mejor
aproximación posible al hardware disponible**. GFX8 no expone ningún registro de
acknowledgement de invalidación. No hay forma, con los registros publicados, de esperar a
que la invalidación termine.

Consecuencia directa: **esperar la completion de la invalidación no es una investigación
pendiente — es `NOT_IMPLEMENTABLE` con este conjunto de registros**. La seguridad del path
depende enteramente de un invariante del propio ring, no de un handshake con el hardware.

Matiz que separa este documento de `017`: el *orden* de ejecución de la invalidación respecto
al siguiente IB **sí** es una pregunta abierta y medible (`NOT_DETERMINED`, RUNTIME). Lo que
es `NOT_IMPLEMENTABLE` es la *espera explícita de completion*, porque falta el registro. No
son lo mismo y conviene no confundirlos al leer "not implementable" como "no investigado".

## Alcance exacto

1. Determinar si GFX8 (GFX6/GFX7/GFX8 = familia VI/CIK) expone un ACK de invalidación.
2. Comparar con GFX9+, donde sí existe.
3. Localizar qué garantiza realmente el `WAIT_REG_MEM`/`PFP_SYNC_ME` del path GFX8.
4. Clasificar `hardware execution ordering` (AGENTS.md:141) con la evidencia disponible.

## Criterio de terminación (cumplido)

Buscados los registros de acknowledgement/invalidate en las 5 cabeceras GMC de la
generación VI/CIK y en MMHUB. La diferencia entre generaciones está cerrada.

---

## 1 · GFX8 no tiene ACK de invalidación

Búsqueda exhaustiva sobre las cabeceras de registros de la generación:

```
$ for f in gmc_6_0_d gmc_7_0_d gmc_7_1_d gmc_8_1_d gmc_8_2_d; do
      grep -c "ACK\|ACKNOWLEDGE" $f.h; done
1 1 1 1 1
```

Cada una tiene **1** coincidencia, y en las cinco es la misma: `mmMC_SHARED_BLACKOUT_CNTL`,
offset `0x82b`. La subcadena `ACK` casa dentro de `BLACKOUT`. No es un registro de
acknowledgement:

```
gmc_6_0_d.h:1007  gmc_7_0_d.h:263  gmc_7_1_d.h:295  gmc_8_1_d.h:307  gmc_8_2_d.h:304
#define mmMC_SHARED_BLACKOUT_CNTL   0x082B   (las cinco, mismo offset)
```

Descartadas las cinco, quedan **0** registros de acknowledgement en toda la generación.
`PROVEN_ABSENT` por objeto nombrado, no por un `grep -c` que contaba sin querer.

Corrijo aquí un dato del borrador de este documento: había reportado `0` para cuatro de las
cinco cabeceras. El valor real es `1` en las cinco, por la razón de arriba.

Los únicos registros INVALIDATE en toda la generación (`grep -n "INVALIDATE" gmc_8_2_d.h`):

```
617:  mmVM_INVALIDATE_REQUEST    0x51e
618:  mmVM_INVALIDATE_RESPONSE   0x51f
```

Dos registros. Sin pareja REQ/ACK, sin canal de completion consultable. `RESPONSE` existe
(`DOMAIN_INVALIDATED_0..15`, `gmc_8_2_sh_mask.h:6621-6652`) pero **no hay ningún campo de
request al que correlacionarlo**: `REQUEST` es un mapa de 16 bits de dominios, no una
ventana con token. Escribir `REQUEST=0x3` y leer `RESPONSE` no permite saber si esos dos
bits fueron recién invalidados o proceden de una invalidación anterior. El hardware no
ofrece un handshake utilizable.

`NO_INVALIDATION` (bit 30 de `ATC_VMID{n}_PASID_MAPPING`, `gmc_8_2_sh_mask.h:6071-6072`)
es un caso especial de esta falta de canal: puede inhibir la invalidación de un VMID sin que
ningún registro lo refleje como pendiente. Un `RESPONSE` con el bit puesto podría ser de una
invalidação que el hardware decidió no ejecutar. No he verificado ese efecto (exige RUNTIME),
así que queda `NOT_DETERMINED`, pero la forma del registro lo hace plausible y por eso la
correlación por `RESPONSE` no es siquiera una opción a medias.

GFX9+ sí lo tiene, y el contraste es el que da la medida de lo que falta:

| | GFX8 (`gmc_v8_0`) | GFX9 (`mmhub_3_0_0`) |
|---|---|---|
| Registro de petición | `mmVM_INVALIDATE_REQUEST` `0x51e` (16 dominios) | `regMMVM_INVALIDATE_ENG0_REQ` `0x763` |
| Registro de ack | **NO EXISTE** | `regMMVM_INVALIDATE_ENG0_ACK` `0x775`, `PER_VMID_INVALIDATE_ACK_MASK 0x0000FFFF` |
| Semáforo de power-gating | no | `regMMVM_INVALIDATE_ENG0_SEM` `0x751` |
| Cómo espera el driver | `WAIT_REG_MEM` sin predicado | `emit_reg_write_reg_wait(req, ack, req, 1<<vmid)` — **compara de verdad** |

`gmc_v9_0_emit_flush_gpu_tlb` (`gmc_v9_0.c:951-955`):

```c
amdgpu_ring_emit_reg_write_reg_wait(ring, hub->vm_inv_eng0_req + …,
                                    hub->vm_inv_eng0_ack + …,
                                    req, 1 << vmid);
```

`FUNCTION(3)` (`==`), `ref=req`, `mask=1<<vmid` contra un registro de ack. Eso **sí**
consume completion. `gfx_v9_0_wait_reg_mem` (`gfx_v9_0.c:1172-1192`) centraliza el
encoding y usa `WAIT_REG_MEM_FUNCTION(3) | /* equal */`.

GFX8 no tiene nada de eso. `PROVEN` por ausencia en las 5 cabeceras de la generación, no
por lectura parcial.

## 2 · El código GFX8 no puede esperar aunque quisiera

`struct amdgpu_ring_funcs` declara dos punteros de espera con predicado
(`amdgpu_ring.h:282-285`):

```c
void (*emit_reg_wait)(struct amdgpu_ring *ring, uint32_t reg,
                      uint32_t val, uint32_t mask);
void (*emit_reg_write_reg_wait)(struct amdgpu_ring *ring,
                                uint32_t reg0, uint32_t reg1,
                                uint32_t ref, uint32_t mask);
```

`grep -c "emit_reg_wait\|emit_reg_write_reg_wait" gfx_v8_0.c` → **0**. Las tres
`ring_funcs` de `gfx_v8_0` — `gfx_v8_0_ring_funcs_gfx` :6873-6917,
`gfx_v8_0_ring_funcs_compute` :6919-6952, `gfx_v8_0_ring_funcs_kiq` :6954-6977 —
**no asignan ninguno de los dos**. Es un `PROVEN` estructural: `emit_wreg` está implementado, `emit_reg_wait` no
existe para GFX8.

`LIMITACIÓN` del modo en que lo comprobé: `grep -c "emit_reg_wait\|emit_reg_write_reg_wait"
gfx_v8_0.c` devuelve 0. Eso prueba que **el identificador no aparece**, no que el puntero sea
nulo en tiempo de ejecución. Para afirmar lo segundo haría falta inicializar un
`struct amdgpu_ring_funcs` de GFX8 y leer el offset del campo, algo que exige RUNTIME y que
`AGENTS.md` §Seguridad prohíbe sin autorización. Lo que sí es `PROVEN` por lectura de
código: los tres `ring_funcs` de `gfx_v8_0` listan sus campos explícitamente (designador
designado, sin `= NULL` implícito en la inicialización) y `emit_reg_wait` no está entre
ellos. La distinción importa: `NOT_FOUND` el nombre, `PROVEN_DERIVED` la ausencia en la
inicialización.

Y no es un descuido de la interfaz: `amdgpu_gmc_fw_reg_write_reg_wait`
(`amdgpu_gmc.c:877-897`) llama a `amdgpu_ring_emit_reg_write_reg_wait`, que es un macro
directo sin comprobación (`amdgpu_ring.h:450`). Si se invocarase sobre un ring GFX8,
**deref de puntero nulo**. Que no lo haga es lo único que evita el fallo: las únicas
llamadas del árbol están en `gmc_v9_0.c:805`, `gmc_v10_0.c:260`, `gmc_v11_0.c:248`,
`gmc_v12_0.c:325`, `gmc_v12_1.c:387` — **ninguna GFX8**. `NOT_REPRODUCED`, y la condición
de seguridad es "solo se llama desde GMC de GFX9+", no una guarda en el código.

`NEGATIVE_RESULT`: no existe ninguna ruta en GFX8 que espere un ack de invalidación. No es
que esté sin explorar; es que no hay registro que esperar.

## 3 · Qué garantiza realmente el sufijo

```
PTBA                    (2 WREG:  gfx_v8_0_ring_emit_wreg, 5 dw cada uno = 10)
WAIT_REG_MEM always     (7 dw, no compara)
PFP_SYNC_ME             (2 dw, sólo ring GFX)
```

Corrección: escribí 6 dw para el `WAIT_REG_MEM`. Conteo literal de llamadas a
`amdgpu_ring_write` en el bloque: **7** (header, config, `mmVM_INVALIDATE_REQUEST`, `0`,
`0` ref, `0` mask, `0x20` poll). El total del path es 10 + 7 + 2 = **19 dw en ring GFX**.

Reparto de motores, de `vid.h:150-164`:

```
WRITE_DATA_ENGINE_SEL(x)  (x << 30)   0=me  1=pfp  2=ce
WR_CONFIRM                (1 << 20)
WAIT_REG_MEM_ENGINE(x)    (x << 8)    0=me  1=pfp
```

`gfx_v8_0_ring_emit_wreg` (`gfx_v8_0.c:6352-6374`) selecciona
`WRITE_DATA_ENGINE_SEL(1) | WR_CONFIRM` para ring GFX, es decir **los WREG los ejecuta el
PFP**. El `WAIT_REG_MEM` se emite con `WAIT_REG_MEM_ENGINE(0)`, es decir **lo consume el
ME**. El `PFP_SYNC_ME` posterior existe porque el PFP no puede seguir leyendo el ring antes
de que el ME haya pasado por el wait: sin predicado, ese wait no bloquea nada, así que el
sync sí es un requisito real de orden interno del ring, no un refuerzo del anterior.

Reordenado por motor:

```
PFP:  [WRITE PTBA] → [WRITE INVALIDATE_REQUEST]  ...→  [PFP_SYNC_ME]
                                                          │
ME :                                    [WAIT_REG_MEM always]
```

Lo que `PFP_SYNC_ME` protege es **la decodificación de paquetes**, no la invalidación. Es
independiente del problema de completion: seguiría siendo necesario aunque el wait
comparase.

## 4 · Clasificación del punto abierto de AGENTS.md:141

`hardware execution ordering NOT_PROVEN`. Con esta evidencia:

| Elemento | Estado | Base |
|---|---|---|
| Orden de emisión software `PTBA → INVALIDATE → WAIT → PFP_SYNC_ME → next IB` | `PROVEN_DERIVED` | `gfx_v8_0.c:6197-6221` + `:6352-6374` |
| Que el WAIT no compare | `PROVEN` (encoding) | `vid.h:169-189`, `mask=0` |
| Que GFX8 no expone ack de invalidación | `PROVEN_ABSENT` | 5 cabeceras GMC, 0 coincidencias |
| Que el path GFX8 no pueda esperar completion | `NOT_IMPLEMENTABLE`¹ | falta el registro; no falta la investigación |
| Orden de ejecución hardware de la invalidación respecto al siguiente IB | `NOT_DETERMINED` | requiere RUNTIME; **y no es la pregunta correcta** |

La repregunta: no "¿el hardware ordena X antes que Y?" sino **"¿qué garantiza que el
siguiente IB no se ejecute con la TLB viejas?"**. La respuesta del driver GFX8 es: *nada
explícitamente*. Lainvalidación y el siguiente IB son instrucciones en el mismo ring; el
orden entre la escritura de `0x51e` y el fetch del IB depende del hardware.

**Esto NO es un defecto del driver de referencia.** Es una limitación de la generación.
Un driver propio para Polaris12 hereda la misma restricción, y la respuesta correcta es
`MODEL_CHOICE`: añadir un fence/poll explícito en el software, o aceptar el riesgo
documentado. `DESIGN_FREEDOM` aplica. Lo que **no** se puede hacer es fingir que el
`WAIT_REG_MEM` es un fence: `017` ya lo caracterizó como no-op y este documento explica por qué
no hay alternativa.

## 5 · Refutación de 017 §5, segunda fila

`017` dejó abierto: *"Qué garantiza hardware el intervalo `0x20` sin comparación"*.

Reformulado y **cerrado en parte**: no es una propiedad del intervalo. `poll_interval` sólo
tiene sentido cuando hay predicado; con `FUNCTION=always` el campo no es consumido por
ninguna decisión. Lo que se investigaba era un efecto del paquete que el propio paquete
declara no tener. `NOT_DETERMINED` → reformulado como: **no hay garantía, y no puede
haberla con estos registros**. El intervalo `0x20` es un residuo de un paquete que en GFX9
sí compara (`gfx_v9_0.c:1191` también usa `0x20` con `FUNCTION(3)`).

## 6 · UNLOCKS

- La capa de invalidación del driver propio tiene un requisito nuevo y **verificable**:
  el hardware no ofrece completion, así que cualquier sincronización debe aportarla el
  software. Eso es `REQUIREMENT` derivado de evidencia, no herencia.
- `VM_INVALIDATE_RESPONSE` sigue siendo `NOT_DETERMINED`: si en algún momento se quisiera
  un poll, ese es el único registro candidato, y su semántica (lectura-no-correlacionable)
  es justamente lo que impide usarlo. Requiere RUNTIME para caracterizarlo, y el valor
  que dé no resolvería el problema de correlación.
- `amdgpu_gmc_fw_reg_write_reg_wait` sin guarda para rings sin
  `emit_reg_write_reg_wait`: si el driver propio reordena el flush, cuidado. `NEGATIVE_RESULT`
  heredable.

## 7 · Criterio de falsificación

Se refutaría si: (a) apareciera un registro de ack de invalidación en
`gmc_8_2_d.h`/`gmc_8_1_d.h` fuera del rango `0x51e/0x51f` — refutaría §1 y reabriría
`NOT_IMPLEMENTABLE`; (b) la especificación PM4 de GFX8 definiera `FUNCTION(always)` como
"esperar hasta que `REQUEST` valga `ref`" — entonces el wait sí sería un fence y tanto
`017` §4 como §4 de este documento se caerían; (c) `WAIT_REG_MEM_ENGINE` resultara tener
otro significado que "motor que evalúa el predicado". (b) y (c) son `NOT_DETERMINED` con
la evidencia local: `PROVISIONAL`.

## 7bis · Vocabulario: `NOT_IMPLEMENTABLE` no está en AGENTS.md

El modelo epistemológico de `AGENTS.md:176-193` no incluye `NOT_IMPLEMENTABLE`. Lo uso
aquí para "no se puede, con los registros publicados" y lo declaro explícitamente para que
no se lea como uno de los estados canónicos. Si colisiona con el vocabulario del proyecto,
lo correcto es reescribirlo como `NOT_AVAILABLE` (el registro no existe) — que sí es
canónico y describe el mismo hecho. `PROVISIONAL` hasta que se decida.

## 8 · Evidencia

```
sha256 tarball: 12e8d5a973d1ad7c5a5c69882e4022b131ed715db7003fdcd760ddf8c3e51941 (linux-7.2.8.tar.xz)
                 recalculado; coincide con upstream.sha256 y local.sha256.
                 LIMITACIÓN: esos ficheros guardan el hash sin nombre → `sha256sum -c` falla.
                 El hash cubre el .tar.xz, no el árbol extraído.

gmc_8_0.c:              655-660, 662-677, 1728-1731
gfx_v8_0.c:             6197-6221, 6352-6374,
                        6873-6917 (ring_funcs_gfx), 6919-6952 (compute), 6954-6977 (kiq)
gfx_v9_0.c:             1172-1192 (wait_reg_mem helper), 5662-5673, 5938-5982
amdgpu_gmc.c:           877-897
amdgpu_ring.c:          433-439        amdgpu_ring.h: 282-285, 449-450
vid.h:                  150-164, 169-189, 196-200
gmc_v9_0.c:             707-722, 920-967
amdgpu/sid.h:           sin WAIT_REG_MEM_OPERATION (grep rc=1)
include/asic_reg/gmc/  gmc_6_0_d.h, gmc_7_0_d.h, gmc_7_1_d.h, gmc_8_1_d.h, gmc_8_2_d.h
                        → grep -c "ACK\|ACKNOWLEDGE" = 1 en las cinco
                        → única coincidencia en cada una = mmMC_SHARED_BLACKOUT_CNTL
                          0x82b (subcadena de BLACKOUT), descartada por inspección
include/asic_reg/gmc/gmc_8_2_d.h:  617-618
include/asic_reg/gmc/gmc_8_2_sh_mask.h: 6621-6652, 6071-6072
include/asic_reg/mmhub/mmhub_3_0_0_offset.h:  796, 900, 936, 972
include/asic_reg/mmhub/mmhub_3_0_0_sh_mask.h: 6223-6225
```

Ningún registro leído de MMIO en hardware. Ninguna operación runtime. `GPU INTACTA`.