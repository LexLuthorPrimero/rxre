# 1228 — `ENG_SEL` está en `<<25` en GFX8, GFX9 y GFX10, y en `<<28` solo en GFX12.1. Y el `PASID` de 2 bits está **reproducido en los 4 headers**, así que no es un defecto de GFX8

```text
AGENCIA=RX550-INVESTIGACION · WORK_CLASS=CLOSE-OUT · CROSS-LINEAGE
AUTOR=AGENTE-INSTR
WRITE_EXECUTION=NONE · GPU=NONE TOUCHED · RUNTIME=NOT_RUN
DISPOSITIVO_TOCADO=NINGUNO · ni 0000:01:00.0 (1002:699f) ni 0000:00:02.0 (8086:0412)
ESCRITOS_POR_ESTA_ITERACION   ninguno (solo lectura)
CIERRA   1227 §5:  la contradiccion de PASID  y  la acotacion que propuse
CORRIGE  mi propio parseo,  que dijo <<28 para GFX9 y GFX10 cuando la fuente
         dice <<25 en los dos
DESRULEO LA CONTRADICCION DE PASID NO ES UN DEFECTO DE GFX8:  es uniforme en
         los 4 headers del paquete,  y eso la saca del ambito de la RX550
GENERADO=2026-10-06 · MEDIDO=EN ESTA HOST
```

## 1 · Cuáles headers declaran `QUERY_STATUS`

```text
  header              generacion   opcode   campos
  vid.h               GFX8           0xA4     6/6
  soc15d.h            GFX9           0xA4     6/6
  nvd.h               GFX10          0xA4     6/6
  gfx_v12_1_pkt.h     GFX12.1        0xA4     6/6
  --------------------------------------------------------------------------
  cikd.h              GFX7           —        0/6
  sid.h               GFX6/7         —        0/6
```

`cikd.h` y `sid.h` no declaran ni el opcode ni ningún campo. **El paquete no existe antes de
GFX8.** Eso es un dato nuevo y limpio: no es que el linaje viejo discrepe, es que no lo tiene.

Y el opcode es `0xA4` en los cuatro, sin una sola excepción.

## 2 · Los desplazamientos, leídos de la fuente y no de un parseo

Esta es la tabla que importa, leída con `grep -n` sobre las líneas literales:

```text
  campo              vid.h(8)  soc15d(9)  nvd(10)  gfx_v12_1(12.1)
  --------------------------------------------------------------------
  CONTEXT_ID          << 0       << 0       << 0       << 0
  INTERRUPT_SEL       << 28      << 28      << 28      << 28
  COMMAND             << 30      << 30      << 30      << 30
  PASID               << 0       << 0       << 0       << 0
  DOORBELL_OFFSET     << 2       << 2       << 2       << 2
  ENG_SEL             << 25      << 25      << 25      << 28      <-- el unico que se mueve
```

**Cinco de los seis desplazamientos son idénticos en los cuatro headers.** El sexto,
`ENG_SEL`, está en `<<25` en tres y en `<<28` en uno solo.

**GFX8 está en la mayoría de tres.** El único que se aparta es `gfx_v12_1_pkt.h`, o sea
**GFX12.1**. Y por la regla del grafo de includes que vengo aplicando: para la RX550 vale lo que
diga `vid.h`, y `vid.h` está de acuerdo con GFX9 y GFX10.

## 3 · El cambio de GFX12.1 es coherente, y por eso no es una errata

`DOORBELL_OFFSET` no tiene un final propio: **su borde superior lo define el desplazamiento de
`ENG_SEL`**, porque son los dos campos contiguos del mismo dword.

```text
  DOORBELL_OFFSET ocupa [ENG_SEL-1 : 2]   ->  anchura = ENG_SEL - 2

  GFX8 / GFX9 / GFX10    ENG_SEL=25   DOORBELL_OFFSET = [24:2]  = 23 bits
  GFX12.1                ENG_SEL=28   DOORBELL_OFFSET = [27:2]  = 26 bits
```

Quien movió `ENG_SEL` de 25 a 28 **amplió `DOORBELL_OFFSET` de 23 a 26 bits como consecuencia
automática**, porque el segundo campo se define por el primero. Eso es exactamente la firma de
un cambio de generación deliberado, no la de un número tecleado mal: una errata en `ENG_SEL` sola
habría dejado a `DOORBELL_OFFSET` con una anchura arbitraria, y aquí no hay arbitrariedad, hay
una dependencia.

Y es coherente con `1205`, donde quedó escrito que el máximo de `DOORBELL_OFFSET` depende de
`num_compute_rings`, que es runtime. **Un campo cuyo techo es runtime necesita más bits, no
menos**: por eso GFX12.1, con más colas de cómputo, le da 26 en vez de 23.

## 4 · `PASID`: la contradicción de `1227` sale del alcance de la RX550

`1227 §5` dejó registrado:

```text
  vid.h:439   la prosa dice "CONTROL2"  en singular  ->  un dword
  vid.h:450   PASID           << 0
  vid.h:452   DOORBELL_OFFSET << 2
  =>  PASID queda en [1:0],  dos bits.  Un PASID de 2 bits no puede ser un PASID.
```

Ahora se añade el dato decisivo:

```text
  PASID << 0   con   DOORBELL_OFFSET << 2   esta en LOS CUATRO headers
```

**Es idéntico en los cuatro.** No es una errata de `vid.h` ni un descuido de la generación GFX8:
es una propiedad de la familia de headers entera, reproducida en GFX8, GFX9, GFX10 y GFX12.1.

Eso **acota** la contradicción en vez de dejarla abierta, y la deja en dos salidas, ninguna de
las cuales es un defecto de la RX550:

```text
  a)  /* CONTROL2a */ y /* CONTROL2b */  de vid.h:449,451  designan DOS DWORDS
      distintos,  no dos mitades del mismo.  Entonces la prosa,  que dice
      "3. CONTROL2" en una sola linea,  esta abreviada y omite un dword.

  b)  la prosa dice bien y hay un solo CONTROL2,  entonces PASID ocupa [1:0]  y
      la macro esta mal en los cuatro headers.
```

**Entre las dos no se puede decidir todavía**, y hay una razón de peso para no hacerlo rápido:
`PASID` tiene **cero emisiones** en los seis puntos de `QUERY_STATUS` del driver, y ninguno de
esos seis pertenece a GFX8. No hay ni una sola escritura en el árbol con la que contrastarla.

Lo que sí queda cerrado es lo que importa para el target:

```text
  para la RX550  vid.h  es la autoridad,  y dice  PASID <<0, DOORBELL_OFFSET <<2
                 ENG_SEL <<25,  con DOORBELL_OFFSET de 23 bits
  GFX8 esta de acuerdo con GFX9 y GFX10 en los seis campos
```

Así que la lectura operativa para construir no depende del nudo: **si vas a escribir
`PASID`, el driver no te da ningún ejemplo de cómo se usa, y el header no te da un ancho
creíble.** Eso es `NOT_DETERMINED` con el motivo escrito, no un hueco que rellenar de memoria.

## 5 · Autocrítica: dos veces que el parseo y la fuente no coincidieron

En este mismo hallazgo pasó dos veces, y las dos se resolvieron leyendo la línea:

```text
  (a) el primer regex  (  #define\s+PACKET3_QUERY_STATUS_...  )  devolvio una
      tabla de seis "None" y las seis filas de guiones.  Todo vacio,  pero con
      formato de tabla,  que es lo que hace que un fallo parezca un resultado.
      Motivo:  en vid.h el # y el define estan separados por ESPACIOS
      (#              define ...).   septima vez con la misma clase de fallo.

  (b) el segundo parseo,  ya sin regex  (  troceando la linea  ),  devolvio
      ENG_SEL << 28 para soc15d.h y nvd.h.  La fuente dice << 25 en los dos.
      Un solo header se aparta,  no tres,  y la conclusion cambia entera:
      "tres headers coinciden"  ->  "GFX8 esta en la mayoria de tres"
      frente a  "GFX8 es el unico que se aparta".

  El segundo casi se cuela.  Si no hubiera releido las lineas literales con
  grep,  el hallazgo habria dicho que GFX8 es el outlier  cuando es el que
  esta de acuerdo con dos de los tres.
```

La defensa que funciona en las dos: **si la conclusion depende de un numero, la linea de
origen se lee.** No el agregado, la linea.

## 6 · Procedimiento

```text
PREGUNTA   ¿ENG_SEL se aparta en GFX8?  y  ¿la contradiccion de PASID es de GFX8?
FUENTES    las 3 lineas de QUERY_STATUS en los 4 headers que lo declaran,
            leidas con grep -n y cat -A para ver el espaciado real
           presencia/ausencia del opcode y de los campos en cikd.h y sid.h
MEDIDO     4 headers declaran el paquete (GFX8, 9, 10, 12.1),  opcode 0xA4 en los 4
           cikd.h y sid.h no declaran nada:  el paquete no existe antes de GFX8
           5 de 6 desplazamientos identicos en los 4 headers
           ENG_SEL:  <<25 en vid.h/soc15d.h/nvd.h      <<28 en gfx_v12_1_pkt.h
           =>  GFX8 esta en la mayoria de tres,  no es el outlier
           DOORBELL_OFFSET = [ENG_SEL-1 : 2],  anchura ENG_SEL-2
           =>  23 bits en GFX8/9/10,  26 bits en GFX12.1,  y el uno move el otro
           PASID <<0 con DOORBELL_OFFSET <<2 esta en los CUATRO headers
           =>  la contradiccion es de la familia de headers,  no de la RX550
CONTRADICCION  sigue NOT_DETERMINED entre (a) CONTROL2 son dos dwords y la
           prosa abrevia,  y (b) la prosa acierta y PASID es erroneo en los 4.
           Motivo de no cierre:  PASID tiene 0 emisiones,  y ninguna de las 6
           pertenece a GFX8.  No hay escritura en el arbol con la que contrastarla.
DISPOSITIVO  NINGUNO.  i915 y amdgpu intactos.
RUNTIME      NOT_RUN
LO QUE SIGUE
  - item 10 de la cola:  cuanto de los 51 paquetes sin estructura se determina
    desde AMDGPU/, uvd_v6_0.c y vce_v*.c
  - item 11:  declarar SATURATED el frente PM4 con el motivo escrito
  - item 12:  una lectura controlada sobre 0000:01:00.0.  Cerraria el ENG_SEL de
    25 bits de esta RX550,  que hasta ahora solo consta de 4 headers  ninguno de
    los cuales es el hardware
```