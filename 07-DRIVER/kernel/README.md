# rx550.ko — driver exclusivo para la RX 550 (Polaris 12, GFX8)

**Ronda 1**: skeleton compilable. Un char device, un ioctl. Nada más.

---

## 1. Objetivo del módulo

Sustituir el stack `amdgpu` + RADV por un driver propio para el PCI `1002:699f`.
El objetivo final es que el compute shader de la Fase 2
(`../decompressor/decompress_bc3.comp`, que ya produjo **0 de 4096 bytes
discrepantes** contra el decodificador de referencia en la RX 550 real) se pueda
ejecutar **sin** `amdgpu` debajo.

Ese número importa para el diseño: la aritmética del shader ya está resuelta y
verificada en hardware. Lo que falta es el camino de submit, que es exactamente
lo que este driver tiene que construir.

## 2. Arquitectura mínima inicial

```
userspace                          kernel
---------                          ------
test_version_ioctl.c  --ioctl-->  rx550_ioctl()
                                   ├─ rx550_ioctl_version()    [Ronda 1: implementado]
                                   └─ rx550_ioctl_device_info()[Ronda 1: -ENOTTY]

/dev/rx550  <--cdev/udev--
```

Componentes que tendrá, en orden de llegada:

1. **char device vía `cdev`** — hecho
2. **`RX550_IOCTL_VERSION`** — hecho
3. **`RX550_IOCTL_DEVICE_INFO`** — declarado, no implementado
4. **Mapeo de BAR / VRAM a userspace** — sin empezar
5. **Ring de compute + submit de PM4** — sin empezar
6. **Fences e interrupción** — sin empezar
7. **Migración a DRM** — sin empezar

## 3. IOCTLs planeados

| nº | Nombre | Estado | Nota |
|---|---|---|---|
| `0x00` | `RX550_IOCTL_VERSION` | **implementado** | `_IOR`, struct de 24 B |
| `0x01` | `RX550_IOCTL_DEVICE_INFO` | declarado, `-ENOTTY` | `_IOR`, struct de 72 B |
| `0x02` | `RX550_IOCTL_SUBMIT_COMPUTE` | **placeholder** | `_IOWR`, struct sin definir |
| `0x03` | `RX550_IOCTL_WAIT_FENCE` | **placeholder** | `_IOWR`, struct sin definir |

Los números son fijos para siempre. `0x02` y `0x03` tienen structs placeholder
a propósito: definirlas ahora congelaría una suposición en el ABI. Sus structs
reales necesitan punteros a buffers de comandos, tamaños, índices de ring y
offsets de doorbell, y ninguno de esos está establecido. Hasta que IA-1 reporte
los ioctls de `amdgpu` y los formatos PM4, definirlas sería adivinar en público.

## 4. Decisiones de diseño

### char device (`cdev`) y no DRM — y por qué es sólo el principio

DRM es la respuesta correcta a largo plazo y este driveronitorio creciendo hacia
ahí. No lo es para el primer módulo, por tres razones de riesgo:

1. **Superficie de DRM que hay que acertar antes de que sirva**: GEM, sync
   objects, un path de modesetting o de compute, y el modelo de device con
   DRM-master que un driver de compute headless no usa. Tomar todo eso en el
   primer commit significa depurar el core de DRM y el hardware a la vez.
2. **Un char device tiene un solo modo de fallo que razonar**: el encoding del
   ioctl y el layout del struct. Eso es justo lo que la Ronda 1 verifica.
3. **Es un subconjunto estricto**, así que la migración es aditiva:
   `/dev/rx550` pasa a ser el primary node de DRM y los ioctls pasan a ser
   `drm_ioctls`. No hay reescritura.

**El coste, dicho claramente**: un char device no da a userspace un BAR mapeado,
y el mapeo de BAR es lo que un driver de GPU real necesita. Eso llega con la
migración a DRM, no antes.

### `cdev` y no un minor estático

Un major estático fijo codifica un namespace global en el kernel y no se puede
asignar dinámicamente. `cdev` deja que udev cree `/dev/rx550`, así que el nodo
aparece sólo con el módulo cargado.

### Los números de ioctl no se reutilizan

`0x00` ya respondió en la Ronda 1. Reutilizar un número para otro significado
rompe en silencio todo binario construido contra el header anterior, porque el
ioctl devuelve éxito igual.

## 5. Dependencias que necesito del Ingeniero Inverso

En `../outgoing-reviews/2026-09-29-driver-to-rever.md`, por orden de prioridad:

1. Los números de ioctl que usa `amdgpu` para submit de compute, creación de BOs
   y mapeo de memoria. Needed para el diseño de `SUBMIT_COMPUTE`.
2. El formato de los packets PM4 tipo `PACKET3_DISPATCH_DIRECT` para gfx_v8.

Sin (2) no hay submit. Sin (1) el diseño del ioctl va a ser una suposición.

## 6. Estado de compilación

```
$ make            →  rx550.ko, 362 112 B, rc=0
$ modinfo rx550.ko
  version:    1.0.0
  license:    GPL
  vermagic:   7.1.3-200.nobara.fc44.x86_64 SMP preempt mod_unload
  srcversion: 3A7301ACC5F2D4CC3C0C75D
  depends:
  signer:     (ninguno)
```

### ⛔ El módulo compila pero no se podrá cargar en este host

```
CONFIG_MODULE_SIG_ALL=y            todo .ko queda SIN FIRMAR
CONFIG_SECURITY_LOCKDOWN_LSM=y     lockdown rechaza módulos no firmados
CONFIG_MODULE_SIG_KEY="certs/signing_key.pem"
/etc/pki/kernel*                   NO ENCONTRADO — la clave privada no está
```

`lockdown` rechaza un módulo sin firma **antes de examinar la firma**, así que
`insmod` fallará. Esto no es un defecto de este código: es una política del host.
Lo mismo ya estaba registrado en `PROYECTO_STATUS.md` como
`ABI_EQUIVALENCE = UNKNOWN`; aquí se confirma que sigue vigente y se añade que
la clave no está en el host, no sólo que sería distinta.

`make check-config` imprime estas cuatro líneas sin tocar nada. Es el primer
comando de cualquier ronda que necesite cargar el módulo.

**Para validar sin hardware** hace falta un entorno donde el módulo sí cargue: un
`/dev/rx550` simulado en userspace no exercises el camino del kernel, y una VM
con un kernel sin lockdown sí lo hace sin cambiar la política del host.

## 7. Plan de pruebas mínimo

| prueba | qué establece | estado |
|---|---|---|
| `make` | el módulo compila contra el árbol del host | **OK**, verificado |
| `gcc -o test_version_ioctl` | el test compila contra el mismo header | **OK**, verificado |
| `_Static_assert` de tamaños, en ambos lados | kernel y userspace comparten layout | **OK**, verificado |
| `modinfo` | metadatos y ausencia de firma | **OK**, verificado |
| `test_version_ioctl` con el módulo cargado | el ioctl devuelve la versión | **`NOT_RUN`** — bloqueo de firma |
| control negativo: ioctl que devuelve basura | el test **rechaza** un driver roto | **`NOT_EXECUTED`** |

Sobre la última fila: la rama `ENOTTY` está escrita y es alcanzable por
inspección, pero **no la he ejecutado**. Un test que nunca se ha visto fallar no
demonstra que detecte, y en este proyecto eso ya costó un ciclo entero
(`test_compress.c` comparaba la implementación contra una copia de sí misma y
pasaba con 26/26). Queda como `NOT_EXECUTED` a propósito.

## 8. Lo que este módulo NO hace

- No programa la GPU. No hay ring, ni submit, ni fences, ni interrupción.
- No mapea VRAM ni BAR a userspace.
- No reemplaza nada: `amdgpu` sigue cargado y en uso.
- No tiene test que haya pasado end-to-end.

El shader de la Fase 2 **no se ejecuta a través de este driver**. Se ejecuta a
través de Vulkan y RADV. Este driver es el camino futuro, y está en su primera
de tres piezas.
