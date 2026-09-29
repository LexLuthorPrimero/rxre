# RX 550 — Benchmarks candidatos para M2

Preparado el 2026-09-20. Este directorio contiene documentación y descargas del repositorio. No se autorizó ni se ejecutó una nueva carga de benchmark. Las instalaciones fuera del repositorio y las corridas históricas se registran como estados separados en `BENCHMARK-INVENTORY.md`; su existencia no se certifica desde este repositorio.

> **Alcance de este README**: describe únicamente lo **descargado dentro del repositorio**.
> Las **instalaciones** (fuera del repo, en `~/Escritorio/berchmark/instalados/`) y la
> **ejecución con resultado experimental** son hechos distintos, inventariados en
> `BENCHMARK-INVENTORY.md` (tabla «Estado canónico por benchmark»).
> Resumen: **1 descarga completa en el repo** (GravityMark) + **1 parcial** (Superposition);
> **4 instalaciones externas observadas, no certificadas por el repo**; **2 resultados históricos**
> (GravityMark no discriminativo; Superposition inconcluso en la configuración probada). Heaven y Valley:
> instalación externa observada, sin resultado.

## Estructura

* `official-downloads/gravitymark/`: instalador Linux oficial de GravityMark.
* `official-downloads/unigine/`: reservado para instaladores UNIGINE si una fase posterior los autoriza.
* `cancelled-downloads/`: descarga parcial conservada y sin ejecutar de Superposition; la
  objeción de CLI no se confirma como descarte (la `superposition_cli` fue verificada).
* `docs/`: inventario y registros de procedencia.

Los archivos `.run` no son ejecutables por el proceso que los descargó; son instaladores conservados para revisión posterior. Antes de una instalación, hay que revisar y aceptar explícitamente las licencias que correspondan.

## Candidato prioritario

**GravityMark 1.89** fue un candidato histórico; el resultado conservado no fue
discriminativo para M2. Cualquier reconsideración requiere autorización nueva. La selección
de GPU prevista, si se autorizara, sería Vulkan con `VK_ICD_FILENAMES=...` y verificación
explícita de `0x699f`; `MESA_VK_DEVICE_SELECT=1002:699f` es opcional y no sustituye la
comprobación.

## Otros candidatos descargados

UNIGINE Superposition 1.1 tiene una parcial preservada; Heaven 4.0 y Valley 1.0 no están
descargados dentro del repo. Sus instalaciones externas son observaciones no certificadas.
La automatización de las ediciones gratuitas sigue siendo una fuente de capacidad por
auditar; no se deduce elegibilidad M2.

## Pendiente deliberado

No se descargó el GpuTest/FurMark histórico investigado inicialmente. La evidencia previa señalaba opciones de CLI no suficientemente documentadas y reportes de inestabilidad del kernel. La página oficial actual de Geeks3D promociona FurMark 2 (su sucesor), no el paquete GpuTest investigado. Queda pendiente de revisión explícita antes de incorporar un sustituto de alto estrés.

Tampoco se descargaron RPM de repositorios (vkmark, glmark2, stress-ng, clpeak, Phoronix Test Suite): ya están identificados como disponibles en Nobara/Fedora, pero obtenerlos no aporta un binario independiente y podría llevar a resolver dependencias. Se mantienen como alternativas para una fase posterior autorizada.
