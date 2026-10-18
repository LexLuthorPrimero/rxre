# RXRE-004 — BACKEND CONTRACT (congelado)

> Contrato **público** de un backend de reverse engineering para RXRE.
> El código que lo implementa está en `backends/contract.py`; este documento
> es la versión congelada, y el código lo cumple, no al revés.

Un backend **no es una autoridad semántica**. Es un *productor de evidencia*.
RXRE no asume que la salida de ningún backend representa la semántica verdadera
del hardware, y el contrato existe para que esa suposición nunca sea
necesaria.

---

## 0. Qué congela este documento (§14)

Cada elemento que el enunciado exige congelar, y dónde está. Los términos
ingleses son los del enunciado; el texto va en castellano.

| §14 | sección | congelado como |
|---|---|---|
| `backend contract` | §1 | identidad, versión **verificada**, commit separado |
| `capability states` | §2, §7 | 4 estados + regla de agregación + allow-list |
| `input contract` | §7 | identificador cerrado; precheck de firma antes de invocar |
| `output contract` | §3, §4 | 4 canales + 11 peldaños epistémicos |
| `provenance` | §5 | 13 eslabones + 3 ramas `PROVENANCE_INCOMPLETE` |
| `error states` | §2 | 6 estados con `rc` y las 3 colapses prohibidas |
| `normalization` | §3.1, §4 | `limpieza` declarada; nada sube de peldaño |
| `result identity` | §6 | hash de 4 componentes; determinismo ≠ unicidad |
| `explainability` | §5, §9 | `explain` reconstruye los 13; lo que no se promete |

---

## 1. Identidad

Todo backend expone, **verificado en runtime**, no declarado:

```json
{
  "backend_id": "rizin",
  "exe": "rizin",
  "path": "/usr/bin/rizin",
  "existe": true,
  "tool_version": "rizin 0.7.4 @ linux-x86-64, package: 0.7.4-9.fc43",
  "version_verificada": true,
  "backend_version_status": "VERIFIED",
  "version_flag": "-v",
  "repository": "https://github.com/rizinorg/rizin.git",
  "repository_commit": "d14c3fac4126bc5fbe66e7f3d1660aeab22b01d8"
}
```

### 1.1 `tool_version` ≠ `repository_commit`

Son **datos distintos** y por eso son campos distintos:

| | qué es | valor medido |
|---|---|---|
| `tool_version` | el binario que **corre** | rizin 0.7.4 (Fedora 43) |
| `repository_commit` | el **código fuente** auditado | `d14c3fac…` (v0.10.0-dev) |

Aquí **no coinciden**: el repo es más nuevo que el binario instalado. Un
envelope que solo lleve `tool_version` pierde el commit; uno que solo lleve el
commit no dice qué versión se ejecutó.

### 1.2 Un backend entra solo si su versión es verificable

> **backend verificable en runtime = requisito, no buena práctica**

MEDIDO: `import angr` **funciona** dentro del árbol del proyecto, porque el
directorio clonado se llama `angr` y Python lo toma como *namespace package*:

```python
>>> import angr
>>> angr.__file__
None
>>> angr.__path__
['…/tools/rxre/github/angr']   ← el DIRECTORIO del repo, no el paquete
>>> angr.Project
AttributeError: module 'angr' has no attribute 'Project'
```

Fuera del árbol: `ModuleNotFoundError: No module named 'angr'`.

> un import que funciona no es un paquete importado

Un backend cuya identidad no se puede verificar **no entra en provenance**:
se registraría un `backend_version` que nadie puede confirmar.

### 1.3 `backend_version_status`

| status | cuándo | `tool_version` |
|---|---|---|
| `VERIFIED` | algún flag (`-v`/`-V`/`--version`) respondió | la línea que respondió |
| `UNVERIFIED` | el binario existe pero no responde a ningún flag | **vacío** |

`UNVERIFIED` con la versión vacía es **mejor** que `VERIFIED` con una versión
inventada. Es la misma lección que F8: *`exit 0` con una salida que no es la
pedida*. La apariencia de éxito sin contenido es el fallo caro.

---

## 2. Estados

Seis estados. `empty`, `blocked` y `error` **no** significan lo mismo, y añadir
`unsupported` y `invalid_input` es la razón de que sean seis y no cuatro.

| estado | `rc` | significa |
|---|---|---|
| `ok` | 0 | se ejecutó y produjo salida parseable |
| `empty` | 0 | se ejecutó y no produjo nada. **NO** es que el objeto no exista |
| `unsupported` | 4 | el backend **no tiene** esa capacidad, con nombre y versión |
| `blocked` | 2 | se intentó y una precondición falló (backend, permisos, build) |
| `invalid_input` | 5 | la entrada no es válida para este backend |
| `error` | 1 | fallo del backend |

### 2.1 Las tres colapses prohibidos

```
unsupported  →  empty      PROHIBIDO
blocked      →  empty      PROHIBIDO
error        →  empty      PROHIBIDO
```

Un backend que no sabe decompilar **no está vacío**: no sabe. Colapsar eso hace
que una IA que pregunte por decompilación reciba "vacío" y concluya que el
binario no tiene — la conversión `empty → absent` que este proyecto cuenta
desde el principio.

### 2.2 `unsupported` MEDIDO, no inventado

Un ELF con `e_machine` desconocido (`0xFFFF`) pasa el precheck de firma,
`rz-bin` responde **rc=0** y devuelve `info` **con contenido**, pero sin `arch`:

```
rizin  ->  arch=None                  machine='<unknown>: 0xffff'
radare2 ->  arch='Unknown or unsupported arch'
/bin/ls ->  arch='x86'
```

Reducido a la forma del contrato, esto sería `ok` con `arch: null`, y una IA
leería "arquitectura: null" como si el binario no tuviera arquitectura. **No la
tiene: es que nadie la ha identificado.**

```
no saber qué arquitectura es  ≠  no haber nada que mirar
```

---

## 3. Los cuatro canales

Un campo `output` confunde cuatro cosas distintas:

| canal | qué es |
|---|---|
| `raw_output` | lo que el backend escupió, byte a byte |
| `normalized_output` | lo que RXRE entendió |
| `provenance` | quién, con qué versión, con qué commit, sobre qué hash |
| `status` | si se pudo, si no, y por qué |

### 3.1 `limpieza` es un campo declarado

MEDIDO: rizin y radare2 meten secuencias ANSI y `\r` en `stdout`.

```
rizin -qc 'aaa; afbj @ entry0'            ->  no parsea (ANSI + \r)
rizin -q -e scr.color=0 -c 'aaa; afbj …'  ->  JSON OK
```

Por eso `limpieza` lleva `{aplicada, caracteres_quitados}`. **Una salida con
secuencias de control no es una salida inválida: es una salida que hay que
limpiar, y decirlo.** Un normalizador que no lo limpiara declararía `error`
sobre una salida perfectamente válida.

---

## 4. Representaciones epistémicas

Ordenadas de menor a mayor confianza. `type` dice en qué peldaño está cada
resultado:

```
raw_binary < disassembly < function_candidate < basic_block < control_flow
          < call_graph < xref < data_flow < decompilation
          < semantic_hypothesis < validated_semantics
```

### 4.1 La regla

> un resultado no puede declararse de un nivel superior al que su producer
> demuestra

```python
puede_declarar(DECOMPILATION, VALIDATED_SEMANTICS)  ->  False
```

Responde `False` casi siempre, y por eso sirve. **La salida de un
decompilador es una hipótesis semántica, no semántica validada.** Guardarla como
`validated_semantics` sin evidencia adicional es el defecto que §10 prohíbe.

---

## 5. Provenance

`result_id` debe poder reconstruir:

```
result_id → operation_id → backend → tool_version → repository_commit
           → input_artifact → input_hash → command_or_api → argv
           → raw_output → transformacion → normalizador → normalized_result
```

**13 eslabones.** Si alguno falta: `PROVENANCE_INCOMPLETE`, dicho.

### 5.1 Tres ramas sin artefacto

Solo tres, y son tres por razones distintas:

| rama | por qué no hay provenance |
|---|---|
| `timeout` | no hay `stdout` |
| `rc != 0` | el backend falló |
| stdout no parseable | hay bytes, no hay artefacto |

Las salidas tempranas (`no existe` / `no es ELF`) **no** llevan
`PROVENANCE_INCOMPLETE`: no hay provenance que pueda estar incompleto, porque
el backend no se invocó.

### 5.2 El `target` de una operación binaria NO es un PCI

MEDIDO: `persistir()` firmaba **todas** las operaciones con
`target: "0000:01:00.0"`, incluidas las que solo abren un fichero. Eso
adjuntaba una lectura de hardware que no había ocurrido: evidencia de la RX550
firmada por una operación de fichero.

```
un target que no se ha tocado no se puede escribir como target
```

El target real es el artefacto, y su identificador es su **hash**, no su nombre
— dos ficheros con el mismo nombre en sitios distintos son artefactos
distintos:

```
binary:rxre_min.elf@a183f60d67ba1787
```

---

## 6. Identidad de resultado

### 6.1 `result_id` es un hash de (tipo, artefacto, backend, valor)

Regla heredada de F6: **un identificador que colisiona no identifica.**

MEDIDO (F6): un id derivado solo de (tipo, valor, herramienta) daba 9 ids
distintos para 36 resultados, y con `INSERT OR REPLACE` 36 filas se
convertían en 9 sin que nada lo notara.

### 6.2 Determinismo ≠ unicidad

Son **propiedades distintas**, y confundirlas es un error:

- **determinismo**: la misma entrada da el mismo id
- **unicidad**: entradas distintas no comparten id

MEDIDO: dos copias byte-idénticas de `rxre_min.elf` en rutas distintas dan el
**mismo** `value` normalizado y **distintos** `result_id`. Con un id derivado
sólo del valor, colisionarían.

> un resultado reproducible puede seguir colisionando

Y por eso `COLISION` en un `result_id` determinista **no es un fallo**: es que
la evidencia ya existe y `explain` la alcanza. Reportarlo como `persistido:
false` sería decir "no se guardó" cuando en realidad **sí** está guardada.

---

## 7. Allow-list de capacidades

```
AI → op:run → capability → REGISTRY → ALLOWLIST → backend contract → adapter → backend
```

**Nunca:** `AI → op:run → string arbitrario → shell`.

Una capability es un identificador **cerrado** (`prefijo.nombre`). Se acepta
sólo si:

1. existe en el registry;
2. tiene ficha;
3. tiene contrato;
4. **tiene adapter**;
5. está declarada `AVAILABLE` o `PARTIAL`.

Es el mismo patrón que F3: `target_permitido` no era una lista negra de
targets peligrosos, era *"permite explícitamente sólo estos targets"*.

### 7.1 `PARTIAL` es ejecutable

Existe un producer, pero su salida no cumple el contrato. Es ejecutable **y su
limitación viaja con él**. Ocultarla sería mentir que la capacidad no existe;
declararla `AVAILABLE` sería mentir que cumple.

### 7.2 `NOT_DETERMINED` NO es ejecutable

No se comprobó que falte: se comprobó que **no se puede verificar**. Un backend
no verificable no puede entrar en la allow-list, porque su resultado no tendría
provenance creíble.

---

## 8. `plan` sin ejecución

Cada paso declara tres cosas **distintas**:

| campo | significa | NO significa |
|---|---|---|
| `verifiable` | el registry **afirma** que hay producer | que vaya a funcionar |
| `available` | se puede pedir **ahora** | — |
| `reason` | por qué no, cuando no | — |

`execution` vale literalmente `not_started`. Un plan **no** es una promesa: es
un camino con sus puertas marcadas, algunas cerradas.

MEDIDO sobre `binary.decompile`: 6 pasos, **6 verificables, 1 ejecutable**. Un
plan que sólo contuviera pasos ejecutables sería más vistoso y menos útil: la
IA tiene que ver `binary.decompile` como un callejón **antes** de recorrer los
otros cinco.

---

## 9. Lo que el contrato NO promete

- Que un backend instalado hoy dé lo mismo mañana. La versión es dato suyo.
- Que `AVAILABLE` signifique *completo*. MEDIDO: `binary.dataflow` es
  `AVAILABLE` en radare2 (JSON válido) y su **conjunto de escrituras sale
  vacío** para `campo`, que tiene un store probable en `0x400024` confirmado
  por `objdump` y por el ESIL de rizin (`edx,0x30000000,edi,-,=[4]`).
- Que un `empty` signifique ausencia. MEDIDO: `rizin -qc -e scr.color=0 'cmd'`
  sale **vacío sin error**, porque `-qc` consume el argumento siguiente como
  comando y se come el `-e`. Es la misma clase de error que `aa` frente a
  `aaa`: *un `empty` por invocación incorrecta*.
- Que cuatro repositorios clonado sean cuatro backends disponibles. Clonar no
  es ejecutar; `angr` y `rz-ghidra` siguen en `NOT_DETERMINED`.