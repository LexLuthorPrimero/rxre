# CONTRADICTIONS — registry

> Una contradicción no se resuelve borrando una de las dos afirmaciones. Se registra
> con las dos, se analyse el alcance, y se resuelve con evidencia nueva o se deja
> `OPEN` con la causa nombrada.
>
> `LAST_SCAN: 2026-10-01 11:20 -03:00` · método: `git log -S` sobre claims en
> conflicto, `git blame` para fecha y commit de cada versión, re-lectura del código
> citado, reejecución de herramientas.

---

## C-001 · `PROYECTO_STATUS.md` se contradice a sí mismo

```
ESTADO   RESOLVED  (2026-10-01, por agente de documentación)
SEVERIDAD ALTA — un fichero que dice PASS arriba y FAIL abajo hace que un agente
           elija la línea que leyó segundo. Es exactamente el daño que este registro
           existe para evitar.
```

```
CLAIM_A  PROYECTO_STATUS.md:4    "Fase 2 completa — el shader se ejecuta en la RX 550 y
                                su salida coincide byte a byte con el decodificador de
                                CPU (0/4096, 3 corridas)."
        PROYECTO_STATUS.md:75-77  "Agreement GPU vs CPU: ESTABLECIDO — 0 de 4096 bytes,
                                en 3 corridas consecutivas."

CLAIM_B  PROYECTO_STATUS.md:164  "1. El agreement test NO pasa. El shader corre, pero
                                57 de 64 bloques difieren en color."
```

Cronología, obtenida con `git log -S` y `git blame`:

| commit | hora | qué pasó |
|---|---|---|
| `b8294b1` | 2026-09-29 00:44 | se escribe el fichero. Limitación #1 dice `NO pasa`. El agreement es `PARTIAL/NOT_RUN` |
| `b7ed0c1` | 2026-09-29 01:10 | se corrige el push constant. Limitación #1 **sigue diciendo** `NO pasa` |
| `7ed1eca` | 2026-09-29 01:17 | AD-13 pasa a `COMPLETE` con la evidencia `0/4096` en 3 corridas. **La cabecera se actualiza; las limitaciones no** |
| `49bd550` | 2026-09-29 02:24 | se corrige una limitación falsa sobre `spirv-val`. Las otras siguen |

```
CONFLICT  la limitación #1 y la cabecera son el mismo hecho en dos estados. La
         limitación es de `b7ed0c1`, anterior a la evidencia que la refuta.
POSIBLE DIFERENCIA DE ALCANCE  ninguna: ambos hablan del agreement test de 64 bloques
         sobre la RX 550. No es CPU vs GPU ni un corpus distinto.
VEREDICTO  CLAIM_A es la vigente. CLAIM_B era correcta hasta las 01:10 y quedó
         obsoleta a las 01:17 sin que nadie la borrara.

RESOLUCIÓN  las cuatro limitaciones de `PROYECTO_STATUS.md:162-169` se marcaron
  SUPERSEDED / NOT_RECHECKED con el commit y la hora que las deja obsoletas. El texto
  original se conserva literal bajo la marca (§16: no se borra historia).
  Los "próximos pasos" 1 y 2 y la frase de la §Conclusión que decía "lo que falta es
  evidencia de ejecución en la RX 550" se marcaron igual: los tres eran falsos al
  escribirse y el último había sobrevivido al commit que los refutaba.

EVIDENCIA  7ed1eca  04-IMPLEMENTACION/work/*.decompress.log  (0 de 16384, 3 imágenes)
RESIDUO  la limitación #3 ("el test devuelve rc=0 aunque imprima [FAIL]") NO se ha
         re-verificado. Marcada NOT_RECHECKED. Es lo único de esta lista que puede dar
         un verde falso en CI hoy. Acción 1 de MASTER-RESEARCH-STATUS.
```

## C-002 · `29⁄9⁄26.md:169` conserva una afirmación refutada

```
ESTADO   OPEN  (documental, no técnico)
SEVERIDAD MEDIA — la afirmación es falsa, pero la corrección existe y está en otro
           fichero. Un agente que lea `29⁄9⁄26.md` sin llegar a `017` se lleva el error.
```

```
CLAIM_A  29⁄9⁄26.md:166-171   [CLOSED]  "WAIT_REG_MEM espera REQUEST == 0"
CLAIM_B  017 §3              la codificación es FUNCTION=0 (always), ref=0, mask=0.
                             Ningún bit se compara. 017 §4 lo marca REFUTED.
```

```
CONFLICT  el documento A confundió `ref = 0` con "comparar contra cero". Con
         FUNCTION=always el valor de ref no es un operando de comparación; y con
         mask=0 la comparación `(reg & 0) == (0 & 0)` es verdadera en la primera
         lectura, que no distingue nada.
ALCANCE   sólo el path de ring de GFX8. No afecta a 025 (ruta GART, path distinto).
         Lo que de A sobrevive y sigue PROVEN: el mecanismo de invalidación, el
         request por VMID, y que no era prueba de completion — eso último pasa a ser
         más fuerte, porque 018 lo convierte en NOT_IMPLEMENTABLE.
VEREDICTO  CLAIM_B. Refutación con evidencia de encoding, no por inferencia.
```

**Por qué sigue `OPEN`**: `29⁄9⁄26.md` no lleva ninguna marca de enmienda, y su
mtime (2026-09-29 23:12) es anterior a `017` (2026-10-01 09:52). Añadir una nota de
precedencia es una escritura en un fichero de otra sesión. `COORDINACION.md:184` es
"informa, no arregles". **La acción recomendada** es una nota de dos líneas al principio
de `29⁄9⁄26.md` apuntando a `017 §4`. Está en `OPEN-FRONTIERS.md` (F6) porque es
trabajo real, no un hueco de conocimiento.

## C-003 · Dos `block_size` para la misma geometría

```
ESTADO   RESOLVED  (2026-10-01) — a favor del valor 10
SEVERIDAD ALTA — afecta a la implementación del driver propio: reservation, tamaño de
           PTB, y de dónde acaba el aperture GART.
```

```
CLAIM_A  024-page-table-geometria-gfx8.md §2.3, §2.4, §6
         block_size = amdgpu_vm_get_block_size(vm_size) = 13
         PAGE_TABLE_BLOCK_SIZE escrito = 4  ->  0x04000000
         PTB = 2^13 = 8192 entradas = 64 KiB
         CLASIFICADO COMO PROVEN_DERIVED

CLAIM_B  gfx8vmgeom (commit 2599c65, escrito el mismo día)
         block_size = amdgpu_vm_get_block_size(tmp) = 10
         PAGE_TABLE_BLOCK_SIZE escrito = 1  ->  0x01000000
         PTB = 2^10 = 1024 entradas = 8 KiB
         Y CONTRASTA LA CADENA DERIVADA CONTRA LA LÍNEA QUE EL HOST IMPRIMIÓ EN EL BOOT:
             observada: vm size is 64 GB, 2 levels, block size is 10-bit,
                         fragment size is 9-bit
```

```
CONFLICT  las dos derivaciones leen la MISMA función y eligen ramas opuestas de su
         único `if`. `get_block_size` es:
             bits = ilog2(x) + 18
             return x <= 8 ? bits - 9 : (bits + 3) / 2
         Con x = 2   (lo que pasa el driver):  bits = 19, 2 <= 8  -> 10
         Con x = 64  (lo que dice 024):      bits = 24, 64 > 8  -> 13

POSIBLE DIFERENCIA DE ALCANCE  ninguna. `024` §2.1 calcula `tmp = 2` correctamente y
         lo escribe en su propia línea 101. Después, en §2.3, usa `vm_size` donde el
         código usa `tmp`. La contradicción está dentro del mismo documento.
VEREDICTO  CLAIM_B. Tres pruebas independientes:
   (a) el código: amdgpu_vm.c:2454  `adev->vm_manager.block_size =
                                   amdgpu_vm_get_block_size(tmp);`
       y `tmp` a esa altura es el resultado de `tmp = DIV_ROUND_UP(fls64(tmp)-1,9)-1`
       en la línea 2427. No se reasigna entre 2427 y 2454: comprobado por barrido.
   (b) el host: imprimió "block size is 10-bit" en el boot. Un valor observado por el
       hardware pesa más que dos derivaciones.
   (c) la herramienta: `make test` -> 37 aserciones, 0 fallos, y la línea derivada
       coincide con la observada caracter por caracter.
EVIDENCIA  amdgpu_vm.c:2424-2454 (leído directamente)
           02-ARQUITECTURA/RESEARCH-LINES.md:1861 y research_log.md:496 (el log)
           gfx8vmgeom commit 2599c65, salida de `make test` reejecutada 2026-10-01
NOTAS     024 §5 (saturación del campo de 4 bits) y §8 (UNLOCKS, "block_size 13")
           arrastran el mismo error. Su §4 (que el `-9` es MODEL_CHOICE del driver,
           no convención del hardware, por el mask/shift distinto en GFX9) es
           CORRECTO e independiente del error.
           023-pte §5 arrastra la misma tabla por RAM (13/14/14/15) — mismo origen.
```

**Registro histórico (no se borra)**: `024` mantiene su clasificación `PROVEN_DERIVED`
en su texto. Este registro es el que lo corrige, con fecha. Si `024` se vuelve a
editar, la marca de aquí es la que manda.

## C-004 · Cabecera de registros GMC: `gmc_8_1_d.h` vs `gmc_8_2_d.h`

```
ESTADO   RESOLVED  (por el propio 023-pte §4, 2026-10-01)
SEVERIDAD BAJA — cambió la atribución de fuente, no ninguna conclusión.
```

```
CLAIM_A  017, 018, 019  atribuyen los offsets GMC a gmc/gmc_8_2_d.h
CLAIM_B  gmc_v8_0.c:35 incluye gmc/gmc_8_1_d.h;  gfx_v8_0.c:41 incluye gmc/gmc_8_2_d.h
         Para el bloque GMC de GFX8 la cabecera correcta es la primera.
```

```
CONFLICT  atribución de fuente, no de resultado.
RESOLUCIÓN COMPARADOS 15 REGISTROS, offsets 15/15 IDÉNTICOS.
         Diferencia global entre las dos cabeceras: 8_1 tiene 1156 registros, 8_2 tiene
         882; 315 sólo en 8_1, 41 sólo en 8_2, y UN offset distinto
         (mmMC_CG_DATAPORT 0xa21 -> 0xa32) que ninguno de los tres findings cita.
CLASIFICACIÓN  CORRECTION_OF_PROVENANCE. Ninguna conclusión cambia.
```

## C-005 · `014-q1` cerró la geometría con tres cifras `PROVEN` que eran falsas

```
ESTADO   RESOLVED  (commit 2599c65)
SEVERIDAD ALTA en su momento — tres cifras marcadas PROVEN que un driver propio habría
           implementing al revés.
```

```
CLAIM_A  08-ARQUITECTURA/designs/014-q1-gpuvm-minimal.md, cerrado Q1 GPUVM_MINIMAL
              BITS_PER_LEVEL   = 9      PROVEN
              GPUVA_WIDTH_BITS = 30     PROVEN
              MIN_VIABLE_ASPACE = 2 MiB PROVEN
CLAIM_B  gfx8vmgeom + 024
              block_size = 10  ->  PTB = 2^10 = 1024 entradas, no 512
              PTB mide 8 KiB, no 4 KiB;  la unidad mínima real es 4 MiB
              GPUVA = 36 bits, no 30
              PDB0 = 16384 entradas = 128 KiB, no 512 = 4 KiB
```

```
CONFLICT  ninguna de las tres se equivocó por criterio: se equivocaron de rama.
         014 cites `else if (num_level > 1) block_size = 9;` — la rama que NO corre,
         porque num_level = 1. Dos detalles hacen que la lectura fuera plausible y
         por eso el error pasó: (a) fragment_size = 9 también es un 9, y convive con
         block_size en el mismo dev_info, así que "9" parecía confirmado dos veces;
         (b) con max_level=1 la aritmética del tamaño pediría 2 niveles, luego la
         suposición "9 porque 2^9" parecía derivar.
POSIBLE DIFERENCIA DE ALCANCE  ninguna: mismo ASIC, mismo corpus, misma función.
VEREDICTO  CLAIM_B.
EVIDENCIA  la línea del boot, que ningún documento de 014 menciona
RESIDUO    la suposición de 014 es la misma que `DRIVER-MISSION-STATE.md` enuncia como
           "el modelo de VM es plano por necesidad" (C-006)
```

## C-006 · `DRIVER-MISSION-STATE.md`: "plano por necesidad"

```
ESTADO   PARTIALLY_RESOLVED
SEVERIDAD MEDIA — media frase del documento es falsa, la otra media sobrevive.
```

```
CLAIM_A  08-ARQUITECTURA/designs/DRIVER-MISSION-STATE.md
         "GFX8 no tiene motor de recorrido de tabla de paginas. La tabla la escribe
          la CPU. El modelo de VM es plano por necesidad, no por eleccion."
```

```
CONFLICT  la segunda frase es REFUTED: el nivel lo elige max_level = 1, un argumento
         literal en gmc_v8_0.c:1127. No es una limitación del silicio.
LO QUE SOBREVIVE  la primera frase. PROVEN en el corpus: 0 coincidencias de mmVM_* en
         gca/gfx_8_0_d.h y gfx_8_1_d.h; 61 en gmc/gmc_8_2_d.h. Y es compatible con un
         modelo plano.
POR QUÉ NO SE RESUELVE COMPLETO  "no hay motor de recorrido" y "el nivel lo elige el
         software" son hechos DISTINTOS, y el documento los mezclaba. El segundo está
         resuelto (refutado). El primero no: la ausencia de registros en el árbol de
         GCA no prueba que el ASIC no pueda recorrer — absence-of-registers es
         NOT_FOUND, no PROVEN_ABSENT.
ACCIÓN     024 §6 ya lo marca. El fichero DRIVER-MISSION-STATE.md no lleva la marca.
           Añadirla es escritura en fichero ajeno: acción F5, no hecha aquí.
```

## C-007 · `MASTER-RESEARCH-STATUS.md` de `00-INDICE/` se autodescribe mal

```
ESTADO   RESOLVED por referencia (2026-10-01)
SEVERIDAD ALTA — un agente nuevo que entre por donde el propio repo le indica Leaná
           el estado de una línea que no es la que se trabaja.
```

```
CLAIM_A  00-INDICE/MASTER-RESEARCH-STATUS.md
         "Punto único de entrada del proyecto — No reconstruir el estado leyendo
          otros archivos."
         Última actualización declarada: 2026-09-25 · Versión 2.19
         Contenido: R-4B / D6 / C1 / telemetría — línea histórica de septiembre
CLAIM_B  docs/MASTER-RESEARCH-STATUS.md, 2026-10-01: la línea A (GFX8 RE + driver
         propio) no aparece en absoluto
```

```
CONFLICT  no es una contradicción de hechos: es una contradicción de ALCANCE que se
         presenta como(totalidad). El documento se declara único y es parcial.
MEDIDA    grep de rx550_drv, STAGE1, vm-invalidate, vmflush, COND_EXEC, GEN_PTEPDE
         sobre el fichero de 64085 B -> 0 coincidencias en los seis.
         64 KB de texto vigente-senalado, sobre una línea que fue cerrada hace 8 días.
RESOLUCIÓN  docs/MASTER-RESEARCH-STATUS.md pasa a ser el índice. El de 00-INDICE queda
         acotado por referencia desde aquí. NO SE BORRA: contiene el histórico R-4B/D6
         y nadie ha decidido que se discarded. §16.
PENDIENTE  la reversa — que 00-INDICE deje de autodescribirse como entrada única — es
         una edición de un fichero de 64 KB propiedad de otra sesión. No hecha.
         Registrada como acción, no como error mío.
```

## C-008 · `.write-lock/owner`: formato incompatible con su propio preflight

```
ESTADO   OPEN
SEVERIDAD MEDIA — no corrompe conocimiento, pero rompe el mecanismo que existe para
           evitar que dos sesiones sobrescriban el trabajo de otra. Ya costó dos
           pérdidas reales (COORDINACION.md:9-12).
```

```
CLAIM_A  COORDINACION.md:66-80 (PREFLIGHT §2) prescribe extraer el PID con
             grep -oE 'pid=[0-9]+' .write-lock/owner
CLAIM_B  COORDINACION.md:136-137 (Adquirir el turno) escribe el owner como
             echo "$$ $(date -Is)" > .write-lock/owner
         -> el formato que el protocolo genera NO contiene el token que el protocolo
            busca. El preflight no puede extraer el PID de un owner generado por él.
```

Medido el 2026-10-01, tres `owner` coexistiendo con tres formatos:

```
.write-lock/owner        52756 2026-10-01T10:40:08-03:00 takeover-human; alcance=tools/
                         -> grep 'pid=[0-9]+' NO casa. El preflight caería en
                            OWNER_NOT_RUNNING por un motivo que no es liveness.
.write-lock/findings/owner  PID=53801 2026-10-01T10:50:07-03:00
                         -> casa
.write-lock/pteflags/owner  54930 … scope=pteflags pid=54930
                         -> casa (por el segundo token)
```

```
CONFLICT  dos formatos del mismo fichero bajo el mismo protocolo. El que genera el
         protocolo no es el que lee el protocolo.
ALCANCE   todo Queue entry. Un owner vivo con el formato de la raíz se lee como
         OWNER_NOT_RUNNING -> REQUIRE HUMAN AUTHORIZATION. Falla hacia el lado
         conservador (no corrompe), así que no es peligroso: es inútil. Lo que sí es
         peligroso es lo que 021-write-lock §Reproducción ya demostró:
           mkdir .write-lock/findings  tiene ÉXITO con .write-lock ya creado.
         El cerrojo de ámbito no excluye a la raíz, y la raíz no excluye al ámbito.
         La colisión se pidió dos veces en la misma mañana y una vez más el índice
         numérico quedó duplicado.
ESTADO DE HOY  el owner de la raíz desapareció durante la ronda (estaba a las 11:01,
         no estaba a las 11:02). Nadie lo borró desde la sesión de documentación —que
         aún no había escrito nada—, así que no hay registro de quién lo liberó.
         Misma laguna que 021-write-lock §Evidencia ya había nombrado.
NO SE TOCA  021-write-lock §Corrección propone el guard exacto (comprobar el ancestro
         antes del mkdir) y declara que no lo aplica porque COORDINACION.md es ley
         operativa y eso requiere decisión humana. Sigue sin aplicarse. Es la acción
         más barata de arreglar y la más cara de no arreglar.
```

## C-010 · La clasificación del bloqueo de tres fronteras era incorrecta, y lo dice el propio árbol

```
ESTADO   RESOLVED (2026-10-01) — y esta vez la afirmación que se cae es MÍA
SEVERIDAD ALTA — iba a hacer perder horas a cualquier agente que hubiera leído mis
           documentos y decidido buscar una especificación que no existe
```

```
CLAIM_A  docs/OPEN-FRONTIERS.md, en F2b, F3 y en la tabla de NOT_DETERMINED, hasta las
         12:40 de hoy:
           "BLOQUEOS: BLOCKED_BY_CORPUS — falta la especificación. No es una laguna de
            análisis: evidence_search.py con --expect declarado es la vía, y ya se usó;
            la fuente no está en este repo"
         N1, N3 y N5 repetían el mismo encuadre

CLAIM_B  033-pm4-spec-gfx8-no-existe-y-el-encuadre.md (RESOLVES el BLOCKED de 022,
         023 y 029):
           La especificación primaria EXISTE, es accesible, tiene 637 páginas, y no
           contiene absolutamente nada de PM4. Contado, no supuesto: cero apariciones
           de PACKET3, PKT3, RELEASE_MEM, COND_EXEC, VM_INVALIDATE, INT_SEL, WRITE_AT,
           GRBM, mmCP
           Documento: Reference Guide — Graphics Core Next Architecture, Generation 3,
           rev. 1.0 (2015-03); la vigente en docs.amd.com es 1.1 (2016-08-01), doc 70645
           AMD nunca publicó la especificación del framing PM4 para GCN3
```

```
CONFLICT  No es un conflicto de hechos: es un conflicto de ESTADO DEL BLOQUEO, y es el
         más caro de esta ronda porque un estado de bloqueo equivocado dirige el trabajo
         al sitio equivocado
ALCANCE   DIRECTO sobre tres fronteras de docs/ y sobre N1, N3, N5:
            F2b  semántica de cada bit de PTE
            F3   significado de PAGE_TABLE_DEPTH 0 vs 1
            N1   qué garantiza el intervalo 0x20 de un WAIT_REG_MEM sin predicado
         Con lo que yo escribí, las tres decían "buscar el documento". Con lo que se ha
         medido, las tres dicen "el documento no existe: hay que medir el hardware"
         Y hay una cuarta que yo no tenía registrada y ahora sí:
            F3c  el payload de COND_EXEC, RELEASE_MEM, VM_INVALIDATE_RESPONSE e
                 INT_SEL=2. No era una frontera: era una frontera escondida dentro de
                 "falta la spec"
POR QUÉ YO ME EQUIVOQUÉ, que es la parte instructive
  Escribí "falta la especificación... la fuente no está en este repo" y lo presenté
  como una limitación del CORPUS. La confundí con el árbol de fuentes local. La
  especificación es un documento EXTERNO, y no estaba en el repo porque no está en
  ninguna parte: no es que esté fuera, es que AMD no la escribió
  Es exactamente el error que este repo ya cometió cuatro veces, en otra forma:
  declarar una ausencia sin haber buscado el universo correcto. evidence_search.py
  busca en el árbol; la spec estaba en docs.amd.com
VEREDICTO  CLAIM_B, con las dos versiones registradas
RESOLUCIÓN
  · C-010 en este registro, con mi afirmación y su fecha
  · F2b, F3 y la tabla de NOT_DETERMINED reclasificados a BLOCKED_BY_NEGATIVE_RESULT
  · F3c creada como frontera propia: las cuatro preguntas de payload, agrupadas, con el
    experimento ya diseñado en 022 §5 y la observación de que comparte bloqueo con F1
  · RE-29, RE-30, RE-31 en EVIDENCE-MATRIX. RE-30 cierra una ambigüedad que RE-08
    dejaba abierta (de qué se resta el 1), y RE-31 refuta una aserción de freedreno con
    un contraejemplo vivo
LO QUE NO SE HIZO  buscar más la especificación. Eso es lo que esta contradicción
  acaba de ahorrar
```

## C-011 · El emisor de PTE correcto es `sdma_v3_0`, no `sdma_v4_0`: `035` y `036` escriben un PTE de más

```
ESTADO   RESOLVED a favor de `sdma_v3_0`  ·  SEVERIDAD MUY ALTA
         035 y 036 ya están IMPLEMENTADOS en `rx550_pm4.c`. Un driver propio que
         copie ese código escribe UN PTE POR ENCIMA del final del rango pedido, en el
         ASIC real. Es corrupción silenciosa de memoria, no un error de documentación
ARBITRAJE   el kernel en ejecución, otra vez, y con la MISMA disciplina que zanjó C-009
```

```
CLAIM_A  035-correccion-ptepde-es-polaris12.md  ·  036 (que lo implementa)
              "023 leyó el fichero equivocado: sdma_v3_0.c es Tonga/CIK, no Polaris12.
               El fichero del ASIC de este proyecto es sdma_v4_0.c"
              de ahí: SDMA_OP_PTEPDE, y sobre todo  último dword = `count - 1`
              036 lo pone en el driver propio:
                RX550_SDMA_OP_PTEPDE        12   vega10_sdma_pkt_open.h:37
                RX550_SDMA_PTEPDE_DW        10   sdma_v4_0.c:1649-1658
                rx550_pm4.c  emits 10 dwords: hdr, pe[2], flags[2], addr[2], incr, 0, count-1

CLAIM_B  la ruta de descubrimiento de AMDGPU, en el corpus, leída entera
              vi.c:2107-2113   case CHIP_POLARIS12:
                                   amdgpu_device_ip_block_add(adev, &sdma_v3_1_ip_block);
              sdma_v3_0.c:1693-1700
                                 const struct amdgpu_ip_block_version sdma_v3_1_ip_block = {
                                     .type  = AMD_IP_BLOCK_TYPE_SDMA,
                                     .major = 3, .minor = 1, .rev = 0,
                                     .funcs = &sdma_v3_0_ip_funcs,     <-- HERE
                                 };
              sdma_v3_0.c:1112  amdgpu_sdma_set_vm_pte_scheds(adev, &sdma_v3_0_vm_pte_funcs);
              sdma_v3_0.c        .set_pte_pde = sdma_v3_0_vm_set_pte_pde
              sdma_v3_0.c        ib->ptr[ib->length_dw++] = count; /* number of entries */
                                               ^^^^ SIN el menos uno
  El bloque se LLAMA v3_1 pero su .funcs es el de v3_0. No hay ambigüedad: la struct
  completa dice `.funcs = &sdma_v3_0_ip_funcs`, y ese es el único camino de código
```

**El árbitro, y es el mismo patrón que zanjó `C-009`: preguntarle a la máquina.**

```console
$ journalctl -k -b --no-pager | grep "detected ip block number"
oct 01 05:49:05 amdgpu 0000:01:00.0: detected ip block number 4 <sdma_v3_1_0> (sdma_v3_0)
```

El formato del mensaje es `"detected ip block number %d <%s_v%d_%d_%d> (%s)
"`
(`amdgpu_ip.c:241-245`), así que se **decodifica**, no se adivina:

```
  4        num_ip_blocks
  sdma     ip_block_name(tipo)
  3 1 0    major.minor.rev
  sdma_v3_0  funcs->name
```

`SDMA0_HWIP = 3.1.0`, y el nombre de las funciones es **`sdma_v3_0`**. El hardware de esta
máquina ejecuta el emisor `sdma_v3_0_vm_set_pte_pde`, que escribe `count`.

**Y un dato más, que es el que hace la contradicción tan difícil de detectar:** `sdma_v3_1_ip_block`
**no tiene fichero propio**. No existe `sdma_v3_1.c` en ningún corpus del repo, ni en 7.1.3
ni en 7.2.8. Es una *alias* de v3_0 declarada en el mismo `sdma_v3_0.c`, línea 1693. Un barrido
por nombres de fichero —que es lo que hizo `023`— encuentra `sdma_v3_0.c` y no ve nada raro.
Un barrido por *bloques de ip* encuentra un `sdma_v3_1` y concluye que hay un emisor nuevo
que no está. Los dos barridos dan respuestas opuestas y los dos parecen razonados.

```
POR QUÉ 035 CAYÓ, y es más interesante que el hecho de que cayó
  Buscó "el fichero de SDMA de Polaris12" por NOMBRE. No existe uno propio: el ASIC usa
  sdma_v3_0.c. Cuando eso no aparece, la conclusión natural —y aquí la falsa— es que el
  fichero que se leyó es de otra generación
  ERROR_TYPE que declara 035: `ASIC_LEER_ANTES_DE_TIME`, "leer antes de tiempo". El nombre
  describe un ASIC leído antes de existir. El nombre real es el inverso: se conclusions que
  una ausencia en el barrido es evidencia de una generación distinta, sin haber
  comprobado que la ausencia tenga una causa. La ausencia SÍ tenía causa: un alias
  La regla que faltaba, y que 046Independientemente escribió para otro caso:
      COMPILE_GATE_BEFORE_TRACE_GATE -> aquí sería TRACE_GATE_BEFORE_ABSENCE_INFERENCE
      un identificador ausente en un barrido hay que seguir hasta su declaración antes de
      tratarlo como una entidad nueva
LO QUE 035 ACIERTA, y no se tira
  · la OFF-BY-ONE ES REAL, pero en la DIRECCIÓN OPUESTA a la que dice:
      sdma_v4_0.c:1658   count - 1     (Vega10/Polaris12 de la familia v4)
      sdma_v3_0.c:996    count         (CIK/Tonga, y TAMBIÉN Polaris12 por vía sdma_v3_1)
    La diferencia entre las dos implementaciones es REAL y está en el fuente. Lo que
    cambia es a cuál pertenece ESTE ASIC
  · el nombre del opcode: en sdma_v3_0.c es `SDMA_OP_GEN_PTEPDE`. El nombre que cita 035
    (`SDMA_OP_PTEPDE`) pertenece a la cabecera v4. Con la ruta correcta el nombre es el de
    `023`. Los dos nombres valen 12
  · el total de 10 dwords: correcto en AMBOS emisores. Eso sí sobrevive
  · y el diagnóstico de 023 fue bueno: 023 sí cierra que el productor es un paquete SDMA
    de 10 dwords. Falló en el nombre del fichero y en el argumento `count`
CONSECUENCIA, y hay que ser preciso sobre su gravedad
  `rx550_pm4.c` está ESCRITO y COMPILA con `count - 1`. El estado correcto es:
      la suite de 036 pasa porque compara contra la misma constante equivocada del .h
      75 checks verdes NO detectan el error: en 036 las dos puntas leen RX550_SDMA_PTEPDE_DW
      del mismo header. Es coherencia, no validación
      Y 036 declara haber hecho 5 mutaciones que la suite detecta. Ninguna de las cinco
      puede ser esta, porque la suite no tiene una segunda fuente con la que discrepar
  Lo que hace falta es un control NEGATIVO contra el emisor del driver de REFERENCIA en el
  corpus, que es lo que detectó que el ASIC es v3 y no v4
RESOLUCIÓN  CLAIM_B. `RX550_SDMA_PTEPDE_DW` y `count - 1` son CORRECTOS PARA VEGA10 y
           families v4, y FALSOS para este ASIC. El emisor de referencia de esta GPU
           escribe `count`
LO QUE NO SE HACE  editar 035 ni 036. Son de otra sesión, y 036 es implementación viva.
  COORDINACION.md:184: informa, no arregles
RESIDUO  grave. El error está en código compilable, no en un documento. Y sigue creciendo:
  los findings sin versionar llegaron a 28 en esta mañana, y este es el primero cuya
  NICIO correcta NO está en la documentación
```

---

## C-009 · `block_size` = 10 o 22: el kernel en ejecución zanja

```
ESTADO   RESOLVED a favor de 10, 2026-10-01, por arbitraje del host
SEVERIDAD MUY ALTA — es la cifra que gobierna el tamaño de la page table, el ancho del
           índice de PTE y dónde termina la GART. Un error aquí se propaga a todo lo
           que el driver propio asigne.
VERIFICADO CONTRA EL HOST EN EJECUCIÓN, no contra el árbol
```

```
CLAIM_A  RE-10 / gfx8vmgeom / 024-ya-corregido
              block_size = 10
              num_level = 1, root_level = AMDGPU_VM_PDB0
              cadena: amdgpu_vm.c:2424 tmp = roundup_pow_of_two(16777216) = 2^24
                      :2427 tmp = DIV_ROUND_UP(fls64(2^24)-1, 9) - 1 = DIV_ROUND_UP(24,9)-1 = 2
                      :2428 num_level = min(max_level=1, tmp=2) = 1
                      :2438 switch case 1 -> root_level = AMDGPU_VM_PDB0
                      :2454 block_size = amdgpu_vm_get_block_size(tmp = 2)
                               bits = ilog2(2) + 18 = 19 ; 2 <= 8 -> 19 - 9 = 10

CLAIM_B  030-page-walker-gfx8-2-niveles.md  (UNTRACKED, apareció esta mañana)
              "Y me equivoqué en block_size. Reporté 13/14/15. Es 22/23/24."
              root_level = AMDGPU_VM_PDB2
              VA[39:31] 6 bits índice de PDE · VA[30:9] 22 bits índice de PTE
              Lo escribe como CORRECCIÓN de un error previo
```

**El árbitro, y es el más fuerte disponible: el kernel que está corriendo ahora mismo.**

```console
$ journalctl -k -b --no-pager | grep "vm size is"
oct 01 05:49:05 kalm kernel: amdgpu 0000:01:00.0: vm size is 64 GB, 2 levels,
                                    block size is 10-bit, fragment size is 9-bit
```

Ese es el `dev_info` de `amdgpu_vm.c:2463` de ESTA máquina, con ESTE kernel
(`7.1.3-200.nobara.fc44`), arrancado HOY. Imprime **`block size is 10-bit`**.
`CLAIM_A` coincide con el hardware; `CLAIM_B` no.

```
POR QUÉ B FALLA, y es el mismo error por tercera vez
  El parámetro de amdgpu_vm_get_block_size se llama `vm_size`, pero su uso real son
  PÁGINAS redondeadas a potencia de dos. Eso lo dice CLAIM_B, y es cierto.
  El error es qué valor tiene `tmp` en la línea 2454:
    CLAIM_B alimenta tmp = 2^24 = 16777216, que es roundup_pow_of_two(max_pfn), el
                    valor de ANTES de la línea 2427
    el código pasa tmp = 2, que es el valor de DESPUÉS
  get_block_size(2^24): bits = 24+18 = 42 ; 2^24 > 8 -> (42+3)/2 = 22   <-- el 22
  get_block_size(2)  : bits = 1+18  = 19 ; 2    <= 8 -> 19-9  = 10   <-- el 10
  tmp se reasigna en 2427. Barrido de 2424 a 2454: no hay más reasignaciones.
  Verificado en LOS DOS corpus:
    7.1.3  amdgpu_vm.c:2400-2465   7.2.8  amdgpu_vm.c:2400-2465   idéntico
SEGUNDA AFIRMACIÓN DE B, TAMBIÉN REFUTADA
  root_level = AMDGPU_VM_PDB2 para num_level = 1. El switch dice lo contrario:
    case 4 -> PDB3 · case 3 -> PDB2 · case 2 -> PDB1 · case 1 -> PDB0
  y el enum lo confirma: enum amdgpu_vm_level { PDB3=0, PDB2=1, PDB1=2, PDB0=3, PTB=4 }
  (amdgpu_vm.h:191-197). num_level = 1 -> PDB0. Para llegar a PDB2 haría falta
  num_level = 3.
LO QUE B ACIERTA, y queda registrado aparte como PROVEN
  El título dice "el page walker es de 2 niveles" y ESO es cierto: num_level = 1 se
  imprime como num_level + 1 = 2, y el walk es PDB + PTB. El finding no lo contradice;
  lo que cambia es la aritmética
  Y el predicado de no-huge-pages es real y está bien citado para su corpus declarado:
    rx550-upstream-7.2.8/.../amdgpu_vm_pt.c:825-832
      } else if (adev->asic_type < CHIP_VEGA10 && (flags & AMDGPU_PTE_VALID)) {
              /* No huge page support before GMC v9 */
              if (cursor.level != AMDGPU_VM_PTB) { ... continue; }
    En 7.1.3 el mismo predicado está en la línea 840. La cita es correcta para 7.2.8,
    que es el CORPUS que el finding declara
  -> RE-28: antes de GMC v9 el driver se NIEGA a usar un nivel no-hoja como hoja. No hay
     descriptores de bloque en operación normal, y PAGE_TABLE_BLOCK_SIZE no se usa como
     tamaño de bloque. Eso RECORTA el espacio de diseño del driver propio
NOTA SOBRE LA CRONOLOGÍA DE LOS ERRORES, que es lo que hay que aprender
  13/14/15  de 019 y 024  -> feed de vm_size        -> corregido, TIPO A
  22/23/24  de 030-walker -> feed de tmp pre-2427  -> refractado HOY, TIPO B
  10        de gfx8vmgeom -> feed de tmp post-2427 -> CORRECTO, confirmado por el host
  Los tres leen la MISMA función. Dos se equivocan de argumento y uno no. La diferencia
  entre el correcto y los incorrectos no es el análisis: es que la cadena se comprobó
  contra la línea que el hardware imprimió. gfx8vmgeom lo hace explícito en su salida
  ("el contraste con el host") y por eso su número sobrevivió a dos intentos de
  corrección posteriores
RESOLUCIÓN  RE-10 se mantiene. `block_size = 10`, `num_level = 1`, `root_level = PDB0`
RESIDUO  `030-page-walker-gfx8-2-niveles.md` es UNTRACKED y sigue en el disco con sus
  cifras. Es de otra sesión. Informar, no arreglar (COORDINACION.md:184). La tabla
  `FINDINGS-INDEX.md` lo marca como refutado en este punto
```

---

## Contradicciones registradas y no resueltas, en una línea

| ID | Asunto | Estado | Quién puede resolverla |
|---|---|---|---|
| C-002 | `29⁄9⁄26.md:169` sin marca de enmienda | `OPEN` | sesión autora, nota de precedencia (F6) |
| C-008 | formato de `owner` ≠ regex del preflight; ámbitos no excluyentes | `OPEN` | decisión humana sobre `COORDINACION.md` |
| C-009 | `block_size` 10 vs 22 | `RESOLVED` a favor de 10 | resuelto por el `dev_info` del kernel en ejecución |
| C-010 | "falta la spec PM4" como bloqueo pendiente | `RESOLVED` | la spec existe y se contó: no contiene PM4. **La afirmación que se cae es de este trabajo** |
| C-011 | `sdma_v3_0` (real) vs `sdma_v4_0` (publicado) para el emisor de PTE | `RESOLVED` a favor de `v3_0` | `vi.c:2113` + `sdma_v3_0.c:1699` + el `dev_info` del host. **Y está implementado en código compilable** |
| C-006 | `DRIVER-MISSION-STATE.md` sin la marca de `024` | `PARTIALLY_RESOLVED` | sesión autora (F5) |
| C-007 | `00-INDICE/MASTER-RESEARCH-STATUS.md` se autodescribe entrada única | `OPEN` | decisión sobre 64 KB de histórico |
| — | 87 findings y 6 herramientas sin versionar | `UNTRACKED_EVIDENCE` | `git add` por las sesiones propietarias |
| — | 24 índices de finding duplicados + huecos en la numeración (004) | `INVALID` | renombrado por las sesiones autoras |

---

## C-012 · Dos índices operacionales con el mismo nombre, y el censo abre el que no es el mío

```
ESTADO    **NOT_DETERMINED**, y no es arbitrable con lo que hay en el árbol.
          Es una decisión de coordinación, no un hecho técnico
ABIERTO POR  `tools/drift.py --toolkit`, que descubrió que el registro de
          herramientas conoce 2 directorios y el repositorio tiene 7

QUÉ SE MIDIO
  7 directorios con guiones, 5 de ellos con CERO scripts documentados
  76 scripts sin entrada TL-, en total
      revkit                                 18 guiones   5928 lineas   0 documentados
      01-AUDITORIA/FASE-C1-RUNTIME-PREFLIGHT  17          10836        0
      08-ARQUITECTURA/tools/btfq              7           1744         0
      06-INGENIERIA-INVERSA/corpus            5            694         0
      01-AUDITORIA/DOCUMENTATION-ROUTER/...   3           1195         0

  Eso, por sí solo, no es una contradicción: es trabajo sin documentar.

LA CONTRADICCIÓN PROPIAMENTE DITA, y es MÍA
  existe un censo documental DISEÑADO Y CONGELADO en
  `01-AUDITORIA/DOCUMENTATION-ROUTER/DOCUMENTATION-INVENTORY-ROUTING.tsv`
  1576 filas, con `ROUTING-SCHEMA.md` y un `KNOWLEDGE-POLICY` en estado
  `DESIGN_FROZEN` que dice que las discrepancias se registran como CONTRADICTION
  de mis 15 ficheros de `docs/`, en ese censo hay  CERO
  y los dos únicos «matches» aparentes son OTROS ficheros con el MISMO NOMBRE:
      docs/MASTER-RESEARCH-STATUS.md   ->  la fila es 00-INDICE/MASTER-RESEARCH-STATUS.md
      docs/EVIDENCE-MATRIX.md          ->  la fila es 01-AUDITORIA/AUDIT-001/EVIDENCE-MATRIX.md
  es decir: la colisión de nombre es lo que hace que mi documentación sea INALCANZABLE
  por el router del proyecto, y la colisión la creé yo

  9 de mis 15 ficheros de `docs/` colisionan por nombre con otro fichero del árbol:
      CONTRADICTIONS.md  CURRENT-STATE.md  DECISIONS.md  EVIDENCE-MATRIX.md
      KNOWLEDGE-GRAPH.md  MASTER-RESEARCH-STATUS.md  NEGATIVE-RESULTS.md
      OPEN-FRONTIERS.md  TOOLS-STATUS.md
  y el caso peor es el índice:
      00-INDICE/MASTER-RESEARCH-STATUS.md   64085 bytes   2026-09-28
      docs/MASTER-RESEARCH-STATUS.md        49067 bytes   2026-10-02
      contenido IDENTICO? NO

LAS DOS VERSIONES, y las dos están vivas
  lo que hace el registro, cuando alguien pide MASTER-RESEARCH-STATUS, es abrir el
  de `00-INDICE/`, de 64 kB, congelado el 28-09
  lo que está pasando hoy es que OTRA sesión está escribiendo un SEGUNDO índice en la
  RAÍZ, y esos ficheros se modificaron HOY:
      ./TOOLS-STATUS.md      3657 bytes  2026-10-02   (docs/: 112414)
      ./OPEN-FRONTIERS.md   22353 bytes  2026-10-02   (docs/:  44722)
      ./EVIDENCE-MATRIX.md  13847 bytes  2026-10-02   (docs/: 105761)
      ./KNOWLEDGE-GRAPH.md    618 bytes  2026-10-02   (docs/:  18762)
      ./CONTRADICTIONS.md     816 bytes  2026-10-02   (docs/:  32710)
      ./CURRENT-STATE.md     1010 bytes  2026-10-02   (docs/:  11319)
  o sea: DOS índices operacionales, escritos en paralelo, con seis nombres
  idénticos, y ninguna de las dos partes aware de la otra

POR QUÉ NO SE ARBITRA AQUÍ, y hay que decirlo con claridad
  no hay forma de arbitrarlo leyendo.  Las dos partes:
      · la de `docs/` tiene 41 entradas TL-, 50 claims, 11 contradicciones y nueve
        herramientas con self-test y 135 checks
      · la de raíz se está escribiendo ahora mismo, es más pequeña en todo, y es más
        nueva en todo
  «más nueva» no es un argumento: la de raíz se modifica más porque se está
  escribiendo, no porque sea más correcta.  Y «más grande» tampoco: el tamaño mide
  quanto, no si
  ARBITRARLO ES UNA DECISIÓN DE COORDINACIÓN ENTRE SESIONES, y
  `COORDINACION.md:184` es claro: informar, no arreglar.  Editar el TSV de otra
  sesión sería exactamente el `OwnedError` que ese fichero prohíbe

LO QUE ESTA SESIÓN HACE, Y ES LO ÚNICO QUE LE TOCA
  1 · registra la contradicción, que es lo que el `KNOWLEDGE-POLICY` congelado pide
  2 · desambigua DENTRO de sus propios ficheros, que sí son suyos
  3 · escribe la línea exacta que falta, sin aplicarla

LA LÍNEA QUE FALTA, y NO SE APLICA
  en `DOCUMENTATION-INVENTORY-ROUTING.tsv` no hay ninguna fila para `docs/`.  Con el
  esquema de las 12 columnas que ya usan, haría falta UNA por fichero, y el mínimo
  imprescindible para que el router no abra el documento equivocado es:
      docs/MASTER-RESEARCH-STATUS.md  md  STATUS  CURRENT  SECONDARY  PROJECT_STATUS
  más `RELATIONSHIPS` apuntando a `00-INDICE/MASTER-RESEARCH-STATUS.md`, para que la
  relación quede explícita en vez de deducida por un nombre coincidente
  QUÉ NO SE HACE: no se edita el TSV, no se renombra nada mío, y no se decide cuál
  de los dos índices sobrevive.  Las tres son decisiones de una persona o de una
  sesión con la ley operativa

UNA COSA QUE ESTO ENSEÑA, y que ya se había visto
  la colisión de nombre no es un problema de este documento: es la misma clase que
  `UNIDENTIFIABLE` en `citations.py`, y la misma que `RE-47`.  Un nombre que no
  identifica un fichero convierte una referencia bienintencionada en una referencia
  ambigua, y el lector que la resuelve no sabe que había una elección
  aquí la resolución es fácil porque las dos versiones están una al lado de la otra.
  En el censo, con 1576 filas, no lo es

Y LO QUE ESTO NO TOCA
  nada de lo que hay en el árbol de corpus, ni los drivers de ninguna línea, ni los
  8 cerrojos de otras sesiones.  Es un hueco de nomenclatura y de registro, y se
  arregla con una fila y una decisión

---

## Actualización de `C-011` — la mitad del `.c` queda resuelta el 2026-10-02

```
QUÉ DECÍA C-011
  el emisor de PTE correcto es `sdma_v3_0`, no `sdma_v4_0`.  `035` y `036` escribían
  un PTE de más.  Un driver propio que copiara ese código escribiría UN PTE POR
  ENCIMA del final del rango, en el ASIC real: corrupción silenciosa de memoria
QUÉ SIGUE VIGENTE
  la primera mitad: este ASIC despacha `sdma_v3_0`, y `rx550_pm4.c` ya NO llama a la
  ruta de `sdma_v4_0`.  `sdma_v3_0.c` es el fichero correcto.  Eso no se movió
QUÉ QUEDA RESUELTO, y cuándo
  2026-10-02.  `rx550_pm4.c:280-298` escribe `count`, no `count - 1`, y la función
  entera replica `sdma_v3_0.c:986-996` dword a dword y en orden.  Medido en `RE-52`
  y en `F3d`
  además `07-DRIVER/kernel/rx550_pm4.h` lo declara en su propio comentario, con el
  arbitraje escrito, así que la corrección está en el código y no sólo en la
  documentación de este proyecto
QUÉ NO SE TOCA
  la fila de `C-011` no se borra ni se reescribe.  Existió el defecto, se detectó
  tarde, y esa historia es parte del resultado: dice que una suite de 181 checks
  verde puede no ver un error de un byte en el argumento de un emisor de DMA
  `revkit/PTEPDE-GFX8.md` hizo la pregunta que faltaba y la dejó escrita.  La
  respuesta está en `RE-52`, y ese fichero es de otra sesión y no se ha tocado: lo
  que corresponde es que quien lo escribió la incorpore
```

## C-013 · `always` de `WAIT_REG_MEM` no es inalcanzable: lo dije yo, y era falso

```
QUÉ DECÍA
  en `revkit/WAIT-REG-MEM-REAL.md` (commit 7b7df82) escribí que el campo
  `FUNCTION` ocupaba `[1:0]`, o sea dos bits, y que por tanto el valor
  `always` —que sería 4 o mayor— no cabía y por tanto era inalcanzable en
  GFX8. Lo presenté como corroboración sobre `DERIVATION`, corroborado dos
  commits después con un paquete real del anillo

QUÉ ES FALSO, EN LAS DOS PARTES
  1. `sid.h:398-406` define
        #define WAIT_REG_MEM_FUNCTION(x) ((x) << 0)
     con SIETE valores: 0 always, 1 <, 2 <=, 3 ==, 4 !=, 5 >=, 6 >.
     Son tres bits, no dos
  2. `always` es el valor 0, que se codifica sin problema. La razón que
     di —que no cabe en el campo— era falsa de partida

QUÉ SIGUE VIGENTE
  que GFX8 emite `FUNCTION(0)` y `FUNCTION(3)`, y solo eso, sigue siendo
  cierto, y ahora está además OBSERVED en un paquete real. Lo que cambia
  es la RAZÓN: no es que `always` no quepa, es que este driver no lo
  emite nunca. Que es una afirmación distinta y mucho más débil

POR QUÉ PASÓ
  leí `WAIT_REG_MEM_FUNCTION(x) ((x) << 0)` como si fuera un campo de dos
  bits porque era el número que esperaba, y construí encima una
  corroboración sobre un paquete real. El paquete real verificaba lo que
  yo ya había concluido, no lo que la macro dice. Un dato observado
  confirma la hipótesis que se puso a prueba; si el dato solo encaja con
  la hipótesis, no confirma nada

LA LECCIÓN OPERATIVA
  cuando un dato OBSERVED encaja con lo esperado, hay que comprobar que
  la expectativa venga de la fuente y no de la memoria. En este caso
  `sid.h:398` estaba a un `grep` de distancia y decía otra cosa

CÓMO SE RESUELVE
  2026-10-02. La afirmación está retirada de forma VISIBLE en
  `revkit/WAIT-REG-MEM-REAL.md`, con la macro correcta al lado y el
  comentario de que la corrección importa. No se borra la versión
  equivocada: un hallazgo que se retira en silencio vuelve a aparecer
  dentro de medio año

QUÉ NO SE TOCA
  la conclusión de que GFX8 no emite `always` sigue en pie y en
  `WAIT-REG-MEM.md`, con el mismo `STATE`
```

## C-014 · Dos ausencias afirmadas con un solo `grep` de un fichero

```
QUÉ DECÍA
  dos cosas, ambas en EV-17, ambas con su STATE puesto como si fueran
  mediciones:
  1. "GFX8 no emite nunca `always`"
  2. "`WAIT_REG_MEM_OPERATION` NO está definido para GFX8, NOT_IN_CORPUS"
QUÉ ES FALSO
  1. `gfx_v8_0.c:6201` emite `WAIT_REG_MEM_FUNCTION(0) /* always */`, dentro
     de `gfx_v8_0_ring_emit_vm_flush`. El comentario del driver dice para
     qué: "wait for the invalidate to complete"
  2. está en `amdgpu/vid.h:180`, que `gfx_v8_0.c` incluye en su línea 35:
        #define WAIT_REG_MEM_OPERATION(x)  ((x) << 6)
     El comentario da `0 wait_reg_mem`, `1 wr_wait_wr_reg`, y coinciden con
     los dos valores que el driver usa. Además `soc15d.h:191`, `cikd.h:307`
     y `nvd.h:180` dicen lo mismo

QUÉ NO SE TOCA
  lo de C-013 sigue en pie en su mitad buena: `always` es el valor 0 y es
  codificable, `sid.h:398-406` da siete valores en tres bits. Lo que se
  retira es la conclusión de que GFX8 no lo emite nunca, que era lo único
  que quedaba en pie de la corroboración que construí en C-013

POR QUÉ PASÓ, Y QUE ES LO NUEVO
  las dos son la misma regla, la REGLA CRÍTICA DE LECTURA COMPLETA del
  AGENTS.md: "Una lectura parcial jamás puede sustentar una ausencia"
  1. para decir que no lo emitía: `grep -n WAIT_REG_MEM_FUNCTION gfx_v8_0.c`
     da tres líneas, una es el `always`
  2. para decir que no estaba definido: `grep -rn` de la definición sobre
     TODO el corpus da cinco ficheros. Yo miré uno solo: el que ya sabía
     que no existía, `gfx_8_1_pkt.h`
  El caso 2 es el grave, porque el `NOT_IN_CORPUS` iba dentro de una fila de
  evidencia con su STATE. Una ausencia afirmada con la seguridad de una
  medición. Y hay un agravante: ya lo había hecho una vez en esta sesión,
  con los punteros del anillo (retirada la afirmación de que eran MMIO), y
  en aquel caso también busqué donde sabía que no estaba

LO QUE SE APRENDE, Y ES OPERATIVO
    la diferencia entre "no está" y "no lo he buscado donde toca" no la da
  la confianza del que escribe, la da el número de sitios recorridos. El
  fallo no es de criterio, es de alcance de búsqueda
  la regla que sale: una afirmación de ausencia lleva el comando de
  búsqueda en la propia fila, con el alcance, para que otro pueda repetirla
  y ver que se ha recorrido lo mismo. Sin eso, `NOT_IN_CORPUS` y
  `PROVEN_ABSENT` son la misma palabra escrita con distinta confianza

QUÉ RESOLVIÓ ELLO, ADEMÁS DE LAS DOS RETIRADAS
  mirar el segundo emisor destapó EV-25: hay DOS formas de `WAIT_REG_MEM`
  en GFX8, y la que importa para el invalidate es la que no se estaba
  mirando. La del HDP flush tiene control `0x143`; la del vm flush tiene
  control CERO, con `FUNCTION(0) always` y `ref`/`mask` a cero
  eso responde a la pregunta que AGENTS.md llevaba abierta como
  `hardware trigger de always: NO_DETERMINED`. No es un trigger: es una
  espera. El hardware no dispara nada; el driver deja un paquete que no
  retorna hasta que `VM_INVALIDATE_REQUEST` ha cambiado

Y DE PASO, UNA CONCILIACIÓN ENTRE SESIONES
  finding 106 de otra sesión (`daec702`) concluye que
  `VM_INVALIDATE_REQUEST` no tiene campo `FUNCTION`. Es CORRECTO, y queda
  corroborado en la generación que le toca a GFX8: `gfx_v8_0.c` incluye
  `gmc_8_2_d.h` y `gmc_8_2_sh_mask.h`, donde los únicos campos de
  `VM_INVALIDATE_REQUEST` son `INVALIDATE_DOMAIN_0..15`, shifts 0 a 15.
  Ninguno por encima del bit 15, en las cinco generaciones de GMC

  NO hay contradicción entre 106 y EV-17, porque son dos `FUNCTION`
  distintos: uno es un campo de un opcode de PM4 (`sid.h:398`), el otro
  sería un registro MMIO. se habían confundido durante semanas. Lo que hace
  falta no era elegir uno, era decir sobre cuál se estaba hablando

CÓMO SE RESUELVE
  2026-10-02. Las dos afirmaciones están retiradas de forma VISIBLE dentro
  de EV-17, con el comando de búsqueda que las refuta al lado. No se borran:
  una afirmación retirada en silencio reaparece. Y EV-25 queda como fila
  nueva con lo que se encontró al mirar el emisor que faltaba
```
