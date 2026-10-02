# 188 · El nombre del op 12 no es un alias: seis emisores, seis de seis, y una cita que señalaba a la generación equivocada

```
CLASSIFICATION=CORRECTION+MEASUREMENT · TRACK=STATIC
CORPUS=RESEARCH/working/linux-7.2.8 · HARDWARE_SCOPE=HOST-C/RX550/0000:01:00.0
WORK_CLASS=READ_ONLY/EVIDENCE · WRITE_LOCAL=PROPIOS · MODIFICATIONS_CORPUS=0
RUNTIME=NOT_RUN · GPU INTACTA · CERROJOS=0
```

## Qué resuelve

Un nombre de opcode que había cambiado **tres veces** en el mismo header del
driver propio. La pregunta era siempre la misma —¿`SDMA_OP_GEN_PTEPDE` o
`SDMA_OP_PTEPDE`?— y la respuesta siempre había sido un argumento. Ahora es
una medición sobre **los seis emisores del op 12 que existen en el árbol**:

```
  emisor           nombre del op 12    campo count    generación SDMA
  sdma_v2_4.c:714     GEN_PTEPDE        count          V2
  sdma_v3_0.c:987     GEN_PTEPDE        count          V2   <-- corre en esta GPU
  sdma_v4_0.c:1649    PTEPDE            count - 1      V3
  sdma_v4_4_2.c:1245  PTEPDE            count - 1      V3
  sdma_v5_0.c:1217    PTEPDE            count - 1      V3
  sdma_v5_2.c:1116    PTEPDE            count - 1      V3
```

**Seis de seis, sin excepción.** El nombre **predice** la convención del `count`
en el 100 % de los casos. No son dos sinónimos escritos de forma distinta: el
nombre marca la generación, y la generación decide el campo.

## 1 · El hallazgo de fondo: la cita apuntaba a la generación equivocada

`rx550_pm4.h` decía:

```
#define RX550_SDMA_OP_PTEPDE   12   /* vega10_sdma_pkt_open.h:37 */
```

El **valor** es correcto. La **autoridad** no: `vega10_sdma_pkt_open.h` es la
cabecera de la generación V3, la que esta GPU **no** ejecuta, y la que usa
`count - 1` — exactamente la convención que `findings/044` tuvo que deshacer en
el codificador.

Una cita equivocada es **peor que un número equivocado**, porque el número
equivocado se nota al compararlo con el fichero y la cita equivocada **presta
autoridad al error**. Un lector que confiara en esa línea «arreglaría» el campo
a `count - 1` y tendría razón según la autoridad citada y razón **contra esta
GPU**. El error queda lavado.

Corregido a la cabecera de esta generación y a su nombre:

```
#define RX550_SDMA_OP_GEN_PTEPDE 12   /* tonga_sdma_pkt_open.h:37 */
```

`tonga_sdma_pkt_open.h:37` es `SDMA_OP_GEN_PTEPDE 12`, y es la que incluye
`sdma_v3_0.c`, el fichero que corre.

## 2 · Por qué el nombre es el discriminador y no la decoración

Ambos headers definen el valor **12**, así que el byte emitido es idéntico y
aquí no se puede discriminar mirando la salida. El discriminador es la
**convención del `count`**, y el nombre la marca de forma consistente en los
seis emisores. Eso convierte «¿cuál es el nombre correcto?» en una pregunta con
respuesta verificable, que es lo que no tenía antes.

## 3 · La trampa de `vega10_sdma_pkt_open.h`, y por qué casi escribo un hallazgo falso

Esa cabecera define **tres** formas del paquete de op 12, cada una con un campo
`SUB_OP` en los bits 15:8 que selecciona `GEN` / `COPY` / `RMW` /
`COPY_BACKWARDS`:

```
  vega10_sdma_pkt_open.h:55-58    SDMA_SUBOP_PTEPDE_GEN 0, _COPY 1, _RMW 2, _COPY_BACKWARDS 3
  vega10_sdma_pkt_open.h:1753-56  SDMA_PKT_PTEPDE_COPY_HEADER_sub_op_mask 0xFF, _shift 8
  vega10_sdma_pkt_open.h:1742     SDMA_PKT_PTEPDE_COPY
  vega10_sdma_pkt_open.h:1815     SDMA_PKT_PTEPDE_COPY_BACKWARDS
  vega10_sdma_pkt_open.h:1899     SDMA_PKT_PTEPDE_RMW
```

Leí eso y estaba a punto de concluir que el op 12 de esta GPU necesitaba un
`SUB_OP` que el driver no escribe, con lo que la cabecera emitida estaría mal.
**Era falso, y lo falso estaba a un `sed` de convertirse en hallazgo.**

Lo que dice el emisor real de V3:

```
  sdma_v5_0.c:1217   ib->ptr[ib->length_dw++] = SDMA_PKT_HEADER_OP(SDMA_OP_PTEPDE);
```

`SDMA_PKT_HEADER_OP`, el macro **genérico**, cuyo campo `op` son los bits 7:0
(`tonga_sdma_pkt_open.h:55-56`) — no el macro por paquete con `SUB_OP`. **Ninguno
de los seis emisores usa los macros por paquete.** Esos macros describen una
superficie de despacho que este corpus nunca usa; usarlos emitiría `0x00000Cxx`
en vez de `0x0000000C`.

La lección operativa es la que ya está escrita en `AGENTS.md`: el payload de un
paquete lo define **lo que escribe el emisor**, no la cabecera donde se encontró
el nombre. Lo que quedaba después de leer los macros —que el emisor no los usa—
es lo único que mide, y es lo contrario de lo que la lectura rápida sugería.

## 4 · Dos defectos más que la medición destapó

**«Verbatim» era falso.** `rx550_pm4.c` describía su transcripción como
*«sdma_v4_0.c:1643-1659 verbatim»*, y al mismo tiempo, veinte líneas más abajo,
anotaba que ese no es el fichero que corre y que el `count` difiere. *Verbatim*
afirmaba identidad donde hay una diferencia medida de un campo. Retirado: la
transcripción es de `sdma_v4_0.c`, y **dos** campos difieren del fichero que
corre, el nombre del op y el `count`, en la misma dirección que la generación.

**La cita por número desnudo era ambigua.** El header decía *«see findings/035
for why the name is PTEPDE»*, pero **hay dos ficheros con el número 035**:

```
  035-block-size-tres-claims-y-un-log.md
  035-correccion-ptepde-es-polaris12.md     <-- el que trata del nombre
```

Una cita por número desnudo cuando el número está duplicado no apunta a nada.
Es la regla que ya existe en el proyecto, y este caso es el argumento de por
qué: **el duplicado se perdona mientras nadie cite, y aquí ya se citaba.**

## 5 · La cadena de cuál es la generación que corre

Sin esto, la tabla anterior sólo dice qué hacen seis ficheros, no cuál importa:

```
  vi.c:2107              case CHIP_POLARIS12:
  vi.c:2113              amdgpu_device_ip_block_add(adev, &sdma_v3_1_ip_block);
  sdma_v3_0.c:1693       const struct amdgpu_ip_block_version sdma_v3_1_ip_block =
  amdgpu_device.c:2136   case CHIP_POLARIS12:
  amdgpu_device.c:2143       adev->family = AMDGPU_FAMILY_VI;
  amdgpu_device.c:2145       r = vi_set_ip_blocks(adev);
  amdgpu_device.c:2149   default:  r = amdgpu_discovery_set_ip_blocks(adev);
```

POLARIS12 toma un `case` explícito que llama a `vi_set_ip_blocks()`. El
`default:` —que es quien llamaría a `amdgpu_discovery_set_ip_blocks()`, el que
selecciona `sdma_v4_0_ip_block` para `SDMA0_HWIP` 4.x— no se alcanza. La cadena
por líneas idénticas está verificada en `findings/115`–`120`.

El comentario anterior del driver describía esto como «el `default:` del switch en
`amdgpu_device.c:2145`». La línea 2145 es la **llamada** `vi_set_ip_blocks`, no el
`default:`, que está en 2149. El sentido era el correcto; la línea no.

## 6 · El hueco de las herramientas que esto deja abierto

`tools/treescope.py` verifica que una cita `fichero.c:NNN` **resuelva** contra el
árbol declarado. No verifica que el hallazgo citado **sostenga** la afirmación
para la que se cita. Aquí eso dos casos que ninguna herramienta separa:

- una cita que resuelve y además sostiene la afirmación;
- una cita que resuelve, está en el fichero correcto, y **no dice nada de lo que
  se le pide**.

La segunda clase es la que ha producido cuatro años de oscilación en este
nombre. Es observable mecánicamente —el término citado aparece o no en el
hallazgo citado— y por tanto automatizable, y no lo está. Queda declarado:

```
PENDIENTE=una cita puede resolver y no sostener la afirmacion, y ninguna
          herramienta lo distingue
  | HALLAZGO=188-el-nombre-del-op-12-y-la-cita-equivocada.md
  | ESTADO=NOT_DETERMINED
  | NECESITA=cross-check de que el termino citado (p.ej. GEN_PTEPDE) aparece
  |          en el hallazgo citado, NO solo de que el numero resuelve
  | ALCANZABLE_SIN_ROOT=si
```

## Lo que esto NO cambia

La emisión es correcta y no se modifica ningún byte. `rx550_pm4.h` gana el nombre
y la cita correctos; el valor sigue siendo 12, la cabecera sigue siendo
`0x0000000C`, y `test_pm4` sigue en **208 checks, 0 failures**.

Sigue sin establecerse que este paquete escriba una tabla de páginas en el
RX 550. Es el productor **PROVEN** en cuanto a qué fichero y qué convención
reproduce (`findings/043`, `findings/115`–`120`), y **`NOT_PROVEN`** en cuanto a
su efecto. `insmod` es NIVEL 4 y sigue pendiente de autorización
(`AGENTS.md` 76-82).

## Procedencia

```
medición propia    6 emisores del op 12 en 7.2.8, tabla completa arriba
tonga_sdma_pkt_open.h:37        SDMA_OP_GEN_PTEPDE 12   (cabecera de ESTA gen)
vega10_sdma_pkt_open.h:37       SDMA_OP_PTEPDE     12   (V3, la que NO corre)
tonga_sdma_pkt_open.h:55-56     SDMA_PKT_HEADER_op_mask 0xFF, op_shift 0
vega10_sdma_pkt_open.h:55-58    SDMA_SUBOP_PTEPDE_GEN/COPY/RMW/COPY_BACKWARDS
sdma_v5_0.c:1217-1225           emisor V3: macro GENÉRICO + count - 1
tools/mutate.py                 arnés, 8/8, y el mutante ptepde_count_menos_uno
                                lo detecta un check_eq con cita a (043)
findings/043, 044, 115-120      qué generación corre, verificada línea a línea
07-DRIVER/tests/test_pm4.c      208 checks, 0 failures
```

## CORRECCION POSTERIOR

Ninguna sobre lo afirmado arriba. La afirmación «nada observable cambia»
—presente en el comentario anterior de `rx550_pm4.h`— **era correcta en su
conclusión y no estaba medida en su premisa**. Aquí queda medida sobre seis
emisores, y lo que la vuelve correcta es un hecho que el comentario anterior no
mencionaba: que los seis usan el macro genérico y ninguno el de por paquete.
Por eso no se retira como errónea sino que se sustituye por su justificación.
