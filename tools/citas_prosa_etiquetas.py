"""ETIQUETAS A MANO de citas por numero sobre duplicado.

Son 12, y estan las 12 porque son TODAS las que el proxy marco como
`C3_reasignada_con_destino` o `INDECIDIBLE`, mas dos que marco como
`C1_contenido_univoco` y que se comproban por la misma via.  No es una muestra:
es la poblacion completa de las salidas dudosas del proxy, adjudicada leyendo
la prosa y los ficheros de destino.

El campo `clase` es la ETIQUETA, no la salida del proxy.  `prueba` dice COMO se
adjudico, porque una etiqueta sin su prueba no se puede revisar ni refutar.

FORMAS, y por que solo hay dos:

  C1  la cita sostiene lo que dice, o el numero esta citado como DATO y no como
      destino (caso 077).  No es un defecto de la cita.
  C2  la cita no tiene contenido que la discrimine: los dos ficheros del numero
      encajan igual, o no hay nada en la frase que diga cual.  Reparable por
      nombre solo si se sabe cual; aqui no se sabe.
  C3  la cita no apunta a lo que dice.
"""

ETIQUETAS = [
    # ---- num 1011: el mapa dice 1011 -> 1020, relacion=contenido ----------
    # La hipotesis del proxy era que toda cita a 1011 deberia apuntar a 1020.
    dict(citante="FINDINGS-RENUMERACIONES.md", linea=61, num=1011,
         clase="C1",
         destino="",
         prueba="Es la FILA del propio indice de renumeraciones: `| `1011` | "
                "`1020` | 3 |`. La cita va en el sitio cuyo trabajo es decir "
                "que 1011 se movio a 1020. Correcta por construccion, como la "
                "autocita de findings_index.refs_colgadas."),
    dict(citante="08-ARQUITECTURA/RESERVAS-DESYNC.md", linea=182, num=1011,
         clase="C1",
         destino="",
         prueba="El documento dice que el fichero se movio DE 1011. La cita "
                "nombra el numero viejo en su papel de numero viejo."),
    dict(citante="08-ARQUITECTURA/RESERVAS-DESYNC.md", linea=183, num=1011,
         clase="C1", destino="",
         prueba="Idem 182, misma frase partida en dos lineas."),
    dict(citante="08-ARQUITECTURA/RESERVAS-DESYNC.md", linea=283, num=1011,
         clase="C1", destino="",
         prueba="La propia frase: 'caen sobre `1011`, que esta duplicado'. Es "
                "el documento hablando DE la cita de sus lineas 182-183."),
    dict(citante="08-ARQUITECTURA/RESERVAS-DESYNC.md", linea=353, num=1011,
         clase="C1", destino="",
         prueba="'El renumerado de a750603 movio el hallazgo a 1020 y dejo "
                "`1011` con dos ficheros'. Habla del numero, no cita el "
                "hallazgo que 1011 contiene."),
    dict(citante="06-INGENIERIA-INVERSA/findings/"
                 "1039-el-repositorio-tiene-cinco-objetos-corruptos-y-la-"
                 "herramienta-que-lo-diria-exit-0.md", linea=39, num=1011,
         clase="C1", destino="1011-el-grep-de-ad8-no-puede-distinguir-y-el-isa-si.md",
         prueba="PRUEBA OBJETIVA, no de vocabulario: el hallazgo afirma 'un "
                "fichero que en el arbol de trabajo tiene 11 598 bytes' y "
                "MEDIDO el tamano de los dos candidatos es 1011-el-grep-...md "
                "= 11598 B y 1020-la-apertura-...md = 12700 B. Ademas el blob "
                "499bffcbd6f3 existe y mide 0 bytes, que es lo que el hallazgo "
                "describe. La cita va al 1011 de HOY."),
    dict(citante="06-INGENIERIA-INVERSA/findings/"
                 "1039-el-repositorio-tiene-cinco-objetos-corruptos-y-la-"
                 "herramienta-que-lo-diria-exit-0.md", linea=119, num=1011,
         clase="C1", destino="1011-el-grep-de-ad8-no-puede-distinguir-y-el-isa-si.md",
         prueba="Misma cifra, 11 598 bytes, misma prueba que la linea 39."),
    dict(citante="06-INGENIERIA-INVERSA/findings/"
                 "1035-las-tres-anomalias-del-corpus-dos-son-de-kbuild-una-"
                 "es-un-injerto-y-el-agujero-de-reproducibilidad-no-es-"
                 "ninguna.md", linea=516, num=1011,
         clase="C2", destino="",
         prueba="'Hallazgos relacionados: `1033` §R6 (confirmado y "
                "completado), `1011`, `403`, `551`, `968`'. Una lista de "
                "numeros pelados: no hay nada en la frase que diga cual de los "
                "dos ficheros 1011 es. Ni el titulo del hallazgo ni su cuerpo "
                "dicen que hallazgos son estos. DECLARABLE, NO REPARABLE: "
                "poner un nombre seria inventarlo."),

    # ---- num 272: relacion=numero, la flecha NO repara -------------------
    dict(citante="06-INGENIERIA-INVERSA/findings/"
                 "077-141-citas-que-eran-rangos-y-10-omisiones-reales.md",
         linea=32, num=272, clase="C1", destino="",
         prueba="La frase siguiente dice '**Ninguno de esos findings existe.**' "
                "El 272 esta citado como DATOS de un regex roto, no como "
                "destino. Es el mismo argumento que sostiene el registro de "
                "codigo CITA-CODIGO-EXCEPTIONS: aqui el numero ambiguo es el "
                "SUJETO del instrumento, y reescribirlo destruiria el "
                "instrumento."),
    dict(citante="06-INGENIERIA-INVERSA/findings/"
                 "273-no-hay-layout-para-la-revision-7.md", linea=96, num=272,
         clase="C1",
         destino="272-el-techo-de-overdrive-sale-de-una-lectura-fuera-de-rango.md",
         prueba="La celda cita 'overdriveLimit.engineClock = 2952790445'. Ese "
                "valor literal esta en el TITULO del hallazgo 272-del-techo-de-"
                "overdrive (medido, leido) y no aparece en el de cg_mask. El "
                "contenido discrimina y la cita va al fichero correcto."),
    dict(citante="06-INGENIERIA-INVERSA/findings/"
                 "273-no-hay-layout-para-la-revision-7.md", linea=110, num=272,
         clase="C1",
         destino="272-el-techo-de-overdrive-sale-de-una-lectura-fuera-de-rango.md",
         prueba="'no es \"esta placa va rara\", es \"el techo de...\"': el "
                "segundo 272 trata del techo de overdrive de la placa. "
                "Discrimina por contenido."),
    dict(citante="06-INGENIERIA-INVERSA/findings/"
                 "261-banco-de-pruebas-de-computo-y-el-bug-que-lo-invalido.md",
         linea=188, num=272,
         clase="C1",
         destino="272-cg-mask-y-cu-mask-son-categorias-distintas.md",
         prueba="La linea es '/sys/module/amdgpu/parameters/cg_mask lee'. La "
                "cadena `cg_mask` aparece en el titulo y el cuerpo del primer "
                "272 y no en el del segundo. Discrimina por contenido."),
]