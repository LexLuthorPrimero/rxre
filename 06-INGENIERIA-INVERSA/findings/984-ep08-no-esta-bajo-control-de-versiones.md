# 984 · El experimento EP08 **no está bajo control de versiones**: un `sed -i` lo destruye y git no lo recupera

```text
CLASSIFICATION=ERROR+PROVENIENCE · TRACK=CORPUS
CORPUS=03-EXPERIMENTOS/ep08-doorbell-suppression/  (directo entero)
HARDWARE_SCOPE=no aplica
WORK_CLASS=READ_ANALYSIS + WRITE_LOCAL
AUTHORIZATION=NONE · GPU INTACTA · SIN ESCRITURA AL HARDWARE
AUTORIA=AGENT-04 (RUNTIME/PROBING/FUZZING/ORACLES)
HALLAZGO=demostrado por su propio incidente: borro 9 bytes y no habia red
```

## El hecho

```
$ git status --porcelain -- 03-EXPERIMENTOS/ep08-doorbell-suppression/
?? 03-EXPERIMENTOS/ep08-doorbell-suppression/

$ git ls-files  03-EXPERIMENTOS/ep08-doorbell-suppression/
(vacio)
```

**Ni `preruntime.sh`, ni `nhwa.c`, ni el `Makefile` están versionados.** Todo el
directorio es un `??` sin seguimiento.

## No es teórico: pasó en este mismo turno

Para construir un runner de pruebas ejecuté

```bash
sed -i 's/^main "\$@"$//' 03-EXPERIMENTOS/ep08-doorbell-suppression/preruntime.sh
```

sobre el **original**, en vez de sobre una copia. Borró la invocación final `main "$@"`.
**Nueve bytes**, 25513 → 25504.

Se detectó por hash (`d12d67b5…`, que no era ninguno de los valores registrados) y se
restauró reconstruyendo el byte y **verificando el hash contra el valor fijado en el
commit `9d6de62`**:

```
c0349f7f72bb00c5ccfce567c4736ef9bfbeeb48b270e9849533c38875826633   == original, byte a byte
```

Nada se perdió. **Se salvó porque el sha256 estaba escrito en un artefacto del turno
anterior.** Si no se hubiera medido ese hash, la recuperación habría sido manual, y el
harness más cuidadosamente diseñado del proyecto habría quedado inservible.

## Por qué no había red

Los seis workspaces son **bind mounts del mismo inodo**, no copias:

```
$ find /home/lucas/Escritorio/RX550-INVESTIGACION* -name preruntime.sh | xargs sha256sum | awk '{print $1}' | sort -u
d12d67b5f1d297c61fcb6ee71050ffb0a4c51bfd3637aff3e8a365058c01f58d      <- UN solo valor
```

Un inodo, seis rutas. Un error de escritura aparece en los seis sitios a la vez, y no hay
copia de seguridad por la estructura del árbol: la estructura es la que **es** una copia de
seguridad, y aquí no lo es porque nunca hubo versiones.

## Lo que sí estaba a salvo, por casualidad

| Artefacto | ¿Versionado? | Consecuencia |
|---|---|---|
| `preruntime.sh` | **NO** | pérdida total sin hash externo |
| `nhwa.c` | **NO** | ídem |
| `Makefile` | **NO** | ídem |
| `nhwa.ko` | NO, y `.gitignore` excluye `*.ko` y `*.o` | se puede reconstruir compilando |
| **el sha256, en `973` y en `ep08-validation.md`** | **SÍ, commiteado** | **única vía de recuperación** |

Es decir: lo que salvó el fichero fue un artefacto de documentación, no el control de
versiones. Y el fichero que protege —el que tiene la puerta de autorización, la validación
conductual de `no_hw_access` y el OFFSET GUARD— es precisamente el que no lo tiene.

## Por qué este repo ya sabe que pasa

`COORDINACION.md` dice, textual, que se perdió trabajo real dos veces por sesiones
escribiendo sobre los mismos ficheros, y por eso existe el cerrojo de directorio atómico.
El cerrojo serializa **escrituras concurrentes**. No protege de **`sed -i` sobre el
fichero equivocado**, que es un error de una sola sesión, con el árbol limpio y el cerrojo
libre: exactamente el estado en el que el protocolo declara la puerta abierta.

Este hallazgo es la categoría que falta: **no es concurrencia, es destructividad local**, y
el cerrojo por ámbito no la cubre porque nadie puede ser sujeto de uno mismo.

## Recomendación, con su coste, y sin tomarla aquí

```
1. git add 03-EXPERIMENTOS/ep08-doorbell-suppression/{preruntime.sh,nhwa.c,Makefile}
   Coste: ninguno. Contexto: ~37 KB de texto.
2. NO añadir nhwa.ko ni los .o: son 1.1 MB de binarios reconstruibles, y .gitignore ya
   los excluye. Añadirlos sería el error opuesto.
3. Regla general: un instrumento experimental que NO se versiona no puede auditarse de
   forma reproducible, porque no hay contra qué comparar un hash.
```

**No se ejecuta aquí.** Qué entra en el índice es una decisión estructural que no es de un
nodo de runtime, y el árbol tiene 505 ficheros sin seguimiento esperando su propia decisión.
Se registra con su coste.

## Lo que este hallazgo NO dice

- **No dice** que se haya perdido trabajo. Se perdio y se recupero, con verificación.
- **No dice** que el cerrojo sea inútil. Serializa escrituras concurrentes, que es lo que
  hace bien y lo que le toca.
- **No dice** que el fichero esté mal. Esta perfecto. Lo que falta es la red debajo.
- **No acusa** a nadie. Fue un error mío, en este turno, con la verificacion puesta.

```
LIMITACION  El alcance medido es ESTE directorio. No se ha hecho un censo de quantos
            instrumentos mas del arbol estan sin versionar; ese censo es trabajo de otro
            nodo y deberia hacerse.
```