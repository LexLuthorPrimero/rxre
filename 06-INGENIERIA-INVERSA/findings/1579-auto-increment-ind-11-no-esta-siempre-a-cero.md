# 1579 — Ítem 3 cerrado: `AUTO_INCREMENT_IND_11` **no está siempre a 0** — el SMC no autoincrementa por defecto, el driver lo enciende solo para la subida del firmware, y `mmSMC_IND_ACCESS_CNTL` tiene **cuatro direcciones distintas** según la cabecera que enlace la unidad de compilación

```text
AGENCIA=RX550-INVESTIGACION · WORK_CLASS=CLOSEOUT · SEMANTICA-DE-REGISTRO
CLASSIFICATION=EVIDENCIA-POR-LECTURA-DE-CÓDIGO+EVIDENCIA-POR-GRAFO-DE-INCLUDES+CORRECCIÓN-PROPIA
MODIFICATIONS=1574 §"primitiva de lectura" (la corroboración más fuerte que podía tener)
AUTOR=AGENTE-INSTR
WRITE_EXECUTION=NONE · GPU=NONE TOUCHED · RUNTIME=NOT_RUN
DISPOSITIVO_TOCADO=NINGUNO · ni 0000:01:00.0 (1002:699f) ni 0000:00:02.0 (8086:0412)
ESCRITOS_POR_ESTA_ITERACION   ninguno (solo lectura)
CIERRA   el tercer hueco de riesgo cero,  y CORRIGE una afirmación mía
```

## 0 · La afirmación que yo arrastraba, y que era falsa a medias

En mi estado de trabajo tenía escrito, sobre este registro:

```text
  "SMC_IND_ACCESS_CNTL / AUTO_INCREMENT_IND_11 — lo que escribe
   smu7_smumgr.c:44 con valor 0 antes de cada lectura.  O sea que el SMC no
   autoincrementa, y eso gobierna si smu7_copy_bytes_to_smc hace algo
   elegante.  Que hace EDC y power en el stepping 0xCF..."
```

La primera mitad es **cierta pero estaba mal generalizada**: es cierto que `:44` pone 0,
pero **`smu7_smumgr.c:425` lo pone a 1**, y hay un camino entero que depende de eso. Lo
que estaba por ver —"si `smu7_copy_bytes_to_smc` hace algo elegante"— es exactamente lo
que resulta ser: hace lo contrario de lo que hace el otro camino, y la razón es
justamente el bit.

## 1 · El bit, y su posición

```text
  smu_7_1_3_sh_mask.h:391   SMC_IND_ACCESS_CNTL__AUTO_INCREMENT_IND_11_MASK   0x800
  smu_7_1_3_sh_mask.h:392   SMC_IND_ACCESS_CNTL__AUTO_INCREMENT_IND_11__SHIFT 0xb
```

Bit 11, máscara `0x800`. Idéntico en 7.1.1, 7.1.2 y 7.1.3. Y el campo **no se llama igual
en todas partes**:

```text
  AUTO_INCREMENT_IND_0    si_smc.c  ci_smumgr.c  iceland_smumgr.c   (ASICs viejos)
  AUTO_INCREMENT_IND_11   smu7_smumgr.c                          (SMU7)
```

Y AMD lo dice explícitamente en el propio código, en un comentario que es la razón de
todo este hallazgo:

```c
  smu7_smumgr.c:44
      PHM_WRITE_FIELD(hwmgr->device, SMC_IND_ACCESS_CNTL,
                      AUTO_INCREMENT_IND_11, 0);
      /* on ci, SMC_IND_ACCESS_CNTL is different */
```

## 2 · Los dos caminos, y por qué divergen

**Camino A — un dword cada vez. El índice se reescribe SIEMPRE.**

```c
  smu7_smumgr.c:38-46   smu7_set_smc_sram_address()
      :40   assert  4-byte aligned
      :41   assert  dentro del area
      :43   cgs_write_register(device, mmSMC_IND_INDEX_11, smc_addr);
      :44   AUTO_INCREMENT_IND_11 = 0
```

Y su consumidor, `smu7_copy_bytes_to_smc` (`:49-112`):

```c
      :63   while (byte_count >= 4) {
      :65       data = src[0]*0x1000000 + src[1]*0x10000 + src[2]*0x100 + src[3];
      :67       result = smu7_set_smc_sram_address(hwmgr, addr, limit);   <-- EN EL BUCLE
      :72       cgs_write_register(device, mmSMC_IND_DATA_11, data);
      :76       addr += 4;
```

**Volver a escribir el índice dentro del bucle es la consecuencia directa del bit a 0.**
Con auto-incremento activado, las líneas 67 y 76 sobrarían.

**Camino B — subida del firmware. El índice NO se reescribe nunca.**

```c
  smu7_smumgr.c:418-435  smu7_upload_smc_firmware_data()
      :424  cgs_write_register(device, mmSMC_IND_INDEX_11, 0x20000);   <-- una vez
      :425  AUTO_INCREMENT_IND_11 = 1
      :427  for (; byte_count >= 4; byte_count -= 4)
      :428      cgs_write_register(device, mmSMC_IND_DATA_11, *src++);  <-- en cascada
      :430  AUTO_INCREMENT_IND_11 = 0                                 <-- lo restaura
```

**La semántica queda cerrada:**

```text
  AUTO_INCREMENT_IND_11 = 0   el puerto de DATOS no mueve el INDICE
                              -> hay que reescribir el indice por dword
                              -> smu7_copy_bytes_to_smc lo hace en el bucle (:67)
  AUTO_INCREMENT_IND_11 = 1   el puerto de DATOS avanza el indice solo
                              -> se puede escribir en cascada
                              -> smu7_upload_smc_firmware_data lo hace (:427-428)
                              -> y devuelve el registro a 0 al terminar (:430)
```

O sea, respondiendo a mi pregunta de ayer de forma directa: **el SMC no autoincrementa;
lo que autoincrementa es una decisión del driver, tomada solo para volcar el firmware,
y deshecha al terminar.** No hay estado oculto entre llamadas, y por eso
`smu7_read_smc_sram_dword` es seguro sin un `AUTO_INCREMENT` explícito antes de cada
lectura.

## 3 · Y de paso queda fijada una convención de bytes, que no era explícita en ninguna parte

```c
  smu7_smumgr.c:64   /* Bytes are written into the SMC addres space with the MSB first. */
  smu7_smumgr.c:65   data = src[0]*0x1000000 + src[1]*0x10000 + src[2]*0x100 + src[3];
```

**El espacio de direcciones del SMC es MSB-first (big-endian) para los bytes de un
dword.** Es decir, el byte que va en la dirección más baja es el de **menor peso**. Eso
no es lo que hace la CPU con un `memcpy` normal, y no aparece en ningún header: solo en
un comentario y en esa línea.

Y el resto de bytes sueltos se hace por read-modify-write (`:79-109`):

```c
      :89   original_data = cgs_read_register(device, mmSMC_IND_DATA_11);   <-- LECTURA
      :91   extra_shift = 8 * (4 - byte_count);
      :99   data <<= extra_shift;
      :101  data |= (original_data & ~((~0UL) << extra_shift));             <-- conserva
      :108  cgs_write_register(device, mmSMC_IND_DATA_11, data);
```

## 4 · El hallazgo de fondo: la DIRECCIÓN del registro depende de la cabecera, y el árbol usa cuatro

Esto sí es un peligro con forma, y no lo buscaba:

```text
  fichero que USA el registro        cabecera que incluye       valor
  ----------------------------------------------------------------------
  si_smc.c                           smu/smu_6_0_d.h            0x008A
  ci_smumgr.c                        smu/smu_7_0_1_d.h          0x0090
  kv_smc.c                           smu/smu_7_0_0_d.h          0x0090
  iceland_smumgr.c                   smu/smu_7_1_1_d.h          0x0090
  smu7_smumgr.c  <-- NUESTRO CAMINO   (via smu7_common.h)        0x0092
                                                            smu_7_1_3_d.h
```

**En nuestro camino el valor es `0x92`**, y la cadena que lo fija es explícita:

```text
  smu7_smumgr.c --> smu7_common.h:30 --> include "smu/smu_7_1_3_d.h"
```

Y `smu7_common.h` es, de hecho, **el juego de registros completo de GFX8 en una sola
cabecera**, con el emparejamiento de bloques escrito a mano:

```c
  smu7_common.h:30   smu/smu_7_1_3_d.h        <- el bloque SMU,  prestado de 7.1.3
  smu7_common.h:37   gmc/gmc_8_1_d.h           <- el bloque MC,   prestado de 8.1
  smu7_common.h:40   bif/bif_5_0_d.h
  smu7_common.h:43   dce/dce_10_0_d.h
  smu7_common.h:46   gca/gfx_8_0_d.h          <- el bloque GFX,  NATIVO
  smu7_common.h:49   oss/oss_3_0_d.h
```

Eso **corrobora `1546` por una vía independiente**: GFX8 es nativo en `gca`, prestado en
`gmc` —y ahora también se ve que el bloque **SMU está prestado de la familia 7.1.3**.

**Y el peligro, enunciado:** *elegir qué registro se direcciona es un efecto lateral de
elegir qué cabecera se incluye.* No hay `static_assert`, ni macro de comprobación, ni
comentario que lo advierta. El único aviso que existe es el comentario de `smu7_smumgr.c:44`,
que habla de CI y no del mecanismo general. Si alguien añade a un fichero de GFX8 un uso
de `SMC_IND_ACCESS_CNTL` y ese fichero enlaza `smu_7_1_1_d.h` por otra razón, escribirá
en `0x90` creyendo que es el mismo registro. **Hoy no hay ningún conflicto vivo** —
los cinco que lo usan son de ASICs anteriores a GFX8, y `vi.c` (que sí enlaza
`smu_7_1_1_d.h`, `:50`) no lo toca—, pero el mecanismo no avisa.

## 5 · Y el resultado que más me importa: la lectura de `0x20030` ya tiene receta del propio driver

`1574` dejó pendiente el valor de `SMC_RAM[0x20030]`, y dijo que hacen falta dos accesos
de registro. **Acabo de encontrar esos dos accesos escritos por AMD, dos veces:**

```c
  smu7_smumgr.c:229-238   smu7_read_smc_sram_dword()
      :233   result = smu7_set_smc_sram_address(hwmgr, smc_addr, limit);
             //  = escribir mmSMC_IND_INDEX_11 (0x1AC) con smc_addr
             //  = poner AUTO_INCREMENT_IND_11 a 0
      :235   *value = cgs_read_register(device, mmSMC_IND_DATA_11);   //  leer 0x1AD
```

Y el read-modify-write de `:89` hace exactamente el mismo par para un dword parcial.

**La receta que voy a proponer es, literalmente, la del driver:** escribir el índice,
dejar el auto-incremento a 0, leer el puerto de datos. Lo que `1574`.chainaba como
"primitiva deducida" queda corroborado por el consumidor real de la función.

**Y hay un dato de robustez que no tenía:** las direcciones del par que necesito **no
dependen de qué cabecera se elija**:

```text
                smu_7_1_1   smu_7_1_2   smu_7_1_3
  mmSMC_IND_INDEX_11    0x1AC      0x1AC      0x1AC
  mmSMC_IND_DATA_11     0x1AD      0x1AD      0x1AD
```

Los tres linajes coinciden. O sea que **la duda que yo tenía sobre "qué cabecera toma
prestada GFX8" no bloquea esa lectura**, que es lo único que me quedaba por resolver de
esa pregunta. Lo que sí depende de la cabecera es `SMC_IND_ACCESS_CNTL` (0x90 vs 0x92),
y como la lectura solo necesita el par INDEX/DATA, la lectura queda **independiente del
linaje**.

## 6 · Procedimiento y alcance

```text
PREGUNTA   que gobierna SMC_IND_ACCESS_CNTL / AUTO_INCREMENT_IND_11,  y si el SMC
           autoincrementa
FUENTES    las definiciones de registro y de campo en include/asic_reg/smu
           los 5 ficheros que usan el registro,  con la cabecera que enlazan
           la cadena smu7_smumgr.c -> smu7_common.h -> smu_7_1_3_d.h
           smu7_copy_bytes_to_smc entero        (:49-112)
           smu7_upload_smc_firmware_data entero (:418-435)
           smu7_read_smc_sram_dword             (:229-238)
MEDIDO     el bit es el 11,  mascara 0x800,  identico en los tres linajes
           el campo se llama AUTO_INCREMENT_IND_0 en los ASICs viejos  y
           AUTO_INCREMENT_IND_11 en SMU7,  con un comentario de AMD en :44
           AUTO_INCREMENT = 0  ->  el consumidor REESCRIBE el indice en el bucle (:67)
           AUTO_INCREMENT = 1  ->  el consumidor escribe en cascada      (:427-428)
                                  y lo restaura a 0                      (:430)
           la direccion del CNTL es 0x8A / 0x90 / 0x90 / 0x90 / 0x92 segun cabecera
           NUESTRO camino da 0x92,  via smu7_common.h:30
           smu7_common.h empareja 7_1_3 + gmc_8_1 + gfx_8_0  -> corrobora 1546
           INDEX_11 y DATA_11 valen 0x1AC / 0x1AD en los TRES linajes
DESVIO MIO  la afirmacion que yo arrastraba  ("no autoincrementa")  era cierta a
           medias: certaino que :44 lo pone a 0,  pero hay un segundo camino que
           lo pone a 1.  No lo habiamirado porque solo lei la llamada de lectura
DISPOSITIVO  NINGUNO.  i915 ausente,  amdgpu intacto
RUNTIME      NOT_RUN
```

## 7 · Lo que sigue

```text
  huecos de riesgo cero restantes:  4 · 5 · 6 · 7
  el 4 ya tiene la mecanica:  comparar POR OFFSET  y no por nombre.  Aqui se
       ha visto por que funciona:  las truncaturas de nombre  y el desglose de
       Reserved[3] de 1578  son la misma falta de alineacion entre copias
  y sigue en pie lo unico que cierra soft_regs_start:  el valor de
       SMC_RAM[0x20030].  Ahora con la receta del propio driver,  con las dos
       direcciones confirmadas en los tres linajes,  y sin depender de que
       cabecera toma prestada GFX8.  Falta tu OK para los dos accesos
```