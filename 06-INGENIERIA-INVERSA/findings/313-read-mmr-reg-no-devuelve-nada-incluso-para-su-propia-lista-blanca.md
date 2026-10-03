# 313 · `AMDGPU_INFO_READ_MMR_REG` no devuelve nada, ni siquiera para los 19 registros de su propia lista blanca

```
PENDIENTE=313-1 | HALLAZGO=313-read-mmr-reg-no-devuelve-nada-incluso-para-su-propia-lista-blanca.md
             | ESTADO=PARTIAL
             | NECESITA=/dev/dri/renderD129
             | ALCANZABLE_SIN_ROOT=si
```

## Que se midio

`924` cerro que `READ_MMR_REG` es MMIO con lista blanca, y que esa lista no
tiene registros de MC ni de VM. Eso acota los 123 huecos clasificados
`UN_REGISTRO` de forma util.

La lista de `soc21.c:287-307` tiene **19 entradas**. Se probaron las 19 con sus
offsets de `gc_11_0_0_offset.h` mas dos controles negativos:

```
  regGRBM_STATUS          0x0da4   ERRNO Bad address
  regGRBM_STATUS2         0x0da2   ERRNO Bad address
  regGRBM_STATUS_SE0..SE3 0x0da5.. ERRNO Bad address
  regSDMA0_STATUS_REG     0x0025   ERRNO Bad address
  regSDMA1_STATUS_REG     0x0625   ERRNO Bad address
  regCP_STAT              0x0f40   ERRNO Bad address
  regCP_STALLED_STAT1..3  0x0f3c.. ERRNO Bad address
  regCP_CPF_*             0x0e27.. ERRNO Bad address
  regCP_CPC_*             0x0e24.. ERRNO Bad address
  regGB_ADDR_CONFIG       0x13de   ERRNO Bad address
  NO-listado offset 0x0000        ERRNO Bad address
  NO-listado offset 0x0013        ERRNO Bad address

  leidos 0 de 21
```

## Lo que SI queda cerrado

**El ioctl llega al driver.** `EFAULT` no es `EACCES` ni `EINVAL`: el
`case AMDGPU_INFO_READ_MMR_REG` se ejecuto, llamo a
`amdgpu_asic_read_register()`, y ese devolvio error, que `amdgpu_kms.c:915-918`
convierte en `-EFAULT`.

Y el nodo es el correcto: el hallazgo 312 midio que `renderD129` responde 15 de
19 en el resto de la superficie. Esta llamada no es un problema de permisos.

## La hipotesis que NO se sostiene

La explicacion obvia es que `adev->reg_offset[hwip][inst][seg]` no se inicializa
para Polaris12, y entonces `soc21_read_register` (`soc21.c:348`) hace
`if (!adev->reg_offset[...]) continue;` en todas las entradas, se agotan, y
devuelve `-EINVAL`.

**Y es falsa, o al menos no explica el dato.** Si la tabla estuviera a cero, la
comparacion seria `reg_offset != (0 + en->reg_offset)`, o sea que pedir
exactamente `0x0da4` **empataria** con `regGRBM_STATUS`. No empato.

Con la informacion de la UAPI y del codigo de esta maquina, hay tres
explicaciones que siguen abiertas y que este experimento **no** separa:

1. La tabla `reg_offset` tiene valores distintos de los que asumo, y la suma no
   da ninguno de los 19 offsets.
2. La ruta de codigo de esta placa no es `soc21_read_register`, sino otra
   `read_register` de la tabla `asic_funcs`.
3. El filtro rechaza antes, por el `count > 128` o por el `se_num`/`sh_num` mal
   formados, y `EFAULT` llega por otra via.

Lo que **no** se puede decir es "la lista blanca de Polaris12 esta vacia" ni
"estos registros no existen". Solo: por esta via, en esta maquina, con estos
offsets, no se lee ninguno.

## Por que esto importa mas de lo que parece

Los 123 huecos `UN_REGISTRO` dicen "se cierra leyendo un registro". Este
experimento dice que **la unica via de lectura de registros desde userspace sin
root, en esta placa, no devuelve nada**. O sea que la via que el clasificador
propone para cerrar 123 huecos no esta disponible.

Eso no los hace irresolubles: un driver propio los leeria. Pero cambia el
costo: no son "una lectura", que es lo que sugiere la etiqueta, son "un driver
que todavia no existe".

## RIESGO ASUMIDO, y era MAYOR DE LO QUE PENSE

`soc21_read_register` no es una lectura pasiva: `amdgpu_kms.c:909` hace
`amdgpu_gfx_off_ctrl(adev, false)` antes y `:921` lo vuelve a encender despues.
Apagar y encender el control del motor GFX 21 veces es una manipulacion real del
estado del motor, aunque el driver la restaure.

Se eligieron 21 llamadas y no un barrido por eso, y por lo mismo **no se ha
barrido**. Un barrido de la lista blanca buscada en bruto seria del orden de
10^5 llamadas de apagado/encendido, y eso ya no es una lectura.

El display de esta maquina va por la Intel (hallazgo 312): la sesion no se
caeria. El riesgo es sobre el motor GFX, no sobre la pantalla.

## Que NO se ha hecho

- No se ha barrido el rango de offsets. Ver arriba: no es una lectura.
- No se ha tocado `reg_offset` ni el driver. Es lectura de codigo, no
  ejecucion.
- No se afirma nada sobre la semantica de `GB_ADDR_CONFIG`. Es el registro de
  la base de la tabla de paginas, que es central para el trabajo, y aqui no se
  pudo leer ni una vez.

## Como reproducirlo

```
gcc -O2 -o amdmmr 08-ARQUITECTURA/tools/amdmmr.c
./amdmmr /dev/dri/renderD129
```

El programa lleva dos controles negativos por si la lista blanca devolviera
algo: sin ellos, "leidos 19 de 19" seria indistinguible de "el filtro no
existe".
