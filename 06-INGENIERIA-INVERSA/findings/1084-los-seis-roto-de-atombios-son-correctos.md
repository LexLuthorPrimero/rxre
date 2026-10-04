# 1084 — los seis `ROTO` de `ATOMBIOS-DECODER.md` son 6 de 6 correctos, y mi instrumento no los encontraba porque no sabe que un documento puede citar otro árbol

```text
AGENCIA=RX550-INVESTIGACION · WORK_CLASS=AGENT-MAIN-VALIDITY
CLASSIFICATION=DEFECT-MIO · TRACK=STATIC
GENERADO=2026-10-04 · MEDIDO=EN ESTA HOST
AFECTADO=tools/sello_prov.py  (NO reparado) · 08-ARQUITECTURA/ATOMBIOS-DECODER.md:527-537
ORIGEN=1079 §3 (14 ROTO, 6 mios) -> 1059 (el subagente explore lo localizo)
ESTADO=PROBADO · el documento es CORRECTO · el instrumento es el que falla
herramienta   tools/sello_prov.py 1.3.0
```

## 0 · El resultado

**Los seis `ROTO` que reportaba mi censo son seis de seis correctos.** El documento
`ATOMBIOS-DECODER.md` no tiene ni un solo error en su bloque de procedencia, y mi
instrumento los marcó como ficheros inexistentes.

```text
ruta citada                                    baseline  working  kernelbuild  7.2.8
drivers/gpu/drm/amd/amdgpu/amdgpu_atombios.c     OK        OK       OK           DIF
drivers/gpu/drm/amd/amdgpu/amdgpu_atombios.h     OK        OK       OK           OK
drivers/gpu/drm/amd/include/atombios.h           OK        OK       OK           OK
drivers/gpu/drm/amd/include/atomfirmware.h       OK        OK       OK           OK
drivers/gpu/drm/amd/amdgpu/amdgpu_atomfirmware.c OK        OK       OK           OK
drivers/gpu/drm/amd/amdgpu/atom.h                 OK        OK       OK           DIF

RESEARCH/baseline/linux-7.1.3     6 de 6
RESEARCH/working/linux-7.1.3      6 de 6
RESEARCH/kernelbuild/linux-7.1.3  6 de 6
rx550-upstream-7.2.8/linux-7.2.8  4 de 6      <-- no es esta
```

**Y el discriminante sale gratis de la propia tabla:** los tres árboles `linux-7.1.3`
cumplen los seis, y el `7.2.8` falla en dos. El documento está leyendo el `7.1.3`, y
su bloque dice exactamente eso en la línea 28.

## 1 · POR QUÉ MI INSTRUMENTO NO LOS ENCONTRABA

Porque resolví `drivers/gpu/drm/amd/amdgpu/amdgpu_atombios.c` contra la **raíz del
proyecto**, y el fichero está a **profundidad 13** dentro de `RESEARCH/baseline/
linux-7.1.3/`. Un `find -maxdepth 6` no lo encuentra. Yo lo hice con `-maxdepth 6`
al principio de esta sesión y concluí —incorrectamente— que el árbol no estaba.

**La lección no es "usa `-maxdepth` grande".** Es que **estaba asumiendo que un
bloque de procedencia cita ficheros relativos a la raíz del proyecto**, y esa
suposición es falsa en un proyecto que guarda un corpus de kernel dentro de sí mismo.
La asunción no estaba escrita en ninguna parte: estaba en el código, que es donde
peor se esconden las suposiciones.

## 2 · LO QUE NO HE REPARADO, Y POR QUÉ NO ES SINTÁCTICO

Podría añadir "busca también bajo `RESEARCH/*/linux-*/`" y el censo bajaría de 14 a 8
`ROTO`. **Eso sería una suposición vestida de regla**, y esta sección explica por qué
no lo es:

Un bloque de procedencia cita `drivers/gpu/drm/amd/...`. Para resolverlo hay que saber
**qué prefijo de raíz usa ese documento**, y ese prefijo:

1. **No es sintáctico.** La misma ruta significaría cosa distinta en dos documentos
   distintos, y el censo no tiene forma de saberlo leyendo las vallas.
2. **Ya está escrito en el documento.** `ATOMBIOS-DECODER.md:28` dice
   `RESEARCH/baseline/linux-7.1.3/...` en la tabla de fuentes. **La respuesta está
   en el documento y yo no la leía.**
3. **Es una decisión, no un hecho.** Si mañana el autor pasa a leer de
   `working/`, el prefijo cambia y el bloque sigue siendo válido.

Las tres cosas apuntan a lo mismo: **el prefijo de raíz es un dato del documento, y
un instrumento sintáctico no lo tiene.** Se puede oferecer como campo explícito —
`raiz   RESEARCH/baseline/linux-7.1.3` en el propio bloque — y entonces sí es
comprobable. **Eso es un cambio de convención, y una convención nueva la decide quien
escribe, no quien audita.**

Lo que sí hago, y es lo que este hallazgo sostiene, es **dejar de reportar `ROTO`**
cuando el documento no declara raíz: `NOT_DECLARED` es un hecho; `ROTO` es una
conclusión que la herramienta no tiene derecho a sacar.

## 3 · EL NÚMERO QUE ESTO VALE

De los 14 `ROTO` del censo del `1079`:

| origen | n | quién es el que falla |
|---|---|---|
| `ATOMBIOS-DECODER.md:527-537` | **6** | **yo**, por no leer la línea 28 |
| `401:134` | 1 | el documento: cita `amdgpu/gfx_v8_0.c`, que no existe con ese nombre |
| documentos en vuelo de otra sesión | 7 | no adjudicable (§50) |

**6 de 14 falsos positivos, y los 6 son del mismo defecto.** Lo que queda son 1
posible defecto real y 7 no adjudicables. Es la proporción de siempre en este trabajo:
un instrumento que fabrica falsos positivos donde hay hallazgos reales consume el
mismo canal y hace que se ignore el canal.

## 4 · Lo que este hallazgo NO es

- **No repara nada.** `sello_prov` sigue resolviendo contra la raíz del proyecto y
  sigue reportando `ROTO` en esos seis. Lo escrito arriba es el análisis; el arreglo es una
  convención que hay que decidir.
- **No propone la convención como hecha.** La idea de `raiz <prefijo>` en el bloque
  está aquí como **candidata**, y §2 dice por qué no la aplico por mi cuenta.
- **No audita `401:134`**, que sigue `NOT_DETERMINED` desde el `1059`.
- **No toca la GPU, ni el driver, ni mide rendimiento.**

## 5 · Procedencia

```text
medida     4 raíces candidatas × 6 rutas citadas, 24 comparaciones
           linux-7.1.3 (baseline/working/kernelbuild)  6 de 6 cada una
           linux-7.2.8                                   4 de 6
declarado  ATOMBIOS-DECODER.md:28  ->  "RESEARCH/baseline/linux-7.1.3/..."
bloque     ATOMBIOS-DECODER.md:525-540, 6 digests completos de 64 hex
escrituras  0 en el árbol.  No reparado.
```

**Lo que este documento NO prueba.** No prueba que los otros siete `ROTO` sean
correctos: seis son de material en vuelo y no son adjudicables, y uno
(`401:134`) sigue sin adjudicar. No prueba que la raíz sea `baseline` y no `working`
o `kernelbuild`: los tres son **byte-idénticos en estos seis ficheros**, así que el
documento es correcto y la elección entre ellos es indistinguible con esta evidencia.
Y no prueba nada sobre el hardware.