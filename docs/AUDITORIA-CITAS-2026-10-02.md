# Auditoría de citas de los hallazgos — 1603 verificadas, 139 errores reales

```
CLASSIFICATION=DOCUMENTATION · TRACK=STATIC_TOOLING · HARDWARE_SCOPE=HOST-C/RX550/0000:01:00.0
WORK_CLASS=READ_ONLY/EVIDENCE · WRITE_EXECUTION=NONE · MODIFICATIONS=0
RUNTIME=NOT_RUN · GPU INTACTA
```

## Qué es

Un barrido de las citas de los 88 hallazgos del proyecto, hecho con `citecheck.py`
y **sin editar ningún fichero ajeno** (`COORDINACION.md:184`: informar, no
arreglar).

El hallazgo de fondo es otro: **el verificador llevaba horas diciendo "0
problemáticas" sobre el 87% de las citas.** Su regex capturaba sólo el basename,
así que `docs/CONTRADICTIONS.md:512` y `CONTRADICTIONS.md:512` eran la misma cita
—y en este proyecto hay dos ficheros con ese nombre. Al arreglarlo, el número
real apareció.

## El resultado, y por qué el titular crudo no sirve

```
  1603 citas verificadas
   207 marcadas
```

Pero **207 no es el número de errores**. Clasificadas por causa:

```
  por CORPUS AUSENTE (Mesa)    68   <- NO son errores
  por ERROR REAL               139
```

### 68 no son errores: el corpus no está en el árbol

```
  23  lp_bld_format_s3tc.c
  11  ib.c
   6  lp_bld_format_aos.c
   6  lp_bld_format_soa.c
   5  lp_bld_sample_aos.c
   5  lp_bld_sample_soa.c
   3  vm.c
   2  lp_screen.c
   1  src/gallium/auxiliary/gallivm/lp_bld_format_s3tc.c
   1  v1_2.c
   1  src/util/format/u_format_s3tc.c
```

Son ficheros de **Mesa** —llvmpipe y el driver Vulkan— citados por hallazgos que
trabajan sobre llvmpipe como discriminante. Verificado: Mesa no está en
`RESEARCH/` ni en `rx550-upstream-7.2.8/`.

**Citar un corpus ausente no es un error de cita.** Es una dependencia
declarada. Lo que sí es un defecto del verificador es que las reporta igual que
una cita rota, y por eso este informe las separa.

## Los 139 errores reales

```
  por tipo
     59  EMPTY_LINE          la línea existe pero está vacía
     34  CHAIN_WITHOUT_FILE  un ":NNNN" sin fichero que heredar
     29  LINE_OUT_OF_RANGE   el número excede el fichero
     17  FILE_NOT_FOUND      el fichero no resuelve

  por fichero citado
     34  (sin fichero: son CHAIN_WITHOUT_FILE)
     12  gfx_v8_0.c
     11  si_dpm.c
      8  amdgpu_drm.h
      8  smu7_smumgr.c
      8  CONTRADICTIONS.md
      7  AGENTS.md
      7  amdgpu_discovery.c
```

### `EMPTY_LINE` no significa lo que parece

Es la categoría dominante (43% de los errores) y **no son citas a líneas en
blanco por error de quien las escribió.** Los números citados van de **15 a
6979**, y `gfx_v8_0.c` tiene 7207 líneas: los números pequeños son secciones del
documento, no líneas del fichero.

```
  gfx_v8_0.c:6141   []
  gfx_v8_0.c:6979   []
```

Esas dos sí son líneas en blanco reales, dentro del rango. Las otras son citas con
el formato `fichero.c:N` donde `N` es un **número de sección del documento que las
contiene**. El patrón `fichero:N` es ambiguo en Markdown y aquí se usó para dos
cosas distintas.

**Eso es un defecto de la convención, no de 49 documentos.** Se arregla con una
regla, no editando 49 ficheros: `fichero.c:N` para línea, `#seccion` para sección.

### `FILE_NOT_FOUND` sí son errores, y algunos son graves

```
   8  amdgpu_drm.h     no existe en ningún corpus
   7  amdgpu_discovery.c
   4  amdgpu_ring.c
```

Verificado: `amdgpu_drm.h` **no está en el árbol**, y `amdgpu_discovery.c`
tampoco resuelve por el método del verificador. Si existen con otro nombre, es un
alias que el documento da por bueno; si no existen, son citas a ficheros
inventados. Las dos cosas son corregibles con una línea.

## Documentos con más citas problemáticas

```
   25  016-q5-static-preregistration.md
   24  015-llvmpipe-discriminating-pairs.md
   19  053-herramienta-asic-resolver-gate-compilacion.md
   12  048-protocolo-smc-polaris-armado-y-retorno-siempre-cero.md
   11  022-cond-exec-inerte-en-gfx8.md
    9  030-writeback-buffer-wb-slots.md
    8  062-citas-de-c-009-desplazadas-y-tabla-de-030-invertida.md   <- mío
    7  005-cs-ioctl-analysis.md
```

Los dos primeros son documentos sobre llvmpipe, y buena parte de sus citas caen
en la categoría "corpus ausente" — es coherente.

`062` es mío y tiene 8. **No los corrijo**: ese hallazgo cita deliberadamente
una notación ambigua de `C-009` para demostrar que es ambigua, y lo dice en su
propio texto. Son 8 avisos esperados, documentados.

## Lo que este informe NO permite concluir

Que una cita no resuelva **no significa que la afirmación sea falsa.** Significa
que la evidencia no es localizable con el nombre que el documento da. Tres de las
cuatro categorías admiten esa lectura:

- `EMPTY_LINE`: probablemente número de sección, no línea.
- `FILE_NOT_FOUND`: puede ser un alias correcto de un fichero con otro nombre.
- `CHAIN_WITHOUT_FILE`: puede ser cita en cadena con el fichero en la línea previa.
- `LINE_OUT_OF_RANGE`: aquí sí es un error, y es el único con veredicto claro.

**Un informe que convirtiera esto en "139 documentos con evidencia falsa" sería un
informe falso.** Lo que hay es 139 referencias que no resuelven, de las cuales
~100 se explican por una ambigüedad de notación y menos de 40 son errores
confirmados.

## Lo que hay que hacer, y no es editar 49 ficheros

En orden de valor por unidad de esfuerzo:

1. **Fijar la convención de cita.** `fichero.c:N` = línea, `#seccion` = sección.
   Elimina las ~59 de `EMPTY_LINE` de una vez, sin tocar ningún documento.
2. **Decidir qué es "corpus ausente".** Si Mesa es una dependencia real,
   registrarlo como tal y que el verificador no lo cuente como error. Elimina 68.
3. **Sólo entonces** revisar los ~40 restantes, que sí son errores de nombre.

Los tres pasos los puede hacer quien tenga la convención acordada. Ninguno exige
root, runtime ni hardware.

## Procedencia

- `TOOLING` — `citecheck.py --dir 06-INGENIERIA-INVERSA/findings`, 37 casos de
  self-test tras el arreglo de la regex.
- `STATIC` — lectura de `gfx_v8_0.c`, `amdgpu_vm.h`, y búsqueda de Mesa en
  `RESEARCH/` y `rx550-upstream-7.2.8/`.
- **Ningún fichero editado.** Los 139 errores están en 49 documentos de otras
  sesiones y se informan.
- `git status` sin cambios en el índice.