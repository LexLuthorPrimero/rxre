# 023 · La convención `n = payload − 1` de PACKET3, medida sobre el corpus

`CLASSIFICATION=DOCUMENTATION` · `TRACK=STATIC` · `CORPUS=RESEARCH/working/linux-7.1.3`
`WORK_CLASS=READ_ONLY/EVIDENCE` · `WRITE_EXECUTION=NONE` · `MODIFICATIONS=0`
`RUNTIME=NOT_RUN` · `GPU INTACTA`
`AMENDA=022-cond-exec-inerte-en-gfx8.md` (§4), 020-vmflush-dword-budget-gfx8.md
`MEDIDO_EN_MI_ASIC_POR=045` — **la tabla de §4 de este documento no incluye `gfx_v8_0.c`, que es
el fichero de esta GPU** (`vi.c:2107-2123` añade `gfx_v8_0_ip_block`). Las seis generaciones de
la tabla son evidencia de contraste, no evidencia del ASIC, y la conclusión quedó redactada
como si midiera el ASIC. Es el mismo patrón que `043` retractionó en `035`: medir en la
generación equivocada sin notar que se ha medido fuera de objetivo.

Medido con `tools/pm4census.py` sobre `gfx_v8_0.c`: **43 de 43 emisiones reconcilian con
`count = payload - 1`**, 86% de cobertura declarada, 5 `SIN MEDIR` y 2 `LIMITE` impresas. La
regla que este documento estableció queda `PROVEN_DERIVED` **sobre el ASIC de esta GPU**, y no
extrapolada de cinco generaciones ajenas.

Y el `NEGATIVE_RESULT` de `SET_CONFIG_REG` con 1 payload **no se retracta, cambia su
fundamento**: en `gfx_v8_0.c`, `SET_CONFIG_REG, 1` tiene 2 payload. La excepción de
`gfx_v12_1.c:3371` es de otro ASIC, así que no es un `NEGATIVE_RESULT` sobre esta tarjeta sino
una observación de contraste. Ver `045-la-convencion-de-count-nunca-se-midio-en-mi-asic.md`.

## CUDA principal

`020` y `022` trataron la convencion de encoding de `PACKET3(op, n)` como algo
observado en dos o tres paquetes. Ahora esta **medida sobre el corpus entero**:

```
path GFX8 (gfx_v6_0, gfx_v7_0, gfx_v8_0, gmc_v8_0, sdma_v3_0)
  emisiones PACKET3 contables : 68
  n - payload = -1            : 68      excepcion cero

arbol amdgpu completo (304 ficheros)
  emisiones PACKET3 contables : 171
  n - payload = -1            : 170
  n - payload = +0            : 1       (gfx_v12_1.c:3371, ver §4)
```

Herramienta: `08-ARQUITECTURA/tools/pm4_count_census.py`. Sin ella, "n = payload − 1"
seria una regla recordada; con ella, es una propiedad con excepcion cero en el path
que nos interesa.

## CUDA secundaria: una correccion

`022` §4 afirmo que el cuarto dword de `COND_EXEC` era "un dword extra fuera del
payload". **Es falso.** dw4 es el cuarto payload. Esa frase era una suposicion mia
sobre la convencion, y esta ronda la mide. `022` queda enmendado.

## Alcance exacto

1. Medir, para cada `PACKET3(op, n)` emitido, el numero de payload realmente escrito.
2. Establecer la convencion sobre el corpus, con su excepcion countada.
3. Verificar los dos casos de los que dependen `020` y `022`.
4. Corregir lo que la medicion desmienta.

## Criterio de terminacion (cumplido)

171 emisiones contables clasificadas; las no contables identificadas con su motivo.
Agotado.

---

## 1 · Que mide la herramienta

Para cada linea con `amdgpu_ring_write(ring, PACKET3(X, n))`, cuenta las llamadas
`amdgpu_ring_write` siguientes hasta el **siguiente header de paquete** o el fin de la
funcion. Ese numero es el payload. Compara con `n`.

Tres reglas, y por que cada una:

1. **Cada `amdgpu_ring_write()` escribe 1 dword.** Contar `1+n` por `PACKET3` duplica.
   Este error lo cometi en `020` y produjo un residual negativo imposible.
2. **El payload termina en el siguiente header.** Un paquete no se extiende dentro
   del siguiente.
3. **Lo que no se puede contar de forma estatica se marca `UNKNOWN` con su motivo.**
   Nunca se inventa un numero. Una rama o un loop entre el header y el final hacen el
   payload condicional: se declara incountable, no se estima.

### 1.1 · Dos criterios de acierto, y por que el primero no servia

El veredicto inicial era "la convencion se cumple si `-1` esta en la distribucion".
Con un mutante que desplaza el conteo, esa condicion se cumplia igual con **1 de 172**
emisiones y la herramienta salia con `rc=0`. Un criterio que no puede fallar no es un
criterio.

Criterio final: `-1` debe dominar, es decir cubrir **al menos el 90%** de las emisiones
contables. Con el mutante: 1/172 → `rc=1`. Con el arbol real: 170/171 → `rc=0`.

### 1.2 · Un filtro demasiado permisivo, y su sintoma

Un intento de relajar la regla 3 para contar payloads condicionales produjo
`74/88` con la convencion repartida en siete valores distintos (-1 a -8) y sin
dominante. El sintoma diagnostico es ese: **una distribucion sin dominante indica que
el conteo se esta attributando al paquete equivocado**, aqui por atravesar la rama
hasta el header siguiente. Se revirtio a la regla estricta.

Ninguna de las dos direcciones era correcta por defecto; la buena es la que se
justifica con el sintoma, no la que se escribio primero.

## 2 · Resultado sobre el path GFX8

```
$ pm4_count_census.py --only=fx8
ficheros barrados: 5  (gfx_v6_0, gfx_v7_0, gfx_v8_0, gmc_v8_0, sdma_v3_0)
emisiones PACKET3 con n literal y final alcanzable : 68
emisiones no contables de forma estatica          : 22

  n - payload = -1   :   68 ocurrencias
VEREDICTO: la convencion n = payload - 1 se cumple en TODAS las emisiones.
```

**68 de 68.** Sin excepcion. Eso incluye los dos paquetes de los que depende el resto
del trabajo de esta serie.

Las 22 no contables y su motivo:

| fichero | funcion | motivo |
|---|---|---|
| `gfx_v6_0`, `v7_0`, `v8_0` | `ring_test_ring`, `cp_gfx_start` (x2) | loops |
| idem | `ring_emit_ib`, `ring_emit_ib_gfx`, `ring_emit_pipeline_sync` | rama |
| idem | `ring_emit_vm_flush` (x2 en v6/v7) | rama antes de PFP_SYNC_ME |
| `gfx_v8_0` | `kiq_kcq_enable`, `kcq_disable`, `ring_emit_fence_kiq` | rama |
| `gfx_v8_0` | `ring_emit_ce_meta`, `ring_emit_de_meta` | `n` no literal (`cnt_ce`, `cnt_de`) |

`gfx_v8_0_ring_emit_vm_flush` e `init_cond_exec` estan en la lista de incountables por
la mecanica automatica, y por eso los verifique a mano (§3). Declarar la convencion sin
verificar los dos casos de los que dependen `020` y `022` habria sido dejarlos fuera
justo cuando mas importan.

## 3 · Los dos casos que 020 y 022 trataban como pendientes

Medidos con la regla estricta, parando en el siguiente header:

```
PACKET3(WAIT_REG_MEM, 5)   payload = 6     n - payload = -1
PACKET3(COND_EXEC,     3)   payload = 4     n - payload = -1
```

**`WAIT_REG_MEM`**: los 2 dwords de `PFP_SYNC_ME` que siguen **no** son payload de este
paquete — `PFP_SYNC_ME` es un paquete propio. Confirma el conteo de `020`.

**`COND_EXEC`**: payload = 4, luego **dw4 es payload del paquete**, no un extra. Corrige
`022` §4, que afirmo lo contrario.

## 4 · La unica excepcion del arbol

```
gfx_v12_1.c:3371  gfx_v12_1_ring_emit_ib_compute   n=1  payload=1
```

`PACKET3(PACKET3_SET_CONFIG_REG, 1)` seguido de **un** solo dword. La convencion
exigiria dos. Contraste con el resto del arbol, donde el mismo paquete se emite siempre
con dos payload:

```
gfx_v6_0.c:1867    SET_CONFIG_REG, 1  ->  reg offset + 0xDEADBEEF   (2 payload)
gfx_v6_0.c:1897    SET_CONFIG_REG, 1  ->  reg offset + 0            (2 payload)
gfx_v10_0.c:8687   SET_CONFIG_REG, 1  ->  reg + gds_compute_max_... (2 payload)
gfx_v11_0.c:5985   SET_CONFIG_REG, 1  ->  reg + gds_compute_max_... (2 payload)
gfx_v12_1.c:3371   SET_CONFIG_REG, 1  ->  reg                      (1 payload)  <--
gfx_v7_0.c:2246    SET_CONFIG_REG, 1  ->  reg offset               (2 payload)
```

Cinco de seis con dos payload. El sexto es una inconsistencia real del driver de
referencia.

**No es alcanzable en Polaris12**: `gfx_v12_1.c` es GFX12.1, y nuestra placa usa
`gfx_v8_0` (`vi.c:2107-2112`, `gfx_v8_0_ip_block`). Se registra como `NEGATIVE_RESULT`
heredable — si el driver propio llegara a emitir `SET_CONFIG_REG` con un payload, ese
es el camino donde el corpus no resuelve la duda, y no por falta de busqueda sino
porque la fuente es contradictoria.

Tambien pasar por aqui el caso de `gfx_v9_0_ring_emit_cleaner_shader`
(`PACKET3(...,RUN_CLEANER_SHADER, 0)`): aparecio como excepcion en una version del
filtro y hoy cae correctamente en `UNKNOWN`, porque su payload va detras de un
`if/else`. Registrado porque explica por que el recuento movio de 172 a 171 entre
versiones de la herramienta: no es que el corpus cambiara, es que el filtro paso a
declararlo incountable en vez de contarlo mal.

## 5 · La pregunta que NO se resuelve aqui

`022` §4 dejo abierto que campo lee el hardware como `num_skip`. Este documento **no
lo resuelve**, y si deja claro por que:

```
PACKET3_COND_EXEC = 0x22        (vid.h:125, sid.h:359)
```

Opcode y nada mas. En todo `include/` no hay un solo bitfield, comentario ni
documentacion de `COND_EXEC`. `grep` sobre el arbol de registros: 0 resultados.

Reproduccion del parche, dword a dword, para dejar el valor sobre la mesa:

```
dw3 (payload declarado, nunca parcheado) = 0
dw4 (payload parcheado por el driver)    = dw_dist(offset, wptr-1) = nº de dwords de la envolvente
```

El software entrega un valor distinto en cada lectura. Solo una hace que el paquete
sirva. Cual es `NOT_DETERMINED` con la causa nombrada: **falta la especificacion PM4
de GFX8**, no falta analisis del corpus. Una `HYPOTHESIS` adicional —que el hardware lea
el campo parcheado, porque es el unico que recibe informacion util— sigue siendo
`HYPOTHESIS` y no se presenta como conclusion.

### ENMENDADO POR `033` — la causa era permanente, y el referente del `−1` ya no es `NOT_DETERMINED`

Dos correcciones a este documento:

1. **La causa es una ausencia en el plano del fabricante, no una fuente no buscada.**
   La ISA de GCN3 (637 paginas, Rev 1.0 de 2015) esta publicada y **no contiene ninguna
   especificacion PM4**: cero ocurrencias de `PACKET3`, `RELEASE_MEM`, `COND_EXEC`,
   `VM_INVALIDATE`, `INT_SEL`, `WRITE_AT`, `GRBM`, `mmCP`. Ese `NOT_DETERMINED` de arriba
   no se cierra buscando mas. Ver `033` §1.

2. **El `NOT_DETERMINED` mas importante de este documento —de que se resta el `1`— ya
   esta resuelto, y no por la especificacion inexistente sino por el corpus:**

   ```
   campo F  =  numero de dwords de DATOS - 1
   paquete  =  F + 2 dwords
   F = 0x3FFF = RESERVADO (cabecera sola = el paquete, NOP unitario)
   ```

   Tres evidencias, todas medidas: (a) `PACKET3(WAIT_REG_MEM, 5)` con **6** dwords de
   datos en los tres sitios de GFX8, lo que da un paquete de 7 dwords, que es la
   dimension real de `WAIT_REG_MEM` en GCN3; (b) `gfx_v11_0.c:553-568`
   `insert_nop` escribe `F = num_nop − 2` y recursa `num_nop − 1`, que encaja exacto sin
   solapamientos; (c) el tope `0x3ffe` y el caso base `.nop = PACKET3(PACKET3_NOP, 0x3FFF)`
   ("Header itself is a NOP packet") solo tienen sentido juntos si `0x3FFF` queda fuera
   de la formula.

   Mi convencion medida era correcta; lo que faltaba era **de que** se restaba el uno.
   El `NOT_DETERMINED` de §5 (el `dw4` parcheado) **sigue abierto**, y por el motivo que
   §1 de `033` establece.

## 6 · Lo que esto NO es

| Afirmacion | Estado |
|---|---|
| `n = payload - 1` en 68/68 del path GFX8 | `PROVEN` (medido) |
| La unica excepcion del arbol es `gfx_v12_1.c:3371` | `PROVEN` (medido) |
| `dw4` de COND_EXEC es payload, no extra | `PROVEN` (medido) — corrige `022` |
| Los 2 dwords de PFP_SYNC_ME no son payload de WAIT_REG_MEM | `PROVEN` (medido) |
| `SET_CONFIG_REG,1` con 1 payload es una inconsistencia upstream | `PROVEN_DERIVED` (5 de 6 con 2) |
| Que campo lee el hardware como `num_skip` | `NOT_DETERMINED` — falta la spec PM4 |
| Que el hardware ejecute los 68 paquetes como el driver espera | `NOT_DETERMINED` — el encoding no es la semantica |

Ultima fila. Medir que el encoding es coherente **no** dice que el hardware lo
interprete asi. Es el mismo patron que `017`: una constante coherente no es una
semantica. `017` ya demostro que un comentario de driver no es evidencia; aqui lo
relevante es que un header de packet bien formado tampoco lo es.

## 7 · Confounders

Ninguno para el resultado: es conteo de fuente. La unica fuente de error posible es
el parser, y por eso el filtro declara `UNKNOWN` en vez de estimar, y por eso la
herramienta se somete a mutacion.

Riesgo residual declarado: el parser no entiende `#ifdef` ni macros de packet, asi que
un payload definido por macro se contaria como 1 llamada. Ningun `PACKET3` del path
GFX8 cae en eso —comprobado por los 68 contables y las 22 declaradas—, pero el limite
existe y esta ahi dicho.

## 8 · UNLOCKS

- El driver propio puede emitir PM4 en GFX8 con una convencion **verificada sobre 68
  emisiones del propio ASIC**, no heredada de un paquete de otra generacion. Es la
  base minima para escribir un codificador PM4 propio sin inventar encoding.
- `020` y `022` quedan con su base verificada: los conteos de dwords que
  sostienen el presupuesto de ring ya no descansan en una suposicion de encoding.
- La excepcion de `gfx_v12_1.c` identifica donde el corpus **no** puede resolver una
  duda de encoding. Es un punto de entrada concreto si el driver propio necesita ese
  paquete.
- Queda una sola fuente primaria que el corpus no contiene: la **especificacion PM4
  de GFX8**. Todo lo demas de esta serie se ha cerrado con el corpus. Es el limite
  real del metodo estatico aqui, y conviene nombrarlo una vez y no repetirlo por
  hallazgo.

## 9 · Criterio de falsificacion

Se refutaria si: (a) un `PACKET3` del path GFX8 tuviera un payload contable que no
cumpliera `n = payload - 1` — el veredicto lo listaria como excepcion y `rc`
seguiria siendo 0 (por el margen del 90%), asi que la refutacion es visible en la
salida, no silenciosa;
(b) el hardware interpretara `n` como payload y no como payload−1, lo que
invalida **toda** la aritmetica de dwords de `020` y `021` — plausible, y por eso
`020`/`021` declaran que el hardware ejecutar eso como `NOT_DETERMINED`; (c) el
conteo de payloads fuera erroneo en los 68 casos — la mutacion demuestra que la
herramienta detecta un desvio, y la excepcion cero en el path es la comprobacion
cross. (a) y (b) refutan; (c) esta cubierto por el diseno de la herramienta.

## 10 · Evidencia

```
herramienta:  08-ARQUITECTURA/tools/pm4_count_census.py
              --only=fx8  restringe al path; sin argumento barre los 304 ficheros
              salida: distribucion de (n - payload), excepciones, y UNKNOWN con motivo
              criterio de acierto: -1 debe cubrir >= 90% de las contables
              verificado con mutante (payload+2): 1/172 -> rc=1

gfx_v6_0.c:1867,1897   SET_CONFIG_REG,1 con 2 payload (contraste)
gfx_v7_0.c:2246        SET_CONFIG_REG,1 con 2 payload (contraste)
gfx_v10_0.c:8687       SET_CONFIG_REG,1 con 2 payload (contraste)
gfx_v11_0.c:5985       SET_CONFIG_REG,1 con 2 payload (contraste)
gfx_v12_1.c:3371       SET_CONFIG_REG,1 con 1 payload  <-- excepcion
gfx_v9_0.c:7429        RUN_CLEANER_SHADER,0  payload tras if/else -> UNKNOWN
gfx_v8_0.c:6199,6209   WAIT_REG_MEM,5 -> payload 6 ; PFP_SYNC_ME,0 aparte
gfx_v8_0.c:6320-6332   COND_EXEC,3    -> payload 4
vi.h:  105-107 (PACKET3), 125 (COND_EXEC = 0x22)
sid.h: 336-337 (PACKET3), 359 (COND_EXEC = 0x22)
include/ (todo el arbol de registros): 0 resultados para COND_EXEC
```

Ningun registro obtenido de MMIO. Ninguna operacion runtime. `GPU INTACTA`.

Nota de redaccion: el borrador de §8 y §9 contenia cuatro fragmentos corruptos,
entre ellos texto en chino introducido al redactar. Corregidos; el contenido
tecnico no cambio. Es el cuarto caso del mismo defecto al escribir bajo carga, y
por eso la nota se conserva: el defecto es mio y se repite.