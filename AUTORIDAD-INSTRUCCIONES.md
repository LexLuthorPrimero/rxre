# AGENTE-SMU — AUTORIDAD DE INSTRUCCIONES

> Declaracion de quien manda. Leida por cualquier agente antes de actuar.

## 1. QUE MANDA

```text
AGENTS.md   en la raiz del repositorio
            = MASTER PROMPT V6 + DIRECTIVA VIGENTE del 2026-10-04
            = 53382 bytes
            = sha256 ca1ad44368ade558a93ad36d0c3a505d09e6c2bbc758c5bbe1dc31a86dc72332
            = 2026-10-04, seccion "DIRECTIVA VIGENTE" + el contador compartido
```

**MEDIDO 2026-10-04: este registro estaba DESVIADO ANTES de que nadie lo tocara.**
Decir `45247 bytes / aadc625a…` cuando el fichero llevaba tiempo en 49596 bytes con
`sha256 3ca73133…`. Es decir: la comprobacion de §2 —*"si divergen, el de la raiz
manda"* — llevaba tiempo sin poder aplicarse, porque las dos cifras registradas no
correspondían a ningún fichero que existiera.

Un registro de hash que no se re-deriva cuando el fichero cambia es peor que no
tenerlo: se lee como una garantia y no es nada. Por eso la cifra de arriba lleva
**fecha y motivo**, y no solo el hash. Si vuelve a cambiar `AGENTS.md`, esto hay que
re-derivarlo en el mismo commit, no en otro.

Ese fichero es la instruccion. Nada mas lo es.

Tambien esta en `~/.config/opencode/AGENTS.md`, con **sha identico** — se
verifico con `sha256sum` sobre los dos. Si divergen, el de la raiz del
repositorio es el que manda, porque es el del proyecto.

## 2. QUE NO MANDA

Cuatro ficheros del repositorio tienen nombres que empiezan por `AGENTS` y se
autodeclaran con titulos como `HIGHEST PRIORITY`, `LLM-OPTIMIZED` o
`OBJETIVO PERMANENTE`. **Ninguno gobierna.** Todos llevan ahora un aviso al
principio que lo dice, y su contenido se conserva integro como material de
trabajo.

| Fichero | Que es realmente | Bytes |
|---|---|---|
| `AGENTS-BORRADOR-48.md` | borrador con directivas propias | 3 909 |
| `02-ARQUITECTURA/AGENTS-ADVERSARIAL-AUDIT.md` | auditoria de si el prompt gobierna | 62 971 |
| `docs/AGENTS-RECTOR-2026-10-02.md` | propuesta de modo de trabajo | 31 382 |
| `docs/AGENTS-ADDENDA.md` | propuesta de addenda al prompt | 14 099 |

Que el nombre empiece por `AGENTS` no concede autoridad. La autoridad la tiene
**el contenido del prompt vigente**, y el criterio para reconocerlo es que
contenga las secciones que el prompt declara.

## 3. LAS CONTRADICCIONES CONCRETAS

El borrador se autodeclara de maxima prioridad y contradice al prompt vigente en
dos puntos materiales:

```text
NO_EXECUTION_AUTHORIZATION
   "ZERO permission to execute, modify, or alter system state.
    You are an investigator, not an executor."
   V6 §71 PRIVILEGES: "No bloquear automáticamente sudo / su / root",
   y §63 IMPLEMENTATION GATE exige BUILD -> LOAD/EXECUTE -> OBSERVE.
   El prompt vigente manda: la ejecucion esta permitida y es exigida.

CRITICAL_DIRECTIVES / EPISTEMIC_STATE_ENUM (CLOSED SET)
   Tokens propios: FACT_FOR_<source>, AUTOOBSERVED,
   CONTRADICTION_WITHOUT_RESOLUTION.
   V6 §10 EPISTEMIC KERNEL: ninguno de esos tres existe; y la lista de §10 es
   ABIERTA, no cerrada. Una enum cerrada declarada en un borrador sin autoridad
   no cierra un kernel de estados que el prompt deja abierto.
```

Que las dos apunten en la direccion contraria es lo que hace el asunto
urgente: un agente que lea solo el borradorhara lo contrario de lo que el
prompt vigente pide, y lo hara con la maxima confianza.

## 4. COMO COMPROBAR QUE MANDA V6

```bash
sha256sum AGENTS.md ~/.config/opencode/AGENTS.md
```

Si los dos hashes coinciden con `aadc625a1646…`, V6 esta instalado en los dos
niveles. Si el hash **no** coincide, el prompt vigente ha cambiado y hay que
releerlo entero antes de actuar — no raizarlo de memoria.

Ese es el fallo real que se ha producido tres veces en una sesion: el
`AGENTS.md` paso de 32 269 a 45 247 a 15 358 bytes y volvio a 45 247, y un
agente mantuvo reglas citadas por numero de linea durante horas sin que nadie
notara el cambio. **La regla no es leer el prompt: es comprobar que sigue siendo
el que se leyó.**

## 5. LO QUE ESTA EN EL PROMPT Y SE PERDIÓ

Una version de 15 358 bytes de este mismo fichero —
sustituido y luego revertido por otro agente — contenia reglas de operacion
especificas del proyecto que el prompt vigente **no** tiene:

```text
Escritura: lock por scope     .write-lock/<scope> + scopeguard.py --locks
Declara la autoria            AUTORIA= en la cabecera de cada nota propia
Runtime                       "NO EJECUTADO, y no es cosa tuya"
Tasa de intrusion CJK         ~6 por nota, verificar con grep -cP
Reglas de escritura           "Ningun numero que decide una conclusion
                                se calcula a mano"
```

Esas reglas son del proyecto, no del prompt, y esas reglas siguen siendo
buenas. **No se han perdido: estan en este fichero y en `.write-lock/`, que
siguen en pie.** Lo que no se puede es atribuirlas al prompt vigente.

## 6. LA AUDITARIA DEL PROYECTO

`02-ARQUITECTURA/AGENTS-ADVERSARIAL-AUDIT.md` examino si el prompt gobierna la
conducta o solo la describe. Su conclusion, textual:

```text
"Las de control, gobiernan (22 familias). Las demas describen."
19 familias de reglas "no dejan nada": ningun artefacto, ninguna comprobacion.
```

Esa auditoria se hizo sobre una version anterior del prompt y no se ha repetido
contra este. Pero su hallazgo sigue siendo el criterio de este documento: **un
prompt que solo se lee gobierna en la medida en que el agente lo cumple, y nada
mas.** Por eso lo que hace que V6 mande no es su presencia en el fichero, sino
que sus reglas se comprueban — que es lo que hace el ciclo de validacion.

## 7. REGLAS DE ESTE DOCUMENTO

```text
1. Ante cualquier duda de autoridad, manda AGENTS.md de la raiz.
2. Un fichero que se llame AGENTS-* sin serlo no tiene autoridad.
3. Ningun numero de linea es una cita: el contenido es la cita.
4. Si el hash de AGENTS.md cambia, se relee entero antes de actuar.
5. Ningun agente sobrescribe el trabajo de otro para resolver una ambiguedad.
   Un aviso al principio es suficiente y no destruye nada.
```

AUTORIA=AGENTE-SMU
WORK_CLASS=integracion-de-instruccion
WRITE_EXECUTION=escritura atomica (tmp + rename) en 4 ficheros; ninguna
  sobrescritura de contenido; el prompt vigente NO se toco
MODIFICATIONS=4 ficheros con aviso de subordinacion (reescrito con la
  referencia correcta del prompt); AGENTS.md de la raiz RESTAURADO a V6 desde
  ~/.config/opencode/AGENTS.md, con copia del contenido desplazado en
  /var/tmp/rx550/AGENTS.RECTOR-5d33ccab.bak; .write-lock/agentes/owner creado