# FINDINGS-RENUMERACIONES

<!-- GENERADO por 08-ARQUITECTURA/tools/findings_index.py --escribir-reenvio.
     NO EDITAR A MANO: la siguiente ejecucion lo sobrescribe. -->

Tabla de renumeraciones de hallazgos. Sirve para **resolver una referencia
colgada**: si un documento cita el hallazgo `NNN` y ese numero ya no corresponde,
el par de esta tabla dice a donde fue.

## Por que existe

El numero de hallazgo es la clave primaria de la base de conocimiento. Varias
sesiones renumeraron sus hallazgos para resolver colisiones de numero, y **no
dejaron registro**. Como el renumerado ademas esta SIN COMMITEAR, ni el historial
de git lo conserva: comparar el arbol contra HEAD es hoy la unica fuente.

## Como se detecta

Por el **stem del nombre de fichero**, no por el titulo. El titulo no sirve: al
renumerar, el numero viejo deja de contener ese contenido, y el titulo solo
aparece una vez en el arbol. El nombre se conserva:

```
185-tlb-de-gfx8-entra-en-bloques-de-8-pte.md    (viejo, borrado)
239-tlb-de-gfx8-entra-en-bloques-de-8-pte.md    (nuevo)
```

## REASIGNADO = el numero viejo esta ocupado por OTRO contenido

No es lo mismo que una colision. Una colision son **dos** ficheros con el mismo
numero, y se ve. Una reasignacion es **un** fichero con el numero y contenido
distinto, y **no produce ninguna senal**: solo referencias que apuntan al
hallazgo equivocado. Por eso esta tabla marca los dos casos por separado.

## Uso

`viejo` ya no es el hallazgo. Para citarlo hay que usar `nuevo`. Cuando la tabla
no tiene entrada para un numero, ese numero es el que tiene hoy: no hay ambiguedad
de ese tipo.

## Advertencias


- Numeros con **colision** (>1 fichero): **74**
- Renumeraciones detectadas: **43**, de ellas **REASIGNADAS: 42**
- Ficheros en `findings/`: **509**
- **Referencias colgando** (`` `NNN` `` que ya no es ese hallazgo): **1033**, en **42** numeros distintos

Las referencias colgando son el dano real. Un numero renumerado sigue
escribiendose en el texto de otros hallazgos y **nada parece roto**,
porque el numero sigue existiendo. Solo se ven al cruzarlas contra
esta tabla.

| citado | deberia ser | veces |
|---|---|---|
| `052` | `193` | 8 |
| `085` | `194` | 46 |
| `088` | `195` | 17 |
| `089` | `196` | 12 |
| `090` | `205` | 13 |
| `091` | `206` | 10 |
| `092` | `207` | 22 |
| `093` | `208` | 13 |
| `102` | `209` | 23 |
| `103` | `210` | 83 |
| `104` | `211` | 118 |
| `105` | `212` | 26 |
| `106` | `213` | 27 |
| `109` | `214` | 12 |
| `110` | `215` | 21 |
| `111` | `216` | 24 |
| `112` | `217` | 15 |
| `113` | `218` | 24 |
| `114` | `219` | 9 |
| `116` | `220` | 44 |
| `117` | `221` | 7 |
| `118` | `222` | 6 |
| `119` | `223` | 4 |
| `120` | `224` | 48 |
| `123` | `225` | 15 |
| `124` | `226` | 20 |
| `125` | `227` | 17 |
| `126` | `228` | 16 |
| `128` | `229` | 29 |
| `144` | `231` | 31 |
| `156` | `232` | 72 |
| `163` | `233` | 32 |
| `167` | `234` | 28 |
| `168` | `235` | 6 |
| `169` | `236` | 40 |
| `176` | `237` | 24 |
| `177` | `238` | 10 |
| `185` | `239` | 26 |
| `188` | `240` | 18 |
| `189` | `241` | 7 |
| `190` | `198` | 4 |
| `202` | `242` | 6 |

El renumerado **no esta commiteado**: HEAD y el arbol de trabajo
describen bases de datos distintas. Por eso la fuente es la
comparacion contra HEAD y no el historial.

## Numeros con colision (clave primaria no unica)

| numero | ficheros |
|---|---|
| 001 | 001-amdgpu-location.md<br>001-amdgpu-overview.md |
| 010 | 010-integration-validation.md<br>010-pgm-rsrc1-decoded.md |
| 021 | 021-frame-budget-gfx8-peor-caso.md<br>021-write-lock-scoped-subdir-does-not-block.md |
| 023 | 023-pm4-count-convencion-medida.md<br>023-pte-productor-sdma-gfx8.md |
| 024 | 024-page-table-geometria-gfx8.md<br>024-pm4dw-herramienta-conteo-emision.md |
| 025 | 025-gart-invalidate-con-orden-cpu.md<br>025-vm-flush-path-gfx8-63dw.md |
| 026 | 026-frame-completo-gfx8-121dw.md<br>026-pte-encoding-gfx8.md |
| 027 | 027-ptba-produccion-gfx8.md<br>027-write-multiple-resuelto.md |
| 028 | 028-emit-frame-size-justificado.md<br>028-fence-completion-orden-d.md |
| 029 | 029-orden-validacion-fence-no-ring.md<br>029-release-mem-y-eop-exec-muerto.md |
| 030 | 030-page-walker-gfx8-2-niveles.md<br>030-writeback-buffer-wb-slots.md |
| 031 | 031-aridad-no-entregada.md<br>031-rptr-wptr-tres-dominios.md |
| 032 | 032-fence-lectura-coherente-por-pin.md<br>032-pte-invalido-no-existe.md |
| 033 | 033-mmu-vm-no-publicado.md<br>033-pm4-spec-gfx8-no-existe-y-el-encuadre.md<br>033-protections-opaco-en-el-camino-gpuvm.md |
| 035 | 035-block-size-tres-claims-y-un-log.md<br>035-correccion-ptepde-es-polaris12.md |
| 036 | 036-correccion-023-implementada-ptepde.md<br>036-vocabulario-pm4-vivo-polaris12.md |
| 037 | 037-mapa-registros-mosaico-y-60-escrituras.md<br>037-ptba-dos-tramos-y-vm-flush.md |
| 038 | 038-herramientas-para-no-repetir-errores.md<br>038-validador-flujo-y-regla-del-count.md |
| 039 | 039-cierre-de-includes-resolucion-real.md<br>039-coherencia-ib-si-existe.md |
| 040 | 040-corpus-verificado-contra-binario-y-runtime.md<br>040-smu-canal-mensajes-gfx8.md<br>040-wptr-doorbell-y-tres-productores-de-ib.md |
| 041 | 041-curva-at-histeresis-dvfs-gfx8.md<br>041-grafo-y-detector-contradicciones.md<br>041-herramientas-de-procedencia-y-auditoria.md |
| 042 | 042-at-wire-format-inversion-cg-r-l.md<br>042-mapa-causal-y-mecanismo-hqd-mqd.md<br>042-vmid-map-y-la-particion-que-es-decision.md |
| 043 | 043-asercion-struct-mqd-contra-offsets.md<br>043-pll-bsp-asi-pasi.md<br>043-vuelta-atras-035-y-036-leian-el-asic-equivocado.md |
| 044 | 044-asercion-corroborada-y-regla-propias-ajenas.md<br>044-correccion-implementada-y-por-que-make-no-vio-el-cambio.md<br>044-xclk-fuentes-y-constantes-legacy.md |
| 045 | 045-fronteras-obsoletas-y-cuatro-formas-de-mentir.md<br>045-la-convencion-de-count-nunca-se-midio-en-mi-asic.md<br>045-smu-cadena-completa-y-cierre-de-scope.md |
| 046 | 046-auto-referencia-y-la-jerarquia-de-fuentes.md<br>046-correccion-smu-ruta-no-compilada-para-polaris12.md<br>046-la-version-de-ip-que-nunca-se-consulta.md |
| 047 | 047-el-handler-si-lee-src-data.md<br>047-los-diez-selectores-y-el-limite-del-claim.md<br>047-ruta-real-polaris12-canal-smc-argumento-vtable.md |
| 048 | 048-claims-y-lo-que-el-proyecto-realmente-cita.md<br>048-numeros-de-hallazgo-no-identifican.md<br>048-protocolo-smc-polaris-armado-y-retorno-siempre-cero.md |
| 049 | 049-los-497-respaldos-en-codigo-resueltos.md<br>049-modelo-voltaje-smio-polaris12.md |
| 050 | 050-correccion-chip-id-y-clock-stretcher.md<br>050-frontera-de-corpus-no-de-hardware.md<br>050-la-frontera-ordenada-por-su-via-de-cierre.md |
| 051 | 051-asic-id-desde-pci-config.md<br>051-interrupt-vector-iv-gfx8-y-teardown-lifo.md<br>051-leer-agents-md-cambia-la-politica.md |
| 056 | 056-function-always-spec-primaria-descartada-con-causa.md<br>056-siete-herramientas-y-22-bugs-encontrados.md |
| 071 | 071-el-except-que-devuelve-stub-y-el-flag-que-desactiva-la-auditoria.md<br>071-f2-ejecutado-bloqueado-por-saturacion-gpu.md |
| 072 | 072-f3c-estatico-cond-exc-e-invalidate-response.md<br>072-la-lista-cerrada-de-verbos-que-cronometraba-el-grafo.md |
| 073 | 073-el-indice-por-numero-descarta-y-el-grafo-pierde-aristas.md<br>073-f7-medido-216-sin-versionar-y-17-ids-duplicados.md |
| 074 | 074-25-aristas-que-existian-y-44-findings-sin-relacion.md<br>074-f2b-el-hardware-compone-el-pte.md |
| 081 | 081-la-tabla-dpm-son-1884-bytes-no-1120.md<br>081-system-access-mode-3-es-not-in-sys.md |
| 082 | 082-el-acceso-no-mapeado-pide-pagina-prt.md<br>082-ocho-fallos-de-layout-que-producen-numeros-plausibles-y-falsos.md |
| 083 | 083-auditoria-de-las-110-copias-a-la-ram-del-smc.md<br>083-en-gfx8-el-prt-se-puede-activar-y-no-hay-quien-lo-atienda.md<br>083-sg-cache-coherency-l1-l2-y-asimetria.md |
| 084 | 084-mecanismo-de-copia-al-smc-y-assert-de-rango.md<br>084-se-packet-consumption-y-granularidad.md |
| 086 | 086-sf-vram-256m-visibles-y-la-bar.md<br>086-usec-timeout-del-handshake-smc.md |
| 087 | 087-los-tres-pidcontroller-son-del-firmware.md<br>087-sf-gmc-8-1-nombre-no-predice-generacion.md<br>087-vm-fault-stop-0-y-ip-block-mask-confirma-047.md |
| 094 | 094-arranque-y-escritura-de-4-bytes-en-campo-de-1.md<br>094-gfx8-solo-escribe-los-bits-0-11-del-pte.md<br>094-sd-presupuesto-del-frame-dos-cifras-viejas.md |
| 095 | 095-camino-termico-y-un-assert-inerte.md<br>095-los-5-sin-medir-y-los-2-limite-reconcilian.md<br>095-se-pfp-me-ce-tres-motores-tres-icache.md |
| 096 | 096-arbitraje-dram-sin-inicializar-y-tabla-de-ventilacion.md<br>096-el-discriminante-abc-no-es-cerrable-desde-el-corpus.md<br>096-se-mecanismo-de-fence-completo.md |
| 097 | 097-el-memset-que-falta-en-dos-de-cinco.md<br>097-los-faults-de-vm-estan-desactivados-en-esta-placa.md<br>097-se-observado-24-de-24-pares-eop-delta-1.md |
| 098 | 098-graphicsbootlevel-dos-escritores-dos-espacios-de-indices.md<br>098-prt-funciona-al-reves-en-gfx9.md<br>098-se-observado-retraso-fence-0-a-4.md |
| 099 | 099-el-retorno-del-setup-de-tablas-dpm-se-ignora.md<br>099-prt-no-tiene-consumidor-en-el-arbol.md<br>099-sc-observado-prt-enmascara-el-fault-de-pde0.md |
| 100 | 100-el-limite-de-la-sram-del-smc-es-el-doble-de-la-sram-declarada.md<br>100-prt-no-tiene-consumidor-ni-en-firmware-ni-irq.md<br>100-sf-observado-gart-65536-y-el-sysfs-que-no-lo-dice.md |
| 101 | 101-corpus-hueco-ttm-cierre-parcial-y-valor.md<br>101-el-return-temprano-deja-el-selector-de-rango-del-pll-en-cero.md<br>101-gfx8-decodifica-el-tipo-de-fault-y-nadie-lo-lee.md |
| 107 | 107-el-parche-de-uvd-escribe-sobre-smio-5.md<br>107-el-reset-vacia-tlb-sin-request.md<br>107-sc-function-always-2-de-7-y-el-ring-usa-1.md |
| 108 | 108-el-determinante-del-desfase-y-lo-que-no-se-puede-cerrar.md<br>108-sd-pfp-escribe-me-espera-punto-de-visibilidad.md |
| 115 | 115-firmware-smc-si-en-el-corpus.md<br>115-sd-cuando-hay-invalidate-regla-por-vmid.md |
| 121 | 121-la-deuda-de-340-no-se-limpa-se-evita.md<br>121-pm4-estatico-y-la-contabilidad-cuadra.md<br>121-tabla-de-relojes-dpm-reconstruida.md |
| 122 | 122-e-los-10-wait-reg-mem-son-hdp-flush.md<br>122-para-que-el-encuadre-de-dos-fuentes-resulte-honesto.md<br>122-ulplatformcaps-decode-y-validacion-cruzada.md |
| 127 | 127-align-mask-no-se-opone-a-emit-ib-size.md<br>127-dos-rutas-y-la-de-caida-defectuosa.md<br>127-g-hay-una-cache-l2-de-fragmentos.md |
| 130 | 130-ab-el-l1-guarda-un-pte-por-fragmento.md<br>130-la-clase-count-menos-n-barrida.md<br>130-pm4-contrastado-contra-el-codigo-del-ko.md |
| 131 | 131-c-prt-no-esta-bloqueado.md<br>131-los-26-count-valen-uno-y-esta-medido.md |
| 132 | 132-a-flags-de-pte-frag-y-tf.md<br>132-clockstretcher-viva-en-mi-placa.md |
| 133 | 133-g-el-mtype-no-existe-en-gfx8.md<br>133-ulv-viva-y-linklevel-count-mas-1.md |
| 134 | 134-hay-un-objeto-vddc-svid2-y-vddcphase-es-3.md<br>134-que-se-puede-ver-sin-root-y-que-no.md |
| 135 | 135-packet3-clasificados-por-quien-los-usa.md<br>135-tres-capas-del-mvdd-por-nivel.md |
| 136 | 136-el-indice-del-proyecto-estaba-obsoleto.md<br>136-g-la-cadena-de-coherencia-cerrada.md |
| 246 | 246-la-coherencia-de-gfx8-son-tres-registros-y-ninguno-de-cache.md<br>246-todo-el-mmio-pasa-por-dos-helpers.md |
| 258 | 258-veinticuatro-gbs-de-vram-contra-dos-gbs-de-pcie.md<br>258-verificar-el-target-coincide-en-diez-campos-y-la-amd-no-es-card0.md |
| 261 | 261-banco-de-pruebas-de-computo-y-el-bug-que-lo-invalido.md<br>261-dri-0-no-es-la-rx-550-y-card1-no-es-un-nodo-drm.md |
| 262 | 262-dos-escritores-en-la-misma-ram-del-smc.md<br>262-el-control-tardo-tres-versiones-en-ser-un-control.md |
| 265 | 265-el-tamano-de-cache-de-gfx8-no-esta-en-ningun-sitio.md<br>265-la-tabla-que-manda-es-el-vbios-y-no-el-avfs.md |
| 272 | 272-cg-mask-y-cu-mask-son-categorias-distintas.md<br>272-el-techo-de-overdrive-sale-de-una-lectura-fuera-de-rango.md |
| 288 | 288-el-barrido-tiene-dos-codos-y-ninguno-mide-cache.md<br>288-falla-no-es-una-unidad-cinco-herramientas-encontrandose-a-si-mismas.md |
| 959 | 959-el-barrido-como-suite-y-los-dos-fallos-de-su-veredicto.md<br>959-el-barrido-como-suite-y-los-tres-fallos.md |
| 968 | 968-el-documento-que-declara-que-manda-declara-una-version-que-no-existe.md<br>968-q5-universo-de-tablas-gfx8.md |
| 998 | 998-el-oracle-del-proyecto-no-tiene-selftest-pero-la-tabla-dice-que-si.md<br>998-no-hay-allocateur-de-vmid-y-el-fsm-que-pide-el-mandato-no-es-el-que-existe.md |
| 999 | 999-el-corpus-de-definiciones-de-registro-es-identico-en-los-dos-arboles.md<br>999-el-fetch-del-anillo-es-un-bloque-de-registros-cp-rb-y-no-un-paquete.md |

## Renumeraciones

| viejo | nuevo | reasignado | fichero |
|---|---|---|---|
| 052 | 193 | **SI** | `tabla-de-asic-desde-el-binario.md` |
| 085 | 194 | **SI** | `huella-de-escritura-del-host-dentro-de-la-tabla-dpm.md` |
| 088 | 195 | **SI** | `cache-validada-por-longitud.md` |
| 089 | 196 | **SI** | `codificacion-de-frecuencia-de-reloj-punto-fijo.md` |
| 090 | 205 | **SI** | `regla-de-intercambio-y-cambio-de-codificacion-en-navi.md` |
| 091 | 206 | **SI** | `contrato-de-niveles-y-un-limite-no-comprobado.md` |
| 092 | 207 | **SI** | `palabra-de-voltaje-empaquetada-y-busqueda-por-techo.md` |
| 093 | 208 | **SI** | `lut-de-voltaje-del-smc.md` |
| 102 | 209 | **SI** | `siete-campos-de-pmfuses-se-suben-a-cero.md` |
| 103 | 210 | **SI** | `sc-handshake-de-completacion-existe-y-072-se-equivoco.md` |
| 104 | 211 | **SI** | `sc-invalidate-request-response-16-bits.md` |
| 105 | 212 | **SI** | `la-disposicion-del-firmware-por-un-shift-de-bits.md` |
| 106 | 213 | **SI** | `herramienta-de-cobertura-de-escrituras-en-la-sram.md` |
| 109 | 214 | **SI** | `ambito-de-variable-un-bug-de-la-herramienta-que-cazaba-mis` |
| 110 | 215 | **SI** | `allowmvddswitch-se-escribe-a-soft-regs-start.md` |
| 111 | 216 | **SI** | `cero-verificacion-de-lo-escrito-en-la-sram.md` |
| 112 | 217 | **SI** | `cadena-muerta-de-la-tabla-de-registros-mc.md` |
| 113 | 218 | **SI** | `sd-el-vm-flush-lo-pide-el-scheduler.md` |
| 114 | 219 | **SI** | `el-byte-que-se-escribe-no-es-offsetof-del-campo.md` |
| 116 | 220 | **SI** | `clock-stretch-amount-leido-del-vbios.md` |
| 117 | 221 | **SI** | `fw-smc-es-el-de-esta-placa-confirmado-por-dos-vias.md` |
| 118 | 222 | **SI** | `tjmax-93-a-operating-temp-43.md` |
| 119 | 223 | **SI** | `resultado-negativo-estados-ppt-sin-relojes.md` |
| 120 | 224 | **SI** | `dpm-levels-8-contra-una-cuenta-solo-validada-con-ge-1.md` |
| 123 | 225 | **SI** | `tabla-cac-vddgfx-basura-pero-con-un-cap-apagado.md` |
| 124 | 226 | **SI** | `barrido-de-la-frontera-vbios-host.md` |
| 125 | 227 | **SI** | `enable-dpm-tasks-devuelve-cero.md` |
| 126 | 228 | **SI** | `contrato-de-error-de-los-1093-asserts.md` |
| 128 | 229 | **SI** | `copia-sin-cota-contra-array-fijo-de-8.md` |
| 144 | 231 | **SI** | `ip-version-del-firmware-cierra-gfx-hwip.md` |
| 156 | 232 | **SI** | `coherencia-cpu-gpu-tres-mecanismos.md` |
| 163 | 233 | **SI** | `escritor-cpu-desactivado-por-dos-razones.md` |
| 167 | 234 | **SI** | `una-cita-puede-resolver-y-no-servir.md` |
| 168 | 235 | **SI** | `los-600mhz-son-el-techo-de-hdmi-2-0.md` |
| 169 | 236 | **SI** | `los-nueve-bloques-ip.md` |
| 176 | 237 | **SI** | `la-densidad-de-delegacion.md` |
| 177 | 238 | **SI** | `la-densidad-clasifica-el-fichero.md` |
| 185 | 239 | **SI** | `tlb-de-gfx8-entra-en-bloques-de-8-pte.md` |
| 188 | 240 | **SI** | `la-cadena-de-identidad-observada.md` |
| 189 | 241 | **SI** | `el-eslabon-que-faltaba-era-un-literal.md` |
| 190 | 198 | **SI** | `tres-correcciones-de-la-poda.md` |
| 202 | 242 | **SI** | `los-registros-caben-en-bar5-con-4x-de-holgura.md` |
| 975 | 976 | no | `corregcion-a-974-el-escritor-del-bit-51-es-inalcanzable-en` |
