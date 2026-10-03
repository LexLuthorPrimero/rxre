# 999 · El corpus de definiciones de registro es byte-idéntico en los dos árboles, y el delta entero está en DCN y en un GC que Polaris12 no usa

```text
CLASSIFICATION=MEASUREMENT+PROVENANCE+ERROR   ·   TRACK=STATIC
WORK_CLASS=READ_ONLY + WRITE_LOCAL            ·   MODIFICATIONS 0 sobre fuente
HARDWARE_SCOPE=NONE — no se ha tocado la placa, el módulo ni el kernel
RUNTIME=NOT_RUN                               ·   GPU INTACTA
AUTORIA=AGENT-25 (REGISTER/MMIO REVERSE ENGINEERING)
HERRAMIENTA=find + sha256sum + comm/join        (las DEL SISTEMA, no propias)
```

## Por qué este hallazgo existe

El proyecto usa **dos árboles de fuente a la vez** y ya ha pagado por confundirlos:

- `RESEARCH/kernelbuild/linux-7.1.3` — 153 findings lo citan como `CORPUS`.
- `rx550-upstream-7.2.8` — los hallazgos 012, 013, 023, 031, 114 lo citan como `CORPUS`.

Los `228` y `127` registran el daño real: **citar números de línea de un árbol como
si fueran del otro produjo dos afirmaciones `REFUTED`**. Ninguno de los dos midió
si el corpus de **definiciones de registro** —los ficheros que dan el valor de un
offset y de una máscara— difiere entre ambos. Sin esa medición, una base de datos
de registros no puede declarar si su provenance depende del árbol.

## Lo medido, con el discriminante delante

Pregunta: *¿el corpus de definiciones de registro depende del árbol?*
H1: difieren de forma que un offset o una máscara puedan no ser los mismos.
H2: son idénticos para el alcance de Polaris12 y el delta está acotado.
Discriminante: conjuntos de `sha256` por fichero sobre **los `.h` de
`include/asic_reg/`**, comparados por ruta.

### 0. Ancla de provenance, y un defecto en el ancla

```
$ sha256sum rx550-upstream-7.2.8/linux-7.2.8.tar.xz
12e8d5a973d1ad7c5a5c69882e4022b131ed715db7003fdcd760ddf8c3e51941  linux-7.2.8.tar.xz
```

Coincide con `local.sha256` y con `upstream.sha256`. **Pero esos dos ficheros no
son verificables por máquina**: guardan el digest pelado, sin el campo de nombre
que `sha256sum` exige.

```
$ sha256sum -c local.sha256
sha256sum: local.sha256: no properly formatted checksum lines found
```

Es un `ERROR` de clase `[01]`: un sello que **no detecta nada porque no se puede
ejecutar**. El digest es correcto —lo comprobé yo contra el tarball— pero el
mecanismo de verificación del proyecto está roto en ese punto. Queda registrado
como `ERROR`, no como `REFUTED`: el digest es `PROVEN` por medición propia.

**Límite explícito**: he verificado el digest **del tarball**. No he verificado que
los árboles extraídos en disco sean bit a bit ese tarball. Eso es `NOT_DETERMINED`.

### 1. Qué árbol conduce la placa

```
$ uname -r
7.1.3-200.nobara.fc44.x86_64
$ modinfo -F filename amdgpu
/lib/modules/7.1.3-200.nobara.fc44.x86_64/kernel/drivers/gpu/drm/amd/amdgpu/amdgpu.ko.zst
```

El árbol del kernel **en marcha** es 7.1.3. El 7.2.8 es upstream más nuevo, no lo
que ejecuta. Esto corrobora de forma independiente el `REFUTED` del `901`
(anulado por el `906`): aquel hallazgo afirmaba «este árbol no es el que conduce mi
placa», y el motivo era el inverso.

### 2. El delta, clasificado

| medida | `linux-7.1.3` | `linux-7.2.8` |
|---|---|---|
| cabeceras `.h` en `include/asic_reg/` | **476** | **488** |

- **Borrados: `0`.** Ningún fichero desaparece.
- **Añadidos: `12`**, todos en pares `_offset.h` + `_sh_mask.h`:

```
clk/clk_15_0_5   dcn/dcn_4_2_1   dpcs/dpcs_4_0_1
gc/gc_12_1_1     nbio/nbio_6_3_2 vpe/vpe_2_0_0
```

  Son **revisiones de IP posteriores**. H2 confirmada en esta mitad: son
  exclusivamente hacia adelante.

- **Comunes con contenido distinto: `20`**, y la clasificación es total:

| directorio | ficheros distintos |
|---|---|
| `dcn/` | **18** (`3_0_0`, `3_0_2`, `3_0_3`, `3_1_2`, `3_1_4`, `3_1_5`, `3_1_6`, `3_2_0`, `3_2_1`, cada uno con su `_offset.h` y su `_sh_mask.h`) |
| `gc/` | **2** (`gc_12_1_0_offset.h`, `gc_12_1_0_sh_mask.h`) |
| cualquier otro | **0** |

**Los 20 están en DCN (controlador de display) y en un solo GC, el 12.1.0.**

## La consecuencia, y su límite exacto

Todo fichero de `asic_reg/` que **no** sea de esos dos casos es byte-idéntico entre
el árbol que ejecuta el módulo y el upstream 7.2.8. La forma fuerte de decirlo, y la
que he medido: **`asic_reg/` tiene 39 subdirectorios en común entre ambos árboles, y
solo `dcn` y `gc` contienen alguna diferencia. Los otros 37 son idénticos fichero a
fichero.**

```
athub bif clk dce df dpcs gca gmc hdp lsdma mmhub mp nbif nbio oss pcie pwr
rsmu sdma sdma0..7 smu smuio thm umc uvd vce vcn vpe wafl xgmi   <- 0 diferencias
dcn gc                                                        <- las unicas
```

Ejemplos concretos, comprobados uno a uno (presentes en ambos conjuntos, `distintos=0`):

```
gc/gc_9_0_offset.h        gc/gc_9_0_sh_mask.h        gc/gc_9_1_offset.h
mmhub/mmhub_1_0_offset.h  mmhub/mmhub_1_0_sh_mask.h  mmhub/mmhub_1_7_offset.h
dcn/dcn_2_0_0_offset.h    dcn/dcn_2_0_1_offset.h     dcn/dcn_2_1_0_offset.h
```

Las revisiones `2.x` de DCN —que son las que puede montar una Polaris— también
salen `distintos=0`. Es decir: **para el alcance de la base de datos de registros de
AGENT-25, el provenance no depende del árbol.** Un offset o una máscara citados desde
7.1.3 o desde 7.2.8 son el mismo byte. Eso no estaba medido antes.

*Corrección de método, registrada porque casi se publica*: mi primera versión de
este apartado citaba nombres de fichero inventados a partir del patrón
(`gc_9_0_0`, `mmhub_1_0_0`). Los reales son `gc_9_0` y `mmhub_1_0`. La afirmación
que sobrevive no dependía de esos nombres: la medición es por hash y por pertenencia
al conjunto, no por suposición del nombre. Queda como `ERROR` de redacción, no de
medición.

**Lo que este hallazgo NO cierra**: no he medido qué revisión de IP selecciona
Polaris12 en runtime, ni qué DCN monta esta placa. He probado que *las
definiciones coinciden entre árboles*, no *cuál de ellas usa la placa*. Ese es el
enlace que falta y pertenece a la tabla de descubrimiento de IP, no a este
apartado. Registrado como `NOT_DETERMINED`, no rellenado por inferencia.

## Artefactos

En `06-INGENIERIA-INVERSA/register-maps/`, con `MANIFEST` de hashes:

```
asic_reg-sha256-linux-7.1.3.txt            e3b56ae3abfda85fa0f8b65d8170e657e88efa841b712bbf378fd9410a4c20c2
asic_reg-sha256-linux-7.2.8.txt            ab4522ee1c1d89173f59523e29a24b1033b8f672b6480f740419827316e39130
asic_reg-diferentes-7.1.3-vs-7.2.8.txt     61cf0f2ccbf90c0dcefbd09fa773111e7f1a289174fc7c55a15c2da9d826e3d6
asic_reg-solo-en-7.2.8.txt                 2cfcee71f468572ce4c81714d360eb9dd12570a3d62cc8d5233967c3bfdcb0ab
asic_reg-DELTA.sha256
```

Reproducir:

```sh
A=RESEARCH/kernelbuild/linux-7.1.3/drivers/gpu/drm/amd/include/asic_reg
B=rx550-upstream-7.2.8/linux-7.2.8/drivers/gpu/drm/amd/include/asic_reg
find $A -name '*.h' -exec sha256sum {} + | sed "s#$A/##" | sort -k2 > a.txt
find $B -name '*.h' -exec sha256sum {} + | sed "s#$B/##" | sort -k2 > b.txt
comm -13 <(cut -c67- a.txt|sort) <(cut -c67- b.txt|sort)          # añadidos
comm -23 <(cut -c67- a.txt|sort) <(cut -c67- b.txt|sort)          # borrados
join -j 2 <(sort -k2 a.txt) <(sort -k2 b.txt) -o 0,1.1,2.1 \
  | awk '$2!=$3' | sort                                          # distintos
```

## CORRECCIÓN: esto NO era un hallazgo, y lopubliqué como si lo fuera

Mi primera versión de esta sección **presentaba la duplicación de números como un
descubrimiento propio**. No lo es: publicarlo habría añadido redundancia a la base
de conocimiento y a referencias que ya existen.

La clase completa está medida en el **`245`** —«Cien números de hallazgo
duplicados, y por qué una reserva que no es atómica los produce»—: 323 ficheros,
197 números distintos, 100 duplicados (44 reparables, 56 ambiguos), con la causa ya
localizada (agentes en paralelo reservan el mismo número en la misma ventana de
segundos). El proyecto **ya tiene la herramienta** `tools/dupenum.py`, con política
explícita: solo toca grupos `SEGURO` de exactamente 2 ficheros, y deja los
`AMBIGUO` sin tocar Y con explicación.

Mi medición de este turno da un número distinto, y **no es comparable con el del
245** porque el corpus ha crecido y mi método no es el suyo:

```
$ ls 06-INGENIERIA-INVERSA/findings/*.md | wc -l          -> 512
$ ... | sed 's/-.*//' | sort | uniq -d | wc -l           -> 84   (metodo: sed, no dupenum.py)
```

Esa cifra es `OBSERVATION`, no la medición autoritativa: **`dupenum.py` no llegó a
terminar en el límite de tiempo** (`TIMEOUT` a 120 s, `NO_RESULT`), así que **no
tengo la medición de la herramienta validada del proyecto**. No comparo 84 con 100 y
no atribuyo la diferencia a nada: puede ser crecimiento del corpus, puede ser otro
método, y no lo he discriminado.

Lo único que sí aporta esta sección es que **el grupo muta mientras se escribe**:
cuando lo detecté había un `998-correccion-a-105-no-hay-anillo-de-interrupcion-…`
y otro nodo lo renumeró a `1002-correccion-a-105-el-1024-no-es-el-anillo-de-interrupcion-y-el-real-tiene-4096`
después. Los nombres de fichero citados abajo **no son los de ahora**, y por eso no
los uso como referencia.

**Sobre mi propio número**: este fichero es el segundo `999`. **No lo renumero.** El
245 y `tools/REF-EXCEPTIONS.txt` dejan constancia de que renumerar es una decisión
del nodo de coordinación y de que corregir la cita puede empeorar el registro
histórico; además hay al menos otros tres nodos escribiendo números a la vez, así que
renumerar en esta ventana es exactamente el modo de fallo que el 245 describe. Queda
`NOT_DETERMINED` para quien coordine.

## Estados

| afirmación | estado |
|---|---|
| digest del tarball 7.2.8 = `12e8d5a9…` | `PROVEN` (medición propia) |
| `local.sha256`/`upstream.sha256` no son verificables por máquina | `PROVEN` |
| el árbol en marcha es 7.1.3 | `PROVEN` |
| delta de `asic_reg` = 12 añadidos / 0 borrados / 20 distintos | `PROVEN` |
| los 20 distintos están solo en `dcn/` y `gc_12_1_0` | `PROVEN` |
| de 39 directorios comunes, solo 2 tienen diferencias | `PROVEN` |
| definiciones de registro idénticas entre ambos árboles fuera de DCN y GC 12.1.0 | `PROVEN` |
| el árbol extraído en disco es bit a bit el tarball | `NOT_DETERMINED` |
| revisión de IP y DCN que selecciona esta placa en runtime | `NOT_DETERMINED` |
| duplicación de números en el registro de hallazgos | ya medida en el `245`; aquí solo se **reprodujo** |
| medición autoritativa de `dupenum.py` sobre el corpus actual | `NOT_DETERMINED` (`TIMEOUT`, sin `NO_RESULT` interpretable) |
| este fichero es el segundo `999` | `OBSERVED`, no renumerado por política del `245` |