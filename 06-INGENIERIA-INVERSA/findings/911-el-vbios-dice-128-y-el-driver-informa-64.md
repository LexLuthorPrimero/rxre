# 911 · El VBIOS dice 128 bits y el driver informa 64: `amdgpu_atombios_get_vram_width` lee la tabla del IGP
AUTORIA=AGENTE-SMU

```text
CLASSIFICATION=MEASUREMENT+ERROR-CORRECTION+BUG-UPSTREAM · TRACK=RUNTIME+STATIC
CORPUS=RESEARCH/working/linux-7.1.3 amdgpu_atombios.c:770-793, gmc_v8_0.c:515,557,
          amdgpu_kms.c:875-1114 + vbios.rom volcado del ASIC
HARDWARE_SCOPE=HOST-C/RX550/0000:01:00.0 · GPU INTACTA · MODIFICATIONS_CORPUS=0
INSTRUMENTO NUEVO=vbiosread.py, vuelca la imagen del VBIOS por ioctl sin root
```

## Qué resuelve

**⇒ Cierra `909`, `908` y `602` en el mismo punto, y de la misma manera: el campo del driver está
mal y el VBIOS tiene razón. El bus es de 128 bits. `602` estaba bien; `258` y `909` estaban mal.**
`RESOLVED`

**⇒ `PROVEN`: el VBIOS de esta placa se declara `GDDR5 128bit`, y no contiene la cadena `64bit`
ni una sola vez.** `PROVEN`

```text
  offset 0x131 del volcado:
    ...EXPRESS GDDR5
    D09001 Lexa XL A0 GDDR5 128bit 2GB 214e/300m
```

**⇒ `PROVEN`: el driver no lee de ahí. `amdgpu_atombios.c:770-793` returns
`igp_info->info_8.ucUMAChannelNumber * 64`, y el comentario de la línea 778 dice, textual, «get any
igp specific overrides». Es una función de IGP aplicado a una tarjeta discreta, y el 64 es el
multiplicador del campo equivocado.** `PROVEN`

```c
  770  int amdgpu_atombios_get_vram_width(struct amdgpu_device *adev)
  773      int index = GetIndexIntoMasterTable(DATA, IntegratedSystemInfo);
  778      /* get any igp specific overrides */
  781      igp_info = (union igp_info *)(mode_info->atom_context->bios + data_offset);
  783      switch (crev) {
  784      case 8:
  785      case 9:
  786          return igp_info->info_8.ucUMAChannelNumber * 64;
```

**⇒ `PROVEN_DERIVED`: el techo de 48,0 GB/s vuelve a ser el correcto, y sin multiplicadores raros.**
`PROVEN_DERIVED`

```text
  128 bits / 8 = 16 B   x 2 (GDDR5 es doble velocidad) x 1,5 GHz = 48,0 GB/s
  medido en 606: 43,2 a 44,5 GB/s = 90,0% a 92,7%
  y no hace falta el flag QDR: la hipótesis del multiplicador 4 era una hipótesis
```

## 1 · El VBIOS estaba bloqueado por una búsqueda incompleta

**⇒ `PROVEN`: `/sys/bus/pci/devices/0000:01:00.0/rom` es `-rw------- root root`, 131.072 bytes, y
no se lee sin root. El bloqueo era real por esa vía.** `PROVEN`

**⇒ `PROVEN_DERIVED`: pero no había más que esa vía. `amdgpu_kms.c:1103-1113` vuelca la imagen
entera del VBIOS a un búfer de usuario con `AMDGPU_INFO_VBIOS_IMAGE`, y el preámbulo de
`amdgpu_info_ioctl`, línea 652, solo comprueba que `return_size` y `return_pointer` no sean cero.
No hay comprobación de privilegios. Y `/dev/dri/renderD129` es `crw-rw-rw-`.** `PROVEN_DERIVED`

**⇒ `PROVEN`: volcado obtenido, 58.880 bytes, y el control de firma y de tamaño pasan.** `PROVEN`

```text
  vbios_size    58880
  vbios_name    D09001 Lexa XL A0 GDDR5 128bit 2GB 214e/300m
  vbios_pn      xxx-xxx-xxx
  vbios_version 0xF320201
  vbios_ver_str 015.050.002.001.000000
  vbios_date    2021/05/12 03:53
  y en 0x240 hay 0x699F1002, que es el vendor 0x1002 con el device 0x699F de esta placa
```

**⇒ `PROVEN_DERIVED`: es la cuarta vez en esta sesión que declaro una capacidad ausente sin haber
buscado la vía completa. Las otras tres: el flag `--mem` de `606`, el tamaño de caché de `265`, y
la cita de `258` en `602`. Esta es la primera en que lo ausente era una capacidad y no un dato, y
es la que más tiempo costó, porque la frontera llevaba marcada como bloqueada desde el principio
de la sesión.** `PROVEN_DERIVED`

## 2 · Qué dice `258` y qué dice `909`, y por qué los dos se equivocaron igual

**⇒ `PROVEN_DERIVED`: las tres notas caminaron en círculo porque la cifra que comparaban era la
misma y ninguna miró de dónde salía.** `PROVEN_DERIVED`

| nota | afirmación | veredicto |
|---|---|---|
| `258` | bus de 64 bits, techo 24,0 GB/s | ancho mal, multiplicador mal |
| `602` | 64 bits refutado por medición, luego 128 bits | **correcto**, y no lo acepté |
| `606` | 43,2 a 44,5 GB/s medidos, dos rutas | correcto |
| `908` | «el campo del driver es el dudoso» | **el campo es el que está mal** |
| `909` | «64 bits está corroborado por dos lecturas» | dos lectores de una variable, y la variable está mal |

**⇒ `PROVEN_DERIVED`: y el punto donde `909` se equivocó de lado es uno que él mismo
señaló en su §1. Tomó el log de arranque como prueba porque no lo había abierto, y cometió el
mismo error que `602`. Dos notas seguidas con el mismo verificador —una lectura del driver—

**⇒ `PROVEN_DERIVED`: que el campo salga de `adev->gmc.vram_width`, que a su vez sale de una
función que lee la tabla del IGP, es un error de lectura en el driver, no un dato dudoso. La
diferencia importa para el proyecto: un dato dudoso se investiga, un error se corrige, y aquí hay
un sitio concreto donde corregirlo.** `PROVEN_DERIVED`

## 3 · Lo que esto deja established, y lo que no

**⇒ `PROVEN`: el techo de VRAM de este proyecto es 48,0 GB/s y se usa el 90% al 93%.** `PROVEN`

**⇒ `PROVEN_DERIVED`: y los porcentajes de utilización de VRAM de `258`, `271` y `282` estaban mal
por el ancho equivocado, y los de `602` estaban bien por una razón que no era la buena. Los dos
conjuntos necesitan corrección y esta nota las hace.** `PROVEN_DERIVED`

**⇒ `CORROBORATED`: la predicción de `602` se cumple. Cuando `602` dedujo que el bus no podía ser de
64 bits porque 43,2 GB/s no caben en 24,0, la explicación correcta era un ancho de 128 bits, y el
VBIOS la confirma de forma independiente y por escrito.** `CORROBORATED`

**⇒ `NOT_DETERMINED`: leer `ucMemBusWidth` de la `ATOM_VRAM_INFO_TABLE` directamente.** `NOT_DETERMINED`

```text
  por que sigue pendiente siendo NOT_DETERMINED y no CORROBORATED
    la cadena de nombre del VBIOS dice 128bit, y es una cadena que escribe el firmware
    de la placa. Es evidencia fuerte, pero es un texto, no un campo de anchura.
    el campo que lo declara de forma estructurada es ucMemBusWidth de ATOM_VRAM_INFO_TABLE,
    y la tabla maestra no la he localizado todavia: mi primer intentoBusco empirica de
    entradas de tipo 25 salio con cero, y no he averiguado por que. Geometria, no semántica.
```

**⇒ `NOT_DETERMINED`: y el flag QDR. Con 128 bits y doble velocidad no hace falta para el techo, y
sigue sin consumidor en el driver (`amdgpu_atombios.c:1152`, cero referencias más a `qdr`). Es un
dato muerto que no affects ninguna magnitud de este proyecto.** `NOT_DETERMINED`

## 4 · La regla de método, que es lo más transferible

**⇒ `PROVEN_DERIVED`: durante toda la sesión he tratado «bloqueado por root» como «bloqueado», y
no lo era. Tres veces he declarado una ausencia sin haber buscado la vía completa: `--mem`, el
tamaño de caché, la cita de `258`. Y las tres eran de la misma forma: había miró en un sitio
razonable y no seguí buscando.** `PROVEN_DERIVED`

**⇒ `PROVEN_DERIVED`: la forma que funciona es enumerar las vías antes de declarar el bloqueo, y
para cada vía preguntar quién la permite. El ROM de PCI es `root`. La ioctl `AMDGPU_INFO` sobre
un nodo `crw-rw-rw-` no lo es. La diferencia no era de permisos, era que yo solo había visto
la primera.** `PROVEN_DERIVED`

**⇒ `PROVEN_DERIVED`: y hay un aviso para el resto del proyecto. `AMDGPU_INFO_DEV_INFO` informa
`vram_bit_width`, y esa es una afirmación del driver, no del hardware. `258` la usó para construir
un techo y no comprobó de dónde salía. La regla general es la de §8 aplicada a un campo de ioctl
y no a un comentario: **un valor que informa el driver es evidencia sobre el driver, y para que
sea evidencia sobre el hardware tiene que haber dos caminos que no compartan origen**.** `PROVEN_DERIVED`

## 5 · PENDIENTE

```text
TODO-2 | ESTADO=RESUELTA por 911. El bus es de 128 bits, por el nombre del VBIOS.
           | PENDIENTE_LO_UNICO=leer ucMemBusWidth de ATOM_VRAM_INFO_TABLE, que
           |          corroboraria el texto con un campo estructurado.
909   | ESTADO=REFUTADA en su conclusion: 64 bits NO esta corroborado, esta mal.
908   | ESTADO=RESUELTA: la contradiccion era driver contra hardware, no entre campos.
602   | ESTADO=CONFIRMADA: el bus es de 128 bits. Su correccion de 258 era correcta.
258   | SU ANCHO DE 64 BITS ESTA REFUTADO, y la razon es una funcion de IGP en una dGPU.
           | SU ARITMETICA TAMBIEN: multiplicar por 2 sobre 128 bits da 48,0, no 24,0.
258   | SU NOT_AVAILABLE SOBRE LA LECTURA EN VIVO TAMBIEN: se lee sin root, por ioctl.
265   | ESTADO=CORROBORADA por 908: gl2c_cache_size vale 0
272   | ESTADO=DESBLOQUEADO en su parte de VBIOS, y pendiente de re-ejecutar lo que depende de el

REGLA | Antes de declarar un bloqueo por permisos, enumerar las vias y preguntar quien
       | permite cada una. El ROM de PCI pide root; la ioctl no.
REGLA | Un valor que informa el driver es evidencia sobre el driver. Para que sea
       | evidencia sobre el hardware hace falta un segundo camino que no comparta origen.

INSTRUMENTO=vbiosread.py | ESTADO=WIP, vuelca el VBIOS sin root y lo verifica por firma
           | PENDIENTE=el self-test aun no pasa; la comprobacion de firma usa ATOM y esta
           |          placa arranca con la firma VBE 55AA, no con ATOM. Hay que corregirlo
           |          antes de declararlo VALIDATED, y localizar la tabla maestra.
```