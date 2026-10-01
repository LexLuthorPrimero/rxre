# revkit — herramientas para no repetir el trabajo manual

Cada herramienta existe porque un tarea concreta se estaba haciendo a mano,
repetidamente, y cometía los mismos errores. Ninguna existe por completitud.

## El problema que estas herramientas resuelven

En esta sesión los errores que costaron tiempo no fueron de razonamiento,
fueron de **instrumentación**:

| error | consecuencia | herramienta que lo evita |
|---|---|---|
| `grep MTYPE_UC` casa dentro de `X86_MEMTYPE_UC` | conclusión **invertida** sobre MTYPE | `cidx.py` con límites de palabra reales |
| buscar un símbolo en un solo directorio | «no existe» siendo falso | `cidx.py` indexa las 625 fuentes |
| `grep` dio 0 y se reportó sin comprobar | parecía un struct vacío | avisos explícitos en cada herramienta |
| copiar `block_size` del `9` del fragment | Q1 cerrado con cifra falsa | `pte.py` separa definido de alcanzable |
| atribuir `card0` a la RX550 | dato del ASIC equivocado | `obs.py` localiza por identidad PCI |
| contar 11 líneas de log como 11 corroboraciones | evidencia inflada | `obs.py log-uniq` deduplica |

## Las herramientas

### `cidx.py` — índice del corpus

```
./cidx.py stats                     resumen
./cidx.py find  SIMBOLO             dónde aparece
./cidx.py use   SIMBOLO             quién lo consume
./cidx.py def   SIMBOLO             dónde se define
./cidx.py callers SIMBOLO           quién lo llama
./cidx.py absent SIMBOLO             ausencia CON ENUMERACIÓN
./cidx.py funcs                     catálogo de funciones
```

625 ficheros, 13820 símbolos, 8928 funciones. Cacheado: 4,2 s la primera,
**0,19 s** después.

El detalle que importa: los límites de palabra son
`(?<![A-Za-z0-9_])NAME(?![A-Za-z0-9_])`, no `\bNAME\b`, porque `\b` casa
dentro de `AMDGPU_PTE_VALIDATE`. Y si le pides un **fragmento** en vez de un
identificador, avisa en vez de devolver 0: un 0 por nombre equivocado se lee
como ausencia.

`absent` devuelve `NOT_FOUND`, nunca `PROVEN_ABSENT`, salvo que se le pidan
las variantes.

### `regs.py` — decodificador de registros

```
./regs.py REGISTRO CAMPO             mask, shift, ancho, por ASIC
./regs.py REGISTRO CAMPO --asic gfx_8_0
./regs.py REGISTRO                   lista sus campos
./regs.py --find PATRON              qué ficheros/registros/campos casan
./regs.py --incumplen                MASK incoherente con su SHIFT
```

3,4 M macros, 146901 registros. Cacheado: 2,2 s por consulta.

Verificado contra el fuente:

```
$ ./regs.py CC_GC_SHADER_ARRAY_CONFIG INACTIVE_CUS --asic gfx_8_0
  gfx_8_0   MASK=0xffff0000 SHIFT=16 -> 16 bits @ 16   gfx_8_0_sh_mask.h:17713
```

Que coincide con lo verificado a mano.

El filtro `--asic` es lo que hace la respuesta no ambigua: el mismo campo tiene
valores distintos en `gfx_8_0`, `gfx_9_0`, `gfx_10_0`... Dar un valor sin decir
de qué ASIC es una respuesta incompleta, y equivocarse de ASIC no da error
visible.

### `obs.py` — observación del host

```
./obs.py gpu                         localiza por identidad PCI
./obs.py sysfs                       atributos, marcando los no legibles
./obs.py log-uniq --filtro REGEX     hechos únicos, no ocurrencias
./obs.py params                      parámetros de módulo
./obs.py json                        salida para máquinas
```

Lo que más aporta: `log-uniq`. El driver reinicia GART once veces durante el
arranque, así que el log tiene 11 líneas de `PCIE GART of 256M` que son **un
solo hecho**. Contarlas como once es evidencia inflada.

Y distingue `rom` (existe, `-rw-------`, no legible) de `AUSENTE`. Un fichero
que existe pero no se puede leer no es un dato que valga cero.

### `vclaims.py` — verifica las citas de los documentos

```
./vclaims.py [ruta]                  comprueba fichero.c:LINEA
```

788 citas en 47 documentos de `08-ARQUITECTURA/`: **0 rotas**.

Lo que hace:
- comprueba que el fichero existe y tiene esa línea;
- distingue las dos raíces: `working` (subárbol parcial) y `kernelbuild`
  (árbol completo, con 4 ficheros instrumentados);
- cuando un nombre existe en varios sitios, elige el que **contiene la línea
  citada** en vez del primero que aparece;
- separa las citas a fuentes externas (Mesa, Vulkan) de las rotas.

Lo que **no** hace, y está declarado en su salida: no comprueba que la
conclusión sea correcta. Una cita puede ser válida y sostener una conclusión
errada, como en `014`, donde la rama citada existe pero no es la que se
ejecuta.

### `pte.py` — flags de PTE de GFX8

```
./pte.py bits                        qué está DEFINIDO
./pte.py para-gfx8                   qué es ALCANZABLE desde GFX8
./pte.py dump 0x...                  decodifica una PTE de 64 bits
```

La distinción de `bits` frente a `para-gfx8` es el punto de la herramienta.
El corpus define los flags de **todas** las generaciones, así que «definido» no
es «usado por GFX8»:

```
CON ALCANZABILIDAD DEMOSTRADA (15)
DEFINIDOS PERO NINGUN CONSUMIDOR ALCANZABLE (4)
  AMDGPU_PTE_LOG         55  solo gmc_v10_0.c, gmc_v11_0.c
  AMDGPU_PTE_NOALLOC     58  solo gmc_v10_0.c, gmc_v11_0.c
  AMDGPU_PTE_DCC         58  solo gmc_v12_0.c
  AMDGPU_PTE_BUS_ATOMICS 59  solo gmc_v12_1.c
SIN NINGUN CONSUMIDOR (0)
```

Esos cuatro son `NOT_APPLICABLE` para GFX8, **no** `PROVEN_ABSENT`. Y es
precisamente el mecanismo que produjo la conclusión falsa de MTYPE: un flag
definido en un fichero compartido y consumido solo por rutas de otro ASIC.

Verificado de forma independiente contra `pteflags`: `SYSTEM=1`,
`SNOOPED=2`, `READABLE=5`, y `LOG`/`NOALLOC` solo en `gmc_v10`/`gmc_v11`.

### `ibtrace.py` — secuencias de emisión de IB

```
./ibtrace.py func FICHERO::FUNCION    una función, escritura a escritura
./ibtrace.py todas [filtro]          inventario de las que emiten
./ibtrace.py sync                    las que emiten opcodes de sincronización
./ibtrace.py diff A.c B.c            la misma función en dos ficheros
```

63 funciones con emisión en `gfx_v8_0.c`. Antes eso era leer 4000 líneas.

Reproduce lo verificado a mano para `emit_vm_flush`: 9 escrituras, 2 headers,
`PACKET3_WAIT_REG_MEM = 0x3C`.

Reconoce **las dos** formas de escribir en un IB, y las mezcla en una lista
ordenada porque en un IB el orden de los dwords **es** el paquete:

```c
amdgpu_ring_write(ring, VALOR);        /* el común */
ib->ptr[ib->length_dw++] = VALOR;      /* el de SDMA, y el que escribe las PTEs */
```

### `causa.py` — mapa causal, que es lo que pide el protocolo

```
./causa.py mapa SIMBOLO        SOURCE -> usos -> dónde se corta la cadena
./causa.py flujo SIMBOLO       quién lo escribe, quién lo pasa, quién lo usa
./causa.py descubrir FICHERO   registros MMIO, separando leídos de solo-escritos
```

El paso que importa es el tercero: **decir dónde se corta la cadena**. Un mapa
que llega a «nadie lo consume» no está incompleto, es una *afirmación*, y una
afirmación necesita evidencia que esta herramienta no aporta.

`descubrir gfx_v8_0` da **117 registros MMIO, 50 solo-escritos**. Esos son los
que el hardware consume sin feedback: no hay observable en el driver de
referencia para ninguno.

### `verdiff.py` — diferencial entre las dos versiones del driver

```
./verdiff.py fn FICHERO FUNCION    cómo cambia entre 7.1.3 y 7.2.8
./verdiff.py doc SIMBOLO           el símbolo en los COMENTARIOS de ambas
./verdiff.py nuevo                 símbolos que 7.2.8 tiene y 7.1.3 no
```

Hay **dos árboles completos** en el corpus (`RESEARCH/working/linux-7.1.3` y
`rx550-upstream-7.2.8`, mismo sha256) y el segundo no se usaba. Cuando algo es
`NOT_DETERMINED` hay tres vías: runtime (bloqueado), documentación externa (no
está), y **otra generación del mismo driver** (disponible, e ignorada).

`doc` es la más infravalorada: un comentario de upstream junto a un registro
suele decir qué hace, y es evidencia que la versión propia no da.

Ha corroborado por segunda fuente que `emit_vm_flush` y
`emit_flush_gpu_tlb` son **idénticas** en 7.1.3 y 7.2.8.

### `estado.py` — consolida el estado del proyecto

```
./estado.py censo             cuenta estados: PROVEN, NOT_DETERMINED, REFUTED...
./estado.py contradicciones   las de docs/CONTRADICTIONS.md con su ESTADO
./estado.py cobertura         documentos que afirman PROVEN sin cita al corpus
./estado.py registro          índice de documentos
```

No edita nada. Es una vista, y lo dice en su salida.

Cifras del censo: 5768 marcas de estado, 2415 de resolución y 3353 no
resuelta. 204 documentos afirman `PROVEN`; 129 con cita al corpus, 75 sin ella.

### `scan.py` — descubre trabajo pendiente

```
./scan.py [--solo SECCION]
```

Cinco secciones, cada una con su **criterio declarado**: bloqueantes, huecos,
invariantes, solo-escritos, abiertas.

La sección de invariantes es la que ha dado más: `PFP_SYNC_ME` en
`emit_vm_flush` aparece en **siete** generaciones (v6–v12). El proyecto lo tenía
como decisión de GFX8; es de la familia.

### `correlate.py` — enlaza hallazgos con herramientas

```
./correlate.py
```

Para cada documento: qué símbolos y citas tiene, qué herramienta puede
responderlo, y el comando exacto. 158 documentos, 24 herramientas
clasificadas. Señala además los símbolos que aparecen en varios documentos,
que es o corroboración de que importa, o duplicación que divergirá.

## Documentos de hallazgo

Cada uno responde una pregunta con evidencia de las herramientas:

| documento | qué cierra |
|---|---|
| `WAIT-REG-MEM.md` | qué valores de `FUNCTION` emite GFX8, y las tres funciones que emiten WAIT_REG_MEM |
| `INVALIDATE-CANALES.md` | los 18 canales de invalidate que el driver no usa, y el layout de `VM_INVALIDATE_RESPONSE` |
| `RB-POLL.md` | el ring scheduling, y por qué `0x60` es `POLL_FREQUENCY` y no `IDLE_POLL_COUNT` |
| `PTEPDE-GFX8.md` | la secuencia de PTEPDE del ASIC real, con `count - 1` |

Los dos últimos contienen **correcciones de hallazgos anteriores**, con el
razonamiento que se refutó. Se dejan visibles a propósito: un documento donde
solo se ve el resultado final no permite saber cuánto se comprobó.

## Límite común

Ninguna de estas herramientas lee MMIO. `/sys/kernel/debug/dri` está en `0400`
y sin `sudo` no hay acceso, así que el camino de runtime completo sigue
cerrado. Todo lo de aquí es estático más lo que el kernel ya publicó en sysfs
y en el log.

Lo que sí cierra huecos sin hardware: **otra generación del mismo driver**.
`verdiff.py` la usa, y ha servido para corroborar por segunda fuente dos
cadenas de emisión y para acotar una pregunta de layout de registro.

### `check.sh` — todas las validaciones en un comando

```
./check.sh           todo, reindexa
./check.sh rapido    solo lo que no reindexa
```

9 validaciones en ~14 s. Continúa tras un fallo, para que un fallo no oculte
los demás.

## Errores que estas herramientas cometieron durante su construcción

Están aquí porque el patrón se repite:

1. **`cidx` devolvía 0 en silencio** cuando se le pedía un fragmento en vez de
   un identificador completo. Ahora avisa y lista los nombres reales.
2. **`regs` no encontraba ningún campo** con la primera versión de la regex:
   exigía `__MASK`, y el formato real es `_MASK` con un solo guion bajo.
   Indexaba 3,4 M macros y no encontraba ni una. Devolver 0 sobre un índice
   mal construido es peor que no tener índice.
3. **`regs` duplicaba el índice entero** porque `REGINC` está dentro de
   `DRVINC` y se recorren ambos. Hacía que «6 ASIC definen esto» respondiera 12.
4. **`regs` emparejaba MASK con SHIFT por posición de lista**, lo que daba
   `SHIFT=?` y un ancho plausible pero falso. Ahora empareja por fichero y
   línea más cercana.
5. **`vclaims` reportaba 91 citas rotas** de las que 59 eran legítimas:
   buscaba solo en `working`, que no tiene `include/uapi/drm` ni `kernel/`.
   Y resolvía `pci.h` al `include/uapi/linux/pci.h` de 49 líneas en vez del
   `include/linux/pci.h` de 2879, marcando como error una cita correcta.
6. **El primer `check.sh` apuntaba a `cn6.py` en el directorio equivocado** y
   falló con «No such file». Lo detectó él mismo al ejecutarse.

## Requisitos

Python 3 sin dependencias externas. Todo el resto es el corpus y sysfs.

## Límite común

Ninguna de estas herramientas lee MMIO. `/sys/kernel/debug/dri` está en `0400`
y sin `sudo` no hay acceso, así que el camino de runtime completo sigue
cerrado. Todo lo de aquí es estático más lo que el kernel ya publicó en sysfs
y en el log.