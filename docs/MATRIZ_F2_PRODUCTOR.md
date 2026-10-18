# MATRIZ F2 — PRODUCTOR DEL SNAPSHOT (INSPECCIÓN REAL, SIN EJECUCIÓN)
# Estado: READ-ONLY / SIN PRIVILEGIOS / SIN EDITAR PROYECTO
# Fuente: BLOQUE 0 del prompt actual; archivos inspeccionados directamente

## 1. ¿Qué dispositivo selecciona y cómo lo identifica?
CONTRATO REAL (core/fuego.py:106-118): `revertir()` usa `self.dispositivos.get(dispositivo_id)`; no hay identificación automática de hardware. El script propuesto (`scripts/crear_snapshot_gpu.py`) usa `device_id="gpu0"` fijo (línea propuesta), sin consultar `/proc/iomem` para identificar cuál GPU corresponde.
EVIDENCIA: `.rxre/gpu0/` existe → el dispositivo es `gpu0`. `core/fuego.py` no tiene lógica de detección de hardware.
CONCLUSIÓN: Selección es manual (`gpu0`); identificación no automática. No hay mapa `gpu0 → RX 550` verificado.

## 2. ¿`gpu0` corresponde a la RX 550, a la Intel integrada o a otro dispositivo.
EVIDENCIA: `/sys/class/drm/card1/` existe (Intel integrado). `lspci` muestra Host bridge Intel, NO AMD/ATI. `/proc/iomem` no muestra `amdgpu`. El `amdgpu.ko` está en repo pero no cargado como dispositivo visto por `lspci`.
CONCLUSIÓN: `gpu0` probablemente refiere a `card1` (Intel integrada), NO a RX 550 AMD. No hay evidencia de RX 550 activa en este host.

## 3. ¿Qué direcciones, registros o regiones intenta leer.
CONTRATO PROPUESTO (docs/CONTRATO_F2_W5_MINIMO.md): `int(s, 16)` de `/proc/iomem` (líneas con `amdgpu`/`drm`), luego `mmap.mmap(..., offset=base)` sobre `/dev/mem` para 4096 bytes.
EVIDENCIA REAL: `/proc/iomem` NO muestra `amdgpu`; `lspci` no muestra AMD. La región MMIO de `amdgpu` no es detectable en este hardware.
CONCLUSIÓN: El script intentaría leer una región que no existe en este hardware. Riesgo: leer offset incorrecto o 0.

## 4. ¿Si utiliza `/dev/mem`, sysfs, ioctl, MMIO u otro mecanismo.
CONTRATO PROPUESTO: `/dev/mem` + `mmap.mmap` + `struct.unpack("<I", ...)`.
EVIDENCIA REAL: `core/fuego.py` no usa `/dev/mem` ni `mmap`. `fuego.py` solo copia archivos.
CONCLUSIÓN: El mecanismo es lectura directa de memoria física (`/dev/mem`) — más sensible que sysfs (`/sys/class/drm/card1/` ya accesible sin root).

## 5. Todas las rutas donde escribe, crea, trunca o reemplaza archivos.
LEER: `/proc/iomem` (no privilegiado); `/dev/mem` (privilegiado, root kmem).
ESCRIBIR: `.rxre/gpu0/original/` (propuesto) o `.rxre/gpu0/original` (real — archivo vacío); `.rxre/gpu0/restaurado` (por `revertir()`); `metadata.json` (propuesto).
TRUNCAR/REEMPLAZAR: `shutil.copyfile` en `revertir()` escribe `restaurado`; no modifica `original`.
EVIDENCIA REAL: `.rxre/gpu0/original` existe (archivo vacío, 0 bytes); no es `register_0.bin` ni `metadata.json`.
CONCLUSIÓN: Escritura solo en directorio de proyecto (`.rxre/`); lectura requiere root para `/dev/mem`; sysfs es alternativa sin root.

## 6. Si realiza operaciones adicionales sobre hardware.
CONTRATO PROPUESTO: Ninguna (solo lectura MMIO de 4096 bytes). No invoca `ioctl`, no modifica registros GPU.
EVIDENCIA REAL: `core/fuego.py` no opera sobre hardware; solo copia archivos.
CONCLUSIÓN: No hay operaciones adicionales; límite claro.

## 7. Que formato, longitud, contenido y metadatos debe tener el snapshot.
CONTRATO PROPUESTO: `.bin` = 4096 bytes; `metadata.json` = `{"device": "gpu0", "mmio_base": "...", "size": 4096, "hash": "sha256..."}`.
EVIDENCIA REAL: No existe archivo `.bin`; `.rxre/gpu0/original` es vacío; no hay metadatos.
CONCLUSIÓN: El contrato del documento propone un formato específico; el archivo real no lo cumple. El snapshot no está construido.

## 8. Si el test valida contenido real o solo existencia/longitud del archivo.
EVIDENCIA REAL (`test_f2_snapshot_real.py` líneas 10-20): `assert snap.stat().st_size > 0` y `assert r is not None`. No valida hash, no valida contenido de registro, no valida procedencia de datos.
CONCLUSIÓN: El test solo valida existencia + tamaño > 0. No es un test de contenido de snapshot. Es suficiente para confirmar que un archivo real está presente, no para confirmar que es el registro correcto de la GPU.

## 9. Si `core/fuego.py:revertir()` puede ejecutar escrituras sobre el dispositivo y bajo que condiciones.
EVIDENCIA REAL (`core/fuego.py` líneas 99-118): `revertir()` solo hace `shutil.copyfile(origen, destino_final)` donde `origen = .rxre/gpu0/original` y `destino_final = .rxre/gpu0/restaurado`. No escribe en `/dev/mem`; no modifica GPU; no usa `ioctl`; no requiere `root` (solo necesita que `original` sea legible por el usuario).
CONDICIÓN: `original` debe existir como archivo; no requiere root para la operación de copia (si `original` es accesible al usuario); no modifica hardware.
CONCLUSIÓN: `revertir()` NO escribe sobre dispositivo. Es seguro (solo copia archivo en `.rxre/`).

## 10. Si el script puede producir un archivo vacío, parcial, incorrecto o atribuido al dispositivo equivocado.
EVIDENCIA REAL: El archivo `.rxre/gpu0/original` ya existe (vacío). El script no existe (`scripts/crear_snapshot_gpu.py` no está en disco). Si se creara manualmente sin verificar `amdgpu` en `/proc/iomem`, podría usar `base = 0` (incorrecto) o leer de una región incorrecta (Intel en lugar de AMD). El identificador `gpu0` no está verificado contra `lspci`; podría referir a `card1` (Intel) o a otro dispositivo.
CONCLUSIÓN: Sí, existe riesgo: (a) archivo vacío ya presente podría confundir; (b) sin verificación de `amdgpu` / `lspci`, el snapshot podría ser de región incorrecta; (c) sin verificación de hash en `register_0.bin`, no hay procedencia. Requiere contrato de verificación antes de confiar.
