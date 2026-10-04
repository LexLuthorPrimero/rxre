# 1055 — `--chip` no validado convertía un filtro mal formado en una conclusión de hardware

```text
AGENCIA=RX550-INVESTIGACION · WORK_CLASS=AGENT-MAIN-VALIDITY
GENERADO=2026-10-04 · MEDIDO=EN ESTA HOST
AFECTADO=tools/hwip.py:803 (--chip) · :899 (la consecuencia)
ESTADO=PROBADO · REPARADO · 5 vectores PASS · invariante bajo cwd
ORIGEN=08-ARQUITECTURA/FILTROS-MAL-FORMADOS.md
```

## El defecto

`tools/hwip.py` acepta `--chip` con default `CHIP_POLARIS12` y no lo valida contra nada.
Un nombre que no casa no da un error: da un resultado.

MEDIDO, tres invocaciones, las tres con **rc=0**:

```
$ python3 tools/hwip.py --chip CHIP_POLARIS12
$ python3 tools/hwip.py --chip Polaris12
$ python3 tools/hwip.py --chip CHIP_GA10
```

Las tres imprimen, textual:

```
  NINGUNO. Ningun `case CHIP_GA10:` del corpus escribe
  adev->ip_versions[] con un valor constante.

  Consecuencia directa: para esta GPU, TODAS las versiones de IP
  se leen de la tarjeta. No hay ningun atajo estatico.
```

Y aquí está lo que el informe de origen no había visto: **la frase «para esta GPU» está
fija en el código, en la línea 899**. Así que preguntar por `CHIP_GA10` —que no es esta
GPU— seguía afirmando una conclusión **sobre esta**. La herramienta hacía una
afirmación de hardware bajo una premisa falsa, con salida limpia y código de salida
cero.

> No es un filtro que devuelve el conjunto equivocado. Es un filtro que **decide**, y
> no dice que ha decidido.

## Por qué esto es la peor clase del proyecto, y hay 15 más

El hallazgo 1048 habla de un filtro que excluye por construcción a la población que dice
medir. El 1050, uno que devuelve vacío sin decirlo. Este es el tercero de la misma
familia y el más caro, porque el conjunto vacío **no se queda en el conjunto vacío**:
sale por la boca del programa como verdad sobre el hardware.

El proyecto tiene escrito lo contrario en varios sitios, y esta herramienta lo incumple
en la misma línea:

- `trace_path.py:510-512` valida `--chip` contra el enum y devuelve **rc=2**.
- `hwip.py:899` afirma una consecuencia sin mirar quién preguntó.

El patrón correcto ya estaba escrito, a un fichero de distancia.

## El arreglo, y mi primer intento falló

Lo primero que hice fue delegar en `tools/trace_path.py:parse_chip_enum`, que ya existe
y ya hace esto. Correcto en principio. **Imposible en la práctica:**

```
MEDIDO
find_kernel(None)      -> rx550-upstream-7.2.8/linux-7.2.8
amd_asic_type.h        -> solo existe en RESEARCH/kernelref/ y RESEARCH/kernelbuild/
                           NO en RESEARCH/baseline/ ni en el upstream
```

`parse_chip_enum` lee `include/drm/amd_asic_type.h`, y ese fichero no está en el árbol
que `hwip.py` usa. Con el enum vacío, **todos** los chips salían como desconocidos y mi arreglo
dejó **rc=2 hasta para `CHIP_POLARIS12`**.

MEDIDO, porque lo probé:

```
CHIP_POLARIS12   rc=2    ERROR  CHIP_POLARIS12 no es un ASIC de include/drm/amd_asic_type.h
```

> Un arreglo de un filtro que no distingue «filtro mal» de «no hay datos» es **el mismo
> defecto que repara, con el signo cambiado**. Antes decía «no hay hardcodeos» cuando
> preguntabas mal; después decía «no preguntes bien» cuando preguntabas bien.

Y la causa de mi error es la misma de siempre: **conté directorios a mano** para llegar
al enum, en vez de comprobar dónde está. `root` es `drivers/gpu/drm/amd`, y el kernel
está cuatro niveles arriba, no tres.

### La población correcta es la que la herramienta ya razona

Los nombres `CHIP_` que aparecen **en su propio corpus**:

```
MEDIDO sobre rx550-upstream-7.2.8/linux-7.2.8
  nombres CHIP_ distintos en el corpus   39
  CHIP_POLARIS12 aparece                 74 veces
  los mas frecuentes: CHIP_POLARIS10 99, CHIP_POLARIS12 74, CHIP_TONGA 70,
                     CHIP_POLARIS11 69, CHIP_HAWAII 63, CHIP_KAVERI 63
```

Un ASIC que no está ahí **no puede tener un `case` que escribir**, así que la respuesta
honesta es «no conozco este ASIC», que es distinta de «no hay ningún hardcodeo». Y esa
población no puede fallar por un fichero que falta, que es lo que me pasó.

## La decisión que tomé: `--chip Polaris12` **funciona**

Es el error que cualquiera cometería, y convertirlo en un error de uso sería una barrera
falsa. Pero solo si la resolución es **única**:

| paso | regla | resultado |
|---|---|---|
| 1 | coincidencia exacta | se usa |
| 2 | sufijo único, sin distinguir mayúsculas | se usa, **con aviso en stderr** |
| 3 | ambiguo, o no existe | **no se elige**, rc=2 con los candidatos |

El paso 3 es el importante: aceptar el primero de varios sería volver a hacer lo mismo
que hacía el filtro, elegir en silencio un destino que el usuario no dijo.

MEDIDO, los cinco casos:

```
CHIP_POLARIS12   rc=0   Consecuencia directa: para CHIP_POLARIS12, TODAS las versiones de IP ...
Polaris12        rc=0   AVISO  --chip Polaris12 resuelto a sufijo unico
CHIP_GA10        rc=2   ERROR  CHIP_GA10 no es un ASIC que aparezca en el corpus (39 conocidos)
nonsense         rc=2   ERROR  nonsense no es un ASIC que aparezca en el corpus (39 conocidos)
Polaris          rc=2   ERROR  Polaris no es un ASIC que aparezca en el corpus (39 conocidos)
                       quiza: CHIP_POLARIS10, CHIP_POLARIS11, CHIP_POLARIS12
                       No se afirma nada sobre ningun ASIC: un filtro que no casa
                       no puede producir una conclusion de hardware.
```

Y la consecuencia ahora **nombra el chip que se preguntó**, en vez de decir «esta GPU»:

```python
# antes, fijo:
print("  Consecuencia directa: para esta GPU, TODAS las versiones de IP se leen")
# despues, del chip resuelto:
print("  Consecuencia directa: para %s, TODAS las versiones de IP se leen" % chip)
```

`CHIP_GA10` da rc=2 diciendo *«no aparece en el corpus»*, no *«no existe»*. Que es
exactamente la distinción `PARTIAL` frente a `PROVEN_ABSENT`, en el mensaje de error de
una herramienta.

## Verificado

| prueba | resultado |
|---|---|
| `--chip CHIP_POLARIS12` | rc=0, y la consecuencia nombra el chip |
| `--chip Polaris12` | rc=0 con aviso visible de resolución |
| `--chip CHIP_GA10` / `nonsense` / `Polaris` | **rc=2**, sin afirmar nada |
| `--chip Polaris` | lista los 3 candidatos |
| self-test | **PASS, 5 vectores**, 6 OK / 0 FAIL |
| misma invocación desde la raíz y desde `tools/` | salida **byte a byte idéntica** |

La última es la del hallazgo 1051: `toolreg.py:485` corre los self-tests con
`cwd=os.path.dirname(t.path)`, así que una herramienta que dependa del directorio de
trabajo se rompe justo en la puerta que la valida.

## Lo que NO se afirma y NO se ha hecho

- **No he tocado las otras 12 herramientas** del informe. Quedan 16 argumentos en 13
  ficheros, y este repara **uno**. Los demás tienen nombre y línea en
  `08-ARQUITECTURA/FILTROS-MAL-FORMADOS.md`.
- **No se ha escrito `tools/puerta_filtros.py`.** El §8 del informe es un contrato, no un
  código: no existe esa herramienta. Y su primer oráculo **ya se ha falsado una vez**,
  dio un OK falso sobre este mismo fichero, y con el oráculo anclado al valor pasó a 9.
  Una puerta con el oráculo ancho habría autorizado en verde los ocho reparos que el
  informe propone.
- **`tools/reg_census.py:240 --gfx` sigue sin testigo ejecutado**, a más de 180 s. Puede
  ser un falso positivo del informe y no lo he comprobado.
- **`revkit/klog.py` y `revkit/obs.py` no son verificables**: leen `dmesg` y `journalctl`.
- **`revkit/huerfanos.py` lo está cambiando otra sesión** en este momento. Las seis
  líneas que el informe cita siguen diciendo lo que cita, pero el fichero se movió
  durante el turno y no he vuelto a medirlo.
- **No se ha tocado `tools/regconst.py`**, que es el mismo defecto que el hallazgo 1050
  con el mismo `metavar="CLASE"`. Verificado por mí: su resumen es **idéntico** para una
  clase válida, para una inexistente y para un valor sin forma de clase.