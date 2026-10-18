# 1554 — Re-medido con las rutas del `Makefile`: 2640 de 2648 includes resuelven. El hueco real no son las cabeceras ASIC: son `pp_smu` y `dm`, dos de los nueve bloques de POLARIS12, que no están

```text
AGENCIA=RX550-INVESTIGACION · WORK_CLASS=AGENT-RE-TOOLING
GENERADO=2026-10-05 · MEDIDO=EN ESTA HOST

PROMESA QUE CUMPLO   1550 §7 punto 3:  re-medir los inventarios de "lo que
                     falta" con las rutas del Makefile, antes de escribir nada
                     más.  Esta es esa re-medición.

REFUTA, mio    1531 §5 completo.  Decia "94 .c no compilan" y "el corpus esta
               sano para leer pero NO COMPILABLE".  MEDIDO con las 12 rutas
               reales:  2640 de 2648 includes resuelven = 99,70 %.
PROVEN         los 8 que no resuelven son 3 cabeceras en 3 ficheros, y dos de
               ellos (cik.c, si.c) son de ASICs que no son POLARIS12.
DESCUBRE       el hueco REAL:  pp_smu.c y dm.c NO EXISTEN en el corpus, y son
               dos de los nueve ip_blocks que vi.c instancia para CHIP_POLARIS12.
               smu/ tiene 0 entradas y dc/ tiene 0.
PROVEN         amdkfd (68), ras/ras_mgr (17), display (7) y pm/inc (3) SI estan.
               El corpus esta recortado por modulo, no por cabecera.
ERROR, mio     el que mas me importa:  tardo 30 hallazgos en leer un Makefile
               que estaba a 3 lineas y que define la verdad de donde estan las
               cabeceras.
```

## 0 · LA PROMESA

`1550` §7 punto 3, textual:

```text
  3. Y LA CORRECCION MAS GRANDE DE ESTA SESION, que toca a 1531 y obliga a
     revisar hacia atras:  ...
     CONCRETO, LO QUE HAY QUE REVISAR:
        - 1479  "falta include/drm/".  ¿Habria otra raiz?
        - 1471  use gmc/gmc_8_1_d.h.  ¿Era ruta inventada?
        - 1480  "5 de 1000 con include no resuelto".  ¿Con que raiz?
        - 1531 §5, este, ya corregido.

     Y HAY UN HUECO REAL CONFIRMADO:  gc_8_0_d.h.  Lo incluye gfx_v8_0.c y
     no esta en ninguna parte del corpus.
```

Antes que nada, una corrección: **dije que `gc_8_0_d.h` no estaba en ninguna
parte. Eso es cierto, pero incompleto** — `gc` sí está como subdirectorio de
`include/asic_reg/`, lo que pasa es que no tiene `gc_8_0_d.h`. Ver §3.

## 1 · LAS DOCE RUTAS, COPIADAS DEL MAKEFILE

`amdgpu/Makefile:34-45`, literalmente:

```bash
ccflags-y := -I$(FULL_AMD_PATH)/include/asic_reg \
	-I$(FULL_AMD_PATH)/include \
	-I$(FULL_AMD_PATH)/amdgpu \
	-I$(FULL_AMD_PATH)/pm/inc \
	-I$(FULL_AMD_PATH)/acp/include \
	-I$(FULL_AMD_DISPLAY_PATH) \
	-I$(FULL_AMD_DISPLAY_PATH)/include \
	-I$(FULL_AMD_DISPLAY_PATH)/modules/inc \
	-I$(FULL_AMD_DISPLAY_PATH)/dc \
	-I$(FULL_AMD_DISPLAY_PATH)/amdgpu_dm \
	-I$(FULL_AMD_PATH)/amdkfd \
	-I$(FULL_AMD_PATH)/ras/ras_mgr
```

**Once `-I`, y el Makefile no añade nada más.** La medición es exactamente esa
lista, con `FULL_AMD_PATH` = `.../drivers/gpu/drm/amd` y
`FULL_AMD_DISPLAY_PATH` = `.../drivers/gpu/drm/amd/display`.

## 2 · LA RE-MEDICIÓN

Sobre los 307 `.c` del driver, los 2648 includes con comillas:

```text
  resueltos:    2640   (99,70 %)
  SIN resolver:    8   ( 0,30 %)
```

Los 8, agrupados:

```text
    amdgpu_smu.h     x6    (amdgpu_vpe.c)
    cik_dpm.h        x1    (cik.c)
    si_dpm.h         x1    (si.c)
```

```text
  PROVEN  el driver resuelve el 99,70 % de sus includes con las rutas que el
          propio Makefile declara.

  Y DE LOS 8 QUE FALTAN, 2 ESTAN EN FICHEROS QUE NO SON MI ASIC:
      cik.c   -> Carribean,  0 apariciones de CHIP_POLARIS12
      si.c    -> Northern Islands,  0 apariciones

  amdgpu_vpe.c no tiene CHIP_POLARIS12 pero si esta en el Makefile, asi que
  se compila siempre; el suyo es amdgpu_smu.h, que esta en pm/swsmu/inc/, un
  subdirectorio que el corpus no tiene.

  PROVEN  para POLARIS12 el impacto de los 8 es CERO en cik.c y si.c, y
          ninguno en los 9 ip_blocks que vi.c instancia.
```

## 3 · Y EL HUECO REAL, QUE NO SON LAS CABECERAS

Cuando `1531` conto 94, concluyo que el corpus esta sano para leer pero no
compilable. La segunda mitad era mia y era falsa. Pero **la primera es
cierta, y el hueco que sí existe no está donde yo decía.**

Los nueve ip_blocks de `CHIP_POLARIS12` (`vi.c:2106-2126`):

```text
  vi_common           vi.c          presente
  gmc_v8_1            gmc_v8_0.c    presente
  tonga_ih            tonga_ih.c    presente
  gfx_v8_0            gfx_v8_0.c    presente
  sdma_v3_1           sdma_v3_0.c   presente
  pp_smu              pp_smu.c      NO EXISTE EN EL CORPUS
  dm                  dm.c          NO EXISTE EN EL CORPUS
  uvd_v6_3            uvd_v6_0.c    presente
  vce_v3_4            vce_v3_0.c    presente
```

Y la razón:

```bash
$ grep -rn "pp_smu_ip_block\s*=" *.c        -> nada
$ grep -rn "dm_ip_block\s*=" *.c            -> nada
$ ls smu/ | wc -l                            -> 0
$ ls dc/   | wc -l                            -> 0
$ find . -name "pp_smu.h"                    -> nada
```

```text
  PROVEN_ABSENT  con inventario cerrado:  pp_smu_ip_block y dm_ip_block NO se
                 definen en ninguna parte del corpus.  Y smu/ y dc/ estan
                 vacios (0 entradas cada uno).

  Y ESO ES EL HUECO REAL, y es de MODULO, no de cabecera:

     amdkfd            68 entradas   PRESENTE
     ras/ras_mgr       17 entradas   PRESENTE
     display            7 entradas   PRESENTE
     pm/inc             3 entradas   PRESENTE
     smu/               0 entradas   VACIO
     dc/                0 entradas   VACIO

  EL CORPUS ESTA RECORTADO POR MODULO.  Y ESTOS DOS MODULOS SON JUSTO LOS
  DOS QUE SON "GESTION" (reloj/potencia y display), no "datos".

  QUE ES EXACTAMENTE LO QUE VENI DICIENDO DESDE QUE PREGUNTASTE CUANTO SABIA:
  que de los 9 bloques, los que se RENDIMIENTO y GESTION son los que no
  tengo, y los de RUTA DE DATOS estan casi todos.
```

## 4 · LO QUE ESO CIERRA, Y LO QUE ABRE

```text
  CIERRA, con correccion:
    1471  use gmc/gmc_8_1_d.h.  EXISTE, en include/asic_reg/gmc/.  Mi ruta
          era inventada, pero la cabecera existe y el contenido que leí de
          gfx_v8_0.c sigue siendo correcto.  La AFIRMACION de 1471 (que el GMC
          aplicable es 8_1 y el 8_2 esta por una rama de APU) NO se toca:  sale
          de gfx_v8_0.c:41, que si esta en el corpus.

    1479  "falta include/drm/".  HAY QUE RE-MEDIRLO con las rutas, y no lo he
          hecho.  include/drm/ esta en el arbol del kernel, no en
          drivers/gpu/drm/amd, asi que mi ruta anterior (amd/) no podia
          encontrarlo.  Y eso es un fallo de ruta, igual que este.
          NOT_DETERMINED hasta que lo mida.

    1480  "5 de 1000 con include no resuelto".  RE-MEDIDO:  son 8 de 2648, y
          ninguno en la ruta de POLARIS12.  La CONCLUSION de 1480 ("ninguno
          en la ruta de la RX550") SE CONFIRMA con la medicion correcta, y la
          CIFRA era mala.  Un hallazgo con la conclusion buena y la cifra mala.

    1531  "94 .c no compilan" / "NO COMPILABLE".  REFUTADO.  Son 8 includes en
          3 ficheros, dos de ellos de otros ASICs.

    1550  mi propia correccion de 1531 era incompleta:  decia que faltaban
          cabeceras de subdirectorio.  FALSO.  Los subdirectorios estan
          completos (asic_reg con bif, oss, gmc, gc...).  Lo que falta son dos
          MODULOS.

  Y LA CORRECCION A MI MISMO SOBRE gc_8_0_d.h, que dije que "no esta en
  ninguna parte del corpus":
      gc/ SI existe, en include/asic_reg/.  Lo que no esta es gc_8_0_d.h
      dentro de gc/.  Un subdirectorio con 0 ficheros utiles.
      CORREGIDO aqui.
```

## 5 · ESTADO

```text
PROVEN          con las 12 rutas del Makefile, el driver resuelve 2640 de 2648
                includes (99,70 %).  Los 8 que faltan son 3 cabeceras en 3
                ficheros.
PROVEN          2 de esos 3 ficheros (cik.c, si.c) son de otros ASICs:  0
                apariciones de CHIP_POLARIS12.  Impacto cero en mi tarjeta.
PROVEN_ABSENT  pp_smu_ip_block y dm_ip_block no se definen en ninguna parte
                del corpus, y smu/ y dc/ tienen 0 entradas.  Con inventario
                cerrado.
PROVEN          el corpus esta recortado por MODULO, no por cabecera:
                amdkfd 68, ras_mgr 17, display 7, pm/inc 3, smu 0, dc 0.

REFUTADO, mio  1531 §5, entero.  "94 .c no compilan" -> 8 includes en 3
               ficheros.  Y "sano para leer pero NO COMPILABLE" -> la segunda
               mitad es falsa.
REFUTADO, mio  1531 §5 y mi numero:  los subdirectorios ASIC (bif, oss, gmc,
               gc, dce, smu...) SI estan en include/asic_reg/.  No faltaban.
CORRIGE, mio   1550 decia que gc_8_0_d.h "no esta en ninguna parte".  El
               subdirectorio gc SI esta; lo que falta es ese fichero dentro.
CORRIGE, mio   1550 §7 decia "un hueco real confirmado: gc_8_0_d.h".  El hueco
               real es otro, y es mayor:  pp_smu y dm, dos modulos enteros.
CONFIRMA        1480 en su CONCLUSION (ningun include sin resolver en la ruta
                de POLARIS12), y corrige su CIFRA (5 de 1000 -> 8 de 2648).

NOT_DETERMINED  1479:  si falta include/drm/ con la ruta correcta.  No lo he
                re-medido.  Es el siguiente.
```

## 6 · LO QUE SIGUE, Y ES LO QUE NO PUEDO SEGUIR HACIENDO

```text
  1. 1479:  re-medir include/drm/ con las rutas.  Es lo que prometi en 1550 y
     es lo unico que queda de la lista de tres.

  2. Y DESPUES, EL HALLAZGO DE ESTE HALLAZGO:  el corpus no tiene los modulos
     de GESTION.  No es un defecto del corpus, es un recorte.  Y tiene una
     consecuencia que hay que escribir:

     PP_SMU ES EL QUE MANDA LOS RELOJES.  Sin el, no puedo responder por que
     SCLK esta en 997 MHz (1541) ni si es el optimo.  Y sin DM no puedo
     responder por el display, pero eso es la frontera dura y no me toca.

     ASI QUE DE LOS 9 BLOQUES:  5 de datos (leidos), 1 de reloj (ausente),
     1 de display (ausente y vetado), 2 mas.
```

Y aquí tengo que ser honesto sobre el método, porque es la décima vez:

```text
  ERROR, mio  la DECIMA VEZ con "no mire la ruta".  Y esta revela el patron
              completo:

              1500  caja de un digito      -> no mire TODA la salida
              1502  atribui linea al grep  -> no mire CUAL de dos
              1506  igual que 1502
              1508  | head                 -> no mire lo que truncaba
              1516  ciclo parcial          -> VI un patron y preferi verlo
              1518  redondeo               -> no mire la forma que preveia
              1523  "el ultimo"            -> no mire el orden de archivo
              1531  .c -> .h               -> no mire el sentido inverso
              1534  IH en debugfs          -> no mire la TABLA
              1550  raiz de include        -> no mire el Makefile
              1554  raiz de include, otra vez

              Y HAY UN SOLO ORIGEN EN LAS DIEZ:  construi el instrumento en
              lugar de leer la fuente que lo define.

              Y LA REGLA, que es la misma que la de 1514 pero aplicada al
              instrumento:

              ANTES DE MEDIR CON UN INSTRUMENTO, LEER LA FUENTE QUE DICE COMO
              SE USA.  Un Makefile, una tabla, un enum, una cabecera incluida.

              Y ESO ES BARATO.  El Makefile eran 12 lineas.  Lo leí 30
              hallazgos tarde.
```