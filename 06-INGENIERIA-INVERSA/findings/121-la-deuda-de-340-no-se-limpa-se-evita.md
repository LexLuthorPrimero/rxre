# 121 · La deuda de 340 referencias no se limpia: se evita, y el mecanismo ya existe

`CLASSIFICATION=METHODOLOGY` · `TRACK=STATIC` · `WORK_CLASS=READ_ONLY/EVIDENCE`
`WRITE_EXECUTION=NONE` · `MODIFICATIONS=0` · `RUNTIME=NOT_RUN` · `GPU INTACTA`
`HERRAMIENTA=tools/reftriage.py` (ampliada con `cobertura_git`)
`CONTINUES=120` · `RETRACTA_LA_PROMESA_DE=120` (cerrar la deuda por análisis)

## Cuestión principal

`224` dejó 215 citas de deuda real en 51 documentos, y deux preguntas sin
cerrar:

1. De esas 215, ¿cuántas son ficheros **borrados** y cuántas **nunca
   existieron**?
2. ¿Se puede decidir automáticamente?

La segunda tiene un discriminante obvio y aparente: **el historial de git**. Un
fichero borrado aparece como eliminado en un commit; uno que nunca existió no
aparece en ninguno. Eso cerraría las dos clases de un golpe, sin leer un solo
documento.

## Criterio de terminación

Consultar el historial completo del repositorio y comprobar, para cada nombre
citado como roto, si **alguna vez** fue un fichero versionado. **Cumplido: 0
de 130.** Y el criterio, al aplicarlo, **resultó no ser concluyente**, que es
la respuesta.

## Respuesta: el discriminante no funciona, y por qué

```
commits en el historial:                 179
ficheros .md que han estado alguna vez:  5072   (rastreados en algún momento)
ficheros ELIMINADOS en todo el historial:    2
de los 130 nombres citados como rotos, versionados alguna vez:  0
```

El `0` parece limpio y **no lo es**, por una razón que sólo se ve al medir la
cobertura:

```
.md en disco ahora:        735
.md versionados por git:   478     -> 257 nunca versionados
findings en disco:         202
findings versionados:       56     -> el 72 % del corpus NO esta en git
herramientas .py:           40
herramientas versionadas:    1     -> el 97 % NO esta en git
```

**Un fichero que existió en disco y nunca llegó a un commit es invisible para
`git log --all --name-only`.** Con el 72 % del corpus fuera del historial, la
ausencia de un nombre en git no es evidencia de que no existiera: es ausencia
de registro.

De los 2 ficheros que git **sí** registra como borrados
(`06-INGENIERIA-INVERSA/amdgpu-analysis/exported-compute.txt` y
`08-ARQUITECTURA/tools/btfq/CONTRADICCION-014.md`), ninguno está entre los
nombres citados. Es decir: **la clase "se borró" está vacía entre lo
rastreable**, y la clase "nunca existió" y la clase "existió sin commit" son
**indistinguibles**.

## Por qué esta pregunta no es cerrable a posteriori

Para lo versionado, git es un registro completo: si un nombre no aparece en
5072 ficheros de 179 commits, nunca fue un fichero versionado. Para lo no
versionado **no hay registro**: no está git, no hay papelera, no hay copia. Un
fichero borrado de disco sin llegar a commit deja exactamente la misma ausencia
que un fichero que nunca se escribió.

**La consecuencia operativa es la que importa: `224` trataba la deuda como un
trabajo pendiente de análisis, y no lo es.** No hay 215 decisiones que tomar
con datos: hay 215 referencias cuya procedencia ya no es recuperable, y la
única acción posible sobre ellas es declararlas o reescribirlas sin pretending
que una de las dos es la correcta.

## El mecanismo que la evita, y que ya existe

`tools/REF-EXCEPTIONS.txt` con 41 entradas, y `071` que declaro cuatro por
nombre. La regla que sale de aquí:

> **Cuando una cita apunte a un fichero que no existe, se declara la excepción
> en el mismo momento en que se escribe la cita, no después de que una
> herramienta la marque.**

Es la misma forma que `008` aplico a las negaciones: un resultado negativo
sólo es información si el marco que lo produce es recuperable. Una cita rota
sin razón declarada no es un resultado negativo: es un agujero con forma de
evidencia.

**Esto explica por qué se acumulaban 340.** No era un problema de volumen ni
de atención: era un mecanismo que existe, se usó 47 veces, y no se aplicó en el
momento de citar. Por eso el trabajo correcto no es limpiar las 340 —es
irrecuperable— sino **hacer que las siguientes no aparezcan**, que es una línea
en el proceso de escribir un hallazgo, no un barrido.

## Clasificación

| afirmación | estado |
|---|---|
| 130 nombres citados como rotos, 0 versionados alguna vez | `PROVEN` — 179 commits, 5072 ficheros |
| El historial **no** puede separar "se borró" de "nunca existió" | `PROVEN` — sólo el 28 % del corpus está en git |
| La clase "borrado" está vacía entre lo rastreable | `PROVEN` — 2 eliminados, ninguno citado |
| Cuántos de los 130 existieron alguna vez sin llegar a commit | `NOT_DETERMINED` — **y no es recuperable** |
| Que la deuda de 340 sea recuperable por análisis | `REFUTED` — este hallazgo |
| Que declarar la excepción al citar evita la aparición | `PROVEN_DERIVED` — 41 entradas y 4 de `071` |
| Que las 45 citas de `findings/` sean de la clase "nunca existió" | `NOT_DETERMINED` — mismo límite |

## Confounders

- **La cobertura de git es la cifra que manda y cambia.** Si mañana se
  commitea el corpus que falta, la pregunta se vuelve a abrir para lo que se
  commitee, y `reftriage.py` lo dice en cada ejecución para que nadie dé por
  hecho un `0` que es un hueco.
- **79 % de las 340 están fuera de `findings/`**, en documentación de
  auditoría y planificación que cita nombres para afirmar que no existen. La
  acciones para ellas puede ser tan simple como borrar la frase.
- **No se ha reescrito ninguna de las 340.** Declarar una excepción por
  documento es un acto administrativo sobre documentos ajenos al corpus de
  hallazgos, y este hallazgo no lo ejecuta.

`WRITE_EXECUTION=NONE`. `MODIFICATIONS=0`: el árbol de Linux 7.2.8 no se ha
tocado. `GPU INTACTA`.