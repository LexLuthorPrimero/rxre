# 1041 · Leer un registro por ioctl apaga la función *gfx-off* del kernel, y eso no es lo que dice ninguna de las dos herramientas

`CLASSIFICATION=MEASUREMENT` · `TRACK=STATIC`
`CORPUS=linux-7.1.3.tar.xz (sha256 be41c068…)` · `HARDWARE_SCOPE=PCI 1002:699F rev 0xc7`
`WORK_CLASS=READ_ONLY` · `WRITE_EXECUTION=NONE` (para la lectura; la writing la hace el kernel)
`GPU INTACTA` · `MODIFIES_CODE=SI` (`08-ARQUITECTURA/tools/amdmmr.c`, el texto)

---

## La pregunta

Un nodo concurrente, escribiendo contratos para el registro de herramientas, mide que
`amdmmr.c` y `amdinfo.c` abren `/dev/dri` con `O_RDWR` y anota que a `amdmmr.c` eso
"no lo dice". Es cierto: su cabecera dice **"Solo lectura"**.

La pregunta que abría esto no es si la herramienta escribe —no escribe, solo pide
lecturas— sino **qué efecto tiene pedir esa lectura sobre el estado del hardware**.
Una herramienta que no escribe en el hardware no es necesariamente una herramienta
que no cambia el hardware.

## MEDIDO

### 1. La ruta del ioctl apaga el *gfx-off* antes de leer

`amdgpu_kms.c`, `case AMDGPU_INFO_READ_MMR_REG`:

```c
down_read(&adev->reset_domain->sem);
amdgpu_gfx_off_ctrl(adev, false);
ret = 0;
for (i = 0; i < info->read_mmr_reg.count; i++) {
        if (amdgpu_asic_read_register(adev, se_num, sh_num,
                                      info->read_mmr_reg.dword_offset + i,
                                      &regs[i])) { … ret = -EFAULT; break; }
}
amdgpu_gfx_off_ctrl(adev, true);
up_read(&adev->reset_domain->sem);
```

### 2. Y "apagar el gfx-off" es lo contrario de "apagar el motor"

`amdgpu_gfx.h` lo declara:

```c
void amdgpu_gfx_off_ctrl(struct amdgpu_device *adev, bool enable);
```

Devuelve **`void`**. Y `amdgpu_gfx_do_off_ctrl()` en `amdgpu_gfx.c` dice qué hace
cada rama:

```c
if (!(adev->pm.pp_feature & PP_GFXOFF_MASK))
        return;                                  /* sin GFXOFF, AMBAS llamadas son no-op */
mutex_lock(&adev->gfx.gfx_off_mutex);
if (enable) {
        WARN_ON_ONCE(adev->gfx.gfx_off_req_count == 0)   /* desequilibrio */
        adev->gfx.gfx_off_req_count--;
        if (count == 0 && !gfx_off_state)
                schedule_delayed_work(&adev->gfx.gfx_off_delay_work, GFX_OFF_DELAY_ENABLE);
} else {
        if (count == 0) {
                cancel_delayed_work_sync(&adev->gfx.gfx_off_delay_work);
                if (adev->gfx.gfx_off_state &&
                    !amdgpu_dpm_set_powergating_by_smu(adev, AMD_IP_BLOCK_TYPE_GFX, false, 0)) {
                        adev->gfx.gfx_off_state = false;
                        if (adev->gfx.funcs->init_spm_golden)
                                amdgpu_gfx_init_spm_golden(adev);      /* RE-INICIALIZA */
                }
        }
        adev->gfx.gfx_off_req_count++;
}
```

O sea, **`off_ctrl(adev, false)` significa "un cliente pide que GFX siga
alimentado"**: cancela el apagado pendiente, y si el bloque ya estaba apagado lo
vuelve a alimentar **y re-inicializa los golden settings del SPM**
(`amdgpu_gfx_init_spm_golden`).

### 3. El alcance: 19 registros, todos de GC

`soc21.c:287-307` — `soc21_allowed_read_registers[]`, **19 entradas**, todas de la
forma `SOC15_REG_ENTRY(GC, 0, reg…)`. Y `soc21_read_register` (`soc21.c:338`)
devuelve `-EINVAL` para cualquier offset que no esté en la tabla.

`adev->asic->read_register = &soc21_read_register` para esta generación
(`soc21.c`, tabla de ASIC). Y el ioctl acota el lote: `count > 128` → `-EINVAL`.

**Corroborado el 19.** Ni el número de entradas ni el rango de líneas vinieron de
la prosa de la herramienta: están contados en la tabla del corpus.

### 4. Dos mitigaciones que hacen esto mucho más benigno de lo que temía

Al medirlo iba a escribir que el retorno de la llamada se ignoraba, de modo que la
lectura podía ocurrir con el bloque sin quiescer. **Eso era falso**: la función
devuelve `void`, no hay retorno que ignorar. Corregido antes de escribirlo.

Y hay un gate que puede hacer las dos llamadas inertes:

```c
if (!(adev->pm.pp_feature & PP_GFXOFF_MASK))
        return;
```

Si esta tarjeta no anuncia `PP_GFXOFF`, pedir la lectura no cambia nada. Eso es
`NOT_DETERMINED` en esta caja y no lo he medido — no he ejecutado nada contra la
GPU.

## LA CLASIFICACIÓN CORRECTA

`CONTROLLED_WRITE` sobre el **estado de alimentación del bloque GFX**, no
`READ_ONLY`, y no es un apagado del motor:

| | |
|---|---|
| qué cambia | power-gating del bloque GFX, y los golden settings del SPM si ya estaba apagado |
| durante | solo mientras dura la llamada al ioctl |
| reversibilidad | sí, por construcción: la rama `enable=true` va **después** del bucle, no dentro, y se ejecuta incluso si el bucle sale por `break` con `-EFAULT` |
| recuento | `gfx_off_req_count`, así que dos lectores concurrentes no se pisan |
| condiciones | inerte si el ASIC no anuncia `PP_GFXOFF` |
| riesgo residual | `WARN_ON_ONCE(gfx_off_req_count == 0)` en la rama de release: un desequilibrio entre peticiones, sea de donde sea, salta |

## LO QUE ESTABA MAL ESCRITO, Y ESTE HALLAZGO LO CORRIGE

`amdmmr.c` decía:

> *"OJO: el kernel hace amdgpu_gfx_off_ctrl() antes y despues. No es una lectura
> pasiva: apaga el control del motor GFX mientras lee."*

La primera frase es correcta y útil. La segunda dice lo contrario de lo que pasa:
**desactiva la función de apagado, es decir, mantiene el motor encendido**. Un
lector que se quede con la segunda frase llegaria a la conclusion de que la
herramienta apaga la GPU, y de que por eso es mas peligrosa de lo que parece —
cuando el efecto real es transitorio y el bloque no se apaga.

La redacción correcta dice las tres cosas que sí importan: que hay una petición de
mantener GFX alimentado, que es refcontada, y que tiene efecto de estado solo si el
ASIC anuncia `PP_GFXOFF`.

## LO QUE NO ESTA HECHO

- **No he ejecutado la herramienta.** Todo lo de arriba es lectura de corpus y no
  he observado la transición en esta caja. El valor de `PP_GFXOFF` para
  1002:699F rev 0xc7 no está medido.
- **La razón por la que existe la lista blanca** —que el hallazgo 924 ya Presuponia— es que
  sin ella no habría ningún `READ_MMR_REG` utilizable desde userspace sin root.
  Que la lista sea de 19 entradas de GC es una **acotación del alcance** de los 123
  huecos clasificados `UN_REGISTRO`: pueden cerrarse por esta vía los que caigan
  en esos 19, y solo esos.
- **La lista es la de soc21.** `soc15`, `soc24`, `soc_v1_0`, `cik`, `nv`, `si`, `vi`
  tienen su propia. Para esta tarjeta es la de soc21; para otra sería otra, y el
  número 19 **no** es transferible.

## POR QUE ESTO ESTA EN UN HALLAZGO Y NO EN UN COMENTARIO

Porque `AGENTS.md` §42 exige que una operación de escritura pase por
`PRECONDICION → RISK CHECK → … → OBSERVATION → RECOVERY → VALIDATION`, y el
primer paso es *declarar* qué clase es. Aquí la clase se ha deducido del código del
kernel, no de un criterio, y es una clase que dos instrumentos del proyecto no
declaraban. Una herramienta que "solo lee" y que deja el bloque GFX en un estado
de alimentación distinto durante la llamada —y que re-inicializa los golden
settings del SPM si lo encuentra apagado— no es una herramienta de lectura, y el
registro tiene que decirlo.
