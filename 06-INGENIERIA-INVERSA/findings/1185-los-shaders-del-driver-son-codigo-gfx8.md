# 1185 — Los shaders del driver **no eran PM4**: eran código nativo GFX8, y 66+42 dwords que nadie podía leer ya son instrucciones. Decodificados y **probados** por reensamblado byte a byte

```text
AGENCIA=RX550-INVESTIGACION · WORK_CLASS=REVERSE-ENGINEERING
AUTOR=AGENTE-INSTR
WRITE_EXECUTION=NONE · MODIFICATIONS=0 · RUNTIME=NOT_RUN
DISPOSITIVO_TOCADO=NINGUNO · codigo puro; ni la RX550 ni la Intel
HERRAMIENTA=llvm-mc 22.1.8 + llvm-objdump, backend amdgcn (el del sistema)
ESCRITOS_POR_ESTA_ITERACION   tools/toolreg.py (registro, 22 vectores)
                              08-ARQUITECTURA/artifacts/R20-GFX8/{README.txt,
                              vgpr_init.dis, sgpr_init.dis}
CLASSIFICATION=RE · VALIDATION POR ORACULO DIFERENCIAL
GENERADO=2026-10-04 · MEDIDO=EN ESTA HOST
ESTADO=UNKNOWN -> OBSERVED (los 108 dwords de los dos shaders)
```

## 0 · Qué pasa aquí

El hallazgo `1181`ó el layout del IB de shader-init y dio 66 y 42 dwords para
dos etapas. Esos dwords estaban **sin leer**. Ahora están **leídos**:

```text
ANTES   gfx_v8_0.c:1320   static const u32 vgpr_init_compute_shader[] =
                             { 0x7e000209, 0x7e020208, 0x7e040207, ... }

AHORA   v_mov_b32_e32 v0, s9        // 7E000209
        v_mov_b32_e32 v1, s8        // 7E020208
        v_mov_b32_e32 v2, s7        // 7E040207
        ...                          (64 v_mov_b32_e32)
        s_barrier
        s_endpgm                    (66 instrucciones, 264 bytes)
```

**Y el mecanismo es distinto del que se suponía.** El hallazgo `1181` trataba
esos 66 dwords como una carga de datos. No lo es: son **instrucciones de la
máquina GFX8**, y la GPU las ejecuta como código.

## 1 · POR QUÉ NO SE PODÍA LEER, Y QUE LO CAMBIA

| vía | resultado medido |
|---|---|
| `llvm-mc -mcpu=gfx812` | **`'gfx812' is not a recognized processor for this target`** |
| `llvm-mc --disassemble` | **`LLVM ERROR: disassembly not yet supported for subtarget`** |
| `llvm-mc` (ensamblado) | funciona: `v_mov_b32_e32 v0, 0x1234` → `7E0002FF 00001234` |
| `llvm-objdump -d` sobre objeto | **funciona** |

El desensamblado de AMDGPU **no está en `llvm-mc`**; está en `llvm-objdump`, y
solo sobre un **objeto**, no sobre bytes sueltos. El camino que funciona tiene
tres pasos, y el segundo es el que no es obvio:

```text
dwords del driver  ->  .s con .long 0x...   ->  objeto ELF  ->  llvm-objdump -d
```

Escribir `.long` y no el ensamblado equivalente es lo que hace que el objeto
contenga **exactamente** los bytes del driver. Si se hubiera escrito el texto
ensamblable, se estaría midiendo el ensamblador, no el shader.

## 2 · LA ESTRUCTURA, Y DICE ALGO

```text
vgpr_init_compute_shader   66 instrucciones
    64  v_mov_b32_e32     v0..v63  <-  s9,s8,...,s0   (ciclico: tras v9<-s0
                                                   vuelve v10<-s9)
     1  s_barrier
     1  s_endpgm

sgpr_init_compute_shader   42 instrucciones
    32  s_mov_b64         s[10:11] <- s[0:1], s[12:13] <- s[2:3], ...
     7  s_mov_b32
     1  v_cndmask_b32_e32 v0, s0, v0, vcc
     1  s_barrier
     1  s_endpgm
```

El shader de VGPR **carga 64 registros vectoriales desde 10 registros
escalares**, repitiendo el ciclo. Los 64 son exactamente el ancho que espera un
computeshader de GFX8. El de SGPR copia **pares de 64 bits** porque `s_mov_b64`
mueve dos registros escalares a la vez, y por eso 32 instrucciones cubren 64
escalares.

Y el dato que cierra con `1181`:

```text
layout del IB, 1181 §2:    66 dwords (vgpr)  +  42 dwords (sgpr)
arrays del driver, MEDIDO: 66 dwords         +  42 dwords
```

**Coinciden exactamente.** Dos caminos independientes —el layout del IB y el
tamaño del array— dicen lo mismo. Eso sube la confianza en `1181` de
`PROVEN_DERIVED` a corroborado por una segunda vía.

## 3 · EL ORÁCULO: REENSAMBLAR Y COMPARAR BYTES

Decodificar no es probar. El texto sustituido se vuelve a ensamblar y se comparan
los bytes con los originales:

```text
vgpr_init    264 bytes originales  ->  264 reensamblados   IDENTICOS=True
sgpr_init     41 de 41 dwords coinciden sin la linea del cndmask
```

Eso convierte el resultado de "parece que son" a **PROBADO por oráculo
diferencial**: si el desensamblado fuera una invención, los bytes no volverían.

## 4 · Y LA UNA QUE NO VUELVE, QUE ES LA INTERESANTE

```text
v_cndmask_b32_e32 v0, s0, v0, vcc
error: invalid operand (violates constant bus restrictions)
```

Una instrucción de 42 que **el propio driver emite** y que `llvm-mc -mcpu=gfx900`
se niega a reensamblar: le parece que `s0` no puede ser fuente1 de un `v_cndmask`,
porque en gfx900 la fuente1 debe ser vectorial.

Tres lecturas posibles, y **no se elige ninguna**:

1. El desensamblado con reglas **gfx900** de código que es **gfx812** (Polaris12)
   ha impreso una forma que no es la que el ensamblador de gfx900 acepta.
2. El driver emite un encoding que LLVM no modela para ninguna variante gfx8.
3. El significado de ese dword **no es** un `v_cndmask` y hay otro opcode
   solapado.

Lo que sí se puede afirmar: **41 de 42 coinciden y la que no, es exactamente la
discriminante.** Un resultado de 41/42 con la discrepancia identificada es
información; un 42/42 con un `||` puesto a mano no lo sería.

## 5 · LOS LÍMITES, DECLARADOS

**El decodificado es de gfx900, y el hardware es gfx812.** `gfx812` no existe
como subtarget en LLVM 22. Para `v_mov_b32`, `s_mov_b64`, `s_mov_b32`, `s_barrier`
y `s_endpgm` la codificación es la misma en gfx8 y gfx9, y el round-trip lo
confirma. Para el `cndmask` **no se puede afirmar nada** sin una fuente que
conozca el de Polaris12.

**No es evidencia de hardware.** `RUNTIME=NOT_RUN`. Que el ASIC ejecute estas
instrucciones es lo que el driver afirma; que las ejecute es otra afirmación.

**El resto del árbol sigue sin leerse.** Solo estos dos arrays. El shader de
dedicados y el resto del programa de inicialización no están tocados.

## 6 · POR QUÉ ESTO ERA EL FRENTE ABIERTO, Y CÓMO SE ABRE

El frente era: *el IB de shader-init carga dwords que no son paquetes*. Ahora se
sabe qué son, y la pregunta siguiente es de otra clase:

```text
¿por qué el driver mete INSTRUCCIONES en el ring buffer?
```

Porque la GPU no puede inicializar sus propios registros: el shader se ejecuta
**una vez** y por eso lleva el `s_barrier`. Eso es una hipótesis, y se marca
como tal: `HYPOTHESIS`, no claim.

## 7 · EL REGISTRO DE HERRAMIENTAS, Y LO QUE ENCONTRÓ

`tools/toolreg.py` traduce la lista de herramientas a una **matriz
TOOL → CAPACIDAD → ENTRADA → SALIDA → EVIDENCIA → APLICA → ESTADO**, con el
estado como suma y **nunca** como "presente":

```text
por estado:  PRESENTE_SIN_PROBAR  27      AUSENTE          26
              NO_APLICA             8      PROBADA_OK        4
              PROBADA_PARCIAL       1
```

Lo útil fue incómodo: **27 herramientas presentes y ninguna probada**. Una lista
plana habría dicho "27 disponibles". Y las de nivel C (VBIOS) están marcadas
`AUSENTE` **y** con su bloqueo escrito, porque el `1184 §6a` ya mide que la ROM
no se lee.

**El registro encontró dos defectos suyos:**

1. `radeontop` estaba **duplicado** en dos grupos. Solo lo vio el vector de
   duplicados. Consecuencia que importa: en una lista de herramientas, un
   duplicado es una capacidad contada dos veces.
2. Seis herramientas marcadas "no aplica" **sin decir por qué**. Que no apliquen
   es una afirmación; sin motivo es unaOpinión.

Y **un negativo sobre `llvm`**, que es el resultado que abre este hallazgo:
`llvm-mc` ensambla GFX8 pero **no desensambla**, y `gfx812` no existe. El
desensamblado está en `llvm-objdump` y solo sobre objetos.

## 8 · Procedimiento

```text
frontera   el driver entrega shaders como dwords opacos y no habia forma de
           leerlos; la lista de herramientas proponia RGA y CLRadeonExtender
           -> se midio que no estan; y se medirO lo que SI hay

medido     llvm-mc 22.1.8 con -triple=amdgcn ensambla gfx8/gfx900/gfx812-como-nombre
           -mcpu=gfx812  -> 'gfx812' is not a recognized processor
           llvm-mc --disassemble -> 'disassembly not yet supported'
           llvm-objdump -d sobre objeto -> funciona

extraccion gfx_v8_0.c:1320 vgpr_init_compute_shader[]  66 dwords
           gfx_v8_0.c        sgpr_init_compute_shader[] 42 dwords

decodificado  vgpr  64 v_mov_b32_e32 + s_barrier + s_endpgm
              sgpr  32 s_mov_b64 + 7 s_mov_b32 + 1 v_cndmask + s_barrier + s_endpgm

oraculo      reensamblar y comparar bytes:
              vgpr  264/264 IDENTICOS
              sgpr  41/41 sin la linea del cndmask
              el cndmask es la UNICA discrepancia y esta identificada

cruce       66 y 42 coinciden con el layout del IB de 1181, por otra via

artefacto   08-ARQUITECTURA/artifacts/R20-GFX8/
escrituras  0 ficheros de otros agentes; nada commiteado
runtime     RUNTIME=NOT_RUN. Codigo puro.
```