# 1575 — Experimento RXRE sobre `soft_regs_start`: **`INCREMENTAL_VALUE` en el barrido, `COVERAGE GAP` en AST y trace, `NO_LAUNDERING`.** Y un defecto de contrato, más dos demonstrations mías rotas antes de encontrarlo

```text
AGENCIA=RX550-INVESTIGACION · WORK_CLASS=EVALUACION-DE-INSTRUMENTO
CLASSIFICATION=EVALUACIÓN-DE-INSTRUMENTO+COVERAGE-GAP+DEFECTO-DE-CONTRATO
MODIFICATIONS=1574 (el baseline contra el que se midió)
AUTOR=AGENTE-INSTR
WRITE_EXECUTION=NONE · GPU=NONE TOUCHED · RUNTIME=NOT_RUN
DISPOSITIVO_TOCADO=NINGUNO · ni 0000:01:00.0 (1002:699f) ni 0000:00:02.0 (8086:0412)
ESCRITOS_POR_ESTA_ITERACION   ninguno.  No se toco tools/rxre/.
COMPARA CONTRA   1574  (el baseline,  congelado antes de usar RXRE)
VEREDICTO         INCREMENTAL_VALUE      en el alcance de descubrimiento
                  COVERAGE GAP            en xref  y trace,  con motivo nombrado
                  NO_LAUNDERING           en lo que si respondio
                  DEFECTO DE CONTRATO     1,  aislado,  no bloquea
AUTOR=AGENTE-INSTR
GENERADO=2026-10-06 · MEDIDO=EN ESTA HOST
```

## 1 · Lo que RXRE respondió, y lo que no

```text
  capacidad       status      resultados  el motivo,  si lo dio
  ---------------------------------------------------------------------------
  capabilities    ok              9        --
  symbol          ok             20        "encontro 48 coincidencias y se muestran 20:
                                        el tope es de PRESENTACION de esa herramienta,
                                        no del universo"          <- declarado, no escondido
  search          ok              2        idem
  register        ok              4        --
  pm4             ok              -        "pm4ops.py no emite JSON:  se devuelve su
                                        salida como texto, sin reinterpretar"
  provenance      ok              3        idem
  xref            blocked         0        "xref.py no puede construir el AST:  el arbol
                                        esta a medias y completarlo es una ESCRITURA
                                        en el arbol.  NO se ejecuta,  y por tanto NO hay
                                        resultado"                        <- exit 2
  trace           empty           0        "trace_path NO encontro el simbolo en el
                                        subarbol indexado (1 nodo con verdict =
                                        NO_ENCONTRADO)"
```

**Los dos fallos vinieron con motivo, y el motivo es correcto.** `xref` se niego a correr
porque su precondición no se cumple y lo dijo; no devolvió una cadena vacía disfrazada de
respuesta. `trace` dijo `empty` y declaró que `empty` no significa "no existe".

**Eso es exactamente la distinción que pediste que mantuviera**, y la herramienta la respetó
sola. Registro `COVERAGE GAP`, no ausencia de hardware:

```text
  el indice AST de RXRE cubre una fraccion del arbol  ->  xref y trace no pueden
  responder por soft_regs_start  ->  NO ES QUE EL PRODUCTOR NO EXISTA.  El
  productor existe  (  polaris10_smumgr.c:2510  )  y yo ya lo tengo medido.
```

## 2 · Dónde sí hubo valor: una sola consulta barsió lo que mi grep no

Esta es la parte que justificaba la prueba. Yo busqué `SMU7_FIRMWARE_HEADER_LOCATION` en **cuatro**
headers (`smu7.h`, `smu73`, `smu74`, `smu75`). RXRE, en **una** consulta de símbolo, me puso
delante una lectura de `SoftRegisters` en `fiji_smumgr.c:307` que yo no había visto, y que? 
el corpus entero reveló there are **six** smumgr that do this read, each with its **own**
firmware header struct:

```text
  iceland_smumgr.c   SMU71_Firmware_Header
  tonga_smumgr.c     SMU72_Firmware_Header
  fiji_smumgr.c      SMU73_Firmware_Header
  ci_smumgr.c        SMU7_Firmware_Header        ( 256 bytes  )
  polaris10_smumgr.c SMU74_Firmware_Header       ( 180 bytes  )   <-- la RX550
  vegam_smumgr.c     SMU75_Firmware_Header       ( 180 bytes  )
```

Y `smu71.h` y `smu72.h` **no definen** `SMU7_FIRMWARE_HEADER_LOCATION`: lo heredan de `smu7.h`.
Mi baseline decía "0x20000 en los cuatro headers", que era cierto para los cuatro que miré y
**no era una afirmación sobre la familia**.

Con gcc, los seis:

```text
  SMU71_Firmware_Header   sizeof=256   SoftRegisters=48   hoja = 0x20030
  SMU72_Firmware_Header   sizeof=256   SoftRegisters=48   hoja = 0x20030
  SMU73_Firmware_Header   sizeof=256   SoftRegisters=48   hoja = 0x20030
  SMU74_Firmware_Header   sizeof=180   SoftRegisters=48   hoja = 0x20030
  SMU75_Firmware_Header   sizeof=180   SoftRegisters=48   hoja = 0x20030
  SMU7_Firmware_Header    sizeof=256   SoftRegisters=48   hoja = 0x20030
```

**6 de 6: `SoftRegisters` está en el offset 48 y la hoja es `SMC_RAM[0x20030]` en todas las
generaciones**, aunque el tamaño del header se parte en dos grupos (256 y 180). La dirección de
la hoja es un invariante de la familia, y eso no lo Sabía antes de esta prueba.

## 3 · `NO_LAUNDERING`: qué es exactamente

La prueba de laundering, según lo acordado: **reconstruir la cadena a mano antes de leer
`explain()`**. Eso está hecho — el baseline `1574` está escrito y commiteado antes de abrir
RXRE.

Lo que RXRE afirmó, contrastado con el código:

| afirmación de RXRE | mi baseline | verificado contra |
|---|---|---|
| `soft_regs_start` aparece 48 veces | yo encontré 6 **asignaciones** | `grep` — correcto, son usos y asignaciones |
| el campo es `SMU74_Firmware_Header.SoftRegisters` en la línea polaris10 | lo mismo, `polaris10_smumgr.c:2512` | la línea dice `offsetof(SMU74_Firmware_Header, ...)` — coincide |
| los offsets `80/84/88/92/96` de `DRAM_LOG_*` | los mismos, medidos en `1564` | `gcc` — coincide |

**No encontré ni una afirmación de RXRE que fuera falsa.** Ni el producer equivocado, ni el
consumidor equivocado, ni el offset inventado. En lo que respondió, `NO_LAUNDERING`.

Lo que **no** puedo afirmar, y es donde el laundering se escondería: **`xref` y `trace` no
corrieron**, así que de la parte de la cadena que es un grafo — quién llama a quién, qué
representación alimenta a qué consumidor — **RXRE norespondió nada**. No hay laundry que
detectar ahí porque no hay respuesta. Y eso es un `COVERAGE GAP` con nombre, no un Approved.

## 4 · Un defecto de contrato, aislado

```text
  capacidad        n elem   min len   max len   cumple
  search              1        121       121    si
  symbol              1        121       121    si
  register            2        150       173    si
  pm4                 1         76        76    si
  evidence            1        122       122    si
  provenance        163          1         1    NO   <-- frase partida en caracteres
```

`provenance` es la única de las nueve que devuelve `limitations` como `list(texto)` en vez de
`[texto]`:

```text
  limitations[0] = '`'
  limitations[1] = 'p'
  len()           = 163    en vez de 1
```

**El daño real, y es este:** un consumidor que hace `limitations[0]` para leer la primera
limitación recibe **una comilla invertida**. No es `None`, no es un error, no es cadena vacía: es
un valor plausible que no significa nada.

No bloquea la investigación y **no lo toco**, como pediste. Lo dejo con nombre, con su alcance y
con el hecho de que es el único de los nueve.

## 5 · Dos demostraciones mías rotas antes de encontrar el defecto

Esto es lo que más me importa de este hallazgo, más que el defecto.

```text
  (a)  MONTE UNA DEMOSTRACION DE "FALLO SILENCIOSO PELIGROSO"  que era FALSA.
       Afirmaba que  "AST" in limitations  da False  aunque la limitacion
       mencionase AST,  y por tanto el consumidor concluiria que no le avisaron.
       Y es FALSO POR DOS MOTOS  y los dos son mios:
         -  x in lista  prueba pertenencia,  no subcadena.  La misma consulta
            falla en las nueve capacidades:  "no emite JSON" in pm4.limitations
            tambien da False,  y pm4 SI cumple el contrato
         -  la frase de provenance NO contiene "AST".  Eso venía de la
            limitacion de xref.  Importé un dato de un sitio a una prueba sobre
            otro sitio
       Si lo llego a escribir  --  que era lo que estaba a punto de hacer  --  el
       hallazgo seria "RXRE oculta sus limitaciones",  y seria falso.

  (b)  MONTE LA AFIRMACION DE QUE RXRE NO DISTINGUE GENERACIONES.  Y es al
       reves:  no las distingue porque no intenta distinguirlas;  devuelve las
       seis y lo declara.  La limitacion que si declare  --"48 de 48, se muestran
       20,  el tope es de presentacion,  no del universo"  --  es precisa y
       separa el hecho del tope.  Eso es mejor que una distincion silenciosa,  no
       peor.

  (c)  Y una confusion mia de fondo:  pense que el indice AST de RXRE era una
       limitacion de RXRE.  No:  es una limitacion del subarbol que el indice
       cubre.  RXRE lo nombro.  Un indice que cubre menos  es una limitacion
       del indice,  yel no lolamentar porque yo lo leia como limitacion suya.
```

El patrón es el de siempre y ya lo he pagado nueve veces hoy: **una narración que encaja,
construida sobre una medición que no la sostiene.** Lo que la salvó fue mirar el
contraste `pm4` antes de escribir, y ver que mi propio ejemplo de "fallo" fallaba en la
capacidad que sí cumple.

## 6 · Procedimiento

```text
PREGUNTA   ¿de donde sale soft_regs_start?
METODO     1) 1574  baseline reconstructed a mano y commiteado
           2) RXRE por la interfaz publica,  sin el baseline a la vista
           3) contraste de cada afirmacion contra el codigo
BASELINE   1574 ·  8 rondas,  2 compilaciones,  14 greps,  3 en red,  2 errores mios
RXRE       9 capacidades,  3 preguntas
  symbol   ok · 48 coincidencias,  20 mostradas,  tope declarado
  xref     blocked · exit 2 · "no puede construir el AST:  el arbol esta a medias"
  trace    empty · exit 0 · "NO_ENCONTRADO en el subarbol indexado"
  register ok · pm4 ok · provenance ok
NO SE USO explain().  No hizo falta:  la prueba de laundering se hizo contra el
           codigo,  que es lo que acordamos,  y en lo que RXRE respondio no hay
           afirmaciones que contrastar ademas de las de la tabla de §3.
NO SE TOCO tools/rxre/.  Ni una linea.
DISPOSITIVO  NINGUNO.  i915 ausente,  amdgpu intacto
RUNTIME      NOT_RUN
LO QUE SIGUE
  - el frente no se cierra.  Falta  el valor de SMC_RAM[0x20030]  y eso es una
    lectura MMIO.  Con la informacion de 1574  son dos registros:  escribir
    0x1AC con 0x20030  y leer 0x1AD.  Requiere el mismo permiso que 1439  y el
    mismo riesgo de pantalla negra que 1231  documento.
  - y queda la medicion que el propietario pidio  y NO he hecho:
    DISCOVERY COVERAGE con denominador reproducible.  RXRE no puede responderla
    todavia,  y el motivo es concreto:  su indice AST esta incompleto.
```