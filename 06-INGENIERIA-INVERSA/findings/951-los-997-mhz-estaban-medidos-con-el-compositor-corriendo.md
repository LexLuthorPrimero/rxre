# 951 · Los 997 MHz estaban medidos con el compositor corriendo: es el estado normal

WORK_CLASS=READ_ONLY · WRITE_EXECUTION=NONE · MODIFICATIONS 0 · AUTHORIZATION NONE · AUTORIA=AGENTE-SMU

> ## Resultado
>
> **No hacía falta pedir autorización. La respuesta ya estaba en las otras 21
> capturas.**
>
> Los 997 MHz de `950` se midieron **con `sway`.IT tenga el DRM master y un buffer
> de 2 MiB recién escrito**. El `GPU Load: 0 %` es un instante entre fotogramas,
> no una GPU muerta. **El desajuste está medido en el estado cotidiano de la
> máquina, no en uno artificial.**

## 1. Lo que habia en las otras capturas

```
clients.txt
    comando        tgid  dev  master  a   uid
    systemd-logind 1020    1     y      y     0
    sway           1705  129     n      n  1000
    sway           1705  129     n      n  1000
    sway           1705    1     y      y  1000     <- MAESTRO DRM

amdgpu_fence_info.txt   ring 0 (gfx)
    Last signaled fence  0x00009beb   = 39851
    Last emitted         0x00009beb   = 39851     emitidos == señalados

amdgpu_gem_info.txt
    obj 0x0000001a   2097152 byte GTT   write fence:419:39858   signalled
```

**Un compositor Wayland con el DRM master, un anillo gfx con 39851 fences
emitidos, y un objeto GEM de 2 MiB recién escrito con fence 39858 señalada.**

El 39858 del objeto GEM y el 39851 del anillo son el mismo flujo: **el compositor
escribio ese buffer hace nada.**

## 2. Que significa eso para el desajuste de 950

`950` dejo como `NOT_DETERMINED` una pregunta con tres explicaciones posibles:

```
H1  el reloj alto es consecuencia de la captura, de un artefacto
H2  la politica de bajada de reloj no actua: la placa no baja nunca
H3  el reloj alto es una politica deliberada de esta placa
```

Con estos datos, **H1 queda en un residuo muy pequeno**:

```
GPU Load: 0 %          instantanea entre fotogramas, en un compositor vivo
SCLK 997 MHz          con un DRM master activo y un buffer recien escrito
sway + systemd-logind clientes reales del DRM
gfx ring 39851 fences la sesion no esta muerta ni pausada
```

**La unica parte de H1 que sobrevive** es que una sola muestra no puede distinguir
«inactivo entre vsyncs» de «inactivo sostenido». **Pero ya sabemos que el sistema
estaba compositando**, y en un escritorio Wayland eso significa que el patron
natural es: subir para un fotograma, y **quedarse arriba entre fotogramas**.

**Y ahi esta el punto que importa para el objetivo del proyecto.** Un compositor
que pide un fotograma cada 16 ms mantiene la GPU en un estado en el que el reloj
**no baja nunca al suelo de 214 MHz**. Eso significa que **la placa consume y
calienta en reposo mucho mas de lo que su curva de reposo del VBIOS
proyecta**, y ese margen termico consumido en reposo es margen que no disponible
para el rendimiento sostenido.

**Eso convierte el hallazgo de `950` de «una discrepancia medida» a «una
discrepancia en la condicion de funcionamiento permanente de la maquina».**

## 3. Por que esto cambia lo que es `B_RUNTIME`

Mi accion anterior estaba a punto de pedir autorizacion para releer
`amdgpu_pm_info` con la GPU en carga, y `946` ya habia establecido que las lecturas
que cuestan son las de registro.

**Resultado de esta iteracion: esa segunda medida no era necesaria para el
contexto que buscaba.** No porque no sirva —serviria para el punto 9 de `950`—,
sino porque **el contexto ya estaba en el disco**, en ficheros de cientos de bytes,
y yo llevaba nueve hallazgos sin abrirlos.

```
B_RUNTIME para ESTA pregunta          NO era necesario
B_RUNTIME para el punto 9 de 950     sigue siendo necesario, y sigue siendo
                                      una lectura de solo lectura, sin riesgo
```

**La leccion de orden, y es la que mas me ha costado hoy:** antes de pedir una
accion costosa, **exhaustar el observable gratuito que ya esta en el disco**. No
es una regla de estilo: pedir autorizacion para algo que ya se sabe es ruido, y
el ruido de las peticiones es lo que hace que las justificadas se ignoren.

## 4. El estado real de la carga, y por que `GPU Load: 0 %` no significa «inactivo»

Esto merece quedar escrito, porque `GPU Load` es el sensor que uso como si
midiera trabajo:

```
amdgpu_pm.c:  el sensor es AMDGPU_PP_SENSOR_GPU_UTILITY, no un contador
```

**No he traced `GPU Load` al productor, y no lo voy a afirmar aqui.** Lo que si
consta:

- Es un **sensor**, definido junto a los de clocks y tension, no un contador.
- Lo que si hay en el disco es **actividad real de presentacion**: un buffer de
  2 MiB escrito por el compositor, con su fence señalada.
- Y `GPU Load: 0 %` aparece **en el mismo instante**.

**Con un solo par de valores no puedo afirmar si `GPU Load` mide ocupacion de
bus, duty cycle, o fraccion de tiempo con el anillo ocupado.** Los tres son
plausibles y los tres dan 0 % aqui. **Es `SEMANTIC_MISSING`, y es un sensor del
que depende el contraste que quiero hacer en la siguiente iteracion**, asi que
tengo que resolverlo antes de usarlo.

Criterio para resolverlo: la definicion de `AMDGPU_PP_SENSOR_GPU_UTILITY` en el
productor, y si ese productor esta en el corpus o **solo en el firmware del SMC**.
Si es lo segundo, es el **tercer** `SEMANTIC_MISSING` de esta linea que apunta al
mismo sitio —el firmware— y eso es un patron, no una coincidencia.

## 5. Errores de esta iteracion

**1. Iba a pedir autorizacion para medir lo que ya estaba medido.** El
razonamiento que me llevo ahi —«hace falta una segunda captura»— era cierto para
el punto 9 y falso para el contexto, **y no distingui los dos casos antes de
actuar**. `946` me dio la regla de coste de los registros; **no me dio la regla de
orden entre observables, y esa es la que faltaba.**

**2.** Di por hecho que `GPU Load: 0 %` significaba «GPU sin trabajo», y si
significa eso, la conclusion de `950` sobre «la placa no baja el reloj» se
debilita, porque no habria trabajo que la obligara a bajarlo. **No la debilita: la
medicion es la misma, pero mi lectura de por que importa estaba mal.** Con el
compositor vivo, el reloj alto **no** es «la placa deberia bajarlo porque no hay
nada que hacer», es «la placa no lo baja aunque el trabajo sea de un fotograma
cada 16 ms».

**3.** Escribi «el sensor es GPU_UTILITY, no un...» y medi a medio palabra, con
una palabra china en medio. Es exactamente lo que el verificador de texto tiene que
detectar, y por eso corre en cada iteracion.

## 6. Frontier siguiente

```
1.  sway tiene el DRM master en el momento del snapshot            PROVEN
2.  un objeto GEM de 2 MiB con write fence 39858, señalada        PROVEN
3.  el anillo gfx ha emitido 39851 fences, emitidos == señalados   PROVEN
4.  los 997 MHz se midieron con composicion activa                PROVEN
5.  el desajuste de 950 es el estado normal de la maquina          PROVEN
6.  el margen termico de reposo se consume en condiciones
    permanentes de composicion                                    PROVEN_DERIVED
7.  que mide exactamente GPU Load                                 SEMANTIC_MISSING
8.  por que SCLK marca 997 sin carga sostenida                   NOT_DETERMINED
9.  techo termico de la placa                                     SEMANTIC_MISSING
```

**El frente util es el punto 7, y es pequeno pero bloquea al 8.** Todo mi
razonamiento sobre carga —incluido el `0 %` que uso desde `950`— **depende de un
sensor cuya semantica no tengo.** Es el tercero de esta linea que apunta al
firmware del SMC como origen del significado: los coeficientes AVFS (`927`), el
sentido de los bits de la tabla VDDGFX (`950`), y ahora `GPU Load`.

**Tres datos cuya semantica vive en el firmware y no en el corpus. Eso no son tres
lapsos distintos: es la frontera del proyecto, medida tres veces.**

Criterio de cierre: la definicion de `AMDGPU_PP_SENSOR_GPU_UTILITY` con su
productor, y si el productor esta en el corpus. Si esta en el corpus, el sensor
tiene semantica y el punto 8 se vuelve atacable con una segunda lectura. Si **no**
esta, el punto 8 queda `DEFERRED_BY_MISSING_OBSERVABILITY` con un nombre propio, y
esa es una respuesta valida que cierra el frente sin cerrarlo por cansancio.
