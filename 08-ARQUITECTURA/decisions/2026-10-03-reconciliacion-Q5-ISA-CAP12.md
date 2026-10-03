# Reconciliación del nodo Q5-ISA-CAP12 — 2026-10-03

AUTORIA=global-coordinator · WORK_CLASS=reconciliación · WRITE_EXECUTION=2 ficheros nuevos
RUNTIME=NOT_RUN · GPU=INTACTA · SIN_SUDO · SIN_COMMITS · LOCKS=q5-isacap12, recon-q5b

Este documento **no cierra** la frontera Q5. Registra lo que el coordinador verificó por sí
mismo sobre el resultado de un worker, y separa tres cosas que en este proyecto se confunden:
lo que se **midió**, lo que el worker **afirmó**, y lo que el coordinador **no pudo**
corroborar. Incluye **un error del worker** y **un error mío**, porque los dos son del mismo
tipo y ese tipo ya ha costado dinero aquí tres veces.

---

## 1. Estado del nodo

```
NODE_ID        Q5-ISA-CAP12
WORKER         sesion-missing
DESPACHADO POR global-coordinator, bajo cerrojo .write-lock/q5-isacap12
CERRADO POR    RESOLVED_WITH_RESIDUAL_UNIVERSE
ACEPTADO POR   global-coordinator = SI (verificado, no heredado), CON UNA CORRECCION
HIPOTESIS      H2 COBERTURA PARCIAL  — no H1, no H3
```

Artefactos, con hash **medido por el coordinador** y no copiado del informe del worker:

```
08-ARQUITECTURA/artifacts/Q5-ISA-CAP12/
  q5-isa-cap12.md        51949 B   d3c8ad7fade0e7605830b7f3b2c647cebd2ed9cf5addce44fb4a0dcf0c31eee3
  cap12.txt             350492 B   877b92024e43a8d7d74863ffe6873d293e23a6edf961f77dcd274b95920c8df8
  cap12-opcodes-all.tsv  19341 B   a42d1538ffa900deac13d0e666f63e73edd1c66fbc705440573f48d94da15d88
  coverage-216.tsv       15287 B   175ce7daf9a0e5153e1b414e99aaff1ad4430359e5e1f94081093c06219385e5
```

## 2. Verificación independiente de lo load-bearing

Siete afirmaciones del worker comprobadas por separado. Las siete se sostienen en el fondo;
**una tiene mal una cifra**.

| # | Afirmación del worker | Verificación del coordinador | Estado |
|---|---|---|---|
| V1 | Los dos hashes de entrada coinciden | `8e49a376…2853` y `fa6b8ff9…d63`, recomputados después del nodo | CORROBORADO |
| V2 | Cuadre 183 COINCIDE + 2 DIFIERE + 31 AUSENTE = 216 | recountado desde `coverage-216.tsv`: `183 / 2 / 31`, suma `216` | CORROBORADO |
| V3 | 185 con valor + 31 ausentes = 216 | `185 = 183 + 2`; `185 + 31 = 216` | CORROBORADO |
| V4 | **28** de las 31 ausencias son `S_BUFFER_ATOMIC_*` | `grep -c '^#define SQ_S_BUFFER_ATOMIC_'` en el header = **26**; recountado sobre el TSV = **26** | **CORREGIDA: 26, no 28** |
| V5 | `S_CMP_NE_U64` no está en el header | `grep -c 'SQ_S_CMP_NE_U64'` = `0` | CORROBORADO |
| V6 | `S_WAKEUP` tiene **0 apariciones en las 348 páginas** | extracción propia del libro entero: `pdftotext rc=0`, 17667 líneas, `grep -c S_WAKEUP` = `0` | CORROBORADO |
| V7 | El cuadre tiene dos caminos independientes | TSV y tabla markdown | CORROBORADO |

### 2.1 La corrección V4, y por qué no cambia el estado

El worker escribió **28**. Su propia evidencia lo desmiente: los rangos que cita
(`0x40`–`0x4c` y `0x60`–`0x6c`) son 13 + 13 = **26**. Los 26 nombres existen todos en el
header y los 26 son los que el TSV marca `AUSENTE_DE_CH12`. Los otros cinco ausentes son:

```
SQ_S_MOV_REGRD_B32   SQ_S_MOV_FED_B32   SQ_S_GETREG_REGRD_B32
SQ_S_WAKEUP          SQ_S_RFE_RESTORE_B64
```

Es un **error de aritmética sobre un rango que el propio worker ya habia enumerado**. No
toca H2, ni el cuadre, ni la conclusión operativa. Se corrige el número y se deja el
método: el hallazgo structural que el worker sí sostiene —que el hueco **no** es disperso sino
un bloque de 26 atomicos SMEM mas cinco instrucciones concretas— sobrevive intacto.

### 2.2 El error mio, que es del mismo tipo que este

Mi primera comprobacion de V4 dio **`0` `S_BUFFER_ATOMIC_` ausentes**. Era falso. No era
drift ni corrupcion: yo filtre por `$4 == "AUSENTE"` y el token real del TSV es
**`AUSENTE_DE_CH12`**. Mi instrumento no encontro nada y yo nearly leo ese cero como
"el bloque de atomicos no esta ausente".

Es la tercera vez en este proyecto que un filtro mal escrito produce un cero que parece un
hecho. Las otras dos estan escritas en el propio repo: finding **109** ("ambito de variable,
un bug de la herramienta que cazaba mis conclusiones"), el **967** (el detector que informaba
0 colisiones porque su estructura las hacia no representables), y ahora esto. **Un cero
producido por un instrumento no es un cero del mundo.** Se registra aqui para que el
siguiente no lo lea como dato.

---

## 3. HALLAZGO PROPIO DEL COORDINADOR — el mayor del nodo, y no lo yieldó el worker

La afirmacion de origen es `RESEARCH/polaris12xl/LIBRARY-CATALOG.md:630`:

```
M-01 | RX550-INVESTIGACION/05-FUENTES-PDF/gcn3-isa.pdf
     | "AMD Graphics Core Next, Generation 3 ISA, 348 pp ... GFX8 = GCN 3. Es la ISA del objetivo"
```

El documento, leido entero y no de indice:

```
EXTRACCION   pdftotext -layout gcn3-isa.pdf   rc=0   stderr vacio   17667 lineas
PORTADA      "Graphics Core Next Architecture, Generation 3" · August 2016 · Revision 1.1
AUTODENOMINACION  "AMD Volcanic Islands Series"  x5

OCURRENCIAS EN LAS 348 PAGINAS
  GFX8              0        GFX9       0        Polaris     0
  POLARIS           0        VEGA       0        Lexa        0
  Baffin            0        GCN3       0        GCN       49
```

**La fuente primaria no menciona GFX8 ni Polaris ni Lexa ni Baffin, ni una sola vez.** Se
autodenomina "Volcanic Islands Series". Por tanto la frase del catalogo *"GFX8 = GCN 3. Es la ISA
del objetivo"* **no esta en el documento que el catalogo cita**, y no es un hecho: es una
atribucion. `GFX8` y `Volcanic Islands` son dos*nombres* de la misma generacion en dos
vocabularios —el del driver y el de la/documentacion— y el puente entre ellos no es la fuente
primaria. Es el driver.

Esto **degrada** el encuadre del nodo, no su resultado: las 185 coincidencias son
consistencia entre dos documentos, y eso queda dicho en el artefacto. Lo que cambia es que
la premisa del catalogo queda marcada como `CATALOGO_NO_EVIDENCIA` y ya no puede usarse sin
la cadena que va en §4.

---

## 4. El eslabon que faltaba, medido — y es software, no silicio

El ataque de §3 abre una pregunta con discriminante claro: *¿que en la pila de esta maquina
afirma que el ASIC ejecuta la GFX8?* Se responde leyendo el driver que corre en este host:

```
1  /sys/bus/pci/devices/0000:01:00.0/device              = 0x699f        (medido)
2  amdgpu_drv.c:2041   {0x1002, 0x699F, PCI_ANY_ID, PCI_ANY_ID, 0, 0, CHIP_POLARIS12}
3  vi.c:2106-2109      case CHIP_POLARIS12:
                         amdgpu_device_ip_block_add(adev, &gfx_v8_0_ip_block);
                         amdgpu_device_ip_block_add(adev, &gmc_v8_1_ip_block);
4  gfx_v8_0.c:50      #include "gca/gfx_8_0_enum.h"
5  gfx_8_0_enum.h     216 entradas SQ_S_*          sha fa6b8ff9…d63

sha256  amdgpu_drv.c 07a1fff4f6cee85d7df6
        vi.c         c554b770b71edb8476f2
        gfx_v8_0.c   2427f5b5fcb44778a76d
CORPUS   RESEARCH/working/linux-7.1.3   (las 4 copias de sid.h y de gfx_8_0_enum.h son
                                        byte-identicas: working, baseline, kernelbuild, upstream-7.2.8)
```

La cadena esta **cerrada y medida**. Pero hay que leerla bien, porque es donde el proyecto se
equivoca mas a menudo:

```
LO QUE SI DEMUESTRA   el driver que corre en esta maquina asigna gfx_v8_0 a CHIP_POLARIS12,
                      y gfx_v8_0 usa gfx_8_0_enum.h. La tabla que el proyecto llama
                      "GFX8" es la que este ASIC ejecuta, segun el driver.
LO QUE NO DEMUESTRA   que AMD diga que Polaris12 es GCN3. No lo dice en ningun sitio del
                      corpus medido. El enlace GCN3-ISA -> GFX8 es una INFERENCIA cuyo
                      unico puente es el nombre interno del driver.
ESTADO DE LA INFERENCIA  CORROBORADO_POR_CADENA, NO PROVEN. No es nada del silicio: es
                      IMPLEMENTATION_IS_NOT_AUTHORITY aplicado al propio driver del proyecto.
```

El paso 3 aporta además, de regalo y por la misma lectura, el `gmc_v8_1_ip_block` que el
finding **087** nombraba "SF GMC 8.1": aqui esta su asignacion, con linea.

---

## 5. CONTRADICCIONES — como queda cada una

### 5.1 CONTRAD-Q5-AUSENCIA-TABLAS — sigue VIVA, y ahora con un tercer input medido

```
AFIRMA   08-ARQUITECTURA/designs/DRIVER-MISSION-STATE.md:136-138
         "4 de las 5 tablas de opcode GFX8 no estan en el corpus ... NOT_AVAILABLE"
         sha256 21f8ca0e346ea271494b050bd5b9ef4e4c0370f604e9da3baf25c0dd9c9a661b  INTACTO
REFUTA   06-INGENIERIA-INVERSA/findings/968-q5-universo-de-tablas-gfx8.md
         sha256 f46e67e251c0295545d2845893e2e009467e521db7dcfd56d23c0d544e14f8d2  INTACTO
AMBOS    re-verificados despues del nodo. Ninguno modificado. No hay ganador.
```

Donde el tercer input **apoya a AFIRMA**, y es un punto verificable, no una impresion:

> Para las familias **escalares y SMEM no existe tabla de opcode**. El cap. 12 trae 5 tablas
> tituladas *"Instructions for the Opcode Field"*, y son **solo** DS/LDS, MUBUF, MTBUF, MIMG y
> FLAT. Para SOP1/SOP2/SOPK/SOPC/SOPP/SMEM el valor viaja en **187 lineas aisladas** del tipo
> `Microcode <FMT> Opcode N (hex)`. La forma "4 de las 5 tablas" no aparece en esta fuente.

Donde **apoya a REFUTA**, en otro punto:

> La correspondencia existe y es medible para 185/216, y aun asi **no cubre el bloque de 26
> atomicos SMEM**. Confirma la consecuencia que ya estaba escrita: la tabla que "faltaba"
> tampoco resolvia.

Y lo que **no** apoya a ninguno: la existencia de "las 5 tablas" segun las define el 968
(subconjuntos por prefijo — criterio de *definicion*, distinto del criterio de *seccion del
documento*), ni la mitad de "campos de operando y registro", que no era la pregunta.

### 5.2 CONTRADICION NUEVA — el catalogo afirma una atribucion que su fuente no contiene

```
CONTRADICTION_ID     CONTRAD-Q5-GFX8-ES-GCN3
AFIRMA               RESEARCH/polaris12xl/LIBRARY-CATALOG.md:630
                     "GFX8 = GCN 3. Es la ISA del objetivo"
MEDIDO               la fuente citada, leida entera, contiene 0 ocurrencias de
                     GFX8 / GFX9 / Polaris / Lexa / Baffin, y 5 de "Volcanic Islands"
MEDIDO               el puente existe y es el driver: amdgpu_drv.c:2041 -> vi.c:2106-2109
                     -> gfx_v8_0.c:50
RESOLUCION           NO HAY. La afirmacion del catalogo queda marcada
                     CATALOGO_NO_EVIDENCIA. No se modifica el catalogo: registrar la
                     contradiccion con las dos fuentes es lo que corresponde.
LO QUE NO SE HACE    no se elige un ganador, no se reescribe LIBRARY-CATALOG.md, y no se
                     declara que GCN3-ISA sea la ISA del ASIC por el hecho de que el
                     proyecto la catalogo.
```

---

## 6. Estado que cambia, y estado que no

```
Q5-CORPUS-UNIVERSE       RESOLVED_WITH_RESIDUAL_UNIVERSE   (sin cambio)
Q5-ISA-CAP12             RESOLVED_WITH_RESIDUAL_UNIVERSE   NUEVO, H2 COBERTURA PARCIAL
CONTRAD-Q5-AUSENCIA-TABLAS   VIVA, con tercer input medido, sin ganador
CONTRAD-Q5-GFX8-ES-GCN3      VIVA, NUEVA
CATALOGO_M-01                NO_RESUELVE dentro del root: la ruta citada no existe ahi.
                              El PDF real vive en ~/Descargas, sin versionar, con el arbol
                              de origen sin tocarse desde 2026-09-27. OBSERVADO, con hash.
DEPENDENCIA_RAIZ_ACTIVA      El input de este nodo esta FUERA del arbol activo. No se copio
                              al root: son 2,75 MB, serian el primer PDF del repo, y esa es
                              una decision estructural que no es mia.
```

Cobertura medida, que es el numero que sobrevivira a este documento:

```
216  SQ_S_* en gfx_8_0_enum.h
185  con valor en el cap. 12 de la ISA GCN3     (183 coinciden + 2 difieren)
 31  sin valor                                       (26 atomicos SMEM + 5 concretas)
  2  DIFIERE, sin arbitrar:
       SQ_S_ATC_PROBE_BUFFER  la ISA asigna 0x26 a dos instrucciones distintas
       SQ_S_LSHR_B64          la ISA escribe "Opcode 31 (0x15)"; 31 = 0x1F. El header da
                              0x1f, que coincide con el DECIMAL. Con criterio
                              estrictamente-hex serian 184, no 185.
```

Las 2 DIFIERE se quedan **sin resolver y con las dos fuentes**, porque una de ellas es una
auto-contradiccion de la propia ISA. Elegir el header por ser "el que corre" seria aplicar
`IMPLEMENTATION_IS_NOT_AUTHORITY` al reves.

---

## 7. Abierto, con lo que falta para cerrarlo

Lo que este documento **no** dice, escrito para que no se lea de mas:

```
NO dice que la ISA se haya leido como correcta para este ASIC.   Solo 185/216 coinciden.
NO dice que los 31 ausentes sean fallo del cap. 12.               Podrian ser adicion GFX8
                                                                  posterior, otra generacion,
                                                                  o hueco de extraccion.
NO dice que GFX8 = GCN 3.                                        Es una inferencia por el nombre
                                                                  del driver, y ahora consta
                                                                  como tal.
NO dice que 2.75 MB de PDF deban entrar al repo.                 Es decision del humano.
NO cierra CONTRAD-Q5-AUSENCIA-TABLAS.                           La deja viva con tres inputs.
NO toca el driver, el ring, el PM4 ni la placa.                  RUNTIME=NOT_RUN.
```

Y el punto que el propio worker dejo como accion discriminante, que sigue siendo el mejor
siguiente paso porque es el mas barato y el mas informativo:

```
Q5-MEM-TABLES   medir con el metodo ya validado las 5 tablas que el cap. 12 SI trae
                completas (12.7/12.8/12.9/12.12/12.13, PDF 267-284) contra
                SQ_LDS_*/SQ_MUBUF_*/SQ_MTBUF_*/SQ_MIMG_*/SQ_FLAT_*.
                Si tambien dan cobertura alta, la conclusion operativa es que la fuente
                primaria cubre escalares y memoria pero NO el bloque de atomicos SMEM, y el
                bloqueo de Q5 no es "la tabla que faltaba" sino la CABECERA PM4 DEL CP.
                Coste: <10 s CPU, sin GPU, sin sudo.
```

---

## 8. Lo que arrastro abierto, sin resolver, y que no era de este nodo

Medido por el coordinador al llegar. **Ninguno se ha tocado.** Se listan para que no se
pierdan y para que el siguiente no los vuelva a descubrir como si fueran nuevos:

```
[01] .write-lock/owner   declara PID=825739 en scope ROOT. /proc/825739 NO EXISTE.
     Tambien muertos: recon-q5 PID=841580, agentes PID=704737, root-consolidation PID=725664,
     findnum owner "36323". Todos los cerrojos del arbol estan caducados. Por la base comun
     section 10 un owner muerto NO es permiso para tomar: se informa y se pide humano.
     Este turnocerrojo el ambito nuevo q5-isacap12 y recon-q5b, y NO toco los caducados.
[01] 08-ARQUITECTURA/KIT-VERDICT.json.estado (09:08) dice  regla=FAIL:14
     08-ARQUITECTURA/KIT-VERDICT.json      (12:23) dice  regla=PASS:21, veredicto PASS 17/17.
     Dos registros del mismo veredicto que se contradicen. El mas nuevo gana por fecha, no
     por nada medido. NO RECONCILIADO.
[01] CURRENT-STATE.md (09:27) declara "479 findings, numerados del 001 al 966".
     MEDIDO AHORA:  484 ficheros .md, rango 001-970, 385 numeros UNICOS, 72 prefijos
     DUPLICADOS. El universo declarado no cuadra con el arbol.
[01] Colision 968 sin resolver, confirmada con las dos partes:
       968-el-documento-que-declara-que-manda-declara-una-version-que-no-existe.md  6622 B
         sha 3eecc7ca5bee59e5c8a63a9315780fffc0eadcd7f0d5ba374d768ee98f66b972
       968-q5-universo-de-tablas-gfx8.md                                             24417 B
         sha f46e67e251c0295545d2845893e2e009467e521db7dcfd56d23c0d544e14f8d2
[01] Dos rutas de corpus vivos: RESEARCH/working/linux-7.1.3 (3 entradas, 521 MB) y
     RESEARCH/kernelbuild/linux-7.1.3 (32 entradas, 1,8 GB). Las citan 228 y 53 documentos.
     Para sid.h y gfx_8_0_enum.h son byte-identicas, asi que ahi NO diverge. Para el resto del
     arbol: NOT_DETERMINED, no medido.
```

---

```
AUTORIA=global-coordinator
WORK_CLASS=reconciliación
WRITE_EXECUTION=2 ficheros nuevos en 08-ARQUITECTURA/ bajo cerrojos q5-isacap12 y recon-q5b
RUNTIME=NOT_RUN · GPU=INTACTA · SIN_SUDO · SIN_COMMITS · MODIFICADOS_CRITICOS=0

INPUTS_VERIFICADOS
  HEAD                     3d89682195b03f0244a5a2945f2a9567dff704eb
  STATE.md                 21f8ca0e346ea271494b050bd5b9ef4e4c0370f604e9da3baf25c0dd9c9a661b  INTACTO
  968-q5-universo          f46e67e251c0295545d2845893e2e009467e521db7dcfd56d23c0d544e14f8d2  INTACTO
  gcn3-isa.pdf (externo)   8e49a3767b337ec8aff451494c654c84c026720de8e3fa35177b0656f4bc2853
  gfx_8_0_enum.h           fa6b8ff974fccdd54aa0e1b6a6430508a558fd263ead90eaf70bef262e4d5d63
  amdgpu_drv.c             07a1fff4f6cee85d…
  vi.c                     c554b770b71edb847…
  gfx_v8_0.c               2427f5b5fcb44778a76d
  extraccion propia del ISA  pdftotext -layout rc=0, 17667 lineas, stderr vacio
```
