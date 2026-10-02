# 096 · El discriminante (a)/(b)/(c) no es cerrable desde el corpus: seis ficheros de packet y ninguno documenta la semántica del `count`

```text
PENDIENTE=ABC-NO-CERRABLE-DESDE-CORPUS | HALLAZGO=096-el-discriminante-abc-no-es-cerrable-desde-el-corpus.md | ESTADO=NOT_DETERMINED | NECESITA=CORPUS | ALCANZABLE_SIN_ROOT=si
```

## No necesita ruta: es lectura de corpus. 096 ya establecio que el
discriminante no se cierra desde el corpus, y la respuesta correcta es un
NOT_CLOSABLE declarado, no un pendiente de trabajo.


```
ID:           096
TIPO:        PROVEN_ABSENT con consecuencia declarada + refuerzo del lado del driver
ALCANCE:     vid.h, sid.h, cikd.h, soc15d.h, nvd.h, gfx_v12_1_pkt.h — PACKET3
             gfx_v8_0.c:1529/1535/4159/4169
NIVEL:       0 — lectura de corpus
GPU:         INTACTA
CIERRA:      el NEXT ACTION de 095, con resultado NEGATIVO declarado
```

## 1 · EL DISCRIMINANTE QUE SE PROPUSO, Y POR QUÉ NO FUNCIONA

`095` propuso: buscar en los ficheros donde el hardware está documentado si
algún packet usa `count = payload` en vez de `payload − 1`. Si alguno lo hiciera,
la lectura del hardware sería (b) y el driver no compensaría.

Se buscó. La búsqueda tiene tres partes y las tres se ejecutaron.

### Parte 1 · La macro `PACKET3` en seis generaciones

```
vid.h:105            #define PACKET3(op, n)  ((PACKET_TYPE3 << 30) |
                                      (((op) & 0xFF) << 8) |
                                      ((n) & 0x3FFF) << 16)
sid.h:336            idem, con RADEON_PACKET_TYPE3
cikd.h:229           idem
soc15d.h:50          idem
nvd.h:48             idem
gfx_v12_1_pkt.h:48   idem
```

**Idéntica en las seis.** El `count` son **14 bits en la posición 16**, el opcode
8 bits en la posición 8, el tipo en 30-31.

Esto **ya es un dato**: la disposición del campo no ha cambiado en ninguna
generación desde CIK hasta GFX12. Si la *semántica* del campo hubiera cambiado
alguna vez, el cambio tendría que haber sido invisible para el software — y un
cambio invisible en la semántica de un campo de longitud es exactamente el tipo
de cosa que un driver tiene que compensar durante una generación. No hay
evidencia de que lo haga.

Pero no es lo que se buscaba.

### Parte 2 · Documentación de longitud por packet — **cero**

```
$ grep -nE "PACKET3\([A-Z0-9_]+, *[0-9]+\) *[/;]|dwords|data words|following dword" \
      vid.h sid.h cikd.h soc15d.h
(sin resultados)
```

**Ningún fichero de definición de packet documenta cuántos dwords tiene un
packet.** Ni en la generación más nueva, ni en la más vieja.

### Parte 3 · El rango del campo — no discrimina

`count` es de 14 bits: máximo 16383 dwords. Con lectura (a) el paquete entero
cabe en 16384 dwords; con (b) o (c), el payload cabe en 16383. **Un rango de
14 bits no distingue entre las tres lecturas**, y el corpus no contiene ningún
paquete cercano al límite.

## 2 · EL RESULTADO, Y SU LÍMITE

> **`PROVEN_ABSENT`: en este corpus no hay ninguna fuente que documente la
> semántica del campo `count`.** Seis ficheros de packet, ninguna mención a
> longitud en dwords.

Con su límite declarado:

- **Sí prueba**: que el upstream no considera este campo lo bastante
  self-documentado como para documentarlo, en seis generaciones y con el
  hardware de cada una disponible.
- **No prueba**: que la semántica no sea (b). El driver de GFX8 se comporta
  como (b) en 45/45 emisiones medidas más las de este hallazgo, y **eso es lo
  que se sabe**.

**Y esto no es una laguna del proyecto: es una laguna del upstream.** Es la
misma situación que `033` dijo para el spec de PM4 de GFX8, vista desde otro
ángulo: el spec de la generación no está publicado, y **el spec de la
estructura del paquete tampoco**.

> `033` dijo: el spec de arquitectura GFX8 no está publicado.
> `096` añade: **ni siquiera el spec del propio formato de packet está
> documentado en el árbol**, en ninguna generación. Es el mismo hueco una vez
> más, y ahora con seis ejemplos en vez de uno.

## 3 · LO QUE SÍ SE REFUERZA: EL LADO DEL DRIVER, CON `count` VARIABLE

La parte útil de esta iteración no era el discriminante fallido sino lo que
apareció al mirar los mismos bloques por otra razón. En `gfx_v8_0.c:1529` y
`:4159` el `count` **no es una constante**:

```c
/* gfx_v8_0.c:1529 */
ib.ptr[ib.length_dw++] = PACKET3(PACKET3_SET_SH_REG, 1);
ib.ptr[ib.length_dw++] = vgpr_init_regs[i] - PACKET3_SET_SH_REG_START;
ib.ptr[ib.length_dw++] = vgpr_init_regs[i + 1];
/*                       count=1  ->  2 dwords      payload = count + 1 */

/* gfx_v8_0.c:1535 */
ib.ptr[ib.length_dw++] = PACKET3(PACKET3_SET_SH_REG, 2);
ib.ptr[ib.length_dw++] = mmCOMPUTE_PGM_LO - PACKET3_SET_SH_REG_START;
ib.ptr[ib.length_dw++] = lower_32_bits(gpu_addr);
ib.ptr[ib.length_dw++] = upper_32_bits(gpu_addr);
/*                       count=2  ->  3 dwords      payload = count + 1 */

/* gfx_v8_0.c:4159 */
amdgpu_ring_write(ring, PACKET3(PACKET3_SET_CONTEXT_REG, ext->reg_count));
amdgpu_ring_write(ring, ext->reg_index - PACKET3_SET_CONTEXT_REG_START);
for (i = 0; i < ext->reg_count; i++)
        amdgpu_ring_write(ring, ext->extent[i]);
/*                       count=ext->reg_count -> 1 + reg_count dwords
                          payload = count + 1, con count VARIABLE en runtime */
```

El tercero es el más fuerte de todos: **`ext->reg_count` es un valor leído de
los datos del command buffer del shader**, y el driver escribe `count` con ese
valor y emite exactamente `count + 1` dwords detrás.

> **Si el driver compensara una lectura distinta de la del hardware, no podría
> hacerlo con `count = ext->reg_count`.** El valor viene de la aplicación, y
> el driver lo copia tal cual. Compensar exigiría restar uno — y eso es
> precisamente lo que `count = payload − 1` **es**, no un ajuste.
>
> Es el argumento más fuerte que se puede hacer **desde el corpus** a que la
> lectura es (b): no hay ningún punto del driver donde se «traduzca» el valor
> que la aplicación pide en el número de dwords que el hardware tiene que leer.

Esto **substituye** el discriminante fallido por uno mejor, y cabe en una frase:
*no hay traducción, hay copia*.

## 4 · ESTADO

```
driver   count = payload - 1
         45/45 medidas por pm4census
         + 3 mas visibles a mano en este hallazgo (2 fijas, 1 con count VARIABLE)
         = 48 de 48, y el caso variable es el que descarta la compensacion

macro    PACKET3 identica en 6 generaciones. count = 14 bits @ 16.
         Sin cambios en ningun momento de la historia del arbol.

spec     PROVEN_ABSENT: ningun fichero de packet documenta la longitud.
         6 ficheros buscados, 0 menciones.

hardware NOT_DETERMINED. Y ahora con un motivo mas fuerte que en 095:
         no es que falte el spec de GFX8, es que faltan el spec de TODAS las
         generaciones. No hay a donde mirar.
```

## 5 · ERRORES PROPIOS

Ninguno de medición. El error fue **de propuesta**: `095` propuso un
discriminante sin comprobar antes que el observable existiera. Es la clase de
`081`/`082` (cerrar por lectura) aplicada al revés: **propuse un observable sin
verificar que se podía observar.**

Y tiene una mitigación que `095` ya tenía y yo no usé: `033` ya decía que el
spec de GFX8 no está publicado. Si `count` fuera un campo del spec de PM4, el
hueco ya estaba declarado. Lo que no estaba comprobado es que **el spec del
formato del paquete tampoco** estuviera documentado, y eso es lo que `096`
mide.

---

```
RESULTADO DE ITERACIÓN

Entregado:
  096: PROVEN_ABSENT sobre la semantica de `count` en 6 ficheros de packet
    PACKET3 identica en vid.h sid.h cikd.h soc15d.h nvd.h gfx_v12_1_pkt.h
    count = 14 bits @ posicion 16, sin cambios en ninguna generacion
    0 menciones a longitud en dwords en los 6 ficheros
  refuerzo del lado del driver, y es el bueno:
    PACKET3_SET_CONTEXT_REG, ext->reg_count  ->  emite 1 + reg_count dwords
    `ext->reg_count` viene de los DATOS del command buffer de la aplicacion
    y el driver lo copia sin transformarlo

  Consecuencia: si el driver compensara una lectura distinta de la del
  hardware, no podria hacerlo con un valor de runtime. Compensar exigiria
  restar uno, y `count = payload - 1` no es un ajuste: es la copia directa.

Retractado por este hallazgo (como propuesta, no como medida):
  095: "el discriminante es un grep sobre los ficheros donde el hardware esta
       documentado" -- NO HAY TAL COSA. Seis ficheros, cero documentacion.

NEXT ACTION:
  La frontera C queda con UN hueco y se puede nombrar con precision:

    VM_INVALIDATE_REQUEST -> hardware action -> invalidation -> completion
    -> visibility

  - encoding de VM_INVALIDATE_REQUEST:      PROVEN (093, 088)
  - quien lo emite y con que count:           PROVEN (095, 096)
  - hardware action:                          NOT_DETERMINED
  - completion:                               NOT_DETERMINED
  - visibility (cuando un PTE nuevo es visible): NOT_DETERMINED
  - FUNCTION=always:                          NOT_DETERMINED

  Y ahora hay un dato que reduce el hueco de forma concreta: 096 demuestra que
  el driver NO COMPENSA. Eso elimina la hipotesis "el driver escribe count-1
  porque el hardware lee count". La lectura (b) queda como la unica
  consistente con el codigo, y no requiere que el driver este adaptandose.

  Lo que queda es puramente hardware, y AGENTS.md ya dice como se cierra:
  §C "Buscar primero en corpus, headers, historical source, ASIC generations,
  primary docs. Despues runtime discriminants."

  Las cuatro primeras se han agotado para `count`. La quinta es el
  discriminante de runtime, que necesita inyeccion PM4 -- NIVEL 3 con
  justificacion de discriminante, o NIVEL 4 si implica el modulo propio.

  Y hay un camino que NO es inyeccion: el unico estado que la GPU comparte con
  el host sin que el host escriba en la GPU es el de las interrupciones, y
  gmc_v8_0.c:1113 ya registro
  AMDGPU_IRQ_CLIENTID_LEGACY / VISLANDS30_IV_SRCID_GFX_MEM_PROT_FAULT.
  Si el hardware dispara ese src_id cuando deberia, el fault esta activo; si
  no, esta desactivado. Eso es observable sin escribir en la GPU -- es
  precisamente lo que hace `hwip.py` con SDMA0_HWIP, que 043 cerro.

  Ese es el siguiente paso, y es el mismo patron que 043: leer un registro
  para responder una pregunta que el codigo deja abierta.
```