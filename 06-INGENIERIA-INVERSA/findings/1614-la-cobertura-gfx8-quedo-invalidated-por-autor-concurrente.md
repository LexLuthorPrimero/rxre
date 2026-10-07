# 1614 — La cobertura GFX8 quedó invalidada por un autor concurrente, y mi procedencia no tenía forma de verlo

```text
CLASSIFICATION=CONTAMINACION_DE_MEDICION+DEFECTO_DE_INSTRUMENTO+AUTOCORRECCION
WORK_CLASS=RXRE-013-RECOBERTURA-GFX8
AUTOR=AGENTE_RXRE013 (esta sesión)
FECHA=2026-10-07
TARGET=0000:01:00.0 · 1002:699f@c7 · CHIP_POLARIS12 · gfx_8_0
QUESTION=¿qué miden exactamente los 2.633 registros nativos del diccionario GFX8, con la
          unidad y la procedencia correctas, contra el árbol activo?
MODIFICATIONS=tools/rxre_cobertura_gfx8.py (RAIZ derivada de __file__, verify,
              procedencia, guard de productor, estado de la corrida)
              +2 tests y 2 Moleculares de mutación, todos nuevos
              +1 artefacto INVALIDADO y su procedencia marcada
WRITE_EXECUTION=NINGUNO · sin MMIO, sin hardware, sin firmware, sin VBIOS,
                sin tocar Intel, sin tocar display
RUNTIME=READ_ONLY sobre fuente; la corrida es una LECTURA de RXRE
```

## OLD_ARTIFACT

```text
  artifacts/rxre_cobertura_gfx8.jsonl
  OLD_ROOT       /home/lucas/Escritorio/RX550-INVESTIGACION   (otro árbol)
  OLD_HEAD       3e2ef2c
  OLD_SEMANTICS  byte_offset como unidad canónica;  dword_index = valor >> 2
  OLD_COUNT      2633 líneas,  {ok: 2633}   (100 %)
  ESTADO         HISTORICAL / INVALIDADO_PARA_SEMANTICA_VIGENTE
  NO SE BORRA
```

Lo produjo un script con `RAIZ = "/home/lucas/Escritorio/RX550-INVESTIGACION"`
— una constante absoluta a un árbol que tiene **otro** RXRE (sin
`core/relations.py`, y con el `reg_resolve.py` que invertía la unidad). No era
solo una ruta: cambiar `RAIZ` no cambiaba el RXRE medido, porque `sys.path`
resolvía por otra parte.

## NEW_ARTIFACT

```text
  artifacts/rxre_cobertura_gfx8_20261007_INVALIDADA_por_concurrencia.jsonl
  NEW_ROOT       /home/lucas/Escritorio/rxre
  NEW_HEAD       ffb34d9  (el que la corrida tenía al terminar)
  NEW_SEMANTICS  valor = índice dword de registro;  byte offset = valor * 4
  COUNT          2633 líneas,  {ok: 402, SIN_CHOSEN: 975, error: 1256}
  ESTADO         INVALIDADA
```

## El cambio de herramienta, que era lo que había que hacer

```text
  RAIZ         derivada de __file__, con override --raiz= y RXRE_ROOT
  Candados     verifica_arbol(): compara la ruta ABSOLUTA del 'cli' importado
               contra RAIZ y se niega (INVALID_TREE) si no encaja.
               Tres pre-chequeos: cli.py, el diccionario, tools/reg_resolve.py
  Unidad       cada línea declara su unidad y lleva el byte offset DERIVADO
               por * 4 a partir del valor ELEGIDO
  Procedencia  sidecar .meta.json: source_root, origen, git head, rxre
               importado, sha256 de reg_resolve y del productor, generación,
               timestamp, comando, denominador con su entrada, reparto
  Ruta muerta  el fallback .get("byte_offset") se queda pero SE CUENTA:
               chosen es el hit del #define {file, rel, line, value, text};
               byte_offset vive en el out hermano y nunca estuvo dentro de
               chosen.  Medido, no leído: 0 disparos en 2.633.
```

## Por qué la medición es inválida, con evidencia

```text
  reparto      {ok: 402, SIN_CHOSEN: 975, error: 1256}
  primer error en la línea 1378,  y  los 1.256 son consecutivos hasta el final

  reg_resolve_sha256 registrado al final de la corrida   431b884b...
  reg_resolve.py en HEAD (b3188cc, 53f2625, ffb34d9)    ec408d71...
  reg_resolve.py en disco al detectarlo                 3952eb91...

  el sha registrado NO era ninguno de los dos estados estables
  -> otro autor estaba editando tools/reg_resolve.py mientras la corrida lo
     medía.  y 20+ ficheros más del árbol tenían cambios sin commitear.
```

**Mi defecto.** La procedencia tomaba el sha **una vez** y **al final**. Es
decir: describía un productor que no había producido ninguna fila, y el
cambio ya había ocurrido. Sin la huella de fin de carrera no había forma de
distinguirlo, y un reparto con 48 % de filas `error` se leía como una cifra.

## El guard que lo cierra

```text
  huella_productor()   reg_resolve (sha256) + digest de tools/rxre/**/*.py
  se toma ANTES de la primera consulta
  se comprueba cada 50 filas,  y otra vez al final
  si cambia               -> la corrida se marca INVALIDADA,  con la FILA
  si hay filas no medibles -> la corrida se marca INVALIDADA
  estado y motivos_de_invalidez son parte de la MEDICION,  no un comentario
```

`test_cobertura_root013.py` 74 checks verdes (árbol, unidad, procedencia,
override, candados) y `test_cobertura_drift015b.py` 20 checks, **9/9
mutaciones muertas**, cada muerte atribuida a una aserción concreta — entre
ellas «la fila del cambio está localizada», que es lo que distingue un guard
de verdad de una etiqueta.

## VALIDACIÓN

```text
  denominador por tres parsers independientes
    regex del script   2633
    grep -cE           2633
    awk                2633    sin nombres duplicados
  unidad, contra el productor y no contra el número
    mmSMC_IND_INDEX_11  value 0x1ac = dword_index 0x1ac = byte 0x6b0
    mmSMC_IND_DATA_11  value 0x1ad = dword_index 0x1ad = byte 0x6b4
    >> 2 los habría fundido en 0x6b:  por eso está prohibido
```

## DIFFERENCE_CLASSIFICATION

```text
  OLD vs NEW    ROUTING_CHANGE + ARTIFACT_STALE
                la OLD se midió contra otro árbol, con otro RXRE
  raiz          ROUTING_CHANGE   corregido: RAIZ derivada de __file__
  unidad        SEMANTIC_CHANGE  ya REVISA en 1604/1607; el artefacto viejo
                                  se mide con la unidad invertida
  reparto       NO CLASIFICABLE  la NEW está INVALIDADA
```

## NEXT_STATE

```text
  La reejecución de 2.633 registros está BLOQUEADA mientras otro autor siga
  editando tools/reg_resolve.py.  No se relanza a ciegas:  el guard la
  invalidaría,  y eso sería tiempo perdido.

  Y cuando se relance, el resultado que se espera es distinto según la
  semántica que esté implementada:
    · con la regla global de fb8da65      -> 153 ok / 2.480 SIN_CHOSEN
    · con la regla de aplicabilidad (1615) -> 2.633 ok
    · con la regla de CONFLICT de 1616    -> 2.633 ok,  y 0 conflictos
      semánticos,  que es lo que el corpus de esta placa da

  La cifra que salga hay que confrontarla con el MODELO de 1616,  símbolo a
  símbolo,  no con un reparto agregado:  ya se hizo así sobre las primeras 505
  líneas y dio 0 desacuerdos con la regla global.
```