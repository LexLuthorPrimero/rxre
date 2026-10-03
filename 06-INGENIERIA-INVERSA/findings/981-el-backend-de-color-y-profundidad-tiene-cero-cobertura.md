# 981 · El backend de color y profundidad tiene **cero** cobertura, y la afirmación de saturación de `979` era demasiado ancha

```
CLASSIFICATION=CORPUS+MEASUREMENT+NEGATIVE_RESULT · TRACK=STATIC
CORPUS=RESEARCH/working/linux-7.1.3 · HARDWARE_SCOPE=HOST-C/RX550/0000:01:00.0
WORK_CLASS=READ_ONLY/EVIDENCE+WRITE_LOCAL · WRITE_LOCAL=PROPIOS
WRITE_EXECUTION=NONE · MODIFICATIONS=0 (el corpus no se toca; lo unico escrito es este fichero)
RUNTIME=NOT_RUN · GPU INTACTA · SIN MMIO · SIN ESCRITURA A REGISTROS · SIN DEBUGFS
CORRECTS=979-la-frontera-estatica-gfx8-esta-saturada-con-cifras.md
CONTINUES=101-corpus-hueco-ttm-cierre-parcial-y-valor.md
AUTORIA=AGENTE-SMU-3 (AGENT-03, semantica GPU)
```

## Qué cambia

`979` declaró `SATURATED` la frontera de semántica estática GFX8 con **siete**
preguntas, todas de registros y GPUVM. La muestra era de un solo dominio y la
conclusión se escribió más ancha que la evidencia.

**Al medir el resto de mi ambito, hay un subdomain con cero cobertura.** Y es
precisamente el que `UNVERIFIED-CLAIMS.md` tiene con claims de prioridad **ALTA**.

## 1 · La medición, y el error que casi la sostiene

Primera versión, con los patrones que se me ocurren:

```
  CB_ a secas        14 findings      <-- FALSO
  IB  a secas       131 findings      <-- FALSO
```

Los dos están contaminados y los dos dan un número plausible:

- `CB_` matchea **`CB_DISABLE_READ_FAULT_ON_UNMAPPED_ACCESS`**, o sea que estaba
  midiendo los hallazgos de PRT por tercera vez.
- `IB` como token suelto matchea **POS-`IB`-LE**. 129 de los 131 eran prosa.

Corregido con límites de palabra y prefijos de registro:

| area de mi ambito | findings |
|---|---|
| clock / SCLK / MCLK / DPM | 84 |
| TLB | 65 |
| PTE / PDE | 61 |
| IB (con token) | 58 |
| `mmVM_` (GPUVM) | 45 |
| `mmMC_` (memory controller) | 20 |
| `mmDB_` (depth backend) | **2** |
| DCC (compresión de color) | **2** |
| **`mmCB_` (color backend)** | **0** |
| **HTILE** | **0** |
| CB/DB como etapa (`CB_START`, `DB_END`…) | **0** |

**Cero hallazgos mencionan un solo registro `mmCB_`.** Contra 84 para los relojes.

Y no es que los hallazgos existan y yo no los llegue a leer. `135` clasificó los 119
`PACKET3` de `sid.h` por quién los usa, y **no menciona `CB_STATE` ni `DB_STATE`**.
Que el único censo de paquetes de GFX8 no mencione los del backend de color es, en
sí mismo, la respuesta.

## 2 · El hecho positivo: el driver no programa el estado de render por MMIO

En los 9 ficheros del driver que tocan `mmCB_`/`mmDB_`, esto es **todo** lo que
aparece:

```
  28  mmDB_DEBUG2
  23  mmCB_CGTT_SCLK_CTRL
  21  mmDB_DEBUG3
  17  mmCB_HW_CONTROL
  13  mmCB_HW_CONTROL_3
  12  mmDB_DEBUG4
  11  mmDB_CGTT_CLK_CTRL_0
  10  mmDB_DEBUG
   7  mmCB_HW_CONTROL_2
   4  mmDB_RENDER_CONTROL
   4  mmDB_LAST_OF_BURST_CONFIG
   4  mmCB_HW_CONTROL_4
```

Clock gating, contadores de debug y el bloque de control de reset. Y del estado de
render propiamente dicho:

```
  mmCB_COLOR*        0
  mmCB_DEPTH*        0
  mmCB_SHADER_GREG   0
  mmDB_SHADER_CONTROL 0
  mmCB_BLEND*        0
```

**En GCN y Vega, el driver no programa con MMIO el estado del backend de color ni del
de profundidad.** Ni en `si.c`, ni en `gfx_v8_0.c`, ni en `gfx_v6/v7/v9/v10_0.c`.

**Por qué importa para un driver propio, y es la razón de que sea `PROVEN_DERIVED` y
no conjetura:** quien fuese a buscar `mmCB_COLOR0_BASE` para programar un color target
no lo encuentra en amdgpu, y la conclusión natural —"esta ASIC no lo tiene"— es
falsa. La lectura correcta es que **el estado de render no es un problema de
programación de registros, es un problema de transporte en el command stream**, y por
eso pertenece a la frontera de PM4/IB, que es la densa del proyecto (116 y 58), no a
la de registros.

**Lo que no puedo afirmar:** que el hardware no lo tenga, ni donde estan los offsets,
ni como se transportan. Ver seccion 3.

## 3 · El hueco de corpus, y por que NO lo lleno

```
$ ls RESEARCH/working/linux-7.1.3/drivers/gpu/drm/amd/include/asic_reg/
athub bif clk dce dcn df dpcs gc gca gmc hdp lsdma mmhub mp nbif nbio oss
pcie pwr rsmu sdma sdma0..sdma7 smu smuio thm umc uvd vce vcn vpe wafl xgmi

$ find . -iname '*cb_*d.h' -o -iname '*db_*d.h'
(vacio)
```

**No hay `cb/` ni `db/`.** Los headers de registros del color y del depth backend no
estan en este corpus.

Esto es **`NOT_FOUND`, no `PROVEN_ABSENT`**, y la distincion es la que decide si
lleno el hueco: el hardware de una GPU con render backend tiene esos registros
—"DCC lossless", "CB/DB bypass L2", "FMASK", "MSAA 8x SHS/CCS" son precisamente claims
sobre ellos en `UNVERIFIED-CLAIMS.md`, prioridades **ALTA**—, lo que falta es la
copia.

**Aplicando el metodo de `101` (que es el precedente del proyecto para esto):**

```
INFORMATION_GAIN   alto: sin los offsets no hay ninguna forma de cerrar los claims
                   M/N/O/P de UNVERIFIED-CLAIMS (DCC, bypass de L2, FMASK, MSAA)
COSTE             lo que cuesta el bloque de headers cb/ + db/ del kernel
COMPENSACION      DECISIVA: un driver propio necesita ESOS headers de todos modos.
                  Si el proyecto va a escribir su propio codigo C contra esta ASIC,
                  las definiciones de registro del CB/DB son un insumo obligatorio,
                  no una descarga opcional. Salen del mismo sitio que las de GMC.
RIESGO            bajo: son cabeceras, no ejecucion
```

**Mi recomendacion: no es una descarga de valor de investigacion, es un insumo del
driver, y se obtiene cuando se escriba el driver.** No la hago aqui, no la ejecuto, y
no la propongo como tarea prioritaria de esta sesion: nadie ha pedido escribir codigo
de render backend todavia.

Lo que **si** es accionable ya, sin el corpus: la conclusion de la seccion 2. Que el
estado de render de GFX8 no se programa por MMIO se sabe **hoy**, con el corpus que
hay, y eso cambia donde se mira cuando se llegue a esa parte.

## 4 · Lo que NO cierra

| afirmacion | estado |
|---|---|
| el driver de GCN/Vega no programa estado de render CB/DB por MMIO | `PROVEN_DERIVED` (9 ficheros, lista exhaustiva) |
| el estado de render se transporta por el command stream | **`NOT_DETERMINED`** — coherente, pero no medido |
| existen registros de render target en esta ASIC | **`NOT_DETERMINED`**, `NOT_FOUND` en corpus |
| CB/DB bypassean L2 en GFX8 | **`NOT_DETERMINED`**, claim ALTA de `UNVERIFIED-CLAIMS` §M |
| DCC en GFX8 | **`NOT_DETERMINED`**, claim ALTA, 2 hallazgos de 491 |
| el area esta vacia de hallazgos, no de fenomeno | `PROVEN` (medición con dos patrones y su control) |

## Procedencia

- Medición propia y reproducible: `grep -rlE` sobre `06-INGENIERIA-INVERSA/findings/`,
  seis patrones, con el control de los dos contaminados incluido en la tabla para que
  se pueda ver el error y no solo el resultado.
- Fuente primaria: `grep -rlE '\bmmCB_|\bmmDB_'` sobre
  `drivers/gpu/drm/amd/amdgpu/`, y `grep -rhoE` para el recuento por registro.
- `ls` y `find` sobre `include/asic_reg/` para el hueco.
- Sin MMIO, sin lectura de registros, sin debugfs, sin sysfs, sin modulos, sin
  descargas. La GPU no se ha tocado. `RUNTIME=NOT_RUN`.
- No se regenero ningun artefacto generado: son de otras sesiones.
- Ambito: `.write-lock/sem03`, un solo fichero nuevo, este.

## Nota de metodo

Esta nota **corrige a `979`, que es mio, y por el mismo motivo por el que `979`
corrigio a `976`**: una afirmación mas ancha que su muestra.

`979` midio siete preguntas de un dominio y escribio "la frontera de semantica estatica
GFX8 esta saturada". Al medir el ambito entero, no lo esta. **La unidad de una
afirmacion de saturacion es el ambito, y medir un subdominio no da el ambito.**

Y hay un segunda leccion que me llevo, mas caro: la primera medicion de esta nota dio
`CB_ = 14`, un numero **plausible** y con la forma correcta, y era basura. Si lo
hubiera publicado sin el control, habria fundado una frontera sobre un error de
regex. **Un numero de conteo sin su control de contaminacion no es una medida, es
una suerta** — y por eso el control va en la tabla y no en un afterthought.
