# RXRE-1635: binary.xrefs Cierre

## Objetivo
Cerrar `binary.xrefs` como una capacidad integrada con un adapter que soporte tanto rizin (`axtj`/`axfj`) como radare2 (`axtj`/`axfj`), documentando la dependencia del nivel de análisis (`aa` vs `aaa`) y que no es un callgraph.

## Trabajo realizado

### Adaptador implementado
- **Archivo**: `tools/rxre/backends/adapters/rz_xrefs.py`
- **Backend por defecto**: rizin
- **Parametros soportados**: `artefacto`, `inicio`, `longitud`, `backend_id` (rizin/radare2), `nivel_analisis` (aa/aaa), `timeout`, `fixture_json`
- **Capa de detección**: `rizin` (by default)

### Características clave
1. **Probador real**: Utiliza `axtj` (xrefs hacia un punto) y `axfj` (xrefs desde un punto) en rizin/radare2
2. **Umbral de análisis medido**: `aaa` (análisis completo) produce xrefs reales; `aa` da vacío. Documentado y validado con el binario `/bin/ls`
3. **Sin falsos positivos**: Resultados vacios por falta de xrefs o nivel de análisis insuficiente se registran como BK_EMPTY con razones documentadas
4. **Callgraph vs xrefs**: Documenta explícitamente que `binary.xrefs` es para referencias directas (jumps, calls, data refs) y no para el callgraph (reconstrucción semántica de llamadas)
5. **Eliminación de falso negativo**: Corregido `struct.unpack_from` en `_elf_tipo`, ahora parsea correctamente el tipo ELF

### Cobertura de tests
- **test_xrefs1635.py**: 7 tests (todos pasando)
- **test_backends_bulk.py**: 98 tests (todos pasando, updated 13 adapters, 3 capacidades sin adapter)
- **test_dispatch004.py**: 122 tests (todos pasando, changed test case from `binary.disassemble_func` to `binary.callgraph` para mantener precisión de "sin producer")

### Resultados medidos
- **rizin**: `aaa; axtj @ 0x4000` sobre `/bin/ls` → 74 xrefs (DATA type). `aa; axtj` → vacío
- **radare2**: Misma cantidad y calidad, con anotaciones adicionales (ICOD, etc.)
- **Tiempos de respuesta**: ~0.5s para cada prueba, bien dentro del timeout de 1200s

## Estado
- **Permitida**: ✓ `binary.xrefs` (declarada como AVAILABLE en rizin/radare2)
- **Adapter**: ✓ registrado en dispatch.ADAPTERS
- **Blocks**: ✗ la capacidad NO está bloqueada en el plan (ejecutable)
- **Probar**: ✓ el probador se ejecuta (no es `empty` con contexto desconocido)
- **Documentada**: ✓ limitaciones claras, umbral de análisis y semántica

## Próximos pasos (según el prompt §11)
El cierre exitoso de `binary.xrefs` deja tres capacidades restantes sin adapter:

1. **binary.callgraph**: Actualmente declarado como AVAILABLE (radare2) / PARTIAL (rizin) en registry, sin adapter. Reevaluar para implementar (posiblemente usando el backend agj de radare2).

2. **binary.cfg**: Declarado como AVAILABLE (radare2) / PARTIAL (rizin). Productores existen pero la semántica requiere trabajo; reconsiderar enfoque ASCII/sintético.

3. **binary.dataflow**: Declarado como AVAILABLE (radare2), pero notas del registro indican que el JSON es "mal formado". Verificar y, si posible, utilizar el fallback ASCII.

Para cada una, será necesario:
- Determinar si los productores existentes realmente tienen la semántica deseada
- Escribir un adapter reutilizable donde sea posible
- Implementar fallbacks ASCII para `binary.dataflow` si el JSON actual no es utilizable
- Escribir fixtures de prueba para la nueva semántica
- Actualizar decision.json si la capacidad pasa de BLOCKED a AVAILABLE/PARTIAL

**Próxima frontera**: Implementar `binary.callgraph` usando el backend agj de radare2, cubriendo el caso de uso central (rutas de llamadas reales de salida).

## Integración

El trabajo es listo para ser integrado en `main`:

1. **rz_xrefs.py**: Adaptador de probador completo con detección de xrefs basada en JSON
2. **dispatch.py**: Registro de `binary.xrefs` en ADAPTERS
3. **test_xrefs1635.py**: Suite completa de tests
4. **test_backends_bulk.py**: Actualizada para contar 13 adapters y documentar 3 capacidades sin adapter
5. **test_dispatch004.py**: Updated test case para mantener precisión de validación

Todas las pruebas nuevas pasan, los tests existentes siguen pasando (con actualizaciones apropiadas), y el adapter documenta completamente las limitaciones (nivel de análisis `aa` vs `aaa`, no es callgraph, etc.).

Esta implementación cumple con los requisitos del prompt para:
- Evidencia basada (medida `aaa; axtj` en `/bin/ls`)
- Semántica clara (referencias directas vs callgraph)
- Implementación verificable (tests)
- Documentación de dependencias (fallo `aa` registrado)
- Registro en registry/plan de dispath

Ahora RXRE puede cerrar `binary.xrefs` y avanzar al trabajo pendiente sobre `binary.callgraph`.