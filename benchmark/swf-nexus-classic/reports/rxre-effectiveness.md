# Evaluación de efectividad de RXRE como instrumento de RE

Clasificación del cuello de botella de cada descubrimiento
mayor, según las categorías del directive de continuación:
`AI_REASONING`, `RXRE_RETRIEVAL`, `EVIDENCE_INGESTION`,
`PROVENANCE`, `TOOLING`, `RUNTIME_DEPENDENCY`, `UNKNOWN`.

## Resumen ejecutivo

RXRE fue **efectivo** para la ingeniería inversa estática
del SWF: recuperó la estructura del contenedor, la regla de
longitud AVM1 de este dialecto no estándar, la semántica de
`0x4E`/`0x4F` por balance de pila, y el mapeo
propiedad<-multiplicador. El **cuello de botella dominante
fue TOOLING** (el simulador de pila sin rama `else` que
produjo la falsa frontera "saturada"), no AI_REASONING: la
capacidad de razonamiento existía, pero una herramienta
defectuosa la desvió hacia una conclusión falsa durante una
sesión completa.

## Cuello de botella por descubrimiento

| # | Descubrimiento | Cuello de botella | Detalle |
|---|---|---|---|
| 1 | Estructura SWF (CWS, RECT, 30fps, 850×530) | RXRE_RETRIEVAL | Requirió un parser (`swfparse.py`); el formato está documentado, bajo coste. |
| 2 | Regla de longitud AVM1 (`code>=0x80`→u16 len) | AI_REASONING | Derivada de patrones de bytes; la insight clave que desbloqueó todo el desensamblado. |
| 3 | `Push=0x96` (no estándar; `0x9C`=0 veces) | AI_REASONING | Reconocer que la tabla AVM1 oficial NO aplica a este dialecto. Sin esto, todo el análisis habría sido basura. |
| 4 | Tipo-6 = float32+uint32 (NO Double) | AI_REASONING | Refutación de la hipótesis Double por rango de valores (no astronómicos). |
| 5 | `0x4E`=GetMember, `0x4F`=SetMember | AI_REASONING | Prueba por balance de pila (pop/push counts). **El breakthrough decisivo.** |
| 6 | Formato ConstantPool(0x88) | TOOLING | El offset de `walk_actions` estaba desplazado (RXRE-SWF-012 tenía el Count en la posición 2; es la 1). Corrección de herramienta. |
| 7 | Resolución de propiedades (pool de 908) | RXRE_RETRIEVAL | Construir el resolvedor `resolve_constant`; mecánico una vez corregido el formato. |
| 8 | Mapeo propiedad<-multiplicador | AI_REASONING | Patrones EXACTOS STORE/RMW. **Corrigió** asociaciones falsas del heuristico de proximidad. |
| 9 | Funciones `tick`/`createWound` (0x9B/0x8E) | RXRE_RETRIEVAL | Decodificación de DefineFunction; mecánico. |
| 10 | Falsa frontera "SATURADA" (RXRE-SWF-027) | **TOOLING** | **El fallo crítico:** `avm1_trace.py` no tenía rama `else` → trataba opcodes desconocidos como no-ops → corrompía la pila → las constantes "desaparecían" en "llamadas no identificadas". Un defecto de herramienta, no de razonamiento. |
| 11 | Asociaciones falsas (myGameSpeed, smgAimTimer…) | AI_REASONING | El heuristico de "propiedad más cercana" era insuficiente (el multiplicador lo consumían opcodes intermedios). Corregido por el análisis de patrón exacto. |
| 12 | Estados RXRE inválidos + duplicados ×5 | PROVENANCE | `register_claims.py` usaba `CORROBORATED`/`PROVEN_ABSENT` (no en `ESTADOS_RESEARCH`) y se ejecutó 5 veces. Brecha de provenance/ingestión. |
| 13 | Validación diferencial | RUNTIME_DEPENDENCY | Sin runtime Flash local (verificado). Dependencia externa genuina; desbloquea RXRE-SWF-014. |
| 14 | Decodificación de salto + efectos netos por CFG | AI_REASONING | Se construyó `avm1_cfg.py`: CFG con `0x99`=incondicional/`0x9D`=condicional, destino=`pos+2+int16` (100%). El **consenso por script** (no el sistema global, que es inconsistente por opcodes dependientes del valor) determinó `0x9D`=-1, `0x40`=-1, `0x49`=-1, `0x3E`=-1, `0x9F`=-1, `0x42`=0, `0x81`=0, `0x8C`=0. Método validado (0x4E=-1 en 24/25). |
| 15 | 0x52 CallMethod / 0x87 StoreRegister | EVIDENCE_INGESTION | El análisis de profundidad (solo cuenta push/pop) **no basta** para opcodes cuyo efecto depende de valores en la pila. Se clasificaron correctamente como NOT_DETERMINED (RXRE-SWF-045) en lugar de forzar un valor falso. |
| 16 | uint32 tipo-6 NO es función del float32 | **AI_REASONING** | Se REFUTÓ la fórmula `u=((b&0xFFFFF)*0x100001+128)>>8` (verificada a mano en 6 pares) mediante **inversión de fórmula** sobre los 61 pares: exacta solo 27/61; 9 pares sin inversa. El uint32 es un **valor separado** (fracción 0.32). Demuestra que una fórmula "verificada en pocos casos" puede ser coincidencia — hay que probarla sobre TODO el corpus. |
| 17 | Cuerpos de función = tokens nativos (NO AVM1) | **TOOLING + AI_REASONING** | Corrigió `decode_define_function` (no leía `regCount`+`flags` de DefineFunction2 ni la ausencia de `regIdx` en DefineFunction — bug de **herramienta** que desalineaba params/cuerpo). Al decodificar correctamente los 1342 DefineFunction/DefineFunction2: **todo cuerpo = 2 bytes**; **322 empiezan con opcode ≥0x80** (imposible para acción larga en 2B); **306 sin End**. **REFUTA** la premisa "desensamblar tick() para la fórmula": `tick()`=token `0x44`. Las **firmas** revelan el modelo (combate: inDamage/inArmor/inWeapon/inAttacker/inRange/inHeadshot/inKnockback/inBlock/inKillShot; stats: inStr/inDex/inTac/inEnd/inLead/inAwr + 8 armas; física: inX/inY/inXSpeed/inYSpeed/inRot/inRotSpeed/inBounce/inFloor/inAlpha/inScale). La fórmula exacta **no** está en los cuerpos. |
| 18 | Ejecutor simbólico recupera fórmulas del stream principal; 0x47=NIP | **TOOLING + AI_REASONING** | Se construyó `avm1_sym.py` (ejecutor simbólico lineal con pila de expresiones + `expr_depth` para el marco de `CallMethod`). Se descubrió que **`0x47` = NIP** (elimina el elemento debajo del tope) por **balance de pila**: en el patrón de modificadores, con no-op la pila crece +1 por sentencia (no acotado); con NIP el balance neto es 0. Esto recupera, **resueltas por pool**, las fórmulas estadística→modificador (`modDmg=statSTR/15`, `modArmor=statEND/15`, `modSpeed=statDEX/45`, `modRecharge=statTAC/10`, `modAllySmart=statLEAD/15`, `modHurtTactics=statAWR/50`), movimiento (`myAccel=mySpeed/4`, `mySpeedRight=(intendedX-_x)/6`), daño (`myDamage*=3`), armadura-fuente (`myHeadArmor=myHat.myArmor`, `myBodyArmor=myShirt.myArmor`). **La mitigación de armadura NO se recupera**: está en la rutina nativa (token, #17). Demuestra que el "cuello" de los cuerpos nativos se rodea ejecutando el stream principal simbólicamente. |
| 19 | Fórmula de aplicación de daño SÍ está en el stream principal | **AI_REASONING + TOOLING** | Ejecutando el stream principal simbólicamente (#18) y trazando el bytecode, se recuperó la **aplicación de daño de combate**: `myAttackTarget.myHealth = myAttackTarget.myHealth - (myDataRef.myUnarmed.myDamage / 4)`. Confirmada por **traza de bytecode** (script 1627, acciones 31869-31884) + resolución de pool (`LK:203=myAttackTarget`, `LK:62=myHealth`, `LK:12=myDataRef`, `C16:546=myUnarmed`, `C16:481=myDamage`) + **balance de pila neto 0**. El objetivo pierde salud = **daño desarmado / 4**. Esto refuta la suposición de que TODA la lógica de combate está en la rutina nativa: la **aplicación** (resta a la salud) está en el stream; solo el **cómputo** del daño de arma (con mitigación de armadura) está en la nativa `inDamage/inArmor`. Fórmulas relacionadas: `recoilTimer=weapon.myDamage*weapon.myShots`, `skillPoints=myLevel*3`, `myDataRef.myHealth=myHealthMax/2`, `myGun.myHealth-=2`, `targetHealthY=5*(myHealth/myHealthMax)`. |
| 20 | Convención de `SwainMath.randomNumber` PROVEN en 418 sitios; corrige el rango del daño | **AI_REASONING + TOOLING** | Se descobriu que el daño se **aleatoriza** y que el **crítico de headshot está gated por el perk `perkHeadshotCrits`** (`havePerk(perkHeadshotCrits,2,MadnessDataFile)`): `r18=randomNumber(2,120,200)/100 = [1.20,2.00]`, y `r18=1` para `amSpecial && myCat=="melee"`. Para fijar la convención de argumentos se escanearon los **418 sitios de llamada** de `SwainMath.randomNumber` (**179 firmas**): la convención es `randomNumber(precision, lo, hi)` → valor en `[lo,hi]` redondeado a `precision` decimales. De las llamadas con los 3 args enteros comparables, **101** son verificables con **0 violaciones** de `lo<=hi`. **El escaneoRiginal de RXRE-SWF-051 tenía el rango del daño ERRÓNEO**: los args se empujan en orden INVERSO (AVM1), así que `Push[R3,-2,2,SwainMath]` declara `randomNumber(2,-2,R3)` → rango `[-2,R3]`, **NO** `[R3-2,R3+2]`. Fórmula corregida: `damage=Math.floor(randomNumber(2,-2,totalFrameDamage)/4)` → `[0, TFD/4]`. RXRE-SWF-051 pasa a PARTIAL con `superseded_by`. Demuestra el valor de la validación cruzada: un único sitio de llamada sugiere una convención; **418 sitios la prueban**. |

## Brechas de RXRE encontradas y cómo se repararon

1. **TOOLING (la más importante):** el simulador de pila
   `avm1_trace.py` carecía de rama `else`. Esto es un
   defecto de *contrato de herramienta* (§22/§26): un
   simulador que descarta opcodes desconocidos como no-ops
   viola "exit 0 != valid result" — producía una traza
   corrupta con éxito aparente. **Reparación:** re-derivar
   `0x4E`/`0x4F` por balance de pila estático (sin
   depender del simulador defectuoso) y marcar el simulador
   como OBSOLETO en el MANIFEST. **Lección:** un simulador
   de pila debe fallar explícitamente ante opcodes de
   efecto de pila desconocido, no silenciarlos.

2. **PROVENANCE:** el registro de claims usaba estados fuera
   de la lista cerrada `ESTADOS_RESEARCH` y creaba
   duplicados. **Reparación:** registrar vía
   `S.registrar_investigacion` con estados válidos
   (`PROVEN`/`REFUTED`/`SUPPORTED`/`NOT_DETERMINED`/`PARTIAL`/
   `OPEN`) y crear resultados de evidencia vía
   `S.registrar` antes de referenciarlos.

3. **AI_REASONING:** el heuristico de proximidad produjo
   falsas asociaciones. **Reparación:** cambiar de
   "propiedad más cercana" a patrones estructurales
   EXACTOS (STORE: `Push[...,clave,mult]→0x4F`; RMW:
   `Push[o,k,o,k]→0x4E→Push[mult]→Multiply→0x4F`).

4. **RUNTIME_DEPENDENCY:** sin runtime Flash, la fórmula
   exacta y el papel del uint32 del tipo 6 permanecen
   `NOT_DETERMINED`. **Estado:** bloqueado genuinamente;
   no es una brecha de RXRE sino una dependencia externa.

## Qué desbloqueó el breakthrough

El paso de "frontera saturada" a "mapeo resuelto" no
requirió documentación primaria ni runtime: requirió
**balance de pila riguroso** sobre el bytecode ya
desensamblado. Esto demuestra que RXRE puede derivar
semántica de opcodes no estándar sin tabla de referencia,
siempre que la herramienta no descarte silenciosamente lo
desconocido.

## Prioridad de la siguiente investigación

1. **Mitigación de armadura** (RXRE-SWF-015/048/049):
   las fórmulas de escalado, fuentes de armadura
   y modificadores de stats ya están recuperadas
   (RXRE-SWF-049). Lo que falta es la COMBINACIÓN
   `daño = f(myDamage, myArmor)` — está en la
   rutina nativa (token, RXRE-SWF-048) con firma
   `inDamage/inArmor`. Vías: (a) runtime Flash
   (RXRE-SWF-014, dependencia externa); (b)
   reversión de la rutina nativa (requiere el
   intérprete AVM1 de este dialecto o el Flash
   Player fuente).
2. **Simulador de valores completo** (interpretación
   abstracta con CFG): extender `avm1_sym.py`
   (lineal) a un intérprete con flujo de control
   real (uniones de CFG, ramas) para eliminar la
   corrupción de pila restante y resolver los
   opcodes dependientes del valor (`0x52`
   CallMethod, `0x87` StoreRegister, `0x3D`,
   `0x43`, `0x47`, `0x50`, `0x53`). Sin
   dependencia externa.
3. **Significado del uint32 del tipo 6**
   (RXRE-SWF-047): se REFUTÓ que sea función
   determinista del float32 (fórmula exacta solo
   27/61; 9 pares sin inversa). Es un **valor
   separado** (fracción 0.32 = peso/
   probabilidad). Su **significado de juego**
   requiere runtime Flash (RXRE-SWF-014).
   **Dependencia externa.**
4. **Runtime Flash (ruffle)** — validación
   diferencial (RXRE-SWF-014). **Dependencia
   externa genuina.**

## Veredicto

RXRE fue **suficiente** para recuperar la semántica de los
opcodes de acceso a propiedades, el mapeo de constantes
y la decodificación de saltos de este dialecto no
estándar, usando solo análisis estático riguroso
(balance de pila + CFG por consenso). El fallo
principal fue de **herramienta** (el simulador sin
`else`), que indujo a una conclusión falsa que persistió
una sesión; la corrección fue de **razonamiento**
(balance de pila + patrones exactos + consenso CFG).
Las fronteras genuinamente abiertas son la validación
diferencial (ausencia de runtime Flash) y los opcodes
dependientes del valor (requieren simulación de valores,
no solo de profundidad).
