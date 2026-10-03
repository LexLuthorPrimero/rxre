# 979 · La frontera de semántica estática GFX8 está saturada, y el coste está medido: 4 de 7 preguntas ya estaban respondidas

```
CLASSIFICATION=MEASUREMENT+NEGATIVE_RESULT · TRACK=STATIC
CORPUS=RESEARCH/working/linux-7.1.3 · HARDWARE_SCOPE=HOST-C/RX550/0000:01:00.0
WORK_CLASS=READ_ONLY/EVIDENCE+WRITE_LOCAL · WRITE_LOCAL=PROPIOS
WRITE_EXECUTION=NONE · MODIFICATIONS=0 (el corpus no se toca; lo unico escrito es este fichero)
RUNTIME=NOT_RUN · GPU INTACTA · SIN MMIO · SIN ESCRITURA A REGISTROS · SIN DEBUGFS
CONTINUES=974-el-bit-51-si-llega-a-un-pte-de-gfx8-por-el-manejador-de-faults.md
CONTINUES=976-corregcion-a-974-el-escritor-del-bit-51-es-inalcanzable-en-gfx8.md
CONTINUES=978-el-iv-de-gfx8-no-es-el-de-8-dwords.md
CORROBORADO_POR=183-dos-formatos-de-iv-y-la-version-del-bloque-que-decide.md
CORROBORADO_POR=087-sf-gmc-8-1-nombre-no-predice-generacion.md
CORROBORADO_POR=292-citas-a-ficheros-que-esta-gpu-no-ejecuta.md
CORROBORADO_POR=023-pte-productor-sdma-gfx8.md
AUTORIA=AGENTE-SMU-3 (AGENT-03, semantica GPU)
```

## Qué es esto

No es un hallazgo de hardware. Es la medicion de por que un turno entero produjo
**un** hilo productivo, y por que las otras cuatro preguntas ya estaban contestadas
en el corpus con numero de linea.

**Se declara la frontera `SATURATED`**, con la razon que `AGENTS.md` 100 exige que sea
una y no "no se me ocurre mas".

## 1 · La medicion

Siete preguntas que me propuse en este turno, y para cada una, que finding previo las
tenia ya:

| # | pregunta | prior art | veredicto |
|---|---|---|---|
| 1 | ¿que produce el `dev_warn` de PRT? | `099-sc-observado` linea 73: *"alguien mapea con `AMDGPU_VM_PAGE_PRT`"* | **REDUNDANTE** — la evidencia que cite ya lo decia |
| 2 | ¿hay un segundo escritor del bit 51? | ninguno | **NUEVO** -> `974` |
| 3 | ¿alcanza `amdgpu_vm_handle_fault` en GFX8? | ninguno | **NUEVO** -> `976` |
| 4 | ¿el tipo de fault GFX8 es observable? | `101` lo negaba, luego es nuevo; pero el camino KFD no estaba medido | **NUEVO** -> `976` |
| 5 | ¿que decodificador de IV usa GFX8? | `183` completo, con numero de linea | **REDUNDANTE** — `978` es una correccion mia, no un hallazgo |
| 6 | ¿`ip_block` ↔ fichero de implementacion? | `087:126` (tabla) y `087:155` (`sdma_v3_1_ip_block.funcs = &sdma_v3_0_ip_funcs`) | **REDUNDANTE** |
| 7 | ¿que header de registros compila? | `023:138-141`, seccion titulada *"Correccion de provenance: `gmc_8_1_d.h`, no `gmc_8_2_d.h`"*; ademas `203:123`, `121:32`, `242:341` | **REDUNDANTE** |

```
preguntas  7
redundantes 4        (57 %)
nuevas      3        y las 3 son el mismo hilo: PRT
hilos independientes con resultado  1
```

**Ademas, `292` ya habia medido que `gmc_v8_0.c` y `sdma_v3_0.c` estan `EN_DISPATCH`,
y que `dce_v8_0.c` es codigo muerto.** Yo iba a derivar eso. Esta servido.

## 2 · El unico hecho que no estaba reclamado

Verificado antes de escribir, porque ya no me fiaba:

```
$ grep -rliE 'GPUVM_FAULT' 06-INGENIERIA-INVERSA/findings/
978-el-iv-de-gfx8-no-es-el-de-8-dwords.md          <- mio

$ grep -rliE 'pasid != 0|xa_store_irq|vm_manager.pasids' 06-INGENIERIA-INVERSA/findings/
976-...   978-...                                   <- mios, y solo mios
```

**`AMDGPU_INFO_GPUVM_FAULT` devuelve ceros en GFX8, y la causa es que
`amdgpu_vm.c:2675` solo mete la VM en el xarray de PASIDs `if (pasid != 0)`, y un VM
grafico en Polaris12 tiene `pasid == 0`.** Nadie lo tenia. `101` rozaba la zona pero
concluia lo contrario y por otra razon.

Eso es lo que queda. **Un ioctl que existe, responde, y devuelve `0`.** Es peor que
no existir: parece un observable.

## 3 · Lo que queda abierto en mi ambito, y por que no lo hago

Mi ambito es semantica de hardware. Lo que queda sin reclamar, en el ambito de
registros y GPUVM, son **dos discriminantes que necesitan runtime**:

```
D1  ¿PRT esta activo ahora en esta maquina?
    REGISTRO   mmVM_PRT_CNTL        0x534
    CAMPOS     7 (CB/TC disable read/write, L1/L2 store invalid, MASK_PDE0_FAULT)
    CIERRA     la fila "si PRT esta activo ahora" de 099, que quedo NOT_DETERMINED
               por "sin observable" — y el observable es un registro (131)
    COSTE      1 lectura

D2  ¿puede traer el IV de GFX8 un pasid != 0?
    REGISTRO   ninguno: es el anillo del IH, no MMIO
    LEE        tonga_ih_decode_iv -> entry->pasid = (dw[2] >> 16) & 0xffff
    CIERRA     si puede, AMDGPU_INFO_GPUVM_FAULT deja de estar muerta a medias
    COSTE      1 fault real + lectura del anillo del IH desde el host
```

Los dos **exigen MMIO o lectura del anillo con la sesion viva**, y `.write-lock/owner`
lo tiene AGENT-04 con `scope=ROOT write-anywhere`, rol `RUNTIME/PROBING`. `AGENTS.md`
88 prohibe que dos agentes toquen el estado de la GPU a la vez. **No los ejecuto y no los escribo: los dejo con direccion, campo y criterio de cierre.**

## 4 · Por que me cuesta, y no es falta de rigor

No me falta rigor: es **orden**. En las cuatro preguntas redundantes, mi conclusion
final era correcta y mis citas eran verificables. Lo que fallo es que **llego al
final**.

En tres de las cuatro, el prior art estaba en un fichero que yo ya habia listado al
arrancar (`183`, `087`, `292`, `023`, `203`). No los lei. Fui directo a la fuente
primaria porque la fuente primaria es mas rapida y mas silenciosa, y **perdi el
contexto por no haber leido el indice de lo ya resuelto.**

Y hay un ironia que conviene decir: **es exactamente el error que `183` le atribuye a
`131` y que `976` me atribuye a mi** —afirmar sin haber leido lo que ya estaba
escrito—. La clase de error no es mia, es del proyecto. Lo unico que cambia es que
aqui se puede contar.

## 5 · Lo que esta medicion pide, y de quien es

```
PENDIENTE=un preflight que responda "el corpus ya contesta esto?" ANTES de emitir
          un hallazgo, y no despues
  | HALLAZGO=979-... (este)
  | ESTADO=NOT_DETERMINED
  | NECESITA=indexar, por cada hallazgo, el fichero y la linea que su cabecera
  |          declara, y poder preguntar por la *pregunta* y no por el *termino*
  | ALCANZABLE_SIN_ROOT=si
  | NOTA=es el gemelo del hueco que 188:146-168 ya declara ("una cita puede
  |      resolver y no sostener la afirmacion"). Aquel va de la cita; este va de
  |      la pregunta. Los dos son el mismo defecto en dos direcciones.
  | AMBITO=NO es mio. Es herramientas/documentacion. No lo construyo aqui: entrego
  |         la medicion y los siete puntos de datos para que se pueda verificar.
```

## Procedencia

- Todo el recuento de la tabla 1 es **propio y reproducible**: los siete `grep` de la
  seccion 1, sobre `06-INGENIERIA-INVERSA/findings/`, este turno.
- Las citas de prior art son **lineas leidas**, no de memoria: `099-sc-observado:73`,
  `183` completo, `087:126` y `:155`, `292` (tabla `EN_DISPATCH`),
  `023:138-141`, `203:123`, `121:32`, `242:341`, `188:146-168`.
- Sin MMIO, sin lectura de registros, sin debugfs, sin sysfs, sin modulos, sin TLB.
  La GPU no se ha tocado. `RUNTIME=NOT_RUN`.
- No se regenero ningun artefacto generado (`CONTRADICTIONS.md`, `OPEN-FRONTIERS.md`,
  `CURRENT-STATE.md`, `FINDINGS-RENUMERACIONES.md`): son de otras sesiones.
- Ambito: `.write-lock/sem03`, un solo fichero nuevo, este.

## Nota de metodo, y por que esta nota es la mas util del turno

Un hallazgo que dice *"esto ya estaba medido"* tambien es un hallazgo, siempre que
diga **cuatro de siete** y no *"hay cosas repetidas"*. El primero es una medicion con
cifras y se puede refutar. El segundo es una sensacion y no se puede.

Y hay una cosa que solo se ve contando: **las tres preguntas que si produjeron algo
fueron el mismo hilo.** No es que yo hiciese tres descubrimientos; es que la persistencia
**una** pregunta —*¿por qué `131` y `099` no pueden ser verdad a la vez?*— y esa dio
`974`, `976` y `978`. Las otras cuatro preguntas las elegi por variedad, y la
variedad aqui no paga: el corpus ya esta barrido, y saltar de tema es como se
rediscovering lo mismo cinco veces.

**La regla que sale, y es la opuesta de la que acabo:** cuando un hilo da, no se
abandona por aburrimiento; se profundiza. `974` -> `976` -> `978` son tres estados sobre
la misma pregunta, y el tercero nombro un ioctl muerto que el primero no vio.
