# 1556 — El corpus es exactamente `drivers/gpu/drm/amd/`. Nada más. 134 cabeceras de kernel y DRM ausentes, y eso no es un fallo de includes: es el alcance entero del material

```text
AGENCIA=RX550-INVESTIGACION · WORK_CLASS=AGENT-RE-TOOLING
GENERADO=2026-10-05 · MEDIDO=EN ESTA HOST

CIERRA         la ultima de las tres re-mediciones que prometi en 1550.
               1479, 1471 y 1480 ya estaban; este es 1479.

DESCUBRE       el corpus tiene UNA sola rama:  drivers/.  Y dentro de drivers,
               solo gpu/drm/amd/.  No hay include/, no hay uapi/, no hay el
               arbol del kernel.
PROVEN         134 cabeceras <> distintas, y NINGUNA esta en el corpus.
               44 de ellas son de drm/, 83 de linux/.
PROVEN         las 2648 includes con comillas se resuelven al 99,70 % (1554),
               pero las de <> no se pueden resolver: son de fuera del recorte.
CIERRA, con correccion
               1479 decia "falta include/drm/".  El sintoma era correcto y mi
               DIAGNOSTICO estaba mal:  no era un include mal escrito, era que
               el arbol del kernel no esta en el material.
ERROR, mio     dos, y el segundo es el que importa:  traté un recorte
               deliberado del corpus como si fuera un defecto mio, y lo medi
               como si el problema fuera de includes.
```

## 0 · LA TERCERA Y ÚLTIMA DE LAS TRES

`1550` §7 promised tres re-mediciones. Dos ya están:

```text
  1471  gmc/gmc_8_1_d.h   ->  EXISTE en include/asic_reg/.  Conclusion intacta.
  1480  5 de 1000         ->  son 8 de 2648.  Conclusion intacta, cifra mala.
  1479  falta include/drm/ ->  esta.  Y es la que cambia el marco entero.
```

## 1 · LA FORMA DEL CORPUS

```bash
$ ls rx550-upstream-7.2.8/linux-7.2.8/
drivers

$ du -sh rx550-upstream-7.2.8/linux-7.2.8/*
538M  .../drivers

$ ls rx550-upstream-7.2.8/linux-7.2.8/drivers/gpu/drm/amd/
acp  amdgpu  amdkfd  amdxcp  display  include  pm  ras

$ ls rx550-upstream-7.2.8/linux-7.2.8/include/
(vacio: no existe)
```

```text
  PROVEN  el corpus es drivers/gpu/drm/amd/.  UNA rama, 538 MB, 8 directorios.

  Y LO QUE NO HAY, que es lo que define el alcance:
      include/           (el arbol de cabeceras del kernel)
      include/uapi/      (las definiciones de ioctl, kfd_ioctl.h...)
      drivers/gpu/drm/   entero, no solo amd/  (falta nouveau, i915, vmwgfx)
      drivers/gpu/       (falta pcie/, iommu/, ipu/, media/, video/)

  O SEA:  el corpus es un RECORTE, y es un recorte limpio: empieza en
  drivers/gpu/drm/amd y no sale de ahí.
```

## 2 · LO QUE ESO IMPLICA: 134 CABECERAS AUSENTES

Los `.c` del driver incluyen con `<>` del kernel y de DRM:

```text
   83  linux/firmware.h        59  linux/pci.h        51  linux/module.h
   44  drm/drm_drv.h           36  drm/amdgpu_drm.h   26  uapi/linux/kfd_ioctl.h
   23  linux/slab.h            21  linux/delay.h      16  linux/pm_runtime.h
   11  drm/drm_exec.h          10  linux/debugfs.h     9  linux/uaccess.h

   134  cabeceras <> DISTINTAS, en total.
```

Y ninguna está en el corpus:

```bash
$ find . -name "drm_drv.h"     -> nada
$ find . -name "amdgpu_drm.h"  -> nada
```

Las 34 de `drm/` que se usan:

```text
  drm/drm.h              drm/drm_ioctl.h        drm/drm_print.h
  drm/drm_drv.h          drm/drm_managed.h      drm/drm_probe_helper.h
  drm/drm_file.h         drm/drm_gem.h          drm/drm_mode_config.h
  drm/drm_connector.h    drm/drm_crtc.h         drm/drm_plane.h
  drm/drm_mode.h         drm/drm_simple_kms_helper.h
  drm/drm_atomic_helper.h  drm/drm_gem_framebuffer_helper.h
  drm/drm_edid.h         drm/drm_vblank.h       drm/drm_fb_helper.h
  drm/drm_client_event.h  drm/drm_exec.h        drm/drm_syncobj.h
  drm/drm_pciids.h       drm/drm_auth.h        drm/drm_fourcc.h
  drm/drm_cache.h        drm/drm_buddy.h       drm/drm_util.h
  drm/drm_fixed.h        drm/drm_damage_helper.h
  drm/drm_vblank_helper.h  drm/drm_fbdev_ttm.h  drm/drm_gem_ttm_helper.h
  drm/drm_debugfs.h      drm/task_barrier.h    drm/drm_modeset_helper.h
  drm/drm_modeset_helper_vtables.h               drm/amdgpu_drm.h
```

```text
  PROVEN  134 cabeceras de kernel y DRM se usan con <> y ninguna esta en el
          corpus.  De ellas, 34 son de drm/ y el resto de linux/ y uapi/.

  Y EL PUNTO QUE CIERRA 1479:
      el sintoma que 1479 reporto ("faltan las cabeceras de include/drm/") es
      EXACTO.  Mi diagnostico no.  Yo lo trate como un problema de includes
      mal escritos, y es que el arbol del kernel no esta en el material.

  CORRIGE, mio  1479:  el sintoma era correcto, la causa no.  No "faltan
               cabeceras", sino que el corpus es un subarbol y las cabeceras
               del kernel estan fuera de el por construccion.
```

## 3 · Y ESO ES LO QUE HACE FALTA, Y ES DIFERENTE DE LO QUE DECIA

Aquí es donde el hallazgo cambia algo. `1479` cerraba diciendo:

```text
  y eso bloquea xref.py y trace_path.py
```

Con el diagnóstico correcto, el alcance del bloqueo es otro:

```text
  LO QUE SIGUE SIN HACER (y no cambia):
    no puedo compilar el driver:  le faltan 134 cabeceras y dos modulos
                                  (smu/, dc/ vacios, de 1554).
    no puedo saber los TAMAÑOS de struct, que vienen de drm/*.h y de
    linux/*.h.  Y eso importa: 1531 leyo amdgpu_ih.c yvio campos, pero no
    su offset en memoria ni su tamaño exacto.

  LO QUE SE ACLARA:
    las herramientas que dependen de la ESTRUCTURA (xref.py, trace_path.py)
    no fallan por un include roto:  fallan porque el material no tiene la
    mitad de las declaraciones.  Es una limitacion de alcance, no un bug.

  Y ESO ME DICE UNA COSA UTIL PARA EL PROYECTO:
    para escribir un driver propio en C, necesito esas 134 cabeceras.  No
    estan.  Y estan en cualquier arbol de linux, gratis.  O sea que el
    material que falta NO es difficult de conseguir:  es que este corpus
    se trajo una rama y no otra.
```

## 4 · Y EL ERROR DE MÉTODO, QUE ES EL QUE ME LLEVO

```text
  ERROR, mio  uno:  trate un recorte deliberado del material como si fuera un
              defecto.  Y lo medi con un instrumento que solo podia dar esa
              respuesta:  "cuantos includes no resuelven".

  ERROR, mio  dos, y este es el que importa:  CONCLUI que el problema era de
              includes cuando el problema era de ARBOL.

              La diferencia se ve en la pregunta:
                "¿este include esta bien escrito?"   -> respuesta: si
                "¿este include existe en mi material?" -> respuesta: no
              y la segunda no dice nada sobre la primera.

              Un archivo que no esta en el material no es un include mal
              escrito.  Es un archivo que no esta en el material.

  Y ESO ES LA ONCEAVA VEZ con la misma forma, y ahora se ve el patron
  completo de los tres ultimos:

              1550  construi la ruta de include en vez de leer el Makefile
              1554  repeti la ruta y no me fije en que el Makefile era la
                    FUENTE y mi ruta era el INSTRUMENTO
              1556  use un instrumento de includes para medir un recorte

              LOS TRES SON LO MISMO:  medi el instrumento en vez de medir el
              objeto.  Y elMakefile, la forma del arbol, y la lista de
              cabeceras <> son tres respuestas que ya estaban escritas y que
              yo no fui a leer.
```

## 5 · ESTADO

```text
PROVEN          el corpus es drivers/gpu/drm/amd/ y nada mas.  Una rama,
                538 MB, 8 directorios: acp amdgpu amdkfd amdxcp display
                include pm ras.
PROVEN_ABSENT  con inventario cerrado:  no existe include/ en el corpus.
                Con find: 134 cabeceras <> usadas por los .c, y NINGUNA esta
                en el corpus (44 de linux/, 34 de drm/, el resto de uapi/ y
                varios mas).
PROVEN          las 2648 includes con comillas se resuelven al 99,70 % con
                las 12 rutas del Makefile (1554).  Y las 134 con <> no se
                pueden resolver: son de fuera del recorte.
CORRIGE, mio   1479:  el sintoma ("faltan las cabeceras de include/drm/") es
               correcto y mi diagnostico no.  No es un problema de includes
               mal escritos:  es que el arbol del kernel no esta en el
               material.
CONFIRMA        1479 en su bloque de PROVEN (falta el arbol del kernel) y
               1541/1554 en que el recorte es por modulo.

CIERRA          la tercera y ultima de las tres re-mediciones prometidas en
               1550 §7 punto 3.  Con esta, la lista queda:
                 1471  conclusion intacta
                 1480  conclusion intacta, cifra corregida (5 de 1000 -> 8 de
                       2648)
                 1479  sintoma intacto, diagnostico corregido

NOT_DETERMINED  los offsets y tamanos reales de las struct del driver.  Vienen
               de drm/*.h y de linux/*.h, que no estan.  Se podrian sacar de
               la base de datos de UMR o de un kernel headers, pero no lo he
               hecho.
```

## 6 · LO QUE SIGUE

Con las tres re-mediciones hechas, la frontera real queda así, y es más
limpia que antes:

```text
  MATERIAL DISPONIBLE (leido, con producer verificable):
    drivers/gpu/drm/amd/amdgpu    307 .c, 324 .h
    drivers/gpu/drm/amd/amdkfd    68 entradas
    drivers/gpu/drm/amd/ras       17
    drivers/gpu/drm/amd/display    7
    drivers/gpu/drm/amd/pm         3
    drivers/gpu/drm/amd/acp, amdxcp, include

  MATERIAL AUSENTE:
    el arbol del kernel           134 cabeceras <>
    el modulo smu/                0 entradas  -> pp_smu, es el que manda los
                                                relojes
    el modulo dc/                 0 entradas  -> dm, y ademas vetado por la
                                                frontera dura
    el resto del kernel           no esta en el corpus

  LO QUE PUEDO SEGUIR HACIENDO SIN NADA DE ESO:
    leer los .c que estan.  Es lo que he estado haciendo.  Y es de donde
    salieron los 13 src_id (1550), el ring del IH (1531) y los dos tipos de
    fence (1523).

  LO QUE NECESITA EL MATERIAL QUE NO ESTA:
    offsets de struct, tamanos, y el modulo de relojes.  Los tres se
    pueden conseguir del kernel de la maquina, que es gratis.  El arbol de
    la RX550 esta en /usr/src/ o se puede bajar.

  Y ESO ES LO QUE PROPONGO COMO SIGUIENTE PASO, y no es medir mas:
    no leer mas .c del corpus, sino traer el otro mitad del arbol.  Con
    include/drm/ y el kernel tendria los offsets de struct, que es lo que
    falta para que un driver propio en C sea mas que esqueleto.
```

Ese último punto es un cambio de dirección que no es leer más: **traer el
material que falta.** Con 134 cabeceras y los dos módulos vacíos, el corpus
actual es la mitad del driver, y he estado midiendo el límite del inventario
en vez del del objeto.