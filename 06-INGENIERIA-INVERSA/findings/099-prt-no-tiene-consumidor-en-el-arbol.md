# 099 · `AMDGPU_PTE_PRT` se escribe en 6 sitios y no se lee en ninguno: el PRT no tiene consumidor en el árbol

```
ID:           099
TIPO:        PROVEN_ABSENT con denominador — CORRIGE 098 y 083
ALCANCE:     gmc_v6_0/7_0/8_0/9_0/10_0/11_0.c · amdgpu_vm.h · kfd/ · amdgpu_vm_pt.c
NIVEL:       0 — lectura de corpus
GPU:         INTACTA
CORRIGE_A:   098 y 083
```

## 1 · LO QUE HICE MAL, PRIMERO

`098` afirmó, y lo tomé de `083` sin comprobarlo:

> *handler de IRQ: GCN/GFX8 «sin rama PRT» · GFX9+ «con rama PRT»
> (`gmc_v9_0.c:1192`)*

**Es falso.** La línea 1192 de `gmc_v9_0.c` es `get_vm_pte`, no el handler. Y la
búsqueda real:

```
$ grep -n "AMDGPU_PTE_PRT" gmc_v9_0.c
1193:        *flags |= AMDGPU_PTE_PRT;
```

**Una sola aparición en todo el fichero**, y es el lado que *pone* el bit en el
PTE. El handler de fault de GFX9 **tampoco** tiene rama PRT.

Lo cometí por el motivo exacto que este proyecto lleva siete hallazgos
documentando: ** cité un número de línea de un hallazgo anterior sin abrir el
fichero**. `083` lo afirmó, `098` lo repitió, y entre los dos se volvió
"evidencia" sin haber sido medida nunca.

## 2 · LA MEDICIÓN REAL

`AMDGPU_PTE_PRT` en **todo** el árbol:

```
gmc_v6_0.c:385     *flags &= ~AMDGPU_PTE_PRT;      BORRA
gmc_v7_0.c:507     *flags &= ~AMDGPU_PTE_PRT;      BORRA
gmc_v8_0.c:722     *flags &= ~AMDGPU_PTE_PRT;      BORRA
gmc_v9_0.c:1193    *flags |=  AMDGPU_PTE_PRT;      PONE
gmc_v10_0.c:511    *flags |=  AMDGPU_PTE_PRT;      PONE
gmc_v11_0.c:502    *flags |=  AMDGPU_PTE_PRT;      PONE
amdgpu_vm.h:73     #define AMDGPU_PTE_PRT (1ULL << 51)
amdgpu_vm.h:95     ... | AMDGPU_PTE_PRT)
```

Seis escrituras, **cero lecturas**. Y:

```
AMDGPU_PTE_PRT leido en kfd/            : 0
AMDGPU_VM_PAGE_PRT en kfd/              : 0
AMDGPU_VM_PAGE_PRT en amdgpu_vm_pt.c    : 0
```

Y quien llama a `amdgpu_vm_prt_get` — que es lo que activa el PRT:

```
amdgpu_vm.c:1530   amdgpu_vm_prt_get(adev);     (alta de fence)
amdgpu_vm.c:1792   amdgpu_vm_prt_get(adev);     (bo_va_add_mapping)
amdgpu_vm.c:2100   amdgpu_vm_prt_get(adev);     (borde antes)
amdgpu_vm.c:2115   amdgpu_vm_prt_get(adev);     (borde después)
```

**Todos en `amdgpu_vm.c`, el camino del DRM. Ninguno en KFD ni en el camino SVM.**

> **`PROVEN_ABSENT`: el bit `AMDGPU_PTE_PRT` no tiene consumidor en ningún
> fichero del árbol.** Seis sitios lo escriben, ninguno lo lee, y el
> unico camino que lo activa (`amdgpu_vm_prt_get`) no esta en KFD ni en SVM.

## 3 · LA TABLA COMPLETA, Y ES DISTINTA A LA DE `098`

| | GCN v6 / v7 | GFX8 | GFX9 / v10 / v11 |
|---|---|---|---|
| `AMDGPU_PTE_PRT` en `get_vm_pte` | **borra** | **borra** | **pone** |
| `set_prt` / `VM_PRT_CNTL` | sí | sí | **no** |
| registra `GFX_PAGE_INV_FAULT` | `gmc_v7_0` | `gmc_v8_0` | **ninguno** |
| `vm_fault.funcs` | el suyo | `gmc_v8_0_irq_funcs` | el suyo |
| llama `amdgpu_vm_handle_fault` | **no** | **no** | por `amdgpu_gmc.c` |
| **consumidor del bit PRT** | **no** | **no** | **no** |

```
gmc_v8_0.c llama a amdgpu_vm_handle_fault : 0
gmc_v9_0.c llama a amdgpu_vm_handle_fault : 0
quien lo llama: amdgpu_gmc.c  amdgpu_vm.c  gmc_v12_1.c
```

**GFX9+ no registra `GFX_PAGE_INV_FAULT`** — sólo `gmc_v7_0.c` y `gmc_v8_0.c` lo
hacen. Es la tercera señal de que **PRT pertenece a GCN** y que GFX9+ sólo
conserva el lado del PTE.

## 4 · QUÉ SIGNIFICA

Hay dos lecturas posibles, y **el corpus no las distingue**:

**(a) El consumidor está fuera del driver.** El hardware ve el PTE, pide la
página, y quien la sirve es un componente de firmware (PSP/SMU) o un servicio
del host que no pasa por este código. `033` yaocumentó que el
comportamiento de firmware de GFX8 **no está publicado**, así que esta lectura
no es descartable por el corpus.

**(b) El PRT está incompleto upstream en todas las generaciones.** Con
denominador: 6 escrituras, 0 lecturas, 0 en KFD, 0 en SVM.

**Lo que sí se puede afirmar sin decidir entre ellas**: en GFX8, la única
generación donde PRT se activa de verdad (`097` lo medió 6 veces en el journal),
**el PTE nunca se marca y nadie lo lee**. El camino que se ejecuta en esta placa
es: ioctl → `set_prt(true)` → **faults desactivados** → PTE sin PRT → nada que
servir. Las tres piezas que pourraient cerrar el circuito están, y ninguna
conecta con las otras.

## 5 · LA CORRECCIÓN A `098`, Y LO QUE `098` AÚN TIENE RAZÓN

| afirmación | estado tras `099` |
|---|---|
| `VM_PRT_CNTL` es de GCN y GFX9+ lo eliminó | **sigue cierto** — 9 vs 0 apariciones |
| `set_prt` no existe en GFX9+ | **sigue cierto** |
| GFX8 no debe heredar `set_prt` | **sigue cierto**, y ahora con más fuerza |
| «GFX9+ tiene rama PRT en el handler» | **FALSA** — retractada por este hallazgo |
| «PRT funciona» en GFX9+ | **RETIRADA** — no hay consumidor del bit en ninguna generación |

Lo que `098` acertó y no se toca: **el mecanismo de GFX8 está desconectado**, y
un driver propio no debe heredar `set_prt`. Eso no dependía de la rama PRT del
handler de GFX9, dependía de los tres datos que sí están medidos.

## 6 · ERRORES PROPIOS

| error | coste |
|---|---|
| cité `gmc_v9_0.c:1192` como «rama PRT del handler» sin abrir el fichero | un hallazgo (`098`) construido sobre una cita no verificada de `083` |
| repetí en `098` la afirmación sin comprobarla | el mismo error, una iteración después, exactamente igual |

> Es la **segunda vez** en tres hallazgos que cito un número de línea de otro
> hallazgo sin verificarlo. Y la primera vez que el error no fue mío de origen
> sino **heredado**: `083` lo afirmó sin comprobarlo también.
>
> `047`/`089`: **un número de línea citado no es evidencia; es un
> puntero.** Y un puntero que nadie abre se convierte en cita en dos pasos.

---

```
RESULTADO DE ITERACIÓN

Entregado:
  099: AMDGPU_PTE_PRT se ESCRIBE en 6 ficheros (gmc_v6_0/7_0/8_0/9_0/10_0/11_0)
    y NO SE LEE en ninguno. Denominador explicito: 6 escrituras, 0 lecturas.
    kfd/: 0.  amdgpu_vm_pt.c (SVM): 0.
    Los 4 llamadores de amdgpu_vm_prt_get estan todos en amdgpu_vm.c (DRM).

  Tabla completa por generacion (corrige la de 098):
    GCN v6/v7   borra PRT · set_prt si · registra GFX_PAGE_INV_FAULT · sin handle_fault
    GFX8        borra PRT · set_prt si · registra GFX_PAGE_INV_FAULT · sin handle_fault
    GFX9/10/11  PONE PRT · set_prt NO · NO registra GFX_PAGE_INV_FAULT
    TODAS: cero consumidor del bit PRT

Retractado por este hallazgo:
  083 y 098: "GFX9/10/11/12 tienen rama PRT en el handler de fault"
  -> FALSO en las cuatro. gmc_v9_0.c:1192 es get_vm_pte, no el handler, y es
     el unico uso de AMDGPU_PTE_PRT en ese fichero.

Corregido en 098:
  "PRT funciona al reves en GFX9+" -> la parte de la SEMANTICA del mecanismo
  sigue siendo correcta (poner PRT + borrar VALID frente a set_prt), pero la
  parte de que "funciona" se retira: no hay consumidor del bit en NINGUNA
  generacion.

Se mantiene de 098:
  - VM_PRT_CNTL es de GCN (9 vs 0)
  - GFX8 no debe heredar set_prt en un driver propio
  - el mecanismo de GFX8 esta desconectado

NEXT ACTION:
  El consumidor del bit PRT no esta en el codigo, y eso abre la pregunta que
  decide entre las dos lecturas que 099 dejo abiertas:

  (a) lo sirve el FIRMWARE (PSP/SMU), que no esta publicado -> 033
  (b) PRT esta incompleto upstream en todas las generaciones

  Y hay un dato que ya separa parte de las dos, y es de lectura: la placa ha
  pedido pagina 6 veces (097) y en ningun caso se ha servido nada, porque el
  PTE no se marco. Si el firmware fuera el consumidor, el firmware habria
  pedido una pagina para un PTE que no existe, y eso no aparece en ningun log.

  O sea: en ESTA PLACA, el firmware no ha podido servir nada, porque no habia
  PTE que servir. La hipotesis (a) no queda descartada, pero tampoco puede
  explicar lo que se midio: 0 faults, 0 peticiones servidas, 0 PTE marcados.

  Y el paso que decide las dos, y es de lectura pura: smc_msg que mencione
  PRT, page request, o page fault en el camino SMC/PSP. Si el firmware tiene
  ese camino, existe en el corpus o en el log de SMC que 084/085 ya miraron.
  Si no existe, la lectura (b) gana por descarte, y PRT es una funcion
  incompleta upstream en las tres generaciones.
```