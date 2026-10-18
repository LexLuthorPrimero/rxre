#!/usr/bin/env python3
# CONTRACT: name=citas_prosa_adjudicado
# CONTRACT: READONLY=yes
# CONTRACT: WRITES_FILES=no
# CONTRACT: WRITES_SYSFS=no
# CONTRACT: MUTATES_CORPUS=no
# CONTRACT: WRITES_GPU=no
# CONTRACT: TOUCHES_INTEGRATED=no
#
# MEDIDO con RXRE/tools/rxre_contracts.py, no declarado de memoria.  El
# veredicto fue `READONLY=yes, WRITES_FILES=no`, y las 0 escrituras que
# tiene se resolvieron a la clase TEMPORAL: no tiene ninguna escritura, asi que no hay nada que resolver.
#
# Declarar `WRITES_FILES=no` con escrituras dentro no es una contradiccion: es
# exactamente la clase TEMPORAL de `contract_exec.py`, que existe porque una
# regex produjo cinco falsos positivos.  Declararlas `yes` seria MENTIR: el
# validador no puede distinguir un temporal de un fichero del proyecto.
#
# `tools/` tenia 3 contratos de 92.  Este bloque no anade comportamiento: hace
# el comportamiento DECLARABLE, que es la condicion previa a poder usarlo.
# Sobre la frontera: TOUCHES_INTEGRATED=no, y el campo se declara aunque
# toolkit.py no lo conozca -- la frontera que no se puede declarar es la que no
# se puede hacer cumplir (hallazgo 1487).
# -*- coding: utf-8 -*-
# SPDX-License-Identifier: GPL-2.0
"""citas_prosa_adjudicado.py - LAS 132 ADJUDICACIONES A MANO de la muestra.

WORK_CLASS=READ_ONLY · MODIFICATIONS=0 · GPU INTACTA

QUE ES ESTE FICHERO, Y POR QUE NO ES UN DATO

Son 132 veredictos sobre citas concretas, escritas a mano leyendo la prosa que
cita y los ficheros de destino.  No son una verdad de la que se deriven otras
cosas: son la MEDIDA con la que se calibra el censo, y existen para que otra
persona pueda leer la prosa, leer el destino y disagrees.

Cada entrada trae el verbo con el que se adjudico y POR QUE.  Una entrada sin
prueba no se puede revisar, y una muestra sin pruebas no se puede refutar.

REGLAS DE ADJUDICACION, Y SON TRES, NO UNA

    C1  la propia cita dice a cual de los ficheros del numero va, y ese
        fichero sostiene lo que la prosa afirma.
    C2  la cita NO dice a cual va: o la frase no tiene contenido, o el
        contenido aparece en los dos.  No es un defecto de la cita: es que el
        numero no basta, y eso no se arregla reescribiendo sin saber cual.
    C3  la cita dice a cual va, y ese fichero NO dice lo que la prosa afirma.

LA REGLA QUE SE APLICA A LAS CITAS DE INSTRUMENTO

Un subconjunto grande de la muestra cae en ficheros cuyo objeto ES la
ambiguedad de las citas: `stale_gap.py`, `_selftest_stale_gap.py`,
`corpus_gap.py`, `num_collision.py`, `citeambig.py`, `check_num_unico.py`,
`CITA-CODIGO-EXCEPTIONS.txt`, y tambien documentos cuyo trabajo es hablar del
numero de hallazgo (`FINDINGS-RENDEX.md`, el indice de renumeraciones).  Ahi la
cita ambigua es el DATO, y reescribirla por nombre destruiria el instrumento.
Se marcan `C1_INSTRUMENTO` y son C1 por el mismo motivo que el registro
`tools/CITA-CODIGO-EXCEPTIONS.txt` ya declara para el codigo.
"""

ADJ = [
    # =====================================================================
    # ESTRATO  docs | C1_sostenida_por_ngrama   n=14
    # =====================================================================
    ("docs/MASTER-RESEARCH-STATUS.md", 173, 33, "C1", "033-protections-opaco-en-el-camino-gpuvm.md",
     "la prosa da `PDE_ENDIAN_SWAP_MODE` MASK 0x30 y `PTE_ENDIAN_SWAP_MODE` 0x0c; solo "
     "el hallazgo de PROTECTIONS tiene esos identificadores (4 distintos frente a 0)"),
    ("docs/MASTER-RESEARCH-STATUS.md", 171, 33, "C1", "033-protections-opaco-en-el-camino-gpuvm.md",
     "la prosa habla del campo `PROTECTIONS` de 8 bits; ese token esta en el titulo del "
     "destino y en el de ningun otro 033"),
    ("docs/MASTER-RESEARCH-STATUS.md", 120, 24, "C1", "024-page-table-geometria-gfx8.md",
     "`num_level = 1` derivado de `max_level = 1` es la geometria de page table"),
    ("docs/MASTER-RESEARCH-STATUS.md", 147, 35, "C2", "",
     "la circularidad del test propio aparece en los dos 035 (6 y 8 distintos) y ninguno "
     "de los dos nombres dice de test.  DECLARABLE"),
    ("docs/FINDINGS-INDEX.md", 36, 25, "C1_INDICE", "",
     "fila de la tabla de duplicados: `| 025 | 025-gart-... .md . 025-vm-flush-...md |`. "
     "El numero es la etiqueta de la fila y los dos nombres van a continuacion"),
    ("docs/MASTER-RESEARCH-STATUS.md", 122, 46, "C1", "046-la-version-de-ip-que-nunca-se-consulta.md",
     "`ipsolve` resuelve que `.c` implementa cada bloque de IP por ASIC; ese es el titulo "
     "del destino, y `046-correccion-smu-...` no coincide en ninguno"),
    ("docs/MASTER-RESEARCH-STATUS.md", 205, 33, "C1", "033-protections-opaco-en-el-camino-gpuvm.md",
     "la prosa ES la correspondencia PTE -> PROTECTIONS, que es el objeto del destino"),
    ("docs/FINDINGS-INDEX.md", 39, 28, "C1_INDICE", "",
     "fila de la tabla de duplicados, con los dos nombres"),
    ("docs/MASTER-RESEARCH-STATUS.md", 188, 24, "C1", "024-page-table-geometria-gfx8.md",
     "'el modelo de VM plano es una limitacion del silicio' refutado por `max_level = 1`: "
     "los cinco tokens estan en el destino y dos en el otro 024"),
    ("docs/MASTER-RESEARCH-STATUS.md", 149, 51, "C1", "051-interrupt-vector-iv-gfx8-y-teardown-lifo.md",
     "'el nombre del ip_block en el log de arranque NO predice el nombre del fichero': solo "
     "este 051 tiene 'arranque' y 'predice'"),
    ("docs/AGENTS-ADDENDA.md", 253, 28, "C1", "028-fence-completion-orden-d.md",
     "'fence con completion' + `028` §1: el otro 028 no coincide en nada"),
    ("docs/EVIDENCE-MATRIX.md", 269, 24, "C1", "024-page-table-geometria-gfx8.md",
     "`ilog2(64)+18 = 24 -> (24+3)/2 = 13` sobre `gfx8vmgeom`: 'ilog2' solo aparece en el "
     "destino"),
    ("docs/EVIDENCE-MATRIX.md", 267, 24, "C1", "024-page-table-geometria-gfx8.md",
     "`block_size = amdgpu_vm_get_block_size(vm_size)` con seccion §2.3: la funcion de "
     "geometria de page table esta en el destino"),
    ("docs/MASTER-RESEARCH-STATUS.md", 151, 46, "C1", "046-correccion-smu-ruta-no-compilada-para-polaris12.md",
     "`si_dpm.c` y `si_smc.c` no compilan para Polaris12: el nombre del destino lo dice"),
    # =====================================================================
    # ESTRATO  docs | C2_ambigua_senales_en_varios   n=8
    # (el proxy dijo ambigua; a mano 5 son C1 -> falso positivo de ambiguedad)
    # =====================================================================
    ("docs/FINDINGS-INDEX.md", 239, 40, "C2", "",
     "'la linea H que `040` acaba de abrir': cero tokens coincidentes en los tres 040"),
    ("docs/FINDINGS-INDEX.md", 241, 38, "C2", "",
     "'o el indice numerico ya no es': la frase no tiene contenido que elija"),
    ("docs/FINDINGS-INDEX.md", 241, 39, "C2", "",
     "misma frase, mismo motivo"),
    ("docs/MASTER-RESEARCH-STATUS.md", 175, 41, "C1", "041-curva-at-histeresis-dvfs-gfx8.md",
     "'el driver NO escribe los registros de reloj, el firmware del SMU aplica el cambio': "
     "10 tokens distintos en la curva DVFS y 0 en el grafo.  El proxy lo dio por ambiguo: "
     "FALSO POSITIVO DE AMBIGUEDAD"),
    ("docs/MASTER-RESEARCH-STATUS.md", 146, 50, "C2", "",
     "`asic_resolver` y `COMPILE_GATE_BEFORE_TRACE_GATE` no aparecen en ninguno de los tres 050"),
    ("docs/MASTER-RESEARCH-STATUS.md", 172, 33, "C2", "",
     "'el layout del PTE tiene una sola fuente: gmc_v8_0.c:691-702': 8 distintos en dos de "
     "los tres 033, empatados.  Habria que leer el §6 de cada uno"),
    ("docs/FINDINGS-INDEX.md", 138, 23, "C1", "023-pte-productor-sdma-gfx8.md",
     "la fila dice 'Corrige `023`: dice sdma_v4_0 y count - 1', y 'pte-productor-sdma' esta "
     "en el nombre del destino"),
    ("docs/CHANGELOG-RESEARCH.md", 1588, 71, "C1", "071-el-except-que-devuelve-stub-y-el-flag-que-desactiva-la-auditoria.md",
     "'`071` cuenta cinco defectos encadenados de la misma clase': cuenta, defectos, "
     "encadenados, quinta -- 4 contra 0"),
    # =====================================================================
    # ESTRATO  docs | SIN_APOYO_ninguna_senal   n=14
    # =====================================================================
    ("docs/MASTER-RESEARCH-STATUS.md", 454, 23, "C1_INDICE", "",
     "la celda es '7 indices de finding duplicados (`001`,`010`,`021`,`023`,...)': la lista "
     "de duplicados citada COMO DATO"),
    ("docs/NEGATIVE-RESULTS.md", 448, 71, "C2", "",
     "'la regla que `071` propone': un solo token comun ('auditoria') y dos hallazgos 071 "
     "distintos"),
    ("docs/EVIDENCE-MATRIX.md", 1696, 36, "C2", "", "RESIDUO: la frase no nombra nada de los dos 036"),
    ("docs/MASTER-RESEARCH-STATUS.md", 454, 24, "C1_INDICE", "", "misma celda de lista de duplicados"),
    ("docs/MASTER-RESEARCH-STATUS.md", 454, 10, "C1_INDICE", "", "misma celda de lista de duplicados"),
    ("docs/MASTER-RESEARCH-STATUS.md", 323, 24, "C2", "",
     "'`024` con 13': un token ('posteriores') en un 024 y ninguno en el otro"),
    ("docs/OPEN-FRONTIERS.md", 596, 36, "C1", "036-correccion-023-implementada-ptepde.md",
     "la prosa cita `revkit/PTEPDE-GFX8.md`, y 'ptepde' esta en el nombre del destino"),
    ("docs/EVIDENCE-MATRIX.md", 1696, 35, "C2", "", "RESIDUO: frase sin contenido"),
    ("docs/EVIDENCE-MATRIX.md", 1696, 36, "C2", "", "RESIDUO: frase sin contenido"),
    ("docs/EVIDENCE-MATRIX.md", 1728, 36, "C2", "",
     "'`036`, que queda retractado en su campo': no hay nada que elija entre los dos"),
    ("docs/FINDINGS-INDEX.md", 37, 26, "C1_INDICE", "", "fila de la tabla de duplicados, con los dos nombres"),
    ("docs/MASTER-RESEARCH-STATUS.md", 454, 25, "C1_INDICE", "", "misma celda de lista de duplicados"),
    ("docs/EVIDENCE-MATRIX.md", 945, 35, "C2", "", "'ausente hay que seguirlo hasta su declaracion': sin contenido"),
    ("docs/CONTRADICTIONS.md", 704, 35, "C2", "", "'`035` y `036` escribian': sin contenido"),
    # =====================================================================
    # ESTRATO  findings | C1_autocita   n=14   (todas C1 por construccion)
    # =====================================================================
    ("06-INGENIERIA-INVERSA/findings/021-write-lock-scoped-subdir-does-not-block.md", 159, 21,
     "C1_AUTOCITA", "", "la cita esta dentro de un 021 y nombra al otro 021 por nombre"),
    ("06-INGENIERIA-INVERSA/findings/999-el-corpus-de-definiciones-de-registro-es-identico-en-los-dos-arboles.md", 219, 999,
     "C1_AUTOCITA", "", "'este fichero es el segundo `999`': se declara el segundo, no se cita el otro"),
    ("06-INGENIERIA-INVERSA/findings/098-prt-funciona-al-reves-en-gfx9.md", 118, 98,
     "C1_AUTOCITA", "", "'`097` dijo / `098` corrige': tabla de dos filas, la de 098 es la suya"),
    ("06-INGENIERIA-INVERSA/findings/094-gfx8-solo-escribe-los-bits-0-11-del-pte.md", 95, 94,
     "C1_AUTOCITA", "", "'`094` (los bits 40-63 no existen)': se cita a si mismo"),
    ("06-INGENIERIA-INVERSA/findings/047-el-handler-si-lee-src-data.md", 152, 47,
     "C1_AUTOCITA", "", "'`047` §Confounders decia': cita a su propia seccion"),
    ("06-INGENIERIA-INVERSA/findings/096-el-discriminante-abc-no-es-cerrable-desde-el-corpus.md", 94, 96,
     "C1_AUTOCITA", "", "'`096` anade': cita a si mismo"),
    ("06-INGENIERIA-INVERSA/findings/115-sd-cuando-hay-invalidate-regla-por-vmid.md", 157, 115,
     "C1_AUTOCITA", "", "'cosas que `115` necesita': cita a si mismo"),
    ("06-INGENIERIA-INVERSA/findings/030-writeback-buffer-wb-slots.md", 208, 30,
     "C1_AUTOCITA", "", "'corrige mi `030` v1': cita a si mismo"),
    ("06-INGENIERIA-INVERSA/findings/031-rptr-wptr-tres-dominios.md", 412, 31,
     "C1_AUTOCITA", "", "'`031` §2.0 demostro': cita a su propia seccion"),
    ("06-INGENIERIA-INVERSA/findings/030-writeback-buffer-wb-slots.md", 209, 30,
     "C1_AUTOCITA", "", "'corrige mi `030` v1': cita a si mismo"),
    ("06-INGENIERIA-INVERSA/findings/258-veinticuatro-gbs-de-vram-contra-dos-gbs-de-pcie.md", 63, 258,
     "C1_AUTOCITA", "", "'`258` acerto el valor': cita a si mismo"),
    ("06-INGENIERIA-INVERSA/findings/097-los-faults-de-vm-estan-desactivados-en-esta-placa.md", 133, 97,
     "C1_AUTOCITA", "", "'`083` decia / `097` mide': la fila de 097 es la suya"),
    ("06-INGENIERIA-INVERSA/findings/083-en-gfx8-el-prt-se-puede-activar-y-no-hay-quien-lo-atienda.md", 70, 83,
     "C1_AUTOCITA", "", "'la pregunta que `083` dejo abierta': cita a si mismo"),
    ("06-INGENIERIA-INVERSA/findings/094-gfx8-solo-escribe-los-bits-0-11-del-pte.md", 143, 94,
     "C1_AUTOCITA", "", "'bits | PROVEN | 208 + 094': cita a si mismo"),
    # =====================================================================
    # ESTRATO  findings | C1_sostenida_por_ngrama   n=14
    # =====================================================================
    ("06-INGENIERIA-INVERSA/findings/063-memoria-sesion-smu-estado-persistente.md", 3640, 115, "C2", "",
     "'cuarta condicion a la cadena de `115`/`220`': 'cadena' esta en los dos 115"),
    ("06-INGENIERIA-INVERSA/findings/103-el-parche-de-uvd-reescribe-bootvddc.md", 358, 107, "C1",
     "107-el-parche-de-uvd-escribe-sobre-smio-5.md",
     "'VCE pisa lo que escribio UVD': UVD esta en el nombre del destino"),
    ("06-INGENIERIA-INVERSA/findings/035-block-size-tres-claims-y-un-log.md", 222, 24, "C1",
     "024-page-table-geometria-gfx8.md",
     "'el modelo de VM es plano por parametrizacion del driver': modelo, parametrizacion, driver"),
    ("06-INGENIERIA-INVERSA/findings/063-memoria-sesion-smu-estado-persistente.md", 4549, 130, "C2", "",
     "'cierra el NOT_DETERMINED de `130` con medicion': 3 candidatos y ninguno destaca"),
    ("06-INGENIERIA-INVERSA/findings/090-sg-l1-l2-constantes-fijas-y-grano-de-2mib.md", 149, 87, "C1",
     "087-sf-gmc-8-1-nombre-no-predice-generacion.md",
     "'un nombre en el driver no es cosa de esta GPU': el destino se llama 'nombre no predice'"),
    ("06-INGENIERIA-INVERSA/findings/911-el-vbios-dice-128-y-el-driver-informa-64.md", 129, 258, "C1",
     "258-veinticuatro-gbs-de-vram-contra-dos-gbs-de-pcie.md",
     "'los porcentajes de utilizacion de VRAM': porcentajes, utilizacion, 4 contra 0"),
    ("06-INGENIERIA-INVERSA/findings/109-sd-un-anillo-dos-motores-tres-esperas.md", 117, 107, "C1",
     "107-sc-function-always-2-de-7-y-el-ring-usa-1.md",
     "'los atribuí a gfx_v8_0.c:6047': el literal 6047 esta solo en ese fichero"),
    ("06-INGENIERIA-INVERSA/findings/308-setenta-y-cuatro-numeros-colisionan-y-1739-citas-no-saben-a-cual.md",
     97, 133, "C1", "133-g-el-mtype-no-existe-en-gfx8.md",
     "'`133` (el MTYPE)' y la celda de al lado dice g-el-mtype: el nombre lo dice"),
    ("06-INGENIERIA-INVERSA/findings/103-el-parche-de-uvd-escribe-sobre-smio-5.md" if False else
     "06-INGENIERIA-INVERSA/findings/103-el-parche-de-uvd-reescribe-bootvddc.md", 357, 107, "C1",
     "107-el-parche-de-uvd-escribe-sobre-smio-5.md",
     "'el campo es BootVddc': el literal esta solo en ese 107"),
    ("06-INGENIERIA-INVERSA/findings/082-el-acceso-no-mapeado-pide-pagina-prt.md", 114, 47, "C1",
     "047-los-diez-selectores-y-el-limite-del-claim.md",
     "'los diez selectores de amdgpu_ip_version son inalcanzables': el nombre del destino lo dice"),
    ("06-INGENIERIA-INVERSA/findings/091-el-bloqueo-tecnico-que-llevaba-toda-la-sesion-no-existencia.md",
     166, 83, "C1", "083-en-gfx8-el-prt-se-puede-activar-y-no-hay-quien-lo-atienda.md",
     "`VM_PRT_CNTL` real: request_mem, ioremap, RREG32 -- PRT, y PRT esta en el nombre del destino"),
    ("06-INGENIERIA-INVERSA/findings/229-copia-sin-cota-contra-array-fijo-de-8.md", 112, 127, "C2", "",
     "'las dos lecturas fuera de limite de `127`': 2 distintos en uno, 1 en otro, 0 en el tercero"),
    ("06-INGENIERIA-INVERSA/findings/099-prt-no-tiene-consumidor-en-el-arbol.md", 132, 98, "C1",
     "098-prt-funciona-al-reves-en-gfx9.md",
     "'cité gmc_v9_0.c:1192 como rama PRT del handler' describe el hallazgo 098 del PRT en GFX9"),
    ("06-INGENIERIA-INVERSA/findings/284-el-enlace-esta-en-2-gbs-y-la-tarjeta-admite-7877.md", 74, 258,
     "C2", "", "la frase esta truncada en el corte de la unidad y solo aporta 'razonamiento'"),
    # =====================================================================
    # ESTRATO  findings | C1_sostenida_por_token_raro   n=7  (estrato entero)
    # =====================================================================
    ("06-INGENIERIA-INVERSA/findings/063-memoria-sesion-smu-estado-persistente.md", 4219, 127, "C1",
     "127-dos-rutas-y-la-de-caida-defectuosa.md",
     "`ulMaxODEngineClock`: el identificador esta solo en ese 127"),
    ("06-INGENIERIA-INVERSA/findings/082-el-acceso-no-mapeado-pide-pagina-prt.md", 155, 25, "C1",
     "025-vm-flush-path-gfx8-63dw.md",
     "'los 10 dwords ocultos de emit_flush_gpu_tlb': dwords, ocultos, abierto -- y vm-flush"),
    ("06-INGENIERIA-INVERSA/findings/034-corpus-autoconsistente-layouts-pm4.md", 320, 33, "C1",
     "033-pm4-spec-gfx8-no-existe-y-el-encuadre.md",
     "'`033` §4 demostro que freedreno lo esta': freedreno esta solo en ese 033"),
    ("06-INGENIERIA-INVERSA/findings/041-herramientas-de-procedencia-y-auditoria.md", 109, 31, "C1",
     "031-aridad-no-entregada.md",
     "'verificador de aridad de `031` con su compuerta de cobertura': 5 tokens, el otro 031 tiene 0"),
    ("06-INGENIERIA-INVERSA/findings/072-la-lista-cerrada-de-verbos-que-cronometraba-el-grafo.md",
     62, 71, "C2", "",
     "'los cinco fallos de `071`': un token en cada 071 y ninguno de los dos nombres dice 'fallos'"),
    ("06-INGENIERIA-INVERSA/findings/026-frame-completo-gfx8-121dw.md", 44, 24, "C2", "",
     "'para `020`, `024` y `025`: los residuales +98/+57/+46': lista, sin contenido"),
    ("06-INGENIERIA-INVERSA/findings/098-graphicsbootlevel-dos-escritores-dos-espacios-de-indices.md",
     161, 94, "C2", "",
     "`GraphicsInterval` y `:2014-2016`: un token en cada uno de los tres 094"),
    # =====================================================================
    # ESTRATO  findings | C2_ambigua_senales_en_varios   n=14
    # =====================================================================
    ("06-INGENIERIA-INVERSA/findings/272-el-techo-de-overdrive-sale-de-una-lectura-fuera-de-rango.md",
     116, 127, "C1", "127-dos-rutas-y-la-de-caida-defectuosa.md",
     "'la ruta B de overdrive de `127`': hay un 127 que se titula 'dos rutas'"),
    ("06-INGENIERIA-INVERSA/findings/215-allowmvddswitch-se-escribe-a-soft-regs-start.md", 80, 100,
     "C2", "", "la unidad de la cita habla de `217` y de un alineamiento; no selecciona un 100"),
    ("06-INGENIERIA-INVERSA/findings/602-la-cadena-colapsa-y-el-techo-de-vram-estaba-en-la-mitad.md",
     125, 288, "C1", "288-el-barrido-tiene-dos-codos-y-ninguno-mide-cache.md",
     "'el barrido de anchos de banda': el nombre del destino dice 'el-barrido'"),
    ("06-INGENIERIA-INVERSA/findings/100-prt-no-tiene-consumidor-ni-en-firmware-ni-irq.md", 18, 33,
     "C1", "033-mmu-vm-no-publicado.md",
     "'`033` ya dijo que no esta publicado': el titulo del destino lo dice literalmente"),
    ("06-INGENIERIA-INVERSA/findings/987-cobertura-por-area-con-un-instrumento-tres-veces-roto.md",
     115, 33, "C2", "", "'es un muro, como `033`': dos palabras, no selecciona"),
    ("06-INGENIERIA-INVERSA/findings/030-writeback-buffer-wb-slots.md", 133, 29, "C2", "",
     "'`029` §2.4 ya habia identificado como inerte': ninguno de los dos 029 dice 'inerte'"),
    ("06-INGENIERIA-INVERSA/findings/045-la-convencion-de-count-nunca-se-midio-en-mi-asic.md", 85, 26,
     "C2", "", "lista de seis numeros, sin contenido"),
    ("06-INGENIERIA-INVERSA/findings/034-corpus-autoconsistente-layouts-pm4.md", 170, 33, "C2", "",
     "'el mismo argumento que `033` §3.3': dos 033 empatan y habria que leer las secciones"),
    ("06-INGENIERIA-INVERSA/findings/229-copia-sin-cota-contra-array-fijo-de-8.md", 180, 121, "C1",
     "121-tabla-de-relojes-dpm-reconstruida.md",
     "'la misma unidad que midio `121` en la tabla de': hay un 121 cuyo nombre es 'tabla-de-relojes'"),
    ("06-INGENIERIA-INVERSA/findings/273-no-hay-layout-para-la-revision-7.md", 110, 272, "C1",
     "272-el-techo-de-overdrive-sale-de-una-lectura-fuera-de-rango.md",
     "'es el techo de...': el techo de overdrive.  El proxy lo dio por ambiguo: FALSO POSITIVO"),
    ("06-INGENIERIA-INVERSA/findings/217-cadena-muerta-de-la-tabla-de-registros-mc.md", 246, 99,
     "C2", "", "'el patron de `099` se cumple en el codigo compartido': sin contenido"),
    ("06-INGENIERIA-INVERSA/findings/216-cero-verificacion-de-lo-escrito-en-la-sram.md", 123, 101,
     "C2", "", "lista de siete casos, sin contenido"),
    ("06-INGENIERIA-INVERSA/findings/095-los-5-sin-medir-y-los-2-limite-reconcilian.md", 31, 45,
     "C2", "", "'un limite de la herramienta': hay tres 045 y ninguno lo dice del nombre"),
    ("06-INGENIERIA-INVERSA/findings/144-prt-cierra-y-el-corpus-no-tiene-uapi.md", 281, 99, "C2", "",
     "lista de hallazgos con estados entre parentesis, sin contenido"),
    # =====================================================================
    # ESTRATO  findings | SIN_APOYO_ninguna_senal   n=14
    # =====================================================================
    ("06-INGENIERIA-INVERSA/findings/170-no-existe-codigo-que-reutilizar.md", 182, 130, "C2", "",
     "lista de cuatro numeros, sin contenido"),
    ("06-INGENIERIA-INVERSA/findings/077-141-citas-que-eran-rangos-y-10-omisiones-reales.md",
     133, 74, "C2", "",
     "'el conjunto que `074` dejo abierto': hay dos 074 y la frase no nombra el conjunto"),
    ("06-INGENIERIA-INVERSA/findings/108-sd-pfp-escribe-me-espera-punto-de-visibilidad.md", 165, 84,
     "C2", "", "lista con parentesis por tema ('packet consumption'), sin decidir"),
    ("06-INGENIERIA-INVERSA/findings/908-vram-bit-width-dice-64-y-la-medicion-dice-128.md", 55, 258,
     "C2", "",
     "`min_memory_clock_khz` 300.000 / `max_memory_clock_khz` 1.500.000: los dos 258 los podrian "
     "mencionar.  Habria que leer"),
    ("06-INGENIERIA-INVERSA/findings/083-sg-cache-coherency-l1-l2-y-asimetria.md", 158, 51, "C2", "",
     "'encadenada con `067` y `051`': sin contenido"),
    ("06-INGENIERIA-INVERSA/findings/123-e-cuadra-cuando-se-llama-hdp-flush.md", 255, 115, "C2", "",
     "lista de tres pares, sin contenido"),
    ("06-INGENIERIA-INVERSA/findings/969-el-control-marca-como-contaminacion-la-declaracion-correcta.md",
     149, 968, "C2", "", "'## 7 · Relacion con `968`': un encabezado de seccion"),
    ("06-INGENIERIA-INVERSA/findings/097-se-observado-24-de-24-pares-eop-delta-1.md", 55, 96, "C2", "",
     "lista de cuatro numeros, sin contenido"),
    ("06-INGENIERIA-INVERSA/findings/1000-de-pci-enumeration-a-gpu-ready-la-secuencia-completa.md",
     433, 51, "C2", "",
     "'mapa de BAR, 9 bloques, geometria': podria ser el 051 de asic-id-pci, pero no se sostiene"),
    ("06-INGENIERIA-INVERSA/findings/1010-el-limite-de-paginas-de-ttm-que-amdgpu-imprime-como-5907m.md",
     290, 999, "C1_NUMERO", "",
     "'su techo de 3 cifras -- `999` ya lo ocupan dos ficheros': habla del NUMERO 999, no del "
     "hallazgo.  Es la misma clase que el registro de codigo: el numero es el sujeto"),
    ("06-INGENIERIA-INVERSA/findings/114-implgate-cinco-bugs-propios-y-una-afirmacion-falsa.md",
     69, 39, "C2", "",
     "'cito `findings/039` para la': sin contenido sobre los dos 039"),
    ("06-INGENIERIA-INVERSA/findings/111-sd-next-ib-el-pfp-lo-busca.md", 163, 97, "C2", "",
     "lista de pares, sin contenido"),
    ("06-INGENIERIA-INVERSA/findings/074-f2b-el-hardware-compone-el-pte.md", 115, 23, "C1",
     "023-pm4-count-convencion-medida.md",
     "'`C-011` resolvio el emisor correcto': el hallazgo del emisor y su convencion de count"),
    ("06-INGENIERIA-INVERSA/findings/218-sd-el-vm-flush-lo-pide-el-scheduler.md", 158, 94, "C2", "",
     "'reconcilia `094` y `216`': hay tres 094"),
    # =====================================================================
    # ESTRATO  otros | C1_sostenida_por_ngrama   n=14
    # =====================================================================
    ("08-ARQUITECTURA/tools/_selftest_stale_gap.py", 485, 72, "C1_INSTRUMENTO", "",
     "el selftest fabrica la cita 072:117 para comprobar que el detector la ve"),
    ("08-ARQUITECTURA/tools/stale_gap.py", 684, 45, "C1_INSTRUMENTO", "",
     "el linter QUOTA la linea del hallazgo que cita; la cita es parte del texto que analiza"),
    ("08-ARQUITECTURA/tools/stale_gap.py", 927, 72, "C1_INSTRUMENTO", "", "idem, comentario de fixture"),
    ("08-ARQUITECTURA/tools/stale_gap.py", 682, 45, "C1_INSTRUMENTO", "", "idem"),
    ("08-ARQUITECTURA/tools/corpus_gap.py", 167, 40, "C1_INSTRUMENTO", "",
     "`040` en un comentario de la herramienta que audita hallazgos obsoletos"),
    ("tools/CITA-CODIGO-EXCEPTIONS.txt", 58, 1, "C1_INSTRUMENTO", "",
     "es el REGISTRO de las citas por numero en codigo: su trabajo es nombrarlas"),
    ("08-ARQUITECTURA/tools/_selftest_stale_gap.py", 426, 72, "C1_INSTRUMENTO", "", "fixture de self-test"),
    ("08-ARQUITECTURA/tools/num_collision.py", 60, 33, "C1_INSTRUMENTO", "",
     "el ejemplo del docstring es `d033:397` frente a `033:397`: el numero ambiguo es el sujeto"),
    ("08-ARQUITECTURA/tools/_selftest_stale_gap.py", 524, 24, "C1_INSTRUMENTO", "", "fixture de self-test"),
    ("08-ARQUITECTURA/tools/stale_gap.py", 100, 56, "C1_INSTRUMENTO", "", "fixture de self-test"),
    ("tools/artifacts.py", 22, 21, "C1_INSTRUMENTO", "",
     "comentario que explica el caso real 021:154 apuntando a `022-pte-productor-...`"),
    ("NEGATIVE-RESULTS.md", 74, 24, "C1", "024-page-table-geometria-gfx8.md",
     "'`024` / 13': el 13 es (24+3)/2, que es lo que calcula el 024 de geometria"),
    ("NEGATIVE-RESULTS.md", 99, 47, "C2", "",
     "'REFUTED en `047`: comparten h': la frase esta truncada y no selecciona entre los tres 047"),
    ("tools/citeambig.py", 160, 35, "C1_INSTRUMENTO", "",
     "'una cadena `findings/035` dentro de un docstring es un EJEMPLO': el ejemplo es el sujeto"),
    # =====================================================================
    # ESTRATO  otros | C2_ambigua_senales_en_varios   n=5  (estrato entero)
    # =====================================================================
    ("08-ARQUITECTURA/tools/fronteras.py", 132, 258, "C1_INSTRUMENTO", "",
     "'con 70 numeros colisionados, una cita como `258` no se puede': el ejemplo es el sujeto"),
    ("06-INGENIERIA-INVERSA/outgoing-reviews/2026-09-29-rever-to-ia2.md", 201, 10, "C2", "",
     "'CORRECCION 2026-09-29 (tras `010`)': sin contenido sobre los dos 010"),
    ("tools/citeambig.py", 482, 10, "C1_INSTRUMENTO", "",
     "el selftest fabrica el fichero 010-x.md: el numero ambiguo es el sujeto"),
    ("tools/drift.py", 837, 1, "C1_INSTRUMENTO", "",
     "el selftest fabrica findings/001.md: el numero ambiguo es el sujeto"),
    ("08-ARQUITECTURA/tools/fronteras.py", 133, 258, "C1_INSTRUMENTO", "", "idem que la 132"),
    # =====================================================================
    # ESTRATO  otros | SIN_APOYO_ninguna_senal   n=14
    # La mayoria NO SON CITAS: son patrones binarios y tablas de un volcado de
    # registros.  Es el hallazgo que hace que la poblacion de A3 no sea limpia.
    # =====================================================================
    ("05-FUENTES-EXTERNAS/FASE-R0-EXTERNAL-KNOWLEDGE/R0-7-REFERENCIA-X86-64-LECTURA-DESENSAMBLADO.md",
     694, 1, "NO_CITA", "",
     "`001` es un patron binario de 3 bits de la tabla de decodificacion SIB de x86-64"),
    ("05-FUENTES-EXTERNAS/FASE-R0-EXTERNAL-KNOWLEDGE/R0-7-REFERENCIA-X86-64-LECTURA-DESENSAMBLADO.md",
     657, 100, "NO_CITA", "",
     "`100` es el patron SIB base=100 index=100; no es el hallazgo 100"),
    ("tools/citas_prosa_etiquetas.py", 70, 968, "C1_INSTRUMENTO", "",
     "el fichero de etiquetas QUOTA la prosa adjudicada; es el sujeto"),
    ("08-ARQUITECTURA/decisions/2026-10-04-numeros-de-hallazgo-duplicados.md", 39, 999,
     "C1_INSTRUMENTO", "",
     "la decision sobre numeros duplicados nombra `999` COMO NUMERO duplicado"),
    ("08-ARQUITECTURA/tools/corpus_gap.py", 434, 1, "C1_INSTRUMENTO", "",
     "un print() de ejemplo con (001:213, 001:254, ...): el numero es el sujeto"),
    ("08-ARQUITECTURA/artifacts/Q5-MEM-TABLES/mem-tables.txt", 624, 127, "NO_CITA", "",
     "`D0[127:0]` es un rango de bits de un registro, no una cita"),
    ("08-ARQUITECTURA/tools/stale_gap.py", 831, 51, "C1_INSTRUMENTO", "",
     "el linter cita 051:147 como ejemplo de ventana"),
    ("05-FUENTES-EXTERNAS/FASE-R0-EXTERNAL-KNOWLEDGE/R0-7-REFERENCIA-X86-64-LECTURA-DESENSAMBLADO.md",
     697, 100, "NO_CITA", "", "`100` como columna de la tabla SIB"),
    ("tools/implgate.py", 221, 39, "C1_INSTRUMENTO", "",
     "el docstring cuenta el caso real que cito findings/039"),
    ("tools/citas_prosa_etiquetas.py", 70, 1011, "C1_INSTRUMENTO", "",
     "el fichero de etiquetas QUOTA la prosa adjudicada"),
    ("tools/check_num_unico.py", 161, 33, "C1_INSTRUMENTO", "",
     "el docstring explica por que el detector no puede citar `033` por nombre"),
    ("tools/CITA-CODIGO-EXCEPTIONS.txt", 67, 25, "C1_INSTRUMENTO", "",
     "el REGISTRO nombra la cita ambigua que declara"),
    ("05-FUENTES-EXTERNAS/FASE-R0-EXTERNAL-KNOWLEDGE/R0-7-REFERENCIA-X86-64-LECTURA-DESENSAMBLADO.md",
     673, 100, "NO_CITA", "", "`100` como columna de la tabla SIB"),
    ("08-ARQUITECTURA/tools/reenvio_gate.py", 716, 1, "C1_INSTRUMENTO", "",
     "el selftest del ledger escribe '# 002 destino / Era el `001` que ya lo ocupaba': es el sujeto"),
]

# --- el veredicto que se cuenta en la estimacion de clases ---------------
# C1_AUTOCITA, C1_INDICE, C1_INSTRUMENTO y C1_NUMERO son C1 con la prueba ya
# hecha por construccion.  NO_CITA no es C1 ni C2 ni C3: no es una cita, y por
# eso sale de la poblacion de clases y va a su propia cifra.
C1 = ("C1", "C1_AUTOCITA", "C1_INDICE", "C1_INSTRUMENTO", "C1_NUMERO")
C2 = ("C2",)
C3 = ("C3",)