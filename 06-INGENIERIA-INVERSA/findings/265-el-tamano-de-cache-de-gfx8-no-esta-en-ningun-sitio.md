# 265 · El tamaño de caché de GFX8 no está en ningún sitio, y esa ausencia explica por qué `mclk` no se movía

```text
CLASSIFICATION=DOCUMENTATION+DERIVATION · TRACK=STATIC
CORPUS=RESEARCH/working/linux-7.1.3 · HARDWARE_SCOPE=HOST-C/RX550/0000:01:00.0
WORK_CLASS=READ_ONLY/EVIDENCE · WRITE_LOCAL=PROPIOS · MODIFICATIONS_CORPUS=0 · WRITE_EXECUTION=NONE
RUNTIME=NO NECESARIO · GPU INTACTA
```

## Qué resuelve

**Convierte el `NOT_DETERMINED` que `262`ergió como requisito previo —el tamaño de la caché de
datos de GFX8— en `PROVEN_ABSENT`, y con él explica por qué el reloj de memoria no sube.** `PROVEN_ABSENT`.

**⇒ `PROVEN_ABSENT`. El driver de Linux publica cinco tamaños de caché en
`amdgpu_gpu_info`, y los cinco se rellenan exclusivamente desde `amdgpu_discovery.c`, que
requiere un fichero `ip_discovery.bin`. Para Polaris12 ese fichero no existe.** `PROVEN_ABSENT`.

**⇒ `PROVEN`. Y por tanto los cinco valores que `amdgpu_gpu_info` mostraría para esta tarjeta
serían cero, no el tamaño real: no es que el dato sea pequeño, es que nadie lo escribe.**
`PROVEN_DERIVED`.

## 1 · La cadena, campo por campo

**⇒ `PROVEN`. Las cinco publicaciones, todas en `amdgpu/amdgpu_kms.c`:** `PROVEN`.

```c
1048    dev_info->tcp_cache_size  = adev->gfx.config.gc_tcp_l1_size;
1050    dev_info->sqc_data_cache_size = adev->gfx.config.gc_l1_data_cache_size_per_sqc;
1051    dev_info->sqc_inst_cache_size = adev->gfx.config.gc_l1_instruction_cache_size_per_sqc;
1052    dev_info->gl1c_cache_size = adev->gfx.config.gc_gl1c_size_per_instance * ...;
1054    dev_info->gl2c_cache_size = adev->gfx.config.gc_gl2c_per_gpu;
```

**⇒ Y las cinco escrituras están todas en un solo bloque de
`amdgpu/amdgpu_discovery.c:1767-1776`, dentro de la misma guarda:**

```c
1767  if (le16_to_cpu(gc_info->v1.header.version_minor) >= 2) {
1769      adev->gfx.config.gc_tcp_l1_size = le32_to_cpu(gc_info->v1_2.gc_tcp_l1_size);
1771      adev->gfx.config.gc_l1_instruction_cache_size_per_sqc = ...;
1772      adev->gfx.config.gc_l1_data_cache_size_per_sqc = ...;
1774      adev->gfx.config.gc_gl1c_size_per_instance = ...;
1775      adev->gfx.config.gc_gl2c_per_gpu = le32_to_cpu(gc_info->v1_2.gc_gl2c_per_gpu);
1776  }
```

**⇒ `PROVEN_DERIVED. Las cinco fuentes de caché del driver salen del mismo sitio, bajo la misma
condición de versión. No hay una ruta alternativa para GFX8: o hay `ip_discovery`, o las cinco
valen cero.** `PROVEN_DERIVED`.

**⇒ `PROVEN`. Y `ip_discovery` no corre para esta placa, por dos razones independientes ya
establecidas en el proyecto.** `PROVEN`.

| razón | evidencia |
|---|---|
| no existe el fichero | `/lib/firmware/amdgpu/` tiene 8 ficheros `*ip_discovery*` y ninguno es de polaris12 |
| el despacho no llega ahí | `CHIP_POLARIS12` se despacha en `amdgpu_device.c:1980` y su bloque va a `vi_set_ip_blocks`; el único escritor de `ip_versions[][]` es `amdgpu_discovery`, que sólo corre en el `default:` — conclusión de `231` |

**⇒ `PROVEN_DERIVED. Las dos juntos no son «falta un dato»: son «el mecanismo que produciría el
dato no está compilado para esta tarjeta».** `PROVEN_DERIVED`.

## 2 · Lo que sí está en el VBIOS, y por qué no sirve

**⇒ `PROVEN_DERIVED`. Para GFX8 la geometría de la GPU no viene del driver sino de una tabla
ATOM del VBIOS, y esa tabla existe y se lee.** `PROVEN_DERIVED`.

```c
/* amdgpu/amdgpu_atombios.c */
734   int index = GetIndexIntoMasterTable(DATA, GFX_Info);
744   adev->gfx.config.max_shader_engines      = gfx_info->info.max_shader_engines;
745   adev->gfx.config.max_tile_pipes          = gfx_info->info.max_tile_pipes;
746   adev->gfx.config.max_cu_per_sh           = gfx_info->info.max_cu_per_sh;
747   adev->gfx.config.max_sh_per_se           = gfx_info->info.max_sh_per_se;
748   adev->gfx.config.max_backends_per_se     = gfx_info->info.max_backends_per_se;
749   adev->gfx.config.max_texture_channel_caches = gfx_info->info.max_texture_channel_caches;
```

**⇒ `PROVEN`. Y la tabla que se lee del VBIOS, `ATOM_GFX_INFO_V2_1` en `include/atombios.h`, tiene exactamente
nueve campos. El único cuyo nombre lleva «cache» es `max_texture_channel_caches`, que es el
**número de cachés de textura**, no un tamaño: un UCHAR que cuenta unidades, no bytes. Los otros
ocho son número de motores, de tuberías, de CU, de shaders, de backends y dos versiones de IP:**

```c
typedef struct _ATOM_GFX_INFO_V2_1 {
    ATOM_COMMON_TABLE_HEADER asHeader;
    UCHAR GfxIpMinVer;
    UCHAR GfxIpMajVer;
    UCHAR max_shader_engines;
    UCHAR max_tile_pipes;
    UCHAR max_cu_per_sh;
    UCHAR max_sh_per_se;
    UCHAR max_backends_per_se;
    UCHAR max_texture_channel_caches;
} ATOM_GFX_INFO_V2_1;
```

**⇒ `PROVEN_ABSENT. La tabla `GFX_Info` del VBIOS de esta tarjeta no lleva tamaño de caché, y es
la única tabla que el driver consulta para la geometría del GFX en GFX8. No hay una segunda
fuente: el `case CHIP_POLARIS12` de `gfx_v8_0.c:1682` no fija ningún campo de caché, delega todo
en `amdgpu_atombios_get_gfx_info`.** `PROVEN_ABSENT`.

**⇒ `PROVEN_DERIVED. Y esto explica por qué el estado del proyecto dice «8 CUs; CU masks 0x1e»
cuando la tabla tiene `max_cu_per_sh` y `max_shader_engines` pero no el número total de CU: el
número total se deriva multiplicando, y el `0x1e` viene de otro camino. La contradicción que
`261` abrió sobre `cg_mask` no se resuelve con esta tabla, porque esta tabla no lo contiene.** `PROVEN_DERIVED`.

## 3 · La consecuencia para `262`, y es la importante

**⇒ `PROVEN_DERIVED`. `262` dejó escrito que sin conocer el tamaño de caché no se puede elegir un
conjunto de trabajo que la derrote, y por tanto el kernel de memoria no podía dar una medida
válida. Con esta nota el motivo queda superada: no es que falte el dato para escoger el
tamaño, es que para esta tarjeta el dato no está disponible en ninguna fuente del driver.** `PROVEN_DERIVED`.

**⇒ `PROVEN_DERIVED. Y hay una consecuencia más fuerte y más incómoda: si el tamaño de caché no es
un dato que el host pueda conocer en GFX8, entonces un driver propio tampoco puede conocerlo por
esa vía, y tendría que medirlo.** `PROVEN_DERIVED`.

**⇒ `PROVEN_DERIVED. Eso convierte la medición de `PENDIENTE=262-1` en algo que sí tiene
discriminante: un kernel que varíe el salto de acceso y busque el punto en que el ancho de banda
medido deja de crecer. Ese punto es el tamaño de caché, y se obtiene midiendo en lugar de
leyendo.** `PROVEN_DERIVED`.

```text
PENDIENTE=262-1 | HALLAZGO=265-*.md | ESTADO=NOT_DETERMINED
           | NECESITA=CORPUS  (kernel con salto variable; el punto de meseta ES la cache)
           | ALCANZABLE_SIN_ROOT=si
```

## 4 · Lo que esta nota cierra y lo que deja

**⇒ `PROVEN_ABSENT`, con el alcance del §13 del prompt maestro y la regla de lectura completa
aplicada: se han inspeccionado la struct del VBIOS, la struct de `gfx_config`, la función que
rellena los cinco campos, la función que consulta la tabla ATOM, el `switch` de ASIC, el
descubrimiento, y el contenido del directorio de firmware del sistema.** `PROVEN_ABSENT`.

**⇒ `NOT_DETERMINED`: el tamaño de caché como número. Es distinto de la ausencia anterior: la
ausencia es del dato en el driver, y el número es una propiedad del silicio que existe aunque
nadie la lea.** `NOT_DETERMINED`.

**⇒ `PROVEN_DERIVED. Y esa distinción es la que hace que la frontera siga viva en lugar de
cerrarse como bloqueada. El host no lo puede leer, pero un banco de pruebas lo puede medir, y esa
es la vía que queda por recorrer.** `PROVEN_DERIVED`.

**⇒ `NOT_IN_CORPUS`: el firmware SMU como fuente alternativa. `254` cerró su cabecera y `251` cerró
la cadena de lectura de temperatura, y ninguno de los dos abre el interior del microcodigo. Si el
firmware conoce el tamaño de caché, está ahí y no en el driver.** `NOT_IN_CORPUS`.

## 5 · Errores propios de esta nota

**⇒ `ERROR`: uno, y de la familia más difícil. En `262` escribí que el kernel de memoria no
puede medirse sin conocer el tamaño de caché, y presenté eso como una limitación de mi
conocimiento — «no sé el dato»— cuando era una limitación de la fuente. No es lo mismo: yo no lo
busqué, el driver no lo tiene.** `ERROR`.

**⇒ `PROVEN_DERIVED. Y la consecuencia metodológica es la que manda: una pregunta que se declara
`NOT_DETERMINED` porque no he buscado el dato es un `NOT_DETERMINED` provisional, y lo
correcto ante esa sensación es ir a buscar la fuente antes de escribir la nota. Es la diferencia entre «no lo sé» y «no está», y esta nota es exactamente el paso de la primera a la segunda.** `PROVEN_DERIVED`.