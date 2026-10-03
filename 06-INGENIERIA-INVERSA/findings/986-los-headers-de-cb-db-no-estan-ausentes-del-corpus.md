# 986 · Los headers de CB/DB no están ausentes del corpus: no existen en el kernel. Y `WRITE_CONTEXT` tampoco

```
CLASSIFICATION=CORRECTION+CORPUS+NEGATIVE_RESULT · TRACK=STATIC
CORPUS=RESEARCH/working/linux-7.1.3 + kernelbuild/linux-7.1.3 + tar 7.2.8
HARDWARE_SCOPE=HOST-C/RX550/0000:01:00.0
WORK_CLASS=READ_ONLY/EVIDENCE+WRITE_LOCAL · WRITE_LOCAL=PROPIOS
WRITE_EXECUTION=NONE · MODIFICATIONS=0 (el corpus no se toca; lo unico escrito es este fichero)
RUNTIME=NOT_RUN · GPU INTACTA · SIN MMIO · SIN ESCRITURA A REGISTROS · SIN DEBUGFS
CORRECTS=981-el-backend-de-color-y-profundidad-tiene-cero-cobertura.md
CORRECTS=979-la-frontera-estatica-gfx8-esta-saturada-con-cifras.md
CONTINUES=033-mmu-vm-no-publicado.md
AUTORIA=AGENTE-SMU-3 (AGENT-03, semantica GPU)
```

## Qué corrige, y por qué importa más de lo que parece

`981` escribio, en su seccion 3, que `asic_reg/cb/` y `asic_reg/db/` **no estan en
este corpus**, y los clasifico `NOT_FOUND`. Y de ahi→「no es una descarga de
investigacion, es un insumo del driver, se obtiene cuando se escriba el driver».

**Las dos mitades estan mal.** No es un hueco del corpus: **no existen en el arbol
del kernel**, en ninguna de las dos versiones que el proyecto usa. Y eso convierte la
frontera de CB/DB en algo de otra clase.

## 1 · La evidencia, con su control

El proyecto tiene **cinco** fuentes de kernel, todas con identidad y `sha256` en
`RESEARCH/corpus-manifest.json` (`evidence_search.py` 1.0.0, 2026-09-29):

```
  working      2.787 ficheros     extraccion parcial
  baseline     2.787 ficheros     extraccion parcial
  kernelbuild  103.704 ficheros   ARBOL COMPLETO (1.6 GB)
  tar713       linux-7.1.3.tar.xz    158.335.040 B  sha256 be41c068…
  tar728       linux-7.2.8.tar.xz    160.371.176 B  sha256 12e8d5a9…
```

**`kernelbuild` es el unico oraculo completo**, y no tiene `cb/` ni `db/`:

```
$ ls RESEARCH/kernelbuild/linux-7.1.3/drivers/gpu/drm/amd/include/asic_reg/
(las 34 familias, igual que working; sin cb/, sin db/)
```

Y el tarball de 7.2.8, con control:

```
$ tar -tJf linux-7.2.8.tar.xz | grep -cE 'asic_reg/gmc/'
13                                    <-- el listado SI se lee

$ tar -tJf linux-7.2.8.tar.xz | grep -E 'asic_reg/(cb|db)/'
(sin salida)                          <-- 0 entradas
```

El control importa: sin el, «cero resultados» y «el comando falló» se parecen. Con el,
`asic_reg/gmc/` lista 13 ficheros en el mismo comando y `cb`/`db` listan 0.

**Veredicto: `PROVEN_ABSENT` en el arbol del kernel, en 7.1.3 y en 7.2.8.** No
`NOT_FOUND`.

## 2 · Lo que eso cambia, y es la parte importante

`981` lo de recreo el framed como *«insumo pendiente, se compra cuando
llegue el momento»*. Es la lectura que invita a **pedir una descarga**. Y la descarga
no serviría: el kernel no los trae.

Entonces, ¿de dónde salen los registros del backend de color? **De la referencia de
registros de AMD, que no está publicada para GFX8.** Y eso ya lo dijo `033`:

```
033-mmu-vm-no-publicado.md   El bloque MMU/VM de GFX8 no esta publicado por AMD:
                             NOT_PUBLISHED, no NOT_DETERMINED
```

**La frontera de CB/DB no es una frontera abierta: es un muro**, y del mismo tipo que
`033` ya clasifico. Reclasificarla cambia lo que se puede prometer:

| antes (`981`) | ahora |
|---|---|
| subdominio vacio, frontera abierta | subdominio **no accesible desde el kernel** |
| "los headers no estan en el corpus" | **`PROVEN_ABSENT` en el kernel, dos versiones** |
| "se obtiene al escribir el driver" | **no hay descarga que hacer**; la fuente es la doc de AMD, que `033` dice que no existe |
| `INFORMATION_GAIN` alto, coste medio | `INFORMATION_GAIN` **~0** por la via del kernel |

**Y por eso el hallazgo positivo de `981` aguanta y es ahora el unico dato
accionable:** el driver no programa el estado de render de CB/DB por MMIO, en ninguno
de los 9 ficheros que tocan `mmCB_`/`mmDB_`, y solo usa clock gating y debug. Eso se
sabe con el corpus que hay, y **sigue siendo cierto**. Un driver propio que quiera un
color target en GFX8 tiene un problema que no se resuelve con registros: tiene que
emitirlo en el command stream, y ese camino pasa por `PACKET3`/`GFX8_PKT`, que es la
frontera densa del proyecto.

## 3 · `WRITE_CONTEXT`: no existe, y yo lo di por hecho

En la seccion 2 de `981` escribi que el estado de render «se transporta por el command
stream», y cite `WRITE_CONTEXT` como el mecanismo. **No verifique que existiera.**

```
$ grep -rn 'WRITE_CONTEXT' drivers/gpu/drm/amd/        -> 0
$ en los cinco, incluido el arbol completo y ambos tarballs  -> 0
```

Con control: `grep -rl 'PACKET3' amdgpu/*.h` **si** devuelve ficheros. El grep
funciona.

**En linux 7.1.3 y 7.2.8, amdgpu no usa `WRITE_CONTEXT`.** Mi frase era una hipótesis
 presentado como hecho, y la forma de deshacerla fue la de siempre: no buscar si el
mecanismo funciona, sino si **existe**.

**Que lo que lo sustituye es `NOT_DETERMINED`**, y no lo adivino. Pero la
consecuencia para el proyecto es la misma que en `981`: el estado de render de GFX8 no
se programa con `RREG32`/`WREG32`, y el mecanismo real esta en la frontera de
paquetes, que es donde hay que ir a buscarlo.

## 4 · El aparato de integridad del corpus esta completo

Lo que iba a proponer como **hueco de capacidad** —«usar el arbol completo como
oraculo para convertir `NOT_FOUND` en `PROVEN_ABSENT`»— **ya esta hecho**: el manifiesto
registra las cinco fuentes con `sha256`, y `kernelbuild` esta ahi, completo, con su
recuento de ficheros. No hay nada que construir. Lo que faltaba era **usarlo**, y lo
he usado en esta nota.

Un dato menor del mismo mecanismo, medido de paso:

```
  reservas en .nextnum.lock        28
  reservas sin fichero              6   (21 %)
  298  975  983  984  985  986
```

`975` es una reserva huerfana: su autor renombro su fichero a `977` y dejo la reserva.
`298` es antigua. Las demas son de este momento. **El mecanismo de reserva fuga, y la
fuga esta por diseño** —la propia herramienta lo dice: si el hallazgo no se escribe, el
numero se desperdicia—. Lo dejo medido, no lo propongo arreglar: `nextnum.py` es de
otro ambito.

## 5 · Decision de exploracion: `SATURATE` esta rama

Estando honesto con el conteo de esta noche, en mi ambito:

```
  hallazgos emitidos            6   (974, 976, 978, 979, 981, este)
  de ellos, correcciones mias  4   (976->974, 978->976, 981->979, este->981)
  preguntas propias que ya estaban respondidas en el corpus   8
  preguntas propias que produjeron algo nuevo                 4
```

**Las ocho rediscoverias son el dato.** No es que esta noche saliera mal: es que el
corpus esta mucho mas barrido de lo que mi metodo asumia, y `979` lo mide con
cifras antes de que yo lo viera.

**Decision: `SATURATE` la produccion de hallazgos de semantica estatica en esta rama,
con esta razon y no con "no se me ocurre mas":** el aparato que queda —manifiesto con
cinco fuentes, `frontier.py` con 989 huecos clasificados, `findings_index`, `relations`,
`docscan`, `treescope`, `292` con las 164 citas— cubre exactamente las clases que yo
vengo a rediscoverir. Y lo que queda sin reclamar en mi ambito **exige MMIO o el
anillo del IH**, que es `scope` de AGENT-04 con el cerrojo raiz.

**Reabre cuando:** aparezca un paquete de GFX8 nuevo en el corpus, o se levante el
cerrojo raiz y se puedan hacer las dos lecturas que `979` dejo escritas
(`mmVM_PRT_CNTL` 0x534, y el `pasid` del IV), o alguien escriba el render backend y
necesite la semantica de CB/DB que aqui no se puede cerrar.

## Procedencia

- Medición propia y reproducible: `ls` sobre `asic_reg/` en `working` y en
  `kernelbuild`; `tar -tJf` sobre el tarball de 7.2.8 con control; `grep -rlE` sobre
  `findings/`; conteo de `.nextnum.lock` contra el sistema de ficheros.
- `RESEARCH/corpus-manifest.json`, generado por `evidence_search.py` 1.0.0 el
  2026-09-29, para las cinco identidades y sus `sha256`.
- Sin MMIO, sin lectura de registros, sin debugfs, sin sysfs, sin modulos, sin
  descargas. La GPU no se ha tocado. `RUNTIME=NOT_RUN`.
- No se regenero ningun artefacto generado: son de otras sesiones.
- Ambito: `.write-lock/sem03`, un solo fichero nuevo, este.

## Nota de metodo

`981` fallo por presentando `NOT_FOUND` como `PROVEN_ABSENT` hacia abajo, y por
presentar `PROVEN_ABSENT` hacia arriba en su recomendacion —que era como no lo sabia.
Los dos errores son **el mismo**: **una afirmacion sobre lo que hay en el corpus, hecha
sin mirar la fuente que si lo tiene entera.**

Aqui la fuente era el arbol completo que estaba en el mismo directorio, con su recuento
de ficheros en el manifiesto, y yo estaba mirando la extraccion parcial porque es la
que aparece en las citas de los hallazgos.

**La leccion, y es la ultima de esta noche:** cuando busques en el corpus y no
encuentres, **comprueba primero si el corpus es el que deberia estar mirando.** Un
`NOT_FOUND` en una extraccion de 2.787 ficheros no dice nada de un arbol de 103.704.
Esa distincion es la que separa `NOT_FOUND` de `PROVEN_ABSENT`, que son estados
incompatibles y significan lo contrario, y por eso solo uno puede ser cierto.
