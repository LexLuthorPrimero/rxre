# TOOLS-STATUS

<!-- GENERADO POR tools/artifacts.py. NO EDITAR A MANO: la siguiente ejecucion lo sobrescribe. -->

AGENTS.md §AUTOMATIZACIÓN DE VALIDACIÓN exige clasificar cada
herramienta. Y la columna se calcula EJECUTANDO el selftest y mirand
el codigo de salida, no buscando la palabra 'selftest' en el texto:
la primera version hacia eso y daba VALIDATED a 24 de 25
herramientas, incluida esta, que no tiene selftest.

Y A PARTIR DE AQUI HAY UNA TERCERA COSA, que es la que faltaba y la
que hace que el rc signifique algo: **que la herramienta DECLARE
selftest**. Un rc=1 sin selftest no es un test que falla, es una
ejecucion normal que termino con 1. MEDIDO: `integridad.py` no
declara selftest y su rc=1 es `DUPLICADOS 1, CONTAMINADOS 6`, o
sea la auditoria funcionando. Marcarla BROKEN era un falso
veredicto, y era UNO de 62 con rc conocido, no unadera epidemic.

La columna `selftest` dice si el fichero DECLARA el flag. Antes se
sacaba de `detalle`, que nunca esta vacio, asi que ponia `si` en las
70 filas -- incluidas las que la propia tabla marca
`TOOL_UNVALIDATED`. Una columna que no puede decir NO no informa.

- `TOOL_VALIDATED`  el selftest existe y pasa
- `TOOL_BROKEN`      el selftest existe y FALLA
- `TOOL_PARTIAL`     el selftest expira o no se puede ejecutar
- `TOOL_UNVALIDATED` no hay selftest, o no lo soporta

| herramienta | lineas | declara selftest | estado | sha256[:16] |
|---|---|---|---|---|
| `artifacts.py` | 1400 | si | `TOOL_VALIDATED` | `39fd9ab20b3c56aa` |
| `asic_resolver.py` | 950 | si | `TOOL_VALIDATED` | `fb2a8fe32fcf394a` |
| `assert_contract.py` | 555 | si | `TOOL_VALIDATED` | `b203942237ae5ab8` |
| `atom_chain.py` | 650 | si | `TOOL_UNVALIDATED` | `00d4835724a65540` |
| `audit_citations.sh` | 319 | NO | `TOOL_UNVALIDATED` | `dc6f1ac822eb61e0` |
| `cap_census.py` | 388 | si | `TOOL_VALIDATED` | `86d153a17176a1e2` |
| `citas.py` | 288 | si | `TOOL_VALIDATED` | `b0d4393d2212c859` |
| `citations.py` | 1062 | si | `TOOL_VALIDATED` | `6281e397fb19938d` |
| `citeambig.py` | 822 | si | `TOOL_VALIDATED` | `95c2fa42453779fb` |
| `citegen.py` | 509 | si | `TOOL_VALIDATED` | `6b6e35c1800c1d9c` |
| `claim.py` | 758 | si | `TOOL_VALIDATED` | `d580064207cd467e` |
| `claims.py` | 1313 | si | `TOOL_VALIDATED` | `81e30e79120d4415` |
| `constmap.py` | 732 | si | `TOOL_VALIDATED` | `e2149d7cc85081fd` |
| `contradict.py` | 438 | si | `TOOL_VALIDATED` | `43b2bf80fa760dc9` |
| `corroboration.py` | 389 | si | `TOOL_VALIDATED` | `143b28223e3766ae` |
| `count_guard.py` | 604 | si | `TOOL_VALIDATED` | `823bcbf277facbf7` |
| `docscan.py` | 1212 | si | `TOOL_VALIDATED` | `889f990c117e4fc6` |
| `drift.py` | 1074 | si | `TOOL_VALIDATED` | `2fde25b61507624d` |
| `driroute.py` | 288 | si | `TOOL_VALIDATED` | `e8d51e0320b397b0` |
| `drvchain.py` | 627 | si | `TOOL_VALIDATED` | `657905ce2fa0cb17` |
| `dupenum.py` | 430 | si | `TOOL_VALIDATED` | `28ff461733efeee2` |
| `envcheck.py` | 495 | si | `TOOL_VALIDATED` | `be6e1e2a07afce17` |
| `evidence_search.py` | 1129 | si | `TOOL_VALIDATED` | `f364ac1465a51ab8` |
| `fingerprint.py` | 551 | si | `TOOL_VALIDATED` | `aa26c787fb23364c` |
| `flags_inventory.py` | 802 | si | `TOOL_VALIDATED` | `ccd506c561852ba9` |
| `frontier.py` | 910 | si | `TOOL_VALIDATED` | `6069747c7781fe2c` |
| `gccverify.py` | 352 | si | `TOOL_VALIDATED` | `fbdc1fa626333ac2` |
| `govcheck.py` | 883 | si | `TOOL_BROKEN` | `959bf46be6125e98` |
| `hcconsist.py` | 460 | si | `TOOL_VALIDATED` | `61a45f959067e2e6` |
| `hwip.py` | 1013 | si | `TOOL_VALIDATED` | `3f45e975f6f98649` |
| `implgate.py` | 496 | si | `TOOL_VALIDATED` | `75f90b283c785255` |
| `integridad.py` | 555 | si | `TOOL_VALIDATED` | `170590c79ad845c3` |
| `ipsolve.py` | 1221 | si | `TOOL_VALIDATED` | `ca359fdaead32560` |
| `kdeps.c` | 361 | NO | `TOOL_UNVALIDATED` | `78b9de4f2c27465a` |
| `lint.py` | 978 | si | `TOOL_VALIDATED` | `8fe4b7cc0f76e5c9` |
| `mountcheck.py` | 379 | si | `TOOL_VALIDATED` | `564afa2f3d3141c2` |
| `msg_census.py` | 668 | si | `TOOL_VALIDATED` | `f00166daee637707` |
| `mutate.py` | 428 | si | `TOOL_VALIDATED` | `e013ee68e6d2ec3b` |
| `mutscore.py` | 905 | si | `TOOL_VALIDATED` | `884028f47d4684b4` |
| `nextnum.py` | 545 | si | `TOOL_VALIDATED` | `1cca938140b6b817` |
| `oracle.sh` | 414 | si | `TOOL_UNVALIDATED` | `7c84b8254e2a45fc` |
| `pipeline.py` | 671 | si | `TOOL_VALIDATED` | `0ca8f4ab3686dab2` |
| `pm4census.py` | 626 | si | `TOOL_VALIDATED` | `c27984b9dca64d92` |
| `pm4decode.c` | 524 | si | `TOOL_PARTIAL` | `c738eb8356d7e659` |
| `pm4dw.c` | 1459 | NO | `TOOL_UNVALIDATED` | `598f026e36e468b6` |
| `ppt_validate.py` | 823 | si | `TOOL_VALIDATED` | `d3f548b097d89df8` |
| `reftriage.py` | 341 | si | `TOOL_VALIDATED` | `02bff40a119efca3` |
| `reg_census.py` | 369 | si | `TOOL_VALIDATED` | `d9104e563c244f20` |
| `reg_resolve.py` | 540 | si | `TOOL_VALIDATED` | `cc44585983ccea54` |
| `regconst.py` | 454 | si | `TOOL_VALIDATED` | `d96d1cd5014b8ac1` |
| `regtable_audit.py` | 657 | si | `TOOL_VALIDATED` | `094a047084cc182f` |
| `relations.py` | 1014 | si | `TOOL_VALIDATED` | `240506f0e454933a` |
| `round.py` | 944 | si | `TOOL_VALIDATED` | `b4747500e61180eb` |
| `routeaudit.py` | 674 | si | `TOOL_VALIDATED` | `a297885027582a69` |
| `rx550pm4val.c` | 1025 | si | `TOOL_PARTIAL` | `91953a4c660576cf` |
| `rx550ref.c` | 1281 | si | `TOOL_PARTIAL` | `35ebc831db2cb4f1` |
| `smc_copy_scope.py` | 2419 | si | `TOOL_VALIDATED` | `032a0d1c93a4a574` |
| `smc_layout.py` | 1451 | si | `TOOL_VALIDATED` | `4780b325cc1e511b` |
| `snapshot.py` | 1046 | si | `TOOL_VALIDATED` | `37d70894a17592d1` |
| `struct_layout.py` | 1695 | si | `TOOL_VALIDATED` | `7a31e230d1136631` |
| `sysaccess.py` | 345 | si | `TOOL_VALIDATED` | `a2b022cfa26c19c0` |
| `toolcheck.py` | 351 | si | `TOOL_VALIDATED` | `05182e59afd8f486` |
| `toolreg.py` | 704 | si | `TOOL_VALIDATED` | `cecba2cef0be9d36` |
| `trace_path.py` | 780 | si | `TOOL_VALIDATED` | `88da33bec82e7eb9` |
| `treescope.py` | 373 | si | `TOOL_VALIDATED` | `e62e0f366e79b142` |
| `uninit_copy.py` | 831 | si | `TOOL_VALIDATED` | `60ae8d7a5fe666bd` |
| `unreach.py` | 917 | si | `TOOL_VALIDATED` | `5a30c537b0731cc1` |
| `validate_rx550_final.py` | 302 | NO | `TOOL_UNVALIDATED` | `2d7c4c9c8e3e0387` |
| `vmid_map.py` | 879 | si | `TOOL_VALIDATED` | `db23071635a8ace8` |
| `vocabpm4.py` | 492 | si | `TOOL_VALIDATED` | `d325f5b2a951cad5` |
| `which_hw.py` | 693 | si | `TOOL_VALIDATED` | `355e3da03b0db19b` |
| `xref.py` | 586 | si | `TOOL_VALIDATED` | `4205fbc42e9e2abf` |

**Total**: 72 herramientas, 6 `TOOL_UNVALIDATED`, 1 `TOOL_BROKEN`, 4 sin selftest declarado.

AGENTS.md: *`TOOL_UNVALIDATED` no puede cerrar una afirmación crítica*.
Las que lo estan no pueden ser el unico sustento de un hallazgo.
