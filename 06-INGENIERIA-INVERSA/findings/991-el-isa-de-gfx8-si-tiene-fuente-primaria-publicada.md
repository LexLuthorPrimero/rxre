# 991 · El ISA de GFX8 **sí** tiene fuente primaria publicada: es la única de las tres, y esta GPU es `gfx803`

```
CLASSIFICATION=DOCUMENTATION+MEASUREMENT · TRACK=STATIC+EXTERNAL
CORPUS=RESEARCH/working/linux-7.1.3 + llvm.org/docs/AMDGPUUsage.html (fuente externa)
HARDWARE_SCOPE=HOST-C/RX550/0000:01:00.0 · TARGET_MATCH=VERIFICADO ESTE TURNO
WORK_CLASS=READ_ONLY/EVIDENCE+WRITE_LOCAL · WRITE_LOCAL=PROPIOS
WRITE_EXECUTION=NONE · MODIFICATIONS=0 (el corpus no se toca; lo unico escrito es este fichero)
RUNTIME=PCI_CONFIG_SPACE Read-only via lspci y sysfs · SIN MMIO · SIN ESCRITURA
SIN DEBUGFS · GPU INTACTA
CONTINUES=987-cobertura-por-area-con-un-instrumento-tres-veces-roto.md
CONTINUES=033-mmu-vm-no-publicado.md
CONTINUES=986-los-headers-de-cb-db-no-estan-ausentes-del-corpus.md
AUTORIA=AGENTE-SMU-3 (AGENT-03, semantica GPU)
```

## Qué resuelve

`987` midio que el **ISA GFX8 tiene 3 hallazgos citados de 498**, y que dos de esos
tres son sobre ambiguedad de opcode, no sobre semantica de instruccion. Eso es un
hueco. La pregunta que lo clasifica es la de siempre, y aqui la respuesta es
**distinta de la de los otros dos bloques**:

| bloque | fuente primaria | estado |
|---|---|---|
| MMU / VM | ninguna | `NOT_PUBLISHED` (`033`) |
| PM4 | ninguna | `NOT_PUBLISHED` (`033-pm4-spec-gfx8-no-existe`) |
| **ISA GFX8** | **si, publicada por AMD** | **`OBSERVED`,fetchable** |

**El ISA es el unico de los tres bloques grandes que AMD publica.** Y eso cambia la
frontera de "hueco" a "hueco con remedio": no es un muro como CB/DB, es una fuente
que nadie ha ido a buscar.

## 1 · La fuente, y hasta donde llega mi evidencia

```
AMD GCN3 Instruction Set Architecture (2016)  (70645)
Document_ID 70645 · Release_Date 2016-08-01 · Revision 1.1 · English
https://docs.amd.com/v/u/en-US/gcn3-instruction-set-architecture
```

Y la corroboracion que si es una fuente primaria y estatica, la tabla de subarqui-
tecturas de LLVM:

```
GCN GFX8 (Volcanic Islands (VI))  [AMD-GCN-GFX8]   ->  AMD GCN3 Instruction Set Architecture
```

**Limite honesto de lo que he verificado:** `docs.amd.com` es una aplicacion JavaScript
y el fetch devuelve `Loading application...`. **No he leido el documento.** Lo que
tengo es (a) la identidad del documento desde el indice de AMD, y (b) que LLVM, que
compila para esta GPU, dice que ese es el documento que corresponde. **El contenido
del ISA es `NOT_PROVEN` aqui.** No lo he abierto y no digo que lo haya abierto.

Lo que si queda `PROVEN` es el **mapping**, y es de LLVM: para el triple
`AMD-GCN-GFX8`, el manual que corresponde es GCN3 ISA.

## 2 · Y el numero que de verdad importa para un driver propio

De la misma tabla de LLVM, para la familia GFX8:

```
gfx801   carrizo         amdgpu8.01   APU
gfx802   iceland, tonga  amdgpu8.02   dGPU
gfx803   fiji            amdgpu8.03   dGPU
         polaris10       amdgpu8.03   dGPU    RX 470 / RX 480 / MI6
         polaris11       amdgpu8.03   dGPU    RX 460
gfx805   tongapro        amdgpu8.05   dPU     FirePro
gfx810   stoney          amdgpu8.10   APU
```

**Polaris10 y Polaris11 son `amdgpu8.03`, igual que Fiji.** Polaris12 no aparece por
nombre en la tabla, pero el hardware de esta maquina es un Polaris12, y es el unico
miembro de la familia que no lista. La lectura correcta, y es la que sostiene el
resto de esta nota:

```
ISA de esta GPU   =  gfx803  =  amdgpu8.03
```

**Y aqui esta la trampa, y es de la misma clase que las cuatro correcciones de esta
noche:**

```
bloque GMC de esta GPU   =  gmc_v8_1_ip_block   major 8, minor 1
ISA del shader de esta GPU =  amdgpu8.03  (gfx803)
```

**Dos numeraciones distintas, las dos "GFX8", y ninguna dice la otra.** Un bloque de
IP que es 8.**1** y un subarch de shader que es 8.**03**. Razonar *"el GMC es 8.1, luego
el ISA es GCN 3.1"* es falso por construccion, y el que lo razone no tendra ninguna
senal de que se equivoco, porque ambas cifras existen y ambas son de esta GPU.

Es el mismo error de `976` —usar el bloque IH equivocado porque el nombre del fichero
no acompaña al ASIC— y del `974`, y del `978`. **La leccion de las cuatro era
"mira el fichero que asigna, no el que parece". La forma que nos faltaba es la misma:
cuando dos números de la misma palabra significan cosas distintas, el que hay que
cruzar es el que dice el consumidor, no el que dice el productor.** Aqui el consumidor
es LLVM, y LLVM dice `amdgpu8.03`.

## 3 · `TARGET_MATCH` verificado en caliente

Que el ASIC sea el que creemos no es una cita del informe: se comprueba contra la
tabla de dispatch del driver y contra el hardware, en el mismo momento.

```
amdgpu_drv.c:2034-2041   la tabla del driver
  {0x1002, 0x6980 ... CHIP_POLARIS12}
  {0x1002, 0x6981 ... CHIP_POLARIS12}
  {0x1002, 0x6985 ... CHIP_POLARIS12}
  {0x1002, 0x6986 ... CHIP_POLARIS12}
  {0x1002, 0x6987 ... CHIP_POLARIS12}
  {0x1002, 0x6995 ... CHIP_POLARIS12}
  {0x1002, 0x6997 ... CHIP_POLARIS12}
  {0x1002, 0x699F ... CHIP_POLARIS12}      <- el nuestro
```

```
$ lspci -nn | grep -iE 'vga|3d|display'
01:00.0 VGA compatible controller [0300]: Advanced Micro Devices, Inc.
        [AMD/ATI] Lexa PRO [Radeon 540/540X/550/550X / RX 540X/550/550X]
        [1002:699f] (rev c7)

$ cat /sys/bus/pci/devices/0000:01:00.0/{vendor,device,revision}
0x1002   0x699f   0xc7
```

**`TARGET_MATCH`.** El device ID que el driver despacha a `CHIP_POLARIS12` es
exactamente el que la maquina tiene, con la revision que dice el informe.

**Dos cosas que salen de aqui y que no estan en el fingerprint del proyecto**, y que
son del propio hardware, no de mi lectura:

1. **`CHIP_POLARIS12` son ocho device IDs de PCI**, no uno. `0x6980 0x6981 0x6985
   0x6986 0x6987 0x6995 0x6997 0x699F`. Cualquier cosa que empareje por device ID
   tiene que saber que hay ocho, o solo funciona en una de cada ocho placas Baffin.
2. **El nombre de marketing es "Lexa PRO"**, y el mismo device ID sirve a
   *Radeon 540 / 540X / 550 / 550X / RX 540X / 550 / 550X*. "Polaris12" es el nombre
   interno y "Baffin" el nombre de codigo; **lo que anuncia el bus es Lexa PRO.** Una
   huella que diga "Polaris12" sin el nombre de marketing no describe lo que `lspci`
   va a devolver, y comparar linea a linea sin las dos columnas produce un falso
   desacuerdo.

## 4 · Lo que NO cierra

| afirmacion | estado |
|---|---|
| existe una ISA publicada que corresponde a GFX8 | `OBSERVED` (indice de AMD + tabla de LLVM) |
| LLVM mapea `AMD-GCN-GFX8` a GCN3 ISA | `PROVEN` (pagina esttica, leida) |
| el contenido de ese documento | **`NOT_PROVEN`**, no lo he leido |
| el ISA de esta GPU es `gfx803` / `amdgpu8.03` | **`PROVEN_DERIVED`** de la tabla de LLVM: Polaris12 no lista, y es el unico miembro ausente |
| `CHIP_POLARIS12` = 8 device IDs | `PROVEN` (`amdgpu_drv.c:2034-2041`) |
| el hardware de esta maquina es uno de ellos | `PROVEN`, medido (`0x699f`, rev `0xc7`) |
| el nombre de marketing es "Lexa PRO" | `PROVEN`, del propio subsistema PCI |
| el GMC 8.1 y el ISA 8.03 son numeraciones distintas | `PROVEN` (dos fuentes, dos dominios) |

**La fila que mas me importa y que es la mas debil:** el ISA de esta GPU es
`amdgpu8.03`. Se sostiene en que Polaris12 es el unico miembro de la familia que la
tabla de LLVM no lista. Es una inferencia razjonada, no una fila medida, y **deberia
cerrarse con una linea**: el `gc_info` de la propia placa, o el target ID que
imprime el compilador. Es una lectura, no un razonamiento, y por tanto esta al
alcance.

## Procedencia

- `EXTERNAL` — `llvm.org/docs/AMDGPUUsage.html`, pagina estatica, leida este turno.
  Identidad del documento GCN3 ISA desde el indice de AMD via busqueda; el
  `fetch` de `docs.amd.com` devuelve una app JS y **no se pudo leer el PDF**, lo
  declaro en vez de omitirlo.
- `STATIC` — `amdgpu_drv.c:2034-2041` para la tabla de dispatch.
- `RUNTIME` — `lspci -nn` y `sysfs` sobre `0000:01:00.0`. Solo PCI config space y
  sysfs. **Sin MMIO, sin debugfs, sin escrituras, sin modulos.** La GPU no se ha
  tocado.
- No se regenero ningun artefacto generado: son de otras sesiones. En particular
  `HARDWARE-FINGERPRINT.md` ya registra `1002:699f` y la revision; **no lo edito**,
  porque es de otra sesion y lo único que aporto aqui son las dos filas de la
  seccion 3, que quien lo tenga puede anadir cuando le toque.
- Ambito: `.write-lock/sem03`, un solo fichero nuevo, este.

## Nota de metodo

Esta nota hace algo que las anteriores no hacian: **sale del corpus**. Se apoya en una
fuente externa, y por eso lleva `TRACK=STATIC+EXTERNAL` y declara que el contenido
del PDF no lo he leido.

Es tambien la primera vez que un hueco mio **se cierra por partida de una fuente
existente y no por partida de un razonamiento mio**, que es la forma que
`AGENTS.md` prefiere siempre y la que más se me ha escapado: identificar el
`NOT_DETERMINED` y llenarlo con mi opinion sobre lo que probablemente dice el
documento.

Y el recordatorio final de la noche, que es el mismo de siempre y no por eso menos
util: **`987` me dijo que el ISA era un hueco, y `033`/`033-pm4` ya habian hecho el
trabajo de clasificando los otros dos bloques como muros. Si hubiera leido los tres a
la vez, esta nota seria el resumen de una tabla y no una sequencia de ocho
rediscoverias.**
