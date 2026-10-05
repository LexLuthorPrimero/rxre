# 1553 — Retiro la deuda que dejé anotada: **`claims.py` no tiene ese fallo.** Mi diagnóstico de `1546 §6` era erróneo, y el arreglo de una línea que propuse **habría sido una regresión**

```text
AGENCIA=RX550-INVESTIGACION · WORK_CLASS=RETRACTS + AUTOCORRECTION
CLASSIFICATION=RETRACTS-PROPIO+AUTOCORRECTION-SIN-CAMBIO-DE-CODIGO
MODIFICATIONS=1546 §6 (su último párrafo queda retractado)
AUTOR=AGENTE-INSTR
WRITE_EXECUTION=NONE · GPU=NONE TOUCHED · RUNTIME=NOT_RUN
DISPOSITIVO_TOCADO=NINGUNO · ni 0000:01:00.0 (1002:699f) ni 0000:00:02.0 (8086:0412)
ESCRITOS_POR_ESTA_ITERACION   ninguno (solo lectura).  NO se toco ninguna herramienta
RETRACTS  1546 §6  su ultimo parrafo,  que decia:
          "Lo que hay que arreglar es una cosa, y es de una linea:  claims.py debe
           aceptar minuscula inicial,  porque en la nomenclatura de AMD los prefijos ix
           y mmConviven con los demas y el ix es el unico que va en minuscula"
          ESO ESTA MAL,  PORQUE claims.py NO EXTRAE IDENTIFICADORES GENERALES.
GENERADO=2026-10-06 · MEDIDO=EN ESTA HOST
```

## 1 · Lo que afirmé en `1546 §6`, textual

> `claims.py` **EXPOSICION REAL Y ACOTADA**: un identificador que empiece por minúscula no se
> registra. Una línea que cite `ixMC_IO_DEBUG_UP_159` entre acentos graves no cuenta como
> identificador. Afecta a la familia `ix*`, y solo a esa.
>
> Lo que hay que arreglar es una cosa, y es de una línea: `claims.py` debe aceptar minúscula
> inicial, porque en la nomenclatura de AMD los prefijos `ix` y `mm` conviven con los demás y
> el `ix` es el único que va en minúscula. No lo he tocado porque el encargo es findings, pero
> **es un arreglo pendiente y lo digo en vez de callarlo**.

Dos cosas están mal ahí, y la segunda es la grave.

## 2 · La primera: `ix` no es el único prefijo en minúscula, y la cifra era mucho mayor

Medí el alcance antes de decidir nada:

```text
  ficheros de hallazgo analizados                                796
  identificadores que ve  [A-Z] inicial                          7041
  identificadores que veria  [A-Za-z_] inicial                  15957
  ficheros con al menos uno nuevo                                 757
  =>  el patron viejo se pierde 8916 identificadores
```

Y lo que se pierde, por prefijo:

```text
  amdgpu 464   gfx 246   gmc 183   grep 129   mmvm 129   smu7 111
  polaris10 84   emit 83   dc 67   ring 64   max 60   get 60   sdma 57
```

**No son solo prefijos de registro.** Son identificadores de código en general, en minúscula:
`amdgpu_discovery`, `amdgpu_driver_open_kms`, `srcversion`, `umr`, nombres de fichero, nombres de
módulo, nombres de función. Y `mm` también empieza en minúscula, igual que `ix` — así que la
afirmación de `1546` de que "el `ix` es el único" era falsa por partida doble.

## 3 · La grave: `claims.py` no extrae identificadores, extrae **tokens de clasificación**

No miré qué hacía la salida antes de proponer cambiar el patrón que la produce. Ahora sí:

```python
  tools/claims.py:133    CLASE_RX = re.compile(r"`([A-Z][A-Z0-9_]{2,})`")
  tools/claims.py:586    for m in CLASE_RX.finditer(texto):
  tools/claims.py:587        clase = m.group(1)
  tools/claims.py:588        if clase not in CLASES:
  tools/claims.py:589            fuera_de_lista.add(clase)
  tools/claims.py:590            continue
```

Y qué es `CLASES`:

```text
  tipo set,  50 entradas
  todas en mayusculas?   True
  todos con guion bajo? False        (HYPOTHESIS, CONCLUSION, REFUTED, TEST...)
```

**El requisito `[A-Z]` inicial es exactamente lo que garantiza que solo entren screaming-case
constants.** No es un descuido: es el mecanismo que separa un token de clasificación de
cualquier palabra entre acentos graves. Y `ixMC_IO_DEBUG_UP_159` **no es un token de
clasificación**, así que está correctamente excluido. **`claims.py` está bien escrito.**

Las otras dos ocurrencias (`claims.py:309` y `:314`) son otro extractor distinto —el índice de
miembros de `enum`—, y tampoco están afectadas: los `ix*` son `#define`, no miembros de enum.

## 4 · Por qué el arreglo habría sido una regresión, y de qué tipo

Con `[A-Za-z_]` inicial, los 8916 identificadores perdidos entrarían en `fuera_de_lista`
(`claims.py:589`), que se imprime (`claims.py:1039`) como la lista de "cosas que parecen
clasificación y no lo son".

```text
  antes    7041 candidatos,  casi todos tokens de clasificacion reales
  despues 15957 candidatos,  de los cuales 8916 serian
           amdgpu_discovery,  sudo,  relocatable,  description,  compute_,
           srcversion,  un hash sha256 de 64 caracteres,  ...
```

Eso convierte una lista con significado —"esto dice ser una clasificación y no es una
clasificación conocida"— en ruido. **El arreglo habría intercambiado un falso negativo acotado por
un falso positivo masivo.** Y el falso negativo era, por lo que acabo de ver, **correcto**: esos
nombres no son clasificaciones.

Eso es un tipo de error que ya no me había pasado: no fue un número verosímil equivocado ni un
grep vacío. Fue **proponer un cambio destructivo sin leer qué hace el código que iba a
cambiar**, y justificado además con una medición —los 8916— que era cierta y que no
sostenía la conclusión. La medición era del ansi Pattern, no del Propósito.

## 5 · Lo que queda de `1546 §6`

```text
  SE RETIRA   "claims.py necesita aceptar minuscula inicial".  No lo necesita.
              No se hizo el cambio.  La herramienta no se toco.

  SE MANTIENE  la observacion tecnica que sigue siendo cierta:  8916 identificadores
              en minúscula  no entran por CLASE_RX.  Y eso es lo correcto,  porque
              CLASE_RX  extrae tokens de clasificacion y no identificadores.

  SE ABRE,  y es lo unico que sale de aqui:
              si en algun momento hace falta un indice de identificadores de los
              hallazgos,  no es este regex  y no hay que tocar claims.py.  Es otro
              extractor  y otro proposito.
```

Y queda una nota sobre `1546` que sí es sólida y que no retiro: **el hecho de que `[A-Z0-9_]` sea
case-sensitive, y de que `ix*` y `mm*` empiecen en minúscula, es real** — fue lo que me dio un
cero falso al medir `gmc_8_1_d.h` en el §5 de aquel hallazgo. Eso no lo inventé. Lo que hice mal
fue extrapolarlo a una herramienta que(resulta ser) no suffers del problema, porque el problema
que tiene es otro y es a propósito.

## 6 · Procedimiento

```text
PREGUNTA   ¿es cierto que claims.py no registra identificadores en minuscula, y hay
           que arreglarlo?
FUENTES    tools/claims.py:133  (el patron),  :580-590  (que hace con lo que
           encuentra),  :1039  (que imprime),  :111  (CLASES)
           :309  :314  (el segundo extractor, el de enums)
           medicion sobre los 796 ficheros de hallazgo:  7041 contra 15957
MEDIDO     CLASES  =  set de 50 entradas,  todas en mayusculas
     CLASE_RX  se usa  para extraer TOKENS DE CLASIFICACION,  no identificadores
     lo que no encaja  va a fuera_de_lista,  que se imprime
     ixMC_IO_DEBUG_UP_159  NO es un token de clasificacion  ->  bien excluido
     los ix*  son #define,  no miembros de enum  ->  el segundo extractor tampoco falla
     [A-Za-z_]  daria 8916 entradas mas en fuera_de_lista,  mayoritariamente ruido
RETRACTS  1546 §6 ultimo parrafo
DISPOSITIVO  NINGUNO.  Ninguna herramienta tocada.  i915 ausente,  amdgpu intacto
RUNTIME      NOT_RUN
LO QUE SIGUE
  - nada pendiente de este lado.  La deuda queda saldada sin tocar nada
  - el frente real sigue siendo el del hilo SMU/DPM  y el mapa pequeno y cerrado que
    nombro 1552:  DRAM_LOG_* en tres structs distintos,  y solo en uno se usa
```