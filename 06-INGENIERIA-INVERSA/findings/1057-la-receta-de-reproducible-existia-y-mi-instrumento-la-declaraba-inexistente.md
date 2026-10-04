# 1057 — la receta de `reproducible` existía, y mi propio instrumento la declaraba inexistente

```text
AGENCIA=RX550-INVESTIGACION · WORK_CLASS=AGENT-MAIN-VALIDITY
GENERADO=2026-10-04 · MEDIDO=EN ESTA HOST
AFECTADO=tools/sello_prov.py (nuevo, 1.0.0) · este documento
         08-ARQUITECTURA/artifacts/R1-RIESGO/HALLAZGOS.md:15
         08-ARQUITECTURA/artifacts/R2-PM4OPS/HALLAZGOS.md:15
         08-ARQUITECTURA/artifacts/R3-DWARFX/HALLAZGOS.md:15
         06-INGENIERIA-INVERSA/findings/977-...md:318 y :322  <- el hallazgo real
ESTADO=PROBADO · REFUTADO-MI-CLAIM · 41 vectores PASS · 11 mutaciones detectadas
herramienta   tools/sello_prov.py 1.0.0
sha256        7d2bcc1f3f76fc23
```

## 0 · Lo primero, porque es lo que da valor a lo demás

**Escribí una afirmación, la defendí, y era falsa. Un adversario la tumbó en menos
de lo que tardé en escribirla.** Lo escribo entero porque el error es instructive y
porque el proyecto ya tieneenough registros de herramientas que certifican cosas
que no han medido; este va en esa serie con nombre y apellidos.

La afirmación era:

> `reproducible <sha256>` no tiene receta. No la hay porque nadie la escribió, y no se
> deduce de nada del árbol. MEDIDO: el valor declarado no coincide con el sha256 del
> artefacto, ni con el de la salida `--json`, ni con el del selftest, ni con ninguna
> de las cinco normalizaciones razonables del JSON.

**La receta es esta, y está en los tres nodos:**

```python
sha256( json.dumps( json_del_artefacto_sin_la_clave_"generado" , sort_keys=True ) )
```

con los **separadores por defecto** de Python (`", "` y `": "`), UTF-8, sin salto de
línea final. MEDIDO **3 de 3**: R1, R2 y R3.

| nodo | declarado | obtenido con la receta |
|---|---|---|
| R1-RIESGO | `bccfae31267d843c27f1…` | `bccfae31267d843c27f1…` |
| R2-PM4OPS | `c3e6c14b8597fe21221…` | `c3e6c14b8597fe21221…` |
| R3-DWARFX | `a00e8a4a839b575b7f8…` | `a00e8a4a839b575b7f8…` |

## 1 · POR QUÉ LA PERDI, Y POR QUÉ ESO ES LO INTERESANTE

No la perdí por no haber buscado. La busqué con cinco normalizaciones y la dejé
fuera. Las cinco que probé:

| # | normalización | ¿reproduce? |
|---|---|---|
| 1 | tal cual, `sort_keys`, separadores por defecto | no |
| 2 | tal cual, sin ordenar | no |
| 3 | **sin `generado`, `sort_keys`, separadores por defecto** | **SÍ** |
| 4 | sin `generado`, sin ordenar | no |
| 5 | `generado` reemplazado por `""` | no |

Lo que prueba la fila 3 es que **`generado` hay que quitarlo**, no reemplazarlo. Y lo
que me hizo fallar es que las dos formas que probé primero —`indent=2` y compacto— son
exactamente las dos que **no** funcionan:

```
sha256(json.dumps(d, sort_keys=True))                      -> bccfae31…   la buena
sha256(json.dumps(d, sort_keys=True, separators=(",",":"))) -> c4dc1e4c…   no
sha256(json.dumps(d, sort_keys=True, indent=2))            -> c0667bb3…   no
```

**La receta vive en el hueco entre "JSONindentado" y "JSON compacto": en los
separadores por defecto, que no son una cosa ni la otra.** Busqué en los dos
extremos y no miré el centro. Un adversarymiró el centro.

Mi docstring afirmaba eso como MEDIDO, y era una Medición_incompletaписанta como
negativa universal. La diferencia entre "no lo he encontrado" y "no existe" es
justo la que separa `NOT_FOUND` de `PROVEN_ABSENT`, y es la que este proyecto lleva
1056 hallazgos insisting en que no se mezcle. Yo la mezclé en la herramienta.

## 2 · EL DEFECTO DE MÁQUINA, QUE ES PEOR QUE EL ERROR DE PROSA

Mi herramienta devolvía `SIN_RECETA` para la clave `reproducible` **incondicionalmente**.
No intentaba ninguna receta. Es decir: publicaba un veredicto que no era el resultado
de medir, sino el resultado de una decisión escrita en el `if`.

Eso tiene un nombre en este proyecto, y es `IMPLEMENTATION_IS_NOT_AUTHORITY` aplicado
al revés: **la autoridad sin medición**. Y salía con `rc=3` sobre el árbol real, que es
justo el código de salida que un gate usaría para bloquear un commit.

Lo peor es que **el self-test no lopillaba**:

```
chk("V3_reproducible_es_SIN_RECETA", ...)   # valor usado: "d"*64
```

`"d"*64` es un valor que no puede tener receta. El vector pasaba por una razón
trivial: comprobaba que el código corre, no que acierte. Lo sustituí por vectores que
calculan el valor de verdad.

## 3 · Y EN EL SELFTEST HABÍA UN DEFECTO DE ORÁCULO QUE NO ESPERABA ENCONTRAR

Añadido el vector correcto, hice la mutación que este proyecto exige —**romper la
herramienta a propósito para comprobar que el self-test falla**— y la mutación **no
falló**:

```
### M10: la receta usa separadores compactos (la forma que probé y falló)
  37 vectores, 0 fallos          <-- el self-test NO la detecta
```

El motivo: el vector nuevo calculaba el valor esperado **llamando a la función bajo
prueba**.

```python
h_repro = receta_reproducible(art_repro)   # el oraculo es el codigo probado
```

Un oráculo que llama al código que prueba no es un oráculo: es una tautología. Y es
**el mismo defecto que audita este documento, un nivel más adentro**: un self-test que
certifica sin medir.

El arreglo son dos anclas independientes, y una de ellas escrita a mano:

```
REPRO_MUESTRA_DEFECTO  = 40a7f3efa39c9fa5…   # calculada FUERA de esta herramienta
REPRO_MUESTRA_COMPACTO = c4dc1e4c91688309…   # la forma que NO vale
REPRO_MUESTRA_INDENT   = c0667bb308f651954…  # la otra que NO vale
```

Más un vector que exige que **las tres formas sean distintas**. Si algún día
coincidieran, el vector avisa, porque un oráculo que no distingue lo que tiene que
distinguir no distingue nada.

Repetida la mutación con el oráculo arreglado:

```
### M10bis: receta con separadores compactos
  FALLA V3ant4_la_receta_producida_usa_los_separadores_por_defecto  producido=c4dc1e4c esperado=40a7f3ef
### M11: "generado" deja de excluirse -> el hash dependería del reloj
  FALLA V3ant4_…   FALLA V3b_la_receta_no_depende_del_reloj
  41 vectores, 2 fallos
```

`V3b` no es decorativo: comprueba que **la misma fixture con seis relojes distintos
dé el mismo hash**. Esa es la condición de sentido del campo. Si `generado` se colara
dentro, el hash no sería "reproducible": sería el hash de un instante.

## 4 · EL HALLAZGO REAL, Y ES OTRO

Refutado lo mío, queda un hallazgo que sí es del árbol y que **no es** sobre
`reproducible`:

**Los bloques de procedencia no tienen regla de invalidación, y por eso se
convierten solos en afirmaciones falsas.**

`findings/977-suite-gart-no-compila-y-no-era-un-maximo.md` §10 declara el sha256 de
seis ficheros. MEDIDO hoy, con `git` como árbitro:

| linea | fichero | declarado | veredicto | ¿el fichero se movió? |
|---|---|---|---|---|
| 316 | `rx550_gart_write.c` | `d784bb1638bf99b5…` | COINCIDE | no |
| 318 | `rx550_vmid0_gart.h` | `ad2c595836b53d83…` | **DIFIERE** | no |
| 320 | `tests/test_gart_write.c` | `e4f9b510b431e020…` | COINCIDE | no |
| 322 | `tests/Makefile` | `28e3b58255916892…` | **DIFIERE** | no |
| 326 | `Q8-TEST-MATRIX/gate-run-1.txt` | `0280d616a3dd774c…` | COINCIDE | no |
| 328 | `Q8-TEST-MATRIX/gate-run-2.txt` | `0280d616a3dd774c…` | COINCIDE | no |

**2 de 6 son afirmaciones falsas. Y el dato que lo convierte en hallazgo y no en
sospecha es que para los dos, `sha256(HEAD:file) == sha256(file)`**: el fichero no
se ha movido. Lo que está mal es el documento.

```
declarado  ad2c5958…   real bf6d120d0a4c8618…   rx550_vmid0_gart.h
declarado  28e3b582…   real 12171a6954fa64cb…   tests/Makefile
```

Sin esa comprobación contra `HEAD`, "el documento se quedó viejo" y "alguien cambió
el fichero" son la misma observación. Este proyecto ya tiene un documento entero
(`RESERVAS-DESYNC.md`) sobre una fecha que se perdía para siempre, y este es el
mismo Disease en otro órgano: **una referencia correcta en el momento de escribirse
que nadie vuelve a mirar**.

**La causa está en el historial, y no es culpa de quien escribió el 977:**

```
10a798d  977: un .c de produccion que no compilaba, y la puerta que media 7 de 16 suites
28f1c47  vmid0_gart: nueve "return -1" que eran nueve causas distintas con un solo numero
```

El 977 se escribió bien. Dos commits posteriores movieron los dos ficheros. El
documento no tenía ninguna manera de enterarse.

`revkit/sello.py` ya resuelve este problema **para la evidencia**, y su docstring lo
dice con una frase que debería estar en la cabecera del 977: *"un sello que se
sobrescribe a sí mismo no recuerda nada"*. Lo que no existe es **el sello de los
bloques de procedencia de los hallazgos**, que son precisamente las afirmaciones que
el proyecto usa como evidencia.

## 5 · LO QUE NO ESTÁ RESUELTO, Y DÓNDE ESTÁ LA FRONTERA

`tools/sello_prov.py` es `RESEARCH_INSTRUMENT`: `SELF_TESTED`, con 41 vectores y 11
mutaciones deliberadas detectadas. **No es `VALIDATED`.** Falta:

- **Una convención única de bloque de procedencia.** MEDIDO: hay **cuatro** layouts
  distintos en el árbol, y mi instrumento entiende dos.
  1. portador primero, hash después (cabeceras R1/R2/R3)
  2. hash primero, fichero en la línea de continuación (`findings/`, ATOMBIOS-DECODER)
  3. el path **dentro** del valor: `sha256  amdgpu_drv.c 07a1fff4…`
     (`decisions/2026-10-03-reconciliacion-Q5-ISA-CAP12.md:132`)
  4. digest **elidido**: `sha256  c80bb5ff…402f150`
     (`ATOMBIOS-DECODER.md:331-334`) — no es un hash, es una abreviatura con puntos
- **Un valor de hash es External y no tiene ruta** (`968:136` cita un PDF de
  `~/Descargas/`; `q5:181`, `README-corpus-discriminante.md:16` nombran el fichero en
  prosa y no en el bloque). 3 `SIN_RECETA` que son **míos**, no del documento.
- **Una raíz de resolución para los árboles citadores.** MEDIDO por el subagente
  `explore`: `ATOMBIOS-DECODER.md:527-537` cita `drivers/gpu/drm/amd/amdgpu/…`, que
  **existe**, en `RESEARCH/baseline/linux-7.1.3/`, a maxdepth 13. Los 6 `ROTO` que
  reporto son **falsos positivos míos** por asumir raíz = raíz del proyecto.
- **`06-INGENIERIA-INVERSA/findings/401:134`** cita `amdgpu/gfx_v8_0.c`, que no
  existe con ese nombre en ningún sitio. Este **no** lo he adjudicado: `NOT_DETERMINED`.

Con esto, el censo completo del árbol da:

```
COINCIDE 13 · EXISTE 8 · ROTO 7 · MALFORMADO 6 · DIFIERE 2 · SIN_RECETA 3
```

y **de los 18 veredictos no limpios, 16 son límites de mi vocabulario** y **2 son el
hallazgo de §4**. La proportion es el dato: un instrumento que fabrica 16 defectos
falsos donde hay 2 reales es peor que no tener instrumento, porque consume el mismo
canal.

## 6 · EL CONFOUNDER, Y POR QUÉ ESTO AFECTA A TODO LO MEDIDO HOY

**Había otra sesión escribiendo en este árbol mientras yo medía.** MEDIDO:

```
12:39:45  tools/pm4ops.py  4066f5838d1132ab
12:41:48  tools/pm4ops.py  d841c93586238458
12:42:22  tools/pm4ops.py  d4615d752973e369
12:47:15  R1/R2/R3 HALLAZGOS.md reescritas
```

y `python3 tools/pm4ops.py --selftest` pasó con `rc=0` a las 12:33 y devuelve `rc=1`
con 2 vectores rojos (`ALC_6`, `ALC_8`) a las 12:40.

Dos consecuencias, y las dos son reglas:

1. **`git status` no es una foto.** La lista de ficheros modificados que vi al
   empezar el turno ya no era la misma a los veinte minutos. Cualquier commits de
   este turno **no** incluye deliberadamente los ficheros del otro escritor: no son
   míos y no he medido su estado final.
2. **Un hallazgo medido sobre un fichero que se está reescribiendo no es un
   hallazgo, es una carrera.** Los valores de `reproducible` que yo leí a las 12:32
   (`d438cfba…`, `b1693a75…`) **no son** los que están ahora, y mi primer
   argumento se apoyaba en ellos. La refutación llegó a tiempo; un hallazgo con
   esa dependencia, publicado sin verificar, habría sido un halluc con hash.

`FILTROS-REPARO-2.md` ya había documentado dos sesiones activas y `HEAD` moviéndose
dentro de su turno. **No es nuevo. Es el estado normal de este árbol y hay que
tratarlo como tal: una acción por iteración, un escritor por árbol, y medir solo lo
que lleva un turno quieto.**

## 7 · LO QUE ESTA ACCIÓN CAMBIA

| cosa | antes | después |
|---|---|---|
| `reproducible` | campo correcto, receta **no escrita** | campo correcto, receta **en `sello_prov.py`** |
| auditar procedencia | imposible | un comando, `rc` con 5 salidas distintas |
| mi veredicto sobre `reproducible` | `SIN_RECETA` incondicional | se recalcula; `COINCIDE` 3 de 3 |
| oráculo del self-test | circular en `reproducible` | dos anclas externas + guardas de forma |
| 2 hashes del 977 | afirmaciones que nadie mira | **`DIFIERE`, y `git` arbitra que la culpa es del documento** |

## 8 · PROCEDENCIA

```text
herramienta   tools/sello_prov.py 1.0.0
sha256        7d2bcc1f3f76fc23
selftest      41 vectores, 0 fallos, rc=0
mutaciones    11 deliberadas, 11 detectadas
              M1  reproducible->COINCIDE (la mentira que el instrumento caza)
              M2  cero bloques -> rc 0          M3  sha256 nunca DIFIERE
              M4  viga sin cerrar no es error   M5  comparacion por prefijo rota
              M6  minimo de 64 bits desaparece  M7  un fichero roto aborta el censo
              M8  se ignora la forma (b)        M9  SIN_RECETA incondicional
              M10 separadores compactos        M11 "generado" deja de excluirse
hermeticidad  selftest en arbol temporal; no lee el proyecto
origen        adversarial-reviewer (refuto el claim), explore (localizo el arbol
              del kernel, cerro 6 ROTO falsos)
```

**Lo que este documento NO prueba.** No prueba que los otros dos layouts de bloque
sean correctos: no los he implementado, así que no puedo decir si sus hashes
cuadran. No prueba que `reproducible` sea la convención que el proyecto vaya a
adoptar: es la que usan tres nodos, y una convención de tres usuarios no es una
convención. Y no prueba nada sobre el hardware: no se ha tocado la GPU.