# 176 · Las longitudes de los BAR se leen sin root; las direcciones no. Y el mapa de bloques no está en ningún corpus

```
CLASSIFICATION=MEASUREMENT+CORROBORATION · TRACK=RUNTIME_READONLY
CORPUS=RESEARCH/working/linux-7.1.3 · RESEARCH/kernelref/linux-7.1.3
HARDWARE_SCOPE=HOST-C/RX550/0000:01:00.0
WORK_CLASS=READ_ONLY/EVIDENCE · NIVEL=2 · WRITE_EXECUTION=NONE · MODIFICATIONS=0
RUNTIME=READONLY · GPU INTACTA · CERROJOS=0
```

## Qué resuelve

`171` sostiene que el primer eslabón vacío de la cadena es MMIO, y que escribir
`pci_iomap` sin saber qué hay dentro es implementar sin contrato. Este hallazgo
es la mitad de ese contrato que **sí** se puede medir, y dice con precisión qué
mitad no se puede.

```
  $ stat -c%s /sys/bus/pci/devices/0000:01:00.0/resource2
  2097152
  $ cat /sys/bus/pci/devices/0000:01:00.0/resource2
  cat: ...: Permiso denegado          (modo -rw------- root:root, uid 1000)
```

**La longitud de un BAR se lee sin root; su dirección no.** Son dos observables
distintos sobre el mismo fichero, y sólo uno está abierto. Eso convierte la
geometría de BAR en un invariante comprobable sin privilegios, y deja las
direcciones donde estaban: `BLOCKED_BY_PERMISSION`, no `NOT_DETERMINED`.

## 1 · Corroboración por un observable independiente

`findings/164` midió el mapa de BAR leyendo el **contenido** de los ficheros
`resource` y confirmando con `lspci -vv`. Esta ronda lo ha medido con el
**tamaño del inodo**, que no abre el fichero. Dos rutas distintas, mismo
resultado en los cuatro BAR:

| BAR | `164` | esta ronda (`stat`) | |
|---|---|---|---|
| 0 | 256 MiB, memoria 64-bit prefetchable | 268435456 B = 256 MiB | coincide |
| 2 | 2 MiB, memoria 64-bit prefetchable | 2097152 B = 2 MiB | coincide |
| 4 | 256 B, puertos de E/S | 256 B | coincide |
| 5 | 256 KiB, memoria 32-bit no prefetchable | 262144 B = 256 KiB | coincide |
| 1, 3 | no listados | **AUSENTES** | coincide |

Que `resource1` y `resource3` **no existan** es la prueba de que `0` y `2` son
BARs de 64 bits: cada uno ocupa dos ranuras, y la segunda está fusionada. Es
detalle, y coincide.

**Clasificación: `CORROBORATED`, no hallazgo nuevo.** Lo nuevo no es el mapa: es
que **la mitad de él es legible sin root**, cosa que la ruta anterior no exploitaba.

## 2 · Por qué el `st_size` de un `resourceN` es la longitud del BAR

No es una convención mía, es el comportamiento del atributo, y por eso merece
una advertencia en vez de una suposición:

- un fichero sysfs normal mide **4096** en `st_size`, no su contenido;
- estos miden **exactamente la longitud del BAR** en los cuatro casos medidos.

La diferencia es que el kernel crea estos atributos con el tamaño fijado, para
que un consumidor pueda leer la longitud sin abrir el fichero. Aquí eso es una
ventaja. Pero el mismo atributo en otro subsistema puede no estarlo, así que la
lectura por `stat` **debe comprobarse contra el valor conocido antes de
confiarse**, y aquí se comprobó: 4 de 4 coinciden con la tabla de `164`.

Si algún día un `resourceN` devolviera 4096, el indicador de este hallazgo —la
tabla de `164`— es contra lo que hay que mirar, no el sentido común.

## 3 · El mapa bloque→BAR no está en ningún corpus del proyecto

Esto es lo que **no** se pudo resolver, y es un `NOT_IN_CORPUS` con tres
comprobaciones, no una ausencia:

1. **`PCI_BAR` no aparece en ningún árbol de amdgpu.** Ni en 7.2.8 ni en 7.1.3.
   No es una propiedad de amdgpu: la constante vive en cabeceras del núcleo.
2. **`struct amdgpu_ip_block_version` (`amdgpu_ip.h:108`) no tiene campo de
   índice de BAR.** Sus campos son `type`, `major`, `minor`, `rev`, `funcs`. En
   7.2.8 la asociación bloque↔ranura no viaja en el bloque.
3. **No hay ningún `pci_iomap` en el árbol de amdgpu**, en ninguno de los dos
   corpus. La función que hace el mapeo no está en lo que hay.

Y el hallazgo de por qué: **el árbol de 7.2.8 sólo contiene `drivers/`**.

```
rx550-upstream-7.2.8/linux-7.2.8   2839 ficheros   raices: drivers
RESEARCH/working/linux-7.1.3      2787 ficheros   raices: Documentation drivers include
```

El de 7.1.3 trae `include/`; el de 7.2.8 no. Y las definiciones genéricas de
`PCI_BARn_*` sólo aparecen en definiciones locales de drivers no relacionados
(`drivers/usb/cdns3/`, `drivers/crypto/hisilicon/`), nunca en la cabecera común.

**Consecuencia práctica:** cualquier afirmación del tipo *«amdgpu no mapea el
registro X en el BAR Y»* es, en este proyecto, **`NOT_IN_CORPUS`**, y
`PROVEN_ABSENT` sería falso. No es un matiz: es la diferencia entre «lo he
buscado» y «no se puede buscar aquí».

## 4 · Lo que queda, clasificado

```
PROVEN                 las 4 longitudes de BAR, por st_size, sin root
PROVEN                 resource1 y resource3 no existen -> 0 y 2 son de 64 bits
CORROBORATED           las mismas 4 longitudes, por la ruta de 164
NOT_IN_CORPUS          que bloque vive en que BAR, segun el codigo de amdgpu
BLOCKED_BY_PERMISSION  las direcciones de los BAR: config space necesita root
                       (/sys/.../resourceN es 0600 root:root; lspci -v y setpci
                       devuelven sin permiso como uid 1000)
NOT_DETERMINED         nada de esto: cada linea dice por que queda abierta
```

La clasificación del cuarto bloque importa: son tres bloqueos **distintos**, y
cada uno se resuelve con una cosa diferente. Las direcciones no se pueden leer
sin root —eso se resuelve con permisos—. El mapa bloque↔BAR no se puede leer
porque **no está escrito donde se buscó** —eso se resuelve con otro corpus—. Y
`164` dice que el 88 % de la VRAM no tiene BAR y se alcanza por GART, que es un
hecho ya cerrado y no un hueco.

## Procedencia

```
stat -c%s /sys/bus/pci/devices/0000:01:00.0/resource{0,2,4,5}
                        4 de 4 coinciden con la tabla de findings/164
resource1, resource3   no existen
cat resource2          Permiso denegado; -rw------- root:root; uid 1000
lspci -v -s 01:00.0    solo la linea de identificacion, sin verbosidad
setpci -s 01:00.0 0x10 … 0x24   sin permiso
rx550-upstream-7.2.8   2839 ficheros, unica raiz: drivers
RESEARCH/working/linux-7.1.3     2787 ficheros, raices: Documentation drivers include
amdgpu_ip.h:108        struct amdgpu_ip_block_version sin campo de indice de BAR
grep -r PCI_BAR        0 coincidencias en los dos arboles de amdgpu
findings/164, 169, 171 la tabla que esto corrobora y el hueco que delimita
```

## CORRECCION POSTERIOR

Ninguna. Y una advertencia sobre las cifras de `164`: las reproduce con un
observable distinto, pero **no las confirma con un tercero**. Dos rutas que
dependen del mismo kernel y del mismo fichero sysfs pueden compartir un mismo
error de lectura. La corroboración es real y su valor está en que el camino de
medición es otro, no en que sea independiente de raíz.
