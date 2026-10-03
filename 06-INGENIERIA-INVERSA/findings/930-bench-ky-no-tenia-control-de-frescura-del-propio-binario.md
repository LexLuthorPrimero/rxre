# 930 — `bench.py` no tenía control de frescura del propio binario: la suite midió un programa que no era el que había escrito

Estado: `PROVEN`. Corrige una afirmación de `928` y añade un control que faltaba.
Alcance: la RX 550 de esta placa, RADV, Mesa de este equipo.
AUTORIA=AGENTE-SMU
Instrumentos: `bench.py` 15 de 15, `vulkan_compute_probe.c` con `--tex`.

## El fallo, y por qué casi no se ve

Se añadió la bandera `--tex` al banco y se compiló a mano para probarla.
`bench.py` siguió usando el binario `vcp` del directorio, que era de las 03:38, anterior al
parche. La suite `textura` corrió, dio `INVALID`, y su artefacto era perfectly well formed: con
hash de instrumento, con estado del hardware, con marcas de tiempo.

La única señal era un número: **la ventana medida por el runner daba 4 KiB, y las corridas
directas daban 64 KiB.** Si no se hubiera contrastado con una corrida directa, el artefacto habría
sido creible, y la nota que citara ese artefacto habria dado por buena una capacidad que el
instrumento no tiene. Ese es el fallo de este tipo que mas cuesta: no se manifiesta
como un error, sino como un resultado con todos sus sellos.

La causa es una omisión, no un error. `bench.py` tiene `frescura_spv()`, que compara cada `.spv` con
su `.comp` y se niega a consumir un artefacto obsoleto — añadida después de tres incidentes en los que
un shader roto no recompiló y el banco consumió el `.spv` viejo y dio `PASS`. El mismo control para
el binario no existía. El banco declara en su propio módulo que no construye nada, o sea que el
binario es un artefacto externo, y un artefacto externo que se consume necesita el mismo control que
un `.spv`.

**Un control de frescura que cubre la mitad de los artefactos deja la otra mitad con el mismo
defecto que motivó añadirlo.** Y el que no cubre es el que contiene la lógica de todo lo demás.

## El control

`frescura_binario()` en `bench.py`: compara el `mtime` de `vcp` con el de `vulkan_compute_probe.c`,
y guarda los dos `sha256` para que un artefacto pueda invalidarse después. Dos usos:

- `instrumento()` lo incluye en cada artefacto, junto al estado, así que una corrida queda
  invalidable después aunque el binario cambie.
- `main()` **se niega a medir** y devuelve `3` si el binario está obsoleto, en vez de medir y
  rotular después.

El self-test comprueba el control **en los dos sentidos**, que es lo que lo convierte en control y
no en un aviso:

```
frescura del binario dice AL DIA con el binario construido   OK  estado=AL DIA
frescura del binario detecta OBSOLETO                         OK  estado=OBSOLETO
frescura del binario vuelve a AL DIA tras restaurar           OK  fuente restaurada
```

Y de extremo a extremo: tocar la fuente da `INSTRUMENTO OBSOLETO: la fuente es mas nueva que el
binario` y `exit=3`, sin llegar a medir.

## Corrección a `928`

`928` decía que había que cablear `texdump.spv` como control previo porque «el runner no puede
distinguir una ruta de texel válida de una imagen vacía». **Eso era falso.** El control de contenido
de la cadena ya cubre ese caso: con la imagen vacía, `v = 0`, la cadena produce un `acc` distinto del
que produce el modelo del host, y `medir()` rechaza la muestra porque exige `rc == 0` y el control de
contenido. La suite se ejecutó con las dos ramas en `PASS` sobre muestras que pasaron ese control.

Lo que `texdump` aporta no es seguridad sino **localización**: distingue «la imagen no contiene lo
que debe» de «la cadena está mal». Eso sigue siendo útil, y por eso la suite lo usa, pero la
justificación que escribí estaba inflada.

La lección sobre la propia afirmación es más útil que la corrección: escribí una afirmación sobre lo
que un instrumento *no puede* hacer sin comprobar si ese instrumento lo hacía ya. El control que
exigí para el camino de lectura ya existía en el camino de escritura.

## El resultado de `282-1`, ahora con el binario correcto

`bench.py run textura`, con la ventana medida por el propio runner antes del par:

| imagen | `rowPitch` | lectura de la imagen |
|---|---|---|
| 1 KiB | 1024 | OK |
| 4 KiB | 4096 | OK |
| 16 KiB | 16384 | OK |
| 64 KiB | 65536 | OK |
| 256 KiB | 0 | FALLA |
| 1 MiB | 0 | FALLA |
| 4 MiB | 0 | FALLA |
| 16 MiB | 0 | FALLA |

`kib_maximo_util = 64`. El límite aparece por partida doble, en el banco y en el runner, y
`rowPitch == 0` coincide exactamente con el punto donde el contenido deja de cuadrar. Sobre esto la
nota `928` se equivocó al decir que `rowPitch == 0` era un campo sin rellenar: la correlación es
exacta, y es un síntoma del mismo fallo. El portón original decía algo real; lo que no decía era por
qué.

El par, dentro de la ventana, con el control de contenido activo en las dos ramas:

```
storage buffer (binding 0)   mediana=0,000129 s   2,0321 GB/s   1,9684 ns por acceso   PASS
imagen r32ui    (binding 1)  mediana=0,000212 s   1,2365 GB/s   3,2349 ns por acceso   PASS
```

**No se reporta ningún resultado.** El veredicto de la suite dice la razón: *«no comparable: el
conjunto de trabajo son 64 KiB y la L3 de esta CPU es de 8 MiB, así que los dos tiempos son de caché
y la magnitud no es la que 282 pregunta»*.

Ese es el punto donde esta nota se diferencia de un banco que mide y publica. `282` se equivoco una vez publicando un número de muestra única; la respuesta del banco ahora es negarse a
publicar, y el motivo es el que importa: **el instrumento no falla, el instrumento se niega.** Y hay
una diferencia real entre «separación insuficiente» y «no comparable»: el ruido supera la
diferencia es un resultado; el conjunto de trabajo estar en caché es un límite de la técnica.

## Dos niveles de veredicto

La suite `textura` no devuelve un único veredicto, y esa es la decisión de diseño de esta iteración:

```
INVALID + "separacion insuficiente: el ruido no es menor que la diferencia"
INVALID + "no comparable: el conjunto de trabajo cabe en la L3"
PASS    + la diferencia separa Y el conjunto de trabajo sale de caché
```

Colapsarlos en un `INVALID` a secas habría perdido la distinción entre *esta corrida no produce
resultado* y *esta técnica no puede producirlo en esta placa*. Lo primero se arregla repitiendo; lo
segundo se arregla cambiando de técnica. Son decisiones distintas y una sola palabra las mezcla.

## Instrumentos

- `bench.py`: suite `textura`, `frescura_binario()`, puerta de ejecución con `exit=3`, y tres casos
  de self-test. Self-test 15 de 15. `instrumento()` ahora registra `binario_fresco`.
- `vulkan_compute_probe.c`: `--tex`. Sin la bandera nada cambia, y el caso conocido `chain.spv` sigue
  dando 256 de 256.
- `texchain.comp`, `texdump.comp`, `texconst.comp`.
- `bench.py` compila el banco con `freshness` de `.spv`, pero **no** de sí mismo. Corregido.

## Errores propios de esta iteración

Cinco, y cuatro son instrumentales:

1. **La bandera `--tex` quedó después de un `continue`.** Código muerto. Es el mismo defecto que se
   llevó por delante la línea del despacho en `607`.
2. **Moví la escritura de `binding 0` dentro del `else` de `--tex`.** Con la bandera encendida el
   storage buffer se quedaba sin descriptor. Ninguna llamada de Vulkan falló: el conjunto se asignó,
   la llamada devolvió éxito, y el resultado fue un buffer de ceros.
3. **Al sustituir el portón borré la creación de la `imageView`**, que estaba entre el portón y el
   `printf`. Con la vista nula el descriptor no apunta a nada y el despacho no produce nada.
4. **Un barrido con `items=1024` y `wsize=256`** viola el invariante `wsize >= items`. El banco lo
   rechazó correctamente y yo leí ese rechazo como un fallo de la ruta de texel. Después, un script
   con `subprocess` no produjo salida y declaró «el pórtico pasa» donde la corrida directa abortaba.
   **Cuando un script y una corrida directa no coinciden, la corrida directa gana.**
5. **`bench.py` sin control de frescura del binario.** El de esta nota.

En los tres primeros, **ninguna llamada de Vulkan falló y ninguna Instrumento se quejó**. Lo que
faltaba era una cosa presente en el camino, y su ausencia se manifestó como un número medible pero
equivocado. Un banco que comprueba que las llamadas devuelven éxito no ha comprobado nada sobre lo
que midió. El de la nota cinco es el peor de los cinco por una razón distinta: el banco no tenía
ningún control sobre el programa que estaba ejecutando, y su artefacto era indistinguible de uno
correcto.

## Lo que queda abierto

- **`282-1` sigue abierta**, y no por falta de instrumento. La ruta de texel está validada,
  caracterizada y comparada; lo que falta es una técnica que llegue más allá de 64 KiB. Dos vías, y
  las dos con coste: una imagen teselada (`VK_IMAGE_TILING_OPTIMAL`) con copia de host a teselas,
  cuyo coste hay que medir aparte para no contaminar la comparación; o un banco en Metal/RADV fuera
  de Vulkan. La segunda es más limpia porque quita la copia de.host de en medio.
- ~~**`282-2`**~~ **RANCIOSO**: cerrado en `283`, que partió el buffer en dos regiones
  disjuntas y pasó el control de 0/40 a 40/40. Lo arrastré aquí cinco notas después del
  cierre. El detector es `fronteras.py`, y las tres menciones rancias que quedaban en
  928, 930, 933, 934 y 938 estaban todas escritas por mí.
- **`606-2`**: repetir el discriminante de `282` con `--mem=1` vivo, que ya no está muerto desde
  `606`.
