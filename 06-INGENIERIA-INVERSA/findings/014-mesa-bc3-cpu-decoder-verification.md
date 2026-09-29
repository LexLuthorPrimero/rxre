# 014 — Verificación de Q-3: ¿existe un descompresor BC3 en CPU en el Mesa instalado?

**Fecha**: 2026-09-29 · **Ámbito**: `06-INGENIERIA-INVERSA/` · **Host**: `HOST-C` (vivo)
**Pregunta asignada**: IA-1, desde el commit `1e28733`
**Respuesta**: `CONFIRMADO`, con dos correcciones al comando que me dieron, una
de las cuales lo invalidaba como prueba.

---

## Por qué esta pregunta y no otra

La hipótesis de P-9 era «¿cómo demuestro que el shader corrió en hardware y no
en software?». El reframe del commit `1e28733` la convirtió en su refutación:
si el resultado pudiese reproducirse en CPU, entonces no prueba hardware.

Para que esa refutación tenga fuerza hace falta un hecho previo: **que el camino
de software no exista, o que si existe sea distinguible**. La premisa que IA-3
leyó en `/home/lucas/mesa` es que radeonsi y RADV no tienen descompresor BC3 en
CPU. Este documento comprueba esa premisa contra **los binarios que se ejecutan
en este host**, no contra el árbol de fuente.

La distinción importa y es la que `AGENTS.md` marca como error recurrente: el
árbol que alguien leyó y el binario que corre son objetos distintos, y pueden
diferir.

---

## Dos objetos, dos versiones

| Objeto | Identidad |
|---|---|
| Árbol leído por IA-3 | `/home/lucas/mesa`, `26.1-branchpoint-1415-gc5e413533f4` |
| Driver instalado | `mesa-dri-drivers-26.2.3-1.fc44.x86_64`, `mesa-vulkan-drivers-freeworld-26.2.3-1.fc44.x86_64` |

Versiones distintas (`26.1-branchpoint` vs `26.2.3`). La conclusión puede
coincidir; no se puede suponer que coincida.

---

## Corrección 1 — el fichero que se debe mirar es `radeonsi_dri.so`, y es un symlink

El comando que me asignaron era:

```bash
nm -D /usr/lib64/dri/radeon_dri.so | grep -i "dxt5\|s3tc"
```

```
$ ls -la /usr/lib64/dri/radeon_dri.so
ls: no se puede acceder a '/usr/lib64/dri/radeon_dri.so': No existe el fichero o el directorio
```

**`radeon_dri.so` no existe.** El nombre correcto es `radeonsi_dri.so`, y además
es un symlink:

```
$ ls -la /usr/lib64/dri/radeonsi_dri.so
lrwxrwxrwx 1 root root 14 sep 16 21:00 /usr/lib64/dri/radeonsi_dri.so -> libdril_dri.so
```

Esto es `AGENTS.md` §«Verificar el objeto antes de afirmar su ausencia», en su
forma más automática: el comando devolvió 0 líneas y `grep -c` sobre un
fichero inexistente también devuelve 0. **Un `grep -c` que da 0 porque el
fichero no existe y uno que da 0 porque el símbolo no existe son el mismo
número y significan cosas opuestas.** Ejecutado tal cual, el comando "confirma"
cualquier cosa.

## Corrección 2 — los símbolos se buscaban solo entre los dinámicos

`nm -D` lista la interfaz exportada. Una función de decodificación interna de
Mesa es `static` y no aparece ahí. Repetido con todos los símbolos:

```bash
$ nm -a /usr/lib64/dri/libdril_dri.so | grep -ci "dxt5\|s3tc"
0
$ objdump -t /usr/lib64/dri/libdril_dri.so | grep -i "dxtn_fetch\|dxt5_rgba_fetch"
(sin salida)
```

---

## Resultado sobre los binarios reales

| Binario | Símbolos `dxt5`/`s3tc` | Cadenas `dxt5`/`s3tc` |
|---|---|---|
| `/usr/lib64/dri/libdril_dri.so` (= `radeonsi_dri.so`) | **0** | 4 |
| `/usr/lib64/libvulkan_radeon.so` | **0** | 4 |

Las cuatro cadenas, idénticas en ambos:

```
PIPE_FORMAT_DXT5_RGBA
dxt5_rgba
PIPE_FORMAT_DXT5_SRGBA
dxt5_srgba
```

**Qué son esas cuatro cadenas.** Son *nombres de entrada de una tabla de
formatos*, no código. En el árbol:

```
src/util/format/u_format_s3tc.c:36
util_format_dxtn_fetch_t util_format_dxt5_rgba_fetch = (util_format_dxtn_fetch_t)fetch_2d_texel_rgba_dxt5;
```

Y ninguna de las dos formas de ese símbolo existe en el binario compilado:
`nm -a` y `objdump -t` no las encuentran. Una cadena que sobrevive a la
compilación y un símbolo que no, es la firma de una tabla que nombra formatos
que *el driver no puede usar*, no de un descompresor presente.

## Por qué radeonsi no puede caer en software

Tres comprobaciones independientes sobre el árbol:

```bash
$ grep -rn "dxt5_rgba\|dxt5_srgba\|u_format_s3tc" src/gallium/drivers/radeonsi/ | wc -l
0
$ grep -rn "dxt5_rgba\|dxt5_srgba\|u_format_s3tc" src/amd/vulkan/ | wc -l
0
$ grep -rn "util_format_dxtn_fetch\|util_format_dxt5" src/gallium/drivers/radeonsi/
(sin salida)
```

Los símbolos de decodificación DXTT viven en `src/util/format/u_format_s3tc.c`
y en `src/mesa/main/texcompress_s3tc.c`. **Ni radeonsi ni RADV los referencia.**
El único consumidor de `util_format_dxt5_rgba_fetch` fuera de su propio módulo
es llvmpipe.

Consecuencia: un contexto creado sobre radeonsi no tiene un descompresor BC3 en
CPU al que recurrir. La hipótesis «decodifica por software dentro del mismo
driver» queda **cerrada por diseño**, no por casualidad.

---

## Lo que esto NO establece

- **No dice nada de llvmpipe.** llvmpipe sí tiene descompresor BC3. Que
  radeonsi no lo tenga no dice nada del rasterizador de software, que es la vía
  por la que un resultado *podría* reproducirse en CPU. Eso es el otro lado de
  P-9 y lo trata el commit `1e28733` con los pares donde llvmpipe no coincide
  ni con la especificación ni con el truncamiento.
- **No verifica que el binario instalado y el árbol leído sean el mismo
  commit.** Son 26.1-branchpoint y 26.2.3. La conclusión es consistente en
  ambos, pero no se ha identificado el commit exacto del binario.
- **No es una medición de ejecución.** Es inspección de binario y de código
  fuente. Establece qué camino *existe*; no que se haya tomado.
- **`grep -c` sobre rutas inexistentes.** Reiterado arriba porque las dos
  correcciones de este documento nacen de él.

## Falsificación

Esta clasificación se refutaría con:

1. `nm -a` o `objdump -t` sobre `libdril_dri.so` mostrando un símbolo de decodificación
   DXTT. No aparece.
2. `dtrace`/`perf` durante el dispatch de la rampa alfa mostrando ejecución en
   espacio de usuario de una función de decode. **No medido** — es el siguiente
   paso, y es lo que distinguiría «no existe» de «existe pero no se usa».
3. Un paquete Mesa instalado de una versión cuyo árbol sí referencie el
   descompresor desde radeonsi. Habría que revisar la serie 26.3+.

## Procedencia

- Árbol: `/home/lucas/mesa`, `git describe` → `26.1-branchpoint-1415-gc5e413533f4`
- Paquetes: `rpm -q mesa-dri-drivers mesa-vulkan-drivers-freeworld` → `26.2.3-1.fc44.x86_64`
- Binarios: `/usr/lib64/dri/libdril_dri.so`, `/usr/lib64/libvulkan_radeon.so`
- Pregunta originada en: commit `1e28733` «F4-R9: P-9 resuelto»
