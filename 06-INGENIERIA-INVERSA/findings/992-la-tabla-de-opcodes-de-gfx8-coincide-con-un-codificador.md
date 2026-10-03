# 992 · La tabla de opcodes de GFX8 coincide 4 de 4 con un codificador independiente, y el campo opcode no está donde la herramienta dice

```
CLASSIFICATION=MEASUREMENT+CORROBORATION · TRACK=STATIC+CROSS_CHECK
CORPUS=08-ARQUITECTURA/tools/gfx8_opcode.py (sha256 1b1b59838400fb378085931e…)
        + llvm-mc 22.1.8 (codificador independiente, local)
HARDWARE_SCOPE=HOST-C/RX550/0000:01:00.0 · TARGET=amdgcn-amd-amdhsa--gfx803
WORK_CLASS=READ_ONLY/EVIDENCE+WRITE_LOCAL · WRITE_LOCAL=PROPIOS
WRITE_EXECUTION=NONE · MODIFICATIONS=0 (salvo este fichero, unico escrito)
RUNTIME=NOT_RUN · GPU INTACTA · SIN MMIO · SIN ESCRITURA A REGISTROS · SIN DEBUGFS
CONTINUES=991-el-isa-de-gfx8-si-tiene-fuente-primaria-publicada.md
CONTINUES=188-el-nombre-del-op-12-y-la-cita-equivocada.md
AUTORIA=AGENTE-SMU-3 (AGENT-03, semantica GPU)
```

## Qué hace esta nota

`240` declaro un hueco que sigue abierto:

```
PENDIENTE=una cita puede resolver y no sostener la afirmacion, y ninguna
          herramienta lo distingue
  | NECESITA=cross-check de que el termino citado aparece en el hallazgo citado
  | ALCANZABLE_SIN_ROOT=si
```

Eso es un hueco sobre **citas**. Lo que hago aqui es mas fuerte: **no compruebo que
una cita sostenga una afirmacion, sino que la tabla de una herramienta del proyecto
sea correcta**, contrastandola con un codificador que no tiene nada que ver con ella.

Un codificador independiente es el unico oraculo posible para una tabla de opcode: no
la opinion de quien la escribio, ni un comentario, ni otro nombre para el mismo
numero. **`llvm-mc` 22.1.8, `-mcpu=gfx803`, es exactamente eso.**

## 1 · El cross-check, 4 de 4

```
$ echo 's_add_u32 s0, s1, s2' | llvm-mc -triple=amdgcn-amd-amdhsa -mcpu=gfx803 -filetype=obj -
```

| instruccion | palabra ensamblada | opcode segun `gfx8_opcode.py` | coincide |
|---|---|---|---|
| `s_add_u32` | `0x80000201` | **0** | si |
| `s_sub_u32` | `0x80800201` | **1** | si |
| `s_add_i32` | `0x81000201` | **2** | si |
| `s_sub_i32` | `0x81800201` | **3** | si |

La herramienta lo dice en su propio docstring, y es la afirmacion que se puede
contrastar:

```
S_ADD_U32=0, S_SUB_U32=1, S_ADD_I32=2 es una tabla
```

**Y coincide.** Los deltas entre palabras consecutivas son exactamente `0x00800000`,
que es lo que hace un campo que incrementa en uno, empezando en el bit 23.

**Una nota de sintaxis que cuesta un rato:** `SOP2` opera sobre **registros escalares**
(`s0`, no `v0`). `s_add_u32 v0, v1, v2` no ensambla: *"invalid operand for
instruction"*. El campo de operandos es otra tabla, como dice la propia herramienta,
y `V_ADD_F32` si lleva vectores. Confundir los dos registros es un error que el
ensamblador detecta y que una tabla de opcode no.

## 2 · Y el campo opcode no esta donde la herramienta implica

La herramienta dice, literalmente, *"solo el campo de opcode dentro de la familia"*.
**No dice donde vive ese campo**, y no es trivial: si el opcode no estuviera donde se
supone, la tabla seguiria siendo una tabla de valores correctos y estaria mal
ubicada.

Un XOR entre dos codificaciones solo prueba **que bits cambian**. No prueba que esos
bits sean *el opcode*: tambien podrian ser un operando que ese ensamblador eligio
poner ahi. **Para aislar el campo hay que cambiar los operandos**, que es lo que
hice:

```
s_add_u32 s0,  s1, s2   -> 0x80000201
s_add_u32 s3,  s7, s11  -> 0x80030b07
s_add_u32 s15, s31, s63 -> 0x800f3f1f
```

```
XOR(s0/s1/s2 , s3/s7/s11) = 0x00030906
  bits que SI dependen del operando : [1, 2, 8, 11, 16, 17]
  bits que NO dependen del operando: todos los demas
```

**Los bits 23 y 24 —los que cambian al pasar de opcode a opcode— no dependen de los
operandos.** Eso los saca del juego de los operandos por construccion, y ya se sabe
que pertenecen al opcode por el otro experimento. Los dos experimentos juntos
**aislan el campo**; ninguno de los dos solo bastaba.

De los dos, el primero (que cambia el opcode) es el que **no** distingue "campo de
opcode" de "campo de algo mas que correlaciona"; el segundo (que cambia los operandos)
es el que lo hace. **Un solo experimento de diferencia no demuestra un campo: un
campo es lo que no se mueve cuando deberia y se mueve cuando deberia.**

**Donde esta, con honestidad:** el opcode de `SOP2` esta contenido en los bits
`[30:18]`, y los opcodes consecutivos alternan **solo** los bits 23 y 24, lo que es
consistente con un campo de 7 bits en `[29:23]` con el LSB en el bit 23. Eso es
`PROVEN_DERIVED` **a partir de deltas de codificacion**. **No esta confirmado contra
la GCN3 ISA**, que es el documento que de verdad define el formato y que **no he
leido** (`991` §1). Es el mismo `NOT_PROVEN` que alli, y no lo upgraded por haberlo
medido mejor: medir la consistencia de un codificador no es medir el formato.

## 3 · Lo que NO cierra

| afirmacion | estado |
|---|---|
| la tabla de `gfx8_opcode.py` coincide con LLVM en `SOP2` aritmetico | `PROVEN`, 4 de 4, con selftest de la herramienta en verde |
| el opcode de `SOP2` no depende de los operandos | `PROVEN`, por variacion de operandos |
| los bits 23 y 24 son los que incrementan | `PROVEN`, por variacion de opcode |
| el campo esta en `[29:23]` | **`PROVEN_DERIVED`**, no confirmado contra la ISA |
| el resto de familias (`SOP1`, `SMEM`, `VMCNT`, `VINTRP`…) | **`NOT_DETERMINED`**, cross-check de 4 instrucciones de una familia |
| el formato oficial | **`NOT_PROVEN`**, la GCN3 ISA sigue sin leerse |

**El limite que importa y que no quiero disimular:** cuatro instrucciones de una
familia en un corpus que tiene 216 entradas de opcode y 34 tablas. **Es un
cross-check que sale, no un cross-check que cierra.** Lo que hace es **descartar la
hipotesis de que la tabla este corrida**, que era el riesgo real, y no mas.

Y hay una razon por la que 4 bastan para eso y mas no: si la tabla tuviera un
desplazamiento, los cuatro valores habrian salido corridos a la vez. Salen bien, y el
patron de deltas es el de un contador, no el de un desplazamiento.

## Procedencia

- `CROSS_CHECK` — `llvm-mc` (LLVM 22.1.8) en `/usr/bin/llvm-mc`, invocado con
  `-triple=amdgcn-amd-amdhsa -mcpu=gfx803 -filetype=obj`, y lectura de la palabra de
  32 bits del `.text` con `struct.unpack`. Sin red, sin GPU, sin privilegios.
- Herramienta del proyecto contrastada: `08-ARQUITECTURA/tools/gfx8_opcode.py`,
  `sha256 1b1b59838400fb378085931e…`, **selftest en verde** (`rc=0`) antes de usarla.
  Sin el selftest, una tabla que coincide con LLVM podria ser la tabla correcta de la
  herramienta equivocada.
- `TARGET=gfx803` cierra la fila `PROVEN_DERIVED` de `991`: `llvm-mc` acepta
  `-mcpu=gfx803` como target de primera clase y ensambla sin error. **No he leido la
  GCN3 ISA** y el contenido del ISA sigue `NOT_PROVEN`.
- Sin MMIO, sin lectura de registros, sin debugfs, sin sysfs, sin modulos. La GPU no
  se ha tocado. `RUNTIME=NOT_RUN`.
- No se regenero ningun artefacto generado: son de otras sesiones.
- Ambito: `.write-lock/sem03`, un solo fichero nuevo, este.

## Nota de metodo

La razon por la que `240` **puede** declarar su hueco como abierto y yo **no** exigir
una herramienta nueva para esto es que existe un oraculo que no habia usado nadie:
**un ensamblador instalado en la maquina.**

Toda la discusion interna del proyecto sobre nombres de opcode —`164`, `240`, `967`,
los seis emisores de `240` §1— es una discusion sobre **nombres**. Y un nombre no se
discute: **se ensambla**. Bastaba mirar si la maquina tenia un `llvm-mc`, que es lo
que un `command -v` responde, para tener un juez externo con opinions propias.

**Y el metodo del aislamiento es la parte que me llevo:** un campo de bits no se
localiza cambiando lo que tiene que cambiar, sino cambiando **lo que no deberia
cambiar**. El primer experimento —cuatro opcodes y sus deltas— era el intuitivo y
solo demuestra correlacion. El segundo —cambiar los operandos— es el que convierte
correlacion en campo. **Sin el segundo, la afirmacion "el opcode esta en el bit 23"
hubiera sido una conjetura con formato de medicion**, que es exactamente la clase de
cosa que este corpus lleva tres hallazgos corrigiendo.
