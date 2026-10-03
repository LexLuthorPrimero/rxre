```
CLASE      PROVEN · tablas CALCULADAS, no escritas a mano
FUENTE     corpus linux-7.1.3 · /var/tmp/rx550-incident-pre-reboot-dmesg.txt
GENERADO   report 1.0 · cada tabla lleva el comando que la produce
REGENERAR  una regeneracion sin cambios da un fichero byte-identico
UBICACION  /var/tmp/rx550/  (durable; sobrevivio a 3 reinicios)
```


## 1. Resultado

```
  informes leidos        2
  afirmaciones extraidas 8
    CONFIRMADAS   4
    DIFIEREN      0
    NO RESOLUBLES 2
```

## 2. Afirmaciones retiradas

_Se contrasta el valor **vigente**, no el retirado._

| registro | retirado | vigente | veredicto |
|---|---|---|---|
| regIH_RB_BASE | 0x00081 | 0x00083 | INDIRECTO |

## 3. Confirmadas

| registro | valor | espacio | otros valores |
|---|---|---|---|
| mmGRBM_STATUS2 | 0x02002 | plano | 0x2, 0xda2 |
| mmVM_CONTEXT0_PAGE_TABLE_BASE_ADDR | 0x0054f | plano | - |
| mmVM_CONTEXT8_PAGE_TABLE_BASE_ADDR | 0x0050e | plano | - |
| mmGRBM_STATUS2 | 0x02002 | plano | 0x2, 0xda2 |

_`otros valores`: el mismo símbolo en otro espacio de offset. No es un error._
