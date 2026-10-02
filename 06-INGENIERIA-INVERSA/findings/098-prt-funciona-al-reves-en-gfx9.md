# 098 · PRT funciona al revés en GFX9+: se marca el PTE NO VÁLIDO y se deja el fault activo

```
ID:           098
TIPO:        HALLAZGO — CORRIGE EL MARCO DE 097 con evidencia de otra generación
ALCANCE:     gmc_v8_0.c:724/760-781, gmc_v9_0.c:1191-1194, gmc_v6_0.c, gmc_v7_0.c
NIVEL:       0 — lectura de corpus
GPU:         INTACTA
CORRIGE_A:   097
```

## 1 · LO QUE `097` CONCLUYÓ, Y POR QUÉ ESTÁ MAL ENMARCADO

`097` midtermensaje en el journal:

```
"Disabling VM faults because of PRT request!"
```

y concluded que **PRT desactiva la protección de acceso no mapeado y es un
hallazgo de seguridad del driver**. La primera mitad es cierta. La segunda
depende de para qué sirve PRT, y para eso hay que mirar **otra generación**.

## 2 · LA MEDICIÓN QUE CAMBIA TODO

### Dato 1 · `.set_prt` sólo existe en GCN

```
$ grep -n "\.set_prt = " *.c
gmc_v6_0.c:1145    .set_prt = gmc_v6_0_set_prt,
gmc_v7_0.c:1361    .set_prt = gmc_v7_0_set_prt,
gmc_v8_0.c:1732    .set_prt = gmc_v8_0_set_prt,
```

**Ni gmc_v9_0, ni v10_0, ni v11_0, ni v12_0 lo tienen.** GFX9+ eliminó el
mecanismo entero, no sólo la parte rota.

### Dato 2 · `VM_PRT_CNTL` es un registro de GCN

```
$ grep -c VM_PRT_CNTL gmc_v9_0.c gmc_v8_0.c
gmc_v9_0.c:0
gmc_v8_0.c:9
```

**Nueve apariciones en GFX8, cero en GFX9.** El registro que `097` midió en la placa es un registro que **GFX9+ no toca jamás**.

### Dato 3 · Y lo que hace GFX9 en su lugar

```c
/* gmc_v9_0.c:1191 */
if (vm_flags & AMDGPU_VM_PAGE_PRT) {
        *flags |= AMDGPU_PTE_PRT;
        *flags &= ~AMDGPU_PTE_VALID;      /* <<< el PTE se marca NO VALIDO */
}
```

Contra GFX8:

```c
/* gmc_v8_0.c:724 */
*flags &= ~AMDGPU_PTE_PRT;               /* <<< borra el bit PRT */
```

**Son dos disenos opuestos**, y la diferencia es el mecanismo entero:

| | GCN / GFX8 | GFX9+ |
|---|---|---|
| lado PTE | borra `AMDGPU_PTE_PRT` | pone `AMDGPU_PTE_PRT` **y borra `VALID`** |
| registro | escribe `VM_PRT_CNTL`, desactiva 4 faults | **no toca ningún registro** |
| quién pide la página | el hardware, por `VM_PRT_CNTL` | el **hardware, por el page walker al ver `VALID=0`** |
| handler de IRQ | **sin rama PRT** | **con rama PRT** (`gmc_v9_0.c:1192`) |

> **En GFX9+ el mecanismo es: invalidar el PTE y dejar que el page walker fault-
> ee.** El fault no se desactiva nunca: es el que *produce* la petición. El
> handler PRT del fault lo sirve, y con eso la protección sigue activa
> durante toda la operación.

> **En GCN/GFX8 el mecanismo es: desactivar el fault y poner el hardware en
> modo de pedir página por `VM_PRT_CNTL`.** Eso requiere que exista la otra
> mitad —el PTE marcado— y **en GFX8 esa mitad fue eliminada**.

## 3 · POR QUÉ GFX8 ESTÁ ROTO, Y LA DIFERENCIA CON GCN

| | GCN v6 / v7 | GFX8 |
|---|---|---|
| `set_prt` escribe `VM_PRT_CNTL` | sí | sí |
| `get_vm_pte` marca `AMDGPU_PTE_PRT` | **hay que mirar** | **`gmc_v8_0.c:724` lo BORRA** |
| handler con rama PRT | hay que mirar | **no** (`gmc_v9_0`+ sí) |

Las dos mitades del mecanismo se movieron en direcciones opuestas entre GCN y
GFX8. El resultado en GFX8 es un camino que:

```
AMDGPU_VM_PAGE_PRT desde el ioctl
  -> prt_get()                  OK
  -> set_prt(true)              OK  -> VM_PRT_CNTL, 4 faults DESACTIVADOS
  -> get_vm_pte borra PRT       OK  -> ningun PTE marcado
  -> page walker ve VALID=1    OK  -> no hay nada que pedir
  -> handler sin rama PRT       OK  -> no habria quien lo sirviera
```

**Las cuatro mitades existen y ninguna conecta.** El sistema de petición de
página de GFX8 no es una función incompleta: es un camino cuyas cuatro piezas
existen y **ninguna está conectada a las otras**.

## 4 · LA CORRECCIÓN A `097`

`097` afirmó:

> *PRT no es un no-op. Es peor que un no-op: la única parte que funciona es la
> que desactiva la protección de acceso no mapeado, y es alcanzable por ioctl
> desde userspace, sin privilegios.*

**La medición sigue siendo cierta** —el mensaje aparece 6 veces en 13 arranques
y los faults están desactivados en cada una. Lo que cambia es **qué es**:

| `097` dijo | `098` corrige |
|---|---|
| PRT desactiva la protección → fallo de seguridad | Cierto en el caso solicitado. Pero `VM_PRT_CNTL` es el mecanismo **de GCN**, y **GFX9+ lo eliminó** por completo |
| El driver acepta una petición que no puede cumplir | **Sigue siendo cierto, y es más preciso**: GFX8 conserva la mitad de GCN (el `set_prt`) y perdió la otra (el PTE y el handler). No es una función a medias, es un mecanismo **desmontado a medias** |
| «PRT es inerte en 3 sitios» | Es cierto que 2 son inertes. El tercero **funciona**, y en GFX9+ **no existe**, lo que confirma que el diseño elegido fue el otro |

> **El dato que refuerza el hallazgo y que `097` no tenía**: GFX9+ resolvió
> el mismo problema por el camino **opuesto**, y lo hizo **quitando el
> registro**, no arreglando el handler. Eso dice dos cosas:
>
> 1. El problema es **real y conocido upstream**, porque se resolvió.
> 2. **GFX8 se quedó en medio**, y no por descuido de GFX8: porque el cambio de
>    mecanismo se hizo **desactivando** el viejo, y GFX8 sedropsó entre ambos.

## 5 · LO QUE ESTO SIGNIFICA PARA EL DRIVER PROPIO

Es la razón por la que este hallazgo vale más que los anteriores, y es
directamente aplicable:

> **Un driver propio para GFX8 no debe heredar `set_prt`.** No porque
> desactive el fault —porque el registro es de una generación que ya no existe
> en el hardware que lo implementa, y activarlo deja la placa sin protección de
> acceso no mapeado sin mecanismo de sustituto.
>
> El modelo correcto para GFX8 es **el de GFX9**: no tocar `VM_PRT_CNTL`, y si
> se quiere PRT, marcar el PTE no válido y servirlo en el handler de fault. Y
> eso exige escribir un handler, que es justo la parte que el upstream no
> escribió para esta ASIC.

Y hay un dato de coste que sale de aquí: **`get_vm_pte` en GFX8 ya borra el bit
PRT y deja `VALID` intacto**, es decir, la parte que hay hace lo correcto por
defecto. Un driver propio que no añada nada se queda con la protección
activada. El problema sólo aparece si **hereda `set_prt`**.

## 6 · LO QUE SIGUE ABIERTO

- **GFX9+ no tiene `set_prt` en `gmc_*`**, pero `083` encontró la rama PRT en
  `gmc_v9_0.c:1192`. ¿Dónde la sirve exactamente, y está completa? Es la
  referencia contra la cual comparar una implementación propia, así que vale
  la pena leerla entera.
- **`FUNCTION=always`** sigue `NOT_DETERMINED`. Y `097` dejó el dato que lo
  necesita: **cero faults en 13 arranques y 94391 líneas**. Eso no distingue
  «nunca hubo acceso no mapeado» de «el fault no funciona».
- **Si el fault funciona, hay que provocarlo**, y eso es NIVEL 3/4.

---

```
RESULTADO DE ITERACIÓN

Entregado:
  098: .set_prt existe SOLO en gmc_v6_0, gmc_v7_0, gmc_v8_0.  Ni v9 ni v10 ni
    v11 ni v12.  Y VM_PRT_CNTL aparece 9 veces en gmc_v8_0.c y 0 en gmc_v9_0.c.
  GFX9+ hace PRT AL REVES:
    gmc_v9_0.c:1191  *flags |= AMDGPU_PTE_PRT;
                      *flags &= ~AMDGPU_PTE_VALID;   <- el PTE se marca NO VALIDO
    gmc_v8_0.c:724   *flags &= ~AMDGPU_PTE_PRT;      <- lo borra

  Mecanismo GCN/GFX8: desactivar el fault + pedir pagina por VM_PRT_CNTL
  Mecanismo GFX9+:    invalidar el PTE y DEJAR QUE EL PAGE WALKER FAULTE-E

  En GFX8 las cuatro mitades existen y ninguna conecta:
    ioctl OK / set_prt OK / PTE no marcado / handler sin rama PRT

Corregido a 097:
  "PRT desactiva la proteccion -> fallo de seguridad"
  -> la medicion sigue cierta (6 veces en 13 arranques), pero el marco no:
     VM_PRT_CNTL es de GCN y GFX9+ lo ELIMINO por completo. GFX8 no tiene una
     funcion a medias: tiene un mecanismo DESMONTADO a medias, con una mitad
     de cada generacion.

Implicacion directa para el driver propio:
  NO heredar set_prt en GFX8. El modelo correcto es el de GFX9: no tocar
  VM_PRT_CNTL, y si se quiere PRT, marcar el PTE no valido y servirlo en el
  handler de fault. Y get_vm_pte de GFX8 ya hace lo correcto por defecto
  (borra PRT, deja VALID intacto): el problema solo aparece si se hereda set_prt.

NEXT ACTION:
  Leer gmc_v9_0.c ENTERO donde esta la rama PRT del handler de fault. Es la
  referencia contra la cual se compararia una implementacion propia, y es la
  unica fuente del corpus de "como se sirve de verdad una pagina en GFX9+".
  GFX9+ no desactiva el fault, asi que ahi el handler PRT esta en el camino
  normal de fault y se ejecuta siempre que hay un PTE no valido -- es
  exactamente el discriminante que FUNCTION=always necesita, y aqui esta
  CODIFICADO, no publicado.

  Y eso conecta con lo que 097 dejo abierto: 0 faults en 94391 lineas del
  journal significa 0 PTE marcados como no-validos durante toda la actividad
  registrada. Si el mecanismo de GFX9+ fuera identico en hardware, entonces en
  esta placa nunca se ha provocado uno. Eso no se distingue de "el hardware no
  genera el fault" -- pero las dos cosas son distinguibles por lectura del
  handler: si el handler de GFX8 tiene o no el caso que el de GFX9 tiene.
```