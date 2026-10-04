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
| `tools/artifacts.py` | 1511 | si | `TOOL_VALIDATED` | `0c08da6bf4bfca7a` |
| `tools/asic_resolver.py` | 950 | si | `TOOL_VALIDATED` | `fb2a8fe32fcf394a` |
| `tools/assert_contract.py` | 555 | si | `TOOL_VALIDATED` | `b203942237ae5ab8` |
| `tools/atom_chain.py` | 650 | si | `TOOL_UNVALIDATED` | `00d4835724a65540` |
| `tools/audit_citations.sh` | 319 | NO | `TOOL_UNVALIDATED` | `dc6f1ac822eb61e0` |
| `tools/cap_census.py` | 388 | si | `TOOL_VALIDATED` | `86d153a17176a1e2` |
| `tools/check_num_unico.py` | 1186 | si | `TOOL_VALIDATED` | `22a858f6e951e6d9` |
| `tools/citas.py` | 288 | si | `TOOL_VALIDATED` | `b0d4393d2212c859` |
| `tools/citations.py` | 1062 | si | `TOOL_VALIDATED` | `6281e397fb19938d` |
| `tools/citeambig.py` | 822 | si | `TOOL_VALIDATED` | `95c2fa42453779fb` |
| `tools/citegen.py` | 509 | si | `TOOL_VALIDATED` | `6b6e35c1800c1d9c` |
| `tools/claim.py` | 758 | si | `TOOL_VALIDATED` | `d580064207cd467e` |
| `tools/claims.py` | 1366 | si | `TOOL_VALIDATED` | `f11e0d40598f65e7` |
| `tools/constmap.py` | 732 | si | `TOOL_VALIDATED` | `e2149d7cc85081fd` |
| `tools/contradict.py` | 438 | si | `TOOL_VALIDATED` | `43b2bf80fa760dc9` |
| `tools/corroboration.py` | 389 | si | `TOOL_VALIDATED` | `143b28223e3766ae` |
| `tools/count_guard.py` | 604 | si | `TOOL_VALIDATED` | `823bcbf277facbf7` |
| `tools/docscan.py` | 1212 | si | `TOOL_VALIDATED` | `889f990c117e4fc6` |
| `tools/drift.py` | 1074 | si | `TOOL_VALIDATED` | `2fde25b61507624d` |
| `tools/driroute.py` | 288 | si | `TOOL_VALIDATED` | `e8d51e0320b397b0` |
| `tools/drvchain.py` | 627 | si | `TOOL_VALIDATED` | `657905ce2fa0cb17` |
| `tools/dupenum.py` | 586 | si | `TOOL_VALIDATED` | `67181553b9d31cee` |
| `tools/envcheck.py` | 495 | si | `TOOL_VALIDATED` | `be6e1e2a07afce17` |
| `tools/evidence_search.py` | 1129 | si | `TOOL_VALIDATED` | `f364ac1465a51ab8` |
| `tools/fingerprint.py` | 551 | si | `TOOL_VALIDATED` | `aa26c787fb23364c` |
| `tools/flags_inventory.py` | 802 | si | `TOOL_VALIDATED` | `ccd506c561852ba9` |
| `tools/frontier.py` | 925 | si | `TOOL_VALIDATED` | `b69b540b521466e1` |
| `tools/gccverify.py` | 352 | si | `TOOL_VALIDATED` | `fbdc1fa626333ac2` |
| `tools/git_sano.py` | 319 | si | `TOOL_VALIDATED` | `9fb6868eb21c4daa` |
| `tools/govcheck.py` | 883 | si | `TOOL_VALIDATED` | `959bf46be6125e98` |
| `tools/gttlimit.py` | 183 | NO | `TOOL_UNVALIDATED` | `e4f23a671d9332be` |
| `tools/hcconsist.py` | 460 | si | `TOOL_VALIDATED` | `61a45f959067e2e6` |
| `tools/hwip.py` | 1013 | si | `TOOL_VALIDATED` | `3f45e975f6f98649` |
| `tools/implgate.py` | 496 | si | `TOOL_BROKEN` | `75f90b283c785255` |
| `tools/integridad.py` | 555 | si | `TOOL_VALIDATED` | `170590c79ad845c3` |
| `tools/ipsolve.py` | 1221 | si | `TOOL_VALIDATED` | `ca359fdaead32560` |
| `tools/kdeps.c` | 361 | NO | `TOOL_UNVALIDATED` | `78b9de4f2c27465a` |
| `tools/lint.py` | 978 | si | `TOOL_VALIDATED` | `8fe4b7cc0f76e5c9` |
| `tools/mountcheck.py` | 379 | si | `TOOL_VALIDATED` | `564afa2f3d3141c2` |
| `tools/msg_census.py` | 668 | si | `TOOL_VALIDATED` | `f00166daee637707` |
| `tools/mutate.py` | 428 | si | `TOOL_VALIDATED` | `e013ee68e6d2ec3b` |
| `tools/mutscore.py` | 905 | si | `TOOL_VALIDATED` | `884028f47d4684b4` |
| `tools/nextnum.py` | 792 | si | `TOOL_VALIDATED` | `095cc6e3749d3959` |
| `tools/oracle.sh` | 414 | si | `TOOL_UNVALIDATED` | `7c84b8254e2a45fc` |
| `tools/oracle_drift.py` | 536 | si | `TOOL_PARTIAL` | `ef36dbdd598fa220` |
| `tools/pipeline.py` | 671 | si | `TOOL_VALIDATED` | `0ca8f4ab3686dab2` |
| `tools/pm4census.py` | 626 | si | `TOOL_VALIDATED` | `c27984b9dca64d92` |
| `tools/pm4decode.c` | 524 | si | `TOOL_PARTIAL` | `c738eb8356d7e659` |
| `tools/pm4dw.c` | 1459 | NO | `TOOL_UNVALIDATED` | `598f026e36e468b6` |
| `tools/ppt_validate.py` | 823 | si | `TOOL_VALIDATED` | `d3f548b097d89df8` |
| `tools/reftriage.py` | 341 | si | `TOOL_VALIDATED` | `02bff40a119efca3` |
| `tools/reg_census.py` | 369 | si | `TOOL_VALIDATED` | `d9104e563c244f20` |
| `tools/reg_resolve.py` | 540 | si | `TOOL_VALIDATED` | `cc44585983ccea54` |
| `tools/regconst.py` | 454 | si | `TOOL_VALIDATED` | `d96d1cd5014b8ac1` |
| `tools/regtable_audit.py` | 657 | si | `TOOL_VALIDATED` | `094a047084cc182f` |
| `tools/relations.py` | 1014 | si | `TOOL_VALIDATED` | `240506f0e454933a` |
| `tools/round.py` | 944 | si | `TOOL_VALIDATED` | `b4747500e61180eb` |
| `tools/routeaudit.py` | 674 | si | `TOOL_VALIDATED` | `a297885027582a69` |
| `tools/rx550pm4val.c` | 1025 | si | `TOOL_PARTIAL` | `91953a4c660576cf` |
| `tools/rx550ref.c` | 1281 | si | `TOOL_PARTIAL` | `35ebc831db2cb4f1` |
| `tools/smc_copy_scope.py` | 2419 | si | `TOOL_VALIDATED` | `032a0d1c93a4a574` |
| `tools/smc_layout.py` | 1451 | si | `TOOL_VALIDATED` | `4780b325cc1e511b` |
| `tools/snapshot.py` | 1046 | si | `TOOL_VALIDATED` | `37d70894a17592d1` |
| `tools/struct_layout.py` | 1695 | si | `TOOL_VALIDATED` | `7a31e230d1136631` |
| `tools/sysaccess.py` | 345 | si | `TOOL_VALIDATED` | `a2b022cfa26c19c0` |
| `tools/toolcheck.py` | 351 | si | `TOOL_VALIDATED` | `05182e59afd8f486` |
| `tools/toolreg.py` | 970 | si | `TOOL_VALIDATED` | `de205cc15e4c5a2d` |
| `tools/trace_path.py` | 780 | si | `TOOL_VALIDATED` | `88da33bec82e7eb9` |
| `tools/treescope.py` | 373 | si | `TOOL_VALIDATED` | `e62e0f366e79b142` |
| `tools/uninit_copy.py` | 831 | si | `TOOL_VALIDATED` | `60ae8d7a5fe666bd` |
| `tools/unreach.py` | 917 | si | `TOOL_VALIDATED` | `5a30c537b0731cc1` |
| `tools/validate_rx550_final.py` | 302 | NO | `TOOL_UNVALIDATED` | `2d7c4c9c8e3e0387` |
| `tools/vmid_map.py` | 879 | si | `TOOL_VALIDATED` | `db23071635a8ace8` |
| `tools/vocabpm4.py` | 492 | si | `TOOL_VALIDATED` | `d325f5b2a951cad5` |
| `tools/which_hw.py` | 693 | si | `TOOL_VALIDATED` | `355e3da03b0db19b` |
| `tools/xref.py` | 586 | si | `TOOL_VALIDATED` | `4205fbc42e9e2abf` |
| `08-ARQUITECTURA/tools/_selftest_help_no_alloc.py` | 168 | si | `TOOL_PARTIAL` | `11d2c173cdbbc24b` |
| `08-ARQUITECTURA/tools/_selftest_num_collision.py` | 194 | si | `TOOL_PARTIAL` | `73c901994662b895` |
| `08-ARQUITECTURA/tools/_selftest_runtime_obs.py` | 505 | si | `TOOL_PARTIAL` | `64723084d61794b5` |
| `08-ARQUITECTURA/tools/_selftest_stale_gap.py` | 639 | si | `TOOL_PARTIAL` | `113ab5d23e21658c` |
| `08-ARQUITECTURA/tools/ambig_citas.py` | 395 | si | `TOOL_PARTIAL` | `0f53dd595acb241f` |
| `08-ARQUITECTURA/tools/amdinfo.c` | 194 | NO | `TOOL_UNVALIDATED` | `90a06270c9502b31` |
| `08-ARQUITECTURA/tools/amdioread.py` | 321 | si | `TOOL_PARTIAL` | `29ea6177a4e12dac` |
| `08-ARQUITECTURA/tools/amdmmr.c` | 96 | NO | `TOOL_UNVALIDATED` | `8c6abcefab6e4f40` |
| `08-ARQUITECTURA/tools/aperture.py` | 325 | si | `TOOL_PARTIAL` | `e2b6f18d17b94299` |
| `08-ARQUITECTURA/tools/asic_table.py` | 341 | si | `TOOL_PARTIAL` | `88d54ab439b91f73` |
| `08-ARQUITECTURA/tools/bench.py` | 1622 | si | `TOOL_PARTIAL` | `4fb5b397f9eb9a39` |
| `08-ARQUITECTURA/tools/binfacts.py` | 333 | NO | `TOOL_UNVALIDATED` | `ebc70a447124778b` |
| `08-ARQUITECTURA/tools/causal.py` | 409 | si | `TOOL_PARTIAL` | `75f9292858a584f5` |
| `08-ARQUITECTURA/tools/causal_chain.py` | 330 | NO | `TOOL_UNVALIDATED` | `bf5fd75d7de1a9b2` |
| `08-ARQUITECTURA/tools/causal_map.py` | 466 | NO | `TOOL_UNVALIDATED` | `28ef84926ece22b4` |
| `08-ARQUITECTURA/tools/check_chain.py` | 471 | si | `TOOL_PARTIAL` | `506bf4fa6a87405c` |
| `08-ARQUITECTURA/tools/cite_registry.py` | 467 | si | `TOOL_PARTIAL` | `75ec278754d9f22a` |
| `08-ARQUITECTURA/tools/citecheck.py` | 580 | si | `TOOL_PARTIAL` | `2d196491b528bd6a` |
| `08-ARQUITECTURA/tools/commitmsg_lint.py` | 195 | si | `TOOL_PARTIAL` | `6ea22ec75d352ab0` |
| `08-ARQUITECTURA/tools/contract_exec.py` | 641 | si | `TOOL_PARTIAL` | `f6cf05a2a30f698c` |
| `08-ARQUITECTURA/tools/contract_filter.py` | 256 | si | `TOOL_PARTIAL` | `a6db25d3eb3d2580` |
| `08-ARQUITECTURA/tools/contradict.py` | 402 | si | `TOOL_PARTIAL` | `6d31aa3206c2a2b5` |
| `08-ARQUITECTURA/tools/corpus_gap.py` | 465 | si | `TOOL_PARTIAL` | `b07557fe531c5ffa` |
| `08-ARQUITECTURA/tools/corpus_guard.py` | 281 | NO | `TOOL_UNVALIDATED` | `115834333f1f8526` |
| `08-ARQUITECTURA/tools/count_vmflush_dw.py` | 75 | NO | `TOOL_UNVALIDATED` | `d3d981ecf764353a` |
| `08-ARQUITECTURA/tools/doclint.py` | 469 | si | `TOOL_PARTIAL` | `b53ddfd5a610d2ce` |
| `08-ARQUITECTURA/tools/driver_offsets.py` | 498 | si | `TOOL_PARTIAL` | `8ad9bd373b7c0d60` |
| `08-ARQUITECTURA/tools/emisor.py` | 517 | si | `TOOL_PARTIAL` | `f16cf70d42925fd2` |
| `08-ARQUITECTURA/tools/exit_contract.py` | 154 | si | `TOOL_PARTIAL` | `532477488d45c03d` |
| `08-ARQUITECTURA/tools/findings_index.py` | 918 | si | `TOOL_PARTIAL` | `cbe8f00d16000778` |
| `08-ARQUITECTURA/tools/findnum.py` | 721 | si | `TOOL_PARTIAL` | `0c416caa689f0790` |
| `08-ARQUITECTURA/tools/fingerprint.py` | 340 | si | `TOOL_PARTIAL` | `5057d6df1f2b4422` |
| `08-ARQUITECTURA/tools/frame_budget.py` | 137 | NO | `TOOL_UNVALIDATED` | `7fcd489b70e877ee` |
| `08-ARQUITECTURA/tools/fronteras.py` | 479 | si | `TOOL_PARTIAL` | `905447fee7bdded1` |
| `08-ARQUITECTURA/tools/fw_ipver.py` | 293 | si | `TOOL_PARTIAL` | `d3d8acc5d0c27afa` |
| `08-ARQUITECTURA/tools/gfx8_opcode.py` | 401 | si | `TOOL_PARTIAL` | `1b1b59838400fb37` |
| `08-ARQUITECTURA/tools/gmmio_inventory.py` | 343 | NO | `TOOL_UNVALIDATED` | `191d9461f8c9a2d1` |
| `08-ARQUITECTURA/tools/h1_stale.py` | 243 | NO | `TOOL_UNVALIDATED` | `bc460762e6b785df` |
| `08-ARQUITECTURA/tools/hdrmap.py` | 341 | si | `TOOL_PARTIAL` | `f7016fe9fb9e7fe2` |
| `08-ARQUITECTURA/tools/huella.py` | 258 | si | `TOOL_PARTIAL` | `5f6e3dfa3ea8e15b` |
| `08-ARQUITECTURA/tools/include_closure.py` | 227 | NO | `TOOL_UNVALIDATED` | `5195407a7181af9f` |
| `08-ARQUITECTURA/tools/inst_closure.py` | 922 | si | `TOOL_PARTIAL` | `424fc5664b9ab4e1` |
| `08-ARQUITECTURA/tools/ip_surface.py` | 401 | si | `TOOL_PARTIAL` | `e05854f9a5d9cc10` |
| `08-ARQUITECTURA/tools/ipver_zero.py` | 294 | si | `TOOL_PARTIAL` | `a6a3eaf0535ded8f` |
| `08-ARQUITECTURA/tools/ko_immediate.py` | 452 | si | `TOOL_PARTIAL` | `5325f5aa8582fd2e` |
| `08-ARQUITECTURA/tools/mmio_map.py` | 374 | si | `TOOL_PARTIAL` | `18e857142a9a5780` |
| `08-ARQUITECTURA/tools/mqd_layout.py` | 788 | si | `TOOL_PARTIAL` | `6937aa5554f028f0` |
| `08-ARQUITECTURA/tools/next_work.py` | 307 | NO | `TOOL_UNVALIDATED` | `afe8946505a100cd` |
| `08-ARQUITECTURA/tools/num_collision.py` | 255 | si | `TOOL_PARTIAL` | `e10e8d7cd6347089` |
| `08-ARQUITECTURA/tools/pcie_bandwidth.c` | 273 | NO | `TOOL_UNVALIDATED` | `d3b12847123187a8` |
| `08-ARQUITECTURA/tools/pm4_codec.py` | 430 | NO | `TOOL_UNVALIDATED` | `d158f2f0d4a7d7ad` |
| `08-ARQUITECTURA/tools/pm4_count_census.py` | 159 | NO | `TOOL_UNVALIDATED` | `ad1f43a9d767468d` |
| `08-ARQUITECTURA/tools/pm4_emit.py` | 1118 | si | `TOOL_PARTIAL` | `89ca128f5a975e78` |
| `08-ARQUITECTURA/tools/pm4_layout_audit.py` | 178 | NO | `TOOL_UNVALIDATED` | `c588440731a0d5ec` |
| `08-ARQUITECTURA/tools/pm4_reachable.py` | 526 | NO | `TOOL_UNVALIDATED` | `4a154381331ea790` |
| `08-ARQUITECTURA/tools/recovery_preflight.sh` | 105 | NO | `TOOL_UNVALIDATED` | `c155561f5441a0c9` |
| `08-ARQUITECTURA/tools/reenvio_freeze.py` | 548 | si | `TOOL_PARTIAL` | `2944a13f3ea5a3f9` |
| `08-ARQUITECTURA/tools/reenvio_gate.py` | 587 | si | `TOOL_PARTIAL` | `8cd93a661dec5f00` |
| `08-ARQUITECTURA/tools/refs_repair.py` | 559 | si | `TOOL_PARTIAL` | `1d996978b2b935cb` |
| `08-ARQUITECTURA/tools/regdb.py` | 443 | si | `TOOL_PARTIAL` | `93dd5c536a1ee141` |
| `08-ARQUITECTURA/tools/run_all.py` | 691 | si | `TOOL_PARTIAL` | `68ae766c648d7674` |
| `08-ARQUITECTURA/tools/runtime_obs.py` | 432 | NO | `TOOL_UNVALIDATED` | `c002e8024e67d996` |
| `08-ARQUITECTURA/tools/scopeguard.py` | 373 | si | `TOOL_PARTIAL` | `064a5d5ec0b184c9` |
| `08-ARQUITECTURA/tools/smumsg.py` | 381 | si | `TOOL_PARTIAL` | `f7491e50338e078f` |
| `08-ARQUITECTURA/tools/stale_gap.py` | 1227 | si | `TOOL_PARTIAL` | `cc4067b426c8eb35` |
| `08-ARQUITECTURA/tools/struct_rw.py` | 183 | si | `TOOL_PARTIAL` | `f18b3f22ebdd16c1` |
| `08-ARQUITECTURA/tools/toalaudit.py` | 728 | si | `TOOL_PARTIAL` | `a98162c22675aa59` |
| `08-ARQUITECTURA/tools/toolaudit.py` | 916 | si | `TOOL_PARTIAL` | `9f3b6a73aa35e779` |
| `08-ARQUITECTURA/tools/toolkit.py` | 886 | si | `TOOL_PARTIAL` | `be7c579b6d41bdb1` |
| `08-ARQUITECTURA/tools/toolkit_cross.py` | 176 | si | `TOOL_PARTIAL` | `0f45db8eb33b50a9` |
| `08-ARQUITECTURA/tools/unversioned_drift.sh` | 116 | NO | `TOOL_UNVALIDATED` | `d4be00d68f6bb2da` |
| `08-ARQUITECTURA/tools/vbiosread.py` | 478 | si | `TOOL_PARTIAL` | `9b030fc46cdc49cc` |
| `08-ARQUITECTURA/tools/vulkan_compute_probe.c` | 1143 | NO | `TOOL_UNVALIDATED` | `7e7037cadea20251` |
| `08-ARQUITECTURA/tools/xref.py` | 491 | si | `TOOL_PARTIAL` | `90bb073df932d9ba` |
| `04-IMPLEMENTACION/rx550-driver/tools/contratos.sh` | 189 | NO | `TOOL_UNVALIDATED` | `605deecad0957983` |
| `04-IMPLEMENTACION/rx550-driver/tools/corpus_manifest_check.py` | 443 | NO | `TOOL_UNVALIDATED` | `0c4470893fac2610` |
| `04-IMPLEMENTACION/rx550-driver/tools/fix_gart_citations.py` | 215 | NO | `TOOL_UNVALIDATED` | `22cc55ceb2280bae` |
| `04-IMPLEMENTACION/rx550-driver/tools/gart_seq_oracle.py` | 364 | si | `TOOL_PARTIAL` | `5bae1ed9d472eeaf` |
| `04-IMPLEMENTACION/rx550-driver/tools/mutdrv.py` | 356 | si | `TOOL_PARTIAL` | `3668a61864c2956f` |
| `04-IMPLEMENTACION/rx550-driver/tools/tu_compila.sh` | 120 | NO | `TOOL_UNVALIDATED` | `ec32a768b85de4d6` |
| `04-IMPLEMENTACION/tools/rx550_compress.c` | 226 | NO | `TOOL_UNVALIDATED` | `84201716cdb562a0` |
| `04-IMPLEMENTACION/tools/rx550_decompress.c` | 624 | NO | `TOOL_UNVALIDATED` | `e7db60d3a5881930` |
| `09-POWER-CLOCKS/tools/rx550_hold.c` | 35 | NO | `TOOL_UNVALIDATED` | `5153ce6d0a34fa3a` |
| `09-POWER-CLOCKS/tools/rx550_load.c` | 261 | NO | `TOOL_UNVALIDATED` | `ffeb131b726151b3` |
| `01-AUDITORIA/tools/inventario_universo.py` | 185 | NO | `TOOL_UNVALIDATED` | `aa4764ffa1aa2402` |
| `revkit/atomrom.py` | 2200 | NO | `TOOL_UNVALIDATED` | `97e718d5aa4624a8` |
| `revkit/bootcheck.py` | 251 | si | `TOOL_PARTIAL` | `7e97b90ca7a0a5ed` |
| `revkit/btfsnap.py` | 444 | si | `TOOL_PARTIAL` | `c740eeb2906bed96` |
| `revkit/captura.py` | 313 | NO | `TOOL_UNVALIDATED` | `728db65b67ad9112` |
| `revkit/causa.py` | 295 | NO | `TOOL_UNVALIDATED` | `673428deb9ebba75` |
| `revkit/check.sh` | 615 | si | `TOOL_UNVALIDATED` | `2603535bbfb0eff9` |
| `revkit/cidx.py` | 474 | NO | `TOOL_UNVALIDATED` | `4c8a050ab2321d1e` |
| `revkit/cn7.py` | 1024 | NO | `TOOL_UNVALIDATED` | `e1ec5697173a3730` |
| `revkit/cn8.py` | 557 | NO | `TOOL_UNVALIDATED` | `d371fb5082be6dbb` |
| `revkit/correlate.py` | 185 | NO | `TOOL_UNVALIDATED` | `12d211edd56e1730` |
| `revkit/dires.py` | 203 | NO | `TOOL_UNVALIDATED` | `63070f7997e92754` |
| `revkit/emitref.py` | 722 | si | `TOOL_PARTIAL` | `906dd20a2ae0c8a1` |
| `revkit/estado.py` | 195 | NO | `TOOL_UNVALIDATED` | `90fdc43fcd66288f` |
| `revkit/gchwip_alcance.py` | 445 | si | `TOOL_PARTIAL` | `2530551ff03df8b6` |
| `revkit/gfx8blocks.py` | 583 | si | `TOOL_PARTIAL` | `f10ba91ecc40f6ed` |
| `revkit/gputel.py` | 389 | si | `TOOL_PARTIAL` | `0bfbbdc50d79e8fa` |
| `revkit/huerfanos.py` | 237 | NO | `TOOL_UNVALIDATED` | `ef75f6b47b977ca5` |
| `revkit/ibpools.py` | 281 | NO | `TOOL_UNVALIDATED` | `49413b6e5db7b275` |
| `revkit/ibtrace.py` | 568 | si | `TOOL_PARTIAL` | `218a43cb90098326` |
| `revkit/integro.py` | 548 | NO | `TOOL_UNVALIDATED` | `639f64a07d08ae12` |
| `revkit/klog.py` | 185 | NO | `TOOL_UNVALIDATED` | `b5a21c5bd27592c2` |
| `revkit/mmo.py` | 303 | NO | `TOOL_UNVALIDATED` | `c18560f289e93031` |
| `revkit/obs.py` | 229 | NO | `TOOL_UNVALIDATED` | `348c668d92dda5fe` |
| `revkit/pm4dec.py` | 1186 | NO | `TOOL_UNVALIDATED` | `02343b512ca31439` |
| `revkit/pte.py` | 262 | NO | `TOOL_UNVALIDATED` | `563df59d52658b62` |
| `revkit/pub.sh` | 212 | si | `TOOL_UNVALIDATED` | `b7ffb8b3b21e8c2b` |
| `revkit/pub_selftest.sh` | 203 | si | `TOOL_UNVALIDATED` | `68fcebed3b5e30f5` |
| `revkit/regs.py` | 480 | NO | `TOOL_UNVALIDATED` | `1903c3da3b154838` |
| `revkit/scan.py` | 301 | NO | `TOOL_UNVALIDATED` | `2648716103f99e78` |
| `revkit/selfcheck.py` | 683 | NO | `TOOL_UNVALIDATED` | `a049d2a57796e46d` |
| `revkit/sello.py` | 421 | NO | `TOOL_UNVALIDATED` | `2460eb540d953352` |
| `revkit/vclaims.py` | 298 | NO | `TOOL_UNVALIDATED` | `32edc96e8aeff849` |
| `revkit/verdiff.py` | 329 | NO | `TOOL_UNVALIDATED` | `f41335ce3d57fb2c` |

**Total**: 194 herramientas, 63 `TOOL_UNVALIDATED`, 1 `TOOL_BROKEN`, 58 sin selftest declarado.

AGENTS.md: *`TOOL_UNVALIDATED` no puede cerrar una afirmación crítica*.
Las que lo estan no pueden ser el unico sustento de un hallazgo.


## Cobertura, y por que esta seccion existe

MEDIDO 2026-10-04:  el recorrido era de UN solo directorio (`os.path.join(root, "tools")`)  y el proyecto tiene 7.  Con eso el registro clasificaba 72 filas mientras habia **194** ejecutables,  y como el registro es GENERADO nadie lo notaba:  el numero que salia era el de lo que se veia,  que es exactamente el fallo de un control que no puede fallar.  Los dos numeros los cuenta este generador en cada ejecucion, no estan escritos:  un texto que afirma una cifra y la repite es una copia mas,  y las copias envejecen.

| directorio | filas | selftest ejecutado por este generador |
|---|---|---|
| `tools/` | 76 | si |
| `08-ARQUITECTURA/tools/` | 74 | **no** — limite declarado |
| `04-IMPLEMENTACION/rx550-driver/tools/` | 6 | **no** — limite declarado |
| `04-IMPLEMENTACION/tools/` | 2 | **no** — limite declarado |
| `09-POWER-CLOCKS/tools/` | 2 | **no** — limite declarado |
| `01-AUDITORIA/tools/` | 1 | **no** — limite declarado |
| `revkit/` | 33 | **no** — limite declarado |

Las filas existen todas y llevan su `sha256`,  que es lo que las hace citables sin ambiguedad.  Lo que NO se hace es ejecutar sus selftests:  MEDIDO que son mas de 120 s por regeneracion,  y un generador que tarda dos minutos en un artefacto que se regenera a mano no se usa  —que es como muere un generador:  dejando de ejecutarse—.

El estado de esas 118 filas es `TOOL_PARTIAL` con el motivo EN LA FILA, no `TOOL_VALIDATED`:  la tabla no afirma una validacion que nadie ha ejecutado.  Y el limite es un dato  y no una excusa:  un `TOOL_PARTIAL` con su motivo se puede cerrar;  una herramienta ausente no se cierra de ninguna manera.

Y AHORA LA LISTA ES UNA SOLA.  MEDIDO que antes este fichero tenia la suya  —un directorio—  y `toolreg.py` la suya  —dos—  y no coincidaban.  Dos listas de "donde viven las herramientas" es una lista y un grupo de herramientas que nadie mira.  Este fichero importa `toolreg.TOOL_DIRS`,  y la puerta que hace que la lista no se quede corta esta en `toolreg.py`:  `directorios_no_declarados()`,  que recorre el arbol buscando cualquier directorio llamado `tools` y falla si no esta declarado.  MEDIDO que esa puerta encontro tres directorios mas en su primera pasada,  uno de los cuales contiene los instrumentos que generan carga GPU medible.
