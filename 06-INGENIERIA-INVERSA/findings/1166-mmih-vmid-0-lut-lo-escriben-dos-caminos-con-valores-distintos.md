# 1166 — el registro `mmIH_VMID_0_LUT` lo escriben dos caminos con valores distintos, y uno de ellos espera en un busy-wait

```text
AGENCIA=RX550-INVESTIGACION · WORK_CLASS=AGENT-RE-TOOLING
GENERADO=2026-10-04 · MEDIDO=EN ESTA HOST · CORPUS=rx550-upstream-7.2.8
AFECTADO=gmc_v8_0.c:679-683        gmc_v8_0_emit_pasid_mapping   -> WREG, sin espera
         amdgpu_amdkfd_gfx_v8.c:88-110  kgd_set_pasid_vmid_mapping -> WREG + busy-wait
         amdgpu_vm.c:806-808, 847-849  las DOS condiciones que lo disparan
CIERRA=los dos NOT_DETERMINED de
        1153-dos-vias-de-invalidacion-de-tlb-en-gfx8.md
        (los campos VALID_MASK/PASID_MASK, y el RREG32 de respuesta)
ESTADO=PROVEN · dos productores del MISMO registro con valores DISTINTOS
```

## 0 · LO QUE `1153` DEJÓ SIN MEDIR, Y QUE ESTE HALLAZGO CIERRA

`1153` medió las dos vías de invalidación de TLB y dejó dos huecos:

> *Qué valores toma `ATC_VMID0_PASID_MAPPING__PASID_MASK` ni qué bits tiene
> `VALID_MASK`. No se han leído los campos.*

Y de paso sale algo que no había medido: en la vía por PASID, el
driver **lee 15 registros `mmATC_VMID0_PASID_MAPPING`** para construir la máscara.

Esos registros **se escriben en otro sitio**, y ese sitio no es el mismo que los
lee. Y al buscarlo aparece que **hay dos escritores del registro de mapeo**, con
valores distintos.

## 1 · PRODUCTOR A — EL DRIVER, DESDE EL RING

`gmc_v8_0.c:679-683`, completo:

```c
static void gmc_v8_0_emit_pasid_mapping(struct amdgpu_ring *ring, unsigned int vmid,
                                        unsigned int pasid)
{
        amdgpu_ring_emit_wreg(ring, mmIH_VMID_0_LUT + vmid, pasid);
}
```

**Tres cosas, y las tres importan:**

1. Escribe `pasid` **pelado**. Sin máscara de validez.
2. Va por `amdgpu_ring_emit_wreg`, o sea **emite un comando PM4 al ring**. No es
   un MMIO del kernel: es un comando que la GPU ejecutará.
3. **No espera nada.** No hay busy-wait, no hay `UPDATE_STATUS`.

Y se dispara desde `amdgpu_vm.c:847-849`:

```c
if (pasid_mapping_needed)
        amdgpu_gmc_emit_pasid_mapping(ring, job->vmid, job->pasid);
```

con la condición de `amdgpu_vm.c:806-808`:

```c
pasid_mapping_needed &= adev->gmc.gmc_funcs->emit_pasid_mapping &&
```

es decir: **solo si el fence del `pasid_mapping` no está señalado**.

## 2 · PRODUCTOR B — KFD, DESDE ESPACIO DE USUARIO, CON ESPERA

`amdgpu_amdkfd_gfx_v8.c:88-110`, completo:

```c
static int kgd_set_pasid_vmid_mapping(struct amdgpu_device *adev, u32 pasid,
                                      unsigned int vmid, uint32_t inst)
{
        /*
         * We have to assume that there is no outstanding mapping.
         * The ATC_VMID_PASID_MAPPING_UPDATE_STATUS bit could be 0 because
         * a mapping is in progress or because a mapping finished
         * and the SW cleared it.
         * So the protocol is to always wait & clear.
         */
        uint32_t pasid_mapping = (pasid == 0) ? 0 : (uint32_t)pasid |
                        ATC_VMID0_PASID_MAPPING__VALID_MASK;

        WREG32(mmATC_VMID0_PASID_MAPPING + vmid, pasid_mapping);

        while (!(RREG32(mmATC_VMID_PASID_MAPPING_UPDATE_STATUS) & (1U << vmid)))
                cpu_relax();
        WREG32(mmATC_VMID_PASID_MAPPING_UPDATE_STATUS, 1U << vmid);

        /* Mapping vmid to pasid also for IH block */
        WREG32(mmIH_VMID_0_LUT + vmid, pasid_mapping);

        return 0;
}
```

Cuatro diferencias con el productor A, y ninguna es cosmética:

| | A: `gmc_v8_0_emit_pasid_mapping` | B: `kgd_set_pasid_vmid_mapping` |
|---|---|---|
| valor en `mmIH_VMID_0_LUT` | `pasid` | `pasid \| VALID_MASK`, o `0` si pasid==0 |
| cómo llega | **comando PM4 por el ring** | **MMIO del kernel** |
| espera hardware | **ninguna** | **`cpu_relax()` hasta que un bit se ponga** |
| escribe la tabla ATC | **no** | **sí**, y luego la borra con un `WREG32` |

## 3 · EL HECHO QUE IMPORTA: ESCRIBEN VALORES DISTINTOS EN EL MISMO REGISTRO

```
  A escribe:   mmIH_VMID_0_LUT + vmid  <-  pasid
  B escribe:   mmIH_VMID_0_LUT + vmid  <-  pasid | ATC_VMID0_PASID_MAPPING__VALID_MASK
```

**El mismo registro, el mismo campo, dos valores distintos.** Y no es que uno sea
una versión antigua del otro: están en el mismo driver, conviven, y se disparan
por condiciones **independientes**.

La consecuencia que se puede afirmar sin hardware:

> Si `ATC_VMID0_PASID_MAPPING__VALID_MASK` tiene un bit que el IH interpreta, los
> dos productores **dejan el registro en estados distintos**, y el último en
> escribir manda. Es decir: **quién escribe el último decide qué ve el IH**, y no
> hay nada en el código que coordine a los dos.

Y hay un dato estructural que hace la pregunta más afilada: **el productor B
también escribe la tabla ATC que el productor A no toca**. O sea que B hace dos
cosas donde A hace una, y la segunda es precisamente la que `1153` vio leer.

## 4 · EL PROTOCOLO DE ESPERA, QUE ESTÁ DOCUMENTADO POR EL PROPIO CÓDIGO

El comentario de B es la parte más útil del hallazgo, porque **es el driver
explicando un problema de hardware que no puede ver**:

> *We have to assume that there is no outstanding mapping. The
> `ATC_VMID_PASID_MAPPING_UPDATE_STATUS` bit could be 0 because a mapping is in
> progress **or because a mapping finished and the SW cleared it**. So the
> protocol is to always wait & clear.*

Es un protocolo **write-wait-clear**, y la razón de hacerlo así es que un `0` en
ese bit es **ambiguo**: significa las dos cosas. El driver no puede distinguir
«en curso» de «terminado», y por eso espera y limpia siempre.

Y hay un detalle de diseño que solo se ve leyendo la función entera:

```c
WREG32(mmATC_VMID_PASID_MAPPING_UPDATE_STATUS, 1U << vmid);
```

**Escribe 1, no 0.** Escribir un 1 en un registro de estado，habitualmente sería clear-on-1.
Y el comentario lo confirma: *"wait & clear"* con un `WREG32` de `1 << vmid`.
O sea: **el bit es write-1-to-clear**, y eso no está en el nombre del campo ni en
ningún comentario del driver.

> **Un driver propio que implemente este mapeo tiene que reproducir el
> write-1-to-clear, no solo el busy-wait.** Y si se equivoca en eso, el síntoma no
> es un fallo visible: es un `UPDATE_STATUS` que se queda en 1 y un mapa que
> parece funcionar porque el bit ya estaba puesto.

## 5 · LO QUE CIERRA, Y LO QUE SIGUE ABIERTO

**Cierra** (`PROVEN`):

- El valor que A escribe es `pasid` **sin** máscara; el de B es
  `pasid | VALID_MASK`, y `0` si `pasid == 0`.
- `ATC_VMID0_PASID_MAPPING__VALID_MASK` es un **bit de la palabra de mapeo** que
  KFD pone cuando `pasid != 0`, y es lo que permite distinguir «hay PASID» de
  «hay PASID 0». Eso responde a lo que `1153` dejó como *no leído*.
- El protocolo es **write, wait, clear**, y el clear es **escribir un 1**.
- La escritura del IH por KFD es un **MMIO síncrono**; la del driver es un
  **comando PM4 asíncrono** por el ring.

**No cierra** (`NOT_DETERMINED`):

- **Si los dos valores son equivalentes para el hardware.** Que
  `ATC_VMID0_PASID_MAPPING` lleve `VALID_MASK` y `mmIH_VMID_0_LUT` no es lo mismo:
  son registros distintos. Si el campo `VALID` existe solo en el primero, A
  escribe un valor que el segundo quizá no entiende. Eso **no se puede responder
  sin la guía de hardware** y sin leer un registro real.
- **Quién escribe el último en una situación real.** Requiere traza.
- Si los dos caminos pueden escribir para el mismo `(vmid, pasid)`. La condición de
  A es *"el fence no está señalado"* y la de B es una llamada de KFD; no he
  buscado si hay exclusión entre ellas.

## 6 · POR QUÉ ESTE HALLAZGO ES MÁS QUE UN DATO DE TABLA

Porque es la **tercera** vía por la que un mismo campo de la MMU se escribe, y las
tres las había medido por separado sin ver que convergían:

```
  1121   el bit 51 del PTE, borrado en GFX8 / puesto en GFX9+
  1153   ATC_VMID0_PASID_MAPPING, LEIDO en 15 registros para invalidar
  1166   mmIH_VMID_0_LUT, ESCRITO por dos caminos con valores distintos
```

Y la forma que toman es la misma en las tres: **un campo cuyo significado depende
de quién lo escribió y en qué momento**. El bit 51 significa no-retry en GFX9 y
ruido en GFX8; el `PASID_MAPPING` lo escribe el driver sin máscara y KFD con
máscara; y el `mmIH_VMID_0_LUT` lo escriben dos código distintos.

> **El riesgo para un driver propio no es replicating una función: es no saber
> qué valor tiene un campo porque hay dos escritores y ninguno documenta el
> orden.** Y en los tres casos el síntoma sería un fallo de TLB intermitente que
> no se reproduce en una prueba pequeña.

## 7 · ESTADO

```
  mmIH_VMID_0_LUT
     productor A  gmc_v8_0_emit_pasid_mapping   pasid, por PM4, sin espera
     productor B  kgd_set_pasid_vmid_mapping     pasid|VALID, por MMIO, con espera
     se coordinan entre si                     NO MEDIDO
  ATC_VMID_PASID_MAPPING
     escrito solo por B
     leido por gmc_v8_0_flush_gpu_tlb_pasid (15 registros, 1153)
  UPDATE_STATUS
     protocolo                                 write, wait, clear
     el clear es escribir                       1<<vmid     PROVEN
     es write-1-to-clear                       NO DOCUMENTADO por el driver
  equivalencia de los dos valores en el IH     NOT_DETERMINED -> guia de HW

  cierra los dos NOT_DETERMINED de 1153
  GPU     INTACTA
  sudo    NO usado
  MMIO    NO tocado
```