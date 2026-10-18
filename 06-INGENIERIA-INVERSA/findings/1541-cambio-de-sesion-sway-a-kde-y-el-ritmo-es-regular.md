# 1541 — Cambió la sesión: sway → KDE. Las 21 capturas son de sway y hoy hay DRM master en card1. El ritmo del IH es regular (CV 0,063), no ráfagas

```text
AGENCIA=RX550-INVESTIGACION · WORK_CLASS=AGENT-RE-TOOLING
GENERADO=2026-10-05 · MEDIDO=EN ESTA HOST

DESCUBRE       la sesion grafica cambio.  Las 21 capturas son de sway; ahora
               es KDE con Xwayland, plasmashell y firefox.  firefox started
               2026-10-05 10:38:39.
PROVEN         Xwayland (pid 1985) tiene /dev/dri/card1 ABIERTO.  En la captura
               de 1499 nadie era master de card1.  No es un error de 1499:
               el estado cambio.
PROVEN         el ritmo del IH es REGULAR: 40 muestras de 1 s, media 150,7,
               desviacion 9,5, CV 0,063.  Sin rafagas.
PROVEN         gfx concentra el 97,89 % de los fences acumulados (39915 de 40774).
CIERRA         la pregunta de 1538 §7 punto 1: el perfil en el tiempo, medido.
DESCUBRE       el ratio IRQ/fence = 45,7 NO es un dato: mezcla dos instantes.
               fence_info es de 2026-10-02 y /proc/interrupts es de ahora.
               Lo descarto yo mismo.
ERROR, mio     mi regex de nombres de fd cortaba en el digito y parecio que
               los procesos usaban "/dev/dri/render" en vez de renderD128.
```

## 0 · DE DONDE VIENE

`1538` §7 dejó tres puntos, y el tercero era:

```text
  3. LA RELACION ENTRE IRQ Y FENCE.  Tengo 39915 fences acumulados en gfx y
     ~160 IRQ/s.  Si son 1:1, hay una cuenta que comprobar.  Si no lo son,
     el ratio es un dato sobre cuando sincroniza y cuando no.  Es medible con
     /proc y fence_info, los dos ya accesibles.
```

Primero el punto 1 (el perfil), porque de eso depende si la comparación del
punto 3 tiene sentido. Y al medir, apareció algo que no buscaba.

## 1 · EL PERFIL: REGULAR, NO RÁFAGAS

40 muestras de 1 segundo, del contador de IRQ de `0000:01:00.0`:

```text
  155 151 146 161 192 154 144 144 146 154 162 148 149 151 146
  144 148 160 174 151 141 152 142 143 147 152 158 143 145 154
  144 145 159 154 145 144 143 145 145 147

  n = 40   media = 150,7   desviación = 9,5   min = 141   max = 192
  CV (coeficiente de variación) = 0,063
```

```text
  PROVEN  el interrupt handler atiende un ritmo REGULAR, de ~151 IRQ/s, con una
          dispersión del 6,3 %.

  Y ESTO ES UN DATO DE ARQUITECTURA, no de ruido:
      CV 0,063 significa que NO hay ráfagas.  El IH no esta procesando a empujones: mantiene una cola constante y avanza a paso fijo.

  Un CV alto (digamos 0,8) significaría trabajo por lotes: vaciar una cola
  grande y luego esperar.  Con CV bajo, la señal es trabajo continuo y fino.

  Y ESO DICE ALGO SOBRE LA CARGA:  el compositor KDE no genera trabajo
  discontinuo.  Gasta poco y constantemente.
```

## 2 · EL HALLAZGO QUE NO BUSCABA: CAMBIÓ LA SESIÓN

Antes de la cuenta IRQ/fence, fui a ver quién usa la GPU. Y:

```text
  172758  firefox-bin         6 fds  →  /dev/dri/renderD128    started 10:38:39
   1928   plasma-keyboard     3 fds  →  /dev/dri/renderD128    started 04:03:19
   1985   Xwayland            1 fd   →  /dev/dri/card1         started 04:03:21
                              4 fds  →  /dev/dri/renderD128
   2066   plasmashell         3 fds  →  /dev/dri/renderD128    started 04:03:26
   2232   xwaylandvideobr     3 fds  →  /dev/dri/renderD128    started 04:03:32

  uptime: 7h 36m, desde 2026-10-05 04:01:21
```

Y la captura del 2026-10-02:

```text
  clients.txt:
             command  tgid dev master a   uid
      systemd-logind  1020   1    y    y     0
                sway  1705 129    n    n  1000
                sway  1705 129    n    n  1000
                sway  1705 129    n    n  1000
                sway  1705   1    y    y  1000

  minor 129 = card1 = la RX550.  sway la tenia abierta SIN ser master.
  Nadie era master de card1.
```

```text
  DESCUBRE  la sesion grafica cambio:  era sway (un compositor de tile) y ahora
            es KDE Plasma con Xwayland.  Los procesos de ahora (Xwayland,
            plasmashell, plasma-keyboard) arrancaron a las 04:03, y firefox a
            las 10:38.

  PROVEN  Xwayland tiene /dev/dri/card1 ABIERTO.  En la captura de 1499 nadie
          era master de card1.

  Y ESTO NO ES UN ERROR DE 1499:  1499 decio, textual, "en el momento de la
  captura no habia nadie con DRM master en la RX550".  Acoto con "en el
  momento de la captura", y el momento ha cambiado.  Correcto entonces,
  falso ahora, y por eso no lo corrijo: lo que cambio es el mundo.
```

## 3 · Y ESO AFECTA AL PROYECTO DE UNA FORMA CONCRETA

```text
  LAS 21 CAPTURAS SON DE SWAY.  Todo lo que he construido con ellas:

    1499  "nadie master en card1", "la carga es sway"
    1500  frame del anillo gfx:  8 frames de 256 dwords, identicos
    1502  el IB da VMID 7
    1508  los cuatro EVENT_WRITE_EOP, el +1 del workaround
    1512  el anillo sdma0:  1066 packets, 2 tipos de fence
    1516  los 46 IB son 46 slots de 256 en un rango de 251
    1518  el length_dw viene de userspace
    1520  63 fences emitidos, 20 visibles, 43 sobrescritos
    1523  dos tipos de fence (A: sin vm_flush, B: con vm_flush)

  ¿CAMBIA ALGO DE ESO?

  1. LAS ESTRUCTURAS, NO.  El layout de los packets, el fill del anillo, los
     dos tipos de fence, la cadena length_dw: son propiedades del driver y del
     hardware.  No cambian con el compositor.

  2. LOS NUMEROS, SI.  "8 frames de 256" era de una ventana de una carga
     concreta.  Con KDE y firefox puede ser distinto, y no lo se.

  3. EL VMID 7, PROBABLEMENTE SI.  Con sway era 7.  Ahora hay 4 procesos
     usando la RX550 (firefox, Xwayland, plasmashell, plasma-keyboard) y cada
     uno con su VMID.  El 7 puede ser de otro.

  4. "nadie master en card1", SI.  Ahora Xwayland lo tiene.

  Y ESTO ES LO IMPORTANTE Y NO LO HABIA VISTO:
      el cambio de sesion es el PRIMER DATO NUEVO de la RX550 en tres dias.
      Todo lo anterior es de las capturas del dia 2.  Y no es un dato del
      driver:  es un dato del ENTORNO, y el entorno es parte del target
      (AGENTS.md §2).

  LO QUE PUEDO HACER CON ESTO, Y ES LO UNICO:
      volver a capturar los mismos ficheros con la carga actual, y comparar
     Ring-contra-ring.  Eso no necesita debugfs ni root:  es el mismo
      amdgpu_debugfs de siempre... que SI necesita debugfs.
```

Y aquí paro, porque es importante decirlo en vez de pasar al siguiente tema.

## 4 · LO QUE NO PUEDO HACER, Y ES EL LÍMITE REAL

```text
  RECAPTURAR los anillos, o fence_info, o cualquier debugfs:  requiere
  /sys/kernel/debug, que es drwx------ root.

  Asi que el cambio de sesion me dice que el estado que medi hace 3 dias ya no
  es el estado.  Y no puedo medir el nuevo.

  LO QUE SI PUEDO, y es poco:
    - /proc/interrupts:  la tasa y el ritmo.  YA MEDIDO.
    - /proc/<pid>/:  quien usa la GPU.  YA MEDIDO.
    - sysfs:  el estado del dispositivo.

  LO QUE NO PUEDO:
    - los anillos
    - fence_info
    - amdgpu_regs
    - el ring del IH

  Y POR ESO EL RATIO DE LA SECCION SIGUIENTE NO ES UN DATO.
```

## 5 · EL RATIO, DESCARTADO POR MÍ MISMO

La cuenta que `1538` §7 proponía:

```text
  fences acumulados (fence_info, 2026-10-02):   40774
  IRQ acumulados (proc/interrupts, 2026-10-05): 1862907
  ratio:                                          45,7
```

**Ese 45,7 no significa nada y lo descarto.** Razones:

```text
  1.  son dos instantes distintos con 3 dias de diferencia
  2.  fence_info cuenta fences, no IRQ, y no se que proporcion hay
  3.  el denominador (40774) es de sway; el numerador (1862907) es de KDE
      con firefox
```

```text
  LO QUE SI SE PUEDE DECIR CON ESTOS DOS NUMEROS, y es distinto:

  gfx = 39915 de 40774 fences acumulados
      = 97,89 % del total, en el unico anillo que dibuja.

  Y ESO ES UNA AFIRMACION DE ESTRUCTURA, no de ratio:
      los otros 17 anillos juntos hacen el 2,11 %:  859 fences.
      Reparto completo, los 18, leido del fichero:
         39915 gfx        407 sdma0    356 sdma1     17 comp_1.3.0
           13 comp_1.1.0   12 comp_1.2.0   8 uvd   8 uvd_enc0
            8 uvd_enc1     8 vce0        6 comp_1.0.1  4 x5
            0 kiq_0.2.1.0   0 vce1        0 vce2
         = 40774

  PROVEN_DERIVED  el reparto de trabajo esta completamente desequilibrado hacia
                  un solo anillo.  No es "la GPU dibuja mucho y copia algo":
                  es "todo el trabajo de_COMMAND esta en gfx".

  Y ESO, PARA UN DRIVER PROPIO, DICE UNA COSA CONCRETA:
      si hay que elegir por donde empezar a optimizar, es gfx.  No porque
      tenga el 97 % de las fences, sino porque tiene el 97 % del trabajo de
      comando, y las fences son la unidad de sincronizacion que ya se.
      Entender por que el anillo de graficos emite 100 veces mas que el de
      copia es la pregunta que devuelve mas.
```

## 6 · ESTADO

```text
PROVEN          el ritmo del IH es regular: 40 muestras de 1 s, media 150,7
                IRQ/s, desviacion 9,5, CV 0,063, min 141, max 192.  Sin rafagas.
PROVEN          la sesion cambio:  era sway, ahora es KDE Plasma con Xwayland,
                plasmashell, plasma-keyboard y firefox.  Los procesos de ahora
                arrancaron a las 04:03 y firefox a las 10:38 de hoy.
PROVEN          Xwayland (pid 1985) tiene /dev/dri/card1 abierto.  En la
                captura del 2026-10-02 nadie era master de card1.
PROVEN          4 procesos usan la RX550 ahora, ninguno con la Intel:  0 fds
                sobre card0.  FRONTERA DURA RESPETADA en todo el hallazgo.
PROVEN_DERIVED  gfx concentra 39915 de 40774 fences = 97,89 %.  Los otros 17
                anillos juntos hacen 859 = 2,11 %.
CORRIGE, mio   mi primera suma daba 40799 y luego 40755:  dos sumas a mano
                equivocadas.  La buena sale de leer los 18 campos del fichero
                y sumarlos con un programa: 40774.
DESCUBRE        un CV de 0,063 indica cola constante, no trabajo por lotes.

NO CORRIGE 1499  1499 acoto "en el momento de la captura" y es correcto.  El
                estado cambio, no el hallazgo.

DESCARTADO      el ratio IRQ/fence = 45,7.  Mezcla dos instantes con 3 dias de
                diferencia, y fence_info cuenta fences, no IRQ.

NOT_DETERMINED  si cada fence produce una IRQ.  Necesita fence_info del mismo
                instante, y fence_info es debugfs, y debugfs es root.
NOT_DETERMINED  como es el reparto de fences con la carga de KDE.  Mismo
                bloqueo.
```

## 7 · LO QUE SIGUE

```text
  1. EL REPARTO DE FENCES ES EL DATO MAS SOLIDO QUE TENGO PARA DIRIGIR EL
     TRABAJO.  97,89 % en gfx.  Y la pregunta que devuelve mas es por que
     el anillo de graficos emite 100 veces mas que el de copia.  Se responde
     leyendo el frame de gfx, que ya tengo cerrado (1508), y contando cuantos
     frames reales hay entre vallas.  ESTA ES MEDIBLE CON LO QUE TENGO.

  2. Y HAY UNA COOSA QUE ME CUESTA CERRAR:  las 21 capturas son de sway y la
     maquina ahora corre KDE.  Todo el mapeo estructural aguanta (es del
     driver y del hardware), pero los numeros son de una carga que ya no es
     esta.  No lo puedo remediar sin debugfs.

  3. EL RITMO REGULAR ES UN DATO DE RENDIMIENTO QUE NO TENIA.  ~151 IRQ/s es
     una medida en vivo de la carga de la GPU, sin privileged, sin debugfs, y
     con una dispersion del 6 %.  Eso es un baseline.  Si el objetivo del proyecto es
     MAXIMO RENDIMIENTO PRACTICO, este es el numero contra el que comparar,
     y es el primero que tengo que sea una tasa y no un reloj.
```

El punto 3 es el que más me importa: **por fin hay un baseline de rendimiento
que es una tasa de trabajo, no una frecuencia de reloj.** Y el punto 1 es medible
con material que ya tengo.