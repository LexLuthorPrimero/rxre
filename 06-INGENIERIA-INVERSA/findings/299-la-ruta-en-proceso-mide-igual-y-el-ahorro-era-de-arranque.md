# 299 · La ruta en proceso mide igual, y el ahorro era de arranque: la premisa de coste era falsa

```text
CLASSIFICATION=NEGATIVE_RESULT+MEASUREMENT+ERROR · TRACK=TOOLING
CORPUS=NINGUNO (el proyecto) · HARDWARE_SCOPE=NONE
WORK_CLASS=READ_ONLY/EVIDENCE+WRITE_LOCAL · WRITE_LOCAL=PROPIOS · MODIFICATIONS_CORPUS=0
RUNTIME=NOT_RUN · GPU INTACTA · CERROJOS=0
```

## Qué resuelve

El `NEXT_ACTION` de `298` era el último eslabón de la cadena de cobertura:

```text
  que cada herramienta se mida a si misma
  y que mutscore lea su numero en vez de recalcularlo con un subproceso por bandera
```

La justificación escrita era de coste: «es lo que hoy cuesta `lint --json` en
23,7 s dentro de un test».

**La acción no se hace. La cobertura no es el motivo, y el coste tampoco.** Las
dos cosas se han medido, y las dos dicen que no.

## 1 · La ruta en proceso mide EXACTAMENTE lo mismo

Lo que hace hoy `mutscore` es lanzar un subproceso con el `BOOTSTRAP`, y el hijo
escribe su `lineas.json`. La alternativa es llamar a `main()` **dentro del propio
proceso**, bajo un `settrace` propio, y que la herramienta publique el número.

Medido, con la sonda de `runpy` y el `sys.argv` puesto a la bandera:

```
  herramienta        subproc   en-proceso   solo-en-proceso   el subproc ve y el otro no
  lint.py              218          217               0              [0]
  nextnum.py            87           86               0              [0]
  govcheck.py          393          392               0              [0]
  fingerprint.py       173          172               0              [0]
```

`solo-en-proceso = 0` en los cuatro: **la ruta en proceso no cubre ni una línea
que la otra no cubra.** Y lo que falta es exactamente `[0]`.

### Y mi primera sonda estaba mal, y lo dice

La primera medición dio otra cosa, y mucho más dramática:

```
  herramienta        subproc   en-proc   solo-en   faltan
  lint.py              218        176         0      42
  govcheck.py          393        349         0      44
  fingerprint.py       173        113         0      60
```

Cuarenta y dos líneas que la ruta buena ve y la mala no. **Y era mi sonda, no la
ruta.** Había escrito `runpy.run_path(src, run_name="__sonda__")`, y con ese
nombre el guard

```python
  if __name__ == "__main__":
      sys.exit(main())
```

**no se ejecuta**. Lo que faltaba no era la ruta de informe: era el cuerpo del
módulo, que empieza en la línea 3. Las cinco herramientas terminan igual:

```
  lint.py / nextnum.py / govcheck.py / fingerprint.py   if __name__ == "__main__": sys.exit(main())
  toolkit.py                                             if __name__ == "__main__": raise SystemExit(main())
```

Con `run_name="__main__"` y dejando que sea el guard quien llame a `main()`, las
dos rutas dan el mismo conjunto salvo la línea 0.

Esto es `294` por tercera vez: **el detector que da una cifra dramática suele
tener el defecto en el detector.** Si la cifra dice «te faltan 60 líneas», lo
primero que hay que mirar es el detector.

## 2 · El ahorro era de arranque, no de trabajo

```
  herramienta       bandera          subproc     en-proceso    ahorro
  lint.py           --censo          0.895 s      0.042 s      0.853 s
  nextnum.py        --json           0.118 s      0.007 s      0.111 s
  fingerprint.py    --json           1.319 s      0.253 s      1.066 s
  lint.py           --json          38.425 s     25.261 s     13.164 s
  govcheck.py       --json          19.482 s     20.075 s     -0.592 s
```

En las banderas baratas se ahorra tiempo de arranque: 118 ms → 7 ms. En las caras
el ahorro es del orden del ruido, y `govcheck` salió **más lenta** en proceso
(−0,592 s, es decir perdió).

La razón es obvia y no hacía falta medirla: **un subproceso de Python cuesta ~40
ms, y `lint --json` tarda segundos.** El 23,7 s de la justificación es el
escaneo del árbol, y ese trabajo hay que hacerlo igual aunque no haya proceso de
por medio.

```text
  lo que se iba a ahorrar: el arranque de un interprete
  lo que se iba a cambiar: una herramienta de produccion
  la relacion entre las dos cosas: 40 ms contra 23 700 ms
```

## 3 · Y aun así no se haría, por un motivo que no es el coste

Porque el motivo bueno es peor que el motivo escrito.

`mutscore` es el **auditor**. Si cada herramienta publica su propia cobertura, el
auditor pasa a leer un número que ha calculado el audited, con el criterio del
audited, en un entorno que el auditor no controla.

Eso es exactamente el error de `297` un nivel más arriba:

```text
  297  un test que delega en un proceso y no observa el proceso
       tiene el mismo problema que uno que comprueba `exit 0`
  299  y un auditor que delega en el audited tiene el mismo problema
       que uno que comprueba su palabra
```

Se paga con insertar un `settrace` global en cinco herramientas de producción,
que es lo que más puede cambiar el comportamiento de un programa: multiplica el
coste de todo y se lleva por delante cualquier depurador. Y a cambio no se gana
cobertura, que ya era la misma.

```text
  ACCION PROPUESTA   cobertura identica   menos coste marginal   pierde independencia
  VEREDICTO          NO SE HACE, y el motivo no es el coste
```

## 4 · El hallazgo de verdad: el mismo comando, medido 39 veces

Mientras se comprobaba lo anterior, el mismo comando dio cinco cifras:

```
  python3 tools/lint.py --json

      23 757 ms     medido al principio de la sesion
      38 425 s      medido con la sonda de coste
       2 929 ms     medido con el inventario de banderas
       3 486 ms     vuelta 1 del entrelazado
     116 928 ms     vuelta 6, sin aviso

  el mismo fichero, el mismo argumento, la misma maquina, el mismo minuto
```

**Cuarenta veces.** Y `govcheck --json` se disparó en la misma vuelta, de 4,3 s a
23,7 s. Dos herramientas distintas, mismo turno, mismo pico: eso no es una
herramienta lenta, es otra cosa.

### Y hay un diseño que lo separa

La carga nula, medida **entrelazada** con la herramienta en el mismo bucle:

```
  vuelta   bucle-nulo    lint --json     ratio
      1        618 ms       3486 ms        564
      2        618 ms       2914 ms        471
      3        607 ms       2956 ms        486
      4        707 ms       3003 ms        424
      5        649 ms       3002 ms        462
      6        599 ms       2953 ms        492
```

Ni el bucle ni la herramienta se mueven. **Seis vueltas planas, y el pico no se
reproduce.** Entrelazar es lo que convierte «la máquina estaba ocupada» de una
disculpa en una afirmación: si la carga nula se disparase con la herramienta, es
la máquina; si solo se dispara la herramienta, es la herramienta.

Y el culpable se vio sin instrumentación:

```
  ./08-ARQUITECTURA/tools/fronteras.py
  ./revkit/atomrom.py
  ./06-INGENIERIA-INVERSA/findings/938-techo-de-envio-38us-y-por-debajo-de-60us-...
  ./06-INGENIERIA-INVERSA/findings/930-bench-ky-no-tenia-control-de-frescura-...
  ./06-INGENIERIA-INVERSA/findings/934-marcas-de-tiempo-refutan-el-envio-fallido-...
  ./06-INGENIERIA-INVERSA/findings/928-282-1-ruta-de-texel-validada-pero-no-medible-...
  ./06-INGENIERIA-INVERSA/findings/942-282-2-cerrada-en-283-y-arrastrada-en-cinco-...
  ./06-INGENIERIA-INVERSA/findings/933-282-discriminante-ejecutado-no-separa-...
```

Once ficheros escritos en seis minutos, **otro agente, con su propia maquinaria
pesada, en el mismo árbol y la misma máquina.** Dos agentes escribiendo a la vez es
la condición conocida del proyecto (§102, `PROJECT_ACTIVE_AGENT <= 1`, que ya se
sabía incumplido); lo nuevo es que **también contamination el cronómetro**.

### El corolario, que es lo que hay que llevarse

```text
  NINGUNA CIFRA DE COSTE DE ESTE PROYECTO ES CITABLE SIN SUS CONDICIONES DE CARGA
```

Ni los 23,7 s de la justificación de esta acción, ni los 188 s de `--cobertura`,
ni los 3 s que hicieron parecer barato lo que antes salía a 40. Medidas en
silencio: `--cobertura` son 87,4 s y 100,8 s. Medidas con carga ajena: 188 s. Las
tres son el mismo programa.

## 5 · De paso: la línea 0, y por qué las «303» eran las 303

`settrace` emite un evento de línea para el marco del módulo con `f_lineno == 0`,
antes de ejecutar nada. Esa línea entraba en la lista como si fuera código.

Retirado el filtro, **los niveles bajan uno cada uno y el total no se mueve**:

```
                     con el 0    sin el 0
  lint.py                 377         376
  nextnum.py              232         231
  govcheck.py             348         347
  fingerprint.py          172         171
  toolkit.py              242         241
  NUEVAS, cada una        53          53
  NUEVAS, total           303         303
```

El fantasma estaba **en los dos operandos de cada resta**, así que se cancela. Y
de aquí sale una regla que es más útil que el arreglo:

```text
  UNA METRICA HECHA COMO RESTA AGUANTA UN ARTEFACTO ADITIVO
  UNA METRICA INFORMADA COMO NIVEL, NO
```

La de `298` era una diferencia, y por casualidad-eraimmune. La tabla absoluta de
`298` estaba inflada en uno por herramienta, y eso sí que no se puede arreglar
retroactivamente porque está escrita.

**Y elMatched de haberlo comprobado**: si se hubiera «corregido» sin comparar
antes y después, se habría escrito una corrección falsa diciendo que las 303 eran
298. El número era correcto. Sólo se sabe comprobando si se mueve.

El filtro está en `lineas_de_invocacion()` con la razón escrita al lado, y tiene
un vector **probado con dientes**: quitar el filtro a propósito lo hace fallar y
devuelve el total a 303.

## 6 · Lo que NO se establece

```text
  la proporcion real de la causa del pico
    NO_DETERMINADA. La carga nula no se dispara en la misma vuelta que el pico,
    porque el pico no se reproduce. Se sabe que no era la herramienta y que
    habia otro agente escribiendo; no se sabe cuanto de los 116 928 ms fue suyo
  el coste de `mutscore --cobertura` con la maquina descargada
    87 400 ms y 100 754 ms. Son dos medidas y hay dos ordenes de magnitud de
    varianza, asi que la cifra honesta es "unos 90 s, con la carga que haga"
  si la ruta en proceso es mas rapida en un caso real de uso
    NO MEDIDO, y ya no importa: la accion no se hace por la independencia, no
    por el rendimiento
  las tres herramientas sin vectores de ruta
    SIN TOCAR. `govcheck --json` son 4,45 s y su `--selftest` 9,96 s; `fingerprint
    --json` 0,45 s; `toolkit` no expone banderas por `add_argument`. Con los
    costes Medidos por fin de verdad, `fingerprint` y `toolkit` caben y `govcheck`
    no. No se ha hecho ninguna de las dos cosas
```

## 7 · Trazabilidad

```text
  /tmp/opencode/sonda_enproceso.py    la primera sonda, con run_name equivocado
  /tmp/opencode/sonda_enproceso2.py   la misma con el guard, que es la buena
  /tmp/opencode/sonda_coste.py        el reparto subproceso/en-proceso
  /tmp/opencode/banderas.py           el coste de cada bandera y de cada suite
  /tmp/opencode/ms_linea0.bak         copia previa a quitar el filtro
  tools/mutscore.py                   lineas_de_invocacion() con el filtro y 2 vectores
  findings/298                        las 303 y la tabla de niveles, ya escritas
```

## 8 · Corrección de numeración

```text
  este fichero se escribio como 299, reservado con --reservar antes de escribir
  CORRECTED_BY: --reservar 299  RESERVADO
  y en el momento de reservarlo el arbol ya tenia 451 hallazgos y el mas alto era
  el 945, porque hay otro agente reservando en el mismo numero
```
