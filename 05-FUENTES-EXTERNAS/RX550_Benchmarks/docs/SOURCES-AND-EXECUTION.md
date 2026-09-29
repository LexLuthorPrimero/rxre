# Procedencia y ejecución prevista

Fecha de registro: 2026-09-20. Todas las URL son de los autores de cada herramienta. El tamaño y la presencia de los archivos se verifica de forma local al terminar la descarga. No hay suma SHA-256 publicada por los autores en las páginas consultadas; se calculará una suma local para detectar cambios posteriores, pero no constituye una firma de autor.

| Herramienta | Versión | Archivo previsto | Fuente oficial | Estado | Ejecución disponible |
|---|---:|---|---|---|---|
| GravityMark | 1.89 | `official-downloads/gravitymark/GravityMark_1.89.run` | https://gravitymark.tellusim.com/ | descarga sin instalar | El sitio del autor declara CLI y parámetros/presets para automatización. Confirmar `--help` solo tras instalación autorizada. |
| UNIGINE Superposition | 1.1 | `cancelled-downloads/Unigine_Superposition-1.1.run.partial` | https://benchmark.unigine.com/superposition | descarga **parcial/cancelada** en el repo (34.365.440 B preservados) | La `superposition_cli` fue verificada en la observación externa; el alcance de automatización/CSV y cualquier ejecución nueva requieren auditoría/autorización. |
| UNIGINE Heaven | 4.0 | — (no en repo) | https://benchmark.unigine.com/heaven | no descargado en el repo | La página distingue automatización CLI/CSV como funciones de ediciones extendidas. |
| UNIGINE Valley | 1.0 | — (no en repo) | https://benchmark.unigine.com/valley | no descargado en el repo | La página distingue automatización CLI/CSV como funciones de ediciones extendidas. |

> **Nota de alcance (reconciliación 2026-09-24)**: esta tabla documenta el estado
> de las **descargas dentro del repositorio** a fecha 2026-09-20. Las instalaciones
> externas observadas y las dos corridas históricas se registran en
> `../BENCHMARK-INVENTORY.md`, pero no son certificadas por este documento ni autorizan
> una nueva ejecución. No significa que Heaven y Valley estén ausentes del sistema.

## Selección de RX 550 para una futura ejecución

No se ejecutó esta selección. Cuando se autorice una prueba Vulkan, la condición mínima
es usar el ICD RADV y verificar explícitamente el device `0x699f` en el reporte. El selector
numérico es opcional y no se acepta sin esa verificación:

```sh
VK_ICD_FILENAMES=/usr/share/vulkan/icd.d/radeon_icd.x86_64.json
# MESA_VK_DEVICE_SELECT=1002:699f  # opcional; verificar device 0x699f
```

Para OpenGL, el mecanismo identificado es `DRI_PRIME=1`.

## Pendientes por licencia o revisión manual

GravityMark y los tres candidatos UNIGINE son instaladores propietarios. Su ejecución podría mostrar o exigir aceptar una licencia. En el registro de descargas de este repositorio no se autorizó una nueva ejecución; cualquier instalación o corrida histórica externa se conserva solo como observación separada. Antes de cualquier instalación o ejecución, una persona debe revisar la licencia correspondiente y dar autorización explícita.

Corrección de estado: en el alcance de **descargas dentro del repositorio**, solo GravityMark terminó de descargarse; Superposition conserva un fragmento parcial y Heaven/Valley no se descargaron. La afirmación de que la edición gratuita de Superposition carecía de CLI quedó invalidada por la verificación de `superposition_cli`. Las instalaciones y corridas históricas externas están fuera de este registro de descargas y no deben confundirse con una autorización vigente.

## Exclusiones conscientes

* **GpuTest/FurMark legado:** identificado en la investigación previa, pero no descargado. La página oficial vigente orienta a FurMark 2, no a ese paquete legado; además existían reportes de inestabilidad y el conjunto de opciones original no estaba suficientemente documentado. Se requiere una revisión específica antes de adoptar el sucesor.
* **vkmark, glmark2, stress-ng, clpeak y Phoronix Test Suite:** candidatos de repositorio útiles, pero no son descargas externas necesarias ahora. Se instalarán o descargarán desde el repositorio solamente si se autoriza la etapa de ensayo; no se instaló ni ejecutó ninguno.
