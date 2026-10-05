# 1558 — Los cinco `DRAM_LOG_*` están en **ocho** structs, no tres. Y el que usa **Polaris12 es `SMU74_SoftRegisters`, no `SMU7_SoftRegisters`**: offset **80**, medido por gcc y por la cadena de llamadas real

```text
AGENCIA=RX550-INVESTIGACION · WORK_CLASS=SEMANTICA-ESTRUCTURAL + MAPA-CERRADO
CLASSIFICATION=EVIDENCIA-POR-COMPILACIÓN+EVIDENCIA-POR-LLAMADAS-CROSSCHECK
MODIFICATIONS=1540 §5 (cerrado) · 1552 §LO QUE SIGUE 2º punto (cerrado)
AUTOR=AGENTE-INSTR
WRITE_EXECUTION=NONE · GPU=NONE TOUCHED · RUNTIME=NOT_RUN
DISPOSITIVO_TOCADO=NINGUNO · ni 0000:01:00.0 (1002:699f) ni 0000:00:02.0 (8086:0412)
ESCRITOS_POR_ESTA_ITERACION   ninguno dentro del arbol.  La sonda de offsets se
                              compilo en /tmp/opencode/,  fuera del arbol
CIERRA   1552 §LO QUE SIGUE  segundo punto:  "DRAM_LOG_* en tres structs, y solo
                         en uno se usa.  Eso es un mapa pequeno y cerrado que se
                         puede cerrar entero"
CIERRA   1540 §5,  que lo noto y no cerro
GENERADO=2026-10-06 · MEDIDO=EN ESTA HOST
```

## 1 · El mapa, por compilación

Ocho sitios, ocho structs distintos, y **los cinco campos en todos ellos**. offsets por `gcc` con
`#pragma pack(1)`, **una translation unit por generación**, porque los headers se redefinen si se
incluyen juntos:

```text
  struct                        fichero            tamaño   ADDR_H  ADDR_L  PHY_H  PHY_L  BUFF
  ----------------------------------------------------------------------------------------------
  SMU71_SoftRegisters           smu71.h              116       76      80     84     88     92
  SMU72_SoftRegisters           smu72.h              120       80      84     88     92     96
  SMU73_SoftRegisters           smu73.h              120       80      84     88     92     96
  SMU74_SoftRegisters           smu74.h              120       80      84     88     92     96
  SMU75_SoftRegisters           smu75.h              120       80      84     88     92     96
  SMU7_SoftRegisters  (discrete) smu7_discrete.h     120       80      84     88     92     96
  SMU7_SoftRegisters  (fusion)   smu7_fusion.h        84       44      48     52     56     60
  SMU7_Fusion_DpmTable           smu7_fusion.h       788      768     772    776    780    784
```

La última fila son los offsets que ya había medido `1540` con gcc, y encajan con los que he
medido hoy: **las dos mediciones, sobre la misma cabecera, coinciden.** Eso es la validación
cruzada que hacía falta entre `1540` y este hallazgo.

**Y los offsets no dependen de `SMU__NUM_*`**: compilado con `8/8/4` y con `3/2/1` sale
idéntico. Lo comprobé porque esas macros son tamaños de array ycreí que podrían moverlos. No
los mueven, y eso está medido, no supuesto.

## 2 · Cuál se usa en realidad, siguiendo la cadena de llamadas

El hwmgr no toca ningún struct (`1549`). Llama a `smum_get_offsetof`, y el offset lo contesta
**el smumgr**:

```c
  smu7_hwmgr.c:5500   smum_get_offsetof(hwmgr, SMU_SoftRegisters, DRAM_LOG_ADDR_H)
```

Y el smumgr que lleva la RX550 es el de la familia Polaris, que registra su función en
`:2695`:

```c
  2418  static uint32_t polaris10_get_offsetof(uint32_t type, uint32_t member)
  ...
        case SMU_SoftRegisters:
                switch (member) {
        ...
        case DRAM_LOG_ADDR_H:   return offsetof(SMU74_SoftRegisters, DRAM_LOG_ADDR_H);   :2437-2438
        case DRAM_LOG_ADDR_L:   return offsetof(SMU74_SoftRegisters, DRAM_LOG_ADDR_L);   :2439-2440
        case DRAM_LOG_PHY_ADDR_H: return offsetof(SMU74_SoftRegisters, ...);            :2441-2442
        case DRAM_LOG_PHY_ADDR_L: return offsetof(SMU74_SoftRegisters, ...);            :2443-2444
        case DRAM_LOG_BUFF_SIZE: return offsetof(SMU74_SoftRegisters, ...);             :2445-2446
        }
        break;
  2695        .get_offsetof = polaris10_get_offsetof,
```

**El struct que aplica es `SMU74_SoftRegisters`, de `smu74.h`.** No es `SMU7_SoftRegisters`, que
es el que lleva el "7" y el que el nombre del ASIC sugiere.

### El resultado operativo para la RX550

```text
  destino de las cinco escrituras  =  data->soft_regs_start + 80   (ADDR_H)
                                       data->soft_regs_start + 84   (ADDR_L)
                                       data->soft_regs_start + 88   (PHY_ADDR_H)
                                       data->soft_regs_start + 92   (PHY_ADDR_L)
                                       data->soft_regs_start + 96   (BUFF_SIZE)
```

Con la cadena completa, que es lo que la hace verificable:

```text
  smu7_hwmgr.c:5498   cgs_write_ind_register(..., CGS_IND_REG__SMC, base, valor)
      base = data->soft_regs_start
           + polaris10_get_offsetof(SMU_SoftRegisters, DRAM_LOG_X)        <- :2695
           = data->soft_regs_start + offsetof(SMU74_SoftRegisters, DRAM_LOG_X)
           = data->soft_regs_start + 80/84/88/92/96                       <- gcc, pack(1)
```

## 3 · Por qué hay ocho copias, y eso está bien

El diseño es correcto y **la polimorfía es portadora**, no decorativa:

```text
  include/pm/powerplay/inc/smumgr.h:29-33   enum SMU_TABLE   { UVD, VCE, BIF }
  include/pm/powerplay/inc/smumgr.h:35-38   enum SMU_TYPE    { SMU_SoftRegisters=0,
                                                               SMU_Discrete_DpmTable }
  include/pm/powerplay/inc/smumgr.h:40-56   enum SMU_MEMBER  { HandshakeDisables=0, ...,
                                                               DRAM_LOG_BUFF_SIZE }
```

Y el `switch` de `polaris10_get_offsetof` es el que traduce `(tipo, miembro)` a
`offsetof(<struct de esta generación>, <campo>)`. **El nombre del campo es común a las ocho
copias; el offset no.** Por eso hay ocho: cada generación tiene su layout y el smumgr elige.

Además las ocho son **mutuamente excluyentes por construcción**: incluir dos a la vez es un
error de redefinición, medido. No son ocho "copias de color" que se puedan mezclar.

## 4 · Los dos riesgos reales, que son distintos entre sí

### 4.1 · Colisión de nombre con 36 bytes de diferencia

```text
  smu7_discrete.h:38    struct SMU7_SoftRegisters    tamaño 120   bloque en 80
  smu7_fusion.h         struct SMU7_SoftRegisters    tamaño  84   bloque en 44
```

**Dos structs con el MISMO nombre, en dos headers, que no se pueden incluir a la vez, y con 36
bytes de diferencia** (`80 − 44 = 36`, y 120 − 84 = 36). Y con distinta cantidad de campos
declarados: **40 en discrete, 31 en fusion**.

El que se usa en la RX550 no es ninguno de los dos. Pero un lector que busque
"el `SMU7_SoftRegisters` de Polaris12" llegaría al de `smu7_fusion.h`, que es el de APU, y
obtendría 44.

Y el fallo que produciría **no se vería**: 44 y 80 caen ambos dentro de `SMU7_SoftRegisters`, así
que escribiría en el registro equivocado sin faults ni warnings.

### 4.2 · Un invariante que nadie comprueba

```text
  SMU72, SMU73, SMU74, SMU75  y  SMU7_discrete   ponen el bloque en 80.
  Cinco headers coinciden  byte a byte  y no hay NADA en el arbol que lo verifique.
```

Es un invariante real —lo he medido en cinco, y `1540` más yo lo hemos medido dos veces por
independencia en `SMU7_Fusion_DpmTable`— pero **es una coincidencia mantenida a mano.** Si
alguien añade un campo antes del bloque en uno solo de los cinco, el offset de ese smumgr
cambia y el de los otros no, y no hay nada que se queje.

**El peor caso medido es de 4 bytes, no de 36:** `SMU71` está en 76 y los otros cinco en 80.
Cuatro bytes es **un `uint32_t`**, así que el error sería escribir en el campo vecino sin
fallar nada. Ese es el modo de fallo peligroso, y es el que ya existe en el árbol como
divergencia entre 7.1 y 7.2.

## 5 · Procedimiento

```text
PREGUNTA   ¿en cuantos structs estan los cinco DRAM_LOG_*,  y cual usa la RX550?
FUENTES    grep estructural sobre los .h de include/pm/powerplay/,  que asigna cada
           campo a su struct por el llaves  (  los 9 ficheros,  8 structs  )
           smumgr.h:29-56   los tres enums
           polaris10_smumgr.c:2418-2450 y :2695
           smu7_hwmgr.c:5498-5526
MEDIDO     8 structs,  5 campos en cada uno,  offsets por gcc con pack(1)
     una TU por generacion:  los headers se redefinen juntos  (error medido)
     los offsets NO dependen de SMU__NUM_*:  8/8/4 y 3/2/1 dan el mismo resultado
     el struct que usa Polaris12  =  SMU74_SoftRegisters  (smu74.h)
     offset de ADDR_H = 80,  ADDR_L = 84,  PHY_H = 88,  PHY_L = 92,  BUFF = 96
     SMU71 es el unico divergente:  bloque en 76,  4 bytes antes
     SMU7_fusion  =  bloque en 44,  36 bytes antes,  y con el MISMO NOMBRE que
                    el de smu7_discrete.h
     validacion cruzada:  los offsets de SMU7_Fusion_DpmTable (768..784)  medidos
       hoy  coinciden con los que midio 1540 con gcc por otro camino
DESVIO MIO,  y lo cuento porque es el cuarto de esta tanda
  mi primer programa de sonda uso  #SM  (  el operador de conversion a cadena  )
  FUERA de un #define.  Solo funciona dentro de una macro,  y gcc lo leyo como
  una directiva de preprocesamiento.  Ademas lo puse como macro de sentencia en
  ámbito de fichero,  lo que tampoco compila.  Y un -D mio definia SM__NUM_...
  en vez de SMU__NUM_...,  por perder una U
  Los tres los vi  porque gcc los decia con el numero de linea.
  Y uno de mis escaneos estructurales fallo antes:  busco "typedef struct"  y
  smu7_fusion.h:209  abre su struct SIN la palabra typedef  (  esta en :284  ).
  Esa clase de fallo ya la pago por segunda vez en el mismo hilo,  y la primera
  me hizo poner en duda al 1540  cuando 1540 tenia razon.
DISPOSITIVO  NINGUNO.  i915 ausente,  amdgpu intacto,  no se escribio nada
RUNTIME      NOT_RUN
LO QUE SIGUE
  - lo que queda de este frente  y es pequeno:  el valor de soft_regs_start en
    esta placa.  El offset ya esta;  la base es runtime  y es lo unico que
    impide cerrar la direccion completa del DRAM log
  - y una idea de verificacion que no ejecuto aqui:  un chequeo estatico que
    compare los offsetof de los cinco campos entre smu72..smu75 y smu7_discrete
    y falle si divergen.  El invariante existe  y no lo vigila nadie
```