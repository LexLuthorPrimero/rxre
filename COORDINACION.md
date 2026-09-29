# Protocolo de Coordinación — tres sesiones de IA en un árbol compartido

**Obligatorio.** Este fichero es ley operativa para cualquier agente que trabaje en este
repositorio. Se overruled por `AGENTS.md` en caso de conflicto; el resto de las secciones de
`AGENTS.md` siguen vigentes sin modificación.

## Por qué existe

Tres sesiones han escrito sobre los mismos ficheros durante horas. Se perdió trabajo real dos
veces: una reversión completa de AD-12 y D13, y un fichero de 787 líneas sobrescrito por una
reescritura que ni compilaba. Ninguna de las dos sesiones hizo nada fuera de norma: ambas
siguieron su propio plan. El daño vino de que **no había un mecanismo**, sólo la intención.

## Mecanismo: cerrojo de directorio atómico

**`git status` no sirve para arbitrar.** Detecta ficheros que *acaban* de escribirse. Una sesión
que commitea y sigue trabajando deja el árbol limpio entre commits, así que otra entra creyendo
que el turno está libre y ambas escriben a la vez. Un protocolo basado en `git status` no
coordina: se cumple y sigue habiendo colisiones.

`mkdir` sobre un directorio existente **falla**, y el sistema de ficheros garantiza que sólo una
sesión gana. Eso sí es un cerrojo.

### Adquirir el turno

```bash
cd /home/lucas/Escritorio/RX550-INVESTIGACION

if mkdir .write-lock 2>/dev/null; then
    echo "turno adquirido"
    # escribe PID y fecha dentro para que las demás vean quién lo tiene
    echo "$$ $(date -Is)" > .write-lock/owner
else
    echo "turno ocupado: $(cat .write-lock/owner 2>/dev/null)"
    echo "esperando, no preguntar"
fi
```

### Liberar el turno

```bash
rm -f .write-lock/owner && rmdir .write-lock
```

**Libera el cerrojo aunque tu trabajo esté incompleto**, después de commitear lo que tengas. Un
cerrojo retenido por una sesión terminada bloquea a las otras dos para siempre.

### Esperar

Si el cerrojo está tomado:

- **No preguntes** "¿puedo entrar?". La respuesta necesita a la otra sesión, que puede no estar.
- **Espera**, y revisa cada 30 s.
- **Lee** lo que quieras mientras tanto: leer nunca necesita cerrojo.
- Si el cerrojo lleva más de 20 min sin cambios en `owner`, está abandonado. Un cerrojo
  abandonado **no es un permiso para tomarlo**: informa y sigue esperando, o pide al humano.

### Ámbitos independientes

Tres sesiones trabajando en el mismo fichero se serializan. Trabajar en ficheros distintos **no
debe bloquearse**:

```bash
mkdir .write-lock/compressor     # sólo 04-IMPLEMENTACION/compressor/
mkdir .write-lock/decompressor   # sólo 04-IMPLEMENTACION/decompressor/
mkdir .write-lock/docs           # sólo *.md
```

Un subdirectorio del cerrojo es un cerrojo con nombre. El cerrojo raíz significa "escribo en
cualquier sitio" y es el único que excluye a las otras sesiones de todo.

## Reglas

1. **Una escritura a la vez por fichero.** El cerrojo por ámbito es la unidad.
2. **Commitea antes de liberar.** Un turno que acaba sin commit deja trabajo sólo en el disco de
   quien lo hizo, que es exactamente lo que se perdió.
3. **Verifica el hash tras escribir.** Las otras sesiones sobrescriben; comprobar que tu cambio
   sigue ahí 30 s después es más barato que reconstruirlo.
4. **No reescribas trabajo ajeno sin coordinarte.** Si tu versión de un fichero compila y la de
   otra no, el problema es de ellos: informa, no lo arregles.
5. **Un `git commit` recién hecho no es un turno libre.** El cerrojo, no el árbol, arbitra.

## Antes de reportar un resultado

- Compila sin errores, con los avisos que tú usarías.
- Ejecuta el test **más de una vez**. Una diferencia menor que el rango intra-run no es una
  diferencia: es ruido, y se reporta como `NOT_CONCLUYENTE`.
- Si el test puede fallar, **demuéstralo**: reinserta el defecto, ejecútalo, registra el número,
  revierte. Un test nunca observado fallando no prueba que detecte.
- Nombra la fuente de cada cifra. "El informe dice" no es una fuente; `sha256`, commit y fecha sí.

## Divergencias

Si dos sesiones llegan a conclusiones opuestas sobre un dato, **no se promedian ni se elige la
más reciente por defecto**. Se registra la contradicción con ambas mediciones y se pide decisión.
Ha pasado tres veces en este proyecto: truncamiento frente a redondeo, `RX550_BC4X` frente a
BC3, y la máscara del índice de color, que se resolvió midiendo en vez de razonando.

## Sobre `AGENTS.md`

Este protocolo **no reemplaza** a `AGENTS.md` y no lo modifica. `AGENTS.md` gobierna el método;
este fichero gobierna la concurrencia. Ambos son obligatorios.
