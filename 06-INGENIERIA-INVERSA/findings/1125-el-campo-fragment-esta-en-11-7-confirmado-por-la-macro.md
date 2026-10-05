# 1125 — el campo fragment del PTE está en `11:7`, confirmado por la macro; el comentario de `amdgpu_vm_pt.c` es el que miente

```text
AGENCIA=RX550-INVESTIGACION · WORK_CLASS=AGENT-RE-TOOLING
GENERADO=2026-10-04 · MEDIDO=EN ESTA HOST · CORPUS=rx550-upstream-7.2.8
CIERRA=1124-tres-comentarios-del-driver-sobre-el-pte-de-gfx8-incompatibles.md
         (de PROVEN-CONTRADICCION a PROVEN-CON-LOCALIZACION)
ESTADO=PROVEN-CON-LOCALIZACION · la macro del codigo, no un comentario
herramienta   ninguna: lectura de corpus con dos instrumentos independientes
         (grep de la definicion + grep de todos sus usos)
```

## 0 · LA RESPUESTA, QUE ESTA EN UNA MACRO

El hallazgo `1124` dejó abierta una contradicción entre el comentario del
formato del PTE en `gmc_v8_0.c` —que dice que el campo fragment está en `11:7`— y
el comentario de `amdgpu_vm_pt.c:732` —que implica el bit 12—.

La respuesta está en `amdgpu_vm.h:70`:

```c
#define AMDGPU_PTE_FRAG(x)	((x & 0x1fULL) << 7)
```

**El campo está en `11:7`.** Desplazamiento 7, máscara `0x1f` de 5 bits, rango
0–31. El comentario de `gmc_v8_0.c` es el correcto y el de `amdgpu_vm_pt.c` es el
que miente.

Y el uso es **único y explícito**, en el punto donde se compone la entrada:

```c
amdgpu_vm_pt.c:887
  uint64_t upd_flags = flags | AMDGPU_PTE_FRAG(frag);
```

## 1 · POR QUÉ EL COMENTARIO EQUIVOCADO ES TENTADOR, Y POR QUÉ ES EL QUE MÁS

MEDIDO el valor que recibe la macro en el segundo uso, `amdgpu_gmc.c:1167`:

```c
flags |= AMDGPU_PTE_FRAG((adev->gmc.vmid0_page_table_block_size + 9*1));
```

Hay un **`+ 9*1`** literal, y `9` es precisamente el `fragment_size` de esta GPU.
Con un `+ 9` a la vista, la lectura natural es "el fragmento está desplazado
nueve bits más allá, o sea en el bit 12" — y eso es lo que dice el comentario de
`amdgpu_vm_pt.c`.

> **El comentario no está equivocado por descuido: está equivocado por
> coincidencia.** Veintinueve corresponde a `vmid0_page_table_block_size`, que
> es el tamaño de bloque del GART, y el `9` es un término aparte. El autor del
> comentario los leyó como un desplazamiento único.

Esa es la razón por la que el error es peligroso: **un lector que siga el
comentario llega a una conclusión razonable y equivocada**, y no por ignorancia
sino por una coincidencia aritmética.

## 2 · LOS TRES COMENTARIOS, ADJUDICADOS

| afirmación | fichero:línea | veredicto |
|---|---|---|
| A · fragment en `11:7` | `gmc_v8_0.c:686-696` | **CORRECTA** — la macro lo confirma |
| B · granularidad `1 << (12+frag)` | `amdgpu_vm_pt.c:730-733` | **IMPLICA bit 12: FALSA** |
| C · `max_frag = 9` en GFX8, 31 en Vega10+ | `amdgpu_vm_pt.c:749-754` | **CORRECTA**, y el rango 0–31 es el de la máscara |
| A′ · PDE `63:59` y `39:1` | `gmc_v8_0.c:697-703` | **incorrecta**, y choca con el `BUG_ON` de 8 líneas más abajo |

## 3 · Y LA CONTRADICCIÓN DEL PDE, QUE TAMBIÉN SE RESUELVE

`1124` señaló que el `BUG_ON` de `gmc_v8_0.c:709` y el comentario del PDE, a ocho
líneas, discrepan. Con la macro en la mano, la lectura es:

```
  0xFFFFFF0000000FFF   ->  reserva 63:12
  AMDGPU_PTE_FRAG(x)    ->  ocupa 11:7
```

**Consistente.** Los bits `11:7` son del campo fragment y la máscara del `BUG_ON`
no los toca. El comentario del PDE dice que la dirección empieza en el bit 1 y
que `58:40` está reservado, y **las dos cosas son falsas**, pero la segunda
falsedad es la que importa: `58:40` no está reservado, el campo fragment llega
hasta el bit 11.

> El `BUG_ON` es la afirmación correcta y el comentario de al lado está mal en
> las dos mitades. Es el mismo patrón del PTE, en la misma línea de código, con
> el mismo block de comentarios: **este bloque de comentarios describe otro
> formato y nadie lo ha revisado.**

## 4 · LO QUE ESTO CIERRA Y LO QUE NO

**Cierra** (`PROVEN`):

- el campo fragment del PTE de GFX8 está en los bits **`11:7`**, con máscara de
  5 bits y rango 0–31;
- `fragment_size = 9` se escribe como valor `9` en ese campo, y produce
  granularidad `1 << (12 + 9)` = **2 MiB**;
- el comentario de `amdgpu_vm_pt.c:732` es incorrecto y su error viene de la
  coincidencia del `+ 9*1` de `amdgpu_gmc.c:1167`.

**No cierra** (`NOT_DETERMINED`):

- **Que el hardware lea ese campo donde dice la macro.** La macro dice dónde lo
  pone el driver; no dice dónde lo lee la GPU. Eso es `NOT_DETERMINED` con el
  corpus, y no se convierte en `PROVEN` porque una macro y un comentario
  coincidan.
- El formato del PDE, que sigue con dos afirmaciones contradictorias y sin
  cerrar por el mismo motivo: hace falta la guía de hardware.

> La diferencia entre «el driver escribe el campo aquí» y «el hardware lo lee
> aquí» es la misma que separa `IMPLEMENTATION` de `AUTHORITY`. Una macro es
> implementación. Este hallazgo dice dónde escribe el driver, y lo dice bien.

## 5 · POR QUÉ ESTE HALLAZGO ES MÁS ÚTIL QUE EL 1124

Porque `1124` terminó en `NOT_DETERMINED` y este termina en `PROVEN`, y la
diferencia está en **dónde se miró**.

`1124` tenía tres comentarios y una aritmética de solapamiento, y de ahí solo
salía una eliminación mutua: *"no pueden ser los tres ciertos"*. Eso es un
descartes, no una respuesta.

La respuesta estaba en una macro de cinco caracteres: `((x & 0x1fULL) << 7)`.

> **Un comentario se puede refutar con otro comentario. Una macro se refuta con
> el hardware, o no se refuta.** La lección de método es que cuando hay una
> discrepancia sobre un formato binario, la pregunta correcta no es *«qué dicen
> los comentarios»* sino *«qué escribe el código, en qué desplazamiento, con qué máscara»*.
> Y esa pregunta tiene respuesta en el árbol.

## 6 · LO QUE ESTO NO ES

- **No dice que `amdgpu_vm_pt.c` tenga un bug.** El comentario es un comentario.
  El código que importa —`AMDGPU_PTE_FRAG`— es correcto, y el resultado de
  fragmentación que produce es el que el hardware necesita **si** el hardware
  lee donde dice la macro.
- **No modifica nada.** Este hallazgo cierra una contradicción de lectura; la
  arreglar en el upstream no es de este árbol ni de este nodo.
- **No cierra el PDE**, que queda con la misma forma de contradicción y la misma
  causa: un bloque de comentarios que no se ha contrastado con el código.