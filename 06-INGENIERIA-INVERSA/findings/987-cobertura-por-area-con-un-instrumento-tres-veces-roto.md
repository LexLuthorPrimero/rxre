# 987 · Cobertura por área de todo mi ámbito, medida sobre 498 hallazgos — y tres instrumentos rotos antes de llegar a un número

```
CLASSIFICATION=MEASUREMENT+METHODOLOGY+NEGATIVE_RESULT · TRACK=STATIC
CORPUS=06-INGENIERIA-INVERSA/findings (498 ficheros) · HARDWARE_SCOPE=HOST-C/RX550/0000:01:00.0
WORK_CLASS=READ_ONLY/EVIDENCE+WRITE_LOCAL · WRITE_LOCAL=PROPIOS
WRITE_EXECUTION=NONE · MODIFICATIONS=0 (el corpus no se toca; lo unico escrito es este fichero)
RUNTIME=NOT_RUN · GPU INTACTA · SIN MMIO · SIN ESCRITURA A REGISTROS · SIN DEBUGFS
CORRECTS=979-la-frontera-estatica-gfx8-esta-saturada-con-cifras.md
CONTINUES=981-el-backend-de-color-y-profundidad-tiene-cero-cobertura.md
CONTINUES=967-opcode-ambiguidad-era-el-detalector.md
AUTORIA=AGENTE-SMU-3 (AGENT-03, semantica GPU)
```

## Qué es esto

`979` declaró `SATURATED` la frontera de semántica estática GFX8 con **siete
preguntas**, todas de un dominio. `986` estrecho esa afirmación; `981` la contradio
con un hueco real. **Las tres son consenso sobre una base de muestreo demasiado estrecha.**

Esta nota mide **el ambito entero**, con un instrumento que tardo tres versiones en
hacer bien, y las tres versiones rotas estan aqui porque **un hallazgo sobre como
medir que no incluye los errores no es reproducible**.

## 1 · El instrumento, y sus tres versiones

El objetivo es distinguir *mencionar* un termino de *citarlo*. El corpus escribe
los terminos entre backticks, asi que **citado = el token aparece dentro de un span de
backticks**. Los tres fallos fueron de ese test.

**v1 · adyacencia.** `` el caracter inmediatamente antes o despues es un backtick ``

```
  area        fich.  citado
  PTE / PDE      62        3     <-- IMPOSIBLE
```

El corpus escribe `` `PTE format on VI` ``: los backticks envuelven una **frase**, no
el token. Con el test bueno, PTE/PDE da **48 de 62**, no 3. **El ranking estaba
invertido en casi todas las filas.**

**v2 · patron estricto independiente.** `` `TLB[A-Za-z_0-9]*` `` y similares

```
  ISA / opcode    44      462     <-- IMPOSIBLE, contaminacion NEGATIVA
  TLB             66        0     <-- el token nunca va suelto entre backticks
```

Dos fallos opuestos en la misma tabla: el patron de ISA matcheaba **cualquier**
identificador en mayusculas (`` `[A-Z]{2,5}_[A-Z0-9_]+` ``), y los demas nunca
encontraban el token suelto porque no existe esa forma de escribirlo.

**La asercion que lo arrastro**: `citado <= ficheros`, siempre. Una contaminacion
negativa es imposible, y su presencia **no es un dato raro, es el detector
funcionando**. Si no lo hubiera puesto, v2 habria publicado 462 como cobertura de ISA.

**v3 · test de span + asercion + patron capable**

```python
SPAN = re.compile(r'`[^`]*`')                    # spans de backticks
spans = set(SPAN.findall(texto))
citado = ficheros_cuyo_algun_match_aparece_ENTRE_LOS_SPANS
# asercion: citado <= ficheros, en cada fila
```

Y el patron de ISA, que v2 era incapaz de matchear:

```
  S_LOAD_DWORD     v2=False   v3=True
  EXP_FLAT         v2=False   v3=True
  SOP2_C_ADD_U32   v2=False   v3=True
  VINTRP1_LOAD_S16 v2=False   v3=True
```

`S_[A-Z]{2,4}\b` no puede matchear `S_LOAD_DWORD`: tras 4 letras hay un `_`, que es
caracter de palabra, y la `\b` no se cumple. Probe hacia atras tampoco. **El patron
no era demasiado estricto: era incapaz**, y devolvia 1 donde hay 3 ficheros con
decenas de tokens.

## 2 · La medicion, sobre 498 ficheros

```
area              ficheros  citado   citing como barra
GMC / MMIO               0       0
ISA GFX8                  3       3   ###
CB / DB                   3       3   ###
IB / ring                 5       5   #####
CP                       13      13   #############
MC / VRAM                18      18   ##################
SDMA                     18      18   ##################
GART                     20      20   ####################
TLB                      35      35   ###################################
SYNC / fence             38      38   ######################################
PM4 packet               43      43   ###########################################
GPUVM                    44      44   ############################################
PTE / PDE                48      48   ################################################
VMID / PASID             53      53   #####################################################
clocks / DPM             65      65   #################################################################
```

**Tres areas a cero o casi, y las tres se leen distinto:**

**`GMC / MMIO` = 0, y no es un hueco.** Ningun hallazgo menciona un registro `mmGMC_*`,
y la razon es que **el driver no los escribe: los programa el firmware del SMC**. Un
cero aqui es el resultado correcto, no una frontera. **Un area con cero cobertura y un
area que no aplica son la misma cifra y no son la misma cosa**, y por eso el ranking
solo no basta: hay que explicar cada cero.

**`ISA GFX8` = 3, y es un hueco real.** De los tres, dos son `967` (el detector de
ambigüedad de 44 opcodes) y `135` (el censo de `PACKET3`). Es decir: **el opcode de
GFX8 esta medido, y la semantica de la instruccion no.** De `V_ADD_F32` a
`DS_WRITE_B32` hay 498 hallazgos que no citan ninguna.

**`CB / DB` = 3, confirmado por `981`, y `986` lo subio a `PROVEN_ABSENT` en el
kernel.** No es una frontera abierta: es un muro, como `033`.

## 3 · Lo que esto cambia, y lo que no

**Cambia:** la base de muestreo de la que `979`-saturation y `986`-saturation
dependen. `979` uso 7 preguntas; esta nota usa 498 ficheros × 15 areas. Y el veredicto
cambia de forma: **la mayoria del ambito esta densamente cubierta — PTE 48, VMID 53,
clocks 65 — pero hay dos huecos reales y bien delimitados, no una frontera saturada de
forma uniforme.**

**No cambia:**
- Los dos discriminantes de `979` §3 (`mmVM_PRT_CNTL` 0x534, y el `pasid` del IV). Los
  dos siguen necesitando MMIO o el anillo del IH, que es `scope=ROOT` de AGENT-04.
- `986`: los headers de CB/DB no existen en el kernel. Este nota lo confirma por otra
  via —no hay ni un hallazgo que los cite porque no hay nada que citar—.

**Y una honestidad que me cuesta:** yo mismo cai en los tres fallos del instrumento,
**despues de escribir `981`, que advierte exactamente de los dos primeros**. Escribi
la leccion de los controles contaminados y y a los cuarenta minutos construi un
instrumento con un defecto de test identico. **Un principio escrito no es un
principio aprendido hasta que se le incumple a uno mismo.**

## 4 · Procedencia

- Las tres versiones del instrumento, con su salida y su defecto, estan arriba. Los
  conteos son **reproducibles**: `re.findall` sobre `*.md` de
  `06-INGENIERIA-INVERSA/findings/`, sin red, sin tool, sin estado externo.
- `498` ficheros en el momento de la medicion. El numero crece durante la sesion —habia
  491 al empezar— y por eso la cifra lleva fecha y no se toma como estable.
- Sin MMIO, sin lectura de registros, sin debugfs, sin sysfs, sin modulos, sin
  descargas. La GPU no se ha tocado. `RUNTIME=NOT_RUN`.
- No se regenero ningun artefacto generado: son de otras sesiones.
- Ambito: `.write-lock/sem03`, un solo fichero nuevo, este.

## Nota de metodo, y por que el instrumento va en el hallazgo

La tentacion de publicar solo la tabla v3 es fuerte: es la que funciona y da numeros
bonitos. **Publicarla sola habria sido la eleccion de cuatro cifras en vez de doce, y
ninguno de los cuatro habria explicado por que se descartaron las otras ocho.**

La asercion `citado <= ficheros` es la pieza que mas trabajo ha hecho, y cabe en una
linea. Sin ella, v2 habria dicho que la ISA tiene 462 hallazgos y habria sido falso de
una forma que **ninguna revision habria detectado**, porque un numero grande con
decimales convincentes no parece un error de pattern.

Y el otro detectors es el mas tonto: `ISA` con 1 cited y 44 ficheros **debia** sonar
inmediato. Un area con mas ficheros que citas es rarer, salvo que el patron mienta. La
desconfianza correcta ante un area con mas ficheros que citas no es "esta poco
documentada", es **"mi patron no sirve"** — y esa duda, ella misma, es el control.
