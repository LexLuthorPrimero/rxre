# CITAS-150 · ADJUDICACION DE LA BANDA INVISIBLE A LA PUERTA

Nodo `CITAS-150`.  MEDIDO, no supuesto.  Instrumento y artefacto al final.

## 0. RESUMEN, Y LO QUE ESTA CONTESTADO

| magnitud | declarada | MEDIDA aqui |
|---|---|---|
| adjudicaciones de la declaracion previa | 132 | 132 (verificado en el fichero) |
| C1 / C2 / C3 / no-citas de la declaracion | 45,7 % [26,0;65,4] / 54,3 % / **0** / 25 | las cuatro cifras estan en el fichero, en sus lineas |
| poblacion de esta banda | **150** | **225** |
| numeros distintos de esa banda | **28** | **35** |
| renumeradas en total | 174 | **255** |
| renumeradas visibles a la puerta | 24 (2 nums) | **30 (2 nums)**; 24 (2 nums) bajo un criterio escrito en §2.4 |
| **C3 en esta banda** | 0 (declarado, no medido) | **6, verificadas una a una** |

**La unica refutacion posible que el encargo nombro, y se ha producido: C3 deja de ser 0.**
Seis citas apuntan al numero viejo y su contenido esta en el numero nuevo. Las seis
son reparables con la flecha del mapa, y las seis son `relacion=contenido`.

**Y dos cosas mas que no estaban en el encargo:**

1. El numero **150 / 28 no es reproducible** bajo ningun criterio que yo pueda escribir
   (§2.4). No lo he usado. He construida una poblacion que si se reproduce y la he
   adjudicado entera.
2. El **hallazgo 1040**, que adjudico este mismo estrato para el numero `267`, queda
   **REFUTADO** en su conclusion (§5). Su conclusion era que las citas a `267` apuntan a un
   tercer fichero, ni el ocupante ni el destino. Apuntan al ocupante.

---

## 1. LAS CUATRO CIFRAS DE LA DECLARACION PREVIA: VERIFICADAS

Artefacto `08-ARQUITECTURA/CITAS-POR-NUMERO-DECLARACION.md`, verificado por hash ANTES de consumirlo:

```
esperado  sha256 = 36cf982390574084c3d5aad59341648b079e11ce3d077e4f683519618f150398
medido    sha256 = 36cf982390574084c3d5aad59341648b079e11ce3d077e4f683519618f150398   IDENTICO
bytes 15123 · 290 saltos de linea · 291 lineas de texto · sin newline final
```

Las cuatro cifras que el encargo me atribuia **estan todas**, con su linea:

| cifra | donde esta |
|---|---|
| 132 adjudicaciones | linea 28 (`muestra estratificada de 132`), linea 63 (`n = 14 por estrato`), linea 291 |
| C1 = 45,7 % IC [26,0 ; 65,4] | linea 85 |
| C2 = 54,3 % | linea 86 |
| C3 = 0 / 132 | linea 87 (`0 confirmadas sobre 132 adjudicaciones`) |
| 25 no son citas | lineas 21 y 88 (`MEDIDO de forma determinista, no estimado`) |

**Una discrepancia de definicion, no de dato:** el encargo decia `lineas = 291` y
`wc -l` da 290. No es un conflicto: 291 es el numero de lineas de texto y el fichero
no termina en newline. Se declara para que el recuento sea comparable.

**Una correccion que el encargo daba por buena y no lo es.** El encargo y la declaracion
dicen que el parche `citas-no-citas-y-A3-informativo.patch` **NO esta aplicado**
(declaracion linea 202-203). MEDIDO: `tools/check_num_unico.py:315-327` **ya tiene**
`NO_CITA_FICHEROS` con las tres rutas y sus razones, y `gate:640-642` las aplica. El parche
si esta aplicado, o el gate ya lo traia. La declaracion esta vieja en ese punto.

---

## 2. LA POBLACION, Y COMO SE CONSTRUYE

### 2.1 Definiciones: COPIADAS de la puerta, no reinterpretadas

Las tres formas de cita y el alcance estan copiados byte a byte de
`tools/check_num_unico.py`, y **verificado que son identicos** los dos instrumentos:

```
           gate    censo    ¿identico?
RE_NUM     :280    :93      SAME
RE_CITA_LL :285    :94      SAME
RE_CITA_BT :286    :95      SAME
RE_CITA_RUTA:287   :96      SAME
EXT_LEIBLES:329    :97      SAME
CODIGO_EXT :350    :100     SAME
CODIGO_SIN_EXT:351 :101     SAME
REGISTRO_CODIGO:352:102     SAME
EXCLUIDOS  :330(5) :98(7)   DISTINTO   <- ver §6.2
```

Texto exacto de las tres formas, que es lo que define la poblacion:

```python
RE_CITA_LL   = re.compile(r"(?<![\w/.\-])(\d{3,4}):(\d+)\b")   # "272:138"
RE_CITA_BT   = re.compile(r"`(\d{3,4})`")                        # "`272`"
RE_CITA_RUTA = re.compile(r"findings/(\d{3,4})(?![\d\w\-])")     # "findings/272"
EXT_LEIBLES  = (".md", ".py", ".sh", ".c", ".h", ".txt", ".tsv")
EXCLUIDOS_PROPIO = ("RESEARCH", "rx550-upstream-7.2.8", "archive", ".git", "__pycache__")
```

### 2.2 El recorte del recorrido, declarado

`os.walk` desde la raiz del proyecto podando `EXCLUIDOS_PROPIO` **de la puerta**, que
excluye `RESEARCH/`. MEDIDO: **2526 ficheros leidos, 0 omitidos, 339 directorios**.
Ese es el recorte: los ~110 000 ficheros de `RESEARCH/` (los cuenta `gate:173-174`) no
se abren. El recorte es el de la propia puerta, no uno mio, para que mi poblacion sea la
que la puerta veria.

### 2.3 La definicion de la banda, y por que es la invisible

1. Recorrer el arbol con las tres formas de la puerta.
2. `dups` = numeros con **mas de un** fichero `NNN-*.md` en `06-INGENIERIA-INVERSA/findings/`
   (`gate:601`). MEDIDO: **74**.
3. `renumerados` = numeros que aparecen como `viejo` en `REENVIO-FINDINGS.tsv` con
   `reasignado=SI`. MEDIDO: **55** filas de dato, **56** `viejo` distintos.
4. **REN** = toda cita cuyo numero esta en `renumerados`.        MEDIDO: **255**
5. **INV** = REN **y** el numero **NO** esta en `dups`.           MEDIDO: **225**

El paso 5 es el discriminante, y no es mio: es literalmente `gate:635`,
`if num not in dups: continue`. Una cita a un numero renumerado que hoy es UNICO no
entra nunca en la poblacion de A3. Por eso la banda existe, y por eso la puerta no la ve.

REPARTO MEDIDO:

| banda | citas | numeros distintos |
|---|---|---|
| REN (todas) | 255 | 37 |
| REN ∩ dups  -> **VISIBLE** a A3 | **30** | **2** |
| REN \ dups -> **INVISIBLE** a A3 | **225** | **35** |

### 2.4 EL 150 / 28 NO ES REPRODUCIBLE. Lo que he hecho en vez de usarlo

Antes de construir nada he barrido el espacio de definiciones. **Ninguna** combinacion
reproduce el triple declarado (174 renumeradas, 24 visibles, 150 invisibles en 28
numeros). Barrido de 48 combinaciones de:

- alcance: `EXCLUIDOS_PROPIO` de la puerta, o el del censo (que anade `07-DRIVER`)
- extensiones: `EXT_LEIBLES`, o solo `.md`
- deduplicacion: ninguna, por `(fichero,linea,num)`, o por `(fichero,num)`
- renumerados: `viejo & reasignado=SI`, o todo `viejo` del mapa
- mas: solo `relacion=contenido`, solo `relacion=numero`, excluyendo el mapa y su indice,
  excluyendo las herramientas del censo, excluyendo ficheros de codigo

Resultado del barrido (recuento / numeros):

```
excl    ext    dedup    renum |  REN  VIS(n)  INV(n)
propio  EXT    -        SI    |  255   30( 2)  225(35)
censo   EXT    -        SI    |  242   30( 2)  212(35)
propio  md     -        SI    |  204   25( 2)  179(35)
propio  EXT    f+num    SI    |  156   15( 2)  141(35)
censo   EXT    f+num    SI    |  150   15( 2)  135(35)   <- 150 sale aqui, y no es INV
propio  EXT    -        todos |  259   30( 2)  229(36)
solo relacion=contenido      |  141   12( 1)  129(26)
solo relacion=numero         |  114   18( 1)   96( 9)
sin el indice del mapa       |  243   28( 2)  215(35)
sin indice ni herramientas   |  237   24( 2)  213(35)   <- 24(2) sale aqui
```

Dos cosas que si se reproducen, y una que no:

- **`24 visibles en 2 numeros`: SI.** Sale a `237 renumeradas / 24 visibles (2) / 213
  invisibles (35)` cuando se excluyen del recuento el indice del mapa
  (`FINDINGS-RENUMERACIONES.md`) y las herramientas del censo. Ese es el unico criterio
  del barrido que da 24(2). No lo adopto como poblacion porque no hay nada escrito que lo
  funde; lo dejo dicho porque es la unica pieza del tripulo declarado que se sostiene.
- **`150`**: sale como **REN total** en una variante (`censo` + `dedup(fichero,numero)`),
  con 15 visibles y **135** invisibles en 35 numeros. No es la magnitud declarada.
- **`28 numeros`: NO.** El numero de numeros distintos de la banda es **35 en 30 de las
  48 variantes**, 26 si solo se admiten filas `contenido`, y 9 si solo `numero`. **No hay
  ninguna combinacion que de 28.** Y 35 no depende de la deduplicacion ni de la
  extension, porque un numero cuenta o no cuenta segun tenga una cita.

**Conclusion:** el `150 / 28` de la declaracion no es reproducible con un criterio que yo
sepa escribir. Un conjunto de 150 formado por un criterio no escrito no es evidencia, y
por eso **no he adjudicado 150: he adjudicado 225**, con la construccion de §2.3, que es
reproducible y esta escrita. El numero que sale de aqui no es el que se esperaba, y esa
discrepancia se reporta en vez de promediarse.

### 2.5 Procedencia de las 225

97 ficheros distintos. Por directorio:

```
06-INGENIERIA-INVERSA               116
08-ARQUITECTURA                      21
docs                                 20
tools                                14
07-DRIVER                            13
05-FUENTES-EXTERNAS                  11
NEGATIVE-RESULTS.md                  10
FINDINGS-RENUMERACIONES.md           10
01-AUDITORIA                          4
02-ARQUITECTURA                       3
HARDWARE-FINGERPRINT.md               3
```

Por forma de cita: ``NNN``=171, `findings/NNN`=30, `NNN:LL`=24.

---

## 3. QUE SIGNIFICA `viejo -> nuevo`. Medido, no supuesto

Antes de adjudicar hice una comprobacion que decide el metodo. Para las **57 filas** del
mapa compare el `stem` de la fila con los ficheros que HOY llevan ese numero:

```
MEDIDO sobre las 57 filas:
  stem == fichero de HOY con el numero NUEVO :  57 / 57   VERDADERO en todas
  stem == fichero de HOY con el numero VIEJO :   0 / 57   FALSO en todas
```

O sea: la fila dice **el hallazgo con este cuerpo estaba en `viejo` y ahora esta en
`nuevo`**. Y el numero `viejo` **hoy lo ocupa otro hallazgo distinto**. MEDIDO sobre los
35 numeros de esta banda: los 35 tienen **exactamente un** fichero hoy, y ese fichero
**no es** el que el mapa nombra.

**Esto refuta la regla que el encargo me daba.** El encargo decia: *"una cita a un
numero renumerado es correcta si apunta al numero NUEVO, y es un C3 si apunta al
viejo"*. Con esa regla las 225 serian C3 y C3 seria 225. Es falso, y la razon esta
escrita en el propio proyecto:

- `CITAS-POR-NUMERO-DECLARACION.md:147-151`: *"el mapa de renumeraciones dice DONDE esta
  un contenido, no que toda cita al numero viejo este equivocada"*, y las cuatro que
  el proxy marco C3 *"eran falsas"*.
- El caso `1011->1020` se resuelto **por tamano, no por vocabulario** (declaracion
  linea 141-145).
- Y el mas fuerte: el DISCROMINANTE de este nodo no puede ser el numero, porque el
  numero viejo esta hoy Ocupado por otro contenido. Lo que decide es **de que contenido
  habla la prosa**, y eso hay que leerlo.

Por eso el verbo que uso es `C3_APUNTA_AL_VIEJO`: *la cita nombra un numero viejo y su
contenido esta en el nuevo*. Y por eso `CORRECTA_APUNTA_AL_NUEVO` del encargo **no puede
aparecer en la tabla**: por construccion de la banda, toda cita de INV nombra un numero
viejo. Lo que si aparece es `CORRECTA_APUNTA_AL_OCUPANTE`: la cita nombra un numero
renumerado, pero hoy ese numero lo ocupa un hallazgo, y **de ese hallazgo** habla la prosa.
Es la clase mayoritaria, y no existe en el vocabulario del encargo.

---

## 4. LOS VEREDICTOS, Y CADA UNO CON SU PRUEBA

El orden de las comprobaciones **es el dato**, por la misma razon que escribe
`citas_prosa_census.py:536-545`: la comprobacion que depende de contenido va **despues**
de las que son correctas por construccion, porque si se aplica antes mezcla clases.

| # | veredicto | regla | n |
|---|---|---|---|
| 1 | `NO_ES_CITA` | el token es un numero que no es de hallazgo (uid, codigo de salida, constante, valor de registro, direccion PCI, patron binario). Enumerado a mano, con razon positiva por fila | 24 |
| 2 | `C3_APUNTA_AL_VIEJO` | el contenido de la prosa esta en el destino y **no** esta en el ocupante, y la fila es `relacion=contenido`. Verificado a mano una a una | 6 |
| 3 | `CORRECTA_META_RENUMERACION` | la cita esta en el mapa o en su indice, o el contexto declara el renumerado: el numero viejo se nombra **en su papel de numero viejo** | 34 |
| 4 | `CORRECTA_AUTOCITA_OCUPANTE` | la cita esta dentro del fichero que hoy lleva ese numero. Correcta por construccion | 10 |
| 5 | `CORRECTA_AUTOCITA_DESTINO` | la cita esta dentro del fichero destino, hablando del numero viejo | 6 |
| 6 | `CORRECTA_APUNTA_AL_OCUPANTE` | la prosa habla del contenido del ocupante: anclas del contexto en el ocupante y no en el destino | 105 |
| 7 | `RESUELVE_AL_OCUPANTE_NO_VERIFICADA` | el numero es UNICO hoy, luego la cita **resuelve**; pero el contexto no lleva contenido que la confirme o la refute | 40 |

### 4.1 LOS 6 C3. Esta es la cifra que decide C3

Cada uno con su discriminante medido. `oc` = ocurrencias en el ocupante, `de` = en el destino.

```
NEGATIVE-RESULTS.md:238   cita 144 -> 231
   prosa: '`144` cerro `GFX_HWIP` como `PROVEN_ABSENT` y ofrecio el firmware como fuente'
   GFX_HWIP      oc= 0   de=13        firmware   oc= 0  de=23
   ip_version    oc= 0   de= 9        PRT        oc=49  de= 0
   H1 ocupante : '# 144 - El PRT cierra en comportamiento y no en numero, y el corpus
                  no tiene interfaz de usuario'
   H1 destino  : '# 231 - `GFX_HWIP` no existe, pero el IP version esta en el firmware'
   y `144:114` de HOY es un encabezado de seccion, y `144:124` es un cercado de codigo.
   MEDIDO ademas: el MISMO fichero NEGATIVE-RESULTS.md tiene filas `231 | 39` y
   `231 | 210` con ese mismo contenido. La tabla se escribio antes del renumerado y esas
   dos filas no se actualizaron.

NEGATIVE-RESULTS.md:240   cita 144 -> 231     (misma fila y mismo sujeto que :238)

docs/AGENTS-RECTOR-2026-10-02.md:486   cita 103 -> 210
   prosa: 'El handshake de completion **existe** (`103` corrige a `072`)'
   handshake     oc= 0  de= 3      completion  oc=0  de=2      `072`  oc=0  de=12
   H1 destino  : '# 210 - S-C: el handshake de COMPLETACION si existe, y `072` afirmo
                  lo contrario'   = la prosa, literal
   H1 ocupante : '# 103 - El parche de UVD no cae en BootVddc...'  (UVD x24, handshake x0)

docs/AGENTS-RECTOR-2026-10-02.md:488   cita 104 -> 211
   prosa: '`VM_INVALIDATE_REQUEST` y `RESPONSE` son 16 bits cada uno ... (`104`)'
   VM_INVALIDATE_REQUEST oc=0 de=5    VM_INVALIDATE_RESPONSE oc=0 de=5   '16 bits' oc=0 de=5
   H1 destino  : '# 211 - S-C: `VM_INVALIDATE_REQUEST` y `RESPONSE` son 16 bits cada uno,
                  con layout identico'   = la prosa, literal
   H1 ocupante : '# 104 - Once usos de dpm_table_start, y el hueco de 108 bytes...'

NEGATIVE-RESULTS.md:252   cita 188 -> 240
   prosa: '`188` (la cadena observada y el `PROVEN_ABSENT` del simbolo)'
   eslabon  oc=0 de=5     observad  oc=0 de=7     PROVEN_ABSENT  oc=0 de=3
   H1 destino : '# 240 - La cadena de identidad pasa de derivada a observada, y
                  `AMDGPU_FAMILY_VI` no existe en el corpus'

NEGATIVE-RESULTS.md:271   cita 188 -> 240
   prosa: 'Encadenada con `188` (los tres eslabones observados...)'  -> 240
```

**Los seis son reparables con la flecha del mapa, y los seis son `relacion=contenido`.**
MEDIDO: `103->210`, `104->211`, `144->231`, `188->240` son las cuatro parejas, y las
cuatro filas del mapa son de tipo `contenido` con `procedencia=diff`.

**Y no he usado ninguna flecha `numero` para reparar nada.** Es la misma regla que fijo
el hallazgo 1040 decision 2, y se sostiene: para una fila `numero` la flecha no
repara. MEDIDO: la banda toca 36 filas del mapa, **26 `contenido` y 10 `numero`**. Las
10 filas `numero` cubren 9 de los 35 numeros y **96 de las 225 citas**, y **de esas 96 no
ha salido ni un C3**. Los 6 C3 estan todos en filas `contenido`, que es exactamente el
comportamiento que predice la regla de 1040.

### 4.2 DOS CONTROLES, porque un metodo que solo acierta no vale como metodo

El mismo numero, el mismo dia, el veredicto opuesto. Sin esto, los 6 C3 de arriba
serian una afirmacion con recuento de ocurrencias a su favor y nada que la contrastara.

```
CONTROL A  docs/AGENTS-RECTOR-2026-10-02.md:490   cita 106  -> CORRECTA
   prosa: '**`FUNCTION` NO EXISTE en GFX8** ... escribe `1 << vmid`, bits 0-15 (`106`)'
   FUNCTION  oc=20  de= 1        vmid   oc=15  de=0        'no existe' oc=6 de=0
   H1 ocupante : '# 106 - S-C cerrada: `FUNCTION` no existe en GFX8, y el driver solo
                  escribe 16 bits de dominio'   = la prosa, literal
   -> la MISMA frase, el MISMO fichero, la MISMA lista, y aqui el ocupante gana.
   En 484,486,488,490 la lista es 103/104/106 y SOLO 106 es correcta: dos de tres
   quedaron con el numero viejo. Eso es la firma de un documento escrito antes del
   renumerado y no reescrito, no de un error de lectura.

CONTROL B  findings/979-...:123   cita 188  -> CORRECTA
   prosa: 'es el gemelo del hueco que 188:146-168 ya declara ("una cita puede...")'
   cita   oc=21 de= 3        generaci  oc=10 de=0
   equivocada oc= 5 de= 0     'op 12'   oc= 6 de=0
   H1 ocupante : '# 188 - El nombre del op 12 no es un alias ... y una cita que
                  senalaba a la generacion equivocada'   = la prosa, literal
   -> 188 tiene DOS citas correctas (979:123 y 979:136) y DOS C3 (NEG-RESULTS:252 y
      :271). El numero es el mismo. Lo que decide es el contenido de la frase.
```

### 4.3 Lo que NO se afirma

`RESUELVE_AL_OCUPANTE_NO_VERIFICADA` = **40** citations. No las cuento como correctas.
El numero es unico hoy, luego la cita **no es ambigua**: resuelve a un fichero
determinista. Pero el contexto no lleva ningun contenido que confirme que ese es el
hallazgo al que se refiere, asi que **no se afirma que esten bien**. Se afirma solo que
no se han refuteado. La clase C2 de la declaracion es de otra cosa: es ambiguedad
sobre un numero DUPLICADO, y aqui el numero es unico.

`NO_ES_CITA` = **24**. La puerta declara 3 rutas en `NO_CITA_FICHEROS` (`gate:315-327`).
De mis 24, **11 caen dentro de una ruta ya declarada**: las de la tabla de decodificacion
x86-64. Las otras **13 son nuevas** y estan todas en el mismo patron que la puerta todavia
no cubre: **uid de usuario, codigo de salida de shell y constantes de reloj**, que la puerta
cuenta como cita porque `126` y `1000` son tres o cuatro digitos entre acentos graves. Son
el mismo defecto que las no-citas de la declaracion, en ficheros que su
`NO_CITA_FICHEROS` no nombra.

---

## 5. EL HALLAZGO 1040 QUEDA REFUTADO EN SU CONCLUSION

1040 (`findings/1040-una-tabla-con-dos-relaciones-distintas...md`) adjudico este mismo
estrato para el numero `267`, que es **el mayor de la banda**: 39 de mis 225. Su
conclusion, linea 78-79:

> *"el destino pretendido de esas 27 citas es **ni el 267 ni la 271**. Es un tercero."*

**MEDIDO, y es falso.** El ocupante de `267` hoy es
`267-la-curva-vf-de-mi-vbios-no-esta-rellena.md`, y contiene la tabla de 8 niveles con
el clock-stretch por nivel, escrita con otras cabeceras:

```
267:34  Cabecera en `0x9D15`: `ucRevId = 1`, `ucNumEntries = 8`.
267:22    ucCKSVOffsetandDisable UCHAR          <- el campo CKS, con otro nombre
267:36  | lvl | ulSclk | MHz | ucVddInd | usVddcOffset | ulSclkOffset | CKS |
267:38  |  0 | 21400  | 214 |    0     |      0       |      0       | deshabilitado (0x80) |
267:39  |  1 | 55100  | 551 |    2     |     -26       |   3000       | habilitado |
267:45  |  7 | 107100 |1071 |    9     |      0       |   1500       | habilitado |
```

Y las citas a `267` apuntan a **eso**. Discriminantes medidos, ocupante contra destino:

```
   269:161  `ucVddInd`        oc= 6  de=0     272:153  `ulSclk`         oc>0  de=0
   269:163  `MinVoltage`      oc= 2  de=0     272:154  `MinVoltage`     oc= 2  de=0
   604:45   `0x9D15`          oc>0  de=0     603:79   '15 bytes'       oc>0  de=0
   1040:68  `pptable_v1_0.h:185`  la prosa es LITERAL a 267:14-18
   266:125  550:177  550:187  272:125  272:153  -> 8 niveles, VBIOS, 1071 MHz
```

El punto exacto del desacuerdo: 1040 busco la cadena literal `cks_enable` y concluyo
que el destino era un tercero. MEDIDO: `cks_enable` aparece en **10 ficheros** de
`findings/`, no en uno (050 lo tiene 5 veces, que es lo que 1040 cita). Y el
ocupante de 267 tiene la misma tabla con la columna `CKS` y el campo
`ucCKSVOffsetandDisable`. **Es el error que el propio proyecto ya escribio:** buscar un
literal y concluir una ausencia de semantica. `NO_DOCUMENTACION != NO_SEMANTICA`
(`AGENTS.md` 8). Y aqui es peor: no es `NOT_FOUND`, es `FOUND CON OTRO NOMBRE`.

**Lo que 1040 acerto y se mantiene:** su decision 2, que la flecha de una fila `numero`
no repara citas, y su lectura de la fila `267|271` (que es una colision de
asignacion de numero, no un renumerado de contenido). Eso lo he verificado y lo he
respetado: ninguna de mis 6 C3 usa una fila `numero`.

**Una fila de 1040 que no la he medido:** `269:44` dice *"`cks_enable` = 0 en el nivel
0 y 1"* y la tabla de 267 dice nivel 0 deshabilitado y **nivel 1 habilitado**. Si
`cks_enable` significa clock stretch activo, la afirmacion de 269 y la tabla de 267 se
discrepan. Eso **no es un defecto de cita** --las dos son la 267-- es una
contradiccion de contenido entre 267 y 269. Se declara y no se adjudica aqui: es
`NOT_DETERMINED` y no lo he cambiado.

---

## 6. CONSECUENCIA PARA LA PUERTA

### 6.1 El defecto, con la cita que lo demuestra

**La puerta no resuelve el renumerado, y por eso no puede cerrar C3.** No es una
opinion: es una linea.

```
tools/check_num_unico.py:635
                    if num not in dups:
                        continue
```

A3 filtra por `dups` **antes** de contar. Consecuencia medida: las **225** citas de esta
banda van a numeros que HOY son unicos, luego **0 de 225** pueden entrar en la
poblacion de A3, y ningun ajuste de A3 las alcanza. Los 6 C3 que he verificado estan
en `NEGATIVE-RESULTS.md` y `docs/AGENTS-RECTOR-2026-10-02.md`, sobre los numeros 144,
188, 103 y 104, **los cuatro unicos hoy**. A3 no los ve, y no los vera mientras la
linea 635 sea esa.

Y hay una segunda grieta: aunque la cita caiga en un numero duplicado y A3 la cuente, A3
la cuenta **sin saber que ese numero tiene historia**. La fila de `renumerados` se
puede leer antes de la linea 635 y no se lee. MEDIDO: 30 de las 255 renumeradas caen
en numero duplicado, y A3 las cuenta como 30 citas ambiguas más, sin distinguirlas.

**Lo que NO propongo.** No he tocado la puerta. No es mi mandato, y un parche a un
instrumento que otro nodo esta moviendo es como se pierde una medicion. Lo que
procede es el enunciado del defecto:

> *A3 no puede cerrar la clase 3 por construccion, porque su poblacion excluye, por
> `gate:635`, toda cita a un numero renumerado que hoy no este duplicado. La clase 3 no
> esta donde A3 mira.*

### 6.2 El alcance del censo, que no es lo mismo que el de la puerta

MEDIDO, y es una divergencia real entre los dos instrumentos:

```
                     puerta (gate:330)        censo (citas_prosa_census.py:98)
EXCLUIDOS            5 entradas               7 entradas
                     RESEARCH, upstream,      las 5 de la puerta  +
                     archive, .git,            07-DRIVER, node_modules
                     __pycache__
```

El censo excluye `07-DRIVER`. La puerta no. MEDIDO el efecto: `07-DRIVER` contiene
**13** de mis 225. O sea: las dos poblaciones no pueden ser la misma poblacion, y el
`--cruzado` del censo, que afirma *"poblacion == la de A3"* (`censo:59-61`), compara
dos recuentos que se construyen con alcances distintos. Con las 8 constantes de
forma identicas y un alcance distinto, la comparacion no puede salir bien por
construccion, y si sale bien es porque las dos diferencias se compensan, que es peor.

### 6.3 Lo que yo he hecho y la puerta no puede hacer todavia

Las 6 C3 **se reparan** con la flecha del mapa, porque las cuatro filas implicadas son
`contenido` con `procedencia=diff`, que es el caso en que la flecha si mapea
contenido (`1040:48-56`). El instrumento para hacerlo ya existe y ya esta escrito:
`tools/refs_repair.py`. No lo he ejecutado: reescribir prosa es decision de otro nodo, y
esta adjudicacion es una medida.

---

## 7. EL 7 DE LA PUERTA: LAS 71 QUE NO CUBRO, Y POR QUE NO LAS CUBRO

MEDIDO ejecutando la puerta:

```
  A3  citas por numero a un numero duplicado: 2223
  CODIGOS QUE SE DISPARAN: [5, 7]
  CODIGO DEVUELTO         : 5
    5  el indice de disco no regenera identico
    7  hay citas por numero que el CENSO no ha adjudicado  (poblacion 2223, censo 2152)
  RC=5
```

**La cifra es 71, no 70.** El encargo decia 2222 y yo mido 2223. No es un error de
ninguno: el arbol cresce mientras se mide. MEDIDO: entre mi primera y mi segunda pasada
los ficheros leidos pasaron de 2520 a 2526, y `findings/` de 547 a 548. La poblacion de
esta banda **no se movio** (255/30/225 en las dos pasadas), porque los ficheros nuevos
no citan numeros renumerados.

**Mi adjudicacion NO cubre ninguna de las 71, y el motivo es estructural, no de
alcance.** El 7 compara dos **recuentos**: la poblacion de A3 (citas a numero
DUPLICADO, 2223) contra `CENSO_POBLACION = 2152` (`gate:300`). Son dos cifras de
instantes distintos, luego **el 71 no identifica QUE citas son**, y no es un conjunto
enumerable. Y las dos poblaciones son **disjuntas por construccion**:

```
poblacion del 7 : citas a numeros DUPLICADOS      (2223)
poblacion mia  : citas a numeros RENUMERADOS y UNICOS (225)
               ^ una cita no puede estar en las dos: `dups` y `no dups` son complementarios
interseccion    : 0
```

Las dos clases de defecto que quedan son distintas y necesitan instrumentos distintos:

| | que es | quien lo mide | estado |
|---|---|---|---|
| el 7 (exit 7) | la MEDIDA del censo esta caduca frente a una poblacion que ha crecido | refreshing `CENSO_POBLACION`, que es un acto de trabajo, no de verificacion (`gate:62-67`) | declarado, sin hacer |
| esta banda | citas que apuntan al contenido renumerado y no lo dicen | lectura de la prosa, una a una | **medido: 6 C3** |

Que el 7 no cubra esta banda **no es un fallo del 7**: es que mira un numero distinto.
Lo que si es un fallo es que **el 7 se lee como si cubriera todo**, y por eso lo
escribo aqui.

---

## 8. EL INTERVALO: NO LO HAY, Y POR QUE NO LO HAY

Las 225 **son la poblacion completa de la banda**, no una muestra: la banda se construye
con las tres formas de la puerta sobre el arbol entero con su recorte declarado (§2.2),
y se adjudican las 225 una a una. Solo una poblacion completa carece de
incertidumbre de muestreo, asi que **no hay IC de Wilson que calcular**, y no se
presenta ninguno. El numero **225 es exacto**, y **6 C3 tambien**.

**Lo que no es exacto, y se declara como cota y no como intervalo:**

```
denominador de citas reales : 225 - 24 no-citas = 201
C3 confirmadas              : 6
sin verificar (clase 7)     : 40

   cota inferior de C3  =   6 / 201 =  2.99 %   (las confirmadas, y son confirmadas)
   cota superior de C3  =  46 / 201 = 22.89 %   (si las 40 sin verificar fueran C3)
```

Y esto **no** es un IC al 95 %: es el intervalo que produce el hecho de que 40 citas
estan sin adjudicar por contenido. Es una cota de trabajo, y la unica forma de cerrarla
es leer esas 40. Lo que **no** es admisible es presentar el 3,0 % sin la cota, que es
exactamente el error que la declaracion previa denuncia en si misma cuando escribe
*"usar 45,7 % como si fuera 45,7 % seria mentir"* (declaracion linea 94-95).

**Y una distincion que hay que hacer explicita, porque fue el error del encargo:** el
3,0 % es un **recuento sobre una poblacion completa**, no un porcentaje de una muestra.
No lleva IC. El 45,7 % de la declaracion es un **punto medio de una muestra**, y por eso
lleva IC de 40 puntos de ancho. **Las dos cifras no son comparables y no deben
ponerse en la misma columna.**

---

## 9. QUE REFUTARIA ESTAS CIFRAS

Cada afirmacion importante, con la observacion que la refutaria:

| afirmacion | que la refutaria |
|---|---|
| la banda son 225 en 35 numeros | un recorte del recorrido mas amplio que recoja mas citas: p.ej. `RESEARCH/` incluido, o `07-DRIVER` (que son 13 de las 225 y que el censo si excluye) |
| C3 = 6 | que el 144, 188, 103 o 104 de HOY contengan `GFX_HWIP`, `eslabon`+`observad`, `handshake`+`072`, o `VM_INVALIDATE_REQUEST`+`16 bits` respectivamente. MEDIDO: 0 ocurrencias de cada uno. **La refutacion se pudo hacer y salio negativa** |
| las 6 son reparables con la flecha | que la fila del mapa fuera `numero` y no `contenido`. MEDIDO: las cuatro son `contenido`/`diff` |
| la banda es invisible a la puerta | que `gate:635` dejara de filtrar por `dups`, o que `dups` incluyera los 35 |
| 1040 queda refutado | que un hallazgo de la banda dijera lo que las citas a `267` dicen, y que ese hallazgo **no** fuera el 267 de hoy |
| NO hay ambiguedad en la banda | que alguno de los 35 numeros tuviera >1 fichero hoy. MEDIDO: los 35 tienen exactamente 1 |

---

## 10. DERIVA, Y DOS ERRORES MIOS QUE NO SON HALLAZGOS

**Deriva del arbol durante el trabajo, medida:**

```
ficheros leidos en el recorrido : 2520  ->  2526
ficheros .md en findings/       :   547  ->    548
poblacion de A3 (puerta)        :  2222  ->   2223
la banda (255/30/225)           :  255/30/225  ->  255/30/225   INMOVIL
REENVIO-FINDINGS.tsv sha256     : 8bd6c69c665cf460...  ->  IGUAL (el mapa no se movio)
CITAS-POR-NUMERO-DECLARACION   : 36cf982390574084...  ->  IGUAL
```

**`tools/check_num_unico.py` SI cambio de hash** (`ec875d9a...` -> `7ef0a10d...`). Lo
comprobe antes de dar por buena mi poblacion, porque la puerta es el instrumento que la
define. MEDIDO con `git diff`: el cambio es de **22 lineas añadidas y 1 eliminada, todas
de documentacion**, en el docstring del codigo de salida 7. **0 constantes, 0 regex, 0
def.** La poblacion no se ve afectada, y por eso la cifra 225 sigue valiendo. Se declara
porque un hash que cambia bajo los pies es informacion, no ruido.

**El `FileNotFoundError` intermitente que aviso el encargo: NO lo he observado, y el
que he tenido fue mio.** En `CITAS-POR-NUMERO-DECLARACION.md` no me ha pasado ni una
vez: 25 reintentos con hash, todos correctos. En su lugar me ha pasado un
`FileNotFoundError` en `.../findings/220-clock-stretch-amount-le**a**do-del-vbios.md`, y
la causa **es mia**: habia truncado el nombre a 40 caracteres en una tabla de salida y
reconstrui el nombre a mano. El nombre real es `...le**i**do-...`. MEDIDO: 25/25
`open()` fallan, y `os.path.exists`, `os.path.isfile`, `os.stat` y `os.listdir` **cuatro
APIs independientes** coinciden en que no existe: era un nombre mal escrito, no una
lectura intermitente. **Causa: MEDIDO, no `NOT_DETERMINED`.**

Lo dejo escrito porque el sintoma se parece y la conclusion no: si cuatro APIs
coinciden en que el fichero no esta, el fichero no esta, y reintentar no lo va a cambiar.
Un diagnostico que separa `NOT_FOUND` de `OBSERVABILITY_LIMITED` es exactamente esto.

---

## 11. REPRODUCIR

```bash
# 1. hash del artefacto que se consume, antes de consumirlo
python3 -c "import hashlib;print(hashlib.sha256(open('08-ARQUITECTURA/CITAS-POR-NUMERO-DECLARACION.md','rb').read()).hexdigest())"

# 2. el mapa congelado: 57 filas de dato x 6 columnas
python3 -c "print(sum(1 for l in open('08-ARQUITECTURA/tools/REENVIO-FINDINGS.tsv') if l.strip() and not l.startswith('#')))"

# 3. la banda y el reparto visible/invisible  -> 255 / 30(2) / 225(35)
#    (recorrido os.walk con EXCLUIDOS_PROPIO de la puerta; ver §2.3)

# 4. la puerta, que confirma 2223 y el 7
python3 tools/check_num_unico.py ; echo RC=$?

# 5. los 6 C3, cada uno con su discriminante
python3 - <<'EOF'
import os
F='06-INGENIERIA-INVERSA/findings/'
def r(n): return open(F+n,encoding='utf-8',errors='replace').read()
for o,d,t in [('144-prt-cierra-y-el-corpus-no-tiene-uapi.md','231-ip-version-del-firmware-cierra-gfx-hwip.md',['GFX_HWIP','firmware','PRT']),
               ('188-el-nombre-del-op-12-y-la-cita-equivocada.md','240-la-cadena-de-identidad-observada.md',['eslabon','observad']),
               ('103-el-parche-de-uvd-reescribe-bootvddc.md','210-sc-handshake-de-completacion-existe-y-072-se-equivoco.md',['handshake','completion','072']),
               ('104-once-usos-de-dpm-table-start-y-el-hueco-de-108.md','211-sc-invalidate-request-response-16-bits.md',['VM_INVALIDATE_REQUEST','16 bits'])]:
    a,b=r(o),r(d); print(o[:20],'->',d[:20],[(x,a.count(x),b.count(x)) for x in t])
EOF
```

---

## 12. LA TABLA, LAS 225 UNA A UNA

`fichero:linea` · forma · numero · en el mapa · `relacion` · destino · veredicto · prueba.
Ordenada por fichero y linea. Las 6 C3 van marcadas.

| `01-AUDITORIA/DECISIONES-D1-D10.md:693` | ``NNN`` | 144 | si | `contenido` | 231 | `RESUELVE_AL_OCUPANTE_NO_VERIFICADA` | el numero 144 es UNICO hoy, luego la cita resuelve al ocupante; el contexto no lleva contenido que la confirme o la refute |
| `01-AUDITORIA/FASE-C1-RUNTIME-PREFLIGHT/C1-PREFLIGHT-20260925T060029Z-SUPPLEMENT.md:31` | ``NNN`` | 126 | si | `contenido` | 228 | `NO_ES_CITA` | numero de permiso POSIX en una columna de FD-level, no un numero de hallazgo |
| `01-AUDITORIA/OWNERSHIP-AUDIT-HOST-C/OWNERSHIP-AUDIT-HOST-C-20260925T231635Z.md:15` | ``NNN`` | 1000 | si | `numero` | 1004 | `NO_ES_CITA` | uid de usuario del agente de captura, no un numero de hallazgo |
| `01-AUDITORIA/OWNERSHIP-AUDIT-HOST-C/OWNERSHIP-CLOSURE-ATTEMPT-20260925T232522Z.md:50` | ``NNN`` | 1000 | si | `numero` | 1004 | `NO_ES_CITA` | valor de la columna `uid`, no un numero de hallazgo |
| `02-ARQUITECTURA/POLARIS12-MAP/AMDGPU-POLARIS12-DECISION-POINTS.md:146` | ``NNN`` | 1003 | si | `numero` | 1005 | `CORRECTA_APUNTA_AL_OCUPANTE` | anclas del contexto en el ocupante y no en el destino: coincidencia de tema con el titulo |
| `02-ARQUITECTURA/RESEARCH-LINES.md:5683` | ``NNN`` | 128 | si | `contenido` | 229 | `NO_ES_CITA` | valor numerico de una tabla de campos, no un numero de hallazgo |
| `02-ARQUITECTURA/RX550-L0L3-INVENTORY/RX550-L0-L3-INVENTORY.md:13` | `NNN:LL` | 1000 | si | `numero` | 1004 | `NO_ES_CITA` | pareja UID:GID de un usuario, no un numero de hallazgo |
| `05-FUENTES-EXTERNAS/FASE-R0-EXTERNAL-KNOWLEDGE/R0-7-REFERENCIA-X86-64-LECTURA-DESENSAMBLADO.md:659` | ``NNN`` | 110 | si | `contenido` | 215 | `NO_ES_CITA` | codificacion ModRM/SIB o valor de udelay, no un numero de hallazgo; fichero ya declarado NO_CITA_FICHEROS en la puerta (gate:315-327) |
| `05-FUENTES-EXTERNAS/FASE-R0-EXTERNAL-KNOWLEDGE/R0-7-REFERENCIA-X86-64-LECTURA-DESENSAMBLADO.md:660` | ``NNN`` | 111 | si | `contenido` | 216 | `NO_ES_CITA` | codificacion ModRM/SIB o valor de udelay, no un numero de hallazgo; fichero ya declarado NO_CITA_FICHEROS en la puerta (gate:315-327) |
| `05-FUENTES-EXTERNAS/FASE-R0-EXTERNAL-KNOWLEDGE/R0-7-REFERENCIA-X86-64-LECTURA-DESENSAMBLADO.md:667` | ``NNN`` | 110 | si | `contenido` | 215 | `NO_ES_CITA` | codificacion ModRM/SIB o valor de udelay, no un numero de hallazgo; fichero ya declarado NO_CITA_FICHEROS en la puerta (gate:315-327) |
| `05-FUENTES-EXTERNAS/FASE-R0-EXTERNAL-KNOWLEDGE/R0-7-REFERENCIA-X86-64-LECTURA-DESENSAMBLADO.md:668` | ``NNN`` | 111 | si | `contenido` | 216 | `NO_ES_CITA` | codificacion ModRM/SIB o valor de udelay, no un numero de hallazgo; fichero ya declarado NO_CITA_FICHEROS en la puerta (gate:315-327) |
| `05-FUENTES-EXTERNAS/FASE-R0-EXTERNAL-KNOWLEDGE/R0-7-REFERENCIA-X86-64-LECTURA-DESENSAMBLADO.md:675` | ``NNN`` | 110 | si | `contenido` | 215 | `NO_ES_CITA` | codificacion ModRM/SIB o valor de udelay, no un numero de hallazgo; fichero ya declarado NO_CITA_FICHEROS en la puerta (gate:315-327) |
| `05-FUENTES-EXTERNAS/FASE-R0-EXTERNAL-KNOWLEDGE/R0-7-REFERENCIA-X86-64-LECTURA-DESENSAMBLADO.md:676` | ``NNN`` | 111 | si | `contenido` | 216 | `NO_ES_CITA` | codificacion ModRM/SIB o valor de udelay, no un numero de hallazgo; fichero ya declarado NO_CITA_FICHEROS en la puerta (gate:315-327) |
| `05-FUENTES-EXTERNAS/FASE-R0-EXTERNAL-KNOWLEDGE/R0-7-REFERENCIA-X86-64-LECTURA-DESENSAMBLADO.md:683` | ``NNN`` | 110 | si | `contenido` | 215 | `NO_ES_CITA` | codificacion ModRM/SIB o valor de udelay, no un numero de hallazgo; fichero ya declarado NO_CITA_FICHEROS en la puerta (gate:315-327) |
| `05-FUENTES-EXTERNAS/FASE-R0-EXTERNAL-KNOWLEDGE/R0-7-REFERENCIA-X86-64-LECTURA-DESENSAMBLADO.md:684` | ``NNN`` | 111 | si | `contenido` | 216 | `NO_ES_CITA` | codificacion ModRM/SIB o valor de udelay, no un numero de hallazgo; fichero ya declarado NO_CITA_FICHEROS en la puerta (gate:315-327) |
| `05-FUENTES-EXTERNAS/FASE-R0-EXTERNAL-KNOWLEDGE/R0-7-REFERENCIA-X86-64-LECTURA-DESENSAMBLADO.md:699` | ``NNN`` | 110 | si | `contenido` | 215 | `NO_ES_CITA` | codificacion ModRM/SIB o valor de udelay, no un numero de hallazgo; fichero ya declarado NO_CITA_FICHEROS en la puerta (gate:315-327) |
| `05-FUENTES-EXTERNAS/FASE-R0-EXTERNAL-KNOWLEDGE/R0-7-REFERENCIA-X86-64-LECTURA-DESENSAMBLADO.md:700` | ``NNN`` | 111 | si | `contenido` | 216 | `NO_ES_CITA` | codificacion ModRM/SIB o valor de udelay, no un numero de hallazgo; fichero ya declarado NO_CITA_FICHEROS en la puerta (gate:315-327) |
| `05-FUENTES-EXTERNAS/FASE-R0-EXTERNAL-KNOWLEDGE/R0-7-REFERENCIA-X86-64-LECTURA-DESENSAMBLADO.md:1304` | ``NNN`` | 1000 | si | `numero` | 1004 | `NO_ES_CITA` | codificacion ModRM/SIB o valor de udelay, no un numero de hallazgo; fichero ya declarado NO_CITA_FICHEROS en la puerta (gate:315-327) |
| `06-INGENIERIA-INVERSA/findings/044-xclk-fuentes-y-constantes-legacy.md:59` | ``NNN`` | 1000 | si | `numero` | 1004 | `NO_ES_CITA` | constante de reloj MUX_TCLK_TO_XCLK en milisegundos, no un numero de hallazgo |
| `06-INGENIERIA-INVERSA/findings/047-el-handler-si-lee-src-data.md:6` | `NNN:LL` | 52 | si | `contenido` | 193 | `CORRECTA_APUNTA_AL_OCUPANTE` | anclas del contexto en el ocupante y no en el destino: coincidencia de tema con el titulo |
| `06-INGENIERIA-INVERSA/findings/047-el-handler-si-lee-src-data.md:109` | `NNN:LL` | 52 | si | `contenido` | 193 | `CORRECTA_APUNTA_AL_OCUPANTE` | anclas del contexto en el ocupante y no en el destino: coincidencia de tema con el titulo |
| `06-INGENIERIA-INVERSA/findings/047-el-handler-si-lee-src-data.md:110` | `NNN:LL` | 52 | si | `contenido` | 193 | `CORRECTA_APUNTA_AL_OCUPANTE` | anclas del contexto en el ocupante y no en el destino: ['src_id'] |
| `06-INGENIERIA-INVERSA/findings/047-el-handler-si-lee-src-data.md:145` | `NNN:LL` | 52 | si | `contenido` | 193 | `CORRECTA_APUNTA_AL_OCUPANTE` | anclas del contexto en el ocupante y no en el destino: coincidencia de tema con el titulo |
| `06-INGENIERIA-INVERSA/findings/047-el-handler-si-lee-src-data.md:197` | `NNN:LL` | 52 | si | `contenido` | 193 | `CORRECTA_APUNTA_AL_OCUPANTE` | anclas del contexto en el ocupante y no en el destino: ['src_id'] |
| `06-INGENIERIA-INVERSA/findings/047-el-handler-si-lee-src-data.md:207` | `NNN:LL` | 52 | si | `contenido` | 193 | `CORRECTA_APUNTA_AL_OCUPANTE` | anclas del contexto en el ocupante y no en el destino: coincidencia de tema con el titulo |
| `06-INGENIERIA-INVERSA/findings/047-el-handler-si-lee-src-data.md:228` | `NNN:LL` | 52 | si | `contenido` | 193 | `CORRECTA_APUNTA_AL_OCUPANTE` | anclas del contexto en el ocupante y no en el destino: coincidencia de tema con el titulo |
| `06-INGENIERIA-INVERSA/findings/067-cadena-gart-256m-y-tabla-en-vram.md:118` | `NNN:LL` | 88 | si | `contenido` | 195 | `CORRECTA_APUNTA_AL_OCUPANTE` | anclas del contexto en el ocupante y no en el destino: coincidencia de tema con el titulo |
| `06-INGENIERIA-INVERSA/findings/089-gc-hwip-bloqueado-por-capacidad-y-resuelto-estaticamente.md:124` | ``NNN`` | 89 | si | `contenido` | 196 | `CORRECTA_AUTOCITA_OCUPANTE` | la cita esta dentro del fichero que hoy lleva ese numero: correcta por construccion (citas_prosa_census.py:536-545) |
| `06-INGENIERIA-INVERSA/findings/089-gc-hwip-bloqueado-por-capacidad-y-resuelto-estaticamente.md:145` | ``NNN`` | 89 | si | `contenido` | 196 | `CORRECTA_AUTOCITA_OCUPANTE` | la cita esta dentro del fichero que hoy lleva ese numero: correcta por construccion (citas_prosa_census.py:536-545) |
| `06-INGENIERIA-INVERSA/findings/1000-de-pci-enumeration-a-gpu-ready-la-secuencia-completa.md:434` | `findings/NNN` | 202 | si | `contenido` | 242 | `CORRECTA_APUNTA_AL_OCUPANTE` | anclas del contexto en el ocupante y no en el destino: coincidencia de tema con el titulo |
| `06-INGENIERIA-INVERSA/findings/1000-de-pci-enumeration-a-gpu-ready-la-secuencia-completa.md:437` | `findings/NNN` | 163 | si | `contenido` | 233 | `CORRECTA_APUNTA_AL_OCUPANTE` | anclas del contexto en el ocupante y no en el destino: coincidencia de tema con el titulo |
| `06-INGENIERIA-INVERSA/findings/1004-eng-invalidate-es-gfx9-y-no-gfx8.md:379` | ``NNN`` | 1003 | si | `numero` | 1005 | `CORRECTA_META_RENUMERACION` | el contexto declara el renumerado (nombra el numero nuevo o una palabra de renumerado) |
| `06-INGENIERIA-INVERSA/findings/1004-eng-invalidate-es-gfx9-y-no-gfx8.md:383` | ``NNN`` | 1003 | si | `numero` | 1005 | `CORRECTA_APUNTA_AL_OCUPANTE` | anclas del contexto en el ocupante y no en el destino: coincidencia de tema con el titulo |
| `06-INGENIERIA-INVERSA/findings/1004-eng-invalidate-es-gfx9-y-no-gfx8.md:392` | ``NNN`` | 1000 | si | `numero` | 1004 | `CORRECTA_AUTOCITA_DESTINO` | la cita esta dentro del fichero destino del renumerado y habla del numero viejo |
| `06-INGENIERIA-INVERSA/findings/1004-eng-invalidate-es-gfx9-y-no-gfx8.md:412` | ``NNN`` | 1003 | si | `numero` | 1005 | `CORRECTA_META_RENUMERACION` | el contexto declara el renumerado (nombra el numero nuevo o una palabra de renumerado) |
| `06-INGENIERIA-INVERSA/findings/1005-la-telemetria-mmio-devuelve-ebusy-con-la-gpu-suspendida.md:234` | ``NNN`` | 1003 | si | `numero` | 1005 | `CORRECTA_AUTOCITA_DESTINO` | la cita esta dentro del fichero destino del renumerado y habla del numero viejo |
| `06-INGENIERIA-INVERSA/findings/1010-el-limite-de-paginas-de-ttm-que-amdgpu-imprime-como-5907m.md:285` | ``NNN`` | 1000 | si | `numero` | 1004 | `RESUELVE_AL_OCUPANTE_NO_VERIFICADA` | el numero 1000 es UNICO hoy, luego la cita resuelve al ocupante; el contexto no lleva contenido que la confirme o la refute |
| `06-INGENIERIA-INVERSA/findings/104-once-usos-de-dpm-table-start-y-el-hueco-de-108.md:171` | ``NNN`` | 104 | si | `contenido` | 211 | `CORRECTA_AUTOCITA_OCUPANTE` | la cita esta dentro del fichero que hoy lleva ese numero: correcta por construccion (citas_prosa_census.py:536-545) |
| `06-INGENIERIA-INVERSA/findings/104-once-usos-de-dpm-table-start-y-el-hueco-de-108.md:378` | ``NNN`` | 104 | si | `contenido` | 211 | `CORRECTA_AUTOCITA_OCUPANTE` | la cita esta dentro del fichero que hoy lleva ese numero: correcta por construccion (citas_prosa_census.py:536-545) |
| `06-INGENIERIA-INVERSA/findings/104-once-usos-de-dpm-table-start-y-el-hueco-de-108.md:441` | ``NNN`` | 104 | si | `contenido` | 211 | `CORRECTA_AUTOCITA_OCUPANTE` | la cita esta dentro del fichero que hoy lleva ese numero: correcta por construccion (citas_prosa_census.py:536-545) |
| `06-INGENIERIA-INVERSA/findings/1040-una-tabla-con-dos-relaciones-distintas-bajo-el-mismo-nombre-de-columna.md:33` | ``NNN`` | 267 | si | `numero` | 271 | `CORRECTA_META_RENUMERACION` | el contexto declara el renumerado (nombra el numero nuevo o una palabra de renumerado) |
| `06-INGENIERIA-INVERSA/findings/1040-una-tabla-con-dos-relaciones-distintas-bajo-el-mismo-nombre-de-columna.md:63` | ``NNN`` | 267 | si | `numero` | 271 | `CORRECTA_APUNTA_AL_OCUPANTE` | anclas del contexto en el ocupante y no en el destino: coincidencia de tema con el titulo |
| `06-INGENIERIA-INVERSA/findings/1040-una-tabla-con-dos-relaciones-distintas-bajo-el-mismo-nombre-de-columna.md:68` | ``NNN`` | 267 | si | `numero` | 271 | `CORRECTA_APUNTA_AL_OCUPANTE` | anclas del contexto en el ocupante y no en el destino: coincidencia de tema con el titulo |
| `06-INGENIERIA-INVERSA/findings/1040-una-tabla-con-dos-relaciones-distintas-bajo-el-mismo-nombre-de-columna.md:71` | ``NNN`` | 267 | si | `numero` | 271 | `CORRECTA_APUNTA_AL_OCUPANTE` | anclas del contexto en el ocupante y no en el destino: coincidencia de tema con el titulo |
| `06-INGENIERIA-INVERSA/findings/1040-una-tabla-con-dos-relaciones-distintas-bajo-el-mismo-nombre-de-columna.md:74` | ``NNN`` | 267 | si | `numero` | 271 | `CORRECTA_APUNTA_AL_OCUPANTE` | anclas del contexto en el ocupante y no en el destino: coincidencia de tema con el titulo |
| `06-INGENIERIA-INVERSA/findings/1040-una-tabla-con-dos-relaciones-distintas-bajo-el-mismo-nombre-de-columna.md:109` | ``NNN`` | 267 | si | `numero` | 271 | `CORRECTA_APUNTA_AL_OCUPANTE` | anclas del contexto en el ocupante y no en el destino: coincidencia de tema con el titulo |
| `06-INGENIERIA-INVERSA/findings/123-e-cuadra-cuando-se-llama-hdp-flush.md:246` | ``NNN`` | 123 | si | `contenido` | 225 | `CORRECTA_AUTOCITA_OCUPANTE` | la cita esta dentro del fichero que hoy lleva ese numero: correcta por construccion (citas_prosa_census.py:536-545) |
| `06-INGENIERIA-INVERSA/findings/126-g-el-precio-de-la-coherencia.md:204` | ``NNN`` | 126 | si | `contenido` | 228 | `CORRECTA_AUTOCITA_OCUPANTE` | la cita esta dentro del fichero que hoy lleva ese numero: correcta por construccion (citas_prosa_census.py:536-545) |
| `06-INGENIERIA-INVERSA/findings/134-que-se-puede-ver-sin-root-y-que-no.md:107` | `NNN:LL` | 116 | si | `contenido` | 220 | `RESUELVE_AL_OCUPANTE_NO_VERIFICADA` | el numero 116 es UNICO hoy, luego la cita resuelve al ocupante; el contexto no lleva contenido que la confirme o la refute |
| `06-INGENIERIA-INVERSA/findings/144-prt-cierra-y-el-corpus-no-tiene-uapi.md:162` | ``NNN`` | 144 | si | `contenido` | 231 | `CORRECTA_AUTOCITA_OCUPANTE` | la cita esta dentro del fichero que hoy lleva ese numero: correcta por construccion (citas_prosa_census.py:536-545) |
| `06-INGENIERIA-INVERSA/findings/168-el-formato-termino-para-comprobar-citas.md:155` | `findings/NNN` | 167 | si | `contenido` | 234 | `RESUELVE_AL_OCUPANTE_NO_VERIFICADA` | el numero 167 es UNICO hoy, luego la cita resuelve al ocupante; el contexto no lleva contenido que la confirme o la refute |
| `06-INGENIERIA-INVERSA/findings/169-los-cinco-sitios-de-full-visible-vivos.md:177` | ``NNN`` | 169 | si | `contenido` | 236 | `CORRECTA_AUTOCITA_OCUPANTE` | la cita esta dentro del fichero que hoy lleva ese numero: correcta por construccion (citas_prosa_census.py:536-545) |
| `06-INGENIERIA-INVERSA/findings/180-las-ocho-direcciones-de-registro-con-su-linea-en-el-asic.md:151` | `findings/NNN` | 176 | si | `contenido` | 237 | `CORRECTA_APUNTA_AL_OCUPANTE` | anclas del contexto en el ocupante y no en el destino: coincidencia de tema con el titulo |
| `06-INGENIERIA-INVERSA/findings/180-las-ocho-direcciones-de-registro-con-su-linea-en-el-asic.md:178` | `findings/NNN` | 176 | si | `contenido` | 237 | `CORRECTA_APUNTA_AL_OCUPANTE` | anclas del contexto en el ocupante y no en el destino: coincidencia de tema con el titulo |
| `06-INGENIERIA-INVERSA/findings/186-685-afirmaciones-abiertas-no-era-un-resultado.md:129` | `findings/NNN` | 167 | si | `contenido` | 234 | `RESUELVE_AL_OCUPANTE_NO_VERIFICADA` | el numero 167 es UNICO hoy, luego la cita resuelve al ocupante; el contexto no lleva contenido que la confirme o la refute |
| `06-INGENIERIA-INVERSA/findings/196-codificacion-de-frecuencia-de-reloj-punto-fijo.md:164` | ``NNN`` | 1000 | si | `numero` | 1004 | `NO_ES_CITA` | constante de reloj MUX_TCLK_TO_XCLK, no un numero de hallazgo |
| `06-INGENIERIA-INVERSA/findings/196-codificacion-de-frecuencia-de-reloj-punto-fijo.md:237` | ``NNN`` | 1000 | si | `numero` | 1004 | `NO_ES_CITA` | valor de frecuencia de reloj (1000 = 1 GHz escalado), no un numero de hallazgo |
| `06-INGENIERIA-INVERSA/findings/197-la-colision-de-nombres-en-kbuild-que-pierde-codigo-sin-decir-nada.md:98` | `NNN:LL` | 114 | si | `contenido` | 219 | `CORRECTA_APUNTA_AL_OCUPANTE` | anclas del contexto en el ocupante y no en el destino: coincidencia de tema con el titulo |
| `06-INGENIERIA-INVERSA/findings/197-la-colision-de-nombres-en-kbuild-que-pierde-codigo-sin-decir-nada.md:99` | `NNN:LL` | 114 | si | `contenido` | 219 | `CORRECTA_APUNTA_AL_OCUPANTE` | anclas del contexto en el ocupante y no en el destino: coincidencia de tema con el titulo |
| `06-INGENIERIA-INVERSA/findings/197-la-colision-de-nombres-en-kbuild-que-pierde-codigo-sin-decir-nada.md:99` | `NNN:LL` | 189 | si | `contenido` | 241 | `RESUELVE_AL_OCUPANTE_NO_VERIFICADA` | el numero 189 es UNICO hoy, luego la cita resuelve al ocupante; el contexto no lleva contenido que la confirme o la refute |
| `06-INGENIERIA-INVERSA/findings/197-la-colision-de-nombres-en-kbuild-que-pierde-codigo-sin-decir-nada.md:158` | `findings/NNN` | 176 | si | `contenido` | 237 | `CORRECTA_APUNTA_AL_OCUPANTE` | anclas del contexto en el ocupante y no en el destino: coincidencia de tema con el titulo |
| `06-INGENIERIA-INVERSA/findings/202-la-ventana-de-registros-es-bar5-y-el-log-lo-dice.md:108` | `findings/NNN` | 202 | si | `contenido` | 242 | `CORRECTA_AUTOCITA_OCUPANTE` | la cita esta dentro del fichero que hoy lleva ese numero: correcta por construccion (citas_prosa_census.py:536-545) |
| `06-INGENIERIA-INVERSA/findings/202-la-ventana-de-registros-es-bar5-y-el-log-lo-dice.md:296` | `findings/NNN` | 176 | si | `contenido` | 237 | `CORRECTA_APUNTA_AL_OCUPANTE` | anclas del contexto en el ocupante y no en el destino: coincidencia de tema con el titulo |
| `06-INGENIERIA-INVERSA/findings/245-cien-numeros-de-hallazgo-duplicados-y-la-reserva-no-atomica.md:32` | `findings/NNN` | 176 | si | `contenido` | 237 | `CORRECTA_APUNTA_AL_OCUPANTE` | anclas del contexto en el ocupante y no en el destino: coincidencia de tema con el titulo |
| `06-INGENIERIA-INVERSA/findings/245-cien-numeros-de-hallazgo-duplicados-y-la-reserva-no-atomica.md:74` | `findings/NNN` | 202 | si | `contenido` | 242 | `CORRECTA_META_RENUMERACION` | el contexto declara el renumerado (nombra el numero nuevo o una palabra de renumerado) |
| `06-INGENIERIA-INVERSA/findings/245-cien-numeros-de-hallazgo-duplicados-y-la-reserva-no-atomica.md:175` | `findings/NNN` | 202 | si | `contenido` | 242 | `CORRECTA_META_RENUMERACION` | el contexto declara el renumerado (nombra el numero nuevo o una palabra de renumerado) |
| `06-INGENIERIA-INVERSA/findings/250-la-herramienta-que-decia-22-discriminantes-cuando-eran-cero.md:34` | `NNN:LL` | 163 | si | `contenido` | 233 | `CORRECTA_APUNTA_AL_OCUPANTE` | anclas del contexto en el ocupante y no en el destino: coincidencia de tema con el titulo |
| `06-INGENIERIA-INVERSA/findings/250-la-herramienta-que-decia-22-discriminantes-cuando-eran-cero.md:231` | `findings/NNN` | 163 | si | `contenido` | 233 | `CORRECTA_APUNTA_AL_OCUPANTE` | anclas del contexto en el ocupante y no en el destino: coincidencia de tema con el titulo |
| `06-INGENIERIA-INVERSA/findings/266-la-codificacion-del-voltaje-no-es-un-float-y-el-avfs-la-incumple.md:123` | ``NNN`` | 267 | si | `numero` | 271 | `CORRECTA_APUNTA_AL_OCUPANTE` | anclas del contexto en el ocupante y no en el destino: coincidencia de tema con el titulo |
| `06-INGENIERIA-INVERSA/findings/266-la-codificacion-del-voltaje-no-es-un-float-y-el-avfs-la-incumple.md:125` | ``NNN`` | 267 | si | `numero` | 271 | `CORRECTA_APUNTA_AL_OCUPANTE` | anclas del contexto en el ocupante y no en el destino: coincidencia de tema con el titulo |
| `06-INGENIERIA-INVERSA/findings/269-el-techo-de-reloj-no-viene-de-la-tabla-de-voltajes.md:7` | ``NNN`` | 267 | si | `numero` | 271 | `CORRECTA_APUNTA_AL_OCUPANTE` | anclas del contexto en el ocupante y no en el destino: coincidencia de tema con el titulo |
| `06-INGENIERIA-INVERSA/findings/269-el-techo-de-reloj-no-viene-de-la-tabla-de-voltajes.md:44` | ``NNN`` | 267 | si | `numero` | 271 | `CORRECTA_APUNTA_AL_OCUPANTE` | anclas del contexto en el ocupante y no en el destino: coincidencia de tema con el titulo |
| `06-INGENIERIA-INVERSA/findings/269-el-techo-de-reloj-no-viene-de-la-tabla-de-voltajes.md:161` | ``NNN`` | 267 | si | `numero` | 271 | `CORRECTA_APUNTA_AL_OCUPANTE` | anclas del contexto en el ocupante y no en el destino: ['MinVoltage'] |
| `06-INGENIERIA-INVERSA/findings/269-el-techo-de-reloj-no-viene-de-la-tabla-de-voltajes.md:163` | ``NNN`` | 267 | si | `numero` | 271 | `CORRECTA_APUNTA_AL_OCUPANTE` | anclas del contexto en el ocupante y no en el destino: ['ucVddInd'] |
| `06-INGENIERIA-INVERSA/findings/269-el-techo-de-reloj-no-viene-de-la-tabla-de-voltajes.md:207` | ``NNN`` | 267 | si | `numero` | 271 | `CORRECTA_APUNTA_AL_OCUPANTE` | anclas del contexto en el ocupante y no en el destino: coincidencia de tema con el titulo |
| `06-INGENIERIA-INVERSA/findings/271-el-kernel-de-cache-mide-la-tasa-de-emision.md:11` | ``NNN`` | 267 | si | `numero` | 271 | `CORRECTA_AUTOCITA_DESTINO` | la cita esta dentro del fichero destino del renumerado y habla del numero viejo |
| `06-INGENIERIA-INVERSA/findings/272-el-techo-de-overdrive-sale-de-una-lectura-fuera-de-rango.md:125` | ``NNN`` | 267 | si | `numero` | 271 | `CORRECTA_APUNTA_AL_OCUPANTE` | anclas del contexto en el ocupante y no en el destino: coincidencia de tema con el titulo |
| `06-INGENIERIA-INVERSA/findings/272-el-techo-de-overdrive-sale-de-una-lectura-fuera-de-rango.md:153` | ``NNN`` | 267 | si | `numero` | 271 | `CORRECTA_APUNTA_AL_OCUPANTE` | anclas del contexto en el ocupante y no en el destino: ['ulSclk'] |
| `06-INGENIERIA-INVERSA/findings/272-el-techo-de-overdrive-sale-de-una-lectura-fuera-de-rango.md:154` | ``NNN`` | 267 | si | `numero` | 271 | `CORRECTA_APUNTA_AL_OCUPANTE` | anclas del contexto en el ocupante y no en el destino: ['MinVoltage'] |
| `06-INGENIERIA-INVERSA/findings/276-me-offset-leia-fuera-del-buffer-de-especializacion.md:164` | ``NNN`` | 267 | si | `numero` | 271 | `CORRECTA_APUNTA_AL_OCUPANTE` | anclas del contexto en el ocupante y no en el destino: coincidencia de tema con el titulo |
| `06-INGENIERIA-INVERSA/findings/277-la-cadena-dependiente-no-expone-la-memoria-aunque-valide.md:177` | ``NNN`` | 267 | si | `numero` | 271 | `CORRECTA_APUNTA_AL_OCUPANTE` | anclas del contexto en el ocupante y no en el destino: coincidencia de tema con el titulo |
| `06-INGENIERIA-INVERSA/findings/281-el-bucle-si-se-ejecuta-pero-alinea-90-veces.md:176` | ``NNN`` | 267 | si | `numero` | 271 | `CORRECTA_APUNTA_AL_OCUPANTE` | anclas del contexto en el ocupante y no en el destino: coincidencia de tema con el titulo |
| `06-INGENIERIA-INVERSA/findings/287-la-lectura-si-costaba-su-latencia-443-ciclos.md:45` | ``NNN`` | 286 | si | `contenido` | 401 | `RESUELVE_AL_OCUPANTE_NO_VERIFICADA` | el numero 286 es UNICO hoy, luego la cita resuelve al ocupante; el contexto no lleva contenido que la confirme o la refute |
| `06-INGENIERIA-INVERSA/findings/287-la-lectura-si-costaba-su-latencia-443-ciclos.md:185` | ``NNN`` | 286 | si | `contenido` | 401 | `RESUELVE_AL_OCUPANTE_NO_VERIFICADA` | el numero 286 es UNICO hoy, luego la cita resuelve al ocupante; el contexto no lleva contenido que la confirme o la refute |
| `06-INGENIERIA-INVERSA/findings/289-la-cache-retiene-entre-256-y-320-kib.md:154` | ``NNN`` | 286 | si | `contenido` | 401 | `RESUELVE_AL_OCUPANTE_NO_VERIFICADA` | el numero 286 es UNICO hoy, luego la cita resuelve al ocupante; el contexto no lleva contenido que la confirme o la refute |
| `06-INGENIERIA-INVERSA/findings/309-el-allocator-no-veia-los-numeros-de-cuatro-cifras.md:113` | ``NNN`` | 1000 | si | `numero` | 1004 | `RESUELVE_AL_OCUPANTE_NO_VERIFICADA` | el numero 1000 es UNICO hoy, luego la cita resuelve al ocupante; el contexto no lleva contenido que la confirme o la refute |
| `06-INGENIERIA-INVERSA/findings/400-el-resumen-y-el-aviso-tienen-vector.md:146` | ``NNN`` | 290 | si | `numero/numero` | 291,400 | `CORRECTA_AUTOCITA_DESTINO` | la cita esta dentro del fichero destino del renumerado y habla del numero viejo |
| `06-INGENIERIA-INVERSA/findings/400-el-resumen-y-el-aviso-tienen-vector.md:147` | ``NNN`` | 290 | si | `numero/numero` | 291,400 | `CORRECTA_AUTOCITA_DESTINO` | la cita esta dentro del fichero destino del renumerado y habla del numero viejo |
| `06-INGENIERIA-INVERSA/findings/400-el-resumen-y-el-aviso-tienen-vector.md:253` | ``NNN`` | 280 | si | `numero` | 288,288 | `CORRECTA_META_RENUMERACION` | el contexto declara el renumerado (nombra el numero nuevo o una palabra de renumerado) |
| `06-INGENIERIA-INVERSA/findings/400-el-resumen-y-el-aviso-tienen-vector.md:301` | ``NNN`` | 286 | si | `contenido` | 401 | `RESUELVE_AL_OCUPANTE_NO_VERIFICADA` | el numero 286 es UNICO hoy, luego la cita resuelve al ocupante; el contexto no lleva contenido que la confirme o la refute |
| `06-INGENIERIA-INVERSA/findings/401-doclint-no-indexaba-07-driver.md:195` | ``NNN`` | 286 | si | `contenido` | 401 | `CORRECTA_AUTOCITA_DESTINO` | la cita esta dentro del fichero destino del renumerado y habla del numero viejo |
| `06-INGENIERIA-INVERSA/findings/402-tapada-0-no-era-un-resultado-y-ya-no-lo-es.md:193` | ``NNN`` | 280 | si | `numero` | 288,288 | `RESUELVE_AL_OCUPANTE_NO_VERIFICADA` | el numero 280 es UNICO hoy, luego la cita resuelve al ocupante; el contexto no lleva contenido que la confirme o la refute |
| `06-INGENIERIA-INVERSA/findings/402-tapada-0-no-era-un-resultado-y-ya-no-lo-es.md:197` | ``NNN`` | 280 | si | `numero` | 288,288 | `RESUELVE_AL_OCUPANTE_NO_VERIFICADA` | el numero 280 es UNICO hoy, luego la cita resuelve al ocupante; el contexto no lleva contenido que la confirme o la refute |
| `06-INGENIERIA-INVERSA/findings/500-el-shadow-de-los-contadores-y-el-mensaje-que-acusa.md:9` | ``NNN`` | 280 | si | `numero` | 288,288 | `RESUELVE_AL_OCUPANTE_NO_VERIFICADA` | el numero 280 es UNICO hoy, luego la cita resuelve al ocupante; el contexto no lleva contenido que la confirme o la refute |
| `06-INGENIERIA-INVERSA/findings/500-el-shadow-de-los-contadores-y-el-mensaje-que-acusa.md:14` | ``NNN`` | 280 | si | `numero` | 288,288 | `RESUELVE_AL_OCUPANTE_NO_VERIFICADA` | el numero 280 es UNICO hoy, luego la cita resuelve al ocupante; el contexto no lleva contenido que la confirme o la refute |
| `06-INGENIERIA-INVERSA/findings/500-el-shadow-de-los-contadores-y-el-mensaje-que-acusa.md:70` | ``NNN`` | 280 | si | `numero` | 288,288 | `RESUELVE_AL_OCUPANTE_NO_VERIFICADA` | el numero 280 es UNICO hoy, luego la cita resuelve al ocupante; el contexto no lleva contenido que la confirme o la refute |
| `06-INGENIERIA-INVERSA/findings/500-el-shadow-de-los-contadores-y-el-mensaje-que-acusa.md:70` | ``NNN`` | 280 | si | `numero` | 288,288 | `RESUELVE_AL_OCUPANTE_NO_VERIFICADA` | el numero 280 es UNICO hoy, luego la cita resuelve al ocupante; el contexto no lleva contenido que la confirme o la refute |
| `06-INGENIERIA-INVERSA/findings/500-el-shadow-de-los-contadores-y-el-mensaje-que-acusa.md:143` | ``NNN`` | 280 | si | `numero` | 288,288 | `RESUELVE_AL_OCUPANTE_NO_VERIFICADA` | el numero 280 es UNICO hoy, luego la cita resuelve al ocupante; el contexto no lleva contenido que la confirme o la refute |
| `06-INGENIERIA-INVERSA/findings/501-el-hueco-de-la-forma-c-es-real-y-no-es-de-mi-asic.md:213` | ``NNN`` | 267 | si | `numero` | 271 | `CORRECTA_APUNTA_AL_OCUPANTE` | anclas del contexto en el ocupante y no en el destino: coincidencia de tema con el titulo |
| `06-INGENIERIA-INVERSA/findings/502-quien-escribe-cada-byte-de-los-1776.md:105` | ``NNN`` | 267 | si | `numero` | 271 | `CORRECTA_APUNTA_AL_OCUPANTE` | anclas del contexto en el ocupante y no en el destino: coincidencia de tema con el titulo |
| `06-INGENIERIA-INVERSA/findings/550-la-tabla-pcie-esta-empaquetada-y-el-struct-no.md:177` | ``NNN`` | 267 | si | `numero` | 271 | `CORRECTA_APUNTA_AL_OCUPANTE` | anclas del contexto en el ocupante y no en el destino: coincidencia de tema con el titulo |
| `06-INGENIERIA-INVERSA/findings/550-la-tabla-pcie-esta-empaquetada-y-el-struct-no.md:187` | ``NNN`` | 267 | si | `numero` | 271 | `CORRECTA_APUNTA_AL_OCUPANTE` | anclas del contexto en el ocupante y no en el destino: coincidencia de tema con el titulo |
| `06-INGENIERIA-INVERSA/findings/600-un-orden-que-sabe-decir-que-no.md:193` | ``NNN`` | 280 | si | `numero` | 288,288 | `RESUELVE_AL_OCUPANTE_NO_VERIFICADA` | el numero 280 es UNICO hoy, luego la cita resuelve al ocupante; el contexto no lleva contenido que la confirme o la refute |
| `06-INGENIERIA-INVERSA/findings/602-la-cadena-colapsa-y-el-techo-de-vram-estaba-en-la-mitad.md:137` | ``NNN`` | 290 | si | `numero/numero` | 291,400 | `CORRECTA_APUNTA_AL_OCUPANTE` | anclas del contexto en el ocupante y no en el destino: coincidencia de tema con el titulo |
| `06-INGENIERIA-INVERSA/findings/602-la-cadena-colapsa-y-el-techo-de-vram-estaba-en-la-mitad.md:258` | ``NNN`` | 286 | si | `contenido` | 401 | `RESUELVE_AL_OCUPANTE_NO_VERIFICADA` | el numero 286 es UNICO hoy, luego la cita resuelve al ocupante; el contexto no lleva contenido que la confirme o la refute |
| `06-INGENIERIA-INVERSA/findings/603-la-tabla-dpm-no-tiene-relleno-y-502-queda.md:18` | ``NNN`` | 267 | si | `numero` | 271 | `CORRECTA_APUNTA_AL_OCUPANTE` | anclas del contexto en el ocupante y no en el destino: coincidencia de tema con el titulo |
| `06-INGENIERIA-INVERSA/findings/603-la-tabla-dpm-no-tiene-relleno-y-502-queda.md:18` | ``NNN`` | 267 | si | `numero` | 271 | `CORRECTA_APUNTA_AL_OCUPANTE` | anclas del contexto en el ocupante y no en el destino: coincidencia de tema con el titulo |
| `06-INGENIERIA-INVERSA/findings/603-la-tabla-dpm-no-tiene-relleno-y-502-queda.md:75` | ``NNN`` | 267 | si | `numero` | 271 | `CORRECTA_APUNTA_AL_OCUPANTE` | anclas del contexto en el ocupante y no en el destino: coincidencia de tema con el titulo |
| `06-INGENIERIA-INVERSA/findings/603-la-tabla-dpm-no-tiene-relleno-y-502-queda.md:79` | ``NNN`` | 267 | si | `numero` | 271 | `CORRECTA_APUNTA_AL_OCUPANTE` | anclas del contexto en el ocupante y no en el destino: coincidencia de tema con el titulo |
| `06-INGENIERIA-INVERSA/findings/603-la-tabla-dpm-no-tiene-relleno-y-502-queda.md:88` | ``NNN`` | 267 | si | `numero` | 271 | `CORRECTA_APUNTA_AL_OCUPANTE` | anclas del contexto en el ocupante y no en el destino: coincidencia de tema con el titulo |
| `06-INGENIERIA-INVERSA/findings/603-la-tabla-dpm-no-tiene-relleno-y-502-queda.md:89` | ``NNN`` | 267 | si | `numero` | 271 | `CORRECTA_APUNTA_AL_OCUPANTE` | anclas del contexto en el ocupante y no en el destino: coincidencia de tema con el titulo |
| `06-INGENIERIA-INVERSA/findings/603-la-tabla-dpm-no-tiene-relleno-y-502-queda.md:104` | ``NNN`` | 267 | si | `numero` | 271 | `CORRECTA_APUNTA_AL_OCUPANTE` | anclas del contexto en el ocupante y no en el destino: coincidencia de tema con el titulo |
| `06-INGENIERIA-INVERSA/findings/604-una-contradiccion-y-una-premisa-sin-verificar.md:45` | ``NNN`` | 267 | si | `numero` | 271 | `CORRECTA_APUNTA_AL_OCUPANTE` | anclas del contexto en el ocupante y no en el destino: ['0x9D15'] |
| `06-INGENIERIA-INVERSA/findings/604-una-contradiccion-y-una-premisa-sin-verificar.md:49` | ``NNN`` | 267 | si | `numero` | 271 | `CORRECTA_APUNTA_AL_OCUPANTE` | anclas del contexto en el ocupante y no en el destino: ['0x9D15'] |
| `06-INGENIERIA-INVERSA/findings/605-la-ruta-legacy-si-es-la-viva-por-agotamiento.md:137` | ``NNN`` | 267 | si | `numero` | 271 | `CORRECTA_APUNTA_AL_OCUPANTE` | anclas del contexto en el ocupante y no en el destino: coincidencia de tema con el titulo |
| `06-INGENIERIA-INVERSA/findings/606-el-acantonado-del-bar-a-256-mib-y-un-flag-muerto.md:61` | ``NNN`` | 286 | si | `contenido` | 401 | `RESUELVE_AL_OCUPANTE_NO_VERIFICADA` | el numero 286 es UNICO hoy, luego la cita resuelve al ocupante; el contexto no lleva contenido que la confirme o la refute |
| `06-INGENIERIA-INVERSA/findings/606-el-acantonado-del-bar-a-256-mib-y-un-flag-muerto.md:86` | ``NNN`` | 286 | si | `contenido` | 401 | `RESUELVE_AL_OCUPANTE_NO_VERIFICADA` | el numero 286 es UNICO hoy, luego la cita resuelve al ocupante; el contexto no lleva contenido que la confirme o la refute |
| `06-INGENIERIA-INVERSA/findings/607-el-control-que-le-faltaba-al-banco.md:84` | ``NNN`` | 286 | si | `contenido` | 401 | `RESUELVE_AL_OCUPANTE_NO_VERIFICADA` | el numero 286 es UNICO hoy, luego la cita resuelve al ocupante; el contexto no lleva contenido que la confirme o la refute |
| `06-INGENIERIA-INVERSA/findings/943-setenta-numeros-de-nota-duplicados.md:110` | ``NNN`` | 941 | si | `numero` | 942 | `CORRECTA_META_RENUMERACION` | el contexto declara el renumerado (nombra el numero nuevo o una palabra de renumerado) |
| `06-INGENIERIA-INVERSA/findings/943-setenta-numeros-de-nota-duplicados.md:111` | ``NNN`` | 941 | si | `numero` | 942 | `CORRECTA_META_RENUMERACION` | el contexto declara el renumerado (nombra el numero nuevo o una palabra de renumerado) |
| `06-INGENIERIA-INVERSA/findings/944-el-mecanismo-existe-y-429-notas-no-lo-usan.md:47` | ``NNN`` | 941 | si | `numero` | 942 | `CORRECTA_META_RENUMERACION` | el contexto declara el renumerado (nombra el numero nuevo o una palabra de renumerado) |
| `06-INGENIERIA-INVERSA/findings/947-contradiccion-con-931-ro-va-de-1100-a-2100.md:259` | ``NNN`` | 941 | si | `numero` | 942 | `CORRECTA_APUNTA_AL_OCUPANTE` | anclas del contexto en el ocupante y no en el destino: coincidencia de tema con el titulo |
| `06-INGENIERIA-INVERSA/findings/948-camino-cerrado-y-fallo-de-tres-digitos-arreglado.md:9` | ``NNN`` | 944 | si | `numero` | 947 | `CORRECTA_APUNTA_AL_OCUPANTE` | anclas del contexto en el ocupante y no en el destino: coincidencia de tema con el titulo |
| `06-INGENIERIA-INVERSA/findings/948-camino-cerrado-y-fallo-de-tres-digitos-arreglado.md:20` | ``NNN`` | 1000 | si | `numero` | 1004 | `RESUELVE_AL_OCUPANTE_NO_VERIFICADA` | el numero 1000 es UNICO hoy, luego la cita resuelve al ocupante; el contexto no lleva contenido que la confirme o la refute |
| `06-INGENIERIA-INVERSA/findings/953-gpu-load-es-average-graphics-activity.md:159` | ``NNN`` | 941 | si | `numero` | 942 | `CORRECTA_APUNTA_AL_OCUPANTE` | anclas del contexto en el ocupante y no en el destino: coincidencia de tema con el titulo |
| `06-INGENIERIA-INVERSA/findings/953-gpu-load-es-average-graphics-activity.md:193` | ``NNN`` | 941 | si | `numero` | 942 | `CORRECTA_APUNTA_AL_OCUPANTE` | anclas del contexto en el ocupante y no en el destino: ['ATOM_Tonga_PowerTune_Table'] |
| `06-INGENIERIA-INVERSA/findings/956-ro-son-8-bits-de-la-efusiva.md:162` | ``NNN`` | 941 | si | `numero` | 942 | `CORRECTA_APUNTA_AL_OCUPANTE` | anclas del contexto en el ocupante y no en el destino: coincidencia de tema con el titulo |
| `06-INGENIERIA-INVERSA/findings/958-la-huella-no-se-satura-la-hipotesis-refutada.md:99` | ``NNN`` | 944 | si | `numero` | 947 | `CORRECTA_APUNTA_AL_OCUPANTE` | anclas del contexto en el ocupante y no en el destino: coincidencia de tema con el titulo |
| `06-INGENIERIA-INVERSA/findings/963-el-control-que-propuse-era-falso.md:199` | ``NNN`` | 944 | si | `numero` | 947 | `CORRECTA_APUNTA_AL_OCUPANTE` | anclas del contexto en el ocupante y no en el destino: coincidencia de tema con el titulo |
| `06-INGENIERIA-INVERSA/findings/963-el-control-que-propuse-era-falso.md:199` | ``NNN`` | 961 | si | `numero` | 962 | `RESUELVE_AL_OCUPANTE_NO_VERIFICADA` | el numero 961 es UNICO hoy, luego la cita resuelve al ocupante; el contexto no lleva contenido que la confirme o la refute |
| `06-INGENIERIA-INVERSA/findings/979-la-frontera-estatica-gfx8-esta-saturada-con-cifras.md:123` | `NNN:LL` | 188 | si | `contenido` | 240 | `CORRECTA_APUNTA_AL_OCUPANTE` | `cita` 21 vs 3 · `generaci` 10 vs 0 · `equivocada` 5 vs 0 · 'op 12' 6 vs 0. H1 de 188 = la prosa literal. CORRECTA. |
| `06-INGENIERIA-INVERSA/findings/979-la-frontera-estatica-gfx8-esta-saturada-con-cifras.md:136` | `NNN:LL` | 188 | si | `contenido` | 240 | `RESUELVE_AL_OCUPANTE_NO_VERIFICADA` | el numero 188 es UNICO hoy, luego la cita resuelve al ocupante; el contexto no lleva contenido que la confirme o la refute |
| `06-INGENIERIA-INVERSA/findings/992-la-tabla-de-opcodes-de-gfx8-coincide-con-un-codificador.md:103` | ``NNN`` | 991 | si | `numero` | 994 | `CORRECTA_APUNTA_AL_OCUPANTE` | anclas del contexto en el ocupante y no en el destino: coincidencia de tema con el titulo |
| `06-INGENIERIA-INVERSA/findings/992-la-tabla-de-opcodes-de-gfx8-coincide-con-un-codificador.md:135` | ``NNN`` | 991 | si | `numero` | 994 | `CORRECTA_APUNTA_AL_OCUPANTE` | anclas del contexto en el ocupante y no en el destino: coincidencia de tema con el titulo |
| `07-DRIVER/kernel/rx550_drv.c:355` | `findings/NNN` | 176 | si | `contenido` | 237 | `CORRECTA_APUNTA_AL_OCUPANTE` | anclas del contexto en el ocupante y no en el destino: coincidencia de tema con el titulo |
| `07-DRIVER/kernel/rx550_mc.h:72` | `findings/NNN` | 202 | si | `contenido` | 242 | `CORRECTA_APUNTA_AL_OCUPANTE` | anclas del contexto en el ocupante y no en el destino: coincidencia de tema con el titulo |
| `07-DRIVER/kernel/rx550_mmio.c:59` | `findings/NNN` | 176 | si | `contenido` | 237 | `CORRECTA_APUNTA_AL_OCUPANTE` | anclas del contexto en el ocupante y no en el destino: coincidencia de tema con el titulo |
| `07-DRIVER/kernel/rx550_mmio.c:64` | `findings/NNN` | 176 | si | `contenido` | 237 | `CORRECTA_APUNTA_AL_OCUPANTE` | anclas del contexto en el ocupante y no en el destino: coincidencia de tema con el titulo |
| `07-DRIVER/kernel/rx550_mmio.h:20` | `findings/NNN` | 176 | si | `contenido` | 237 | `CORRECTA_APUNTA_AL_OCUPANTE` | anclas del contexto en el ocupante y no en el destino: coincidencia de tema con el titulo |
| `07-DRIVER/kernel/rx550_mmio.h:31` | `findings/NNN` | 176 | si | `contenido` | 237 | `CORRECTA_APUNTA_AL_OCUPANTE` | anclas del contexto en el ocupante y no en el destino: coincidencia de tema con el titulo |
| `07-DRIVER/kernel/rx550_mmio.h:107` | ``NNN`` | 176 | si | `contenido` | 237 | `CORRECTA_APUNTA_AL_OCUPANTE` | anclas del contexto en el ocupante y no en el destino: coincidencia de tema con el titulo |
| `07-DRIVER/kernel/rx550_mmio.h:140` | ``NNN`` | 176 | si | `contenido` | 237 | `CORRECTA_APUNTA_AL_OCUPANTE` | anclas del contexto en el ocupante y no en el destino: coincidencia de tema con el titulo |
| `07-DRIVER/kernel/rx550_mmio.h:190` | ``NNN`` | 176 | si | `contenido` | 237 | `CORRECTA_APUNTA_AL_OCUPANTE` | anclas del contexto en el ocupante y no en el destino: coincidencia de tema con el titulo |
| `07-DRIVER/tests/test_mc.c:198` | `findings/NNN` | 176 | si | `contenido` | 237 | `CORRECTA_APUNTA_AL_OCUPANTE` | anclas del contexto en el ocupante y no en el destino: coincidencia de tema con el titulo |
| `07-DRIVER/tests/test_mmio.c:12` | `findings/NNN` | 176 | si | `contenido` | 237 | `CORRECTA_APUNTA_AL_OCUPANTE` | anclas del contexto en el ocupante y no en el destino: coincidencia de tema con el titulo |
| `07-DRIVER/tests/test_mmio.c:20` | `findings/NNN` | 176 | si | `contenido` | 237 | `CORRECTA_APUNTA_AL_OCUPANTE` | anclas del contexto en el ocupante y no en el destino: coincidencia de tema con el titulo |
| `07-DRIVER/tests/test_mmio.c:92` | `findings/NNN` | 176 | si | `contenido` | 237 | `CORRECTA_APUNTA_AL_OCUPANTE` | anclas del contexto en el ocupante y no en el destino: coincidencia de tema con el titulo |
| `08-ARQUITECTURA/MEMORIA-GFX8.md:95` | ``NNN`` | 128 | si | `contenido` | 229 | `NO_ES_CITA` | constante de cache GL1 escrita a mano en el hardware, no un numero de hallazgo |
| `08-ARQUITECTURA/decisions/2026-10-04-numeros-de-hallazgo-duplicados.md:39` | ``NNN`` | 944 | si | `numero` | 947 | `CORRECTA_APUNTA_AL_OCUPANTE` | anclas del contexto en el ocupante y no en el destino: coincidencia de tema con el titulo |
| `08-ARQUITECTURA/tools/REENVIO-FINDINGS.tsv:72` | ``NNN`` | 1003 | si | `numero` | 1005 | `CORRECTA_META_RENUMERACION` | la cita esta en el mapa o en su indice: el numero viejo es el DATO (citas_prosa_adjudicado.py:27-36) |
| `08-ARQUITECTURA/tools/REENVIO-FINDINGS.tsv:84` | ``NNN`` | 290 | si | `numero/numero` | 291,400 | `CORRECTA_META_RENUMERACION` | la cita esta en el mapa o en su indice: el numero viejo es el DATO (citas_prosa_adjudicado.py:27-36) |
| `08-ARQUITECTURA/tools/REENVIO-FINDINGS.tsv:84` | ``NNN`` | 290 | si | `numero/numero` | 291,400 | `CORRECTA_META_RENUMERACION` | la cita esta en el mapa o en su indice: el numero viejo es el DATO (citas_prosa_adjudicado.py:27-36) |
| `08-ARQUITECTURA/tools/REENVIO-FINDINGS.tsv:201` | ``NNN`` | 267 | si | `numero` | 271 | `CORRECTA_META_RENUMERACION` | la cita esta en el mapa o en su indice: el numero viejo es el DATO (citas_prosa_adjudicado.py:27-36) |
| `08-ARQUITECTURA/tools/_selftest_stale_gap.py:445` | `NNN:LL` | 52 | si | `contenido` | 193 | `CORRECTA_APUNTA_AL_OCUPANTE` | anclas del contexto en el ocupante y no en el destino: coincidencia de tema con el titulo |
| `08-ARQUITECTURA/tools/_selftest_stale_gap.py:446` | `NNN:LL` | 52 | si | `contenido` | 193 | `CORRECTA_APUNTA_AL_OCUPANTE` | anclas del contexto en el ocupante y no en el destino: coincidencia de tema con el titulo |
| `08-ARQUITECTURA/tools/doclint.py:382` | ``NNN`` | 190 | si | `contenido` | 198 | `CORRECTA_APUNTA_AL_OCUPANTE` | anclas del contexto en el ocupante y no en el destino: ['uvd_v6_3'] |
| `08-ARQUITECTURA/tools/findings_index.py:328` | ``NNN`` | 89 | si | `contenido` | 196 | `CORRECTA_META_RENUMERACION` | el contexto declara el renumerado (nombra el numero nuevo o una palabra de renumerado) |
| `08-ARQUITECTURA/tools/findings_index.py:329` | ``NNN`` | 89 | si | `contenido` | 196 | `CORRECTA_META_RENUMERACION` | el contexto declara el renumerado (nombra el numero nuevo o una palabra de renumerado) |
| `08-ARQUITECTURA/tools/findings_index.py:513` | ``NNN`` | 1000 | si | `numero` | 1004 | `CORRECTA_META_RENUMERACION` | el contexto declara el renumerado (nombra el numero nuevo o una palabra de renumerado) |
| `08-ARQUITECTURA/tools/reenvio_gate.py:66` | ``NNN`` | 290 | si | `numero/numero` | 291,400 | `CORRECTA_META_RENUMERACION` | el contexto declara el renumerado (nombra el numero nuevo o una palabra de renumerado) |
| `08-ARQUITECTURA/tools/reenvio_gate.py:66` | ``NNN`` | 290 | si | `numero/numero` | 291,400 | `CORRECTA_META_RENUMERACION` | el contexto declara el renumerado (nombra el numero nuevo o una palabra de renumerado) |
| `08-ARQUITECTURA/tools/reenvio_gate.py:124` | ``NNN`` | 267 | si | `numero` | 271 | `CORRECTA_META_RENUMERACION` | el contexto declara el renumerado (nombra el numero nuevo o una palabra de renumerado) |
| `08-ARQUITECTURA/tools/reenvio_gate.py:162` | ``NNN`` | 267 | si | `numero` | 271 | `CORRECTA_META_RENUMERACION` | el contexto declara el renumerado (nombra el numero nuevo o una palabra de renumerado) |
| `08-ARQUITECTURA/tools/refs_repair.py:25` | ``NNN`` | 202 | si | `contenido` | 242 | `CORRECTA_META_RENUMERACION` | el contexto declara el renumerado (nombra el numero nuevo o una palabra de renumerado) |
| `08-ARQUITECTURA/tools/refs_repair.py:25` | ``NNN`` | 202 | si | `contenido` | 242 | `CORRECTA_META_RENUMERACION` | el contexto declara el renumerado (nombra el numero nuevo o una palabra de renumerado) |
| `08-ARQUITECTURA/tools/refs_repair.py:117` | ``NNN`` | 267 | si | `numero` | 271 | `CORRECTA_META_RENUMERACION` | el contexto declara el renumerado (nombra el numero nuevo o una palabra de renumerado) |
| `08-ARQUITECTURA/tools/stale_gap.py:759` | `NNN:LL` | 52 | si | `contenido` | 193 | `CORRECTA_APUNTA_AL_OCUPANTE` | anclas del contexto en el ocupante y no en el destino: coincidencia de tema con el titulo |
| `08-ARQUITECTURA/tools/stale_gap.py:760` | `NNN:LL` | 52 | si | `contenido` | 193 | `CORRECTA_APUNTA_AL_OCUPANTE` | anclas del contexto en el ocupante y no en el destino: coincidencia de tema con el titulo |
| `FINDINGS-RENUMERACIONES.md:56` | ``NNN`` | 267 | si | `numero` | 271 | `CORRECTA_META_RENUMERACION` | la cita esta en el mapa o en su indice: el numero viejo es el DATO (citas_prosa_adjudicado.py:27-36) |
| `FINDINGS-RENUMERACIONES.md:58` | ``NNN`` | 280 | si | `numero` | 288,288 | `CORRECTA_META_RENUMERACION` | la cita esta en el mapa o en su indice: el numero viejo es el DATO (citas_prosa_adjudicado.py:27-36) |
| `FINDINGS-RENUMERACIONES.md:59` | ``NNN`` | 286 | si | `contenido` | 401 | `CORRECTA_META_RENUMERACION` | la cita esta en el mapa o en su indice: el numero viejo es el DATO (citas_prosa_adjudicado.py:27-36) |
| `FINDINGS-RENUMERACIONES.md:60` | ``NNN`` | 290 | si | `numero/numero` | 291,400 | `CORRECTA_META_RENUMERACION` | la cita esta en el mapa o en su indice: el numero viejo es el DATO (citas_prosa_adjudicado.py:27-36) |
| `FINDINGS-RENUMERACIONES.md:61` | ``NNN`` | 941 | si | `numero` | 942 | `CORRECTA_META_RENUMERACION` | la cita esta en el mapa o en su indice: el numero viejo es el DATO (citas_prosa_adjudicado.py:27-36) |
| `FINDINGS-RENUMERACIONES.md:62` | ``NNN`` | 944 | si | `numero` | 947 | `CORRECTA_META_RENUMERACION` | la cita esta en el mapa o en su indice: el numero viejo es el DATO (citas_prosa_adjudicado.py:27-36) |
| `FINDINGS-RENUMERACIONES.md:63` | ``NNN`` | 961 | si | `numero` | 962 | `CORRECTA_META_RENUMERACION` | la cita esta en el mapa o en su indice: el numero viejo es el DATO (citas_prosa_adjudicado.py:27-36) |
| `FINDINGS-RENUMERACIONES.md:64` | ``NNN`` | 991 | si | `numero` | 994 | `CORRECTA_META_RENUMERACION` | la cita esta en el mapa o en su indice: el numero viejo es el DATO (citas_prosa_adjudicado.py:27-36) |
| `FINDINGS-RENUMERACIONES.md:65` | ``NNN`` | 1000 | si | `numero` | 1004 | `CORRECTA_META_RENUMERACION` | la cita esta en el mapa o en su indice: el numero viejo es el DATO (citas_prosa_adjudicado.py:27-36) |
| `FINDINGS-RENUMERACIONES.md:66` | ``NNN`` | 1003 | si | `numero` | 1005 | `CORRECTA_META_RENUMERACION` | la cita esta en el mapa o en su indice: el numero viejo es el DATO (citas_prosa_adjudicado.py:27-36) |
| `HARDWARE-FINGERPRINT.md:71` | ``NNN`` | 163 | si | `contenido` | 233 | `CORRECTA_APUNTA_AL_OCUPANTE` | anclas del contexto en el ocupante y no en el destino: coincidencia de tema con el titulo |
| `HARDWARE-FINGERPRINT.md:125` | ``NNN`` | 163 | si | `contenido` | 233 | `CORRECTA_APUNTA_AL_OCUPANTE` | anclas del contexto en el ocupante y no en el destino: coincidencia de tema con el titulo |
| `HARDWARE-FINGERPRINT.md:126` | ``NNN`` | 167 | si | `contenido` | 234 | `NO_ES_CITA` | Direccion PCI 0x1002:0x699F del bus, no un numero de hallazgo |
| `NEGATIVE-RESULTS.md:92` | `NNN:LL` | 52 | si | `contenido` | 193 | `CORRECTA_APUNTA_AL_OCUPANTE` | anclas del contexto en el ocupante y no en el destino: coincidencia de tema con el titulo |
| `NEGATIVE-RESULTS.md:94` | `NNN:LL` | 52 | si | `contenido` | 193 | `CORRECTA_APUNTA_AL_OCUPANTE` | anclas del contexto en el ocupante y no en el destino: coincidencia de tema con el titulo |
| `NEGATIVE-RESULTS.md:124` | ``NNN`` | 103 | si | `contenido` | 210 | `RESUELVE_AL_OCUPANTE_NO_VERIFICADA` | el numero 103 es UNICO hoy, luego la cita resuelve al ocupante; el contexto no lleva contenido que la confirme o la refute |
| `NEGATIVE-RESULTS.md:126` | ``NNN`` | 106 | si | `contenido` | 213 | `RESUELVE_AL_OCUPANTE_NO_VERIFICADA` | el contexto tiene anclas en los dos ficheros: el numero no discrimina |
| `NEGATIVE-RESULTS.md:224` | ``NNN`` | 156 | si | `contenido` | 232 | `RESUELVE_AL_OCUPANTE_NO_VERIFICADA` | el numero 156 es UNICO hoy, luego la cita resuelve al ocupante; el contexto no lleva contenido que la confirme o la refute |
| `NEGATIVE-RESULTS.md:238` | ``NNN`` | 144 | si | `contenido` | 231 | `C3_APUNTA_AL_VIEJO` **C3** | destino 231: `GFX_HWIP` 0 vs 13 · `firmware` 0 vs 23 · `ip_version` 0 vs 9 · `PRT` 49 vs 0. El 144 de HOY es `144-prt-cierra-...` y su linea 114 es un encabezado de seccion. |
| `NEGATIVE-RESULTS.md:240` | ``NNN`` | 144 | si | `contenido` | 231 | `C3_APUNTA_AL_VIEJO` **C3** | destino 231: misma fila y mismo sujeto que :238; `144:124` de HOY es un cercado ```c, sin contenido. |
| `NEGATIVE-RESULTS.md:252` | ``NNN`` | 188 | si | `contenido` | 240 | `C3_APUNTA_AL_VIEJO` **C3** | destino 240: `eslabon` 0 vs 5 · `observad` 0 vs 7 · `PROVEN_ABSENT` 0 vs 3. La prosa dice 'la cadena observada'; H1 de 240: 'La cadena de identidad pasa de derivada a observada'. |
| `NEGATIVE-RESULTS.md:271` | ``NNN`` | 188 | si | `contenido` | 240 | `C3_APUNTA_AL_VIEJO` **C3** | destino 240: 'los tres eslabones observados' = 240 (`eslabon` 0 vs 5, `observad` 0 vs 7). |
| `NEGATIVE-RESULTS.md:349` | ``NNN`` | 280 | si | `numero` | 288,288 | `RESUELVE_AL_OCUPANTE_NO_VERIFICADA` | el numero 280 es UNICO hoy, luego la cita resuelve al ocupante; el contexto no lleva contenido que la confirme o la refute |
| `docs/AGENTS-RECTOR-2026-10-02.md:183` | ``NNN`` | 163 | si | `contenido` | 233 | `CORRECTA_APUNTA_AL_OCUPANTE` | anclas del contexto en el ocupante y no en el destino: coincidencia de tema con el titulo |
| `docs/AGENTS-RECTOR-2026-10-02.md:484` | ``NNN`` | 103 | si | `contenido` | 210 | `RESUELVE_AL_OCUPANTE_NO_VERIFICADA` | el numero 103 es UNICO hoy, luego la cita resuelve al ocupante; el contexto no lleva contenido que la confirme o la refute |
| `docs/AGENTS-RECTOR-2026-10-02.md:484` | ``NNN`` | 104 | si | `contenido` | 211 | `RESUELVE_AL_OCUPANTE_NO_VERIFICADA` | el numero 104 es UNICO hoy, luego la cita resuelve al ocupante; el contexto no lleva contenido que la confirme o la refute |
| `docs/AGENTS-RECTOR-2026-10-02.md:484` | ``NNN`` | 106 | si | `contenido` | 213 | `RESUELVE_AL_OCUPANTE_NO_VERIFICADA` | el numero 106 es UNICO hoy, luego la cita resuelve al ocupante; el contexto no lleva contenido que la confirme o la refute |
| `docs/AGENTS-RECTOR-2026-10-02.md:486` | ``NNN`` | 103 | si | `contenido` | 210 | `C3_APUNTA_AL_VIEJO` **C3** | destino 210: `handshake` 0 vs 3 · `completion` 0 vs 2 · `072` 0 vs 12. H1 de 210: 'el handshake de COMPLETACION si existe, y `072` afirmo lo contrario' = la prosa literal. |
| `docs/AGENTS-RECTOR-2026-10-02.md:488` | ``NNN`` | 104 | si | `contenido` | 211 | `C3_APUNTA_AL_VIEJO` **C3** | destino 211: `VM_INVALIDATE_REQUEST` 0 vs 5 · `VM_INVALIDATE_RESPONSE` 0 vs 5 · '16 bits' 0 vs 5. H1 de 211: '`VM_INVALIDATE_REQUEST` y `RESPONSE` son 16 bits cada uno' = la prosa literal. |
| `docs/AGENTS-RECTOR-2026-10-02.md:490` | ``NNN`` | 106 | si | `contenido` | 213 | `CORRECTA_APUNTA_AL_OCUPANTE` | `FUNCTION` 20 vs 1 · `vmid` 15 vs 0. H1 de 106 = la prosa literal. CORRECTA. |
| `docs/CHANGELOG-RESEARCH.md:2617` | ``NNN`` | 190 | si | `contenido` | 198 | `CORRECTA_APUNTA_AL_OCUPANTE` | anclas del contexto en el ocupante y no en el destino: coincidencia de tema con el titulo |
| `docs/CHANGELOG-RESEARCH.md:3343` | ``NNN`` | 126 | si | `contenido` | 228 | `NO_ES_CITA` | codigo de salida de shell 126/127 en una lista de codigos, no un numero de hallazgo |
| `docs/CONTRADICTIONS.md:1034` | ``NNN`` | 126 | si | `contenido` | 228 | `NO_ES_CITA` | codigo de salida de shell, la propia linea lo dice ('el `126` que es de shell') |
| `docs/CURRENT-STATE.md:595` | ``NNN`` | 85 | si | `contenido` | 194 | `CORRECTA_APUNTA_AL_OCUPANTE` | anclas del contexto en el ocupante y no en el destino: coincidencia de tema con el titulo |
| `docs/CURRENT-STATE.md:693` | ``NNN`` | 190 | si | `contenido` | 198 | `CORRECTA_APUNTA_AL_OCUPANTE` | anclas del contexto en el ocupante y no en el destino: coincidencia de tema con el titulo |
| `docs/EVIDENCE-MATRIX.md:3950` | ``NNN`` | 85 | si | `contenido` | 194 | `CORRECTA_APUNTA_AL_OCUPANTE` | anclas del contexto en el ocupante y no en el destino: coincidencia de tema con el titulo |
| `docs/MASTER-RESEARCH-STATUS.md:145` | ``NNN`` | 52 | si | `contenido` | 193 | `CORRECTA_APUNTA_AL_OCUPANTE` | anclas del contexto en el ocupante y no en el destino: ['pasid', 'src_id', 'vmid'] |
| `docs/NEGATIVE-RESULTS.md:1131` | ``NNN`` | 185 | si | `contenido` | 239 | `RESUELVE_AL_OCUPANTE_NO_VERIFICADA` | el numero 185 es UNICO hoy, luego la cita resuelve al ocupante; el contexto no lleva contenido que la confirme o la refute |
| `docs/NEGATIVE-RESULTS.md:1131` | ``NNN`` | 190 | si | `contenido` | 198 | `CORRECTA_APUNTA_AL_OCUPANTE` | anclas del contexto en el ocupante y no en el destino: coincidencia de tema con el titulo |
| `docs/NEGATIVE-RESULTS.md:1376` | ``NNN`` | 190 | si | `contenido` | 198 | `CORRECTA_APUNTA_AL_OCUPANTE` | anclas del contexto en el ocupante y no en el destino: coincidencia de tema con el titulo |
| `docs/TOOLS-STATUS.md:3040` | ``NNN`` | 185 | si | `contenido` | 239 | `RESUELVE_AL_OCUPANTE_NO_VERIFICADA` | el numero 185 es UNICO hoy, luego la cita resuelve al ocupante; el contexto no lleva contenido que la confirme o la refute |
| `docs/TOOLS-STATUS.md:3040` | ``NNN`` | 190 | si | `contenido` | 198 | `CORRECTA_APUNTA_AL_OCUPANTE` | anclas del contexto en el ocupante y no en el destino: coincidencia de tema con el titulo |
| `docs/TOOLS-STATUS.md:3482` | ``NNN`` | 126 | si | `contenido` | 228 | `NO_ES_CITA` | codigo de salida de shell 126/127 en una tabla de fallos de script |
| `tools/check_num_unico.py:144` | ``NNN`` | 110 | si | `contenido` | 215 | `RESUELVE_AL_OCUPANTE_NO_VERIFICADA` | el numero 110 es UNICO hoy, luego la cita resuelve al ocupante; el contexto no lleva contenido que la confirme o la refute |
| `tools/check_num_unico.py:145` | `NNN:LL` | 110 | si | `contenido` | 215 | `RESUELVE_AL_OCUPANTE_NO_VERIFICADA` | el numero 110 es UNICO hoy, luego la cita resuelve al ocupante; el contexto no lleva contenido que la confirme o la refute |
| `tools/check_num_unico.py:149` | ``NNN`` | 110 | si | `contenido` | 215 | `RESUELVE_AL_OCUPANTE_NO_VERIFICADA` | el numero 110 es UNICO hoy, luego la cita resuelve al ocupante; el contexto no lleva contenido que la confirme o la refute |
| `tools/citas_prosa_census.py:255` | ``NNN`` | 110 | si | `contenido` | 215 | `CORRECTA_APUNTA_AL_OCUPANTE` | anclas del contexto en el ocupante y no en el destino: ['wait'] |
| `tools/citas_prosa_census.py:295` | ``NNN`` | 110 | si | `contenido` | 215 | `RESUELVE_AL_OCUPANTE_NO_VERIFICADA` | el numero 110 es UNICO hoy, luego la cita resuelve al ocupante; el contexto no lleva contenido que la confirme o la refute |
| `tools/dupenum.py:20` | ``NNN`` | 167 | si | `contenido` | 234 | `RESUELVE_AL_OCUPANTE_NO_VERIFICADA` | el numero 167 es UNICO hoy, luego la cita resuelve al ocupante; el contexto no lleva contenido que la confirme o la refute |
| `tools/dupenum.py:20` | `findings/NNN` | 176 | si | `contenido` | 237 | `CORRECTA_APUNTA_AL_OCUPANTE` | anclas del contexto en el ocupante y no en el destino: coincidencia de tema con el titulo |
| `tools/dupenum.py:40` | `findings/NNN` | 202 | si | `contenido` | 242 | `CORRECTA_META_RENUMERACION` | el contexto declara el renumerado (nombra el numero nuevo o una palabra de renumerado) |
| `tools/hcconsist.py:8` | `findings/NNN` | 114 | si | `contenido` | 219 | `CORRECTA_APUNTA_AL_OCUPANTE` | anclas del contexto en el ocupante y no en el destino: coincidencia de tema con el titulo |
| `tools/hcconsist.py:119` | `findings/NNN` | 114 | si | `contenido` | 219 | `CORRECTA_APUNTA_AL_OCUPANTE` | anclas del contexto en el ocupante y no en el destino: coincidencia de tema con el titulo |
| `tools/regconst.py:34` | `findings/NNN` | 176 | si | `contenido` | 237 | `CORRECTA_APUNTA_AL_OCUPANTE` | anclas del contexto en el ocupante y no en el destino: coincidencia de tema con el titulo |
| `tools/regconst.py:70` | `findings/NNN` | 176 | si | `contenido` | 237 | `CORRECTA_APUNTA_AL_OCUPANTE` | anclas del contexto en el ocupante y no en el destino: coincidencia de tema con el titulo |
| `tools/regconst.py:425` | `findings/NNN` | 176 | si | `contenido` | 237 | `CORRECTA_APUNTA_AL_OCUPANTE` | anclas del contexto en el ocupante y no en el destino: coincidencia de tema con el titulo |
| `tools/routeaudit.py:150` | `NNN:LL` | 163 | si | `contenido` | 233 | `CORRECTA_APUNTA_AL_OCUPANTE` | anclas del contexto en el ocupante y no en el destino: coincidencia de tema con el titulo |

---

## 13. LO QUE QUEDA ABIERTO, SIN PLAN

- **C3 = 6 es una cota inferior, no el total.** Las 40 citas de la clase 7 estan sin
  adjudicar por contenido. El total de C3 esta en **[6, 46]** y no se puede cerrar sin
  leerlas. Instrumento escrito, muestra no rodada.
- **La contradiccion de contenido entre `267` y `269`** (`269:44` dice `cks_enable = 0`
  en los niveles 0 y 1; la tabla de `267` dice nivel 1 *habilitado*). No es un defecto
  de cita. `NOT_DETERMINED`.
- **`290` tiene dos destinos** (`291` y `400`), y las dos filas son `numero`. MEDIDO: 8
  citas a `290`, y **el mapa no puede decidir** a cual apuntan. Es el unico caso de la
  banda donde la ambiguedad viene del mapa y no del numero. Ninguna de las 8 ha salido
  C3.
- **La divergencia de `EXCLUIDOS` entre la puerta y el censo** (§6.2) invalida el
  `--cruzado` como comparacion de poblaciones. No lo he corregido: son dos instrumentos y
  la correccion es de otro nodo.
- **Las 24 no-citas** necesitan 12 filas mas en `NO_CITA_FICHEROS`, o una regla de
  contexto para uid y codigos de salida. La regla de contexto es mejor que la lista, y no
  la escribo porque no es mi mandato.
- **`findings/` tiene 548 ficheros y 74 numeros duplicados.** El numero de duplicados no
  se movio respecto a la declaracion (74), y la banda tampoco. Es lo unico que sostiene
  que estas cifras son de un instante y no una foto.

