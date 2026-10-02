# 115 · `rx550_pm4_indirect` no era una derivación: el fichero correcto estaba a una tabla de distancia

`CLASSIFICATION=METHODOLOGY` · `TRACK=STATIC` · `WORK_CLASS=READ_ONLY/EVIDENCE`
`WRITE_EXECUTION=OWN_DRIVER_ONLY` · `MODIFICATIONS_CORPUS=0` · `RUNTIME=NOT_RUN` · `GPU INTACTA`
`HERRAMIENTA_NUEVA=tools/hcconsist.py` (`TOOL_VALIDATED`, 14 vectores)
`CONTINUES=114` · `CERRADO_POR=043,046` · `REFINA=043`

## Cuestión principal

`rx550_pm4_indirect()` estaba marcada `PROVEN_DERIVED` y no `PROVEN`, y la
razon era buena y estatica: el fichero del que se copio el cuerpo,
`sdma_v4_0.c`, **no corre en Polaris12**, según
`043-vuelta-atras-035-y-036-leian-el-asic-equivocado.md:27-37` y
`046-la-version-de-ip-que-nunca-se-consulta.md:69-75`. Derivar de un fichero
que no corre obliga a marcar derivado. ¿Es inevitable?

## Criterio de terminación

Localizar el emisor que **sí** corre en esta placa y comparar su cuerpo con
la transcripción, línea a línea. **Cumplido: 20 de 20 líneas idénticas.**

## Respuesta

La cadena de procedencia, completa y trazable:

```
vi.c:2106-2113           case CHIP_POLARIS10/11/12/VEGAM:
                          amdgpu_device_ip_block_add(adev, &sdma_v3_1_ip_block);
sdma_v3_0.c:1693-1699    sdma_v3_1_ip_block -> .funcs = &sdma_v3_0_ip_funcs
sdma_v3_0.c:422-441      sdma_v3_0_ring_emit_ib   <- el emisor de ESTA placa
```

Y la comparación, hecha con `diff` y no a ojo:

```
sdma_v3_0.c:422-441   20 líneas
sdma_v4_0.c:806-825   20 líneas
idénticos SIN normalizar:                     False
idénticos normalizando el prefijo de versión:  True
```

La única diferencia es `v3_0` contra `v4_0` en el nombre de la función y en
el del helper NOP que llama. Todo lo demás —`AMDGPU_JOB_GET_VMID(job)`,
`sdma_*_ring_insert_nop(ring, (2 - lower_32_bits(ring->wptr)) & 7)`,
`SDMA_PKT_HEADER_OP(SDMA_OP_INDIRECT) | ..._VMID(vmid & 0xf)`,
`lower_32_bits(ib->gpu_addr) & 0xffffffe0`, `upper_32_bits(...)`,
`ib->length_dw`, dos ceros finales— es el mismo texto.

Los valores del header coinciden por separado:

```
tonga_sdma_pkt_open.h:29     #define SDMA_OP_INDIRECT  4
vega10_sdma_pkt_open.h:29    #define SDMA_OP_INDIRECT  4
tonga_sdma_pkt_open.h:1649   SDMA_PKT_INDIRECT_HEADER_vmid_mask   0x0000000F
tonga_sdma_pkt_open.h:1650   SDMA_PKT_INDIRECT_HEADER_vmid_shift  16
```

`0xF` en 16 es **VMID en 19:16**, que es exactamente lo que escribe la
función propia.

**Veredicto: `PROVEN`.** La derivación era real —el cuerpo se copió de
`sdma_v4_0.c`— pero **innecesaria**, porque el fichero que sí corre emite los
mismos bytes. El `PROVEN_DERIVED` no era una cautela: era una prudencia sin el dato para cerrar, y se quedó en `PROVEN_DERIVED` porque eso es más honesto que fingir. El dato estaba a **una tabla de distancia**: un `grep` de qué `ip_block` monta `vi.c`.

## La asimetría de procedencia que queda viva

El driver propio cita `vega10_sdma_pkt_open.h` en `rx550_pm4.h:241-243`, y el
SDMA de esta placa incluye **`tonga_sdma_pkt_open.h`**. Mismo valor, distinta
procedencia: la clase exacta de
`041-herramientas-de-procedencia-y-auditoria.md:12`. No se corrige aquí porque
el valor es correcto y corregirlo sin ganancia sería ruido; se registra porque
un día uno de los dos headers cambiará y la cita hay que poder auditarla.

## Lo que `043` deja como clase, y por qué esta la confirma

`043` estableció que hay ficheros del árbol que describen un ASIC distinto.
Este caso es el **contrapunto**: el fichero equivocado dio, aun asi,
**los bytes correctos**.
La mala lectura de ASIC no siempre da un valor falso; a veces da un valor
correcto por la razón equivocada, y eso es peor, porque el valor falso se
detecta comparando con el hardware y el correcto-por-casualidad no se detecta
nunca. Lo único que lo detecta es ir a la tabla.

**Regla que sale de aquí**: cuando una marca diga `PROVEN_DERIVED` por
procedencia, la pregunta que falta no es *si el valor es cierto* —eso lo dice
la derivación— sino *cuál es el fichero de esta placa*. `PROVEN_DERIVED` es
un estado que se puede cerrar estáticamente, y dejarlo abierto por no haber
mirado la tabla es dejar trabajo hecho sin hacerlo.

## Clasificación

| afirmación | estado |
|---|---|
| `sdma_v3_0_ring_emit_ib` corre en Polaris12 | `PROVEN` — `vi.c:2113` + `sdma_v3_0.c:1693` |
| Su cuerpo es idéntico al de `sdma_v4_0_ring_emit_ib` | `PROVEN` — `diff`, 20/20 líneas |
| `SDMA_OP_INDIRECT = 4` en el header de esta placa | `PROVEN` — `tonga:29` |
| VMID en `19:16` | `PROVEN` — `tonga:1649-1650`, `0xF` en 16 |
| `rx550_pm4_indirect` sube a `PROVEN` | `PROVEN` — lo anterior, en cadena |
| Que la emisión se ejerza en runtime en esta placa | `NOT_DETERMINED` — el volcado de `111-...:83-93` tiene 8 IBs por `PACKET3_INDIRECT_BUFFER 0x3F` y **0** por `SDMA_OP_INDIRECT` |
| Si el NOP de alineación a 8 dwords hace falta | `NOT_DETERMINED` — `039-...:176`, `040:185` |
| Por qué el productor gfx omite `INDIRECT_BUFFER_VALID` | `NOT_DETERMINED` — `040:183` |
| Alineación: 4 B en gfx/compute, 32 B en sDMA | `PARTIAL` — `040:186` |
| Que los dos ficheros*sigan* iguales en el futuro | `NOT_DETERMINED` — se midió hoy, no es una invariante |

## Confounders

- **Idénticos hoy no es idénticos siempre.** El `diff` mide `linux-7.2.8`. Una
  divergencia entre ramas habría dado un valor distinto y este hallazgo no
  habría salido.
- **La identidad es de esta función, no del fichero entero.** `sdma_v3_0.c` y
  `sdma_v4_0.c` divergen en otras funciones; que esta coincida no dice nada de
  las demás, y no se ha medido cuáles.
- **`RX550-INVESTIGACION` nunca commitea.** `git log` llega hasta `667fa14`, y
  este hallazgo no está en él: vive sólo en disco, como todo lo demás.
- **`WRITE_EXECUTION=OWN_DRIVER_ONLY`.** El árbol de Linux 7.2.8 no se ha
  tocado: `MODIFICATIONS_CORPUS=0`. `GPU INTACTA`.