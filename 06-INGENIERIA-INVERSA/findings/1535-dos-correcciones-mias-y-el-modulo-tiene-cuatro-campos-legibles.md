# 1535 — dos correcciones mías, y el módulo de memoria tiene cuatro campos que sí se pueden leer

```text
AGENCIA=RX550-INVESTIGACION · PARTE=1/MC-MEMORIA+ROM · FASE=2
CLASSIFICATION=ERROR-CORRECTION-PROPIA + DECODIFICACION + DEPENDENCIA-EXTERNA-DECLARADA
TRACK=STATIC · CERO HARDWARE · Intel no tocada
GENERADO=2026-10-05
AFECTADO=corrijo dos cosas que dije, y una era una afirmacion mia de este mismo turno
ESTADO=PROBADO · ucMemoryType=0x50 -> GDDR5, y NO es una contradiccion del header
       · el V8 no declara encoding numerico; los numeros viven en el V4/V5, y ahi si esta 0x5:DDR5
       · ucMisc=0x04 -> SINGLE rank, burstlength 8.  ucRefreshRateFactor=0 -> 8 ms
       · ucDensity=0x63 y el codigo de vendedor=0 quedan fuera de lo declarado, con nombre
       · EL DISCRIMINADOR QUE NOMBRE EL 1532 ES EXTERNO: no es resoluble con lo que tenemos
```

## 1. Corrección primera: el header NO está desfasado, y mi afirmación era falsa

En el 1532 escribí, sobre `ucMemoryType = 0x50`:

> el header declara 1:DDR1 2:DDR2 3:DDR3 4:DDR4, el ROM USA 5, que no está declarado. Y 5 = GDDR5

**Eso era falso, y lo cazé al ir a verificar antes de escribir.** Lo que hay:

```text
  atombios.h:7815  ATOM_VRAM_MODULE_V4  // [7:4]=0x1:DDR1;=0x2:DDR2;=0x3:DDR3;=0x4:DDR4; 0x5:DDR5
  atombios.h:7857  ATOM_VRAM_MODULE_V5  // [7:4]=0x1:DDR1;...;0x5:DDR5
  atombios.h:7889  ATOM_VRAM_MODULE_V6  // MEM_TYPE_DDR2/DDR3/GDDR3/GDDR5        <-- sin numeros
  atombios.h:7920  ATOM_VRAM_MODULE_V7  // MEM_TYPE_DDR2/DDR3/GDDR3/GDDR5        <-- sin numeros
  atombios.h:7951  ATOM_VRAM_MODULE_V8  // MEM_TYPE_DDR2/DDR3/GDDR3/GDDR5        <-- sin numeros
```

El enum numérico **sí declara `0x5:DDR5`**, en V4 y V5. Lo que pasa es que **V6, V7 y V8 perdieron
los numeros y dejaron solo una lista de nombres.** La documentación no esta desfasada: **empeoro de
las structs viejas a las nuevas**, y como la que uso Polaris12 es la V8, me quedé sin la tabla.

O sea: `0x50` → nibble alto `0x5` → **GDDR5**, y eso es coherente con lo que el header dice. No hay
contradicción. Retiro la afirmación.

> **PROBADO, y con la fuente correcta:** el enum numerico de `ucMemoryType` esta en
> `ATOM_VRAM_MODULE_V4`/`V5` (7815, 7857). El V8 no lo tiene. La lectura del V8 debe apoyarse en el
> V4, no en su propio comentario, que no numera nada.

## 2. Lo que sí se puede leer del módulo de memoria

Valores medidos y su decodificacion por el comentario del producer:

```text
  campo                 valor   decode por el comentario del header
  ------------------------------------------------------------------
  ucMemoryType          0x50    [7:4]=0x5 -> GDDR5              [3:0]=0, como debe
  ucMisc                0x04    bit0=0 -> SINGLE rank
                                 bit2=1 -> burstlength 8
  ucRefreshRateFactor   0x00    [1:0]=00 -> 8 ms
  ucMemoryVenderID      0x40    [7:4]=4 Revision,  [3:0]=0 Vendor code
  ucChannelNum          0x01    1 canal  (pero ver el 1532: el mapa tiene Ch0 y Ch1)
  ucDensity             0x63    FUERA de lo declarado
  ucFIFODepth           0x61    sin unidad declarada
  ucCDR_Bandwidth       0x86    sin unidad declarada
  ucVREFI               0x00    declarado "Not used"
  ucExtMemoryID         0x00    --
```

**`SINGLE rank` es un dato de hardware, no de documentacion.** Es la primera vez que el rango de
memoria de esta placa queda fijado por una lectura del ROM y no por una inferencia. Y encaja con lo
que dijo el hallazgo anterior: `usMcRamCfg.NOOFRANKS = 0`, y `0` como exponente es `2^0 = 1` rank.
**Dos campos independientes del mismo módulo dicen lo mismo: un solo rango.**

Eso es corroboracion mutua entre `ucMisc` y `usMcRamCfg`, y no la habia visto.

## 3. Lo que queda fuera del dominio declarado, con nombre

```text
  ucDensity = 0x63 = 99
     el header solo DEFINA dos valores:  _8Mx32 = 0x13   y   _16Mx32 = 0x23
     (atombios.h:7534, 7537)
     el patron visible es  nibble alto = multiplo de densidad,  nibble bajo = 3 (= x32)
     0x13 -> 1x,  0x23 -> 2x,  0x63 -> 6x
     el comentario NOMBRA cuatro (_8Mx32, _16Mx32, _16Mx16, _32Mx16) pero solo dos tienen define
     0x63 no es ninguno de los dos definidos, y no intentoDivisionarlo para que salga 2 GB.
     NOT_DETERMINED, y la razon es que la tabla de densidades no esta completa en el header.

  ucMemoryVenderID = 0x40, codigo de vendedor = 0
     el header no declara NINGUN enum de codigos de vendedor.  Lo unico que hay es
     ATOM_VRAM_MODULE_MEMORY_VENDOR_ID_MASK = 0xF (atombios.h:7598), que es la mascara, no la tabla.
     Una GDDR5 de Hynix —que es lo que dice la cadena WEIKENG_..._HY...— con vendor code 0 no tiene
     explicacion.  O el 0 significa "sin especificar", o el campo no es lo que dice su nombre.
     NOT_DETERMINED.
```

## 4. Corrección segunda: el discriminador que nombré en el 1532 es EXTERNO

El 1532 cerro diciendo:

> El discriminador del item 1 esta aqui y con nombre: decodificar `25632` y `64B1` contra la tabla
> de deteccion de fabricante.

Fui a buscarlo y **no existe en ninguna fuente que tengamos:**

```text
  grep de WEIKENG, 25632, LEXA_D090 en el corpus del kernel, revkit/ y RXRE/   0 resultados
  tabla de deteccion de fabricante referenciada desde VRAM_Info                  ninguna
  ATOM_VRAM_INFO_HEADER_V2_2 tiene 5 punteros y ninguno es de fabricante
```

`25632` es el nombre de una macro de compilacion del proyecto de board de la BIOS. **No es una tabla
del ROM: es un identificador del fuente con el que se compilo esta BIOS, y ese fuente no lo
tenemos.** El unico `ATOM_MEMORY_VENDOR_BLOCK` del header (7440) no esta referenciado desde ningun
sitio de la tabla que estoy decodificando.

> **Mi error:** nombre un discriminador como si fuera una accion, sin comprobar que el productor
> existe. §95 lo prohibe explicitamente — "que evidencia falta, quien la produce" — y la respuesta
> aqui era **nadie, es externo**. Debi comprobarlo antes de escribirlo como siguiente paso.

**Consecuencia para la contradiccion del 1532:** los 3 testigos del ROM siguen contradicting, y el
cuarto testigo **no es resoluble con las fuentes del proyecto**. La contradiccion del ancho de bus
**queda `DEFERRED` con dependencia externa**, no `NOT_DETERMINED`: hay una razon y es que el
productor no esta aqui.

## 5. Estado del item 1 tras este hallazgo

```text
  ancho de bus        CONTRADICCION entre 3 testigos del ROM.  2 dicen 64, 1 dice 128.
                      DEFERRED: requiere el fuente de la BIOS (WEIKENG_..._GD5_25632_HY64B1).
  tipo de memoria     GDDR5                              PROBADO (dos fuentes en el ROM)
  rango               SINGLE                             PROBADO, y corroborado por dos campos
  canales             2 habilitados (0x0003)            PROBADO del ROM
  bytes por canal     32                                 PROBADO, y coherente con CHANSIZE=0
  densidad            0x63, fuera de la tabla           NOT_DETERMINED, con razon
  codigo de vendedor  0, sin tabla que lo defina        NOT_DETERMINED, con razon
  fila                4 KB                               PROBADO (1528)
  bancos/ranks        crudos y sin consumidor            PROBADO que no se usan (1528)
  nº de filas         desconocido                        NOT_DETERMINED: falta amdgpu_gc_info
```

**Siete de diez con estado, cuatro de ellos PROBADO.** El item 1 ya no es un hueco: es una tabla con
lo que se sabe y con lo que no.

## 6. Decision log (§103)

```text
DECISION    registrar que el discriminador del 1532 es externo, en vez de seguir buscandolo
WHY         tres fuentes negatives: el grep del esquema de nombres, la ausencia del puntero en
            VRAM_Info, y que ATOM_MEMORY_VENDOR_BLOCK no esta referenciado.  Tres negativos
            independientes bastan paraDEPENDENCY_EXTERNA.
ALTERNATIVA  buscar el codigo 25632 en el firmware de la SMC, por si el SMU lleva la misma tabla.
            Descartada por coste: es un binario comprimido y la pista es una cadena de compilacion,
            no un dato de runtime.  Si algun dia hace falta, se vuelve a mirar.
DISCriminante  el fuente WEIKENG_LEXA_D090_BY_GD5_25632_HY64B1/config.h, que no esta en el arbol.
CONSECUENCIA  el item 1 pasa de "3 testigos en contradiccion" a "3 testigos en contradiccion, y el
            cuarto necesita una fuente que el proyecto no tiene".  Eso es un estado, no un fallo.
REVERSIBLE  el 1532 queda intacto salvo esta seccion; el resto de sus measurements no depende de
            que el discriminador sea resoluble.
```

## 7. Lo que me llevo de hoy, que es lo que importa

Tres correcciones en una tarde, y las tres de la misma clase: **afirmé algo antes de verificar que
existía el productor del dato.**

```text
  el header no declara 0x5:DDR5      falso, si lo declara, en las structs viejas
  la tabla de deteccion de fabricante existe   no existe en ninguna fuente
  el byte remap son nibbles          falso, son 2 bits
  el conteo de comandos es 58 de 81  falso, use el puntero equivocado
```

Y la cuarta, que es la que mas me importa, no es un error tecnico sino de **planificacion**:
nombré un siguiente paso sin comprobar que fuera ejecutable. Un plan con un paso imposible no es un
plan con una dificultad: es un plan con una mentira.

> Regla, y ya van varias: **antes de escribir "el siguiente paso es X", comprobar que X existe y que
> algo en el arbol puede producirlo.** Si no, escribir `DEFERRED` con la dependencia nombrada. Cuesta
> un minuto y evita que la siguiente sesion busque algo que no esta.
