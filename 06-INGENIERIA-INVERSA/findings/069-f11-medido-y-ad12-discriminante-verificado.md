# 069 · F11 medido (27 de 34 herramientas citadas) y AD-12 verificado hoy con su discriminante

```
CLASSIFICATION=DOCUMENTATION · TRACK=STATIC + TOOL_VALIDATION
CORPUS=RESEARCH/working/linux-7.1.3 · HARDWARE_SCOPE=HOST-C/RX550/0000:01:00.0
WORK_CLASS=READ_ONLY/EVIDENCE · WRITE_EXECUTION=NONE · MODIFICATIONS=0
RUNTIME=NOT_RUN · GPU INTACTA
```

## Parte 1 · F11 pasa de `NOT_DETERMINED` a medido

F11 preguntaba: *"¿de cuántas herramientas de este árbol se ha leído alguna vez
la SALIDA, y no su cabecera?"*. No requería hardware, no requería root, y estaba
abierta. La medí.

```
  HERRAMIENTAS PYTHON EN 08-ARQUITECTURA/tools   34
    con self-test                                13
    con titular numérico                         16
    que AVISAN si su filtro falla                 2
    CITADAS en la documentación                   27 de 34
    NO citadas                                    7
```

**El titular que F11 pedía publicar, ahora publicado:**

```
  NO CITED: 7 de 34
    _selftest_stale_gap   titular:False  self-test:SI
    btfq                  titular:False  self-test:NO
    cn4                   titular:False  self-test:NO
    cn5                   titular:False  self-test:NO
    cn6                   titular:False  self-test:NO
    sweep                 titular:False  self-test:NO
    vmsize                titular:False  self-test:NO
```

Las siete **no tienen titular en su código**, que es una respuesta distinta de
"su titular no se ha leído". Ninguna publica un número que pueda ser plausible y
equivocado; las siete son herramientas sin recuento. Eso reduce el riesgo que F11
describe, y es un resultado, no una ausencia.

### Lo que la medición NO puede decir, y lo digo

`CITED` significa que el **nombre** de la herramienta aparece en un `.md` del
proyecto. Eso es un proxy de "alguien leyó su salida", no la medida directa:

- una herramienta puede haberse usado sin que su nombre aparezca;
- puede aparecer su nombre sin que nadie la haya ejecutado.

Por eso el estado es `SOSPECHOSO_DE_NO_LEER`, **no** `DESCARTADO`. F11 pide
distinguir "no se usó" de "se usó y el resultado se descartó"; esa distinción no
es decidible desde el árbol documental, y `toolaudit.py` lo declara en vez de
aparentar más de lo que mide.

### El dato interesante que salió de medir

```
  que AVISAN si su filtro falla : 2
```

`pm4_count_census.py` imprime literalmente:

```
NO_PACKET3_FOUND -- el filtro esta roto, no hay resultado
```

Eso es **el comportamiento correcto**, y es la respuesta directa al incidente que
originó F11: `msg_census` devolvió 503 números plausibles de la generación
equivocada sin avisar. Una herramienta que dice "no sé" es más fiable que una que
devuelve un número, y hay dos en el árbol que lo hacen.

## Parte 2 · AD-12: el discriminante existe y funciona, verificado hoy

F2 era "la única frontera abierta de la línea BC3". Su mitad de software ya
estaba cerrada; lo que faltaba era **comprobar que el test discrimina**, y eso no
requería hardware.

```
  $ make check-ramp-discriminates      (el MUTANTE, debe fallar)
  total                      : 65536 / 65536 pares con discrepancia
  peor error                 : 255 de 255  (en a0=0 a1=0)
  distancia entre las 2 transcripciones : 381065 entradas de 524288
  RESULT: NO CONFORMA con la especificacion -- 65536 pares discrepan
  OK: rejected the known-wrong ramp (exit 1). The test discriminates.
```

```
  $ make test                              (el test BUENO)
  total                      : 0 / 65536 pares con discrepancia
  peor error                 : 0 de 255
  distancia entre las 2 transcripciones : 0 entradas de 524288
  RESULT: CONFORMA con la especificacion Microsoft (AD-11, +3/+2)
```

**El discriminante es real**: el test acepta la rampa correcta con 0/65536 y
rechaza la incorrecta con 65536/65536. Un test que pasara con ambas no
certificaría nada, y el `Makefile` está escrito precisamente para que eso no
pueda ocurrir: exige exit distinto de cero del mutante y falla si el test lo
acepta.

Y el número que da peso a F2 está en la salida del propio test:

> `NOTA: bcdec v0.985 TRUNCA y diverge de la spec en ~82.9% de los pares`

**Truncar contra redondear cambia el 82.9 % de los resultados.** Si este hardware
trunca y el encoder emite redondeado, el error viaja dentro del payload del
bloque, de forma sistemática, y un round-trip contra el decodificador propio lo
ocultaría por construcción. Eso es lo que F2 describe, y ahora tiene un número
verificado hoy en vez de una afirmación.

## Lo que F2 sigue necesitando, y por qué no lo ejecuté

La mitad que queda es **qué hace el sampler de esta GPU**, y el camino existe:

```
$ vulkaninfo --summary
  deviceName  = AMD Radeon RX 550 / 550 Series (RADV POLARIS12)
  driverName  = radv
  driverInfo  = Mesa 26.2.3
```

RADV reconoce la GPU y `vkcube` está instalado. **No requiere root, no requiere
cargar módulo y no requiere cerrar el escritorio** — es un render por Vulkan, no
un takeover.

No lo ejecuté en esta pasada porque exige escribir un programa Vulkan que
renderice una rampa BC3 conocida y lea píxeles de vuelta: es trabajo de
implementación, no de una orden, y hacerlo a medias daría un resultado que
parece cerrar F2 y no lo cierra.

Lo que sí queda verificado es que **el camino no está bloqueado**, que es la
pregunta que F6 y F2 dejaron abierta y que nadie había comprobado.

## Estado

| Afirmación | Estado |
|---|---|
| 34 herramientas Python en el árbol | `PROVEN` (medido) |
| 27 de 34 citadas en documentación | `PROVEN` (medido) |
| Las 7 no citadas no tienen titular en código | `PROVEN` |
| 2 herramientas avisan si su filtro falla | `PROVEN` |
| El test AD-12 discrimina (0/65536 vs 65536/65536) | `PROVEN` (ejecutado hoy) |
| `bcdec` trunca, diverge en 82.9 % | `PROVEN` (salida del test) |
| Si **este hardware** trunca o redondea | `NOT_DETERMINED` — requiere el sampler |
| RADV reconoce POLARIS12 | `PROVEN` |
| El nombre citado implica salida leída | `PROVEN_ABSENT` (no se puede) |

## Procedencia

- `CORPUS` — `08-ARQUITECTURA/tools/*.py`, `04-IMPLEMENTACION/compressor/`.
- `TOOL_VALIDATION` — `make check-ramp-discriminates` y `make test`, CPU puro.
  No escriben en la GPU, no requieren root.
- `RUNTIME_READ_ONLY` — `vulkaninfo --summary`. Sin render, sin ioctl de escritura.
- Herramienta nueva: `toolaudit.py`, 17 casos de self-test.
- No se editó `OPEN-FRONTIERS.md`: es de otra sesión. Se informa.