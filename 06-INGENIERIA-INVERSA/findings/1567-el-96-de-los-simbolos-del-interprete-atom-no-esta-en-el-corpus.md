# 1567 — el 76% de los símbolos que necesita el intérprete ATOM no están en este corpus, y eso acota lo que el ROM puede probar

```text
AGENCIA=RX550-INVESTIGACION · PARTE=2/RESET-RECOVERY · HALLAZGO 7 de la parte
CLASSIFICATION=HUECO-DE-CORPUS-CUANTIFICADO+CORRECCION-AL-1561+FONTE-DEL-BLOQUEO
WORK_CLASS=AGENT-MAIN/RE · WRITES=NONE · MODIFICATIONS=0
WRITE_EXECUTION=NONE · RUNTIME=NOT_RUN · GPU INTACTA (0000:01:00.0)
TRACK=STATIC + una lectura de ROM · CERO HARDWARE · Intel no tocada
GENERADO=2026-10-05
AFECTADO=1561 (LO ACOTA y lo estrecha) · 1530 (esto explica su final) · 1548 (el cierre de la parte 1)
ESTADO=PROBADO · amdgpu_atom_asic_init ejecuta UNA tabla, ATOM_CMD_INIT, con un stream de DOS dwords
       · y se sale con return 1 SIN ejecutar nada si falta cualquiera de los dos relojes
       · CORRECCION AL 1561: dije "replay de las tablas ATOM" en plural.  Es una tabla, dos
         parametros.  Y su alcance real depende de una capa que no esta en el corpus.
       · MEDIDO: atom.c usa 79 simbolos ATOM_*; en include/ hay 1216 definidos, pero solo
         3 de los 79 estan.  FALTAN 76.  La capa de comandos y bloques del ROM no esta.
       · por eso el 1530 no pudo nombrar las 160 escrituras: los DATOS estan, el CODIGO no
```

## 1. De donde vengo, y por que este es el hallazgo

El `1561` cerro diciendo, textual:

> *"el unico mecanismo de re-inicializacion del hardware en un cuelgue es **volver a ejecutar
> ese mismo ROM**"*

Y en su seccion de estado:

> *`el unico mecanismo de re-inicializacion del hardware en un cuelgue es volver a ejecutar ese
> mismo ROM`*

Y terminaba diciendo, y esto es lo honesto:

> *"No he leido `amdgpu_atom_asic_init` ni el parser ATOM. Sé que se llama y bajo que compuerta
> entra; **no sé** que tablas ejecuta ni en que orden."*

Pues bien: ya lo he leido. Y lo que ejecuta es mucho menos de lo que la palabra "replay" sugiere.

## 2. La funcion, entera

```c
  /* atom.c:1613-1630, amdgpu_atom_asic_init */
  int amdgpu_atom_asic_init(struct atom_context *ctx)
  {
          int hwi = CU16(ctx->data_table + ATOM_DATA_FWI_PTR);
          uint32_t ps[16];
          int ret;
          memset(ps, 0, 64);
          ps[0] = cpu_to_le32(CU32(hwi + ATOM_FWI_DEFSCLK_PTR));
          ps[1] = cpu_to_le32(CU32(hwi + ATOM_FWI_DEFMCLK_PTR));
          if (!ps[0] || !ps[1])
                  return 1;                                    /* <-- no ejecuta nada */
          if (!CU16(ctx->cmd_table + 4 + 2 * ATOM_CMD_INIT))
                  return 1;                                    /* <-- tampoco */
          ret = amdgpu_atom_execute_table(ctx, ATOM_CMD_INIT, ps, 16);
          if (ret)
                  return ret;
          memset(ps, 0, 64);
          return ret;
  }
```

**Una tabla. Dos parámetros. Dos salidas tempranas que devuelven 1 sin hacer nada.**

> **PROBADO: el "replay del VBIOS" de la recuperación de esta placa es la ejecucion de UNA tabla,
> `ATOM_CMD_INIT`, con un stream de parametros de DOS dwords: el reloj SCLK por defecto y el reloj
> MCLK por defecto.** Y **no ejecuta nada** — devolviendo error — si el ROM no declara alguno de
> los dos relojes.

**CORRECCION AL 1561.** Escribi "replay de las tablas ATOM del VBIOS", en plural, y esa formulation
hacia pensar en una reinicializacion sustancial. Es una tabla con dos argumentos. El 1561 no era
falso en su conclusion —el replay es el mecanismo, y el reset es vestigial, eso se sostiene— pero
**su alcance estaba inflado**, y un lector que lo tomara al pie de la letra creeria que la placa
se reinicializa por completo cuando lo que se ejecuta es un unico comando.

## 3. Y el guard convierte la pregunta en aritmética

Que la recuperacion del respaldo haga algo **depende de dos dwords del ROM**:

```text
  ps[0] = DEFSCLK  (reloj SCLK por defecto)   != 0 ?
  ps[1] = DEFMCLK  (reloj MCLK por defecto)   != 0 ?
```

Si alguno es cero, `return 1` y el respaldo no hace nada — o peor, **reporta que la inicializacion
ATOM fallo** (`dev_warn("asic atom init failed!")`, `amdgpu_device.c:5198`) sin llegar a ejecutar.

Eso es un test binario y concreto sobre el ROM de esta tarjeta. Y para hacerlo necesito cuatro
offsets. Vamos a ver si estan.

## 4. Y aqui esta: no estan

```text
  atom.c:1614   CU16(ctx->data_table + ATOM_DATA_FWI_PTR)
  atom.c:1620   CU32(hwi + ATOM_FWI_DEFSCLK_PTR)
  atom.c:1621   CU32(hwi + ATOM_FWI_DEFMCLK_PTR)
  atom.c:1625   CU16(ctx->cmd_table + 4 + 2 * ATOM_CMD_INIT)
```

Y en `drivers/gpu/drm/amd/include/`:

```text
  ATOM_DATA_FWI_PTR      0 ocurrencias
  ATOM_FWI_DEFSCLK_PTR   0 ocurrencias
  ATOM_FWI_DEFMCLK_PTR   0 ocurrencias
  ATOM_CMD_INIT          0 ocurrencias   (de hecho, ATOM_CMD_* : 0 ocurrencias en atombios.h)
```

**Cuatro simbolos que el codigo usa, ninguno definido.** Y no es un caso aislado, asi que lo medí
entero:

```text
  simbolos ATOM_* que USA atom.c                        79
  simbolos ATOM_* DEFINIDOS en include/                1216
  USADOS POR atom.c Y NO DEFINIDOS                      76          <-- 96% de lo que usa
```

Los primeros que faltan:

```text
  ATOM_ARG_FB   ATOM_ARG_ID   ATOM_ARG_IMM  ATOM_ARG_MC   ATOM_ARG_PLL
  ATOM_ARG_PS   ATOM_ARG_REG  ATOM_ARG_WS   ATOM_ATI_MAGIC  ATOM_BIOS_MAGIC
  ATOM_CASE_END  ...
```

Y los ficheros que deberian contenerlos son muñones:

```text
  include/atom-types.h    42 lineas   (solo alias de tipo: USHORT, ULONG, ...)
  include/atom-bits.h     48 lineas
  include/atom-names.h   100 lineas
```

**>Hay 1216 simbolos `ATOM_*` definidos, asi que el corpus no esta vacio de ATOMBIOS: lo que falta
es una capa concreta, la de comandos y bloques.**

## 5. Y eso explica el final del 1530, que estaba abierto sin que se supiera por que

El `1530` cerro la parte 1 y dejo escrito, textual:

> *"reparte los datos. Decodificarlo es el siguiente paso natural y **NO es un
> `ATOM_INIT_REG_BLOCK`**"*

Y el `1548` cerro la parte 1 con 6 de 9 items PROVEN y uno —justo el de las escrituras sin
nombre— SATURATED por falta de discriminantes.

> **PROBADO por explicaicion: las 160 escrituras sin nombre del ROM no se pudieron identificar
> porque identificarlas exige la capa que falta.** Los *datos* del ROM si estan —`ATOM_VRAM_MODULE_V8`
> esta en `atombios.h`, y el 1540 midio `sizeof(SMU7_Fusion_DpmTable)`
> contra el ROM—; lo que no esta es el *codigo* del ROM: los bloques y comandos queitics dicen **que
> registros se escriben y en que orden**.

Es decir: **todo lo que la parte 1 pudo establecer sobre el ROM vino de tablas
de DATOS. Nada vino de tablas de CODIGO.** Y eso no era casualidad del autor de los hallazgos: es
la forma del hueco.

> **Lo que si puedo afirmar es el limite, y es un limite util: en este corpus se puede leer **que
> datos** declara el ROM de esta tarjeta, y **no se puede leer que hace** con ellos.** Cualquier
> afirmacion sobre el comportamiento del ROM —que registers toca, en que orden, con que valores— es
> `NOT_DETERMINED` por falta de la capa, no por falta de mirar.

## 6. Lo que si se puede leer del ROM, y es un buen corroborante del 1539

Con `tools/atom_chain.py` (autotest: 79 casos, 0 fallos, revalidado hoy):

```text
  tamano del VBIOS      58880 bytes (0xE600)
  base   = CU16(0x48)   0x021C     [ATOM en base+4: b'ATOM']
  data_table            0x97F2
  PowerPlayInfo         0x9C0A     (mdt[15])
  usStructureSize       778
```

Y las cadenas legibles del propio ROM:

```text
  D09001 Lexa XL A0 GDDR5 128bit 2GB 214e/300m
  (C) 1988-2010, Advanced Micro Devices, Inc.   ATOMBIOS   BK-AMD VER015.050.002.001.000000
  hy64b-3.bin        05/12/21 03:53
```

> **CORROBORACION INDEPENDIENTE del 1539: la cadena de placa del ROM dice `GDDR5 128bit`.** El
> 1539 concluyo que el bus es de 128 bits por cuatro fuentes concantes, y una de ellas era
> precisamente esta cadena. **El ancho de bus de esta tarjeta esta escrito dentro de su propio
> firmware**, lo cual es lo esperable y por tanto no añade independencia real — pero si confirma
> que el ROM de la captura es el de esta placa y no el de otra.

Un detalle de forma que conviene registrar, porque es una trampa de lectura: **el fichero se llama
`amdgpu_vbios.txt` y no es texto, es un binario de 58880 bytes.** La extension miente. Y el magic
`0x55AA` esta en los dos primeros bytes en orden big-endian, asi que leerlo con un `cu16` little-endian
da `0xAA55` y parece que el ROM no es ATOM. Me paso eso antes de mirar la herramienta.

## 7. Donde queda la parte 2 tras este hallazgo

```text
  el metodo de reset                     PROBADO  MODE1                    1551
  el reset no resetea                    PROBADO  return 0 sin escribir    1557
  el unico reset real                    PROBADO  mmSRBM_SOFT_RESET        1559
  el respaldo                            PROBADO  replay del VBIOS         1561
  el replay, en cuanto                    UNA tabla, ATOM_CMD_INIT         este
  el replay, con que parametros          2 dwords: DEFSCLK y DEFMCLK      este
  el replay, cuando no hace nada         si cualquiera de los dos es 0    este
  si el replay hace algo en esta placa   NOT_DETERMINED                    este
  que ejecuta ATOM_CMD_INIT              NOT_DETERMINED: falta la capa     este
  el linter de texto                     doclint, ya existia              1565
  cobertura de doclint                    6.6% por defecto, ya medida      1083
RIESGO        ninguno.  Lectura de ROM y de cabeceras.  Cero escrituras.
LIMITE        todo lo de este hallazgo es sobre el CODIGO, y la conclusion es negativa:
              lo que falta no se puede deducir de lo que hay.  Eso es §16, no §62.
LIMITE        el autotest de atom_chain se revalido antes de usar (§22) y pasa 79/79, pero su
              alcance es la capa de DATOS.  En la de CODIGO no dice nada, y no puede.
```

## 8. Decision log (§103)

```text
DECISION    publicar el hueco del 96% Y corregir el alcance del 1561, en el mismo hallazgo
WHY         Los dos hechos son el mismo hallazgo: el 1561 afirmo una capacidad (replay) que al
            medirla resulta ser una tabla, y la razon por la que no se puede medir mas es que
            falta la capa.  Publicarlos juntos evita que alguien lea el 1561 como "se
            reinicializa todo" y se llevar esa idea a un driver propio.
ALTERNATIVA  publicar solo la correccion del 1561 y dejar el hueco para otro dia.  Descartada:
            la correccion sin la causa es inutilizable; no dice que hacer a continuacion.
ALTERNATIVA  buscar los macros fuera del proyecto, en un kernel instalado, y cerrar el hueco.
            Descartada por ahora: es una dependencia externa y §13 dice que un bloqueo no es
            una parada.  Queda como el camino mas barato si eldueño lo quiere.
DISCriminANTE  para el guard de los relojes haria falta leer dos dwords del ROM, y para eso
            falta ATOM_DATA_FWI_PTR.  Con la capa, el discriminante es inmediato.
CONSECUENCIA  la pregunta "que hace MODE1 por debajo", que abrio el 1551, esta contestada hasta
            donde el corpus permite: una tabla, dos parametros, y un guard binario.
REVERSIBLE  nada mutable.  Y el 1561 no se toca: se corrige hacia delante, como se hizo con
            el 1559.
```

## 9. Una reflexion que este hallazgo vuelve a merecer

Tres hallazgos seguidos —`1565`, este, y el `1530` antes— dicen lo mismo de tres maneras
distintas:

```text
  1565  no lei lo que ya estaba escrito, en el tema donde mas habia escrito otro
  1567  no habia leido el alcance exacto de lo que afirme en 1561, y por eso lo escribi
        en plural
  1530  las 160 escrituras quedaron sin nombre porque la capa que las nombra no esta,
        y eso no se savia al escribirlas
```

Y en los tres casos **el defecto no fue de razonamiento**: fue de alcance. Escribí sobre lo que
creía que era el objeto, y el objeto era más pequeño o más grande de lo que creía.

La conclusión operativa es incómoda y la dejo escrita: **en este proyecto, el error por defecto
no es afirmar de más por arriesgarse, es afirmar del tamaño equivocado por no haber medido el
tamaño.** Y medir el tamaño aquí significa abrir la función y contarla, que es exactamente lo
que el `1561` decía no haber hecho y este hallazgo hace.

Es la tercera vez que la lección es "termina la lectura". Voy a dejar de escribirlo como
conclusión moral y empezar a tratarlo como comprobacion: **antes de escribir un hallazgo sobre una
función, haberla ledo entera y haber contado lo que hace.** Es barato y es lo que evita esto.