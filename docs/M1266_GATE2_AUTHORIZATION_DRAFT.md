# DRAFT — Autorización y Protocolo de Aislamiento para el Gate 2 (M1266-A2/B1) — NO AUTORIZADO

Estado: `DRAFT / NOT AUTHORIZED / NOT EXECUTED`. Este documento **no concede ninguna autoridad**,
no activa ejecución, no sustituye `DB_AUTH_ACTOR_M294`, no altera el estado sellado del archivo R3,
y es papel hasta que el propietario lo nombre por escrito con fecha. Cualquier ejecución antes
de esa firma es una violación del propio protocolo y debe abortar fail-closed.

Fecha del borrador: 2026-11-13 · Autor: sesión asistida (RXRE) · Revisor externo: ninguno.

## 1. Alcance (wall, no objetivo)

- Gate 2 / M1266-A2: construcción de analizadores independientes de tramas WAL y de
  confirmaciones ACK del Outbox v1.1.0 (ÉTER-WAL), en C11, **fuera del archivo de producción**.
- Reconstrucción/validación de la cadena B2/EXP: inyección de fallos **controlada y acotada**,
  concurrencia masiva simulada y pérdida de energía **simulada** (kill/proceso/artefacto),
  nunca corte físico de energía (EXP-11 → `NOT_REACHED`, §4).
- Exclusión dura: nada toca `rxre.sqlite3`, `.rxre/`, `rxre-r3/`, el archivo R3, ni el árbol
  de producción; nada publica; sin root/sudo/MMIO/`/dev/mem`/debugfs/UMR; sin `--auto`,
  `op:claim`, sin bucles desatendidos.

## 2. Entorno delimitado (precondición a firmar)

- Host de prueba **dedicado** (distinto del que conserva el archivado R3) o, como mínimo,
  usuario/UID aislado + bwrap con montajes read-only de evidencia y escritura confinada a
  scratch (`/tmp/rxre-m1266-g2/`).
- Copia explícita del material de prueba (tramas WAL sintéticas selladas previamente, `OBX1`,
  fixtures `MANIFEST_V1 a/b`) dentro de scratch; verificar sha256 del material **antes** de
  cualquier inyección.
- Revocación operativa: el host de prueba **no** conserva credenciales ni llaves del archivo
  R3 ni de repositorios externos; red desactivada durante ensayos.
- El borrado/borrado forzado de scratch post-run requiere verificación de que ningún archivo
  sellado fue tocado (sha256 + dev/ino), idéntico al sellado pre-run.

## 3. Criterios de parada y fail-closed

Abortar automáticamente y marcar la misión `BLOCKED` (sin reintentos automáticos) si aparece:

- Cualquier hash de trama/OUTBOX fuera de la tabla sellada de referencia.
- Transición de máquina de estados hacia `UNKNOWN` no acotable documentalmente, o ruido de I/O
  que el analizador no pueda clasificar (`NOT_DETERMINED` obligatorio, no silencio).
- Escritura fuera de scratch, o cualquier señal de acceso a rutas del archivo R3/producción.
- Corrupción detectada en `MANIFEST_V1` o discrepancia entre slots `a`/`b` tras un ensayo.
- Reintento: máximo `max_iter = 3`, decisión humana entre intentos; `autonomous_loop=False`.
- Resultados solo válidos dentro del sobre del ensayo; jamás se promueve `PROVEN`/`PASS` a
  "capacidad general" por un ensayo acotado.

## 4. EXP-11 (corte físico de energía) — `NOT_REACHED` explícito

EXP-11 exige infraestructura física dedicada (host con gestión controlada de alimentación,
registro de cierre sucio, y relectura independiente de medio). **Hasta que esa infraestructura
exista y el propietario la designe, EXP-11 permanece `NOT_REACHED` y no se simula como si lo fuera.**
Una caída de proceso o `kill -9` es una simulación de crash, no de corte de energía; todo
resultado de ese tipo debe etiquetarse `SIMULATED_CRASH`, con limitaciones anotadas.

Mapa preliminar EXP-01…15 (sin ejecución): todos `TENTATIVE / NOT AUTHORIZED`; EXP-11 `NOT_REACHED`;
la matriz final se define en la revisión del borrador firma-por-firma, no aquí.

## 5. Evidencia y verificación

- Sellado previo (seal-before-reveal) de todo material de entrada; el sello se verifica antes
  y después de cada fase; salidas a archivos nuevos únicamente.
- Cada ensayo deja: configuración del entorno (uname, gcc, git rev, locale), comandos exactos,
  hashes de entrada/salida, y dictamen `RESOLVED / UNRESOLVED / NOT_DETERMINED / BLOCKED`.
- Verificación independiente por tercero (misma regla que R3) antes de cualquier cambio de estado.
- Nada de lo producido toca el archivo público ni el release `v1.3.0` sin revisión y aprobación
  escrita del propietario (regla de publicación intacta).

## 6. Rollback y cierre

- Scratch desechable; rollback = restaurar/desechar scratch, nunca tocar el archivo original.
- Cierre: resumen con `evidence_refs` resolubles, limitaciones sin ocultar, y ausencia del
  sobre el owner.

## 7. Firmas / vigencia

Requiere firma explícita del propietario + designación de operador técnico + revisor externo.
Ventana propuesta: 7 días, revocable sin preaviso. Sin esas tres firmas, este documento es inerte.
