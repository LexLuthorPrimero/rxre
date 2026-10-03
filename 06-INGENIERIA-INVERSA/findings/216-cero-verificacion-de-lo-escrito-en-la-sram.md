# 216  El driver escribe 6 tablas en la SRAM del SMC y no relee ninguna: por eso todos los fallos anteriores son mudos

WORK_CLASS=READ_ONLY · WRITE_EXECUTION=NONE · MODIFICATIONS 0

> **DEPENDENCIA ACTUALIZADA por `113`:** una de las siete filas de la tabla, la de `104`,
> queda **REFUTADA**. `dpm_table_start` es la base literal de la tabla y los once usos de
> `dpm_table_start + offsetof(...)` son correctos. El recuento real es de **seis** fallos
> mudos, no siete. La tesis central de este documento -- **cero lecturas de verificacion en
> 17 escrituras** -- no se ve afectada: es una afirmacion independiente, medida sobre el
> codigo, y sigue en pie.

## El hecho, medido

En la ruta de Polaris12 hay **12 llamadas a `smu7_read_smc_sram_dword`**, y las **12 son
lecturas de la cabecera del firmware o de la tabla de PMFuses**. **Ninguna relee algo que el
host haya escrito antes.**

```
:131   lee la cabecera  (dentro de polaris10_setup_graphics_level_structure)
:315   lee la cabecera  (fallback, comentario de DummyBackEnd)
:527   lee PmFuses      (TdcWaterfallCtl, dentro de polaris10_populate_dw8)
:611   lee la cabecera  (PmFuseTable)
:1868  lee la cabecera  (AvfsMeanNSigma)
:1878  lee la cabecera  (AvfsSclkOffsetTable)
:2500  lee la cabecera  (DpmTable)
:2510  lee la cabecera  (SoftRegisters)
:2522  lee la cabecera  (mcRegisterTable)
:2530  lee la cabecera  (FanTable)
:2540  lee la cabecera  (mcArbDramTimingTable)
:2550  lee la cabecera  (Version)
```

Y del lado de las escrituras, `smc_copy_scope` encuentra **13 copias por
`smu7_copy_bytes_to_smc`** mas **4 escrituras registro a registro** a la SRAM del SMC.

**Ninguna de las 17 tiene una lectura de confirmacion.** Es decir: el host escribe 1776
bytes de la tabla DPM, 448 de graficos, 96 de memoria, 384 de arbitraje, 84 de PMFuses, 36
de ventilacion, un `AllowMvddSwitch`, dos parches de nivel de arranque y un
`LowSclkInterruptThreshold`, y **no comprueba ninguno**.

La comprobacion que si existe, en `smu7_copy_bytes_to_smc`, es de **rango y alineacion de
la direccion** (`smu7_smumgr.c:58-59`), no del **contenido**. Como `100` documento,
`limit` es un parametro libre (`smu7_program_jump_on_start` pasa `5` como limite) y la
direccion `0` pasa los dos checks.

## Por que esto no es un detalle: convierte el resto en mudo

Todos los hallazgos de las ultimas tandas son, en el fondo, **el mismo defecto**:

| hallazgo | que falla | como se detecta upstream |
|---|---|---|
| `099` | el retorno del setup DPM se ignora; contadores a 8 y 4 con valores nulos | **no se detecta**: el codigo sigue y sube la tabla |
| `100` | el limite es el doble de la SMC declarada; la direccion 0 pasa los checks | **no se detecta**: el check pasa |
| `101` | un `return` temprano deja el selector de rango del PLL a cero | **no se detecta**: `Fcw_int` sale bien formado |
| `102` | 7 campos de PMFuses a cero | **no se detecta**: cero es un valor valido |
| `103`/`107` | el parche escribe en `Smio[5]` en vez de `UvdBootLevel` | **no se detecta**: el byte se escribe bien |
| ~~`104`~~ | ~~once usos con el desfase de 108~~ | **REFUTADO en `113`: no hay defecto** |
| `110` | `AllowMvddSwitch` se escribe a una direccion que puede no ser la correcta | **no se detecta**: la escritura se pierde sin aviso |

**En los seis que quedan (los siete de la tabla, sin `104`), el mecanismo es el mismo: el host cree que ha hecho algo y el
firmware recibe otra cosa, y no hay ninguna lectura que lo contradiga.**

Y hay un detalle tecnico que lo hace inevitable: **una escritura followed de lectura
seguiria sin detectar casi nada**. `smu7_read_smc_sram_dword` devuelve lo que hay, y si el
host escribio donde creia, leer devuelve lo que escribio: la comprobacion confirma la
escritura equivocada. **Verificar la escritura no sirve: hay que verificar el
CONTENIDO.**

## Y eso tiene una consecuencia sobre lo que he llamado PROVEN

Varios hallazgos los he marcado `PROVEN` por el hecho de que **el codigo hace X**. Eso es
correcto y no lo cambio. Pero hay una distincion que debo hacer explicita, porque se me
ha ido mezclando:

- **PROVEN que el codigo hace X**: verificado leyendo las lineas. Sostiene.
- **PROVEN que el firmware recibe Y**: **no lo he verificado en ninguno de los seis que quedan
  casos.** Depende de lo que haga el firmware con esos bytes, que es `NOT_IN_CORPUS`.

O sea: he dicho "el firmware recibe otra cosa" a la conclusion de "el host escribe otra
cosa". **Son dos afirmaciones distintas**, y la segunda tiene un eslabon que no puedo
cerrar: que el firmware use ese campo para lo que creo.

Donde el eslabon es mecanico, si: la copia grande de `104` mueve bytes que el host copia a la SRAM, y la
copia es integra. `110` concede un permiso a una direccion que puede ser la tabla. Eso no
depende del firmware, depende de donde Caen los bytes.

Donde el eslabon es semantico: `103` escribe un nivel de arranque en `Smio[5]`. Si el
firmware lee `Smio[5]`, hay un problema; si no lo lee, hay un byte raro. `SEMANTIC_MISSING`.

`107` ya lo decia, pero lo que anadio aqui es que **es un elzon que aplica a los seis que quedan**,
no solo a ese.

## La accion que esto habilita

Una lectura de confirmacion por escritura es lo que convierte todo esto de "mudo" a
"detectable", y es barato en el caso de Polaris12: **la SMC son 128 KiB y la tabla DPM son
1884 bytes.** Leer 1884 bytes y compararlos con lo que el host creo que escribio es un
coste de 471 lecturas de 4 bytes, una vez, en el arranque.

Y no hace falta la placa para **disenarlo**: el mecanismo de comparacion es
`memcmp(&tabla_local, lo_que_se_leyo, 1776)`, y el resultado esperado se conoce sin
hardware porque la tabla local es lo que el host quiere que haya.

Lo que **si** necesita la placa es ejecutar la comparacion, y ver que 1776 de 1776
coinciden en el caso bueno y 0 coinciden en el caso del desfase de 108. Ese es el
discriminante, y es de los que `108` describe: el mecanismo esta cerrado, el impacto
depende de la disposicion del firmware.

## Clasificacion

- `SMC_ZERO_VERIFICATION_READS = PROVEN`: 12 llamadas a
  `smu7_read_smc_sram_dword`, y las 12 leen la cabecera del firmware o PMFuses. Ninguna
  relee una escritura previa del host.
- `SMC_SEVENTEEN_WRITES_ZERO_CONFIRMATIONS = PROVEN_DERIVED`: 13 copias por
  `smu7_copy_bytes_to_smc` (contadas por `smc_copy_scope` con offsets de gcc) mas 4
  escrituras registro a registro, sin ninguna lectura de confirmacion.
- `SMC_COPY_CHECK_IS_ADDRESS_ONLY = PROVEN`: `smu7_smumgr.c:58-59` comprueba alineacion y
  rango, nunca contenido.
- `SMC_READBACK_WOULD_CONFIRM_THE_MISTAKE = PROVEN_DERIVED`: releer lo que se escribio
  devuelve lo que se escribio, termasuk el error. **Verificar no sirve: hay que verificar
  el contenido esperado.**
- `FINDING_SEVEN_CLAIMS_ABOUT_HOST_WRITES_NOT_FIRMWARE_READS = PROVEN_DERIVED`: en los
  siete casos (`099`, `100`, `101`, `102`, `103`/`107`, `104`, `110`), de los que `104` queda REFUTADO lo `PROVEN` es que el
  host escribe X; que el firmware lea ese campo y lo interprete como Y es `NOT_IN_CORPUS`
  o `SEMANTIC_MISSING`.
- `SMC_READBACK_IS_CHEAP_HERE = PROVEN_DERIVED`: 1884 bytes = 471 lecturas de 4 bytes,
  una vez, en un arrancar. La SMC son 128 KiB (`POLARIS10_SMC_SIZE`).

## Lo que esto obliga a hacer en un driver propio

Es la conclusion de toda la sesion, y no es un findings mas: **un driver propio tiene que
verificar lo que escribe en la SRAM del firmware.**

Concretamente, al terminar la construccion de la tabla y **antes** de arrancar el
microcodigo:

1. Relee la zona escrita.
2. Compara **byte a byte contra lo que el host quiso escribir**, no contra lo que el host
   escribio.
3. Si no coincide, **no arrancar el firmware**, y volcar la diferencia.

Eso convierte los seis fallos mudos que quedan en seis fallos ruidosos, y ademas es lo que
permitiria discriminar en la placa la pregunta de `108`: si los 1776 bytes que el host
cree escribir aparecen donde el host cree, el hueco de 108 no existe; si aparecen
desplazados, existe.

**Y el orden importa, por el motivo de `110`:** la verificacion va **despues de todas las
escrituras y antes de arrancar el firmware**. Si va antes, no verifica nada.
