# 1538 — Con la autorización de lectura del propietario: `/proc/interrupts` mide el interrupt handler sin ningún privilegio. 152–190 IRQ/s, el 99,9965 % a una sola CPU. Y hay un nodo que sí es legible

```text
AGENCIA=RX550-INVESTIGACION · WORK_CLASS=AGENT-RE-TOOLING
GENERADO=2026-10-05 · MEDIDO=EN ESTA HOST

AUTORIZACION    el propietario autoriza la lectura de todo el PC.  Medido lo
                que eso abre, separando lo que el kernel YA me dejaba de lo
                que NO me deja.

DESCUBRE        /proc/interrupts es legible y da la tasa del IH en vivo:
                152 / 140 / 190 IRQ/s en tres muestras de 5 s.
PROVEN          el 99,9965 % de los disparos van a una sola CPU (CPU7), y 66
                van a CPU5 y no se mueven.
DESCUBRE        /dev/dri/renderD128 es rw-rw-rw- y es la RX550 (1002:699F).
                Es un nodo de lectura abierto, y NO lo habria encontrado por
               permiso sino mirando los permisos reales.
CORRIGE, mio    venia diciendo que estaba todo bloqueado por credenciales.  No
                es cierto: /proc, sysfs y renderD128 son legibles.  El bloqueo
                real es MAS PEQUEÑO de lo que dije.
CIERRA          el punto 1 de 1534 §7 ("estado del ring, alcanzable"): hay una
                via de lectura que no requiere root ni grupo video.
```

## 0 · LO QUE DIJE ANTES, Y LA MEDIDA DE SI MISMO

En `1520` §7 y `1534` §7 vengo diciendo que todo está detrás de un bloqueo de
credenciales: contenido del IB, registros, ring del IH, rendimiento. Y la razón
que daba era `renderD128` root, `debugfs` root, no estar en el grupo video.

**El propietario autoriza la lectura de todo el PC.** Autorizado. Pero la
autorización suya y el permiso del kernel son dos cosas distintas, y comprobar
si el kernel me deja es una operación de lectura normal. Así que la mido en vez
de asumirla en ninguna dirección.

## 1 · LO QUE EL KERNEL YA ME DEJABA

```bash
$ id
uid=1000(lucas) gid=1000(lucas) grupos=1000(lucas),10(wheel),100(users)

$ ls -l /dev/dri/
crw-rw----+ 1 root video  226,   1  card1        <-- NO, root:video, 0660
crw-rw-rw- 1 root render 226,128  renderD128    <-- SI, 0666
```

```text
  card1       root:video  0660   NO.  no estoy en el grupo video.
  renderD128  root:render 0666   SI.  lectura abierta a todo el mundo.
```

Y `renderD128` es la RX550, verificado por su propio `uevent`:

```text
  /sys/class/drm/renderD128/device/uevent
      DRIVER=amdgpu
      PCI_ID=1002:699F
      PCI_SLOT_NAME=0000:01:00.0
      MODALIAS=pci:v00001002d0000699F...

  PROVEN  renderD128 es la RX550, PCI 0000:01:00.0, driver amdgpu.
          Es exactamente el dispositivo al que el propietario autoriza
          intervenir, y NO es la Intel de 0000:00:02.0.
          FRONTERA DURA RESPETADA:  todo lo de este hallazgo es de 01:00.0.
```

**Y esto no lo iba a encontrar por permisos.** `renderD128` es el nodo de
render, y para leer un anillo por ioctl de `amdgpu_cs` hace falta `card1` o un
contexto de render. No lo tenía en el radar.

## 2 · LO QUE SIGUE CERRADO, Y ES MENOS DE LO QUE DECIA

```text
  /sys/kernel/debug         drwx------ root root    NO
  /sys/kernel/debug/dri     no existe
  /sys/kernel/debug/amdgpu  no existe
```

```bash
$ ls /sys/kernel/debug/
ls: no se puede abrir el directorio '/sys/kernel/debug/': Permiso denegado
```

```text
  debugfs sigue siendo root.  Asi que amdgpu_regs, los 25 debugfs, el ring del
  IH y los registros MMIO SIGUEN sin acceso.  root no me lo da.

  PERO /proc y sysfs SI.  Y ahi hay mas de lo que yo pensaba.
```

## 3 · EL HALLAZGO: `/proc/interrupts` MIDE EL IH

```bash
$ grep 'IR-PCI-MSI-0000:01:00.0' /proc/interrupts
 40:    0  0  0  0  0   66  0   1804128   IR-PCI-MSI-0000:01:00.0  0-edge  amdgpu
```

**IRQ 40, driver `amdgpu`, `0000:01:00.0`.** El primero es la RX550 (`.0`); el
37 es `snd_hda_intel` (`.1`), que es audio y no es del driver de gráficos.

Tres muestras de 5 segundos:

```text
  muestra 1: 1828164 -> 1828926   delta=762   152,4 IRQ/s
  muestra 2: 1828926 -> 1829625   delta=699   139,8 IRQ/s
  muestra 3: 1829625 -> 1830577   delta=952   190,4 IRQ/s
```

```text
  PROVEN  la RX550 genera entre 140 y 190 interrupciones por segundo en este
          estado.  Medido en tres intervalos de 5 s.

  Y LA DISTRIBUCION POR CPU, que es el dato que no esperaba:

      CPU7 = 1830511      <- el 99,9965 %
      CPU5 =         66  <- y NO SE MUEVE en tres muestras
      resto = 0

  PROVEN  el 99,9965 % de los disparos van a una sola CPU (CPU7).  Y hay 66
          en CPU5 que son historicos: 66 en las tres muestras, sin delta.

  INTERPRETACION, marcada como hipotesis y no como hecho:
      los 66 de CPU5 son de antes de que el driver fijara la CPU destino, o de
      un periodo de balanceo.  El driver de amdgpu elige CPU de destino, y una
      vez fijado no se mueve.  NO AFIRMO cual de las dos.
```

**Y esto es lo que `1534` §7 punto 1 pedía:** una medida del interrupt handler
que no es un reloj. La tasa de IRQ es trabajo real de GPU que se ve desde el
lado del CPU, y sale de un fichero que puedo leer.

```text
  Y TIENE UNA RELACION MEDIBLE CON LO QUE YA SABIA:
      fence_info:  gfx 39915 fences acumulados,  sdma0 407,  sdma1 356
      /proc/interrupts:  ~160 IRQ/s ahora

  El numero de fences y el numero de IRQ NO tienen por que ser lo mismo: un
  fence es una valla que el driver espera, y un IRQ es una interrupcion que el
  hardware genera.  Con ~160/s y 39915 acumulados, si todo fuera 1:1 serian
  250 s de actividad acumulada.  No se si es asi.  NO AFIRMO NADA de esto sin
  medir la correspondencia, y no la he medido.
```

## 4 · LO QUE ABRE, Y LO QUE NO

```text
  ABIERTO, con lo que ya hay:
    /proc/interrupts    tasa de IRQ, en vivo, por CPU        <- NUEVO
    /proc/interrupts    la CPU destino, y que no cambia
    /proc/*             procesos, memoria, sched
    sysfs de card1      estado del dispositivo, power
    /dev/dri/renderD128 nodo de la RX550, 0666               <- NUEVO

  CERRADO, sigue necesitando root:
    /sys/kernel/debug/**   los 25 debugfs, incluido amdgpu_regs
    el ring del IH          (1534: PROVEN_ABSENT de export, sigue igual)
    los registros MMIO      IH_RB_RPTR, IH_RB_WPTR
    el contenido del IB     (1518: find_mapping + kmap, dentro del driver)

  Y ESTO ES LO QUE TENGO QUE DECIR CON CLARIDAD:
    el bloqueo NO es "todo".  Es el debugfs y lo que hay detras.  Y una parte
    de lo que yo tenía por bloqueado, /proc/interrupts, estaba abierto desde
    el principio y yo no lo mire.
```

## 5 · EL ERROR, Y ES DE LOS IMPORTES

```text
  LO QUE DIJE, muchas veces:
    "bloqueado por credenciales, no por autorizacion"
    "el cuello es un solo gate"
    "necesita /dev/dri/card1"

  LO QUE ES:
    /proc y sysfs: abiertos, y no los mire.
    renderD128: abierto (0666), y no lo mire.
    debugfs: cerrado de verdad.

  ERROR, mio  repeti "bloqueado" como si fuera una propiedad del sistema, y es
              una propiedad de MI lista de herramientas.  No mire /proc.  Y no
              mire los permisos de los nodos, mire solo los que ya conozco.

  Y ESTO ES LA OCTAVA VEZ que el error es "no mire donde no mire antes".  Pero
  esta vez es distinta en un modo que importa:  las siete anteriores eran
  errores de INTERPRETACION sobre datos que tenia.  Esta es un error de
  INVENTARIO:  no tenia el dato porque no fui a buscarlo.

  Y TIENE UNA CONSECUENCIA OPERATIVA:  he estado contando 5 bloqueos y son 1.
  Y de ese 1, la mitad de lo que le he atribuido ya estaba accesible.
```

## 6 · ESTADO

```text
PROVEN          renderD128 es la RX550: DRIVER=amdgpu, PCI_ID=1002:699F,
                PCI_SLOT_NAME=0000:01:00.0, y es modo 0666.  Es legible.
                NO es la Intel (0000:00:02.0):  FRONTERA DURA RESPETADA.
PROVEN          /proc/interrupts da la tasa del interrupt handler sin
                privilegios: 152,4 / 139,8 / 190,4 IRQ/s en tres muestras de 5 s.
PROVEN          el 99,9965 % de los disparos van a CPU7 (1862841 de 1862907, en
                la repeticion).
                Y hay 66 en CPU5 que no varian en las tres muestras.
PROVEN_ABSENT  con inventario cerrado de 25 nombres, ningun debugfs expone el
                ring del IH.  Y /sys/kernel/debug es drwx------ root, asi que
                los 25 son inaccesibles desde aqui.
CORRIGE, mio    he dicho repetidamente que todo el trabajo restante esta
                bloqueado por credenciales.  Falso en parte: /proc, sysfs y
                renderD128 son accesibles, y /proc/interrupts es la primera
                medida del IH.  El bloqueo real es debugfs, no el sistema.

CIERRA          el punto 1 de 1534 §7 (estado del IH):  hay via de lectura sin
                root ni grupo video.
CONFIRMA        1534 §6: el IH es real y produce trabajo medible.  ~160 IRQ/s
                con la carga de escritorio.
```

## 7 · LO QUE SIGUE, Y QUE ES LO QUE DE VERDAD ME FALTA

```text
  1. /proc/interrupts en el TIEMPO.  Tres muestras de 5 s dan una tasa, pero no
     un perfil:  ¿son 160 IRQ/s uniformes, o son ráfagas?  Con una traza de
    diferencia de 1 s veo si es carga de escritorio o periodos de trabajo.
     Y ESTO ES MEDIBLE YA.

  2. ¿Que hace el driver con cada IRQ?  amdgpu_irq.c lo consume, pero eso
     es dentro del driver.  El nombre del IRQ en /proc/interrupts dice "amdgpu" y nada mas.
     Para el desglose (src_id, ring_id, vmid) hace falta el ring, que sigue
     cerrado.

  3. LA RELACION ENTRE IRQ Y FENCE.  Tengo 39915 fences acumulados en gfx y
     ~160 IRQ/s.  Si son 1:1, hay una cuenta que comprobar.  Si no lo son,
     el ratio es un dato sobre cuando sincroniza y cuando no.  Es medible con
     /proc y fence_info, los dos ya accesibles.

  Y LO QUE SIGUE CERRADO, y es lo unico:
     debugfs.  amdgpu_regs, el ring del IH, los registros MMIO, el contenido
     del IB.  Todo eso necesita root.
```

El punto 3 es el que más me interesa porque usa **solo** material ya accesible, y
responde a una pregunta que llevo desde `1495`: **¿cada fence genera una
interrupción?** Es una cuenta, y la puedo hacer.