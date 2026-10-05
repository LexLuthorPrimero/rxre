# 1231 — `fb0` es de la **RX550**, no de la Intel, y `0000:00:02.0` **no existe en el bus PCI**. La premisa de seguridad sobre la que se decidió la frontera no se sostiene

```text
AGENCIA=RX550-INVESTIGACION · WORK_CLASS=CONTRADICTION · HARDWARE-FINGERPRINT
AUTOR=AGENTE-INSTR
WRITE_EXECUTION=NONE · GPU=NONE TOUCHED · RUNTIME=NOT_RUN
DISPOSITIVO_TOCADO=NINGUNO · ni 0000:01:00.0 (1002:699f) ni 0000:00:02.0 (8086:0412)
ESCRITOS_POR_ESTA_ITERACION   ninguno (solo lectura)
CIERRA   nada.  ABRE una contradiccion contra el estado registrado
CONTRADICION   la nota de autorizacion del arbol afirma
               "fb0 = i915drmfb, 1366x768.  La RX550 no tiene nodo fb.
                Mientras ese hecho se cumpla,  trabajar sobre la RX550 no
                amenaza la consola"
               y el TARGET CONTRACT afirma  "iGPU: Intel HD Graphics 4600"
               MEDIDO   las dos cosas eran verdade el 2026-10-04  y son falsas hoy
AUTOCORR.     la primera version de este hallazgo decia "no se sabe por que se
               registro distinto"  y sostenia que la premisa NUNCA se habia
               verificado.  Es falso:  el hallazgo 1439,  GENERADO=2026-10-04,
               registro  fb0_name = i915drmfb  con  card0 control=auto
               runtime=active  como dato MEDIDO.  La maquina cambio despues
ALCANCE   decide el nivel de riesgo del frente de runtime.  No es cosmetico
GENERADO=2026-10-06 · MEDIDO=EN ESTA HOST
```

## 1 · Lo medido

```text
  /sys/class/graphics/fb0/name            amdgpudrmfb          <-- NO i915drmfb
  /sys/class/graphics/fb0/device          ../../../0000:01:00.0
  /sys/class/graphics/fb0/virtual_size    1366,768
  /sys/class/graphics/fb0/modes           U:1366x768p-0
  /proc/fb                                0 amdgpudrmfb        (un solo framebuffer)

  /sys/class/drm/                         card1  card1-DVI-D-1  card1-HDMI-A-1
                                          renderD128  version
                                          NO hay card0

  readlink /sys/bus/pci/devices/0000:00:02.0/driver      (vacio:  sin driver)
  lsmod | grep i915                                     (ninguno)

  lspci -nn -s 00:02.0                                  (no devuelve nada)
  lspci -nn | grep -i vga
      01:00.0  VGA  Lexa PRO [Radeon 540/540X/550/550X / RX 540X/550/550X]
      01:00.1  Audio  Baffin HDMI/DP Audio [Radeon RX 550 640SP / RX 560/560X]
```

Y el bus PCI completo, para que se vea que no es que falte el listado:

```text
  00:00.0  Host bridge          8086:0c00   (DRAM controller del i7-4790)
  00:01.0  PCI bridge x16       8086:0c01
  00:14.0  USB xHCI             8086:8c31
  00:16.0  MEI                  8086:8c3a  8086:8c3a
  00:1a.0  USB EHCI             8086:8c2d  8086:8c2d
  00:1b.0  HDA                 8086:8c20
  00:1c.0  PCI bridge           8086:0c10  8086:0c10
  00:1c.5  PCI bridge           8086:0c1a  8086:0c1a
  00:1d.0  USB EHCI             8086:8c26  8086:8c26
  00:1f.0  LPC                 8086:8c5c  8086:8c5c
  00:1f.2  SATA AHCI            8086:8c02
  00:1f.3  SMBus               8086:8c22  8086:8c22
  01:00.0  VGA   AMD            1002:699f     <-- el unico dispositivo de display
  01:00.1  Audio AMD            1002:aae0
  03:00.0  Ethernet Realtek     10ec:8168

  NO HAY 00:02.0.  Entre 00:01.0 y 00:14.0 no hay ninguna funcion.
```

## 2 · Las dos afirmaciones que caen

### La primera: el framebuffer

```text
  REGISTRADO   fb0 = i915drmfb,  1366x768.
              La RX550 no tiene nodo fb.
  MEDIDO      fb0 = amdgpudrmfb,  1366x768,  en 0000:01:00.0.
              La RX550 SI tiene nodo fb,  y es el unico que hay.
```

El `1366x768` coincide, lo que hace la contradicción más incómoda: **el tamaño es el que se
registró y el dueño es el contrario.** Eso es exactamente lo que pasa cuando dos fuentes
distintas dan el mismo número y una se mezcla con la otra.

### La segunda: la iGPU, y aquí sí hay una transición de estado

```text
  REGISTRADO   iGPU: Intel HD Graphics 4600          (TARGET CONTRACT, §2)
               y en la nota de autorizacion:  "PROHIBIDO tocar 0000:00:02.0,
               la Intel HD 4600, i915"
  MEDIDO      el CPU es  Intel(R) Core(TM) i7-4790 CPU @ 3.60GHz,
               que si lleva el HD 4600 en silicio.
               Pero 0000:00:02.0 no aparece en el bus,  i915 no esta cargado,
               y no hay card0.
               La funcion esta ausente del bus,  no es que este sin(driver).
```

## 2bis · La premisa **sí** se había medido, y la máquina cambió después

Esta es la parte que corregí, y es la que convierte el hallazgo de "una premisa
que nunca se comprobó" en "un estado de hardware que cambió", que es otra cosa
completamente distinta.

```text
  1439-primera-lectura-del-silicio-...   GENERADO=2026-10-04
      INTEL  0000:00:02.0  (i915, HD 4600)   <-- prohibida, verificada intacta
      | fb0_name | i915drmfb | i915drmfb |
      FRONTERA Intel intacta:  fb0=i915drmfb 1366,768, card0 control=auto
                runtime=active,  un /dev/fb0
      y 1467, 1472 y 1489 repiten la misma linea de frontera
```

**Ayer la Intel estaba en el bus, era `fb0`, tenía `card0` con runtime activo, y
`1439` además leyó el silicio de la RX550 por MMIO y no la tocó.** Ese trabajo es real:
leídos 20 registros, con el canario `mmSCRATCH_REG0 = 0xdeadbeef` en el offset que
la cabecera declara, y `mmVM_CONTEXT0_CNTL = 0x00fffed9` / `CONTEXT1_CNTL =
0x01fffedb` que distinguen VMID0 plano de VMID1 PD+PT.

Hoy, un día después:

```text
  0000:00:02.0   ausente del bus
  i915           no cargado
  card0          no existe
  fb0            amdgpudrmfb,  en 0000:01:00.0
```

**La transición ocurrió entre el 2026-10-04 y hoy.** No sé por qué, y no lo adivino:
puede ser un cambio de BIOS, un apagado del iGPU, un cambio de máquina, o que
`1439` se escribiera contra otro host. Lo único que afirmo es que **ayer era
distinto de hoy**, y que eso es un hecho medido por el lado de los dos.

Y **corrijo mi propia lectura de partida, que era peor**: yo daba el tree por
consultado y con la lista de bloqueadas al día, y la lista decía
"Runtime: nunca se ha leído un registro de 0000:01:00.0". **Es falso, y estaba en
el árbol desde ayer.** Lo vi al buscar el ítem 12, es decir, después de proponer
ítem 12. Debí hacer el barrido de §58 **antes** de elegir trabajo, no después de
elegirlo.

## 3 · Qué cambia, en las dos direcciones

### Hacia abajo: la frontera dura es trivialmente cumplible

La prohibición es "no escribir sobre `0000:00:02.0`, no tocar i915, no tocar `fb0` de la Intel,
no alterar su power state, no cambiar la salida de consola". **No hay nada que cumplir**: la
función no está en el bus, el módulo no está cargado, no hay nodo DRM, y `fb0` no es suyo.

Eso no la debilita. La dejo escrita y la cumplo igual: **sigo sin acercarme a nada de la Intel**,
que es la postura correcta aunque el objetivo no exista. Lo que cambia es que la restricción ya
no está protegiendo nada, y eso hay que decirlo para que nadie la lea como una garantía.

### Hacia arriba: el riesgo real es el contrario del que se suponía

Aquí está lo importante. La lógica con la que se autorizó intervenir sobre la RX550 era:

```text
  "Mientras ese hecho se cumpla [la consola es de la Intel],  trabajar sobre la RX550
   no amenaza la consola."
```

Ese hecho **no se cumple**. Y la situacion real es la inversa de la que hace segura la cosa:

```text
  La RX550 es el UNICO dispositivo de display de esta maquina.
  fb0 es suyo.  tty0 esta activo sobre el.
  Un fallo o un reset de la RX550  =  pantalla negra  =  sesion perdida.
```

Es el mismo riesgo que la nota de autorizacion advertia —"el coste de tocar la consola es la
sesion"— pero aplicado **a la RX550** y no a la Intel. Lo que se razonamiento excluia por ser
"la consola es de la Intel" es precisamente la GPU sobre la que se iba a intervenir.

## 4 · Qué hago con esto

```text
  SE MANTIENE   el plan de runtime en  READ_ONLY.  No cambia.
                Una lectura MMIO no puede provocar un fallo de GPU,  asi que
                ni el riesgo nuevo obliga a pararse.

  SE SUBE       cualquier cosa que pase de READ_ONLY.  Escribir un registro,
                pedir un reset, tocar el ring buffer,  cargar firmware,  o
                ejecutar un comando con semantica desconocida.
                Motivo:  la decision del propietario se tomo sobre la premisa
                "la consola es de la Intel",  y esa premisa es falsa.  La
                decision no se invalida,  pero su fundamento cambio  y eso es
                una decision del propietario,  no mia  (§42 exige no saltar una
                etapa de la escalera de intervencion sin justificacion,  y esta
                justificacion cambio).
```

Y `§42` aplicado a la escalera:

```text
  READ_ONLY          permitida,  y es la que sigue vigente
  REVERSIBLE_WRITE   requiere nueva decision del propietario
  CONTROLLED_WRITE   requiere nueva decision del propietario
  HIGH_RISK / DESTRUCTIVE  requiere nueva decision del propietario
                        y ademas hoy el display depende del mismo dispositivo
```

## 5 · Un dato de procedencia que tampoco coincide

```text
  kernel que corre    7.2.9-200.nobara.fc44.x86_64
  arbol que estoy leyendo   linux-7.1.3
```

Todas las emisiones, los `count`, los desplazamientos y los números de línea que he medido son de
`7.1.3`, y el driver cargado es de `7.2.9`. Las **direcciones de registro** de
`gfx_8_0_d.h` casi con seguridad no se mueven entre dos minors, así que `mmCP_DMA_ME_COMMAND =
0xc084` y `mmCP_ECC_FIRSTOCCURRENCE = 0x307a` son de fiar. Pero **la lógica del driver** que he
citado (`ring->me = mec + 1`, `amdgpu_ring_insert_nop`, las 56 emisiones de `gfx_v8_0.c`) puede
haber cambiado.

Queda como `LIMITACION` transversal a toda la cadena de hallazgos del frente PM4: **elcodigo es de
7.1.3 y el hardware corre 7.2.9**. No invalida nada de lo medido porque casi todo lo medido es del
header, que es estable, pero es una limitación real y hay que escribirla.

## 6 · Procedimiento

```text
PREGUNTA   (para el frente de runtime)  ¿puedo leer un registro de 01:00.0 sin
           amenazar nada,  y quien tiene la consola?
HERRAMIENTA  lspci, lsmod, /sys/class/graphics, /sys/class/drm, /proc/fb, DMI
FUENTES    sysfs y procfs.  dmesg NO legible sin escalar  (ya registrado)
MEDIDO     fb0 = amdgpudrmfb en 0000:01:00.0,  1366x768,  unico framebuffer
           0000:00:02.0 ausente del bus  ·  i915 no cargado  ·  no hay card0
           el unico VGA del bus es 01:00.0  (Lexa PRO,  con 01:00.1 audio Baffin)
           board ECS H81H3-M4,  BIOS AMI 4.6.5,  CPU i7-4790:  el silicio de la
           iGPU esta,  la funcion no
CONTRADICCION  registrada contra dos afirmaciones del propio arbol:
           (a)  la nota de autorizacion,  sobre  fb0 = i915drmfb
           (b)  el TARGET CONTRACT §2,  sobre  iGPU: Intel HD Graphics 4600
           RESOLUCION  en cuanto al estado de HOY:  RESOLVED por medicion directa.
           En cuanto a la transicion:  DATADA.  El 2026-10-04  el hallazgo 1439
           la midio como cierta,  con la misma tabla de evidencia.  Hoy es falsa.
           La causa  NO SE DETERMINA  y no se intenta adivinar.
           Y no es una contradiccion del arbol:  es una transicion de estado de
           hardware,  con dos mediciones en dias distintos  que no se contradicen
           entre si  sino que se succession.
DECISION    el plan de runtime sigue en READ_ONLY.  Escalarlo a escritura
           requiere una nueva decision del propietario,  porque el fundamento
           de la decision anterior  ("la consola es de la Intel")  resulto falso
DISPOSITIVO  NINGUNO.  i915 ausente,  amdgpu intacto,  no se escribio nada
RUNTIME      NOT_RUN
LO QUE SIGUE
  el preflight del frente de runtime esta HECHO  y dio un resultado que cambia el
  calculo de riesgo.  Lo que sigue  con permiso vigente  es la lectura:
  una lectura MMIO no puede provocar un fallo de GPU
  y no puede tocar nada de la Intel,  porque no hay nada
  lo que NO sigue sin nueva decision  es cualquier escritura
```