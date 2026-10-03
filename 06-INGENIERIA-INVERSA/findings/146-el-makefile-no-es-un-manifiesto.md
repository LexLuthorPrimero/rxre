# 146 · El Makefile no es un manifiesto: casi reporto 387 ficheros ausentes y eran mi bug

```
CLASSIFICATION=DOCUMENTATION · TRACK=STATIC · TOOL=ERROR_CORRECTION
CORPUS=RESEARCH/working/linux-7.1.3 · HARDWARE_SCOPE=HOST-C/RX550/0000:01:00.0
WORK_CLASS=READ_ONLY/EVIDENCE · WRITE_EXECUTION=NONE · MODIFICATIONS=0
RUNTIME=NOT_RUN · GPU INTACTA
```

## Qué resuelve

**Que el Makefile del corpus no es un manifiesto fiable, y por qué casi publico una
catástrofe que no existía.**

**La cifra buena: 984 ficheros `.c`, 68 Makefiles, 986 `.o` declarados, y sólo 2 sin
fuente — y los dos son renombres, no ausencias.** El corpus está prácticamente
completo para el módulo amdgpu. El hueco real sigue siendo sólo la uAPI.

## 1 · El error, primero y sin adornar

Escribí un script para contrastar los `.o` declarados en cada Makefile con los `.c`
existentes. Resolvía la ruta **en el directorio del propio Makefile**. El resultado:

```
.o declarados en total:   1029
.c que FALTAN:              387        <-- FALSO
Makefiles con faltantes:     32        <-- FALSO
  amdkfd   42 .o, faltan 42
  hwss     37 .o, faltan 37
  mpc       6 .o, faltan  6
```

**Y la bandera de que era mi bug estaba en mi propia salida:** `FALTA /acp_hw.c`, con
barra inicial. Un Makefile no escribe `/acp_hw.c`; escribe
`$(AMDACPPATH)/acp_hw.o`.

**Comprobado antes de creérmelo:**

| directorio | lo que yo decía | lo que hay |
|---|---|---|
| `amdkfd/` | 42 `.c` faltan | **42 `.c` existen** |
| `hwss/` | 37 `.c` faltan | **37 `.c` existen** |
| `dml2_0/` | — | 31 `.c` |
| `dml/` | — | 35 `.c` |
| `clk_mgr/` | — | 35 `.c` |
| `link/` | — | 30 `.c` |

**El bug: esos Makefiles son el del directorio padre y listan ficheros de un
directorio hijo, o usan una variable de ruta.** Mi script los buscaba al lado del
Makefile, donde nunca estuvieron.

**Si lo hubiera escrito, el proyecto habría registrado que al corpus le faltan 387
fuentes, y dos directorios enteros vacíos, y sería falso.** La cifra era tan
alarmante que la regla de `140` —*si una aritmética decide una conclusión, la imprime
un programa*— no bastaba: hacía falta además **comprobar el programa antes de creer
su número**.

## 2 · La medición correcta, sin resolución de rutas

Reescrito para indexar **todos** los `.c` del corpus por nombre base y comprobar
pertenencia, eliminando el problema de rutas por construcción:

```
ficheros .c indexados en el corpus:  984
Makefiles analizados:                 68
.o declarados (basename único):      986
.o SIN fuente en todo el corpus:       2
Makefiles con algún .o sin fuente:     2
```

**984 de 986. Dos, y sólo dos.** `PROVEN`, y por programa.

## 3 · Y los dos son renombres, no ausencias

```
amdgpu/Makefile    declara  amdgpu.o    el fichero es  amdgpu_drv.c
amdxcp/Makefile    declara  amdxcp.o    el fichero es  amdgpu_xcp_drv.c
```

**Y lo importante: `amdgpu_drv.c` sí está, y es donde vive el punto de entrada del
módulo.** Comprobado:

```
grep -rln 'module_init\|pci_driver' amdgpu/*.c
   -> amdgpu_drv.c
```

**Así que el `module_init` y el `pci_driver` del driver amdgpu **sí están en el
corpus**, y con ellos la referencia que el estado del proyecto ya usaba
(`amdgpu_drv.c:2041`, `CHIP_POLARIS12`). Nada falta ahí.**

**Y `amdxcp/` tiene exactamente tres ficheros:** `amdgpu_xcp_drv.h`,
`amdgpu_xcp_drv.c`, `Makefile`. El Makefile nombra un fichero que no existe y el
fichero que existe tiene otro nombre. Mismo patrón.

**Conclusión: hay un desfase de versión entre los Makefiles y las fuentes, localizado
en dos ficheros de nombre.** No es un corpus roto: es un corpus cuyos dos Makefiles
no se renombraron con sus fuentes. `PROVEN_DERIVED`.

## 4 · Qué implica para el proyecto

| afirmación | estado |
|---|---|
| 984 `.c`, 986 `.o` declarados, 2 sin fuente | `PROVEN` (por programa) |
| Los 2 son renombres, no ausencias | `PROVEN` |
| `module_init` y `pci_driver` están en `amdgpu_drv.c` | `PROVEN` |
| El corpus está completo para el módulo amdgpu | `PROVEN_DERIVED` |
| Hay desfase Makefile↔fuentes en 2 ficheros | `PROVEN_DERIVED` |
| **El Makefile no sirve como manifiesto** | **`PROVEN_DERIVED`** |
| La uAPI sigue ausente | `PROVEN` (145, 144) |
| Cuál de los dos ficheros es más reciente | **`NOT_DETERMINED`** — hace falta historial |

**El único hueco real del corpus sigue siendo el de `145`: `include/uapi/drm/amd/` e
`include/drm/`.** Y ese hueco **no aparece en ningún Makefile del corpus**, porque
ningún Makefile de `drivers/gpu/drm/amd/` referencia cabeceras de `include/`. **Es
decir: el Makefile no puede ni detectar el hueco que importa.** Otra razón para no
usarlo como manifiesto.

## 5 · `display/`: lo que sí es explorable

De paso, la estructura de `display/dc/`, que es lo que había pedido mirar:

**Cuarenta subdirectorios, nombrados por bloque de hardware, no por chip:**

```
dce 45   dce110 15  dce112 3  dce120 3  dce60 3  dce80 3
dcn10 9  dcn20 6  dcn201 7  dcn21 3  dcn30 9  dcn301 3  dcn31 9
dml 75   dml2_0 82  link 60  clk_mgr 76  hwss 78  dml2_0 82
dio 43   dccg 25  dwb 7  mpc 13  opp 7  dpp 23  dsc 13
gpio 68  hdcp 2  hpo 9  hubbub 23  hubp 21  inc 45  irq 43
resource 54  dce110 15  bios 31  basics 12  core 12  sspl 18
soc_and_ip_translator 6   pg 5
```

**Y `dce/` no está organise por chip sino por función:** `dce_aux`, `dce_i2c`,
`dce_i2c_hw`, `dce_i2c_sw`, `dce_ipp`, `dce_stream_encoder`, `dce_transform`,
`dce_opp`, `dce_panel_cntl`, `dce_scl_filters`, `dce_audio`, `dce_clock_source`,
`dce_dmcu`, `dce_abm`, `dce_link_encoder`, `dce_mem_input` — 45 ficheros.

**Lo que sólo se separa por chip es lo que de verdad difiere:** `dce112` (compressor,
3 ficheros), `dce120` (timing generator, 3 ficheros), `dcn10`…`dcn31` (9, 6, 7, 3, 9, 3,
9).

**Y no hay `dce_10_0.c`, ni `dce_8_0.c`, ni `dc_10_0.c`.** El Makefile de la raíz de
`display/dc/` declara 17 `.o` y **existen los 17** — con `core/dc.o` en `core/`, que
es donde lovi a buscar. **Mi primera hipótesis fue que faltaba el fichero
selector por chip, y era falsa: el Makefile de la raíz está completo.**

**Lo que sí está por explorar y es real:** para esta GPU el DC es
`dce_10_0` (registros en `amd/include/asic_reg/dce/dce_10_0_d.h`,
`dce_10_0_sh_mask.h`, `dce_10_0_enum.h`, todos presentes) y la implementación
funcional está repartida en `dce/` y `core/`. **Para un driver propio, el camino de
salida a pantalla son `dce_stream_encoder` + `dce_transform` + `dce_opp` +
`core/dc_sink`, y ninguno se ha abierto.**

## Procedencia

- `STATIC` -- `drivers/gpu/drm/amd/{amdgpu,amdxcp,display/dc,display/dc/dce}`,
  Makefiles de los 68 directorios que los contienen, `display/dc/` y sus 40
  subdirectorios.
- Medición: `os.walk` sobre el corpus dos veces — una para indexar los 984 `.c` por
  basename, otra para recorrer los 68 Makefiles y extraer los `.o` con
  `re.findall(r'([A-Za-z0-9_\-]+)\.o\b')`. **El número sale del programa; el
  programa se verificó a mano contra `find` en `amdkfd/` y `hwss/` antes de creerlo.**
- Los dos scripts eran de comprobación puntual y están en `/tmp/opencode/`;
  **no se han guardado en `08-ARQUITECTURA/tools/` y no son herramienta del
  proyecto**, porque su valor es el número que ya está impreso aquí.
- Encadenada con `145` (el 99% del corpus y la uAPI ausente — esta nota **confirma**
  que el resto del corpus está completo), `231` (la uAPI),
  `139` (el PTE, cuya única fuente queda establecida en 145).
- No se editó `AGENTS.md` ni `OPEN-FRONTIERS.md`.

## Nota de método

**Casi escribo que al corpus le faltan 387 fuentes, y eran 2 renombres.**

**Y la causa de mi error es la misma que la causa de mis otros errores de la
tanda, con distinto disfraz.** En `140` fueron restas hexadecimales a mano; en
`137`, `138`, `139` y `142` fue entrar por el símbolo que ya sabía; y aquí fue un
`grep` que no encontraba. **Los cuatro son la misma regla mal aplicada: cuando algo
no aparece, la primera hipótesis es que el patrón o la herramienta están mal, no que
el mundo esté mal.**

**La señal estaba en mi propia salida y no la leí:** `FALTA /acp_hw.c`, con la barra
inicial. Nadie escribe `/acp_hw.c` en un Makefile. **Un resultado raro dentro de un
resultado raro es un dato sobre el programa, no sobre el corpus.**

**Y la consecuencia para el método es concreta: un programa que devuelve un número
hay que contrastarlo con una segunda vía antes de escribir el número.** No porque
los programas mientan —el mío calculaba bien— sino porque **un programa con un bug de
rutas es indistinguible de un corpus roto, y el número que sale es más dramático que
la diferencia entre las dos cosas.** Comprobé con `find`, y la diferencia era 387
contra 2.

**Y hay una regla de infrastructure que sale de aquí, y la escribo para el proyecto:
un Makefile no es un manifiesto de ficheros, porque los Makefiles tienen variables,
rutas relativas al padre, y nombres que envejecen.** Para preguntar qué ficheros hay, hay
que preguntar al sistema de ficheros, no a un `Makefile`.
