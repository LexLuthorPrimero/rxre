# RX550-INVESTIGACION — Raíz documental oficial (proyecto de investigación RX 550)

**Fecha de creación de la raíz:** 2026-09-23 · **Fase:** reorganización documental autorizada (solo estructura; movimientos pendientes de autorización final).

## Estructura oficial

```text
00-INDICE/          Documentos maestros, índices y decisiones de organización
01-AUDITORIA/       Informes de auditoría (documental, madurez, contadores, etc.)
02-ARQUITECTURA/    Arquitectura HW/SW y documentación de conocimiento
03-EXPERIMENTOS/    Experimentos con sus datos, logs y resultados
04-IMPLEMENTACION/  Diseños, herramientas y roadmap de implementación
05-FUENTES-EXTERNAS/ Fuentes externas, manifiestos y referencias
README.md           Este índice de entrada
```

## Carpeta de NotebookLM (independiente de esta raíz)

`~/Escritorio/RX550-INVESTIGACION-NOTEBOOKLM/` — plana, máximo 50 documentos, sin subcarpetas.

## Estado de la reorganización

- [X] Estructura creada
- [X] Git inicializado (baseline)
- [X] Manifest de hashes pre-movimiento (`00-INDICE/REORGANIZACION-MANIFEST.sha256`)
- [ ] Movimientos (pendiente de autorización final)
- [ ] Reparación de referencias/rutas (fase posterior separada)
- [ ] `00-INDICE/FUENTES-FALTANTES.md` (después de la reorganización)
- [ ] `00-INDICE/REGISTRO-DE-MOVIMIENTOS.md` (durante la ejecución)

## Reglas permanentes

- No se modifica sistema (Mesa/kernel/VBIOS/PowerPlay/sysfs), ni `rx550-torneo`, ni se ejecutan benchmarks en esta fase.
- Los archivos no se borran ni se sobrescriben; cada movimiento registra origen → destino → hash → fecha → motivo.
- Fuente viva del estado del proyecto: `00-INDICE/MASTER-RESEARCH-STATUS.md`.