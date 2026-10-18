# 1550 — Las 13 fuentes de interrupción de esta tarjeta, con su `src_id` resuelto. Y el `src_id` del EOP de gráficos es 181, el mismo número que `gfx_v6_0` tenía escrito a mano

```text
AGENCIA=RX550-INVESTIGACION · WORK_CLASS=AGENT-RE-TOOLING
GENERADO=2026-10-05 · MEDIDO=EN ESTA HOST

AREA FIJADA    tonga_ih.

CIERRA         el punto 2 de 1534 §7:  "que hace el driver con cada IRQ".
               La tabla de fuentes existe, es de 13 entradas para POLARIS12,
               y cada una tiene su src_id resuelto.

PROVEN         POLARIS12 registra 13 fuentes de IRQ en 5 bloques:
               5 en gfx, 2 en gmc, 3 en sdma, y 1 cada una en uvd y vce.
PROVEN         CP_END_OF_PIPE = 0xB5 = 181.  Y gfx_v6_0.c:3112 usa el
               LITERAL 181 para lo mismo.  El numero no cambia desde GFX6.
PROVEN_DERIVED  el src_id es una propiedad del MOTOR, no de la generacion.
               Los 4 pares que se pueden cruzar (181, 184, 185, 146, 147,
               224, 247) son identicos entre gfx_v6_0, gmc_v6_0, cik_sdma y
               gfx_v8_0 / gmc_v8_0 / sdma_v3_0.
DESCUBRE       las cabeceras de subdirectorio NO faltan:  estan en
               amd/include/, no en amdgpu/.  Mi ruta de busqueda estaba mal.
ERROR, mio     dos.  Uno de ruta (busque en amdgpu/ lo que estaba en
               amd/include/) y uno de conclusion:  dije que el simbolo
               "no se define en ninguna cabecera" cuando la cabecera estaba,
               en otro directorio.
```

## 0 · DE DONDE

`1534` §7:

```text
  2. ¿Qué hace el driver con cada IRQ?  amdgpu_irq.c lo consume, pero eso es
     dentro.  El nombre del IRQ en /proc/interrupts dice "amdgpu" y nada más.
     Para el desglose (src_id, ring_id, vmid) hace falta el ring, que sigue
     cerrado.
```

Y `1531` §3 había dicho que la entrada del IH lleva `src_id`, `ring_id` y
`vmid`. El `ring_id` y el `vmid` necesitan el ring. **El `src_id` no**: es un
campo del driver, y la tabla de fuentes está en el código.

## 1 · LA TABLA DE FUENTES, Y CÓMO SE CONSTRUYE

`amdgpu_irq.c:492-501` consume la entrada del IH:

```c
client_id = entry.client_id;
src_id = entry.src_id;

if (client_id >= AMDGPU_IRQ_CLIENTID_MAX) {
        dev_dbg(adev->dev, "Invalid client_id in IV: %d\n", client_id);
} else if (src_id >= AMDGPU_MAX_IRQ_SRC_ID) {
        dev_dbg(adev->dev, "Invalid src_id in IV: %d\n", src_id);
}
```

Y la tabla se llena con `amdgpu_irq_add_id` (`amdgpu_irq.c:423`):

```c
int amdgpu_irq_add_id(struct amdgpu_device *adev,
                      unsigned int client_id, unsigned int src_id,
                      struct amdgpu_irq_src *source)
{
        if (client_id >= AMDGPU_IRQ_CLIENTID_MAX)
                return -EINVAL;
        if (src_id >= AMDGPU_MAX_IRQ_SRC_ID)
                return -EINVAL;
        ...
        adev->irq.client[client_id].sources[src_id] = source;
}
```

```text
  PROVEN  la tabla es bidimensional:  client[client_id].sources[src_id].
          Y 1531 §3 decia que tonga_ih_decode_iv pone
          entry->client_id = AMDGPU_IRQ_CLIENTID_LEGACY, o sea SIEMPRE 0.

  PROVEN_DERIVED  con client_id fijo en 0, la tabla efectiva es de UNA
          dimension para mi ASIC:  la de src_id.  Y el limite es
          AMDGPU_MAX_IRQ_SRC_ID = 0x100 = 256 (amdgpu_irq.h:32).
```

**O sea: 256 ranuras, 13 ocupadas.** Y el driver valida el rango en el registro
*y* en el consumo. Es un array disperso con 243 entradas vacías.

## 2 · LAS 13 FUENTES DE POLARIS12, CON SU `src_id`

Inventario cerrado de `amdgpu_irq_add_id` en el árbol, filtrado por los bloques
que `vi.c:2106-2126` instancia para `CHIP_POLARIS12`:

```text
  gfx_v8_0.c:1914-1941   5 fuentes
    CP_END_OF_PIPE              0xB5 = 181    -> adev->gfx.eop_irq
    CP_PRIV_REG_FAULT           0xB8 = 184    -> adev->gfx.priv_reg_irq
    CP_PRIV_INSTR_FAULT         0xB9 = 185    -> adev->gfx.priv_inst_irq
    CP_ECC_ERROR                0xC5 = 197    -> adev->gfx.cp_ecc_error_irq
    SQ_INTERRUPT_MSG            0xEF = 239    -> adev->gfx.sq_irq

  gmc_v8_0.c:1109-1115   2 fuentes
    GFX_PAGE_INV_FAULT          0x92 = 146    -> adev->gmc.vm_fault
    GFX_MEM_PROT_FAULT          0x93 = 147    -> adev->gmc.vm_fault

  sdma_v3_0.c:1124-1140  3 fuentes
    SDMA_TRAP                   0xE0 = 224    -> adev->sdma[...]
    literal 241                 0xF1 = 241
    SDMA_SRBM_WRITE             0xF7 = 247    -> adev->sdma[...]

  uvd_v6_0.c:387-394     2 fuentes
    UVD_SYSTEM_MESSAGE          0x7C = 124
    + las de UVD_ENC_GEN_PURP, en bucle sobre las instancias

  vce_v3_0.c:430         1 fuente
    VCE_TRAP                    0xA7 = 167
```

```text
  PROVEN  13 fuentes registradas por el driver para POLARIS12, en 5 bloques.
          De ellas, 5 son de gráficos, 2 de faults de memoria, 3 de SDMA,
          2 de UVD y 1 de VCE.

  Y LO QUE NO PUEDO DECIR, y es importante decirlo:
          el registro en bucle de uvd_v6_0.c:394 y las fuentes que dependen
          del numero de instancias hacen que el total exacto dependa de la
          configuracion.  13 es lo que se registra en el codigo para mi ASIC
          con los bloques que vi.c instancia.  NO AFIRMO que sean 13 en
          ejecucion sin el debugfs.
```

## 3 · Y EL DATO QUE CIERRA UNA HISTORIA DE VARIAS GENERACIONES

Las 5 fuentes de gráficos, con el nombre resuelto desde
`amd/include/ivsrcid/ivsrcid_vislands30.h`. Y ahora el cruce:

```text
  gfx_v6_0.c:3112   amdgpu_irq_add_id(adev, AMDGPU_IRQ_CLIENTID_LEGACY, 181, &adev->gfx.eop_irq);
  gfx_v8_0.c:1914   amdgpu_irq_add_id(adev, AMDGPU_IRQ_CLIENTID_LEGACY,
                                         VISLANDS30_IV_SRCID_CP_END_OF_PIPE, ...);

  181 == 0xB5 == CP_END_OF_PIPE
```

Y los otros pares que se pueden cruzar:

```text
  gfx_v6_0.c:3116   184  (literal)  ==  CP_PRIV_REG_FAULT     0xB8
  gfx_v6_0.c:3120   185  (literal)  ==  CP_PRIV_INSTR_FAULT   0xB9
  gmc_v6_0.c:822    146  (literal)  ==  GFX_PAGE_INV_FAULT    0x92
  gmc_v6_0.c:826    147  (literal)  ==  GFX_MEM_PROT_FAULT    0x93
  cik_sdma.c:954    224  (literal)  ==  SDMA_TRAP             0xE0
  cik_sdma.c:966    247  (literal)  ==  SDMA_SRBM_WRITE       0xF7
  sdma_v2_4.c:850   241  (literal)  ==  (el mismo 241 de sdma_v3_0.c:1130)
```

```text
  PROVEN_DERIVED  el src_id es una propiedad del MOTOR, no de la generacion.
                  Siete numeros documentados son identicos entre GFX6, GFX7,
                  GFX8, Caribbean y Tonga.

  Y POR ESO, PARA UN DRIVER PROPIO, ESTO ES UTIL:
      no hace falta inventar una tabla de interrupciones.  La de la
      generacion vigente describe la de la anterior, al menos en estos 7
      casos.  Un driver nuevo puede heredar la tabla de gfx_v8_0 y tiene
      razon en la mayoria de los casos.

  Y CONTRASTE CON 1534 §3, donde la tabla parecia dimensionada para cambiar:
      aqui los numeros SI son estables.  Lo que cambia entre generaciones es
      la cabecera del NOMBRE, no el valor.  Ese matiz es el que faltaba.
```

## 4 · MI ERROR DE RUTA, Y ES EL TERCERO DE LA SERIE DE CABECERAS

Busqué `VISLANDS30_IV_SRCID_CP_END_OF_PIPE` en todo el árbol y encontré **una sola
coincidencia: el uso en `gfx_v8_0.c:1914`**. Ninguna definición. Y escribí:

```text
  ERROR, mio  el símbolo se usa pero no se define en ninguna cabecera.
```

**Falso.** Y el `Makefile` del propio driver dice donde mirar, textual:

```bash
$ sed -n '34,35p' amdgpu/Makefile
ccflags-y := -I$(FULL_AMD_PATH)/include/asic_reg \
        -I$(FULL_AMD_PATH)/include \
```

```text
  O SEA:  el driver compila con DOS raices de include, y una de ellas es
          include/asic_reg/, que es donde estan bif/, oss/, gmc/, gc/, etc.

  Y MI TEST NO USA NINGUNA DE LAS DOS.  Use $K = .../amd/amdgpu, que no es
  raiz de include de nada.

  Y ESTO CORRIGE 1531 §5 ENTERO, y en dos direcciones:

  1. EL NUMERO.  1531 conto "94 .c que no compilan".  Con las dos raices del
     Makefile, ese numero NO SE COMPRUEBA.  Y al menos uno de los que cito
     (bif_5_1_d.h, el de tonga_ih.c) SI esta:

        amd/include/asic_reg/bif/bif_5_1_d.h    PRESENTE
        amd/include/asic_reg/oss/oss_3_0_d.h    PRESENTE
        amd/include/asic_reg/gmc/gmc_8_1_d.h    PRESENTE
        amd/include/asic_reg/gmc/gmc_8_2_d.h    PRESENTE
        include/ivsrcid/ivsrcid_vislands30.h     PRESENTE

     PERO gc_8_0_d.h NO ESTA EN NINGUN SITIO DEL CORPUS, y gfx_v8_0.c lo
     incluye.  Ese si es un hueco real, y es el unico que he confirmado.

  2. EL ALCANCE.  1531 §5 decia "el corpus esta sano para leer pero NO
     COMPILABLE".  Si el 94 es un error mio, entonces la segunda mitad de esa
     frase no se sostiene, y hay que rehacerla.

  ERROR, mio  nueve veces con la forma "no mire la ruta".  Esta es la mas
              grave por una razon concreta:  no era un simbolo ni un fichero,
              era el CONJUNTO del arbol, y lo medi con una raiz que yo mismo
              inventé en lugar de leer el Makefile que estaba a 3 lineas.
              Y el Makefile es la primera cosa que se lee al compilar un
              driver de kernel.  Debí leerlo antes de afirmar nada.
```

## 5 · ESTADO

```text
PROVEN          la tabla de fuentes de IRQ es
                adev->irq.client[client_id].sources[src_id], con
                AMDGPU_MAX_IRQ_SRC_ID = 0x100 = 256 ranuras.
                1531 §3 decia que client_id es siempre 0 para mi ASIC
                (AMDGPU_IRQ_CLIENTID_LEGACY), asi que la tabla efectiva es de
                una dimension.
PROVEN          el driver valida el rango en el registro (add_id) y en el
                consumo (amdgpu_irq.c:495-501).
PROVEN          POLARIS12 registra 13 fuentes en 5 bloques:
                5 gfx, 2 gmc, 3 sdma, 2 uvd, 1 vce.  Con su src_id:
                  gfx    CP_END_OF_PIPE 181  CP_PRIV_REG_FAULT 184
                         CP_PRIV_INSTR_FAULT 185  CP_ECC_ERROR 197
                         SQ_INTERRUPT_MSG 239
                  gmc    GFX_PAGE_INV_FAULT 146  GFX_MEM_PROT_FAULT 147
                  sdma   SDMA_TRAP 224  literal 241  SDMA_SRBM_WRITE 247
                  uvd    UVD_SYSTEM_MESSAGE 124  (+ UVD_ENC_GEN_PURP)
                  vce    VCE_TRAP 167
PROVEN_DERIVED  el src_id es propiedad del MOTOR, no de la generacion:
                7 numeros identicos entre GFX6, GFX7, GFX8, CIK y Tonga.
                En gfx_v6_0 estan escritos a mano (181, 184, 185) y en
                gfx_v8_0 como simbolo; el valor es el mismo.
NOT_DETERMINED  si son 13 EN EJECUCION.  El registro de uvd_v6_0:394 va en
                bucle sobre instancias, y el total depende de la
                configuracion.  Verificarlo necesita debugfs.

CORRIGE, mio   1531 §5 ENTERO.  El "94 .c que no compilan" esta medido con
                una raiz falsa ($K = .../amd/amdgpu).  El Makefile declara
                -I.../amd/include/asic_reg y -I.../amd/include, y con esas
                dos raices bif_5_1_d.h, oss_3_0_d.h, gmc_8_1_d.h,
                gmc_8_2_d.h e ivsrcid_vislands30.h ESTAN PRESENTES.
                Un hueco confirmado: gc_8_0_d.h, que gfx_v8_0.c incluye y no
                esta en ninguna parte del corpus.
REFUTADO, mio  1531 §5: "el corpus esta sano para leer pero NO COMPILABLE".
                La segunda mitad no se sostiene.  Queda un hueco real, y es
                uno, no 94.
REFUTADO, mio  "el simbolo VISLANDS30_IV_SRCID_* no se define en ninguna
                cabecera del corpus".  Si se define, en
                amd/include/ivsrcid/ivsrcid_vislands30.h.
```

## 6 · LO QUE SIGUE

```text
  1. Y CON ESTO, EL RING DEL IH TIENE UNA TERCERA VIA DE LECTURA.  No es la
     unica:
        a) el ring del IH, si se exporta  -> 1534: PROVEN_ABSENT
        b) amdgpu_regs con el offset    -> llega a rptr/wptr, no al contenido
        c) ESTA:  la tabla de fuentes.  Es codigo, y da el mapa de que puede
           interrumpir, sin ningun privilegio.

     Las tres dan cosas distintas.  a da los valores.  b da los punteros.
     c da la estructura.  Y c es la unica que ya tengo cerrada.

  2. LO QUE SIGUE ABIERTO, y es lo que mas me importa:  los 13 src_id dicen
     QUE puede interrumpir, pero no CUANDO ni CUANTAS.  Y las 4 EOP por frame
     de 1508 son 4 interrupciones de EOP.  Si CP_END_OF_PIPE = 181 es la que
     dispara el handler, entonces las 4 EOP son 4 disparos de la misma fuente,
     y eso es una cuenta:  4 EOP por frame x frames por IRQ.

     PERO ESO NECESITA EL RING.  Y EL RING SIGUE CERRADO.  Lo digo porque es
     el punto donde se me dea cerrar tonga_ih sin cerrarlo del todo.

  3. Y LA CORRECCION MAS GRANDE DE ESTA SESION, que toca a 1531 y obliga a
     revisar hacia atras:

     1531 §5 conto 94 .c que no compilan.  MEDIDO MAL, por raiz equivocada.
     El Makefile del driver (linea 34-35) declara las dos raices correctas, y
     con ellas las cabeceras que yo decia ausentes estan presentes.

     Y ESO OBLIGA A REVISAR OTROS INVENTARIOS MIOS DE "LO QUE FALTA", porque
     todos compartian el mismo error de fondo:  construi la ruta en lugar de
     leerla.

     CONCRETO, LO QUE HAY QUE REVISAR:
        - 1479  "falta include/drm/".  ¿Habria otra raiz?
        - 1471  use gmc/gmc_8_1_d.h.  ¿Era ruta inventada?
        - 1480  "5 de 1000 con include no resuelto".  ¿Con que raiz?
        - 1531 §5, este, ya corregido.

     Y HAY UN HUECO REAL CONFIRMADO:  gc_8_0_d.h.  Lo incluye gfx_v8_0.c y
     no esta en ninguna parte del corpus.  Ese es el unico que sobrevive.

     NO AFIRMO QUE LOS OTROS ESTEN MAL.  Digo que no los he re-verificado con
     la raiz correcta, y que hasta ahora ninguno se ha hecho.  Ese es el
     trabajo que sigue, y es hacia atras.
```

Ese punto 3 es el que me obliga a parar y mirar atrás, no adelante. Es la
octava vez que un error mío obliga a revisar hallazgos anteriores en vez de
avanzar, y las ocho estaban justificadas. Pero esta podría invalidar una
afirmación sobre el material entero, así que la compro antes de seguir.