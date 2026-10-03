# 923 — `vram_width`: las DOS rutas de `gmc_v8_0_mc_init` están mal, y ninguna lee `ucMemBusWidth`

Estado: `PROVEN` para el mecanismo del bug. `NOT_DETERMINED` para `ucMemBusWidth`, con la razón declarada.
Alcance: la RX 550 de esta placa, Polaris12/GFX8, kernel 7.1.3, amdgpu de ese árbol.
AUTORIA=AGENTE-SMU
Instrumento: `08-ARQUITECTURA/tools/vbiosread.py`, 8 de 8 controles pasan, 1 capacidad declarada como estado.

## Qué se afirmaba antes

En `911` quedó establecido que el ancho de bus real es de 128 bits y que el driver informa 64, y que
la causa es `amdgpu_atombios_get_vram_width`. Esa atribución era correcta pero **incompleta**: nombraba
una función sin comprobar si las dos rutas que la producen eran la única.

## La pregunta que faltaba

No «de dónde sale el 64» sino: **¿alguna ruta de `gmc_v8_0_mc_init` lee el ancho de bus de la VRAM?**

Es una pregunta distinta y con un discriminante distinto: la anterior se respondía leyendo una función;
esta se responde enumerando las rutas y mirando qué registro o tabla consume cada una.

## Respuesta: ninguna

`gmc_v8_0_mc_init` tiene exactamente dos rutas para `adev->gmc.vram_width`, y las dos leen mal:

```
RUTA A, amdgpu_atombios_get_vram_width
    lee  IntegratedSystemInfo.info_8.ucUMAChannelNumber     (atombios.h, _ATOM_INTEGRATED_SYSTEM_INFO_V2)
    y devuelve            ucUMAChannelNumber * 64

RUTA B, el fallback, sólo si la A devuelve 0
    chansize = 64 si MC_ARB_RAMCFG.CHANSIZE está puesto, si no 32
    numchan  = f(MC_SHARED_CHMAP.NOOFCHAN), y case 0 + default devuelven 1
    devuelve  numchan * chansize
```

Tres hechos del corpus, cada uno con su cita:

1. **El struct de la ruta A se llama `_ATOM_INTEGRATED_SYSTEM_INFO_V2`**
   (`include/atombios.h`). No es una inferencia sobre el nombre: es el nombre.

2. **El campo vecino declara una enumeración de memoria que no incluye GDDR5.**
   `ucMemoryType` lleva el comentario `[3:0]=1:DDR1;=2:DDR2;=3:DDR3`. Una tabla con esa
   enumeración describe DDR integrado; esta placa tiene GDDR5 y no tiene UMA. La ruta A
   multiplica por 64 el número de canales de UMA leído de una tabla que no describe su memoria.

3. **La ruta B lee el mapa de canales COMPARTIDOS.** `MC_SHARED_CHMAP` es el mapa de canales
   compartidos. Para una dGPU con VRAM dedicada ese registro no describe el canal de VRAM. Y el
   caso `default` del switch devuelve `numchan = 1`, de modo que un `NOOFCHAN` que el driver no
   sepa interpretar produce 1 canal, no un error: produce un número silenciosamente plausible.

`numchan=1, chansize=64` da exactamente el 64 que informa `vram_bit_width`. También lo da
`numchan=2, chansize=32`. **El mecanismo exacto de la ruta que produjo este 64 concreto es
`NOT_DETERMINED`**; que ninguna de las dos sea correcta es `PROVEN`.

La conclusión que importa para el proyecto no es «el driver se equivoca», sino: **el valor de
`vram_bit_width` que expone la uapi no es una lectura de esta placa.** Es una lectura de una tabla
IGP, o una aritmética sobre el mapa de canales compartidos. Cualquier decisión de diseño tomada
sobre ese campo —incluido el tamaño de buffer deallocation, el cálculo de direcciones, o el límite
de `virtual_address_max`— se apoya en un valor que no describe el ASIC.

## `ucMemBusWidth`: `NOT_DETERMINED`, y por qué

El campo que sí describe el ancho de bus de la VRAM no es alcanzable desde el corpus:

- Búsqueda de `ucMemBusWidth` en el árbol entero del kernel: **0 ocurrencias**. No es `NOT_FOUND`
  por no haber buscado: es `PROVEN_ABSENT` tras búsqueda completa.
- `ATOM_VRAM_INFO_TABLE`: `PROVEN_ABSENT` en el árbol, igual que el anterior.
- `_ATOM_VRAM_INFO_TABLE` sí existe en `include/atombios.h`, y **el campo `VRAM_Info` está en el
  índice 28 de la lista maestra**. Es decir: la tabla existe, se puede apuntar, pero su definición
  de campos no está en el corpus. Decodificarla sería adivinar el layout, que es exactamente lo
  que este proyecto no hace.

Por eso `ucMemBusWidth` queda `NOT_DETERMINED`, y no como pendiente de una búsqueda más: la fuente
que lo definiría no está en el corpus.

## La tabla maestra: no localizada, y el instrumento se niega a elegir

La geometría sí sale del corpus: `ATOM_MASTER_DATA_TABLE` **no es una lista de entradas
`{tipo, tamaño, puntero}`**. Es un struct fijo de 35 `USHORT`, uno por tabla nombrada, más la
cabecera común de 4 bytes: 74 bytes en total. `GetIndexIntoMasterTable(DATA, Campo)` es
`offsetof(...) / sizeof(USHORT)`, o sea el número de orden del campo, y ese número es
directamente un offset dentro del ROM.

Esto explica por qué la primera versión de la búsqueda empírica salió con cero: buscaba entradas de
«tipo 25», un formato que no existe aquí. **El fallo estaba en el instrumento, no en el VBIOS.**

La ruta del propio driver (`amdgpu/atom.c`, sección `amdgpu_atom_parse`) es:

```
base   = CU16(0x48)                                   ATOM_ROM_TABLE_PTR
maestro= CU16(base + 24)                              usMasterDataTableOffset
```

con un matiz que importa: el maestro es `CSTR(usMasterDataTableOffset)`, y `CSTR(x)` es `bios + x`,
**no** `base + x`. `base` sólo sirve para leer los campos de la cabecera.

Con esa ruta, `base = 0x21C` y el destino es `0x1002`, cuyo `structuresize` es 40077 y no 74.
La vía del driver no resuelve. Una búsqueda por estructura con la restricción fuerte
`structuresize == 74` deja **7 candidatas** y ninguna confirmable por una segunda vía.

**`vbiosread.py` no elige ninguna.** Imprime las siete y declara
`ESTADO=NOT_LOCALIZADA_MAESTRA`. Elegir la más plausible produciría offsets que parecerían buenos
y no lo serían.

## Los instrumentos que estaban rotos, y qué se arregló

Todos en `vbiosread.py`. Todos me los detecté a mí mismo al ejecutarlos, y todos son el mismo
tipo de error: **un control que comprueba un supuesto en vez de una propiedad.**

| Qué estaba mal | Por qué fallaba | Arreglo |
|---|---|---|
| El control de firma exigía `ATOM` en el offset 0 | Esta placa arranca con la firma VBE `55AA`; la firma `AMD ATOM BIOS` está en `0x258` | Se comprueban las dos, en sus offsets reales |
| Buscaba entradas de tabla «de tipo 25» | Ese formato no existe: la lista maestra es un struct fijo de `USHORT` | Geometría de 74 bytes tomada de `atombios.h` |
| Exigía «la tabla VRAM está presente» | No es comprobable todavía | Se declara como estado, no como fallo |
| Leía el byte de la firma como `55 aa e9 73` | El dword es little-endian: son `55 aa 73 e9` | Orden correcto |
| Buscaba «POLARIS» en el nombre del VBIOS | El nombre de esta familia en el firmware es **LEXA** | Se aceptan ambos; el nombre queda registrado |

Dos de estos merecen quedar escritos porque son errores de fondo y no de tecleo:

**Un control que nunca puede pasar deja de leerse.** El requisito «la tabla maestra está localizada
de forma unívoca» estaba escrito como un control con verdict OK/FALLA. No es un control: es el
estado de una capacidad. Mientras eso fuese falso, el self-test decía «HAY FALLOS» de forma permanente, y
un test permanentemente en rojo enseña a ignorar el rojo. Ahora los estados se imprimen como
`ESTADO` y no cuentan como fallo, y el self-test separa los dos conceptos.

**Un nombre de firmware no es un nombre de hardware.** `128bit` aparece en el nombre del VBIOS de
esta placa. Buscar «POLARIS» y no encontrarlo no era evidencia de que la placa no fuera Polaris:
era evidencia de que el firmware usa otro nombre para la familia. Lo mismo vale al revés: un
control de identidad que comprueba la palabra equivocada da un `NOT_FOUND` que parece un
descubrimiento y en realidad es una falta de vocabulario.

## Lo que esto cambia

`vram_bit_width` pasa de «un campo con un bug conocido» a «un campo sin ninguna ruta de lectura
correcta en este ASIC». Eso cambia el tratamiento: no es un valor sospechoso que haya que
contrastar, es un valor que hay que **reemplazar** en cualquier código propio. Para un driver
nuestro, el ancho de bus tiene que venir de la ruta que este driver no usa, y esa ruta todavía
no está localizada.

## Instrumentos

- `08-ARQUITECTURA/tools/vbiosread.py` — 8 de 8 controles pasan; una capacidad declarada como
  estado (`NOT_LOCALIZADA_MAESTRA`); rechaza elegir entre candidatas; reproduce la cadena de
  punteros de `amdgpu_atom_parse` y reporta que no resuelve.

- `08-ARQUITECTURA/tools/amdioread.py` — auditoría hecha: `vram_bit_width` sólo se **leía** en
  dos sitios, uno de ellos una lista de impresión y ninguno un consumo en un cálculo. No hay
  contaminación en el código propio. Pero imprimir `vram_bit_width=64` sin marca es afirmar algo
  falso con la misma seguridad con que se afirma el resto de la línea, y ese 64 es
  precisamente el número que se propagaría solo. Añadido `FALSOS_CONOCIDOS`, que marca el campo
  en la propia salida con el motivo y el número de esta nota. 11 de 11 controles pasan.

## Lo que queda abierto

- La ruta concreta que produjo el 64 en esta placa (A o B, y con qué valores): requiere leer
  `MC_SHARED_CHMAP` y `MC_ARB_RAMCFG`, o sea MMIO. Bloqueado por lo ya registrado.
- Localizar la tabla maestra por una vía independiente de la empírica: ya agotada la empírica con
  la geometría del corpus.
- Reemplazar `vram_bit_width` por el valor real (128) en cualquier instrumentación propia que lo
  use. Pendiente: no he audited qué código propio depende de él.
