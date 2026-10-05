# 1438 — el oráculo del fence: la visibilidad no la da el rptr, la da un paquete; y ningún oráculo es demostrable sin hardware

```text
AGENCIA=RX550-INVESTIGACION · WORK_CLASS=AGENT-MAIN/RE
CLASSIFICATION=ESPECIFICACION+CIERRE-DE-UNA-FRONTERA
TRACK=STATIC(corpus) + LECTURA-PASIVA(fdinfo, sysfs) · sin GPU · sin sudo
GENERADO=2026-10-04
AFECTADO=el diseño de la arista fence/IRQ que el hallazgo 1428 dejó abierta
ORIGEN=el hallazgo 1428 decía "la interrupción es la única señal asíncrona" y 1434 decía que
       el rptr leído de memoria del host era "un oráculo mejor".  Ambas cosas eran
       optimistas.  Aquí se mide lo que se puede y lo que no.
ESTADO=PROBADO · el fence NO es el rptr: es un valor de writeback de un paquete
       · el rptr no es un oráculo de finalización, y su latencia no está documentada
       · fdinfo sirve para lactividad y attachment, NO para finalización
       · TODA la liveness del oráculo es indemostrable bajo la restricción actual
       · y cuatro errores de verificación, tres del revisor y uno MÍO
```

## 1. El error de partida: el fence no es el rptr

Mi propia afirmación en el hallazgo 1434 §4 —*"hay oráculo por hardware sin IRQ: rptr y
wptr se leen de memoria del host"*— era **demasiada**. Lo que el rptr da es **cuánto ha
consumido el hardware**, no **si una operación concreta ha terminado**.

La distinción importa, y en gfx8 es tajante porque **no hay barreras**. Verificado, y esta
vez con la trampa de grep en mente (§5.1):

```text
grep -rn 'ATOMIC_ROOT|PACKET3_ATOMIC|SBAR' amdgpu/*.c   ->  0 resultados reales
```

**Cero barreras en todo el driver amdgpu, todas las generaciones.** En gfx8 el IB del
usuario es opaco al kernel (`amdgpu_cs.c:381`, y `parse_cs` es `NULL` en las tres tablas
de ring, `gfx_v8_0.c:6870,6916,6951`), así que el driver no puede insertar una. Por lo
tanto **la visibilidad de las escrituras de un shader la tiene que aportar el propio
programa del usuario**, dentro de su IB, mediante el paquete de fin de trabajo.

Y con cero barreras, el mecanismo de fence tiene que ser otro. **Aviso: no he verificado la
cita concreta del revisor para ese mecanismo** —`CACHE_FLUSH_AND_INV_TS_EVENT`, que no
localicé ni en `amdgpu_ib.c` ni en `amdgpu_fence.c` (§5.4). **El principio de que el
fence no es el rptr se sostiene por la ausencia de barreras, que sí está verificada; el
nombre exacto del paquete, no.**

## 2. El rptr: qué es y por qué no cierra nada

Lo que sí está verificado sobre el rptr, y es real:

```text
lectura del rptr   = *ring->rptr_cpu_addr                 gfx_v8_0.c:6006-6009
wptr con doorbell  = *ring->wptr_cpu_addr                 gfx_v8_0.c:6011-6020
wptr sin doorbell  = mmCP_RB0_WPTR 0x3045                 idem
commit del wptr    = WDOORBELL32(0x020, wptr)  -> BAR2    gfx_v8_0.c:6026-6029
```

Lo que **no** cierra, y es el motivo de retirarlo como oráculo:

| hueco | por qué importa |
|---|---|
| **la latencia del writeback no está documentada en ninguna parte del corpus** | sin ella no hay bucle de sondeo con intervalo justificable |
| `RPTR_WRITEBACK_TIMER` **existe** pero **el driver gfx8 no lo escribe** | el temporizador corre al valor por defecto del silicio, que nadie conoce. **Verificado: sí lo escriben `sdma_v5_0.c:968`, `sdma_v5_2.c:868`, `sdma_v6_0.c:865` — o sea, en las generaciones posteriores. En `sdma_v3_0.c`, que es la de esta placa, no.** |
| las constantes de sondeo de gfx8 (`0x20`, `4`, `0x0A`) son **cuentos de reintento de `WAIT_REG_MEM`**, no periodos de writeback | es un error fácil de cometer al elegir un intervalo |

**Consecuencia**: un bucle de fence por rptr necesita un intervalo, y **el intervalo no se
puede derivar del código**. Habría que medirlo, y medirlo exige escribir un registro.

### 2.1 El idioma correcto del wrap, que sí está en el árbol

```c
/* amdgpu/amdgpu_fence.c:315 */
(int32_t)(want - got) > 0
```

Es la comparación con signo que sobrevive al wrap de un puntero de 32 bits. Existe en el
corpus y es la que un driver debe usar, no un `>=`.

## 3. `fdinfo`: no sirve para el fence, pero sí para otra cosa

Ruta candidata porque no necesita privileged access ni despierta la GPU. Medida:

| afirmación | veredicto |
|---|---|
| `drm-engine-*` mide finalización de GPU | **falso.** es `time_spend[hw_ip]` (`amdgpu_ctx.c:980`): contabilidad del lado CPU, escrita por quien envía. No consulta rptr, ni el writeback, ni ningún MMIO |
| se puede muestrear hoy como línea base | **no.** **30 fds DRM en la máquina, 0 con `drm-engine-*`** |
| hay un cliente vivo que envíe trabajo | **no.** el único cliente amdgpu es Xwayland, con `drm-total-vram: 136 KiB` y **`drm-resident-vram: 0`** — nunca ha enviado trabajo |

> **`fdinfo` no es un oráculo de fence, y no lo rescata nadie.** Es contabilidad de envío.

**Pero aporta algo único**, y por eso no es un callejón sin salida:

```text
drm-client-id: 99      pasid: 58      drm-pdev: 0000:01:00.0
```

Es **el único canal disponible sin privilegios, sin despertar la GPU e independiente del
silicio** para confirmar que hay un cliente amdgpu **adjunto** a `0000:01:00.0` mientras el
dispositivo está en `suspended`/`D3hot`. Eso resuelve la pregunta **"¿hay alguien siquiera
pidiéndole trabajo a esta GPU?"** — que va **antes** de que la pregunta del fence esté
bien planteada — y da una delta del lado del envío (crecimiento de memoria, cambios en
`amd-requested-*`) sin MMIO.

## 4. El veredicto honesto

| oráculo | qué detecta | qué NO detecta | demostrable sin escribir un registro |
|---|---|---|---|
| rptr pasa el objetivo | progreso del hardware | un shader colgado; si una instrucción concreta terminó | **no** |
| un vector MSI (uno solo) | fin asíncrono | nada del interior | **no** |
| bits de ocupado (`mmSRBM_STATUS`, `mmGRBM_STATUS2`) | que el motor respira | por qué | lectura trivial, pero **interpretación no establecida** |
| `fdinfo` | que hay cliente y envío | cualquier cosa de la GPU | **sí**, y ya medido |
| los registros de fault de VM (`0x537/0x53f/0x539`) | *por qué* falló una traducción | que el trabajo terminara | lectura trivial |

> **El conjunto es una especificación bien fundada, y su *liveness* no se puede demostrar
> de ninguna manera bajo la restricción actual.** No hay atajo de sólo lectura a ninguno de
> sus prerrequisitos: escribirlos **es** la acción.
>
> Esto **cierra la frontera del oráculo** en el sentido de §100: no queda discriminante útil
> que no exija hardware. La frontera no está bloqueada por falta de información; está
> bloqueada por la regla que el propietario puso, y esa regla es correcta.

## 5. Cuatro errores de verificación, y por qué importan más que el resultado

### 5.1 El MÍO: `SBAR` dentro de `CROSSBAR` (`SBAR` es subcadena de `CROSS**SBAR**`)

```text
mi grep:      dce_v8_0.c:1902  fb_swap = ((GRPH_RED_SEL_B << GRPH_SWAP_CNTL__GRPH_RED_CROSSBAR__SHIFT)
mi conclusion: "hay 2 barreras en el arbol"   <-- FALSO
realidad:      0 barreras.  El revisor tenia razon y mi verificacion era la defectuosa
```

**Patrón reutilizable**: un grep de identificadores cortos sobre `*_SHIFT`/`__MASK` en
cabeceras de AMD produce falsos positivos casi garantizados. Hay que contar **con el
contexto de la línea**, no las coincidencias.

### 5.2 Del revisor: «`mmSDMA0_STATUS_REG` no lo lee nadie en la ruta VI/gfx8»

**Parcialmente falso.** `vi.c:675-676` lo menciona:

```c
{mmSDMA0_STATUS_REG + SDMA0_REGISTER_OFFSET},
{mmSDMA0_STATUS_REG + SDMA1_REGISTER_OFFSET},
```

Es una **entrada de tabla de registros**, no un uso de la semántica del registro: la
sustancia de su afirmación aguanta, la redacción no. *Un registro puede estar listado en
una tabla de volcado y no ser leído nunca para su significado.*

### 5.3 Del revisor: «`RPTR_WRITEBACK_TIMER` no lo escribe ningún fichero»

**Demasiado fuerte.** Lo escriben `sdma_v5_0.c:968`, `sdma_v5_2.c:868` y
`sdma_v6_0.c:865`. Lo cierto, que es lo que importa, es **que no lo escribe `sdma_v3_0.c`,
que es el de esta placa**. *Una negación sobre un fichero no es una negación sobre el árbol.*

### 5.4 Del revisor: la cita del mecanismo de fence no se sostiene donde él la puso

```text
grep -n 'CACHE_FLUSH_AND_INV_TS' amdgpu/amdgpu_ib.c     ->  0 resultados
```

**No localicé el símbolo donde el revisor lobeds.** No lo doy por bueno. Queda
`NOT_VERIFIED`, y por eso §1 no lo afirma.

## 6. Lo que este hallazgo NO hace

- **No nombra el mecanismo de fence.** §1 sostiene el principio; el paquete concreto no está
  verificado.
- **No mide ninguna latencia.** La del writeback es `NOT_DETERMINED` y medible sólo con
  hardware.
- **No ejecuta nada.** Ni un registro, ni un fdinfo que cree, ni un cliente nuevo.
- **No reabre la toma de posición.** Y la restricción del propietario sigue vigente.

## 7. Procedencia

```text
RESEARCH/baseline/linux-7.1.3/drivers/gpu/drm/amd/     (fuente del kernel que corre)
  amdgpu/gfx_v8_0.c:6006-6029    lectura de rptr/wptr, y el commit por doorbell
  amdgpu/amdgpu_fence.c:315      el idioma del wrap, con signo
  amdgpu/amdgpu_ib.c             CACHE_FLUSH_AND_INV_TS  ->  0 resultados (NO VERIFICADO)
  amdgpu/amdgpu_cs.c:381         parse_cs NULL: el IB del usuario es opaco
  amdgpu/gfx_v8_0.c:6870,6916,6951   las tres tablas de ring
  amdgpu/sdma_v3_0.c             NO escribe RPTR_WRITEBACK_TIMER
  amdgpu/sdma_v5_0.c:968  v5_2:868  v6_0:865    si lo escriben, en otras generaciones
  amdgpu/vi.c:675-676            mmSDMA0_STATUS_REG listado en tabla, no usado
  amdgpu/dce_v8_0.c:1902-1903    el falso positivo: CROSSBAR contiene SBAR
  amdgpu/amdgpu_ctx.c:980        drm-engine-* = time_spend[hw_ip], contabilidad CPU
medido   30 fds DRM en /proc/*/fdinfo/  ->  0 con drm-engine-*
medido   cliente amdgpu: drm-client-id 99, pasid 58, drm-pdev 0000:01:00.0,
         drm-total-vram 136 KiB, drm-resident-vram 0
         runtime_status suspended, D3hot
```

```text
ESTADO=PROBADO · CERO barreras en todo el driver amdgpu, todas las generaciones (verificado
       con grep, y el falso positivo CROSSBAR/SBAR identificado y descartado)
       · el fence NO es el rptr: el rptr mide consumo, no finalización
       · la latencia del writeback NO esta documentada y el temporizador no lo fija gfx8:
         el intervalo de sondeo no se puede derivar del codigo
       · fdinfo mide envio, no finalizacion, y hoy no hay ningun cliente que envie
REFUTADO por mi
  "el rptr es un oraculo de fence mejor que la IRQ"  (lo dije yo en 1434 §4)
  "hay 2 barreras en el arbol"  ->  era SBAR dentro de CROSSBAR
MATIZADO sobre el revisor
  mmSDMA0_STATUS_REG: si aparece en vi.c:675-676, pero como entrada de tabla
  RPTR_WRITEBACK_TIMER: si lo escriben v5/v5_2/v6; lo que no hace es sdma_v3_0.c
  CACHE_FLUSH_AND_INV_TS_EVENT: no localizado donde lo cita  ->  NOT_VERIFIED
CIERRA (frontera, §100)  el oraculo del fence queda como ESPECIFICACION.  No queda
       discriminante util que no exija escribir un registro.  No es falta de informacion:
       es la regla del propietario, y la regla es correcta
APORTA  fdinfo es el unico canal sin privilegios, sin despertar la GPU, para responder
       "hay alguien adjuntado a esta GPU?".  Eso va ANTES de la pregunta del fence
Siguiente  1) localizar de verdad el paquete de fence: buscar CACHE_FLUSH en todo el arbol,
           no solo en amdgpu_ib.c, y en las cabeceras de paquete
         2) si el propietario levanta la restriccion, lo primero que se mide es la latencia
           del writeback con una sola lectura de un solo registro: es la constante que
           falta y bloquea el diseno del bucle
         3) hasta entonces, el diseno del fence se escribe como especificacion con sus
           huecos nombrados, y no como codigo
```
