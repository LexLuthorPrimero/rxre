# Manifiesto de compactación documental — 2026-10-03
# Generado por global-coordinator-01 (AGENT-01 COORDINACION).
# Nada se borra: todo lo movido esta aqui y en git. Destino del estado: ESTADO.md

## Contenido movido, con sha256

```
2a8e59d17243302a177a0e85c8ce47f5a2aa21713b332d563a6694d5e3b5cec8    1605  02-ARQUITECTURA⁄DECISIONS.md
9f838c74dec6f751022e7acae652fb9c5b5719f63895a17bec449e12de01ad48     523  03-EXPERIMENTOS⁄EXP-[NÚMERO]-[NOMBRE-CORTO].md
1d7bcf36f9e7bffd1d65fe6c5d14c03df91c5e4ed3b898466c28942a18c1dde3   28242  29⁄9⁄26.md
da4ad1b418377abd68eee05b5bd265b9feaeb0612735a8bf5e34097cedf6b247   12457  30⁄9⁄26.md
c2c468a40d29c7d6e42150562d420f4dc54e010b2976d64d9f998121897c1935    4046  AGENTS-BORRADOR-48.md
1f339533c00798ee95a08d6d4234b03607cf25156fd4f068ee7a6d7d94dde70e    4230  CIERRE_PROYECTO.md
f29bc17e93a848f038c7b5413f4b053cf88356e8998b33176ce3fc674d246c80    2106  comportamiento.md
a46bde65b60c56c93ca00e60d254eea9964f3e0968c99a970199f2f328ed3bec    6503  FINAL-RELEASE-REPORT.md
c1fc5e8301b3acf9b9818f08826b87703e9d9eff1dfa38602dbbd767ef9834ea    4582  FINAL-RESEARCH-STATUS.md
1d1d31abd1dbbb70b993be88b6d016e8b1eae741384ba2033a84ee6c22bd1655    9815  ideas2.md
f0fb276f42088d332ecfeb95af997a8be9f3c5abb488428509f966d0f2e0716e   17909  ideas3.md
0090312995f2555e9dd2a211704166cfabacaa93019f93e4936a39a90771cbc2    1291  MANIFIESTO.md
d3ac0ebd531625b8a53ce85b6e418af867aed2f70c6b4b6128dd89165ed30dd3     342  PATCH-REGISTRY.md
b078b080af9805efb8c13cd0a7519e329eea814c9280228b24155891439593e7     384  PROBLEM-STATUS.md
1c55b6372611a532d15643250d7fd15a2c561912263de04aebc948311d2903cf   10611  PROYECTO_STATUS.md
188d67916b144e6bb755c6c8ed6d4a8b5ef9a4df46b43a16ae613f2fdcff6420    3286  RELEASE-CANDIDATE.md
357d74c1850d2276fc21afbc310ed220fabc04137c233459cc11baa599af78ce    2015  RELEASE-EXCLUSIONS.md
```

## Por que se movieron

- **PROYECTO_STATUS / CIERRE_PROYECTO / RELEASE-CANDIDATE / FINAL-RELEASE-REPORT /
  RELEASE-EXCLUSIONS / FINAL-RESEARCH-STATUS**: seis documentos que se declaraban
  "estado final" y competian entre si. Son tres cierres sucesivos (2026-09-19,
  09-25, 09-29) sobre el mismo objeto; la divergencia de fechas es lo que los
  hacia parecer documentos distintos. Sus cifras, limitaciones y estados estan
  en `ESTADO.md`, sin resumir y con la fuente citada en cada linea.

- **PATCH-REGISTRY.md**: cabecera de tabla con 2 filas que afirman "LZ4 adaptativo
  Implementado". No hay LZ4 en el codigo del compresor, `DECISIONS.md` no lo
  registra, y AD-8 confirmo BC3/DXT5 estandar. Afirmacion falsa en un documento
  que competia por autoridad. El registro real es `PATCH-REGISTRY-FINAL.md`, 24 filas,
  citado por 23 documentos.

- **PROBLEM-STATUS.md**: plantilla sin rellenar (384 B). El canonico es
  `PROBLEM-STATUS-FINAL.md`, con 8 estados tipados, citado por 27 documentos.

- **ideas2.md / ideas3.md**: brainstorm superado por `ideas.md`.
- **AGENTS-BORRADOR-48.md**: su cabecera dice "SUBORDINADO, NO EJECUTAR".
- **29/9/26.md, 30/9/26.md**: bitacoras sueltas por fecha en la raiz.
- **comportamiento.md**: "regla operativa" que nunca se incorporo a `COORDINACION.md`.

- **02-ARQUITECTURA-DECISIONS.md** y **03-EXPERIMENTOS-EXP-plantilla.md**: nombre
  con U+2044 FRACTION SLASH en lugar de "/", colgados en la raiz y versionados
  desde `ad4d08b`. El primero es un fragmento de 18 lineas cuya unica decision
  (formato RGB565 propio) fue retractada por su propia AD-6, que lo sustituyo por
  BC3 estandar; el segundo es una plantilla sin rellenar. El registro canonico
  esta en `02-ARQUITECTURA/DECISIONS.md`, 1322 lineas.

## Lo que NO se toco, y por que

- **504 findings** en `06-INGENIERIA-INVERSA/findings/`: evidencia primaria. Una
  medicion no se resume sin perderla.
- **9 vistas generadas** por `tools/artifacts.py`: se regeneran solas y declaran
  `NO EDITAR A MANO`. Su desfase respecto al disco es esperado, no un error.
- **PATCH-REGISTRY-FINAL.md** y **PROBLEM-STATUS-FINAL.md**: referenciados por 23
  y 27 documentos. Son canonicos, no duplicados.
- **AGENTS.md**: esta a 0 B por un bind mount, y el origen de ese bind mount
  (`RX550-AGENT-DEFINITIONS/01-COORDINACION/AGENTS.md`) tambien esta a 0 B. El
  canónico commiteado se conserva en el blob `a40e21cb` del object store y en
  `08-ARQUITECTURA/AGENTS.RECTOR-5d33ccab.bak`. Reparar los 6 montajes requiere
  root y esta fuera del alcance documental; se reporta, no se ejecuta.

## Como revertir

```bash
git log --oneline -- archive/documentacion-compactada-20261003/
git mv archive/documentacion-compactada-20261003/<fichero> <destino_original>
```

## Referencias que siguen nombrando a estos ficheros

Comprobadas una a una. **No se repararon a propósito**: son menciones de historia,
no enlaces de navegación, y cambiarlas fabricaría una historia que no ocurrió.

| Fichero | Mención | Por qué se deja |
|---|---|---|
| `08-ARQUITECTURA/decisions/DECISIONS-F4.md` | `PROYECTO_STATUS.md` | cita una limitación tal como se escribió entonces |
| `COORDINACION.md:211` | `CIERRE_PROYECTO.md` | registro de una sesión pasada; COORDINACION.md es ley operativa |
| `01-AUDITORIA/PATCH-RECOVERY/PATCH-SOURCES.md` | `RELEASE-CANDIDATE.md` | inventario de fuentes de una recuperación |
| `01-AUDITORIA/MIGRATION-METHODOLOGY-AUDIT-*.md` | `FINAL-RELEASE-REPORT.md` | auditoría que auditó lo que había entonces |
| `02-ARQUITECTURA/research_log.md` | `FINAL-RESEARCH-STATUS.md` | bitácora: registra el cierre de una fecha |
| `AUTORIDAD-INSTRUCCIONES.md:30` | `AGENTS-BORRADOR-48.md` | inventario de prompts, con su tamaño de entonces |
| `promp.md:418` | `ideas3.md` | transcripción de una sesión |

Los enlaces de navegación sí se repararon: los de `README.md` y
`00-INDICE/README.md` apuntan ahora a `ESTADO.md`.
