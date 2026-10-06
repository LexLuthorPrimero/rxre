# 1578 — Ítem 2 cerrado: la colisión de `SMU7_SoftRegisters` **es irrelevante para Polaris12**, y la premisa con la que lo abrí era incorrecta en dos puntos

```text
AGENCIA=RX550-INVESTIGACION · WORK_CLASS=CLOSEOUT · NAME_COLLISION
CLASSIFICATION=EVIDENCIA-POR-COMPILACIÓN+EVIDENCIA-POR-GRAFO-DE-INCLUDES+REFUTACIÓN-DE-LA-PREMISA
MODIFICATIONS=1558 (parcial: la divergencia de 36 bytes NO era entre las que comparé)
AUTOR=AGENTE-INSTR
WRITE_EXECUTION=NONE · GPU=NONE TOUCHED · RUNTIME=NOT_RUN
DISPOSITIVO_TOCADO=NINGUNO · ni 0000:01:00.0 (1002:699f) ni 0000:00:02.0 (8086:0412)
ESCRITOS_POR_ESTA_ITERACION   ninguno (solo lectura)
CIERRA   el segundo hueco de riesgo cero de mi lista de siete
CORRIGE   mi propia premisa de partida,  en dos puntos medidos
```

## 0 · Lo que yo creía al abrir esto, y por qué estaba mal en los dos puntos

Escribí el ítem 2 así:

```text
  "La colisión de SMU7_SoftRegisters.  Dos structs,  mismo nombre,  en dos
   headers que no se pueden incluir juntos:  120 bytes con el bloque en 80
   (discrete) contra 84 bytes con el bloque en 44 (fusion).  36 bytes de
   diferencia."
```

Los **dos** números de esa frase no resisten la medición:

```text
                          yo dixecreí        MEDIDO
  sizeof, la de discrete  120 bytes          120 bytes        correcto
  bloque DRAM_LOG en 80   80                 80               correcto
  sizeof, la de fusion    84 bytes           --               sin medir nunca
  "36 bytes de diferencia" discrete vs fusion  discrete vs smu74:  CERO
```

El error de fondo es que comparé **discrete contra fusion**, y la pregunta que
importa —para esta placa— es **discrete contra `smu74.h`**. Y `fusion` es justamente
la copia que no usa nadie. Lo que sigue es la medición.

## 1 · Los tres candidatos, y cuál se enlaza con cuál unidad de compilación

Hay tres structs que se llaman igual o casi igual:

```text
  smu74.h:559-591         SMU74_SoftRegisters         43 campos   120 bytes
  smu7_discrete.h:38-88   SMU7_SoftRegisters          40 campos   120 bytes
  smu7_fusion.h:39-78     SMU7_SoftRegisters          31 campos    (no compila
                                                        contra la lista comun)
```

Quién incluye cada cabecera, medido sobre el árbol entero:

```text
  smu7_discrete.h    <-  SOLO  pm/powerplay/smumgr/ci_smumgr.h
  smu7_fusion.h      <-  SOLO  pm/legacy-dpm/kv_dpm.h
  smu74.h            <-  polaris10_smumgr.c · polaris10_smumgr.h
                         smu7_common.h · smu74_discrete.h
```

Y quién usa el **nombre**, en el árbol entero de linux (no solo `amd/`):

```text
  pm/powerplay/smumgr/ci_smumgr.c        11 ocurrencias   (todas offsetof)
  pm/powerplay/inc/smu7_discrete.h        3              (struct, cierre, typedef)
  pm/powerplay/inc/smu7_fusion.h          3              (struct, cierre, typedef)
  NINGUN OTRO FICHERO
```

**Primera conclusión, y es la que cierra el ítem para nuestra placa:** la cadena probada
en `1577` dice que Polaris12 entra por `polaris10_smumgr.c`, y ese fichero incluye
`smu74.h`. La TU de Polaris12 **nunca enlaza el nombre `SMU7_SoftRegisters`** con nada.
No hay colisión para esta placa porque **el nombre no existe en su ámbito**.

Y segundo: `ci_smumgr.h` incluye `smu7_discrete.h`, luego **el único uso real del
nombre se enlaza con la copia _discrete_**, no con la de fusión. Mi hipótesis de
partida era la contraria.

**Tercera: no existe ninguna TU que incluya las dos cabeceras que colisionan.**
`ci_smumgr.c` incluye `ci_smumgr.h`; `kv_dpm.c` y `kv_smc.c` incluyen `kv_dpm.h`. Son
pilas distintas — powerplay y legacy-dpm— y ninguna unit de compilación las junta. La
colisión **no puede morder al compilar**, porque nunca coinciden en un ámbito.

## 2 · Y ahora la medición que desmonta los "36 bytes"

Compilando contra las cabeceras reales (no structs inventados — ver §4, error mío):

```text
  smu74.h:SMU74_SoftRegisters              sizeof = 120
  smu7_discrete.h:SMU7_SoftRegisters      sizeof = 120
```

Y el campo a campo, emparejando **por offset y no por nombre**:

```text
  mismo nombre y mismo offset                       34
  mismo offset, nombre distinto (truncatura)         6
  solo en smu74.h                                    3   (112, 116, 117)
  solo en smu7_discrete.h                            0
                                                     ---
  total en smu74.h                                   43
```

**Cero divergencias de offset.** Los 6 con nombre distinto son truncaturas, y los
cinco que pude comprobar uno a uno coinciden exactamente:

```text
  smu74.h                          off    smu7_discrete.h             off
  PmTimerPeriod                       4    PmTimerP                       4
  AverageGraphicsActivity            60    AverageGraphicsA              60
  AverageMemoryActivity              64    AverageMemoryA                64
  AverageGioActivity                 68    AverageGioA                   68
  UlvEnterCount                     100    UlvEnterC                    100
```

Y los 3 que solo tiene `smu74.h` no son campos nuevos: es el **desglose de la cola de
relleno** de la otra. Directo de las dos cabeceras:

```text
  smu7_discrete.h:86       uint32_t   Reserved[3];        ->  108, 112, 116

  smu74.h:551              uint32_t   UcodeLoadStatus;   ->  108
  smu74.h:552              uint32_t   AllowMvddSwitch;   ->  112
  smu74.h:553              uint8_t    Activity_Weight;   ->  116
  smu74.h:554              uint8_t    Reserved8[3];      ->  117, 118, 119
```

**Son los mismos 12 bytes.** En `smu74.h` tienen nombre; en `smu7_discrete.h` son
relleno. Por eso los dos `sizeof` dan 120.

O sea, la formulación exacta:

```text
  SMU7_SoftRegisters (smu7_discrete.h)
      ES  SMU74_SoftRegisters  con los ULTIMOS 12 BYTES SIN NOMBRAR
```

Un prefijo estricto, campo a campo, sin una sola diferencia de layout. **La divergencia
de 36 bytes que yo traía no existe entre estas dos.**

## 3 · Y el struct que sí divergía es `PROVEN_UNUSED`

`smu7_fusion.h:39-78` no compila ni siquiera contra la lista común de campos:

```text
  error:  'SMU7_SoftRegisters' no tiene un miembro llamado 'AcpiDe...'
```

Es estructuralmente distinto: tiene `uint8_t DisplayPhy1..4Config` donde discrete
tiene `DisplayPhy1..8Config`, y mete `HandshakeDisables` en 12 donde los otros lo
ponen en 48. **Es el divergente de verdad, y no lo usa nadie** (§16 aplicado: conté
el token en el árbol entero de linux, no solo en `amd/`, y además conté
`SMU7_SoftRegisters` y no `SoftRegisters` a secas).

Que su cabecera se use (`kv_dpm.h` la incluye) es otra cosa: `kv_dpm.c` consume
`SMU7_Fusion_GraphicsLevel` y compañía. **Lo que no usa nadie es este struct.**

## 4 · Cuatro errores míos en esta ronda, todos de la misma clase

Los registro porque la tasa es el indicador, y esta ronda los tuvo todos.

```text
  1 · INVENTE UN FIXTURE.  Para los sizeof  probe  con  un struct  que escribi a
      mano en /tmp,  y me devolvio 88 bytes  y offsetof(...,UcodeLoadStatus)=36.
      CERO de esos numeros son reales.  Los borre  y  lo rehice  contra las
      cabeceras  verdaderas.  Esto es fabricar el fixture,  que esta prohibido.

  2 · DIJE QUE MI PROPIA HERRAMIENTA ESTABA ROTA  y no lo estaba.
      offsets_por_compilacion()  espera NOMBRES;  yo le pase  las TUPLAS
      (nombre, offset)  de campos_por_parseo().  Su propio camino  usa
      campos_comunes(),  que devuelve cadenas,  y por eso 1564  — que uso esa
      via-  NO se invalida.   Casi registro  un defecto inexistente.

  3 · DOS EXTRACCIONES CON REGEX MAL ESCRITAS  que devolvieron numeros
      verosimiles:  una se comio HandshakeDisables (=0,  el primero del enum)
      y la otra  borro los cinco DRAM_LOG_*  porque mi clase de caracteres
      era [A-Za-z]+:  y no admite guiones bajos.  Las dos  devuelvian algo,
      no un error.  Esta es  la clase de fallo  que  me ha costado 10 veces
      hoy.

  4 · UNA COMMA DE ANCHO COMPLETO (U+FF0C)  escrita por mi  en un script de
      Python,  y un #include <stdint.h>  que faltaba en la sonda de sizeof.
```

El punto 2 es el que más me importa: **por segunda vez en el día estuve a punto de
publicar un hallazgo falso sobre una herramienta.** La primera fue en `1575`, con la
demostración de fallo silencioso de RXRE. Las dos veces el error fue mío al invocar
la herramienta, no la herramienta. La defensa que funciona es leer la firma y el
cuerpo antes de concluir que algo está roto.

## 5 · El hallazgo lateral: `get_offsetof` devuelve 0, y 0 es un offset válido

Salió de paso y es un tipo de defecto que conviene tener nombrado.

Las dos tablas terminan en `return 0;`:

```text
  ci_smumgr.c:2318             return 0;
  polaris10_smumgr.c  (cola)   return 0;
```

Y **0 es un offset legítimo**: el primer campo de ambas estructuras es
`RefClockFrequency`, en 0. O sea que **un fallo de tabla es indistinguible de un
acierto al campo 0**, sin código de error, sin assert y sin traza.

Cobertura medida de las 15 miembros de `enum SMU_MEMBER`:

```text
                          SoftRegisters   DpmTable   total   huecos
  polaris10_get_offsetof        12            3        15/15     0
  ci_get_offsetof              11            1        12/15     3
```

Los 3 huecos de CI son `UcodeLoadStatus`, `UvdBootLevel` y `VceBootLevel`.

**Y eso no está en nuestra placa**, porque Polaris12 usa la tabla de polaris10, que
cubre 15 de 15. Un `get_offsetof` mal consultado no puede devolver un offset basura
en esta GPU. Lo registro como clase de defecto **de otras familias**, no como
problema de este target.

Y hay una lectura más fina que me gustó: el hueco de `UcodeLoadStatus` en CI **no es
un descuido del driver, es fidelidad**. Esos 12 bytes en el firmware de CI son
relleno —lo prueba §2— así que no hay offset honesto que devolver. El `return 0` es
una respuesta *equivocada*, y aun así el hueco en sí es correcto.

## 6 · Procedimiento y alcance

```text
PREGUNTA   de los dos structs que se llaman SMU7_SoftRegisters,  cual se aplica
           a Polaris12,  y con que criterio se decide
FUENTES    grep del token en el ARBOL ENTERO de linux        (prueba de alcance)
           include-closure de smu7_discrete.h / smu7_fusion.h / smu74.h
           las dos declaraciones struct,  leidas
           gcc -w con las CABECERAS REALES,  offsets por offsetof
           las dos tablas get_offsetof,  leidas enteras  y su cobertura
MEDIDO     el nombre SMU7_SoftRegisters no existe en la TU de Polaris12
           el unico uso real del nombre se enlaza con la copia DISCRETE
           ninguna TU incluye las dos cabeceras que colisionan
           sizeof = 120 en smu74 y en smu7_discrete
           34 campos mismo nombre y offset · 6 truncaturas al mismo offset
           3 campos solo en smu74 = desglose de Reserved[3] de discrete
           0 campos solo en discrete ->  discrete es prefijo estricto de smu74
           smu7_fusion no compila contra la lista comun  y no lo usa nadie
           get_offsetof devuelve 0 en fallo  y 0 es offset valido
           polaris10 cubre 15/15 de enum SMU_MEMBER;  ci cubre 12/15
DESVIO MIO  un fixture inventado que me dio numeros falsos
           un diagnostico erroneo de "mi herramienta esta rota"
           dos regex que devolvieron algo en vez de fallar
           una coma de ancho completo
DISPOSITIVO  NINGUNO.  i915 ausente,  amdgpu intacto
RUNTIME      NOT_RUN
```

**Lo que queda abierto de este ítem, y es poco:** por qué el driver mantiene dos
nombres para lo que es el mismo layout en dos familias. No es un problema, pero es
una decisión de diseño que no está justificada en el código y que hace que un grep
por el nombre devuelva la copia equivocada — que es exactamente lo que me pasó a mí.
Costo de arreglarlo: no lo toco, y no bloquea nada.

## 7 · Lo que sigue

```text
  huecos de riesgo cero que quedan:   3 · 4 · 5 · 6 · 7   (el 1 y el 2, cerrados)
  el 4 ya esta medio hecho aqui:  la comparacion por offset  recupera las
       truncaturas de nombre  que 1564 no podia preguntar.  Falta extenderla
       a las copias smu71/smu72/smu73/smu75,  donde 1564 si encontro 6
       divergencias con corte en 76
  y sigue en pie lo unico que cierra soft_regs_start:  el valor de
       SMC_RAM[0x20030]  por dos accesos de registro  que necesitan tu OK
```