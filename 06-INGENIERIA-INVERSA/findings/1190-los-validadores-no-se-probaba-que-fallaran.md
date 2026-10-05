# 1190 — Los validadores sabían **pasar**, y no se comprobó si sabían **fallar**. Medido por mutación: **9 de 17**. Cero falsos verdes después de arreglarlos, y la última fuga es `NO_APLICA`, que no es `PASA`

```text
AGENCIA=RX550-INVESTIGACION · WORK_CLASS=VALIDATOR-OF-VALIDATORS
AUTOR=AGENTE-INSTR
WRITE_EXECUTION=NONE · GPU=NONE TOUCHED · RUNTIME=NOT_RUN
DISPOSITIVO_TOCADO=NINGUNO · ni 0000:01:00.0 (1002:699f) ni 0000:00:02.0 (8086:0412)
ESCRITOS_POR_ESTA_ITERACION   tools/rxre.py  (155 -> 171 vectores, rc=0)
CLASE=TEST · MEDICION · ESTADO=MEDIDO_Y_CORREGIDO
GENERADO=2026-10-04 · MEDIDO=EN ESTA HOST
```

## 0 · La idea que sí se implementó, y la que no

La propuesta añade **V7 EXPERIMENTAL MEMORY, V8 META-REASONING, V9 SELF-OPTIMIZING, V10 EVIDENCE-CLOSED**, y termina diciendo algo que contradice el resto:

> *"ya tenemos suficiente arquitectura para dejar de diseñar abstractamente y empezar a obtener evidencia de uso real. Las mejoras posteriores deberían surgir de fallos observados."*

Eso último es lo correcto, y es lo que se hizo. **No se añadieron capas.** De las diez
dimensiones del criterio de mejora, esto mejora exactamente dos —`evidence quality` y
`contradiction detection`— y ninguna otra. Las otras ocho no se tocan.

Lo único que había **medible** en todo el mensaje era esto:

```text
VALIDATOR
   ↓
VALIDATOR OF VALIDATOR
   ├── oracle independence?
   ├── false-positive risk?
   ├── false-negative risk?
   └── ...
```

Y de esa lista, **una** se podía medir hoy con lo que ya existe:

```text
¿el validador ve el incumplimiento que dice ver?
```

## 1 · Lo que había, y lo que faltaba

`rxre` tiene nueve validadores ejecutables (`REGLAS`), cada uno nacido de una regla que
este proyecto ya pagó:

```text
AUSENCIA_NO_ES_INEXISTENCIA      NO_APLICA nunca es PASA
VERDE_NO_ES_CORRECTO             rc=0 no certifica
SOFTWARE_NO_ES_HARDWARE
COMPILAR_NO_ES_EJECUTAR
REPRESENTACION_NO_ES_FUENTE
SIN_PROBAR_NO_ES_DISPONIBLE
NULO_NO_ES_CERO
COINCIDENCIA_UNICA_NO_ES_INDEPENDIENTE
DECODIFICADO_NO_ES_VERIFICADO
```

Cada uno tenía vectores que probaban que **pasa** cuando la regla se respeta. Eso es la
mitad, y es la mitad fácil:

> Un validador que no dispara nunca da siempre verde, y no se distingue de uno que
> funciona.

Faltaba la otra mitad: dado un hecho que **incumple** la regla, ¿lo ve? Eso se mide
con **mutación** —se parte de un hecho que cumple y se le rompe uno de los campos que
la regla mira— y se cuentan las que detecta. Lo que no tenía es la medida.

## 2 · El resultado: 9 de 17, y la forma de las fugas

```text
deteccion 9 de 17   fugas: 8   controles rotos: 0
```

Cada regla detecta **su** violación canónica. Ninguna detecta una variante. Ese es
exactamente el perfil de "el test pasa y la puerta no cierra":

| Regla | Canónica | La que se le escapaba | Veredicto |
|---|---|---|---|
| `AUSENCIA_NO_ES_INEXISTENCIA` | `PROVEN_ABSENT` tras `NOT_FOUND` | `PROVEN_ABSENT` **sin decir el veredicto** | PASA |
| `VERDE_NO_ES_CORRECTO` | `validado=False` con `rc=0` | `validado` **ausente** | NO_APLICA |
| `SOFTWARE_NO_ES_HARDWARE` | `estatico` → `OBSERVED` | `"static"` → `OBSERVED` | PASA |
| `COMPILAR_NO_ES_EJECUTAR` | no reejecuta → `CORRECTO` | reejecuta y **da otra cosa** | PASA |
| `REPRESENTACION_NO_ES_FUENTE` | `decompilador` → `PROVEN` | `ghidra` → `PROVEN` | PASA |
| `SIN_PROBAR_NO_ES_DISPONIBLE` | `DISPONIBLE` sin probar | **`VALIDADO`** sin probar | PASA |
| `NULO_NO_ES_CERO` | `0` de origen desconocido | **`"0"` de texto** | PASA |
| `COINCIDENCIA_UNICA_NO_ES_INDEPENDIENTE` | 1 camino → `PROVEN` | 1 camino → **`CORROBORADO`** | PASA |

Las dos últimas merecen nombrarse aparte:

```text
VALIDADO sin probar  se colaba por el lado FUERTE de la misma puerta:
                     la regla solo miraba DISPONIBLE, y VALIDADO es MAS FUERTE
"0" como cero        "0" == 0 es False en Python, pero un cero LEIDO DE UN
                     FICHERO es una cadena, y una cadena numerica es una
                     suposicion con formato de numero
```

## 3 · Dos clases de fuga, porque no son lo mismo

Siete salían `PASA` y una `NO_APLICA`. Juntas en un número, la segunda hacía que la
primera pareciese menos grave. Separadas:

```text
FUGA_ENGANOSA   sale PASA.  La regla dice que el hecho es malo y el validador
                lo aprueba.  Esto es un FALSO VERDE.
FUGA_SIN_JUZGAR sale NO_APLICA.  No aprueba nada, pero tampoco protege: un
                hecho que no declara el dato escapa sin que nadie lo note.
```

## 4 · El defecto de método, que es el que más sale

Cinco de las siete fugas eran **el mismo defecto**:

> Una puerta que se abre cambiando una palabra no es una puerta.

Los validadores comparaban con `==` contra una palabra suelta:

```python
hecho["fuente"] == "estatico"
hecho["origen"] in ("descompilador", "decompilador")
```

Y se esquivaban con una escritura distinta del mismo hecho. Ahora el vocabulario
está **declarado** y es cerrado:

```python
ORIGEN_ESTATICO    = ("estatico","static","source","fuente","codigo", ...)
ORIGEN_REPRESENTACION = ("descompilador","ghidra","radare2","r2","cutter",
                         "pycdc","llvm-objdump","objdump","ida", ...)
AFIRMACION_FUERTE = ("proven","corroborated","corroborado","proven_derived", ...)
ESTADO_DISPONIBLE = ("disponible","validado","verificado","probada_ok", ...)
```

Y una palabra **no reconocida** no se trata como segura por omisión: es un estado
distinto.

### 4.1 Y el que me hice a mí mismo, en el mismo commit

Cerré dos vocabularios y **dejé el tercero abierto**:

```text
la regla   comparaba  afirmacion == "PROVEN"
la mutacion usaba     "CORROBORADO"      <-- el mismo concepto en castellano
```

Con las dos escrituras, la mutación pasaba. Cerrar dos y dejar el tercero no es
cerrar. Está escrito en el bloque del vocabulario para que no se repita.

## 5 · El estado final

```text
$ rxre mutacion

SENSIBILIDAD A MUTACION  16 de 17  (94%)
  falsos verdes: 0      sin juzgar: 1
  AUSENCIA_NO_ES_INEXISTENCIA              2/2
  COINCIDENCIA_UNICA_NO_ES_INDEPENDIENTE   2/2
  COMPILAR_NO_ES_EJECUTAR                  2/2
  DECODIFICADO_NO_ES_VERIFICADO            1/1
  NULO_NO_ES_CERO                          2/2
  REPRESENTACION_NO_ES_FUENTE              2/2
  SIN_PROBAR_NO_ES_DISPONIBLE              2/2
  SOFTWARE_NO_ES_HARDWARE                  2/2
  VERDE_NO_ES_CORRECTO                     1/2
      FUGA_SIN_JUZGAR  rc=0 con validado ausente  ->  NO_APLICA
```

La que queda **es el comportamiento correcto de esa regla**: sin `validado` no hay
nada que juzgar, y `NO_APLICA` no es `PASA`. Se declara en vez de anunciarse como
resuelta. Un vector comprueba que ninguna fuga `SIN_JUZGAR` sale `PASA`.

## 6 · Lo que esta medición NO mide, y hay que decirlo antes de que se lea de más

```text
MEDIDO      mutar UN CAMPO de los que la regla mira
NO MEDIDO   que el validador resista a un ORACULO EQUIVOCADO
NO MEDIDO   que la regla este bien escrita
NO MEDIDO   que un dato que miente de forma COHERENTE se detecte
NO MEDIDO   que el recuento de la validador sea correcto sobre el CORPUS REAL
            (669 hallazgos), y no sobre hechos inventados para la prueba
```

Esto es **un** frente de alarma, y `mutation_sensitivity` no es `correccion`. Los
mutantes son hechos que yo escribí para que la reglaFallara; un validador que
rechaza un mutante que yo mismo fabriqué no ha sido probado contra el cuerpo real
de hallazgos del árbol. Ese es el siguiente paso, y es el que sí mide.

Y hay un límite que conviene dejar escrito porque se va a pedir: **esta cifra mide
la detección de las mutaciones que se me ocurren.** No mide las que no se me
ocurren. Subir de 94% a 100% es añadir casos al fichero; que el 100% signifique algo
es un problema distinto, y sin resolver.

## 7 · Procedimiento

```text
anadido     MUTARIOS           17 (regla, nombre, hecho_que_cumple, mutacion,
                               por_que_deberia_verla)
            mutation_sensitivity()  por regla: deteccion/total/fugas/controles
            clasificacion de gravedad: FUGA_ENGANOSA / FUGA_SIN_JUZGAR
            cuatro vocabularios cerrados, con comparacion por palabra COMPLETA
            CLI `rxre mutacion`

medido      antes:  9 de 17 deteccion, 7 FUGA_ENGANOSA, 1 FUGA_SIN_JUZGAR
            despues: 16 de 17 (94%), 0 FUGA_ENGANOSA, 1 FUGA_SIN_JUZGAR
            controles: los 9 hechos que CUMPLEN siguen dando PASA
            rxre 155 -> 171 vectores, rc=0

corregido   1. NOT_FOUND sin veredicto ya no pasa
            2. "static"/"source"/"fuente" = "estatico"
            3. reejecuta Y da otra cosa ya no pasa
            4. seis instrumentos de representacion, no dos
            5. VALIDADO/VERIFICADO sin prueba ya no pasan
            6. el cero de TEXTO no es un cero medido
            7. CORROBORADO con un camino ya no pasa

no hecho    correr los mutantes contra los 669 hallazgos reales: los hechos que
            se han medido son sinteticos, y eso NO es lo mismo
escrituras  tools/rxre.py unicamente
runtime     RUNTIME=NOT_RUN.  Ni la RX550 ni la Intel.  i915 y amdgpu intactos
```
