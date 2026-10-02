# 083 · Auditoria de las 110 copias a la RAM del SMC: ninguna truncada, todas clasificadas

WORK_CLASS=READ_ONLY · WRITE_EXECUTION=NONE · MODIFICATIONS 0

## Que se buscaba

Una copia truncada a la RAM del SMC **no da error**. El firmware lee lo que dejo la
copia anterior y el sintoma es voltaje o reloj erratico, mucho despues y sin rastro. Por
eso el unico momento de detectarla es aqui, antes de escribir: comparar la longitud de
cada copia contra el tamano del campo de destino.

Herramienta: `tools/smc_layout.py --copies`.

## Resultado

```
llamadas 110   longitudes resueltas 83   no resueltas 0   en variable de runtime 27

Accounting de las copias, por patron de destino:
    DESTINO_SIN_TIPO         67
    CAMPO_COMPLETO           32
    COLA_DEL_STRUCT           6
    SUBCAMPO_CON_OFFSET       5

TRUNCADAS 0   EXCEDEN 0
```

**Ninguna copia del corpus esta truncada y ninguna excede su destino.** Las 110 estan
en uno de cuatro patrones, y las 110 tienen la longitud o la causa por la que no se
puede medir.

## Los cuatro patrones

Un previo sin catalogar de estos delata 36 "truncadas" que son 36 copias correctas de un
solo campo. La longitud hay que medirla contra la referencia que corresponde:

| patron | que es | ejemplo |
|---|---|---|
| `CAMPO_COMPLETO` | la longitud es exactamente el tamano del campo | 1 byte a `GraphicsVoltageChangeEnable`, que es un `uint8_t`. Es una copia **completa** |
| `COLA_DEL_STRUCT` | `sizeof(T) - offsetof(T, campo)`: sube la struct desde ese campo hasta el final | `polaris10_smumgr.c:2118`, 1776 bytes desde `SystemFlags` |
| `SUBCAMPO_CON_OFFSET` | el destino lleva un offset **ademas** del `offsetof`, asi que escribe dentro del campo | `si_dpm.c:4847` copia 12 bytes, una entrada de 16, en bucle. No puede estar truncada por construccion |
| `DESTINO_SIN_TIPO` | el destino es una base desnuda: `pi->dte_table_start + reg_offset`. No hay `offsetof`, luego no hay campo con el que medir, y la extension la define el contrato con el firmware | 67 de 110 |

## La copia que importa para Polaris12

`polaris10_smumgr.c:2118`, la subida de la tabla DPM:

```
longitud        1776 bytes
expresion       sizeof(SMU74_Discrete_DpmTable) - 3 * sizeof(SMU74_PIDController)
destino         SMU74_Discrete_DpmTable.SystemFlags  (offset 108)
struct          1884 bytes
cola desde 108  1776 bytes
patron          COLA_DEL_STRUCT   ·   trunca: no
```

La longitud coincide exactamente con la cola del struct. Esa coincidencia es una
comprobacion independiente del total y es la que fija 1884 como el valor correcto
(ver `081`).

## Las 27 que dependen del runtime

No es que la herramienta no sepa: es que **no hay nada que medir en el codigo**.

```
(uint32_t)array_size          (uint32_t)level_array_size     u32 byte_count
state_size                    graphics_level_size            data->dpm_table.mclk_table.count
```

La longitud la calcula una variable en tiempo de ejecucion. Se clasifican como
`RUNTIME_MISSING`, que es una categoria distinta de `EVIDENCE_MISSING`. Antes las dos
iban juntas en "no resueltas" y 32 sitios parecian un problema de la herramienta
cuando 27 son una limitacion real del analisis estatico.

Causa declarada: `RUNTIME_MISSING`, cerrable solo con instrumentacion.

## Reparto por fichero

```
kv_dpm.c 27   si_dpm.c 14   polaris10_smumgr.c 13   ci_smumgr.c 11   iceland_smumgr.c 10
fiji_smumgr.c 9   tonga_smumgr.c 9   vegam_smumgr.c 8   si_smc.c 2   smu7_smumgr.c 2
kv_smc.c 1   sislands_smc.h 1   kv_dpm.h 1   smu7_smumgr.h 1   smu7_hwmgr.c 1
```

`kv_dpm.c`, `si_dpm.c` y los `*_smumgr.c` de Tonga, Fiji, CI, Iceland y Vega10 son
**referencia de generacion**, no ruta activa de Polaris12. La ruta activa es
`polaris10_smumgr.c` con 13 llamadas, de las cuales 3 son la tabla DPM, la tabla de
arbitraje de DRAM y la tabla de ventilacion.

## Que habilita y que no

Habilita: un driver propio que construya la tabla DPM sabe que tiene que escrever
**1776 bytes** desde `SystemFlags`, y que la cola del struct es exactamente eso. Antes
esa cifra era 1012 y no lo sabemos.

No habilita: ningun juicio sobre lo que el firmware haga con esos bytes. El contrato de
memoria esta medido; la interpretacion sigue `NOT_IN_CORPUS`.

## Clasificacion

- `SMC_COPY_AUDIT = PROVEN` para 83 copias: longitud y destino medidos.
- `SMC_COPY_RUNTIME = RUNTIME_MISSING` para 27 copias, con el nombre de la variable.
- `SMC_COPY_TRUNCATION = PROVEN_ABSENT` en el corpus: 0 de 110.
- `DESTINO_SIN_TIPO = EVIDENCE_MISSING`: 67 copias cuyo alcance define el firmware, no
  un struct. No se pueden truncar contra una referencia de C.