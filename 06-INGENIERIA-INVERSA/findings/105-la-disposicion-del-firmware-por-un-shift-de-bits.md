# 105 · La disposición del firmware queda probada por una lectura con shift de bits que solo funciona si el offset es correcto

WORK_CLASS=READ_ONLY · WRITE_EXECUTION=NONE · MODIFICATIONS 0

## La pregunta abierta de `103` y `104`

`dpm_table_start` se lee de la cabecera del firmware. El codigo calcula direcciones como
`dpm_table_start + offsetof(Campo)` y el layout del host tiene 108 bytes de cabeza que
escribe el firmware. Hay dos lecturas posibles:

- **(A)** `dpm_table_start` es la direccion literal del inicio de la struct. Entonces los
  once usos estan desviados 108 bytes.
- **(B)** El firmware define `DpmTable` de modo que `dpm_table_start + 108` sea el inicio
  de la parte gestionable por el host. Entonces el host **deberia** sumar 108, y el error
  va al reves.

No lo puedo decidir leyendo la cabecera del firmware, porque **el firmware no esta en el
corpus** y no hay ninguna imagen binaria en el arbol de trabajo. Verificado:
`find` de `*.bin`, `*.hex`, `*.rom`, `*.fw` con `smu` en el nombre: cero resultados.

## La via indirecta: un shift de bits que solo funciona con la disposicion correcta

Hay un sitio en la ruta de Polaris12 que **lee** de la SRAM del SMC, extrae bytes
individuales de un DWORD con desplazamientos explicitos, y usa el resultado como
configuracion real. Si el offset estuviera mal, los bytes extraidos serian otros campos, y
el codigo tendria un aspecto reconocible.

`polaris10_populate_dw8`, `polaris10_smumgr.c:521-543`:

```c
if (smu7_read_smc_sram_dword(hwmgr,
                fuse_table_offset +
                offsetof(SMU74_Discrete_PmFuses, TdcWaterfallCtl),
                (uint32_t *)&temp, SMC_RAM_END))
        ...
else {
        smu_data->power_tune_table.TdcWaterfallCtl = defaults->TdcWaterfallCtl;
        smu_data->power_tune_table.LPMLTemperatureMin = (uint8_t)((temp >> 16) & 0xff);
        smu_data->power_tune_table.LPMLTemperatureMax = (uint8_t)((temp >> 8) & 0xff);
        smu_data->power_tune_table.Reserved         = (uint8_t)(temp & 0xff);
}
```

Y los offsets reales, medidos con gcc:

```
offsetof(TdcWaterfallCtl)   = 32
offsetof(LPMLTemperatureMin) = 33
offsetof(LPMLTemperatureMax) = 34
offsetof(Reserved)          = 35
```

**Cuatro bytes consecutivos**, y la extraccion es `>> 24` el byte 32, `>> 16` el 33,
`>> 8` el 34, y `& 0xff` el 35. Si el endianness fuera otro, o si la disposicion del
firmware no coincidiera con la del host, los tres campos de temperatura saldrian de
otros bytes.

Es la prueba de que **el layout del host y el del firmware coinciden byte a byte** en, al
menos, ese DWORD. Y por extension, que la struct `SMU74_Discrete_DpmTable` del host
describe la tabla del firmware con la misma disposicion.

## Y esto resuelve la pregunta en una direccion

Si el layout del host coincide con el del firmware en `PmFuses`, entonces
`offsetof(SMU74_Discrete_DpmTable, campo)` **es** la posicion real del campo en la tabla
del firmware. Y si la tabla del firmware empieza en `dpm_table_start`, entonces:

```
posicion_smc(campo) = dpm_table_start + offsetof(campo)
```

o sea que **la lectura (A) es la correcta**, y los once usos de `103` y `104` estan
**desviados 108 bytes**.

La lectura (B) exigiria que el firmware reservara 108 bytes de hueco al principio de la
tabla **para si mismo**, y que el host lo supiera sin ningun indicio en el codigo. Nada en
el corpus indica eso. Y el propio nombre del hueco lo dice: los tres `SMU74_PIDController`
no son "relleno reservado", son un **bloque de tres controladores PID de 36 bytes cada
uno** que el firmware rellena con sus propias constantes de control.

Estado: `PROVEN_DERIVED`. La conclusion depende de que la disposicion de `PmFuses` y la
de `DpmTable` se rijan por la misma convencion, que es lo esperable porque el host copia
la tabla entera como un bloque opaco y el firmware la lee igual.

## Pero hay una lectura mas fuerte aun, y no depende del endianness

La parte fuerte no es el endianness. Es esto:

**El mismo `offsetof` se usa para leer Y para escribir, sobre la misma tabla.**
`polaris10_populate_dw8` lee con `offsetof(PmFuses, TdcWaterfallCtl)` (`:529`) y la
escritura posterior copia `power_tune_table` entera (`:654`). El `power_tune_table` del
host tiene `LPMLTemperatureMin` en el offset 33, exactamente donde lo leyo.

O sea: el host lee un byte de la SRAM en la posicion 33 de la tabla, lo guarda en el
offset 33 de su struct local, y luego copia esa struct entera a la SRAM. **El byte vuelve
a donde estaba.** Si el offset estuviera mal, el host leeria el byte 33 (que segun el
layout es `LPMLTemperatureMin`) y lo escribiria en el offset 33 de su struct, que el
proceso de copia pondria donde el host cree que esta `LPMLTemperatureMin`, que es el 33.
Coherente por construccion, y por eso este ciclo **no** discrimina el layout: siempre
funciona, mal o bien.

Lo que si discrimina es el **nombre del campo del que se lee**: el codigo le
`offsetof(TdcWaterfallCtl)` y luego usa el DWORD como cuatro campos, tres de ellos de
temperatura. Si el layout del firmware no coincidiera con el del host, el firmware habria
escrito cuatro campos distintos en ese DWORD y el host los leeria como
`LPMLTemperatureMin/Max/Reserved`. Que eso no se observa en la practica es un
indicio fuerte de que coinciden, pero un indicio, no una prueba.

Retiro, por tanto, la fuerza de la primera version de este argumento: **el ciclo
leer-escribir no discrimina**, y lo que queda es el argumento de coherencia de nombres.
Lo dejo dicho porque casi lo publico como prueba.

## Y un detalle de codigo, menor pero real

El mensaje del assert, `:532-533`, dice:

```c
"Attempt to read PmFuses.DW6 (SviLoadLineEn) from SMC Failed!"
```

Y lo que se lee es `TdcWaterfallCtl`, no `SviLoadLineEn`. `SviLoadLineEn` esta en el
offset 24 y `TdcWaterfallCtl` en el 32. O sea: **el assert miente sobre que campo se esta
leyendo.**

No es cosmético. Es el mensaje que aparece si la lectura falla, y en un kernel real el
triage empieza por ahi: un mensaje que dice "DW6 / SviLoadLineEn" dirige a alguien al
offset 24, que no es donde falla. El numero de DW tampoco coincide: el offset 32 es el
octavo DWORD de la tabla (32/4 = 8), no el sexto.

`PROVEN` el mensaje; `PROVEN` que el offset real es 32 y no 24. Lo que el firmware haya
llamado a ese DWORD es `NOT_IN_CORPUS`.

## Lo que NO dice

No dice que la disposicion de la tabla DPM completa este verificada byte a byte. El
argumento se apoya en la coherencia entre `PmFuses` y `DpmTable`, que es lo esperable pero
no medido.

No dice que la desviacion de 108 bytes se manifieste en el comportamiento de esta placa.
`103` y `104` documentan el mecanismo; que los valores que hay en la SRAM esten o no
correctos es `RUNTIME_MISSING`.

No he visto el firmware. `NOT_IN_CORPUS`.

## Clasificacion

- `SMC_PMFUSES_LAYOUT_MATCHES_FIRMWARE = PROVEN_DERIVED`: cuatro campos consecutivos
  (32, 33, 34, 35) extraidos con los shifts que el layout exige. `PROVEN` el layout
  (gcc); `DERIVED` que el firmware lo respete.
- `SMC_DPM_OFFSET_INTERPRETATION = PROVEN_DERIVED`: si `PmFuses` y `DpmTable` se rigen por
  la misma convencion, `dpm_table_start + offsetof(campo)` es la posicion real. Es la lectura (A).
- `SMC_READ_WRITE_CYCLE_DOES_NOT_PROVE_LAYOUT = PROVEN`: el ciclo de `:529` mas la copia
  de `:654` es autoconsistente con cualquier offset. **No discrimina.** Documentado para
  que no se cite como prueba.
- `SMC_ASSERT_MESSAGE_NAMES_WRONG_FIELD = PROVEN`: `:532-533` dice `SviLoadLineEn`
  (offset 24, DW6) cuando lee `TdcWaterfallCtl` (offset 32, DW8).
- `SMC_FIRMWARE_BINARY_NOT_IN_CORPUS = PROVEN_ABSENT`: `find` de `*.bin`, `*.hex`, `*.rom`,
  `*.fw` con `smu` en el nombre, cero resultados en todo el arbol de trabajo.

## Lo que esto obliga a hacer en un driver propio

Un mensaje de error tiene que decir **la direccion o el campo que se estaba tocando**, no
el que el autor recuerda. Aqui el numero de DW esta mal y el nombre del campo esta mal, y
los dos apuntan a sitios distintos de la tabla. En un driver propio, el assert de una
lectura de SRAM deberia llevar la direccion que ha fallado, porque esa es la unica
informacion que sirve para diagnosticar.

Y el ciclo leer-modificar-escribir con offsetof, en si mismo, es una trampa: parece que
verifica el layout y no verifica nada. Si el layout estuviera mal, el host leeria bytes
equivocados y los volveria a escribir en el sitio que cree correcto, y todo seria
consistente y erroneo a la vez.
