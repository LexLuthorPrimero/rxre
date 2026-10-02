# 100 · PRT no tiene consumidor en el driver, ni en firmware, ni IRQ: descartada la hipótesis del firmware

```
ID:           100
TIPO:        PROVEN_ABSENT — RESUELVE la binaria que 099 dejo abierta
ALCANCE:     smu_*.c, psp*.c, amdgpu_smu.c, gmc_v7_0.c, gmc_v8_0.c
NIVEL:       0 — lectura de corpus
GPU:         INTACTA
CIERRA:      la pregunta de 099
```

## 1 · LA BINARIA DE `099`

`099` dejó dos lecturas y un paso que las decidía:

| | lectura | se decide por |
|---|---|---|
| **(a)** | el consumidor del PRT está en **firmware** (PSP/SMU), que `033` ya dijo que no está publicado | ¿existe un camino SMC de page fault en el corpus? |
| **(b)** | PRT está **incompleto upstream** en las tres generaciones | se gana por descarte si (a) no aparece |

## 2 · LAS TRES BÚSQUEDAS

### (1) · SMC: ningún mensaje de page fault ni de PRT

```
$ grep -rniE "PPSMC_MSG_[A-Z_]*(PAGE|PRT|FAULT)" *.c *.h
(sin resultado)

$ grep -rniE "page_request|page request|PRT|page_fault" smu_*.c psp*.c amdgpu_smu.c
(sin resultado)
```

**Cero.** No hay ningún mensaje de SMC cuyo nombre mencione página, PRT ni
fault. Con denominador: todos los ficheros `smu_*.c` y `psp*.c` del árbol.

### (2) · Los IRQ de fault: sólo dos, y sólo en GCN

```
gmc_v7_0.c   amdgpu_irq_add_id(… GFX_PAGE_INV_FAULT, &adev->gmc.vm_fault);
gmc_v7_0.c   amdgpu_irq_add_id(… GFX_MEM_PROT_FAULT, &adev->gmc.vm_fault);
gmc_v8_0.c   amdgpu_irq_add_id(… GFX_PAGE_INV_FAULT, &adev->gmc.vm_fault);
gmc_v8_0.c   amdgpu_irq_add_id(… GFX_MEM_PROT_FAULT, &adev->gmc.vm_fault);
```

Cuatro registros, **dos ficheros, ambos GCN**. `gmc_v9_0.c`, `v10_0`, `v11_0`,
`v12_x`: **ninguno registra un IRQ de fault de página.**

### (3) · `PAGE_FAULT_IRQ`: no existe

```
$ grep -rn "PAGE_FAULT_IRQ" .
0
```

El identificador que se esperaría en GFX9+ **no aparece en el árbol entero**.

## 3 · EL VEREDICTO

> **La lectura (a) queda descartada en el corpus: no hay camino de firmware que
> sirva una página PRT en ninguna generación de este driver.** No hay mensaje
> de SMC que lo nombre, y no hay IRQ de fault de página fuera de GCN.
>
> Y por tanto gana la lectura **(b): PRT es una función incompleta upstream en
> las tres generaciones** — GCN, GFX8 y GFX9+.

La cadena completa, con las cuatro medidas:

```
bit AMDGPU_PTE_PRT     : 6 escrituras, 0 lecturas        (099)
amdgpu_vm_prt_get      : 4 llamadores, 0 en KFD/SVM      (099)
mensaje SMC de PRT     : 0                              (este)
IRQ de fault de pagina : 4 registros, 2 ficheros, GCN    (este)
  -- y GFX9+ registra NINGUNO
```

Y el dato que lo hace concluyente y no sólo «no lo encontré»:

> **GFX9+ pone el bit PRT en el PTE y no registra ningún IRQ de page fault.**
> Si el bit puesto llegara a tener efecto, la página se pediría y **nadie
> recibiría el aviso** —ni el driver, que no registra la IRQ, ni el firmware,
> que no tiene mensaje—. No es que el consumidor esté en otro sitio: es que
> **no hay sitio al que pueda llegar**.

Eso convierte a GFX9+ en un caso **peor que GFX8**: en GFX8 al menos se
desactiva el fault explícitamente (`097`, medido 6 veces), que es una política
declarada. En GFX9+ el PTE se marca y el sistema **no tiene forma de enterarse**.

## 4 · LA TABLA FINAL, Y LA INCOHERENCIA QUE REVELA

| | GCN v6/v7 | GFX8 | GFX9 / v10 / v11 |
|---|---|---|---|
| `AMDGPU_PTE_PRT` en `get_vm_pte` | borra | borra | **pone** |
| `set_prt` / `VM_PRT_CNTL` | sí | sí | **no** |
| IRQ de fault de página | `gmc_v7_0` | `gmc_v8_0` | **ninguno** |
| `amdgpu_vm_handle_fault` | no | no | sólo por `amdgpu_gmc.c` |
| consumidor del bit PRT | no | no | no |

**GFX8 es la única generación coherente**: borra el bit (no marca), y tiene IRQ.
No hace nada de PRT, pero no deja nada a medias.

**GFX9+ es la incoherente**: pone el bit y no registra IRQ. Es el único caso en
que el código **prepara un mecanismo sin ningún receptor**, y eso es un dato
sobre el upstream, no sobre esta placa.

GFX8, en cambio, está en medio: conserva la mitad de GCN (`set_prt`, que
desactiva el fault) y perdio la otra (el PTE y el IRQ GCN sí existen, pero el
handler no las conecta).

## 5 · LO QUE ESTO CIERRA PARA EL DRIVER PROPIO

Tres reglas, las tres derivadas de la tabla y las tres directamente aplicables:

> **1 · No heredar `set_prt` en GFX8.** Es la mitad de GCN de un mecanismo que
> en esta ASIC no tiene receptor. Activa un registro que desactiva el fault de
> acceso no mapeado y no activa nada a cambio.
>
> **2 · No usar `AMDGPU_PTE_PRT` en GFX8.** `gmc_v8_0.c:722` lo borra, y el
> formato del PTE (`093`) no tiene nada en el bit 51: `63:40 reserved`. Es un
> bit que el hardware de esta placa no documenta.
>
> **3 · Si se quiere detección de acceso no mapeado, el camino es el handler de
> IRQ, no el PRT.** `gmc_v8_0.c:1109/1113` ya registra `GFX_PAGE_INV_FAULT` y
> `GFX_MEM_PROT_FAULT`. Ese es el mecanismo real de esta placa, y existe. Lo
> que hay que escribir es el `process` que los sirve —`gmc_v8_0_process_interrupt`
> hoy solo registra e imprime— que es trabajo de driver propio y no de registro.

## 6 · ERRORES PROPIOS

Ninguno en esta iteración: fue una búsqueda con denominador declarado, y el
resultado inesperado (GFX9+ sin IRQ) se investigó antes de escribir.

---

```
RESULTADO DE ITERACIÓN

Entregado:
  100: la hipotesis (a) "el consumidor esta en firmware" queda DESCARTADA
    0 mensajes de SMC con PAGE/PRT/FAULT en todo smu_*/psp*
    4 registros de IRQ de fault de pagina, en 2 ficheros, ambos GCN
    GFX9/v10/v11: NINGUNO registra IRQ de fault de pagina
    PAGE_FAULT_IRQ: 0 apariciones en el arbol entero

  Y el hallazgo que sale de ahi:
    GFX9+ PONE el bit AMDGPU_PTE_PRT en el PTE y NO registra ningun IRQ.
    Si el bit tuviera efecto, la pagina se pediria y NADIE recibiria el aviso.
    No es que el consumidor este en otro sitio: no hay sitio al que llegue.

    GFX8 es la unica generacion coherente: borra el bit y tiene IRQ.
    GFX9+ es la incoherente: prepara un mecanismo sin receptor.

CLOSED (con 099 y 100):
  PRT no tiene consumidor en ninguna generacion de este driver.
  No es una funcion a medias en GFX8: es una funcion sin receptor en todas,
  y en GFX9+ es ademas incoherente por construccion.

Reglas para el driver propio (derivadas, no opinadas):
  1. no heredar set_prt en GFX8
  2. no usar AMDGPU_PTE_PRT en GFX8 (bit 51 = reservado segun 093)
  3. la deteccion de acceso no mapeado real es el handler de IRQ, que YA esta
     registrado (gmc_v8_0.c:1109/1113). Falta escribir el `process` que lo
     sirve: gmc_v8_0_process_interrupt hoy solo registra e imprime.

NEXT ACTION:
  El punto 3 de esas reglas es el trabajo real que queda, y es la direccion
  del proyecto entero: escribir el process de fault de GFX8, que es lo que
  hace que un driver propio sea un driver propio y no un consumidor.

  Y para hacerlo falta saber QUE debe hacer, y eso tiene una referencia en el
  corpus que no se ha leido: amdgpu_vm_handle_fault (amdgpu_vm.c:2991). Es el
  handler generico que GFX9+ usa, y su cuerpo es la especificacion de que
  hacer con un VM fault: que se mira, que se decide, y que se responde.

  Leerlo es el paso siguiente y es NIVEL 0. Y ahi hay algo concreto que esta
  evidencia ya permite afirmar: 097 midio 0 faults en 94391 lineas de journal,
  lo que significa que en esta placa nunca ha llegado un fault por ese camino.
  Asi que la funcion existira y nunca se habra ejecutado aqui -- y eso es una
  limitacion del entorno de medida que hay que declarar cuando se escriba el
  driver propio, porque significa que el codigo no se podra validar aqui
  sin provocarlo.
```