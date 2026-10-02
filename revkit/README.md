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

Ninguna de estas herramientas escribe en la GPU ni en un registro.

`amdgpu_iomem` da `EPERM` incluso con root, y `amdgpu_vm_info` en 7.1.3 no
vuelca page tables: solo lista BOs. El volcado de PTE reales sigue
`NOT_AVAILABLE` por esta vía, que no es lo mismo que inaccesible en el
hardware.

`amdgpu_regs` no se lee: 2 de 3 reinicios del servidor correlacionaron con
su lectura. Se documenta como correlación, no como causa.

Los punteros del anillo (`RPTR`, `WPTR`) **no** son lectura de MMIO: son
espejos en CPU que mantiene el driver. `pm4dec` lo dice explícitamente, y
fue un error mío leerlos como hardware en una primera versión.

Lo que sí cierra huecos sin hardware: **otra generación del mismo driver**.
`verdiff.py` la usa, y ha servido para corroborar por segunda fuente dos
cadenas de emisión y para acotar una pregunta de layout de registro.

### `check.sh` — todas las validaciones en un comando

```
./check.sh           todo, reindexa
./check.sh rapido    solo lo que no reindexa
```

25 validaciones. Continúa tras un fallo, para que un fallo no oculte
los demás.

Tres estados posibles, y no se confunden:

| estado | qué es |
|---|---|
| `OK` | la validación pasó |
| `FALLO` | la validación se ejecutó y falló |
| `OMIT` | no se pudo ejecutar por una dependencia ausente |

`OMIT` no cuenta como `OK`. `cn7` necesita `sid.h`, que vive en el corpus
del kernel y no viaja con `revkit`; en un clon sin corpus sale `OMIT`, no
`FALLO`, porque una dependencia ausente no es una herramienta rota.

### Herramientas de acceso al hardware

Desde que hay acceso root al debugfs, cuatro herramientas observan la
máquina. Ninguna escribe: la lista de nodos es una constante del código y
solo se abren en lectura.

### `mmo.py` — un nodo de debugfs, a mano

```
RX550_SUDO_PASS=... ./mmo.py lista
RX550_SUDO_PASS=... ./mmo.py capacidades      qué se lee y qué no, con el modo real
RX550_SUDO_PASS=... ./mmo.py nodo amdgpu_firmware_info
RX550_SUDO_PASS=... ./mmo.py nodo amdgpu_regs --guardar capturas/x.txt
```

La contraseña va en la variable de entorno `RX550_SUDO_PASS`, nunca en un
argumento (un argumento aparece en `/proc/PID/cmdline`).

`capacidades` es el comando que hay que usar primero: comprueba el modo real
de cada nodo contra la lista blanca. Se incluyen los que **escriben** para
dejar constancia de que se conocen y no se tocan.

### `captura.py` — snapshot de todo lo legible, de una vez

```
RX550_SUDO_PASS=... ./captura.py            los 21 nodos de texto
RX550_SUDO_PASS=... ./captura.py --solo amdgpu_vm_info
```

Una sola sesión de sudo, 0,3 s para 19 nodos. Cada volcado queda como
fichero, así que se analiza las veces que haga falta sin volver a tocar la
GPU.

`amdgpu_regs` está **excluido a propósito**: se reinició el servidor 2 de 3
veces correlacionadas con su lectura. No se ha probado que la lectura lo
cause, pero la correlación basta para no arriesgarse. Se dice como
correlación, no como causa.

### `integro.py` — corrupción y riesgo de pérdida

```
./integro.py escanear            texto corrupto, perdido o truncado
./integro.py escanear --rastrear  además, ficheros sin seguimiento en git
./integro.py autotest            sus propios controles
```

Solo controla ficheros de **texto**. Un NUL en un ELF o un `.pyc` es lo
normal; reportarlo daría 180 falsos positivos y un informe con 180 falsos
positivos no se lee.

Distingue cuatro cosas que se confunden:

| tipo | qué es |
|---|---|
| `PERDIDO` | todo NUL, no hay texto dentro: ir a otra copia |
| `TRUNCADO` | hay texto bueno y luego cola de NUL: recuperable truncando |
| `CORRUPTO` | NUL dispersos |
| `NO SEGUIMIENTO` | sano, pero sin versión en git |

Nació de un hecho: `revkit/mmo.py` tenía 1232 bytes nulos al final tras un
reinicio, y el módulo era **válido**, así que un parser lo daba por bueno.
Solo lo detectaba leer los bytes.

### `atomrom.py` — el VBIOS

```
./atomrom.py autotest         con un ROM sintético, sin el VBIOS real
./atomrom.py rom              los 4 controles que hace el driver
./atomrom.py tablas           inventario de las 35 tablas
```

Los offsets salen de `atom.h` y `atombios.h`, no de memoria, y cada uno
remite a su línea. Valida contra los mismos cuatro controles que ejecuta
`amdgpu_atom_parse()`.

El autotest existe porque el VBIOS **no se versiona** (derechos AMD): una
validación que dependiera de él fallaría en un clon limpio. Y porque un
validador que solo sabe decir «sí» no valida: el autotest comprueba también
que **rechaza** ROM corruptos.

### `pm4dec.py` y `cn7.py` — decodificación PM4

```
./pm4dec.py capturas/amdgpu_ring_gfx.txt
./pm4dec.py capturas/amdgpu_ring_gfx.txt --todos
./cn7.py                       13 controles
```

Los 74 opcodes se extraen de `sid.h` **en tiempo de ejecución**. No hay ni
uno transcrito a mano: transcribir 140 opcodes es exactamente el trabajo que
produce números plausibles y equivocados.

Dos reglas que vienen del corpus y no de memoria:

- `PACKET3_NOP` ocupa **1 dword** aunque su campo de conteo diga `0x3FFF`.
  Es el valor de relleno de GFX8 (`gfx_v8_0.c:6873`), escrito con `memset32`
  en `amdgpu_ring.c:128` y `:154`.
- Un dword de tipo 0 en el anillo GFX **no es un `PKT0`**. `PKT0` no
  aparece en todo el driver: el driver escribe registros con
  `PACKET3_SET_CONTEXT_REG` y compañía.

### `dires.py` — direcciones de registro

```
./dires.py 0x1537 --bloque bif
./dires.py --contar
```

`regs.py` indexa los **campos** (MASK, SHIFT) pero no las **direcciones**, y
sin direcciones no se puede comprobar que un paquete escriba donde dice. Los
headers están en `include/asic_reg/`, ordenados por bloque, no en el
directorio de amdgpu.

Trae autocomprobación: busca `0x1537`/`0x1538`, que se sabe que son
`mmGPU_HDP_FLUSH_REQ`/`_DONE` de BIF 4.1, y si no los encuentra sale con
rc=3 en vez de seguir. El control existe porque la primera versión tenía el
filtro de sufijo mal (`".d.h"` en vez de `"_d.h"`) y devolvía una lista vacía
para BIF, que es justo el bloque de esta GPU. Un filtro mal escrito no avisa.

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
7. **`atomrom` colocaba la master data table en `base`** en vez de en
   `usMasterDataTableOffset`, y leía `usStructureSize=36` donde el layout
   exige 74. Lo útil no es que lo corrigiera: es que **avisó sola** de que
   los nombres no eran de fiar y no publicó el inventario. Un NoAnswer con
   explicación vale más que 35 tablas con aspecto de respuesta.
8. **`captura` contaba un fallo de autenticación como resultado**: con
   contraseña incorrecta imprimía «con contenido: 0, vacíos: 0, error: 0» y
   salía con rc=0. Ahora sale con rc=4 y el stderr de sudo. Es el modo de
   fallo dominante del proyecto: un cero que parece un resultado.
9. **`captura --solo` no era `--solo`**: pedía un nodo y capturaba tres. El
   nombre de la opción decía una cosa y el código hacía otra.
10. **`dires` tenía el filtro de sufijo mal**: `".d.h"` en vez de `"_d.h"`. No
    daba error: devolvía una lista vacía para BIF, el bloque de esta GPU, y
    eso parece un resultado legítimo. Ahora lleva autocomprobación.
11. **Un control que no detectaba su propia mutación**: el de `integro` que
    comprobaba que un `.o` no saliera entre los ficheros de texto pasaba
    tanto si el filtro funcionaba como si estaba roto, porque en ambos casos
    `.o` no llegaba a la lista. Se reescribió para mirar `clasifica()`
    directamente, y se verificó con mutaciones reales.
12. **`integro` con un sniff mal calibrado**: la primera regla daba por
    binario un texto truncado con cola de NUL — que es justo la corrupción
    que hay que detectar. Falló 2 de 7 casos. Un sniff mal calibrado no
    falla: deja de ver cosas.
13. **`pm4dec` publicaba un `NOT_DETERMINED` disfrazado de dato**: leía un
    dword tipo 0 como cabecera de `PKT0` y sacaba «42 escrituras de registro»
    con direcciones como `0x0000`, que no son registros. Se parecía a un
    resultado y era la mitad inventado.

## Requisitos

Python 3 sin dependencias externas. Todo el resto es el corpus y sysfs.

Para las herramientas de hardware hace falta `sudo` y la variable
`RX550_SUDO_PASS`. El valor **no** se guarda en el repositorio: es de la
máquina, no del proyecto.

## Límite común

Ninguna de estas herramientas escribe en la GPU ni en un registro.

`amdgpu_iomem` da `EPERM` incluso con root, y `amdgpu_vm_info` en 7.1.3 no
vuelca page tables: solo lista BOs. El volcado de PTE reales sigue
`NOT_AVAILABLE` por esta vía, que no es lo mismo que inaccesible en el
hardware.

`amdgpu_regs` no se lee: 2 de 3 reinicios del servidor correlacionaron con
su lectura. Se documenta como correlación, no como causa.

Los punteros del anillo (`RPTR`, `WPTR`) **no** son lectura de MMIO: son
espejos en CPU que mantiene el driver. `pm4dec` lo dice explícitamente, y
fue un error mío leerlos como hardware en una primera versión.