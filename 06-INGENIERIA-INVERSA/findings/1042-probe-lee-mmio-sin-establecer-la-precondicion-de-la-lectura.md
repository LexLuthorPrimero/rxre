# 1042 · `probe()` lee MMIO sin establecer la precondición de la lectura, y el resultado alimenta al productor de geometría

`CLASSIFICATION=MEASUREMENT` · `TRACK=STATIC`
`CORPUS=linux-7.1.3.tar.xz (sha256 be41c068…)` · `HARDWARE_SCOPE=PCI 1002:699F rev 0xc7`
`WORK_CLASS=READ_ONLY` · `WRITE_EXECUTION=NONE` · `MODIFICATIONS=1`
`GPU INTACTA` · `MODIFIES_CODE=SI` (`04-IMPLEMENTACION/rx550-driver/rx550_target.c`)

---

## La pregunta

`tests/test_static.sh` afirma:

```
chk 0 RES "pci_enable_device DEFERRED (no llamado)"
```

y `pci_resource.c` explica por qué está diferido, con un motivo explícito:

> **PCI_ENABLEMENT = DEFERRED**
> `pci_enable_device()` habilita decodificación de memoria y bus mastering, y hace
> un reset del dispositivo. Es estado real de hardware. En este componente **NO hay
> consumidor: no se mapea nada todavía**, y `pci_request_region()` es pura
> contabilidad de propiedad […] Habilitar ahora sería una transición de hardware
> sin necesidad demostrable.
> **Lo requiere el componente MMIO, inmediatamente antes del primer `pci_iomap`.**

La última frase es una condición verificable. La cumplí.

## MEDIDO

### La condición se cumple

`rx550_target.c`, `rx550_target_probe()`:

| línea | llamada |
|---|---|
| 84 | `tdev->map_base = pci_iomap(pdev, TARGET_REG_BAR_INDEX, len);` |
| 96 | `rc = rx550_mmio_attach(&tdev->mmio, tdev->map_base, len);` |
| 133-135 | tres `rx550_mmio_read32()` bajo `rx550_probe_read` |
| 138 | `rx550_probe_geometry(pdev, tdev);` — **incondicional** |

Y `pci_enable_device` tiene **0 llamadas** en el componente entero: barrido de
todos los `.c` y `.h` con `^\s*pci_enable_device\s*\(`.

**La razón de diferir ha caducado.** No se mapea nada todavía → ahora se mapea.
El texto dice "lo requiere el componente MMIO, inmediatamente antes del primer
`pci_iomap`", y ese componente existe.

### Lo que eso deja sin precondición

Una lectura MMIO sobre una BAR presupone que el dispositivo **decodifica su
espacio de memoria**. Eso lo habilita el bit `MEMORY_SPACE` del registro `COMMAND`
del PCI, y de eso se encarga `pci_enable_device()`. Esta caja tiene un dato que
importa y que hace el caso más fuerte de lo que parecía:

- Si este driver Casanova el dispositivo, es porque **`amdgpu` no lo posee** — la
  reserva de BAR falla con `-EBUSY` en `drivers/base/dd.c:836-837`, y ese es
  exactamente el mecanismo por el que `probe()` todavía no se ha ejecutado nunca.
- Y si `amdgpu` no lo posee, es que **`amdgpu` no ha llamado a
  `pci_enable_device()` sobre él**. Su `probe()` no llegó a correr.

O sea: **la precondition de la lectura se cumple si y solo si otro driver hizo el
trabajo que este driver tiene prohibido hacer.** Eso no es una incógnita, es una
dependencia circular con un solo sentido: este componente no puede llegar a un
estado donde sus propias lecturas sean fiables por sí mismas.

### Y no es una lectura cualquiera: alimenta el productor

`rx550_probe_geometry()` **no es opcional**. Corre en cada `probe()`, sin módulo
parámetro que lo desactive, y lee los **dos** registros de los que depende la
colocación del GART. Sus tres lecturas van al mismo oráculo `R1/R2` que la sonda
optativa.

Y su salida es la entrada de `rx550_vm_geom`, es decir `block_size`,
`fragment_size`, `num_level` y `max_pfn`. El bloque que produce `block_size = 10`
—PROVEN_DERIVED por barrido de 512 valores en RAM— recibe su ventana de un
productor cuya precondición nadie establece. El consumidor no lo sabe, y no puede
saberlo: `block_size` llega como un entero, y el entero no lleva el estado de
validez de la lectura que lo produjo.

## POR QUÉ NO SE HA AÑADIDO LA LLAMADA

Porque `pci_enable_device()` **escribe en el registro `COMMAND` del dispositivo**
y hace un reset. Eso es `CONTROLLED_WRITE` sobre hardware real, está en
`UNDEF_PROHIBIDOS`, y la autorización para tomarlo requiere nivel 4 y está
bloqueada. Añadir la llamada haría que un `insmod` escribiera en la GPU, que es
precisamente la intervención que el proyecto ha diferido.

Lo que sí se hace es dejar la dependencia explícita y en el sitio donde alguien la
va a encontrar.

## LO QUE ESTA REGISTRADO EN EL CÓDIGO

En el punto de la lectura, y en la sonda de geometría:

- Que la precondición **no la establece este driver** y de quién dependería.
- Que por eso los valores leídos son `NOT_DETERMINED`, no "datos".
- Y que el oráculo `R1` (`rc == 0` en las tres) **no dice que el valor sea válido**:
  una BAR sin decodificación devuelve con éxito y un valor que no es el del
  registro. `R1` mide que el acceso se ejecutó, que es lo que su comentario dice, y
  no una cosa más.

Eso último es el punto que más fácil se malinterpreta. `R1=1` con
`v=0xffffffff/0xffffffff/0xffffffff` sería "acceso ejecutado, tres veces, con el
mismo valor" — y sería **exactamente** lo que se ve si la BAR no decodifica. El
oráculo actual no distingue ese caso del registro que responde.

## LO QUE NO ESTÁ HECHO

- **No he ejecutado nada contra la GPU.** Lo de arriba es lectura de fuente y de
  la lista de prohibiciones. El valor de `COMMAND` en el instante del enlace es
  `NOT_DETERMINED`, y para medirlo haría falta tomar el dispositivo.
- **No he cambiado `test_static.sh`.** El check sigue afirmando `DEFERRED`. Cambiar
  la lista de prohibidos sin la llamada es cosmetics; cambiar la llamada sin
  autorización es la intervención. Lo que hace falta es que el check **afirme la
  dependencia**, no el estado.
- **No he medido si el hardware_decode sobrevive** a un `probe()` exitoso. Que
  el firmware lo mantenga en otros sistemas es `NOT_DETERMINED` aqui, y por eso
  la dependencia circular del punto 2 no se puede romper suponiendo.

## LA REGLA QUE ESTE HALLAZGO TOCA

`AGENTS.md` §14 pide reconstruir `PRODUCER → TRANSFORMATION → REPRESENTATION →
CONSUMER → HARDWARE EFFECT` y registrar el eslabón que falte. Aquí el eslabón que
falta es **anterior al productor**: el estado del dispositivo del que depende la
representación. Un entero que llega sin el estado de validez de la lectura que lo
produjo es una representación sin consumidores honestos — y el primer
consumidor que lo trague va a ser la colocación del GART.
