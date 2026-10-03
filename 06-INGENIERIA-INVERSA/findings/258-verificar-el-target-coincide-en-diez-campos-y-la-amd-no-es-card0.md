# 258 · Verificar el target: coincide en diez campos, y la RX 550 no es `card0`

```
CLASSIFICATION=MEASUREMENT+ERROR+CORRECTION · TRACK=VERIFICATION
CORPUS=NINGUNO (todo del HOST) · HARDWARE_SCOPE=READ_ONLY
WORK_CLASS=READ_ONLY/EVIDENCE · WRITE_LOCAL=PROPIOS · MODIFICATIONS_CORPUS=0
RUNTIME=READ_ONLY (sysfs, DMI legible, journalctl) · GPU INTACTA · CERROJOS=0
```

## Qué resuelve

El §3 del MASTER PROMPT declara un target y avisa, en la misma línea, de que son
"hipótesis iniciales hasta ser verificadas" y de que "no reemplazan un fingerprint
real". El §4 pone VERIFICAR TARGET antes de investigación crítica.

**No existía artefacto de fingerprint.** Se buscó con `find`, no se asumió:
`CURRENT-STATE.md` existe pero habla de correcciones entre hallazgos, no de
identidad de hardware.

Se creó `tools/fingerprint.py`, que es una **herramienta** y no un fichero escrito
a mano, por §35 REPRODUCIBILIDAD y §22 TOOL CONTRACT. 20 comprobaciones.

## 1 · El veredicto

```
TARGET_PARCIAL

  COINCIDE        cpu_model      Intel(R) Core(TM) i7-4790 CPU @ 3.60GHz
  COINCIDE        board          ECS H81H3-M4
  COINCIDE        gpu_id         1002:699f
  COINCIDE        gpu_nombre     Lexa PRO
  COINCIDE        igpu_id        8086:0412
  COINCIDE        driver         amdgpu
  COINCIDE        asic           POLARIS12
  COINCIDE        ip_gmc         gmc_v8_1_0   (ih_v3_0_0)
  COINCIDE        vram           2048 MiB
  COINCIDE        bar_registro   262144 bytes
  COINCIDE        ram_os_total   11.54 GiB

  NO_OBSERVADO    ram_instalado  dmidecode, DEFERRED_BY_PERMISSION
```

`TARGET_PARCIAL` y no `TARGET_MATCH` porque un campo no se ha observado. La
herramienta **no rellena ese campo con el valor declarado**, que es exactamente
lo que haría que un MATCH de este tipo no valiera nada.

## 2 · El hallazgo que tiene consecuencia: la AMD es `card1`

```
  /sys/class/drm/card0/device -> vendor 0x8086 device 0x0412   i915,  Haswell GT3
  /sys/class/drm/card1/device -> vendor 0x1002 device 0x699f   amdgpu, Lexa PRO
```

**La RX 550 es `card1`.** El nodo `0` es la integrada de Intel.

El proyecto tenía **dos convenciones** para la misma ruta y la equivocada estaba
en la documentación:

```
  herramientas.md:35    /sys/kernel/debug/dri/0/amdgpu_pm_info
  herramientas.md:99    cat /sys/kernel/debug/dri/0/amdgpu_register_read
  herramientas.md:101   radeon_reg ... /sys/kernel/debug/dri/0/

  revkit/mmo.py:51      DEBUGFS = "/sys/kernel/debug/dri/0000:01:00.0"   <- esta si
  revkit/captura.py:42  DEBUGFS = "/sys/kernel/debug/dri/0000:01:00.0"   <- esta si
```

Las tres primeras **apuntaban a la GPU equivocada**. Corregidas a la forma por
dirección PCI, que es la que ya usaba `revkit/`.

Y el motivo de fondo es que **`cardN` no está garantizado en ningún kernel**: es
el orden de sondeo de drivers, y en esta placa la integrada se prueba antes que la
discreta. Quien lo escriba como `card0` porque en *su* máquina funciona está
anotando un accidente.

```
  un numero de cardN es un dato de esta maquina, no del kernel
```

## 3 · `11.54 GiB` contra `12 GiB`: una discrepancia que inventé

La primera lectura dio `MemTotal = 11.54 GiB` contra un target de `12 GiB`, y
parecía una discrepancia del target. **No lo era.**

```
  Modulos instalados        4 GiB + 8 GiB = 12 GiB = 12.884.901.888 bytes
  /proc/meminfo MemTotal                11,54 GiB = 12.389.277.696 bytes
  diferencia                                  473 MiB  de reservas
```

Lo que `MemTotal` da es lo que el OS puede usar, no lo que está instalado. La
diferencia son las reservas del firmware y del IOMMU.

Eso tiene una consecuencia de diseño, y por eso el campo se llama
`ram_os_total` y hay **otro campo aparte** para lo instalado: si se comparan las
dos magnitudes contra un mismo target, aparece un `DIFIERE` sobre un target
correcto. **Un falso mismatch es peor que ningún mismatch**, porque se
"corrige" la cosa que está bien.

```
  lo instalado   dmidecode    root        NO_OBSERVADO, DEFERRED_BY_PERMISSION
  lo disponible  MemTotal     sin root    COINCIDE, 11.54 GiB
```

`sudo` pide contraseña en esta máquina y `/sys/firmware/dmi/tables/DMI` da
permiso denegado, así que lo instalado **no se ha medido** y se dice así.

Lo que `inxi` dice de los módulos es una **estimación**, y el propio `inxi` avisa
*"For most reliable report, use superuser + dmidecode"*. Por eso ese campo sale
`ESTIMADO` y no `COINCIDE`, con el motivo al lado. Un campo de target no se
rellena con una estimación sin marcar, porque a la semana ya nadie recuerda de
dónde salió.

## 4 · Sobre el iGPU: `Xeon E3-1200 v3` no contradice `HD 4600`

```
  lspci:  00:02.0  Intel Corporation Xeon E3-1200 v3/4th Gen Core Processor
                   Integrated Graphics Controller   [8086:0412]  (rev 06)
```

El §3 dice "Intel HD Graphics 4600". El device id `0x0412` es **Haswell GT3**, el
mismo dado que monta tanto el HD 4600 de consumo como el Xeon E3-1200 v3. No es
una discrepancia: es el mismo die con dos marcas.

La herramienta compara el **device id** y no el nombre de retail, y dice por qué
en el propio comparador. Un nombre de producto que depende del SKU habría producido
un `DIFIERE` falso, que es el error del §3 en una forma distinta.

## 5 · Confirmaciones de ejecución, no derivaciones

`201` y `183` dedujeron la versión de bloque **antes** de que existiera
el log de arranque capturado. Ahora hay `OBSERVED`:

```
  detected ip block number 1 <gmc_v8_1_0>   (gmc_v8_0)
  detected ip block number 2 <ih_v3_0_0>   (tonga_ih)
  detected ip block number 3 <gfx_v8_0_0>  (gfx_v8_0)
  detected ip block number 4 <sdma_v3_1_0> (sdma_v3_0)
  detected ip block number 5 <smu_v1_0_0>  (powerplay)
```

`gmc_v8_1_0` confirma `201` y `ih_v3_0_0` confirma `183`, con evidencia de
ejecución y no lectura de fuente.

Y `register mmio size: 262144` confirma `202`: la ventana de registros es 256 KiB.

## 6 · Los cuatro bugs que la herramienta tenía al salir por primera vez

Merecen la lista porque son la clase de error que el §8 prohíbe y que esta
herramienta cometió **antes de poder usarse**:

```
  1  leia el MISMO device id para la AMD y para la Intel. Buscaba el primer
     [vvvv:dddd] de `lspci -nn`, y la integrada va antes que la discreta.
     Daba 8086:0c00 dos veces con un DIFIERE que PARECIA un fallo de hardware.
     Corregido: los ids se leen de sysfs, que no depende del orden.

  2  el filtro de secuencias se COMIA los SALTOS DE LINEA. Con el rango
     [\\x00-\\x1f] completo, todo lscpu y todo /proc/meminfo quedaban en una sola
     linea, y ningun patrón con ^ de principio de linea podia casar nunca.
     Dos campos salian NO_OBSERVADO por una sola causa, y el sintoma decia
     "no se lee el fichero" sin senalar que el filtro habia roto el texto.
     Un filtro que destruye la estructura del texto no es un filtro de color.

  3  el nombre del patron de la IP pedia dos componentes y el driver escribe
     tres: cogia gmc_v8_1 donde pone gmc_v8_1_0, y comparaba con DIFIERE
     teniendo el valor correcto delante.

  4  el diccionario de fuentes se quedó con la clave vieja "ram" mientras
     CAMPOS pedia "ram_os_total": dos campos sin dato, en silencio.
```

Cada uno tiene ahora vector, y el del filtro comprueba que los saltos de línea
sobrevivan. Quitándole el rango, fallan tres vectores.

## 7 · Lo que NO se establece

```
  la RAM instalada por modulo    DEFERRED_BY_PERMISSION. dmidecode necesita
                                 contrasena y DMI en sysfs da permiso denegado.
                                 NO se sustituye por la estimacion de inxi
  el tipo de debugfs de la AMD   BLOCKED_BY_PERMISSION: no se puede montar ni
                                 leer /sys/kernel/debug. Por eso la correccion
                                 de las rutas es de NOMBRE, y la existencia
                                 concreta de amdgpu_pm_info NO esta comprobada
  la geometria de reloj y potencia
                                 NO MEDIDO, y fuera del §3
  si TARGET_PARCIAL basta        eso lo decide el plan de la iteracion, no la
                                 herramienta. Aqui solo se mide y se dice
```

## 8 · Trazabilidad

```
  tools/fingerprint.py              la herramienta, 20 comprobaciones, --json
  /sys/class/drm/card0/device       Intel 8086:0412
  /sys/class/drm/card1/device       AMD  1002:699f
  /sys/devices/virtual/dmi/id/*     board_vendor, board_name, bios
  /proc/meminfo                     MemTotal
  06-INGENIERIA-INVERSA/evidencia/boot-amdgpu-*.log   ASIC, IP, VRAM, BAR
  herramientas.md                   3 rutas corregidas, con el aviso puesto
  findings/201 / 202 / 183          corroborados con OBSERVED
```