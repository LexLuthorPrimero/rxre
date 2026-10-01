# cus — el protocolo para descubrir cuántos CUs hay activos

## Por qué esto no es un número constante

`AGENTS.md` declara 8 CUs y máscara `0x1e`. Esos 8 son los **activos**, no los
presentes: el log da `CU per SH 5` con `active_cu_number 8`, o sea **10 CUs
físicos**.

Y ni siquiera los 10 se pueden leer de una constante:

- `max_cu_per_sh` viene del **VBIOS** (`amdgpu_device.c:1848`,
  `gpu_info_fw->gc_num_cu_per_sh`), así que el corpus no puede derivarlo.
- Los 8 **activos** los decide el **silicio**, y se descubren preguntándoselo a
  la GPU: se escribe la máscara de CUs inactivos y se lee de vuelta qué CUs
  quedaron.

`active_cu_per_sh` está en el VBIOS (offset 40 de la tabla) y el driver
**no lo lee**: aparece en las tres declaraciones de `atomfirmware.h` y en
ningún `.c` de `drivers/gpu/drm/`. El firmware publica el dato y el driver de
referencia prefiere preguntar a la GPU.

## La secuencia, con registros y campos

Todo en `gfx_v8_0.c`, función `gfx_v8_0_get_cu_info()` (`:7072`).

### 0. Tomar `grbm_idx_mutex`

```c
mutex_lock(&adev->grbm_idx_mutex);     /* :7089 */
... toda la secuencia ...
gfx_v8_0_select_se_sh(adev, 0xffffffff, 0xffffffff, 0xffffffff, 0);
mutex_unlock(&adev->grbm_idx_mutex);   /* :7117 */
```

No es opcional. `GRBM_GFX_INDEX` es un registro **global** de selección: si
otro hilo cambia el SE/SH seleccionado entre la escritura de la máscara y la
lectura del bitmap, se leen los CUs de otro SH y el conteo mezcla cosas de sitios
distintos sin producir ningún error.

Al final se hace un `select` con `0xffffffff` en los tres campos, que pone los
tres bits de broadcast y devuelve el índice a un estado neutro. Sin ese paso, el
primer consumidor que venga después hereda el SE/SH que dejó el bucle.

### 1. Seleccionar el par SE/SH

```c
gfx_v8_0_select_se_sh(adev, i, j, 0xffffffff, 0);       /* :7096 */
```

Escribe `GRBM_GFX_INDEX` para apuntar a un SE y un SH concretos. Con
`0xffffffff` en `se_num` o `sh_num` pone el bit de broadcast correspondiente
(`SE_BROADCAST_WRITES`, `SH_BROADCAST_WRITES`); con `instance == 0xffffffff`
usa `INSTANCE_BROADCAST_WRITES`.

Esto es obligatorio antes de cada lectura o escritura de configuración de SH:
el registro se selecciona, se opera, y el siguiente registro ya apunta a otro
sitio.

### 2. Escribir la máscara de CUs inactivos

```c
if (i < 4 && j < 2)
        gfx_v8_0_set_user_cu_inactive_bitmap(adev, disable_masks[i * 2 + j]);
```

Y esa función (`gfx_v8_0.c:7046`) hace:

```c
if (!bitmap)
        return;                                    /* <-- con 0 no escribe nada */
data = bitmap << GC_USER_SHADER_ARRAY_CONFIG__INACTIVE_CUS__SHIFT;
data &= GC_USER_SHADER_ARRAY_CONFIG__INACTIVE_CUS_MASK;
WREG32(mmGC_USER_SHADER_ARRAY_CONFIG, data);
```

El `return` con `bitmap == 0` es una trampa fácil de replicar mal: no equivale a
escribir cero. Si no se escribe, el registro conserva el valor anterior, que
puede tener CUs marcados como inactivos de una iteración anterior.

Y el límite del campo está en `include/asic_reg/gca/gfx_8_0_sh_mask.h:17715`:

```
GC_USER_SHADER_ARRAY_CONFIG__INACTIVE_CUS_MASK  0xffff0000
GC_USER_SHADER_ARRAY_CONFIG__INACTIVE_CUS__SHIFT 0x10
```

**16 bits en el shift 16**, luego el campo cubre 16 CUs por SH como máximo. Con
`max_cu_per_sh = 5` sobra espacio; con más de 16 CUs el hardware no podría
representarlos, y el driver no lo comprueba porque el VBIOS no lo diría.

### 3. Leer los CUs activos

```c
static u32 gfx_v8_0_get_cu_active_bitmap(struct amdgpu_device *adev)   /* :7060 */
{
        u32 data, mask;

        data =  RREG32(mmCC_GC_SHADER_ARRAY_CONFIG) |
                RREG32(mmGC_USER_SHADER_ARRAY_CONFIG);

        mask = amdgpu_gfx_create_bitmask(adev->gfx.config.max_cu_per_sh);

        return ~REG_GET_FIELD(data, CC_GC_SHADER_ARRAY_CONFIG, INACTIVE_CUS) & mask;
}
```

Cuatro detalles que hay que replicar exactamente:

1. **OR de dos registros**, no lectura de uno. Se combinan
   `CC_GC_SHADER_ARRAY_CONFIG` y `GC_USER_SHADER_ARRAY_CONFIG`. Los dos tienen
   el campo `INACTIVE_CUS` en el mismo sitio (`0xffff0000`, shift `0x10`), así
   que el OR combina las máscaras de inactive de hardware y de software.

2. **Se extrae de `CC_GC_SHADER_ARRAY_CONFIG`**, aunque `data` sea el OR de los
   dos. Como los campos están alineados, `REG_GET_FIELD(data, ...)` sobre el OR
   da el mismo valor que sobre cualquiera de los dos. Es correcto por la
   coincidencia de posición, y sería incorrecto si las máscaras no coincidieran.

3. **Se invierte** (`~`): el hardware informa de los CUs **inactivos**, y el
   driver quiere los activos.

4. **Se enmascara a `max_cu_per_sh`**. Sin ese `& mask`, los bits por encima
   del número real de CUs —que el hardware pone a uno al invertir, porque
   `INACTIVE_CUS` tiene 16 bits y solo 5 son válidos— saldrían como CUs
   activos. **Ese paso es el que convierte `0xfffffff0` en `0x1e`.**

Sin el paso 4, el conteo daría 31 CUs por SH en vez de 4.

### 4. Contar

```c
for (k = 0; k < max_cu_per_sh; k++) {
        if (bitmap & mask) {
                if (counter < ao_cu_num)
                        ao_bitmap |= mask;
                counter++;
        }
        mask <<= 1;
}
active_cu_number += counter;
```

`ao_cu_num` es `max_cu_per_sh` en GPU discreta y `2` en APU
(`if (adev->flags & AMD_IS_APU)`). Los `ao_cu_num` primeros CUs activos de
cada SH son los **always-on**, que van a `ao_cu_mask` y a
`mmRLC_PG_ALWAYS_ON_CU_MASK` (`gfx_v6_0.c:2834`).

## El resultado y por qué `0x1e`

```
max_cu_per_sh = 5          (del VBIOS)
INACTIVE_CUS  = ...1 0     (el hardware marca 1 CU inactivo)
~INACTIVE_CUS = ...1 1 1 1 1
& mask(5)     = 0b11110   = 0x1e
contar        = 4 CUs activos por SH
SE = 2, SH por SE = 1  ->  active_cu_number = 2 × 1 × 4 = 8
```

El `0x1e` de `AGENTS.md` es el resultado de esa dance, no una constante. Por SE
hay 4 activos de 5 presentes; el quinto CU está ahí pero el silicio lo marca
inactivo.

## Para un driver propio

El orden importa, y es fácil de invertir por error:

```
tomar grbm_idx_mutex
para cada SE, para cada SH:
    1. seleccionar SE/SH                (GRBM_GFX_INDEX)
    2. escribir máscara de inactivos    (GC_USER_SHADER_ARRAY_CONFIG)
       -- y escribirla SIEMPRE, incluso con 0, o limpiar antes de otro modo
    3. releer configuración             (CC_GC_SHADER_ARRAY_CONFIG |
                                          GC_USER_SHADER_ARRAY_CONFIG)
    4. invertir y enmascarar a max_cu_per_sh
    5. contar con popcount
seleccionar el broadcast 0xffffffff y soltar el mutex
```

Los puntos donde un error no da fallo visible:

- **No escribir la máscara con `bitmap == 0`** y no limpiar el registro antes.
- **Olvidar el `& mask`**: da un número de CUs activos plausible y demasiado
  grande. El hardware sigue respondiendo, así que parece un bug de
  scheduling y no de inicialización.
- **Invertir mal**: `0x1e` pasa a `~0x1e`, y el conteo explota.
- **Leer solo un registro**: se pierde la mitad de la información.

## Lo que sigue sin determinar

- **Qué decide el silicio** para poner un CU en `INACTIVE_CUS`. El driver no lo
  calcula: lo pregunta. La razón por la que esta GPU tiene 1 CU inactivo de 5
  por SH no está en ningún fichero del corpus, y sin lectura de MMIO no se puede
  saber. `NOT_DETERMINED`.
- Si los `disable_masks` que pasa el driver (de `amdgpu_gfx_parse_disable_cu`,
  normalmente vacíos sin `disable_cu`) son los que fijan el estado. Con los
  parámetros por defecto no hay ninguno, luego el estado observado es el del
  hardware, no el de una modificación del driver. Eso **sí** está determinado:
  `disable_cu` sale como `(null)` en
  `/sys/module/amdgpu/parameters/disable_cu`.
- Si el patrón `0x1e` es el mismo en cada SH. El driver lo lee por SH
  individualmente y guarda cada bitmap en `cu_info->bitmap[0][i][j]`, así que
  no hace falta suponerlo, pero solo puede comprobarse leyendo los cinco.

## Cómo reproducir lo que sí es reproducible

Sin root, no hay lectura de MMIO, así que este protocolo **no** se puede
ejecutar. Lo verificable sin root es el valor que el driver ya extrajo:

```sh
journalctl -k -b --no-pager | grep "SE .*SH per SE"
```

`GPU INTACTA`, `WRITE_EXECUTION NONE`.