# 1127 — `vmid0_page_table_block_size` es un campo de GFX9 en adelante: en GFX8 se lee y nadie lo escribe, y el GART no lo usa

```text
AGENCIA=RX550-INVESTIGACION · WORK_CLASS=AGENT-RE-TOOLING
GENERADO=2026-10-04 · MEDIDO=EN ESTA HOST · CORPUS=rx550-upstream-7.2.8
AFECTADO=gfxhub_v1_0.c:226-227    (GFX8 LO LEE)
         gmc_v9_0.c:1769,1772     (los unicos que lo ASIGNAN, con valor 12 o 0)
         gmc_v12_0.c:786,789      (idem)
         amdgpu_gmc.c:44-47       (amdgpu_gmc_is_pdb0_enabled, de donde sale el 12)
         amdgpu_gmc.c:1153-1180   (el GART, que NO lo usa en esta generacion)
       1126-el-9-del-gart-es-una-conversion-de-unidades.md  §3bis
ESTADO=PROVEN-CAMPO-SIN-PRODUCTOR-EN-GFX8 · GPU INTACTA · lectura de corpus
```

## 0 · EL HECHO

MEDIDO sobre **todas** las asignaciones del campo en el árbol:

```
  gmc_v9_0.c:1769    vmid0_page_table_block_size = 12
  gmc_v9_0.c:1772    vmid0_page_table_block_size = 0
  gmc_v12_0.c:786    vmid0_page_table_block_size = 12
  gmc_v12_0.c:789    vmid0_page_table_block_size = 0
```

**Cuatro asignaciones, dos ficheros, ninguno de GFX8.** Y en la ruta de nuestra
ASIC el campo **se lee**:

```c
gfxhub_v1_0.c:226-227   (dentro de gfxhub_v1_0_enable_system_domain)
  tmp = REG_SET_FIELD(tmp, VM_CONTEXT0_CNTL, PAGE_TABLE_BLOCK_SIZE,
                      adev->gmc.vmid0_page_table_block_size);
```

Es decir: **GFX8 escribe en el registro `PAGE_TABLE_BLOCK_SIZE` un campo que
nadie ha asignado para GFX8.** Lo que llegue ahí es lo que hubiera en el
`kmalloc` del dispositivo.

## 1 · POR QUÉ ESO ES NORMAL Y NO ES UN BUG — Y POR QUÉ ES IGUAL DE PELIGROSO

La respuesta está en **dónde** viven las dos cosas:

```
  GFX8:      lee  el campo en gfxhub_v1_0.c:227   ->  PAGE_TABLE_BLOCK_SIZE
  GFX9+:     ASIGNA el campo en gmc_v9_0.c:1769   ->  12 o 0
  GFX9+:     usa  el campo en el GART             ->  pde0_page_size
```

**El GART de GFX8 no usa el campo.** MEDIDO: el bucle de
`amdgpu_gmc.c:1178-1180` que llena las PDE0 calcula

```c
u64 pde0_page_size = (1ULL<<adev->gmc.vmid0_page_table_block_size)<<21;
```

pero ese cálculo es de `gmc_v9_0.c` / `gmc_v12_0.c`, donde el campo ya está
asignado. En GFX8 el GART se construye por otro camino —el PDB0 clásico— que no
pasa por `vmid0_page_table_block_size`.

> **El campo no está roto: es un campo de GFX9 en adelante, y GFX8 lo lee por
> herencia de un registro compartido sin haberlo inicializado.** Eso es un hecho
> normal en un driver que evolucionó, y no lo clasifico de defecto.

Y es justo por eso que es peligroso. Porque:

```
  si vale 0 (lo que hubiera en el kmalloc)  ->  PAGE_TABLE_BLOCK_SIZE = 0
  si vale 9                                  ->  PAGE_TABLE_BLOCK_SIZE = 9
```

**El hardware recibe un valor que nadie eligió.** Puede que 0 sea lo correcto
para una page table de 2 niveles —que es lo que hace GFX8— y puede que no. El
corpus **no lo dice**.

## 2 · EL 12 DE GFX9 NO ES UN NÚMERO DE FRAGMENTACIÓN

Y esta es la parte que separa los dos usos del mismo campo, porque se parecen y
no son lo mismo.

MEDIDO el productor del `12`, en `gmc_v9_0.c:1768-1773`:

```c
if (amdgpu_gmc_is_pdb0_enabled(adev)) {
    adev->gmc.vmid0_page_table_depth = 1;
    adev->gmc.vmid0_page_table_block_size = 12;
} else {
    adev->gmc.vmid0_page_table_depth = 0;
    adev->gmc.vmid0_page_table_block_size = 0;
}
```

Y `amdgpu_gmc_is_pdb0_enabled`, en `amdgpu_gmc.c:44-47`:

```c
return adev->gmc.xgmi.connected_to_cpu || amdgpu_virt_xgmi_migrate_enabled(adev);
```

O sea: **el 12 significa "hay un puente XGMI hacia la CPU"**, y el 0 significa
"esta GPU es la de la CPU". No tiene nada que ver con `fragment_size = 9` de esta
ASIC, ni con el `9` de `amdgpu_gmc.c:1167` que `1126` explica.

> **Tres números parecidos en tres contextos distintos**: `fragment_size = 9`
> (fragmentación del L1 TLB), `+ 9*1` en `amdgpu_gmc.c:1167` (conversión de
> unidades `21−12`), y `12` en `gmc_v9_0.c:1769` (presencia de puente XGMI). Con
> un corpus donde conviven, cualquier razonamiento que los mezcle produce un
> número plausible y equivocado — que es el modo de fallo que este proyecto
> lleva documentando desde el principio.

## 3 · LO QUE ESTO DEJA ABIERTO, Y ES LO IMPORTANTE

**No dice qué valor recibe el hardware en esta RX550.** Eso es `NOT_DETERMINED`
con el corpus, y no se convierte en nada más.

Cerrarlo requiere una de dos cosas, y las dos son de runtime:

1. **Leer `mmVM_CONTEXT0_CNTL`** de esta GPU después del arranque y ver qué hay
   en `PAGE_TABLE_BLOCK_SIZE`. Es un registro legible por MMIO y **es del nodo de
   runtime**.
2. Leer `/sys/kernel/debug/dri/*/amdgpu_vm_fault*` o cualquier cosa que exponga
   el block size effective.

Y hay un camino más barato que no requiere root ni GPU: **mirar el BTF o el
`.ko` compilado** para ver si el campo llega a cero o conserva basura. Eso es de
este nodo y es lo que haría en el siguiente ciclo.

> Lo que **no** voy a hacer es suponer que vale 0 porque "lo habitual es que el
> kmalloc devuelva cero". Eso es una suposición sobre la implementación de un
> asignador, no una medida, y `1126` ya mostró que toda la aritmética del GART
> depende de ese valor. **Un supuesto aquí cambia el número de entradas de PDE0
> de 4 a 1025**, y eso no es un detalle de lectura.

## 4 · LA CADENA COMPLETA, PARA QUE NO HAYA QUE REDESCUBRIRLA

```
  REGISTRO  mmVM_CONTEXT0_CNTL.PAGE_TABLE_BLOCK_SIZE
     ^
     |  se escribe con el campo del driver
     |
  gfxhub_v1_0_enable_system_domain()          [gfxhub_v1_0.c:226]
     |
     v  lee
  adev->gmc.vmid0_page_table_block_size
     |
     +-- ASIGNADO por  gmc_v9_0.c:1769  (12 si XGMI, 0 si no)   [GFX9]
     +-- ASIGNADO por  gmc_v12_0.c:786 (12 si XGMI, 0 si no)   [GFX12]
     +-- SIN PRODUCTOR para GFX8                                 [AQUI]
     |
     v  (solo en GFX9+, no en GFX8)
  pde0_page_size = (1 << block_size) << 21    [amdgpu_gmc.c:1156]
     |
     v
  bucle que llena las PDE0 del GART           [amdgpu_gmc.c:1178]
```

## 5 · POR QUÉ ESTE HALLAZGO ES MÁS ÚTIL QUE UN "FALTA INICIALIZAR"

Porque el hallazgo naïve habría sido *«falta inicializar un campo»*, que es una
lista de tareas. Lo que hay aquí es una **cadena**, y la cadena dice tres cosas
que la lista no dice:

1. **El campo no es de esta generación**, así que no hay que "arreglarlo": hay
   que saber qué escribe el hardware cuando recibe basura.
2. **El mismo nombre significa dos cosas** según generación —block size de la
   PDB0 en GFX9+ frente a nada en GFX8— y confundirlas da números plausibles.
3. **La aritmética del GART depende de un valor que nadie eligió**, lo que baja
   `1126` de `PROVEN` a condicional sin cambiar una sola línea de su aritmética.

> La última es la que importa. `1126` dice que con `block_size = 9` el GART tiene
> 4 entradas. Ese "con" **no lo sostiene ninguna lectura**. Es el mismo patrón
> de `1124`: un número correcto con una condición que nadie ha medido.

## 6 · ESTADO

```
  vmid0_page_table_block_size
     ASIGNADO en            GFX9 (12/0), GFX12 (12/0)
     LEIDO en               GFX8 (gfxhub_v1_0.c:227), GFX9+, GFX12
     PRODUCTOR para GFX8    NINGUNO            PROVEN
     valor efectivo en HW   NOT_DETERMINED     -> nodo de runtime, o BTF/.ko
     usa el GART de GFX8    NO                 PROVEN (el GART de GFX8 es otro)

  aritmetica de 1126         CONDICIONAL a este valor

  GPU     INTACTA
  sudo    NO usado
  corpus  solo lectura
```

```
OBSERVATION_FOR_MAIN_AGENT
  `mmVM_CONTEXT0_CNTL.PAGE_TABLE_BLOCK_SIZE` en esta RX550 recibe un valor que
  el driver no asigna para GFX8.  Es un registro legible por MMIO y una lectura
  lo cierra.  Mientras no se lea, la aritmética del GART (1126) es condicional.
  Si el agente principal tiene una lectura de MMIO de este registro, es el dato
  que falta a dos hallazgos.
```