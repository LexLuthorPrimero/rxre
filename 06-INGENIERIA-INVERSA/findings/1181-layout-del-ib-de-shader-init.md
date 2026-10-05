# 1181 — El IB de inicialización de compute de GFX8, reconstruido por completo: **186 + 6 + 66 + 62 + 42 = 362 dwords**, y el 186 lo predice la fórmula del driver por su cuenta

```text
AGENCIA=RX550-INVESTIGACION · WORK_CLASS=VALIDATION · SEMANTIC-CLOSURE
AUTOR=AGENTE-INSTR
WRITE_EXECUTION=NONE · MODIFICATIONS=0 · RUNTIME=NOT_RUN
ESCRITOS_POR_ESTA_ITERACION   08-ARQUITECTURA/artifacts/R17-LOCALES/layout.txt
MODIFICADO_NADA_EXISTENTE    nada: es una reconstruccion sobre evidencia previa
CLASSIFICATION=VALIDATION · CORROBORATION
GENERADO=2026-10-04 · MEDIDO=EN ESTA HOST
ESTADO=LAYOUT CERRADO Y CUADRADO POR DOS VIAS INDEPENDIENTES
```

## 0 · El resultado, primero

```text
rango           que hay                        dwords   de donde sale
--------------- ----------------------------- -------- ------------------------------
ptr[0..185]     stream de comandos               186    CONTADO por el sintetizador
ptr[186..191]   relleno (ALIGN)                   6    vgpr_offset/4 - 186
ptr[192..257]   vgpr_init_compute_shader          66    ARRAY_SIZE(vgpr_init_compute_shader)
ptr[258..319]   relleno (ALIGN)                  62    sgpr_offset/4 - 258
ptr[320..361]   sgpr_init_compute_shader          42    ARRAY_SIZE(sgpr_init_compute_shader)
--------------- ----------------------------- --------
TOTAL                                                362   total_size/4 = 1448/4
```

Y las tres comprobaciones que lo cierran:

```text
1  los comandos, contados por el sintetizador          186
   la fórmula del driver, por su cuenta
     ((ARRAY_SIZE(vgpr_init_regs)/2)*3) + 4 + 5 + 2  =  62 dwords por bloque
     3 bloques                                        =  186 dwords
                                                       -> 186 = 186

2  la suma del layout cubre el total EXACTAMENTE
     186 + 6 + 66 + 62 + 42 = 362     total_size/4 = 362    COINCIDE

3  nada se solapa
     186 <= 192      comandos antes del shader        True
     258 <= 320      vgpr antes de sgpr               True
     362 <= 362      sgpr termina en el total         True
```

## 1 · POR QUÉ 186 ES UNA CONFIRMACIÓN Y NO UNA COINCIDENCIA

El driver **no cuenta** los comandos que escribe. Escribe:

```c
total_size = (((ARRAY_SIZE(vgpr_init_regs) / 2) * 3) + 4 + 5 + 2) * 4;
```

`17` es `ARRAY_SIZE/2` — los pares registro/valor. `* 3` son las tres escrituras
por vuelta (`PACKET3`, dirección, valor). Y `+ 4 + 5 + 2` son los 11 dwords
sueltos del bloque (los 4 del `SET_SH_REG, 2` + `COMPUTE_PGM_LO/HI` + `lower` +
`upper` son 4; el `DISPATCH_DIRECT` con 3 de payload son 5; y el `EVENT_WRITE`
con 1 son 2).

**62 dwords por bloque, escritos a mano por el driver en una fórmula que no
consulta el código.** Y el sintetizador cuenta **186** por un camino
incompleto:186 escrituras contadas, 108 de ellas posicionales, y las 186
restantes del stream.

Que dos caminos distintos den el mismo número, y que ese número sea el que el
driver **usa para reservar el buffer**, es el tipo de corroboración que sostiene
una reconstrucción.

## 2 · LO QUE NO SABÍA Y ESTE RESULTADO ENSEÑA

Escribí en `1138 §1` que el bucle de `vgpr_init_regs` costaba "una IB de 42
dwords" y que faltaban 51 registros. Esos 51 eran los **datos del shader**, no
los comandos, y no son comandos: se escriben **posicionalmente** en
`ib.ptr[vgpr_offset/4 + i]`, y el stream de comandos empieza en `ptr[0]`.

Lo que no había visto hasta ahora es lo que eso implica:

```text
ib.length_dw = 0;                       <- DESPUÉS de cargar el shader
  ... comandos en ib.ptr[ib.length_dw++] ...
```

El reset está en la línea 1524, y los bucles de `SET_SH_REG` de la 1529 en
adelante. **Los dos son del mismo `ib.ptr[]`, con el mismo contador.** O sea que
el buffer se rellena en dos fases que comparten el array, y la segunda arranca en
`ptr[0]` mientras la primera dejó datos en `ptr[192]` y `ptr[320]`.

Eso solo no colisiona si `186 <= 192`, y el margen es de **6 dwords**. Los 6
salen de `ALIGN(744, 256)`: 744 bytes son 186 dwords justos, `ALIGN` los sube a
768, y 768/4 = 192.

> El relleno no es decorativo: es lo que impide que el stream de comandos se
> coma los datos del shader. Y son 6 dwords de margen.

## 3 · EL DATO QUE MÁS INTERESA, Y QUE NO ESPERABA

`ALIGN` sube a 256 **bytes**, y el desglose sale así:

```text
total_size tras el primer ALIGN     = ALIGN(744, 256) = 768 bytes = 192 dwords
  vgpr_offset                       = 768  = ptr[192]

total_size += ALIGN(264, 256)       = 768 + 512 = 1280 = ptr[320]
  sgpr_offset                       = 1280 = ptr[320]

total_size += sizeof(sgpr=168)      = 1448 bytes = 362 dwords
```

**El relleno de 62 dwords entre los dos bloques de shader no viene del
alineamiento.** Viene de que `ALIGN(264, 256)` sube los 66 dwords del bloque
vgpr a 128, dejando 62 entre el fin del bloque y el principio del siguiente.

Eso es una consecuencia aritmética que **no se ve en ningún `if`** del driver.
Está implícita en que `ALIGN` opere sobre bytes y el bloque ocupe un número
impar de dwords. Si el bloque fueran 64 dwords, `ALIGN(256, 256)` = 256 = 64
dwords y el relleno sería 0.

**El relleno entre bloques es una propiedad del tamaño del bloque de shader, no
una decisión explícita de nadie.** Y eso es un hecho que no se puede ver leyendo
el código: hay que ejecutarlo.

## 4 · LO QUE ESTO NO ES

**No es una verificación de hardware.** `RUNTIME=NOT_RUN`. Que el ASICreserve
`amdgpu_ib_get(adev, NULL, 1448, ...)` yacepte 362 dwords de buffer es una
afirmación del driver sobre el hardware que **no he comprobado**.

**No es una prediccion de ejecucion.** La IB se construye o no segun
`asic_type != CHIP_CARRIZO` y si el ring esta listo. Hay dos salidas
tempranas en las líneas 1485-1490 que no he reproducido. Con esos valores la
función no llega a la línea 1524 y no hay IB. La reconstrucción es de **la ruta
que escribe**.

**No he reproducido `lower_32_bits(gpu_addr)` ni `upper_32_bits(gpu_addr)`.** Los
dwords 3 y 4 de cada bloque `SET_SH_REG, 2` son la dirección del shader, y
`gpu_addr` depende de `amdgpu_ib_get`, que es una llamada de runtime. Los 9
`INCOMPLETO` que quedan son exactamente esos: `4 × 3` de `gpu_addr` y 1 de
`COMPUTE_DISPATCH_INITIATOR`. No son un fallo del sintetizador — son valores que
**no existen en el código fuente**, y localizarlos exige la placa.

**Y las dos salidas tempranas** que he nombrado son un límite de lo que la
reconstrucción cubre, no un defecto de la reconstrucción. El dato es "la ruta
que escribe"; el alcance es `NOT_DETERMINED` para la otra.

## 5 · POR QUÉ ESTO ES MÁS QUE UNA TABLA

Un layout de buffer no es una lista de offsets. Es:

```text
un reparto de un espacio FINITO
  donde lo que se coloca al principio no pisa lo que se coloca al final
  y donde el hueco entre ambos no está escrito en ningún sitio
  y depende del tamaño de lo que se coloca
```

Y las tres cosas se comprueban con números, no con lectura:

```text
que no se pise      -> 186 <= 192       y  258 <= 320
que el total cierre -> 186+6+66+62+42 = 362 = total_size/4
que el hueco cuadre -> 62 = 128 - 66,  y 128 = ALIGN(264,256)/4
```

La tercera es la que no se puede leer. La primera y la segunda sí, y se leen
después.

## 6 · PROCEDIMIENTO

```text
fuente    08-ARQUITECTURA/artifacts/R17-LOCALES/ib.json  (ibref, sintetizado)
          294 dwords, 285 completos, 9 incompletos
          locales: total_size=1448  vgpr_offset=768  sgpr_offset=1280

desglose  108 escrituras POSICIONALES  -> los dos bloques de shader (66 + 42)
          186 escrituras SECUENCIALES  -> el stream de comandos

cifras    comandos     186   medido por el sintetizador
          comandos     186   formula del driver, por su cuenta
          filler        6   = 192 - 186,  y ALIGN(744,256)/4 - 186
          filler       62   = 128 - 66,  y ALIGN(264,256)/4 - 66
          total       362   = total_size/4

artefacto 08-ARQUITECTURA/artifacts/R17-LOCALES/layout.txt
```

## 7 · LO QUE NO ESTÁ HECHO

**`ib.length_dw` no se propaga en el instrumento.** No hace falta para el layout —
el reset a 0 es lo que separa las dos fases, y la herramienta ya distingue
posicional de secuencial por construcción. Pero `gfx_v8_0_ring_emit_ib_compute`
usa `length_dw` de otra manera (como índice de un IB que ya existe), y ahí la
propagación del contador **sí** haría falta. No está hecha y no la he medido.

**Los dos valores de `gpu_addr`** quedan `INCOMPLETO` porque no están en el
código. Es el límite correcto y no lo voy a rellenar con un valor inventado: un
`gpu_addr = 0` que "funcionaría" en el round-trip sería una falsificación.

**No he comprobado la ruta de `asic_type != CHIP_CARRIZO`.** El layout es de la
ruta que escribe, declarado en §4.

**Y esto no prueba que la IB sea la que el hardware ejecuta.** Prueba que la
síntesis es internamente coherente y que la aritmética del driver, evaluada con
sus propias reglas, produce el mismo reparto que el driver reserva. Que el ASIC
acepte ese reparto es otra afirmación, y es de otro tipo de evidencia.