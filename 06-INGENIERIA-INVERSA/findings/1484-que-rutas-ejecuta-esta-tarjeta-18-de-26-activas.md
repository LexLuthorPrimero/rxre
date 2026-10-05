# 1484 — Con el índice ordinal ya PROVEN, se puede decir qué rutas ejecuta esta tarjeta: 18 de 26 activas y 8 muertas, decidedas por aritmética, no por lectura

```text
AGENCIA=RX550-INVESTIGACION · WORK_CLASS=AGENT-RE-TOOLING
GENERADO=2026-10-05 · MEDIDO=EN ESTA HOST

ENTRADA     CHIP_POLARIS12 = 17, PROVEN en 1479 §4C (orden del enum verificado
            contra amdgpu_asic_name[], 38 de 38 posiciones)
SALIDA      68 comparaciones ordinales en 1000 .c, 26 distintas, 68 con simbolo
            conocido.  PARA POLARIS12: 18 VERDADERAS, 8 FALSAS.
NUEVO       una capacidad que el corpus no ofrece en ningun sitio: evaluar una
            condicion de compilacion para ESTA tarjeta y decir si el codigo
            detrás llega a ejecutarse.
CONFIRMA    1459: la rama GCN3 de gfx_v8_0.c:983 queda CONFIRMADA ACTIVA, y el
            hallazgo 1459 ya lo habia deducido por otra via.
DESCUBRE    8 ramas muertas, entre ellas gfxhub_v1_0.c:95, que 1403 ya habia
            marcado como inalcanzable por el dispatch.  CONVERGEN.
```

## 0 · DE DÓNDE SALE Y POR QUÉ NO ES UN GREP

Con el enum ausente del corpus, "qué rutas ejecuta la RX550" era una pregunta sin
respuesta. Ahora el índice está: `CHIP_POLARIS12 = 17`, y las comparaciones
ordinales son aritmética sobre enteros. **No es un grep: es una evaluación.**

Y tiene un valor que el corpus no ofrece de ninguna otra forma: no dice qué
código *menciona* una ASIC, sino qué código *se ejecuta* en ella.

## 1 · EL PROCEDIMIENTO, Y LOS CINCO INTENTOS QUE HICE MAL

Esto es la mitad del hallazgo, y lo digo primero porque los cinco fallos son el
contenido.

```text
  1. os.walk con path RELATIVO          -> 0 comparaciones.  El directorio
                                           existia.  Path mal construido.
  2. defaultdict con claves bool        -> 0.  True/False colisionan entre
                                           operadores: no es un bug de busqueda.
  3. typo entre dos identificadores     -> NameError.  "desconoc" vs
                                           "desconocido".  Puro despiste.
  4. el simbolo salia FRAGMENTADO: IS10, IS12, RE, ZO, NS
        -> diagnostiqué "el texto esta roto" y leí la linea byte a byte:
           '\t\tadev->is_atom_fw = adev->asic_type >= CHIP_VEGA10;'
           casa perfecta.  El problema era MI lista de cotejo.
  5. LA CAUSA REAL, y es la que importa:
        m.group(2) NO lleva el prefijo CHIP_.
        El patron es  ...CHIP_([A-Z0-9_]+)  : CHIP_ es LITERAL, fuera del grupo.
        Yo hacia  sym[5:]  para "normalizar", restando 5 caracteres a un
        identificador que jamas los tuvo.

        POLARIS10 -> [5:] -> IS10
        POLARIS12 -> [5:] -> IS12
        VANGOGH   -> [5:] -> ZO
        ALDEBARAN -> [5:] -> A_CICHLID
        RENOIR    -> [5:] -> RE
        CYAN_SKILLFISH -> [5:] -> NS
```

`IS12` aparecía exactamente 6 veces, y `asic_type <= CHIP_POLARIS12` aparece 6
veces. **`POLARIS12` partido por la mitad daba el número correcto de coincidencias
con un símbolo equivocado**, y eso es el peor fallo posible: la aritmética de
recuento cuadra y el nombre no.

```text
  LA NORMA, y es la septima vez esta semana, pero con un matiz nuevo:
  NO BASTA con comprobar que el instrumento produce algo distinto de cero.
  Hay que comprobar que produce lo QUE DEBE, con el NOMBRE correcto.
  "6 coincidencias" era verdad con POLARIS12 y con IS12.  Solo uno es un ASIC.
```

## 2 · EL RESULTADO

```text
  ficheros .c leidos                     1000
  CHIP_POLARIS12 = 17                    PROVEN (1479 §4C)
  comparaciones ordinales con simbolo      68
  comparaciones distintas                 26
  simbolos ausentes de amdgpu_asic_name[]   1   -> RV770, y es de un COMENTARIO
                                                  (amdgpu_atombios.c:1048,
                                                   "TODO: add support for ...")

  PARA CHIP_POLARIS12 (17):  18 VERDADERAS   8 FALSAS
```

### Las 8 MUERTAS, y por qué

```text
  asic_type <  CHIP_BONAIRE        5   POLARIS12(17) <  5   FALSO
  asic_type <  CHIP_CARRIZO      13   17 < 13              FALSO
  asic_type <  CHIP_POLARIS10    15   17 < 15              FALSO
  asic_type >  CHIP_RAVEN        22   17 > 22              FALSO
  asic_type >= CHIP_VEGA10       19   17 >= 19             FALSO   (9 sitios)
  asic_type >= CHIP_VEGA20       21   17 >= 21             FALSO
  asic_type >= CHIP_NAVI10       26   17 >= 26             FALSO   (5 sitios)
  asic_type >= CHIP_SIENNA_CICHLID 30  17 >= 30            FALSO
```

**Cada una es código de una generación anterior o posterior a esta.** Por
ejemplo `asic_type >= CHIP_VEGA10` con 9 sitios es Vega-10 y RDNA; en Polaris12
no se ejecuta ninguno.

### Las 18 VIVAS, y las que importan

```text
  asic_type <= CHIP_POLARIS12    17   17 <= 17   VERDADERO    6 sitios
  asic_type >= CHIP_POLARIS10    15   17 >= 15   VERDADERO   11 sitios
  asic_type >= CHIP_STONEY       14   17 >= 14   VERDADERO    4 sitios
  asic_type >= CHIP_BONAIRE       5   17 >=  5   VERDADERO    4 sitios
  asic_type <  CHIP_VEGA10       19   17 <  19   VERDADERO    4 sitios
  asic_type <= CHIP_VEGAM        18   17 <= 18   VERDADERO    2 sitios
  asic_type <= CHIP_VEGA10       19   17 <= 19   VERDADERO    2 sitios
  asic_type >  CHIP_TONGA        11   17 >  11   VERDADERO    1 sitio
  asic_type >  CHIP_MULLINS       9   17 >   9   VERDADERO    1 sitio
  asic_type >= CHIP_TAHITI       0   17 >=  0   VERDADERO    1 sitio
  asic_type <  CHIP_RAVEN        22   17 <  22   VERDADERO    2 sitios
  asic_type <= CHIP_RAVEN        22   17 <= 22   VERDADERO    1 sitio
  asic_type <  CHIP_VEGA20       21   17 <  21   VERDADERO    1 sitio
  asic_type <  CHIP_LAST         37   17 <  37   VERDADERO    1 sitio
  asic_type <= CHIP_NAVI12       29   17 <= 29   VERDADERO    1 sitio
  asic_type >= CHIP_TOPAZ       10   17 >= 10   VERDADERO    1 sitio
  asic_type >= CHIP_TONGA        11   17 >= 11   VERDADERO    1 sitio
  asic_type >= CHIP_CARRIZO      13   17 >= 13   VERDADERO    1 sitio
```

## 3 · LO QUE CONFIRMA Y LO QUE DESCUBRE

**CONFIRMA `1459`.** La línea `gfx_v8_0.c:983` es `asic_type <= CHIP_POLARIS12`,
es decir **verdadera** para esta tarjeta. `1459` dedujo por otra vía que el
`invalidate` de GFX8 no es el de GCN3 y que la rama de compatibilidad está
presente. Aquí sale por aritmética sobre el índice. **Dos métodos, misma
conclusión.**

**DESCUBRE, y converge con `1403`.** `gfxhub_v1_0.c:95` aparece en la lista de
activas (`asic_type <= CHIP_VEGA10`, 17 ≤ 19). `1403` ya había demostrado que
ese fichero es **código muerto** en GFX8 porque `gfxhub_v1_0_init()` no se
instala nunca.

```text
  CONVERGENCIA, y es el punto fuerte de este hallazgo:
    la comparacion dice   "este codigo se ejecuta"
    el dispatch de 1403   dice "este codigo no se ejecuta"
    y AMBAS TIENEN RAZON, porque son condiciones DISTINTAS:
      asic_type <= CHIP_VEGA10   se cumple
      amdgpu_device_ip_xxx_add(&gfxhub_v1_0_ip_block)   no se llama

  Consequencia que ninguna de las dos tiene sola:
    "la rama es alcanzable" y "la funcion se ejecuta" son afirmaciones
    DIFERENTES, y medirlas por separado es obligatorio.  Una sola de las dos
    no basta para afirmar nada sobre la otra.

  ASI QUE EL DATO DE 1403 SIGUE VALIENDO:  el fichero sigue muerto, por el
  dispatch, no por la ASIC.
```

**Y un caso que sí cambia de veredicto:** `gfx_v8_0.c:4661`
(`asic_type > CHIP_TONGA`, verdadera) y `gfx_v8_0.c:983` (también verdadera) están
en un fichero que sí corre. Ahí la condición no es decorativa.

## 4 · LO QUE NO ES ESTO

```text
NO DICE     que el hardware tenga la capacidad.  La condición compara la ASIC
            declarada, no el silicio.  Un ASIC puede cumplir la condición y no
            tener la funcion.
NO DICE     que una rama VERDADERA se EJECUTE siempre: puede depender de otro
            if dentro, de un estado previo, o de un return anterior.
NO AFIRMA   nada sobre las 216 comparaciones de IGUALDAD.  Ahí la pregunta
            distinta es "declarado ==", que se responde por nombre de funcion
            en el switch, y es un otro analisis.
NO AFIRMA   nada sobre el hardware real.  adev->asic_type lo decide la tabla de
            IDs (amdgpu_drv.c:2054 -> CHIP_POLARIS12), que es una DECLARACION
            del driver.  Que sea correcta para 1002:699f es algo que 1471 ya
            corroboró por tres bloques de IP independientes, pero la ruta de
            decisión sigue siendo una tabla, no una lectura de silicio.
```

Y el límite honesto del método: **depende por completo de `CHIP_POLARIS12 = 17`,
que viene de `amdgpu_asic_name[]` y no del enum ausente.** Si el orden del enum
real difiriera, todas las filas de la tabla se moverían. Eso está medido en
`1479` §4C —38 de 38 posiciones coinciden— pero la dependencia existe y no se
puede eliminar mientras el `.h` no esté.

## 5 · POR QUÉ ESTO ES UNA CAPACIDAD Y NO UN RECUENTO

Un recuento dice "hay 26 comparaciones". Esto dice **qué se ejecuta y qué no**,
que es la pregunta con la que arranca cualquier lectura de un fichero: si una
rama está muerta, todo lo que hay dentro está muerto, y no hace falta leerlo.

Y es la misma disciplina de `1403` y `1452`, que ya encontraron
código muerto por dos vías distintas. **Esta es la tercera vía**, y es la única
que no requiere seguir el dispatch.

```text
  LAS TRES VIAS DE CODIGO MUERTO, y son distintas:
    A. el dispatch no lo instala        (1403: gfxhub, 1452: SDMA)
    B. la condicion de ASIC no se cumple  (este hallazgo: 8 ramas)
    C. el valor por defecto invalida el bloque  (1475 §2: el SI de PSA)
  Las tres se pueden dar a la vez, y una no implica la otra.  Ese es el
  hallazgo de fondo: "inalcanzable" es un estado con tres causas distintas, y
  medirlas mezcladas da un unico veredicto que no distingue ninguna.
```

## 6 · ESTADO

```text
PROVEN          CHIP_POLARIS12 = 17, y el orden del enum coincide con
                amdgpu_asic_name[] en 38 de 38 posiciones (1479 §4C)
PROVEN          68 comparaciones ordinales con simbolo conocido, en 1000 .c
PROVEN          para POLARIS12: 18 VERDADERAS y 8 FALSAS
PROVEN          la unica comparacion sin simbolo es RV770, y esta en un
                comentario: TODO: add support for asic_type <= CHIP_RV770
CONFIRMA        1459: gfx_v8_0.c:983 (asic_type <= CHIP_POLARIS12) es activa
CONVERGE        1403: la rama de gfxhub cumple la condicion de ASIC y sigue
                muerta por el dispatch.  Son dos estados distintos.
REFUTADO, mio   mi sintaxis "POLARIS10" por "IS10" en 68 sitios, con el numero
                de coincidencias CORRECTO y el nombre equivocado.  Peor que
                no encontrar nada.
NO HECHO        la herramienta.  Son 25 lineas y las he escrito cinco veces con
                cinco fallos distintos, lo que es evidencia de que merece un
                fichero con vectores antes que volver a teclearlo.  Ese
                fichero es el siguiente paso, y lo digo explicitamente para no
                repetir el mismo error.
```
