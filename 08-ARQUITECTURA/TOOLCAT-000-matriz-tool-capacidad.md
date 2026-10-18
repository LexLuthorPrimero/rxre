# TOOLCAT — matriz TOOL → CAPACIDAD → ENTRADA → SALIDA → EVIDENCIA → GFX8 → ESTADO

```text
AGENCIA=RX550-INVESTIGACION · WORK_CLASS=AGENT-RE-TOOLING
GENERADO=2026-10-04 · MEDIDO=EN ESTA HOST · PROBE=ejecutado, no supuesto
FICHERO=este            · VERSION=1.0.0
PARTE DE=el catálogo maestro que pidio el propietario
```

## 0 · QUÉ ES ESTO Y QUÉ NO ES

El propietario pasó un catálogo de 23 secciones y ~200 herramientas. Este
documento **no es el catálogo**: es la **medición de qué hay realmente
instalado**, porque el catálogo enumera lo que existe en el mundo y el
`§22 TOOL VALIDATION` del proyecto exige distinguir *herramienta que existe* de
*herramienta medida y funcional*.

**Todo lo de la columna ESTADO está medido en esta máquina**, con `command -v`
y con ejecución real. Lo que no se pudo ejecutar dice por qué.

```text
  ESTADO de una herramienta
     PRESENTE      el binario existe, ejecutado al menos una vez
     PRESENTE*     existe pero NO ejecutada en esta sesion
     AUSENTE       no esta en el sistema
     NO_APLICA     no tiene sentido en este host (build de kernel, etc)
```

**El criterio de inclusión es estricto:** una herramienta entra en la matriz si
produce **evidencia sobre la RX550** que hoy no produce otra. Un desensamblador
más, sin objetivo, no entra.

## 1 · LA MATRIZ

```text
ID    HERRAMIENTA        CAPACIDAD QUE APORTA                  ENTRADA -> SALIDA              GFX8?  ESTADO
----  -----------------  -------------------------------------  ---------------------------  -----  --------

== ORACLE DE REGISTROS (el hallazgo de esta sesion) ==

R01   umr database       bits y offsets de registro, campo a   .reg de /usr/share/umr      SI     PRESENTE
                           campo, INDEPENDIENTE del driver      -> nombre de campo + bits
      /usr/share/umr/     PROVEN: 4 de 4 offsets GMC medidos                              (1459)
      database/ip/*.reg   desde la fuente coinciden con umr

R02   polaris12.asic      mapa de familias y bloques de la     .asic -> lista de .reg      SI     PRESENTE
                           ASIC, declara gmc810/gfx800/oss300                           (1459)

== DECODIFICACION DE PM4 / IB ==

P01   tools/pm4tila.py    troceado de IB en paquetes, con       IB binario -> tabla de      SI     PRESENTE*
      (propio, 1.1.0)     el handoff dword-a-dword validado    paquetes con offsets           31 vectores
P02   PACKET3 el layout   PACKET3: tipo en [15:8], cuenta en    cikd.h:229-231 -> el layout SI     PRESENTE
                           [29:16]. PROVEN por dato y por                                 (1412,1459)
                           fuente externa (intel-gpu-tools)

== ALCANCE Y ALCANZABILIDAD (lo que mas hallazgos ha dado) ==

A01   tools/unreach.py    prueba de alcanzabilidad de un        simbolo -> PROVEN            SI     PRESENTE*
      (de otra sesion)    puntero de tabla de dispatch         alcanzable / INALCANZABLE
                           PRODUJO: 1166, 1177, 1178, 1403                              (propio)
A02   grep con alcance    "quien INSTALA la tabla" vs          tabla -> tabla que corre     SI     PRESENTE
                           "quien la invoca"                   en esta ASIC                  (propio)
                          DISTINGUE POR SERIE, no por nombre de fichero
                           PRODUJO: 1403, 1452 (subagente)
A03   lectura de COMENTARIOS  el driver explica en un         fichero -> la respuesta       SI     PRESENTE
      (metodo, no tool)   comentario lo que uno busca en 4     que unoiba a pedir al HW
                           lineas de codigo
                           PRODUJO: 1430 (corrigio a 1404)

== SOURCE / BUSQUEDA ==

S01   rg (ripgrep)        busqueda transversal en el corpus   patron -> ficheros:linea   SI     PRESENTE*
S02   git                  historial del corpus               commit -> diff               SI     PRESENTE*
S03   GNU Global / ctags  indice de simbolos del corpus       simbolo -> usos             SI     AUSENTE
S04   Coccinelle           transformacion de codigo, semantica patron -> parche     SI     AUSENTE
S05   clang-query / AST    consultas sobre el AST real        AST -> respuesta            SI     AUSENTE
      (clang-tidy solo)

== BINARY / DWARF ==

B01   readelf/objdump      ELF, secciones, simbolos            binario -> estructura       SI     PRESENTE*
B02   pahole + BTF viva    tipos reales del kernel vivo       /sys/kernel/btf/amdgpu     SI     PRESENTE*
      /sys/kernel/btf/     NO es el corpus: es el kernel vivo,                     (medido 2026-10-04)
      amdgpu               que es una fuente DISTINTA
B03   llvm-dwarfdump       igual que B01 para DWARF            binario -> tipos           SI     AUSENTE

== GPU ISA ==

G01   LLVM AMDGPU backend compilar shader a ISA GFX8         shader -> ISA               SI     AUSENTE
G02   RGA                  lo anterior, con estadisticas      shader -> ISA + recursos    SI     AUSENTE
G03   CLRadeonExtender     desensamblado de binarios GCN      binario -> ISA             SI     AUSENTE
      clrxdisasm

== RUNTIME (bloqueado por credenciales, no por decision) ==

T01   umr (ejecutable)     LECTURA de registros MMIO          registro -> valor           SI     PRESENTE*
      /usr/bin/umr         requiere root: sudo pide password                              (bloqueado)
T02   umr --ring-stream    volcado y DECODIFICADO del anillo  ring -> paquetes           SI     PRESENTE*
                           cruzaria mi decodificador propio
T03   debugfs dri/         registros, anillos, VRAM            fichero debugfs -> datos    SI     PRESENTE*
      /sys/kernel/debug/   Permiso denegado sin root                               (medido)
T04   drgn / crash / kgdb  estado del kernel vivo             kernel -> estructura       SI     AUSENTE
T05   bpftrace / trace-cmd traza de eventos                  kernel -> eventos          SI     PRESENTE*
T06   perf / turbostat     potencia, frecuencia, temperatura   sysfs/hwmon -> telemetria  SI     AUSENTE

== VBIOS / SMU (rama que NO se abre ahora) ==

V01   SRBPolaris / PBE     edicion de ROM                     ROM -> tabla                SI     AUSENTE
V02   UPP                   tablas PowerPlay                   ROM -> PowerPlay            SI     AUSENTE
V03   YAABE                 estructura AtomBIOS completa      ROM -> estructura          SI     AUSENTE
V04   amd_smu_reverse_eng   firmware SMU                       ROM -> mensajes             SI     AUSENTE
      NOTA: hay un hallazgo 1406 de otro nodo sobre VRAM leida de ROM.
      La rama VBIOS la sigue otro nodo: NO la duplico.

== GENERACION PROPIA (las que si justifico construir) ==

G-1   regalias.py           CATALOGO DE ALIASING y su INVERSO addr <-> simbolo, con  SI     VALIDADO
      (propio, 1.0.0)      procedencia hasta el FICHERO, que es     bloque y generacion      33 vectores
                           donde esta la desambiguacion real                               (1470)
                           Mide: 26,75 % de las direcciones en >1 bloque,
                           31,14 % de los simbolos en >1 direccion. Ningun
                           numero unico: hace visible la ambiguedad.
                           Detecta tambien el fallo de padding que produce
                           NOT_FOUND falsos (9197 simbolos).
                           Modo nuevo --simbolo (inverso), --cabecera (fija ASIC)
G-2   alcance.py           Dispatch real por ASIC              corpus -> tabla que corre   SI     NO EXISTE
                           generaliza A02 y lo hace repetible
G-3   ptediff.py            diff de tablas de paginas entre    dump A, dump B -> delta    SI     NO EXISTE
                           dos instantes
G-4   reach-mmio.py         lectura MMIO de solo lectura,       registro -> valor + hash   SI     NO EXISTE
                           con registro de procedencia        POR HACER cuando haya
                                                                        credenciales
G-5   scope-asic.py        Subconjunto de cabeceras que        polaris12.asic ->          SI     NO EXISTE
      (propuesto, 1470)     APLICA a esta ASIC, para quitar      lista de ficheros         ABRE un hueco
                           la ambiguedad de 26,75 %             con el bloque/generacion
                           El hueco ya esta MEDIDO: la generacion
                           solo esta en el nombre del fichero y
                           nadie lo lee.  Es el siguiente paso natural.
```

## 2 · LO QUE LA MEDICION CAMBIA RESPECTO AL CATALOGO DEL PROPIETARIO

**Cinco cosas, y ninguna es «añadir una herramienta».**

**1. El oráculo que faltaba ya estaba instalado.** El catálogo no lo menciona:
`umr` viene con un database de registros en `/usr/share/umr/database/`, y es la
única fuente independiente de los bits de un campo. Con él cerré `1440` §4 sin
hardware. **La pieza de más valor de esta tanda vino con el paquete ya
instalado.**

**2. El agujero de la lista es `si.h`, y es un stub.** El catálogo propone
`PACKET3 el layout` y fuentes de referencia; el problema real es que **las
cabeceras de macros PM4 del corpus están vaciadas a 2 defines** (`1421` §6). Ninguna
herramienta de la lista arregla eso: falta el fichero. **Un catálogo de 200
herramientas no sustituye a un fichero de 1 KB que falta.**

**3. `S03`, `S04`, `S05` son las de mayor retorno y no están instaladas.**
Coccinelle y clang-query operate sobre el AST, que es lo que convierte
«contar menciones» en «contar invocaciones» — **el error que ha producido cinco
correcciones seguidas en esta sesión.**

**4. El bloque runtime no es un problema de herramientas.** `umr`, debugfs,
`bpftrace` **están instalados**. Falta el permiso. **Una herramienta ausente se
puede instalar; un permiso ausente hay que pedírselo al dueño.**

**5. VBIOS es otra rama y tiene dueño.** Hay un `1406` de otro nodo sobre la
ROM. Abrirla sería `DEPENDENCY BLOCK` duplicado.

## 3 · EL ORDEN, Y POR QUÉ NO ES EL DEL CATALOGO

```text
  AHORA, sin credenciales y sin depender de nadie
     1. G-1 regalias.py    HECHO.  VALIDADO, 33 vectores, 3 de 3 cross-check
     2. G-5 scope-asic.py  el siguiente natural: la ambiguedad que queda es
                           de GENERACION, y `polaris12.asic` dice cual aplica.
                           Convierte 26,75 % de ambiguedad en un subconjunto
                           aplicable a ESTA tarjeta.  Falta la columna de
                           generacion -> fichero, y ahi esta el hueco.
     3. G-2 alcance.py    convierte A02 (que hice a mano 3 veces) en herramienta
     4. S01 rg             ya esta; lo que falta es el HABITO de usarlo con alcance,
                           no la herramienta.  Y con `--`-word-boundary y el
                           padding en cuenta, que es lo que midio 1470.
     5. A03               leer comentarios: metodo, coste cero, ya dio 1430

  EN CUANTO HAYA CREDENCIALES (un viaje)
     6. T01 umr -r         cierra TODOS los NOT_DETERMINED de lectura de registro
     7. T02 umr --ring     cruza mi decodificador propio contra el de referencia
     8. G-4 reach-mmio    convierte el punto 6 en evidencia repetible

  RAMAS QUE NO ABRO YO
     V01-V04  VBIOS/SMU: otro nodo
     T04/T06  kernel debugging y telemetria: sin hardware accesible todavia
```

## 4 · EL CRITERIO DE INCLUSIÓN, ESCRITO PARA PODER DISPUTARLO

```text
  Una herramienta entra en la matriz si cumple las tres:

  1. produce EVIDENCIA sobre ESTA RX550
     (no «informacion en general sobre GPUs AMD»)

  2. no produce lo que YA produce una herramienta de la matriz
     (si la duplica, se integra con la existente, no se instala)

  3. su COSTE es justificable con el hueco que cierra
     (§99 NO TOOL THEATER: sin hueco medido, no entra)
```

**Y el criterio de salida, que también hay que escribir:**

```text
  Una herramienta SALE de la matriz, y se marca RETIRED, cuando:

  - su unico uso fue duplicar otra
  - el hueco que cubria lo cerro otra via
  - el corpus dejo de existir (cambio de version)
  - se demostro que no aplica a GFX8
```

**Ninguna herramienta de esta matriz ha sido retirada todavía.** Y eso hay que
decirlo: **la matriz tiene cerotools retiradas porque tiene menos de un mes de
vida y casi todo es recien medido.**

## 5 · ESTADO DE ESTE DOCUMENTO

```text
  VERSION 1.0.0
  MEDIDO   2026-10-04, en esta host
  ALCANCE  solo lo que produce evidencia sobre CHIP_POLARIS12
  NORMATIVO  §24 TOOL VALIDATION: una herramienta no es valida porque ejecuta
             aqui esta PRESENTE / PRESENTE*, no PROVEN. Lo validado son las
             herramientas PROPIAS, con vectores.
  PENDIENTE  auditar el estado de las marcadas PRESENTE* cuando se usen
  PROXIMO   G-1 registro2.py, que es la unica que responde a un hueco YA medido

  NO es un catalogo de lo que existe en el mundo. Es lo que HAY aqui, medido.
```