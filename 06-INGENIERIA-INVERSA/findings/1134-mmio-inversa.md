# 1134 — La transformada que `1132 §6` declaró falta: **decodificación inversa de MMIO**. `0x1348 + 0x2000 = 0x3348 = mmGDS_COMPUTE_MAX_WAVE_ID`, el registro que el driver escribió

```text
AGENCIA=RX550-INVESTIGACION · WORK_CLASS=IMPLEMENTATION + SEMANTIC-CLOSURE
AUTOR=AGENTE-INSTR
WRITE_EXECUTION=NONE · MODIFICATIONS=0 · RUNTIME=NOT_RUN
ESCRITOS_POR_ESTA_ITERACION   tools/mmio.py            (instrumento nuevo)
                              tools/verif.py           (4 medidas)
                              08-ARQUITECTURA/artifacts/R11-MMIO/{salida.txt,
                              edc.json, ibc.json}
                              08-ARQUITECTURA/artifacts/VERIF/linea-base.json
MODIFICADO_NADA_EXISTENTE    pm4_codec.py, pm4_emit.py INTACTOS
CLASSIFICATION=IMPLEMENTATION · MEASUREMENT
GENERADO=2026-10-04 · MEDIDO=EN ESTA HOST
ESTADO=INSTRUMENTO NUEVO, 23 VECTORES, PUERTA EN 42 MEDIDAS
```

## 0 · El resultado, primero

```text
PROBLEMA     el payload de SET_{CONFIG,SH,CONTEXT,UCONFIG}_REG no es un campo:
             es `direccion MMIO - base`. Ninguna tabla de layout lo describe,
             porque hace falta una TRANSFORMADA y no un rango de bits.

INSTRUMENTO  tools/mmio.py   23 vectores, 0,45 s
PUERTA       38 -> 42 medidas, perturbada y restaurada

CASO 1  gfx_v8_0_ring_emit_ib_compute
        0x00001348 + 0x2000 = 0x3348  ->  mmGDS_COMPUTE_MAX_WAVE_ID   UNICO
        el registro que el driver escribio, con su nombre

CASO 2  gfx_v8_0_do_edc_gpr_workarounds
        0x0000020C + 0x2C00 = 0x2E0C  ->  mmCOMPUTE_PGM_LO            UNICO
        x3, los tres SET_SH_REG de la IB
```

## 1 · POR QUÉ NO SE PODÍA ANTES, Y POR QUÉ ESO NO ES UN DETALLE

`1132 §6` dejó escrito que el payload de `SET_SH_REG` no es un campo, sino una
dirección relativa, y que por eso *"no es 'falta el campo X', es 'falta un tipo
de transformada'"*. Ese diagnóstico es el que decide qué instrumento hace
falta, y es la razón de que esto no sea otra entrada en un diccionario.

La operación que falta es:

```text
registro = base_de_ventana + payload
```

y las tres cosas que hay que poder responder antes de applying:

```text
1. QUE base.        El opcode y la base salen del MISMO fichero.
2. QUE valor.       Un solo nombre, o varios, o ninguno. Los tres se declaran.
3. QUE se de NAME.  Una tabla de 83.441 macros que mezcla dos espacios de valores.
```

## 2 · PUNTO 1 · LA BASE, LEÍDA, NO ESCRITA

```text
vid.h:340  #define PACKET3_SET_CONFIG_REG       0x68
vid.h:347  #define PACKET3_SET_SH_REG           0x76
vid.h:343  #define PACKET3_SET_CONTEXT_REG      0x69
vid.h:352  #define PACKET3_SET_UCONFIG_REG      0x79

vid.h:341  #define PACKET3_SET_CONFIG_REG_START 0x00002000
vid.h:348  #define PACKET3_SET_SH_REG_START     0x00002c00
vid.h:344  #define PACKET3_SET_CONTEXT_REG_START 0x000a000
vid.h:353  #define PACKET3_SET_UCONFIG_REG_START 0x000c000
```

Ni el opcode ni la base están escritos en el instrumento. Se leen de `vid.h`, y
del **mismo** fichero, de modo que no pueden contradecirse: si
`PACKET3_SET_SH_REG` desapareciera, la ventana desaparecería con ella y se
deciría, en vez de servir un valor cacheado.

Y la base va a la puerta con su opcode:

```text
mmio.bases   ['SET_CONFIG_REG=0x68/0x2000', 'SET_CONTEXT_REG=0x69/0xA000',
              'SET_SH_REG=0x76/0x2C00',      'SET_UCONFIG_REG=0x79/0xC000']
```

Perturbada a `SET_SH_REG=0x76/0x9999`, la puerta lo dice y sale `rc=1`.

## 3 · PUNTO 2 · LOS TRES ESTADOS, DECLARADOS

```text
UNICO       un solo macro mm*: el nombre es el del registro
MULTIPLE    varios: se dan todos y se dice que el VALOR no los desambigua
NINGUNO     ninguno: se dice, con su absoluto, y NO se inventa un nombre
SIN_LIGAR   el payload depende de un parametro que no se ligo. No es un fallo
            de decodificacion: es una ausencia conocida y rotulada
NO_ES_DIRECCION  el driver escribe un valor, no una direccion menos base
```

Que los seis aparezcan en la salida es la parte que importa. El fallo de esta
clase de instrumento no es responder mal: es **callarse**, y el silencio es
indistinguible de un acierto.

El caso `MULTIPLE` tiene además un límite estructural: con 10.219 valores `mm*`,
el 89,2% tiene un único nombre. El 10,8% restante son los casos en los que el
instrumento tiene que **elegir**, y no elige.

## 4 · PUNTO 3 · LA SEPARACIÓN QUE HACE FALTA, Y POR QUÉ

La tabla de macros del árbol tiene 83.441 entradas. Mezcla **dos espacios de
valores distintos**:

```text
mmX          una DIRECCION de registro
X__MASK      una MASCARA de un campo dentro de un registro
```

Sin separarlos, el mapa inverso es ruido:

```text
0x2000 -> 421 nombres      MC_ARB_AGE_CNTL__RESET_WR_GROUP5_MASK,
                            MC_ARB_RET_CREDITS2__NECKDOWN_CNTR_MONITOR_WR_MASK,
                            ... y 418 mas
```

421 nombres para un valor. Eso no es ambigüedad, es **dos espacios de valores
en el mismo sitio**, y confundirlos produce una salida que parece informational
y no lo es.

Separando por el prefijo `mm` —que es la convención del propio kernel para una
dirección de registro—:

```text
valores con >= 1 nombre mm*     10.219
   con un UNICO nombre             9.117   (89,2%)

0x2000 -> mmGRBM_CNTL                       (unico)
0x2C00 -> mmSPI_SHADER_TBA_LO_PS            (unico)
0xA000 -> mmDB_RENDER_CONTROL                (unico)
0xC000 -> mmCP_EOP_DONE_ADDR_LO             (unico)
0x2E0C -> mmCOMPUTE_PGM_LO                   (unico)
```

La medición va **antes** de construirlo, no después, y está en el `docstring`:
porque la primera versión de la idea era "mapa inverso de la tabla", que es
exactamente la versión que produce 421 nombres.

## 5 · LOS DOS CASOS, SOBRE IB REALES

### 5a · `SET_CONFIG_REG`

```text
gfx_v8_0.c:6119   amdgpu_ring_write(ring, PACKET3(PACKET3_SET_CONFIG_REG, 1));
gfx_v8_0.c:6121   amdgpu_ring_write(ring, mmGDS_COMPUTE_MAX_WAVE_ID
                                        - PACKET3_SET_CONFIG_REG_START);
```

```text
dw  CABECERA  PACKET3_SET_CONFIG_REG  opcode 0x68  base 0x2000   VENTANA
dw  PAYLOAD   PACKET3_SET_CONFIG_REG  0x00001348  0x3348        UNICO
                                                       mmGDS_COMPUTE_MAX_WAVE_ID
dw  PAYLOAD   PACKET3_SET_CONFIG_REG  -           -            SIN_LIGAR
    ring->adev->gds.gds_compute_max_wave_id
```

El segundo payload es un **valor**, no una dirección menos base, y sale
`SIN_LIGAR` con su expresión. Correcto: en `SET_CONFIG_REG` el driver escribe
dirección y valor, y el valor no se decodifica porque no es una dirección.

### 5b · `SET_SH_REG`, tres veces

```text
gfx_v8_0.c:1536   mmCOMPUTE_PGM_LO - PACKET3_SET_SH_REG_START

dw  CABECERA  PACKET3_SET_SH_REG  opcode 0x76  base 0x2C00   VENTANA
dw  PAYLOAD   PACKET3_SET_SH_REG  0x0000020C  0x2E0C        UNICO  mmCOMPUTE_PGM_LO
dw  PAYLOAD   PACKET3_SET_SH_REG  -           -            SIN_LIGAR  lower_32_bits(gpu_addr)
dw  PAYLOAD   PACKET3_SET_SH_REG  -           -            SIN_LIGAR  upper_32_bits(gpu_addr)
```

Tres apariciones del mismo registro en la misma IB, todas `UNICO`. Y los
`vgpr_init_regs[i]` salen `SIN_LIGAR` porque son un array indexado por el bucle:
**no hay forma de ligarlos** y no se finge lo contrario.

## 6 · LO QUE ESTO CIERRA Y LO QUE NO

**Cierra**, con valores:

```text
antes   una IB de inicializacion de shader de GFX8 no se podia decodificar
        en ninguna parte de su payload
ahora   los payloads de direccion se resuelven por nombre, y los que no se
        pueden resolver se declaran por que
```

**No cierra**, y conviene que quede escrito:

**`MULTIPLE` no se ha visto nunca en una ejecución.** Está implementado y
vectorizado con un dict sintético, pero sobre IB reales el 100% de lo resuelto
ha salido `UNICO` o `NINGUNO`. El vector es una prueba de que la rama existe y
elige bien; no es evidencia de que el caso ocurra.

**No se han ligado los parámetros de bucle.** 12 de 15 payloads de las dos IB
salen `SIN_LIGAR`. Los que dependen de `vgpr_init_regs[i]`,
`ring->adev->gds.gds_compute_max_wave_id` o `gpu_addr` no se pueden resolver
estáticamente, y no se han inventado valores.

**El layout de `SET_*_REG` sigue sin existir.** Esto no lo sustituye: el
payload era lo que no se podía leer, y ahora sí, pero la **cabecera** de estos
paquetes sigue sin declarar fields en `DOC_LAYOUTS`, y eso es de otra sesión.

**Nada de esto es evidencia de hardware.** `RUNTIME=NOT_RUN`. La base la
declaran cuatro cabeceras del kernel; que el hardware la respete no lo he
verificado yo. El `UNICO` de `mmCOMPUTE_PGM_LO` dice que la aritmética cuadra
con el driver, no que el hardware la interprete así.

## 7 · MIS ERRORES EN ESTA ITERACIÓN

Todos ocurrieron, y todos los atrapa un vector. Los tres primeros los encontró el
selftest; los dos últimos, el propio uso.

| # | error | cómo salió |
|---|---|---|
| 1 | `formatear` en modo json **imprimía y devolvía `None`** | el vector que leía el JSON se comió un `TypeError` de `json.loads`, y el fallo parecía "el JSON está mal" cuando estaba mal el retorno |
| 2 | vector que contaba 3 literales donde hay **4** (`"300"` también es entero) | `SELFTEST FALLIDO: 2` |
| 3 | vector que buscaba la clave `0` en un dict indexado por `0x100` | `SELFTEST FALLIDO: 2` |
| 4 | `ejecutar` de `verif` usa `argv_extra` **o** `flag`, no los dos | pedí `--estatico` sin `--json` y el fallo salió como `JSON_INVALIDO`, que señala el síntoma equivocado |
| 5 | `_ventanas_de` devolvía el **mapa** y el `for` iteraba sobre las claves | `TypeError: string indices must be integers`, que señalaba a la lista cuando el error estaba en el lado del mapa |

Los dos últimos tienen el mismo fondo: **convertir un tipo en otro en la
frontera y no mirar lo que sale**. Los dos aparecieron en la primera ejecución.

Y uno de proceso, que es el mismo de `1133 §3`: `formatear` no devolvía nada y
no me enteré hasta que lo usó un vector. Un instrumento con un camino principal
correcto y un camino secundario escrito a medias es un instrumento que parece
validado.

## 8 · PROCEDENCIA

```text
tools/mmio.py              instrumento nuevo, 23 vectores, rc=0, 0,45 s
08-ARQUITECTURA/artifacts/R11-MMIO/
    salida.txt             las dos IB con la fuente y las ventanas
    edc.json               IB de gfx_v8_0_do_edc_gpr_workarounds
    ibc.json               IB de gfx_v8_0_ring_emit_ib_compute

puerta   38 -> 42 medidas
         mmio.ventanas     4
         mmio.macros       83441
         mmio.valores_mm   10219
         mmio.bases        los 4 pares opcode/base con su fuente
         perturbada SET_SH_REG=0x76/0x9999   rc=1
         restaurada                            rc=0

otros    layoutcross 79 vectores rc=0
         ibref        39 vectores rc=0
escrituras 0 ficheros de otros agentes
```

## 9 · LO QUE NO ESTÁ HECHO

**`SET_SH_REG_OFFSET` (0x77).** Existe en `vid.h:350` y tiene una ventana
distinta. No lo he incluido: no sé si comparte la base de `SET_SH_REG` o tiene
la suya, y asumirlo sería inventar. Es el siguiente paso natural y está sin
hecho a propósito.

**Los parámetros de bucle.** `vgpr_init_regs[i]`, `sgpr1_init_regs[i]`,
`sgpr2_init_regs[i]` salen de tablas estáticas del driver. Localizar esas tablas
y sintetizar la IB completa con ellas convertiría 12 `SIN_LIGAR` en `UNICO`, y
es trabajo de datos, no de instrumento.

**Los otros tres paquetes de ventana.** Solo hay un `SET_CONFIG_REG` y un
`SET_SH_REG` en las dos funciones que probé; `SET_CONTEXT_REG` y
`SET_UCONFIG_REG` están implementados pero sin caso real que mostrar.

**La integración con `ibref`.** Ahora son dos instrumentos que se pasan un JSON
a mano. La integración de una línea está, y no la he hecho porque, hasta que no
se sepa si `SET_SH_REG_OFFSET` comparte base, unificarlos sería prematuro.