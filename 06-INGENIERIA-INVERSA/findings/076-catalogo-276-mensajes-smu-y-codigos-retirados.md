# 076 · Los 276 mensajes del firmware SMU para Polaris12, y 297 códigos que ya no existen

```
CLASSIFICATION=DOCUMENTATION · TRACK=STATIC · CORPUS=RESEARCH/working/linux-7.1.3
HARDWARE_SCOPE=HOST-C/RX550/0000:01:00.0 · WORK_CLASS=READ_ONLY/EVIDENCE
WRITE_EXECUTION=NONE · MODIFICATIONS=0 · RUNTIME=NOT_RUN · GPU INTACTA
```

## Qué resuelve

`070` cerró el contrato host↔SMC y dejó abierto *"qué mensajes existen"*. Eso es
**dato generado**: 276 entradas que una máquina debe extraer, no que una persona
debe transcribir. Y no son un catálogo plano — la numeración tiene estructura.

## La estructura de la numeración, que es el dato que importa

```
  mensajes definidos            276
  rango                         0x0010 .. 0x0802
  páginas de 0x100 con mensajes   7
  páginas VACÍAS dentro del rango  2
  códigos ausentes dentro de página  297
```

**Los códigos se asignan por páginas de 0x100, no de uno en uno.** Los saltos:

```
  0x0089 -> 0x00f8      0x019d -> 0x0200      0x0282 -> 0x0300
  0x0317 -> 0x0400      0x0415 -> 0x0600      0x0601 -> 0x0800
```

Eso tiene una consecuencia práctica directa. **Un driver propio que asuma
numeración consecutiva escribe en el mensaje equivocado.** Entre `0x0089` y
`0x00f8` hay 110 códigos que **no existen**: escribir a `0x00a0` no llega a
ningún mensaje, y no hay error que lo indique.

La primera versión de la herramienta reportaba **1759 códigos ausentes** sobre el
rango global. Era un número sin significado: mezclaba los 297 códigos retirados
dentro de una página con las páginas enteras sin asignar. Corregido, y la
distinción se reporta explícita:

- **hueco dentro de una página** = un código que se retiró. Escribir ahí no
  alcanza nada.
- **página vacía** = espacio sin asignar. Escribir ahí tampoco, pero no es un
  mensaje retirado: es un bloque reservado.

## El hallazgo sobre generación que se repite por tercera vez

```
  mensajes referenciados por el host en TODO el árbol   832
  de los que están en smu7_ppsmc.h (Polaris12)            276
  mensajes usados que NO son de esta generación          556
```

Los 556 que faltan **sí existen**, en `cz_ppsmc.h`, `vega10_ppsmc.h` y
`vega20_ppsmc.h`, que conviven en el mismo árbol. Ejemplos: `PPSMC_MSG_AllowGfxOff`,
`PPSMC_MSG_AllowIHHostInterrupt`, `PPSMC_MSG_ActiveProcessNotify`.

Es la **tercera vez** que aparece la misma clase de error:

| | dónde |
|---|---|
| `065` | 7 registros con dirección distinta entre familias GMC/MMHUB |
| `075` | `AMDGPU_PTE_PRT_FLAG` devuelve 0 porque es GFX12+ |
| `076` | 556 mensajes del host que no son de Polaris12 |

**Un nombre presente en el árbol de amdgpu no es una cosa de esta GPU.** Las tres
veces la clave estaba en una condición de generación escondida, y las tres
veces el resultado era plausible y erróneo. Eso merece una herramienta propia, no
sólo un recordatorio: el filtro correcto es "¿esta generación lo usa?".

## Lo que la herramienta NO dice

```
  enviados con parametro        0
```

Cero. Y eso **no significa** que ningún mensaje lleve parámetro. El detector
busca `smu7_send_msg_to_smc_with_parameter(...)` y no encuentra ninguno en esa
forma, pero `070` ya probó que el parámetro viaja en `mmSMC_MSG_ARG_0` (`0xa4`) y
que `smu7_send_msg_to_smc_offset` lo usa con `0x20000`. **El detector está mal
construido para esa llamada**, y lo digo en vez de reportar un cero que parece un
resultado.

Corregirlo requiere seguir el puntero de función, no el nombre literal: la
función real se alcanza por `vm_pte_funcs` / `smu7_send_msg_to_smc`, y el nombre
aparece en un puntero. Es trabajo pendiente, y es un fallo conocido, no un
resultado.

Y el límite grande, que la herramienta declara en su última línea:

> Esto cataloga la **interfaz**, no la **semántica**. Que exista un mensaje no dice
> qué hace: eso vive en el firmware, que es un blob binario. Y "referenciado por
> el host" es textual, no verificado — un mensaje puede estar en el código y ser
> inalcanzable en esta ruta.

## Familias de mensajes

Los 276 se agrupan por prefijo, y la distribución dice qué controla esta GPU:

```
  DPM 11 · MCLKDPM 9 · PCIeDPM 6 · UVDDPM 5 · VCEDPM 5 · ACPDPM 5
  SAMUDPM 5 · NBDPM 5 · API 5 · CollectCAC 4 · PM 4 · PCIE 4 · SCLKDPM 4
  LCLKDPM 4 · MASTER 4 · CAC 4 · PG 3 · InferredStateSweep 2
```

**DPM domina**: DPM, más los seis grupos de dominio (MC/LC/PCIE/UVD/VCE/ACP/SMU/NB),
más `PG` (power gating) y `MASTER`. Es el perfil esperado de un ASIC donde, como
estableció `070` y `046`, el host no escribe los relojes: los **pide**. Lo que
controla son transiciones de estado y límites por dominio, no valores de reloj.

`InferredStateSweep` es el único con nombre de "inferencia", y es el que más
interesa para un driver propio: un barrido de estados inferidos es exactamente el
punto donde el firmware tiene información que el host no.

## Procedencia

- `CORPUS` — `pm/powerplay/inc/{smu7,cz,vega10,vega20}_ppsmc.h`,
  `pm/powerplay/smumgr/`.
- Herramienta: `smumsg.py`, 18 casos de self-test.
- Encadenada con `070` (el canal y el parámetro en `0xa4`) y `046` (tablas de
  voltaje por dominio en vez de curvas).
- Sin `RUNTIME`, sin lectura de la GPU, sin escrituras.
- No se editó `OPEN-FRONTIERS.md`: es de otra sesión (`COORDINACION.md:184`).