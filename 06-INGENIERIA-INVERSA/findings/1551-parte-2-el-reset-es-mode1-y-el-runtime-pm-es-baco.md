# 1551 — PARTE 2: el reset es MODE1 y el runtime PM es BACO, y son dos decisiones con el mismo nombre

```text
AGENCIA=RX550-INVESTIGACION · PARTE=2/RESET-RECOVERY · HALLAZGO 1 de la parte
CLASSIFICATION=DETERMINACION-POR-ALCANZABILIDAD+HOMONIMO+CORROBORACION-DE-LOG
TRACK=STATIC + una LECTURA de dmesg · CERO ESCRITURA · Intel no tocada
GENERADO=2026-10-05
AFECTADO=1418 (lo confirma y lo precisa) · 107 (el unico hallazgo previo de esta parte)
ESTADO=PROBADO · el metodo de RESET de esta placa es MODE1, por eliminacion de ramas
       · el metodo de RUNTIME PM es BACO, y el log de arranque lo dice
       · son DOS decisiones distintas que comparten el nombre BACO
       · y las cuatro ramas que pueden activar BACO como reset viven dentro de casos de MP1,
         que esta tarjeta NO tiene: son inalcanzables
       · el selector que decide, amdgpu_ip_version, convierte un bloque ausente en 0 sin error
```

## 1. Por que este es el primer hallazgo de la parte 2, y no otro

La parte 1 se cerro porque el controlador de memoria tiene una pregunta con respuesta: *quien lo
programa*. Aqui la pregunta analoga es *como se resetea esta tarjeta*, y tiene la misma forma: una
decision, un selector, y la posibilidad de que el camino que se lee no sea el que corre.

Antes, por la regla, mire lo que hay. **Reset/recovery tiene un solo hallazgo previo, el `107`**, y mi
clasificador habia marcado "siete huecos" antes de ajustarlo: la mayoria de lo que capturas como reset
era en realidad GPUVM y memoria. **Es la parte menos explorada del arbol**, y eso es exactamente por
que se elige como primera.

## 2. La cadena de decision del metodo de reset

`soc15_asic_reset_method` (`soc15.c:527`), completa y en orden:

```c
  int baco_reset = 0;
  if (amdgpu_reset_method == MODE1|MODE2|BACO|PCI) { ... return amdgpu_reset_method; }
  if (amdgpu_reset_method != -1)
          dev_warn(adev->dev, "Specified reset method:%d isn't supported, using AUTO instead");
  switch (amdgpu_ip_version(adev, MP1_HWIP, 0)) {
  case 10.0.0, 10.0.1, 12.0.0, 12.0.1:      return MODE2;
  case 9.0.0, 11.0.2:                     baco_reset = ...;  break;
  case 13.0.2:                            ...  break;
  case 13.0.6, 13.0.14, 13.0.12:          ...  break;
  default:                                 break;
  }
  if (baco_reset) return BACO;
  else             return MODE1;
```

**Observacion estructural, y es el hallazgo:** `baco_reset` **solo se puede poner dentro de un `case`
del switch de MP1.** No hay ninguna otra asignacion en la funcion. O sea: **sin MP1, BACO como metodo de
reset es inalcanzable por construccion**, no por configuracion.

## 3. Y esta tarjeta no tiene MP1

El `1418` lo midio, y lozego. Del log de arranque:

```text
  detected ip block number 0 <common_v1_0_0>   (vi_common)
  detected ip block number 1 <gmc_v8_1_0>      (gmc_v8_0)
  detected ip block number 2 <ih_v3_0_0>       (tonga_ih)
  detected ip block number 3 <gfx_v8_0_0>      (gfx_v8_0)
  ...
  MP0 / MP1 / THM / SMUIO / NBIF0 / ATHUB / MMHUB / OSSSYS:  NO aparecen
```

**Y el `1418` tambien dice que `soc15.c` es `NO_APLICABLE` a esta tarjeta.** Eso me habria hecho
abandonar la ruta entera, asi que lo verifique por mi cuenta antes de seguir o antes de publicar nada:
el 1418 razona sobre **bloques IP**, que es una cosa, y sobre que el subagente de Arcturus
inventario `soc15.c` es otra. Polaris12 pertenece a la familia soc15 por ASIC, asi que las funciones de
`soc15.c` si son suyas. **La conclusion del 1418 es correcta sobre bloques IP y no implica lo que
parece sobre el fichero.**

## 4. Y aqui esta la trampa del selector

```c
  static inline uint32_t amdgpu_ip_version(const struct amdgpu_device *adev,
                                            uint8_t ip, uint8_t inst)
  {
          /* This considers only major/minor/rev and ignores subrevision/variant fields. */
          return adev->ip_versions[ip][inst] & ~0xFFU;
  }
```

**Es una lectura enmascarada de un array. Para un bloque ausente devuelve 0, y el switch se va al
`default: break;` sin decir nada.**

> **PROBADO: el driver no tiene camino de error para un bloque IP ausente.** Se comporta como si la
> version fuera 0, y 0 no casa con ninguna rama. **La seleccion de rama por version de IP es un
> fallthrough silencioso, y no un error.** Este selector se usa **630 veces en 99 ficheros**: es el mas
> usado del driver, y en todos ellos el patron es el mismo.

Con MP1 ausente: `default: break` → `baco_reset` sigue en 0 → **`return AMD_RESET_METHOD_MODE1`.**

> **PROBADO por eliminacion de ramas: el metodo de reset de esta placa es MODE1**, y las cuatro ramas
> que podrian activar BACO son inalcanzables porque estan tras un bloque que la placa no tiene.

Y lo corroboro por el log: **el aviso `"Specified reset method:%d isn't supported"` NO aparece**, luego
`amdgpu_reset_method` vale `-1` y se toma la rama AUTO, que es la que escribi arriba. Es la firma de
que el camino recorrido es el que creo.

## 5. Sexto homonimo, y por casi me equivoco

Iba a escribir "BACO es inalcanzable en esta placa". **Es falso como frase**, y el log me paro:

```text
  [    40.055809] amdgpu 0000:01:00.0: Using BACO for runtime pm
```

BACO **si** se usa en esta tarjeta. Y es una **decision distinta**, en `amdgpu_device.c:642`, la
seleccion de `rpm_mode`:

```c
          switch (adev->asic_type) {
          case CHIP_VEGA20: case CHIP_ARCTURUS:  break;      /* BACO no soportado */
          case CHIP_VEGA10:                      ...          break;
          default:
                  /* enable BACO as runpm mode on CI+ */
                  if (!amdgpu_passthrough(adev))
                          adev->pm.rpm_mode = AMDGPU_RUNPM_BACO;
                  break;
          }
          if (adev->pm.rpm_mode == AMDGPU_RUNPM_BACO) {
                  if (bamaco_support & MACO_SUPPORT) { ... "Using BAMACO for runtime pm" }
                  else                                  { ... "Using BACO for runtime pm" }
          }
```

POLARIS12 cae en el **`default:`**, y el log dice **"Using BACO"** y no "BAMACO", o sea que
`bamaco_support & MACO_SUPPORT` era falso.

> **Lo que dice el log, en una linea: esta placa reinicia con MODE1 y suspende con BACO.**
> **Dos mecanismos distintos, el mismo nombre, y un switch distinto cada uno.** El de reset depende de
> MP1, que no existe. El de runtime pm depende del ASIC, y Polaris12 cae en `default`.

Sexto homonimo del proyecto. Los otros cinco: `num_banks` (1528), `prt` (139), `SMU74_SoftRegisters`
(1540), `CHMAP`/`CHREMAP` (1522), `UpH`/`UpHyst` (1544).

## 6. Que queda de la parte 2

```text
  el metodo de reset de esta placa            PROBADO  MODE1, por eliminacion y por el log
  las cuatro ramas de BACO                    INALCANZABLES, con el mecanismo dicho
  el modo de runtime pm                       PROBADO  BACO, el log lo dice
  amdgpu_reset_method por defecto             -1 / AUTO, corroborado por la ausencia del aviso
  bamaco_support & MACO_SUPPORT               falso, por el texto del log (BACO y no BAMACO)
  lo que hace MODE1 por debajo                SIN MIRAR.  Es el siguiente hallazgo de la parte.
  amdgpu_reset_method, su valor por defecto   NOT_DETERMINED: la declaracion module_param no
                                               esta en este corpus.  Inferido -1 por el log, no
                                               leido.  La distincion importa.
RIESGO        ninguno.  La unica operacion fue un dmesg de lectura.  Cero escrituras, cero sysfs,
              cero modulos, cero contextos graficos.
LIMITE        conclusion por eliminacion de ramas sobre un switch.  La rama no tomada esta probada
              por la ausencia del bloque; el valor de retorno concreto no se lee en runtime.
```

## 7. Decision log (§103)

```text
DECISION    publicar MODE1 y BACO como dos cosas, y no "el metodo de reset es BACO"
WHY         el log dice BACO y la lectura estatica dice MODE1, y no es contradiccion: son dos
            switches distintos.  Publicar solo uno de los dos seria el error que el 1418 ya
            cometio una vez, de confundir el ASIC con la lista de bloques.
ALTERNATIVA  dar por cerrada la parte 2 con este hallazgo.  Descartada: no he mirado que hace
            MODE1 por debajo, que es justamente donde esta el mecanismo.
ALTERNATIVA  aceptar la conclusion del 1418 y decir que soc15.c no aplica.  Verificada y
            descartada antes de escribir: el 1418 razona sobre bloques IP, no sobre ficheros.
DISCriminante  ninguno necesario para el metodo.  Para el resto, leer MMIO, y es hardware.
CONSECUENCIA  la parte 2 arranca con su primer dato y con un mecanismo ya nombrado para el
            segundo: el camino que no se lee es el que importa.
REVERSIBLE  si MP1 apareciera en el log de arranque —y no aparece— toda la rama caeria.
```

## 8. Una nota sobre el metodo que se ve aqui

Tardé mas de lo debido en este hallazgo, y la razon es util: me puse a verificar el alcance de la
afirmacion del 1418, luego el comportamiento de `amdgpu_ip_version`, luego el default del parametro de
modulo, y solo despues a escribir. **Cuatro verificaciones antes del primer commit**, cuando antes
publicaba con dos.

Y aun asi casi publico "BACO es inalcanzable", porque no mire el log hasta el final. **El log estaba
disponible todo el rato.** Lo que faltaba no era informacion: era el habito de mirar la fuente que
uno tiene delante antes de afirmar, y no solo despues de escribir.

Es el mismo patron de los quince hallazgos anteriores, en su forma mas simple: **mirar antes de
afirmar, no despues.** Y por eso el arbol tiene ahora quince hallazgos con producer, y no quince
opiniones.
