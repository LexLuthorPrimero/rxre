# Procedencia y ejecución prevista

Fecha de registro: 2026-09-20. Todas las URL son de los autores de cada herramienta. El tamaño y la presencia de los archivos se verifica de forma local al terminar la descarga. No hay suma SHA-256 publicada por los autores en las páginas consultadas; se calculará una suma local para detectar cambios posteriores, pero no constituye una firma de autor.

| Herramienta | Versión | Archivo previsto | Fuente oficial | Estado | Ejecución disponible |
|---|---:|---|---|---|---|
| GravityMark | 1.89 | `official-downloads/gravitymark/GravityMark_1.89.run` | https://gravitymark.tellusim.com/ | descarga sin instalar | El sitio del autor declara CLI y parámetros/presets para automatización. Confirmar `--help` solo tras instalación autorizada. |
| UNIGINE Superposition | 1.1 | — | https://benchmark.unigine.com/superposition | pendiente, no descargado | El manual indica: marcar el `.run` como ejecutable, ejecutarlo para descomprimir y lanzar `Superposition`. Eso es instalación y no se hizo. La automatización/CSV está asociada a ediciones extendidas. |
| UNIGINE Heaven | 4.0 | — | https://benchmark.unigine.com/heaven | pendiente, no descargado | La página distingue automatización CLI/CSV como funciones de ediciones extendidas. |
| UNIGINE Valley | 1.0 | — | https://benchmark.unigine.com/valley | pendiente, no descargado | La página distingue automatización CLI/CSV como funciones de ediciones extendidas. |

## Selección de RX 550 para una futura ejecución

No se ejecutó esta selección. Cuando se autorice una prueba Vulkan, la configuración investigada para usar la RX 550 (PCI ID `1002:699f`) en vez de la Intel de pantalla es:

```sh
VK_ICD_FILENAMES=/usr/share/vulkan/icd.d/radeon_icd.x86_64.json \\
MESA_VK_DEVICE_SELECT=1002:699f
```

Para OpenGL, el mecanismo identificado es `DRI_PRIME=1`.

## Pendientes por licencia o revisión manual

GravityMark y los tres candidatos UNIGINE son instaladores propietarios. Su ejecución podría mostrar o exigir aceptar una licencia; por ello GravityMark no recibió permiso de ejecución ni se descomprimió, y los paquetes UNIGINE se dejaron pendientes. Antes de cualquier instalación, una persona debe revisar la licencia correspondiente y dar autorización explícita.

Corrección de estado: de los cuatro candidatos evaluados, solo GravityMark terminó de descargarse. Superposition se canceló al comprobar que su versión Linux ocupa 1.64 GB y que la edición gratuita no ofrece la automatización necesaria para M2; su fragmento de 34,365,440 bytes quedó preservado en `cancelled-downloads/`, no es instalable ni debe usarse. Heaven y Valley no se iniciaron.

## Exclusiones conscientes

* **GpuTest/FurMark legado:** identificado en la investigación previa, pero no descargado. La página oficial vigente orienta a FurMark 2, no a ese paquete legado; además existían reportes de inestabilidad y el conjunto de opciones original no estaba suficientemente documentado. Se requiere una revisión específica antes de adoptar el sucesor.
* **vkmark, glmark2, stress-ng, clpeak y Phoronix Test Suite:** candidatos de repositorio útiles, pero no son descargas externas necesarias ahora. Se instalarán o descargarán desde el repositorio solamente si se autoriza la etapa de ensayo; no se instaló ni ejecutó ninguno.
