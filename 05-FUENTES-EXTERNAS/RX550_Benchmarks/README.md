# RX 550 — Benchmarks candidatos para M2

Preparado el 2026-09-20. Este directorio contiene solamente **descargas sin instalar** y documentación. No se ejecutó ningún benchmark, instalador, prueba de estrés ni comando que modifique la GPU, Mesa, `amdgpu`, `rx550-torneo` o los artefactos de M1.

## Estructura

* `official-downloads/gravitymark/`: instalador Linux oficial de GravityMark.
* `official-downloads/unigine/`: reservado para instaladores UNIGINE si una fase posterior los autoriza.
* `cancelled-downloads/`: descarga parcial conservada y sin ejecutar, trasladada aquí al descartar Superposition por no ser una opción reproducible de terminal en la edición gratuita.
* `docs/`: inventario y registros de procedencia.

Los archivos `.run` no son ejecutables por el proceso que los descargó; son instaladores conservados para revisión posterior. Antes de una instalación, hay que revisar y aceptar explícitamente las licencias que correspondan.

## Candidato prioritario

**GravityMark 1.89** es el primer candidato a evaluar para M2: sus autores documentan automatización por línea de comandos y una escena gestionada en la GPU, dos propiedades útiles para buscar una carga que haga ligarse el límite de potencia. Selección de GPU prevista cuando se autorice la ejecución: Vulkan con `VK_ICD_FILENAMES=/usr/share/vulkan/icd.d/radeon_icd.x86_64.json` y `MESA_VK_DEVICE_SELECT=1002:699f`.

## Otros candidatos descargados

UNIGINE Superposition 1.1, Heaven 4.0 y Valley 1.0 son cargas gráficas de referencia. Su propia documentación ofrece descarga Linux; Heaven y Valley indican explícitamente que la automatización por línea de comandos y los informes CSV corresponden a ediciones extendidas. Por eso quedan identificados como opciones secundarias pendientes, no descargados como parte de esta preparación reproducible para M2.

## Pendiente deliberado

No se descargó el GpuTest/FurMark histórico investigado inicialmente. La evidencia previa señalaba opciones de CLI no suficientemente documentadas y reportes de inestabilidad del kernel. La página oficial actual de Geeks3D promociona FurMark 2 (su sucesor), no el paquete GpuTest investigado. Queda pendiente de revisión explícita antes de incorporar un sustituto de alto estrés.

Tampoco se descargaron RPM de repositorios (vkmark, glmark2, stress-ng, clpeak, Phoronix Test Suite): ya están identificados como disponibles en Nobara/Fedora, pero obtenerlos no aporta un binario independiente y podría llevar a resolver dependencias. Se mantienen como alternativas para una fase posterior autorizada.
