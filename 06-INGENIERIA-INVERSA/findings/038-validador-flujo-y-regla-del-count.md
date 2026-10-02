# 038 · Herramienta: validador de flujo de comandos, y la regla `count = payload − 1` que encontró

`CLASSIFICATION=TOOL+CORRECTION` · `TRACK=STATIC` · `TOOL=tools/rx550pm4val.c`
`GPU INTACTA` · `RUNTIME=NOT_RUN` · `CORPUS=MODIFICATIONS=0`

## CUDA principal

Dos cosas, y la segunda es una corrección de un `NOT_DETERMINED` que yo había dejado
mal escrita.

**1.** `036` y `037` declararon una circularidad: el codificador se escribió leyendo amdgpu,
y las expectativas del test se transcribieron del **mismo** amdgpu, así que un error de
lectura replicado en los dos sitios pasa las 147 comprobaciones. `035` es exactamente eso,
sucedido. La circularidad está rota ahora con `tools/rx550pm4val.c` + `rx550pm4_emit.c`: un
generador que enlaza el mismo `rx550_pm4.c` que el módulo y llama a los mismos emisores, y
un validador que **no tiene acceso al corpus**. Los dos son correctos a la vez sólo si los
dwords lo son.

**2.** La herramienta encontró, en su propio selftest, que **el campo `count` de un PACKET3
es siempre el payload menos uno** en todo el camino GFX8. Yo tenía escrito lo contrario.

## La regla del `count`, y por qué corrige lo que yo escribí

| paquete | count | payload real | total | count + 2 |
|---|---|---|---|---|
| `WRITE_DATA` | 3 | cmd, reg, 0, val = 4 | 5 | ✓ |
| `WAIT_REG_MEM` | 5 | cmd, reg, 0, ref, mask, poll = 6 | 7 | ✓ |
| `PFP_SYNC_ME` | 0 | 0x0 = 1 | 2 | ✓ |
| `EVENT_WRITE` | 0 | token = 1 | 2 | ✓ |
| `SET_SH_REG` | 1 | offset, value = 2 | 3 | ✓ |
| `SET_SH_REG` x2 | 2 | off, lo, hi = 3 | 4 | ✓ |
| `DISPATCH_DIRECT` | 3 | x, y, z, initiator = 4 | 5 | ✓ |

**Siete de siete.** Total de dwords = `count + 2`.

Yo escribí en `rx550_pm4.c`, sobre `wait_reg_mem`:

> SEVEN dwords with a count of 5. The header declares five payload words and the code
> writes them, so the count and the payload agree.

**Eso es falso.** Escribe *seis* dwords de payload tras una cuenta de 5, no cinco. Y sobre
`dispatch_direct` escribí que el desajuste "is NOT_DETERMINED". No lo es: es la misma regla.

La lección es de método, no de formato. Escribí dos veces "esto no encaja, es raro, no lo
explico", y no se me ocurrió **medir la misma propiedad en los siete paquetes del camino a ver
si era raro o general**. Era general. La propiedad que busqué —"por qué este paquete"—
implicaba que había una respuesta por paquete, y la respuesta es una regla.

`PROVEN_DERIVED` sobre siete instancias medidas. No es una ley de la arquitectura: es una
observación sobre el camino GFX8, y un ASIC distinto podría no cumplirla. Lo que sí es
`PROVEN` es que en este camino el `count` **no** describe el payload, así que ningún
decodificador de GFX8 puede usar `count + 1` como longitud.

## La herramienta

`tools/rx550pm4val.c`, 850 líneas, C11, `-Wall -Wextra` sin warnings, sin dependencias.

**Regla de diseño central, y es la que viene de `031`:** *si no puede parsear, no puede
reportar éxito.* Tres códigos de salida distintos:

| código | significado |
|---|---|
| 0 | `CLEAN` — cada dword consumido por un paquete que la herramienta entiende |
| 1 | `VIOLATION` — se decodificó todo, pero una relación se violó |
| 2 | `UNDECODED` — el recorrido se detuvo: opcode desconocido, o paquete que se sale |

`031` registró que el verificador de aridad reportaba `0 mismatches` sobre 2 llamadas de 63
definiciones, y que eso no era un pass sino un fallo de cobertura disfrazado. Aquí el código 2
impide el disfraz por construcción: un opcode fuera de la tabla **para el recorrido**.

**Lo que comprueba sin consultar el corpus** — esto es lo que rompe la circularidad:

- ¿PACKET3 (`bits[31:30] == 0b11`) o sDMA (opcode en `bits[7:0]`)? Longitud accordingly:
  `count + 2` para PACKET3, longitud **implícita en el opcode** para sDMA.
- Que la longitud declarada quepa en el buffer.
- Que un paquete sDMA no se salga por el final. sDMA **no tiene cuenta**, así que un paquete
  corto no es un error de parseo sino un flujo de instrucciones distinto.
- Que el PTBA y la máscara de invalidación **naming el mismo VMID**, derivándolo de la
  dirección y no de una constante.
- Que la dirección de PTBA esté en uno de los dos tramos reales.
- Que el orden de los pasos sea PTBA < invalidate < wait, **por posición**.
- Que el campo de entradas del PTEPDE no haya desbordado.
- Que el dword 8 del PTEPDE sea 0.

**Lo que no puede comprobar, y está escrito en el propio `--help`**: si un valor es el
valor correcto. Si el codificador y la intención del driver estuvieran mal en la misma
dirección, el flujo sería internamente coherente y pasaría. Eso es lo que lo hace
cross-check y no prueba.

## 12 vectores de selftest, y 3 mutaciones del codificador

`--selftest`: 12/12 con el comportamiento especificado. Incluye vacío, opcode PACKET3
desconocido, opcode sDMA desconocido, PTEPDE truncado, PACKET3 truncado, PTBA truncado,
VMID cruzados, `0x557`, contador desbordado, dword 8 no nulo, y orden alterado.

**Mutaciones inyectadas en `rx550_pm4.c` y observadas por el validador:**

| mutación | ¿detectada? | por qué |
|---|---|---|
| PTBA como array único de 16 (bug de `037`) | **SÍ**, VMIDs 8/9/15 | la dirección cae fuera de ambos tramos → vm-flush incompleto |
| invertir invalidate y PTBA | **SÍ**, los 5 vectores | comparación de posiciones |
| `count` en vez de `count - 1` (bug de `035`) | **NO** | ver abajo |

La primera tiene la sensibilidad correcta: VMIDs 0 y 3 quedan `CLEAN` porque el tramo 0 sí es
paso 1 desde `0x54f`, y los VMIDs ≥ 8 quedan `VIOLATION`. Distingue la mitad del rango donde
el error es invisible de la mitad donde no lo es, que es lo que hace que un detector sea
informativo en vez de sólo ruidoso.

La tercera **no se puede detectar con este método** y conviene decirlo sin rodeos: `count` y
`count-1` son ambos números pequeños plausibles y el flujo es internamente coherente. Es el
límite irreducible entre **estructura** y **valor**. `test_pm4` la cubre con una aserción
explícita (`dw9 is not the raw count`). Las dos herramientas son complementarias, no
redundantes: `test_pm4` comprueba valores contra el corpus, el validador comprueba estructura
sin el corpus. Juntas cierran más que cualquiera.

## Dos errores del propio validador, encontrados por sus propias pruebas

**La longitud.** Escribí `count + 1` porque es lo que se le ocurre a uno. El selftest
reportó `dword 0x00000900 is neither a PACKET3 nor a known sDMA packet` sobre un flujo
perfectamente válido: se desincronizaba un dword antes. De ahí salió la regla de la tabla.

**Una comprobación de alineación falsa.** Puse `if (val & 0xfff) err(...)` en el PTBA.
Marcaba como error **toda** escritura legal, incluido el vector bueno, porque lo que se
escribe ahí es `pd_addr >> 12`, un **PFN**: sus 12 bits bajos son bits significativos del PFN,
no relleno. El requisito de alineación es sobre `pd_addr` antes del desplazamiento, y es del
llamador. Enseña lo mismo que `037`: *el nombre del campo no dice qué restricción tiene*.

Y un tercero, de los vectores de prueba: puse `v[9]` esperando que fuera la máscara de
invalidación y es el contador del PTEPDE; y `v[7]` esperando que fuera el registro PTBA y es
el `incr`. Los índices reales son 19 y 12. El vector 9 "pasaba" por la razón equivocada. Un
selftest también necesita comprobarse contra lo que dice hacer.

## Cómo se ejecuta

```
$ cd 07-DRIVER && make -C tests crosscheck
  gfx 3 0x900000 1         CLEAN
  gfx 8 0x12345000 1       CLEAN
  gfx 15 0x80000000 1      CLEAN
  compute 9 0x40000000 1   CLEAN
  compute 0 0x1000 1       CLEAN
  pteonly 0 0 4            CLEAN
  pteonly 0 0 1 8 0x103    CLEAN
```

Salida real del codificador, decodificada sin acceso a amdgpu. Ejemplo del detalle que
produce:

```
dw0    sDMA   PTEPDE           len=10   (implied by opcode)
  [PTE  ] pe=0x0000000000800000 flags=0x0000000000000007 addr=0x2000 incr=0x8 count=1
dw10   PACKET3 WRITE_DATA       count=3    len=5
  [PTBA ] run1 vmid=8  reg=0x050E  pfn (pd_addr>>12) = 0x00012345
dw15   PACKET3 WRITE_DATA       count=3    len=5
  [INV  ] VM_INVALIDATE_REQUEST = 0x00000100
dw20   PACKET3 WAIT_REG_MEM     count=5    len=7
  [WAIT ] reg=0x051E ref=0 mask=0 poll=0x20 op=0 function=always mem_space=reg engine=me
  .     this WAIT_REG_MEM compares nothing (function=always, mask=0); what it waits on
        is NOT_DETERMINED (findings/029)
dw27   PACKET3 PFP_SYNC_ME      count=0    len=2
--- vm-flush order verified: PTBA dw10 < invalidate dw15 < wait dw20 ---
```

Ese `NOT_DETERMINED` de `029` aparece en la salida del validador porque el validador puede
ver que la comparación no compara. Un lector del flujo se entera sin abrir el árbol.

## Falsación

- La regla `count = payload − 1` se refutaría con un paquete del camino GFX8 que no la
  cumpla. Siete medidos, ninguno la incumple. Un octavo la refutaría; el validador lo
  reportaría como error de longitud, que es exactamente para lo que está.
- El validador se refuta si un flujo producido por un encoder correcto sale `VIOLATION`, o si
  una de las tres mutaciones deja de salir. Las dos cosas son comprobables con
  `make -C tests crosscheck` y las tres mutaciones están en la historia de esta iteración.
- La afirmación de que el validador rompe la circularidad se refutaría si aceptara un flujo
  con un error de valor. Ya se sabe que acepta uno: `count` en vez de `count-1`. Está
  declarado.

## UNLOCKS

- Los decodificadores de PM4/IB de este proyecto ya no dependen de transcripciones. El
  primero existe; un decodificador de IB (el `SDMA_OP_INDIRECT` ya está decodificado) es el
  siguiente paso natural y tiene la misma forma.
- La distinción **estructura vs valor** queda nombrada y repartida entre dos herramientas.
  Es la lección general de `031`, `035` y `037` juntas: cada vez, la respuesta a "por qué esto
  no cuadra" fue medir la misma propiedad en el resto del conjunto antes de preguntarse por
  qué este caso concreto.
- `RX550_VM_FLUSH_DW` y las longitudes de PTEPDE se pueden ahora validar contra una regla y no
  contra una transcripción.

## Evidencia

```
tools/rx550pm4val.c          850 líneas, C11, sin warnings, sha256 e9c7508b…a115
07-DRIVER/tests/rx550pm4_emit.c  127 líneas, sha256 900e83cc…a46
07-DRIVER/tests/Makefile     objetivo crosscheck, sha256 12a9c23f…cad1
selftest                     12/12 PASS
mutaciones                   2 de 3 detectadas; la 3ª declarada no detectable por método
suite completa               22 + 12 + 147 = 181 checks, 0 fallos
rx550.ko                     KBUILD_RC=0
corpus:                      MODIFICATIONS=0, sha256 12e8d5a973d1ad7c…c3e51941
```

Ningún registro leído de MMIO. `insmod` no ejecutado. `GPU INTACTA`.
