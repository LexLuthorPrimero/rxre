# 145 · El 99% del corpus es `drivers/gpu/drm/amd/`, y por eso no hay uAPI

```
CLASSIFICATION=DOCUMENTATION · TRACK=STATIC
CORPUS=RESEARCH/working/linux-7.1.3 · HARDWARE_SCOPE=HOST-C/RX550/0000:01:00.0
WORK_CLASS=READ_ONLY/EVIDENCE · WRITE_EXECUTION=NONE · MODIFICATIONS=0
RUNTIME=NOT_RUN · GPU INTACTA
```

## Qué resuelve

**La ruta interna que nombré en `231` está agotada, y el hueco tiene una causa de una
línea.** No es que la uAPI esté repartida por el corpus y yo no la haya encontrado:
**es que el corpus se construyó con un glob enraizado en `drivers/gpu/drm/amd/`, y
`drm_amdgpu.h` vive fuera de ese subárbol.**

**Y eso convierte un `NOT_IN_CORPUS` en una acción concreta, de `NIVEL 0`.**

## 1 · La ruta interna, agotada

`231` dejó abierta esta ruta interna: *si algún fichero de `amdkfd` declara las
estructuras GEM-VA o los ioctl, la uAPI estaría disponible por una vía que nadie ha
mirado.*

Medido sobre los seis subdirectorios de AMD que no son `amdgpu`:

```
grep -rn 'struct drm_amdgpu_\|DRM_IOCTL_AMDGPU' \
     amdkfd  display  pm  ras  acp  amdxcp
   -> VACÍO
```

Y sobre todo el árbol de AMD:

```
grep -rlE '^struct drm_[a-z_]+ \{'  drivers/gpu/drm/amd
   -> VACÍO
```

**Cero estructuras uAPI, cero ioctl, cero estructuras `drm_*` definidas en todo el
corpus.** La ruta interna está agotada. `PROVEN_ABSENT`.

**La ruta queda en `NOT_FOUND`, que con la medición de `231` confirma el
`NOT_IN_CORPUS`.**

## 2 · Y el número que explica por qué

Recuento por directorio, impreso por programa:

| directorio | ficheros |
|---|---|
| `display` | 1168 |
| `amdgpu` | 632 |
| `include` (las 551 de `asic_reg/`) | 551 |
| `pm` | 284 |
| `amdkfd` | 68 |
| `ras` | 59 |
| `acp` | 4 |
| `amdxcp` | 3 |
| **total `drivers/gpu/drm/amd/`** | **2769** |
| **corpus completo** | **2787** |
| **fuera de `amd/`** | **18** |

**El 99,35% del corpus es el árbol de AMD.** Fuera hay dieciocho ficheros: los de
`drivers/pci`, los de `drivers/base`, el `ABI/testing/sysfs-bus-pci` y el
`pm_runtime.h`.

**Y el subdirectorio más grande del corpus no es `amdgpu/` sino `display/`, con 1168
ficheros — más que el driver y más que todos los registros juntos.** Eso es el
controlador de display (DC/DCN), que para esta GPU es `dce_10_0`, y que nadie ha
mirado en este proyecto. **Es un bloque entero de trabajo sin explorar**, y es
mayor que todo lo que he leído de `amdgpu/`.

## 3 · La causa del hueco, en una línea

**El corpus contiene todo lo que hay bajo `drivers/gpu/drm/amd/`, y nada de fuera.**

Y `drm_amdgpu.h` —donde viven los números de ioctl, el layout de
`drm_amdgpu_gem_va` y `drm_amdgpu_gem_va_mapping`, y los valores de `AMDGPU_VM_*`,
`AMDGPU_VA_OP_*`, `AMDGPU_PTE_*`— está en:

```
include/uapi/drm/amd/drm_amdgpu.h
```

**Que no está bajo `drivers/gpu/drm/amd/`.** Y el árbol `include/drm/` entero —el
núcleo de DRM, del que el driver usa `drm_gem_object_lookup`, `drm_file`,
`drm_exec`, `drm_syncobj`, `drm_gem_ttm_helper`— tampoco.

**Eso explica las once cabeceras que `231` declaró `FALTA` y `Documentation/` con un
solo fichero. No es una poda selectiva: es un glob.**

## 4 · Y un falso positivo que costó una hipótesis entera

`amd/include/` tiene un fichero llamado **`pptable.h`**, 760 líneas, y lo leí
buscando una segunda definición del PTE.

**Es "PowerTune Play Table": controladores de ventilador, sensores térmicos,
`ATOM_PP_THERMALCONTROLLER_NONE`, `ATOM_PP_FANPARAMETERS_NACHMAN`.** No tiene nada
que ver con page tables.

**Y `vi_structs.h`, 533 líneas, no define PTE ni PDE:** sus dos únicas coincidencias
con "PTE" son literalmente *"PFP IB base address which get pre-empted"*.

**Así que el formato del PTE de GFX8 tiene una sola fuente en este corpus:** el
comentario de `gmc_v8_0.c:691-710` que encontró `139`, y los `#define` de
`amdgpu_vm.h`. **No hay segunda fuente, y ya se ha buscado en los dos sitios donde
podía estar.** `139` no se puede corroborar desde dentro del corpus, sólo ampliar.
Eso es un límite, y hay que decirlo junto con el hallazgo.

*Un nombre que se parece a lo que uno busca no es una fuente. `pptable.h` se lee
"page table" y es un termostato.* La regla es la de siempre aplicada al otro lado:
**ante un nombre que promete, comprobar el contenido; y `pptable.h` se comprobó, y
era un termostato.**

## 5 · La acción, y es de NIVEL 0

**Para cerrar el `NOT_IN_CORPUS` de `231` no hace falta hardware, ni placa, ni root,
ni cerrar la sesión gráfica. Hace falta copiar dos directorios al corpus:**

```
include/uapi/drm/amd/     ->  drm_amdgpu.h y los gem_* de amdgpu
include/drm/              ->  drm_drv.h, drm_gem.h, drm_exec.h, drm_syncobj.h, ...
```

**Con esos dos, el corpus compila, `amdgpu_gem.c` resuelve sus once includes, y las
cuatro filas de `231` que eran `NOT_IN_CORPUS` pasan a ser `NOT_FOUND` —que se
cierran con un `grep`.**

**Y es la acción de mayor valor informativo disponible ahora mismo en todo el
proyecto**, por tres razones que se pueden comprobar:

1. **Desbloquea la frontera del driver con userspace**, que es lo único que separa el
   objetivo final de todo lo demás. Todo lo demás está cerrado o acotado.
2. **No requiere la GPU.** Es copiar ficheros. `NIVEL 0`.
3. **Es falsable en un minuto:** si copiado el directorio los includes siguen sin
   resolver, la explicación del glob es incorrecta y hay que buscar otra.

**Y no la ejecuto yo**, porque `RESEARCH/working/linux-7.1.3` es el corpus del
proyecto, no una herramienta mía, y añadir ficheros al corpus compartido es una
decisión de quien lo curó, no una tarea de investigación. **Lo que sí hago es
dejar medido exactamente qué falta y por qué, para que la decisión sea de un
minuto.**

## Lo que NO cierra

| afirmación | estado |
|---|---|
| `NOT_IN_CORPUS` de `231` confirmado | `PROVEN` (cero en seis directorios) |
| Ningún `.c` del corpus define un `struct drm_*` | `PROVEN_ABSENT` |
| El 99,35% del corpus es `drivers/gpu/drm/amd/` | `PROVEN` (por `find`) |
| Fuera de `amd/` hay 18 ficheros | `PROVEN` |
| `display/` (1168) es el bloque más grande, y está sin explorar | `PROVEN` |
| La causa es un glob enraizado en `drivers/gpu/drm/amd/` | `PROVEN_DERIVED` |
| El formato del PTE tiene una sola fuente en el corpus | `PROVEN_DERIVED` |
| `pptable.h` es PowerTune, no page table | `OBSERVED` (falso positivo mío) |
| Qué hay en `display/dce_10_0*` relevante para esta GPU | **`NOT_OBSERVED`** — 1168 ficheros sin mirar |
| Los valores de `AMDGPU_VM_*` | **`NOT_IN_CORPUS`** — se cierra copiando |
| `struct drm_amdgpu_gem_va` | **`NOT_IN_CORPUS`** — ídem |
| Si el glob fue deliberado | **`NOT_DETERMINED`** — pregunta al que lo curó |

**La segunda fila de las que se cierran copiando es la que decide el proyecto, y la
tercera es la que nadie ha tocado: `display/` es más grande que `amdgpu/` y nadie ha
abierto un solo fichero de él.** Para un driver propio, la salida a pantalla —la
abertura de una ventana por un compositor— es|display| por definición, y `231` acaba
de demostrar que sin uAPI no hay compositor. **Son el mismo problema por los dos
extremos.**

## Procedencia

- `STATIC` -- `drivers/gpu/drm/amd/{acp,amdgpu,amdkfd,amdxcp,display,include,pm,ras}`,
  `amd/include/pptable.h`, `amd/include/vi_structs.h`, `amd/include/displayobject.h`,
  `amd/include/kgd_kfd_interface.h`.
- Medición: `os.walk` sobre el corpus para el recuento por directorio;
  `grep -rn` sobre los seis directorios no-`amdgpu` para las estructuras uAPI;
  `grep -rlE` sobre `drivers/gpu/drm/amd` para cualquier `struct drm_*`.
  **Todo impreso por programa.** El 99,35% y el 18 salen de un `os.walk`, no de una
  impresión.
- Encadenada con `231` (la uAPI ausente — esta nota **confirma** su `NOT_IN_CORPUS`
  y explica la causa), `139` (el formato del PTE, cuya única fuente queda
  establecida), `143` (los registros golden), `140` (el mapa de direcciones),
  `136`/`137` (la traducción).
- No se editó `AGENTS.md` ni `OPEN-FRONTIERS.md`, y **no se añadió nada al corpus**:
  `RESEARCH/working/linux-7.1.3` no es mío.

## Nota de método

**Nombré una ruta interna para no declarar `NOT_IN_CORPUS` sin agotarla, y la ruta
era buena: `amdkfd` está, `display` está, `ras` está, y en ninguno hay una sola
estructura uAPI.** Cuarenta y cinco segundos de `grep` y una pregunta contestada.

**Y la respuesta no era "no está": era "el corpus es otra cosa".** El recuento
por directorio dice que el 99% de lo que hay es `drivers/gpu/drm/amd/`, y que
`display/` es el bloque más grande. **No estaba buscando la uAPI: estaba midiendo el
corpus, y el corpus me dijo qué es.**

*Antes de aceptar un `NOT_IN_CORPUS` hay que saber de dónde sale el corpus.* Y la
pregunta que lo responde no es "qué más hay", sino **"qué proporción hay de cada
cosa"** — porque una proporción del 99% te dice que la recolección usó un glob, y un
glob te dice exactamente qué añadir para cerrarlo. **Eso convierte un `NOT_IN_CORPUS`
en una línea de trabajo, y es la diferencia entre un muro y una puerta.**

**Y el falso positivo de `pptable.h` es la otra mitad de la lección.** Casi escribo
una corroboración del formato del PTE contra un termostato de ventilador. **Un
nombre que se parece a lo que buscas no es una evidencia: es una hipótesis con
mayúsculas.**
