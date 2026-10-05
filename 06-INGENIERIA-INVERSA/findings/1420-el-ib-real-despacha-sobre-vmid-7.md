# 1420 — el IB real despacha sobre **VMID 7**, y el discriminante que lo identifica como anillo de gráficos está en un bit: `INDIRECT_BUFFER_VALID`

```text
AGENCIA=RX550-INVESTIGACION · WORK_CLASS=AGENT-RE-TOOLING
GENERADO=2026-10-04 · MEDIDO=EN ESTA HOST
ARTEFACTO=revkit/capturas/amdgpu_ring_gfx.txt   dwords 18..21
CORPUS=rx550-upstream-7.2.8 (solo lectura)

AFECTADO=gfx_v8_0.c:6075-6105      gfx_v8_0_ring_emit_ib_gfx      (SIN VALID)
         gfx_v8_0.c:6107-6139      gfx_v8_0_ring_emit_ib_compute  (CON VALID)
         cikd.h:317                INDIRECT_BUFFER_VALID = 1 << 23
         15 sitios vmid<<24 en el arbol, 6 generaciones          discriminante
         gmc_v8_0.c:1156-1162      first_kfd_vmid = 8

AFINA=1404, que habia dejado abierto quien configura los contextos 2-15
CORRIGE=mi propia atribucion: primero lo identifique como el emisor de compute
ESTADO=OBSERVADO-el-VMID · PROVEN-el-discriminante
```

## 0 · LO QUE HAY EN EL ARTEFACTO

`1412` midió que el anillo capturado estaba en reposo y que su única orden real es
un `PACKET3_INDIRECT_BUFFER` en el dword 18 de cada bloque. Los cuatro dwords:

```
  18  0xc0023f00   PACKET3_INDIRECT_BUFFER, count 2
  19  0x00278000   gpu_addr & 0xFFFFFFFC
  20  0x00000001   upper_32_bits(gpu_addr) & 0xFFFF
  21  0x07000158   control
```

Y la fuente, `gfx_v8_0_ring_emit_ib_gfx` (`gfx_v8_0.c:6075-6105`), literalmente
las cuatro escrituras:

```c
        amdgpu_ring_write(ring, header);
        amdgpu_ring_write(ring,
                          (ib->gpu_addr & 0xFFFFFFFC));
        amdgpu_ring_write(ring, upper_32_bits(ib->gpu_addr) & 0xFFFF);
        amdgpu_ring_write(ring, control);
```

con `control` construido en la línea 6088:

```c
        control |= ib->length_dw | (vmid << 24);
```

**El orden y la forma coinciden exactamente.** Dos valores salen del artefacto:

```
  ib->gpu_addr  =  0x0001_00278000
  control       =  0x07000158
      vmid << 24 ->  0x07000000   ->   vmid = 7
      resto      ->  0x000158     ->   length_dw = 344
```

## 1 · EL DISCRIMINANTE, Y POR QUÉ ME HACE FALLO

Cuando vi `control = 0x07000158` **leí primero** `gfx_v8_0_ring_emit_ib_compute`
(`gfx_v8_0.c:6113`), que es la línea que se parece:

```c
        u32 control = INDIRECT_BUFFER_VALID | ib->length_dw | (vmid << 24);
```

Y con `INDIRECT_BUFFER_VALID = (1 << 23)` (`cikd.h:317`), el valor del artefacto
**no encaja**: `0x07000158 & 0x800000 == 0`, y el bit 23 está limpio.

**Eso es un discriminante real, y no una rafia:** los dos emisores del árbol **se
distinguen por un bit**. MEDIDO sobre los quince sitios que construyen el control
con `vmid << 24`:

```
  ANILLO DE GRAFICOS   control |=  ib->length_dw | (vmid << 24)      SIN VALID
     gfx_v6_0.c:1934     gfx_v7_0.c:2215     gfx_v8_0.c:6088
     gfx_v9_0.c:5460     gfx_v10_0.c:8656    gfx_v11_0.c:6006
     gfx_v12_0.c:4522

  ANILLO DE COMPUTE   control  =  INDIRECT_BUFFER_VALID | ... | ...  CON VALID
     gfx_v7_0.c:2233     gfx_v8_0.c:6113     gfx_v9_0.c:5554
     gfx_v10_0.c:8686    gfx_v11_0.c:6036    gfx_v12_0.c:4541
     gfx_v9_4_3.c:2928   gfx_v12_1.c:3427   (este ultimo con PACKET3_INDIRECT_BUFFER__VALID)
```

**Seis generaciones, siete emisores de gráficos sin el bit, ocho de compute con
el bit, y ni una excepción.** El discriminante no es una coincidencia de un
fichero: es una regla del driver.

> **Y por eso el error se detecta solo:** me lleva a leer la fuente que me cuadraba,
> el valor no encajó, y el hueco señaló la función correcta. **Un desacuerdo entre
> artefacto y fuente, medido, es información; un desacorde que se «arregla»
> ajustando el artefacto es un agujero.**
>
> Es la diferencia entre `1412` §3, donde mi decodificador dio un cero falso y no
> había nada que lo contrastara, y aquí, donde el contraste era aritmética sobre
> un campo con nombre. **El mismo bucle, con y sin oráculo.**

## 2 · EL HECHO: LA GPU DESPACHÓ TRABAJO SOBRE EL VMID 7

Esto es lo que el artefacto establece, y es la primera observación de hardware de
este proyecto sobre **qué VMID se usa de verdad**:

```
  VMID en la palabra de control del IB            7        OBSERVADO
  ese VMID estaba en el rango que el driver
  reserva para amdgpu graficos/compute (1-7)?      SI, es el ultimo   PROVEN
  ese VMID esta en el rango que KFD usaria (8-15)? NO                PROVEN
  campo length del IB                              0x158 = 344       OBSERVADO
  direccion del IB                                 0x0001_00278000   OBSERVADO
 volumen de trabajo real por bloque                1                 OBSERVADO
```

**VMID 7 es el último del rango de amdgpu**, el contiguo a `first_kfd_vmid = 8`.
No es un VMID arbitrario: es exactamente el borde.

## 3 · POR QUÉ ESTO AFINA A `1404` Y LO DEJA MÁS CORTANTE

`1404` encontró, y dejó así:

```
  ENABLE_CONTEXT lo escribe   solo mmVM_CONTEXT0_CNTL y mmVM_CONTEXT1_CNTL
  y mmVM_CONTEXT{2..15}_CNTL no existen en ninguna cabecera GMC
  -> quien configura los contextos 2 a 15:   NOT_DETERMINED
```

Con esto, la pregunta deja de ser teórica:

> **La GPU despachó trabajo sobre el VMID 7, y en todo el corpus no hay una sola
> escritura a `mmVM_CONTEXT7_CNTL`.** Y el trabajo se ejecutó: el anillo encadena un
> `EVENT_WRITE_EOP` a una dirección de memoria después del IB.

**Eso no demuestra que el contexto esté bien configurado** —un IB puede
ejecutarse y fallar al traducir direcciones— pero **acota la pregunta a dos
hipótesis concretas**, y ambas son decidibles:

| hipótesis | qué implica | discriminante |
|---|---|---|
| **H1** el reset deja `ENABLE_CONTEXT = 1` en los contextos 2–15 | el driver **no necesita** escribirlos, y `1404` no es un hueco sino el diseño correcto | leer `mmVM_CONTEXT7_CNTL` y ver `ENABLE_CONTEXT` |
| **H2** el CNTL de los contextos 2–15 vive en la ventana **GC** (`0x0882–0x088f`) y otra ruta lo escribe | hay un escritor fuera de alcance, y `1404` sigue siendo un hueco real | leer `0x0888` (`CONTEXT7_CNTL` en GC) y ver si es distinto |

**Las dos son una lectura MMIO cada una, y las dos son en registros que `1128` ya
pidió para otro campo.** El viaje al nodo de runtime no crece: se le añaden dos
lecturas al mismo bloque.

> **Y hay una tercera salida que este hallazgo hace visible y que nadie había
> nombrado:** si `mmVM_CONTEXT7_CNTL` **no existe** en la ventana GMC (y
> `1404` probó que ningún header GMC lo publica), entonces **el concepto
> «CNTL por contexto» para 2–15 no aplica a esta ASIC tal como está escrito el
> driver**, y lo que hay que replicar es otra cosa. Eso no se responde leyendo
> código: se responde leyendo el registro.

## 4 · LO QUE NO SE AFIRMA

- **No se dice que el VMID 7 esté bien configurado.** Se dice que hubo un
  despacho sobre él. Si la traducción de direcciones estuviera mal, el IB se
  ejecutaría y daría basura o faults, y eso **no** se ve en un anillo: solo se ve
  en la salida.
- **No se afirma que `length_dw = 344` sean bytes o dwords.** El campo es
  `control[15:0]`, y el driver mete ahí `ib->length_dw` sin convertir. Que el
  hardware lo lea como bytes o como dwords es `NOT_PUBLISHED` en este corpus.
- **No se dice que este anillo sea representativo.** Es un anillo en reposo con
  un IB. `1412` §1 ya registró que el artefacto es una muestra de un caso, no un
  perfil de carga.
- **No se toca el artefacto.** Se lee.

## 5 · LO QUE ESTE HALLAZGO LE PASA AL INSTRUMENTO QUE FALTA

`1412` §6 dejó anotado que un catálogo de aliasing no resuelve el problema de
nombrar registros. Este hallazgo enseña **qué sí lo resuelve**, y es un
procedimiento de dos pasos que ya está medido:

```
  PASO 1   un campo con NOMBRE y VALOR en la fuente, no una direccion suelta
           -> discriminante aritmetico entre dos emisores
              ejemplo: INDIRECT_BUFFER_VALID, bit 23, presente en compute y
              ausente en gfx.  15 sitios, 6 generaciones, cero excepciones.

  PASO 2   un paquete con varios campos con nombre, en orden fijo
           -> atribucion por coincidencia de la TUPLA COMPLETA
              ejemplo: gpu_addr lo, gpu_addr hi, control.  Tres a la vez, no uno.

  PASO 3   lo que queda sin nombre son las direcciones aisladas, y eso es
           NOT_DETERMINED con motivo medido (1412 §5)
```

> **El orden importa: primero los campos, después las direcciones.** Al revés se
> obtiene un `grep` que devuelve el primer símbolo que encuentra y una conclusión
> falsa. Es el mismo orden que en `1412` §3, donde leí el campo equivocado del
> paquete equivocado y obtuve un cero.

## 6 · ESTADO

```
  ARTEFACTO revkit/capturas/amdgpu_ring_gfx.txt, dwords 18..21
     PACKET3_INDIRECT_BUFFER, count 2
     gpu_addr    0x0001_00278000          OBSERVADO
     control     0x07000158               OBSERVADO
        vmid     7                        OBSERVADO   <-- el dato nuevo
        length   0x158 = 344              OBSERVADO, unidades NOT_DETERMINED
     atribuido a gfx_v8_0_ring_emit_ib_gfx (gfx_v8_0.c:6075-6105)
        por los TRES dwords a la vez, en orden fijo          PROVEN
     y NO al emisor de compute: bit 23 (INDIRECT_BUFFER_VALID) ausente

  discriminante INDIRECT_BUFFER_VALID
     graphics   sin el bit    7 emisores, 6 generaciones     PROVEN
     compute    con el bit    8 emisores, 6 generaciones     PROVEN
     excepciones                                                     0

  afina a 1404
     hubo un despacho real sobre el VMID 7                OBSERVADO
     no hay escritura a mmVM_CONTEXT7_CNTL en el corpus    PROVEN
     H1 el reset lo habilita                              1 lectura MMIO
     H2 otro bloque lo escribe                            1 lectura MMIO
     H3 el CNTL por contexto no aplica a 2-15             1 lectura MMIO

  CORRIGE mi atribucion inicial (compute) en cuanto a
     un dato del artefacto no encajo con la fuente que yo preferia

  corpus  solo lectura
  GPU     INTACTA
  sudo    NO usado
```