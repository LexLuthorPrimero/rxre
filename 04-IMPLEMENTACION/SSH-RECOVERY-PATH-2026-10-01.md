# SSH RECOVERY PATH — construcción y estado

```
NODE            DRIVER.EXCLUSIVE.INFRA.SSH_RECOVERY_PATH
FECHA           2026-10-01T10:05Z
ROL             WRITE_EXECUTION #1
ALCANCE         construir y demostrar recovery vía SSH
RESULT          PARTIAL   (1 de 3 condiciones del criterio)
GPU_TOCADO      NO        en ningún momento
LOCK            adquirido al inicio, liberado al final
COMMIT          NO        el commit no estaba en el alcance autorizado
```

## Por qué existe

`AGENTS.md §249`:

> Never begin an isolation operation without an independent documented recovery
> path; TTY/recovery availability is an explicit gate.

El takeover de la RX550 no puede empezar sin una ruta de restore que sobreviva
a la pérdida del display. Este documento construye y mide esa ruta.

## Restricción descubierta que condiciona todo

La sesión del agente **cuelga de la sesión gráfica**:

```
konsole  pid 2683   DISPLAY=:0  WAYLAND_DISPLAY=wayland-0
  └── bash   pts/3
       └── opencode  pts/3
            └── opencode
                 └── bash        ← esta sesión
```

Si el takeover deja el display inservible, konsole muere, el pty master cierra y
esta sesión recibe SIGHUP. **El agente no puede ser su propia ruta de
recuperación.** Esto es independiente del contenido del takeover y se sostiene
aunque la RX550 no se toque nunca.

## Candidatos evaluados

| ruta | independiente del display | estado |
|---|---|---|
| esta sesión (`konsole` → `pts/3`) | **NO** | descartada, `PROVEN` dependiente |
| VT1 / getty | sí, pero depende del `boot_vga` | `NOT_DEMONSTRATED` |
| consola serie `ttyS0` | sí | `NOT_AVAILABLE` — `getty@serial-console` disabled, sin peer |
| SSH sobre `enp3s0` | **sí** | construida, parcialmente demostrada |
| reboot | sí | disponible; no equivale por sí sola a una ruta probada |

## Construcción

### Preferencia por clave: primero se comprobó si existía

```
~/.ssh/authorized_keys        AUSENTE
/etc/ssh/authorized_keys      AUSENTE
~/.ssh/                       no existe
claves públicas del usuario   0
```

No había autenticación SSH previa. **No se instaló ninguna clave**, porque no
hizo falta: el daemon ofrece autenticación por contraseña.

### Cambio aplicado

Un solo cambio, el mínimo autorizado:

```bash
systemctl start sshd
```

Sin cambios en `firewalld`, sin cambios en `sshd_config`, sin tocar el driver,
sin tocar sysfs de la GPU.

## Evidencia

### 1 · El daemon está operativo

```
ActiveState=active  SubState=running  MainPID=30031
Started            Thu 2026-10-01 07:01:24 -03

journalctl:
  sshd[30031]: Server listening on 0.0.0.0 port 22.
  sshd[30031]: Server listening on :: port 22.

banner en loopback   SSH-2.0-OpenSSH_10.2
banner en LAN        SSH-2.0-OpenSSH_10.2   (192.168.100.136:22)
```

`PROVEN`. El daemon acepta conexiones tanto en loopback como en la dirección de
la interfaz, es decir en `0.0.0.0`, no sólo en `127.0.0.1`.

### 2 · Hay un método de autenticación utilizable

```
$ ssh -o BatchMode=yes lucas@192.168.100.136 true
lucas@127.0.0.1: Permission denied (publickey,gssapi-keyex,gssapi-with-mic,password)

journalctl:
  sshd-session[30145]: Connection closed by authenticating user lucas
                       127.0.0.1 port 51490 [preauth]
```

`password` figura entre los métodos ofrecidos. `BatchMode=yes` impide enviar
contraseña, de ahí el rechazo: **el rechazo demuestra que la autenticación por
contraseña está habilitada y que el daemon resuelve el usuario `lucas`**.

Consecuencia: un peer con la contraseña de login del usuario puede autenticarse
sin que haya que configurar nada más.

### 3 · La red hasta el puerto no está bloqueada

```
firewalld  active, zona FedoraWorkstation
query-service=ssh  →  yes       (ya estaba permitido; no se modificó)
enp3s0    UP  192.168.100.136/24, gw 192.168.100.1
```

`PROVEN` para el permiso de firewall. `SUPPORTED` para la alcanzabilidad desde
otro hosts: `kdeconnectd` escucha en `0.0.0.0:1716` en la misma interfaz, lo que
indica que el inbound en LAN funciona, pero no se ha probado desde fuera.

## Criterio: separación de niveles

El criterio original —«una sesión SSH permanece independiente del display»—
mezclaba dos preguntas de distinto nivel. Un disruptor de sesión no prueba
supervivencia ante un disruptor de driver, y el takeover es lo segundo.

```
SSH_RECOVERY

[1]  sshd operativo                                        PROVEN
[2]  peer externo autenticado                              PENDIENTE
[3a] independencia estructural del display                PROVEN_IN_KIND
[3b] supervivencia ante el takeover de la RX550           NOT_PROVEN_EMPIRICALLY
```

### `[3a]` · Evidencia estructural

`PROVEN_IN_KIND`. Ninguna arista de dependencia une `sshd` con el entorno
gráfico, en ninguna dirección:

```
$ systemctl show sshd -p Wants --value | grep -c display-manager
0
$ systemctl show display-manager -p Wants -p After --value | grep -c sshd
0
$ systemctl show sshd      -p WantedBy --value    →  (vacío)
$ systemctl show display-manager -p WantedBy --value →  graphical.target
```

`sshd` no tiene `WantedBy`: arranca en `basic.target`. El display manager
arranca en `graphical.target`. Desenlazar la RX550 no toca ninguna de esas
aristas.

La comparación con esta sesión, que **sí** depende del display, muestra que la
diferencia es real y notrivial:

| | esta sesión | sesión SSH |
|---|---|---|
| árbol de procesos | `konsole` → `pts/3` → `bash` | `sshd` → shell |
| proceso raíz | `konsole`, `DISPLAY=:0` | `sshd`, sin display |
| depende del display manager | sí | no |

### `[3b]` · Lo que no se afirma

`NOT_PROVEN_EMPIRICALLY`, y deliberadamente no se va a cerrar. La
circularidad es directa: la operación que rompe el display es el propio
takeover, así que probar la recuperación exigiría ejecutar lo que la
recuperación protege.

Además, la supervivencia de canal depende del nivel del disruptor, y el
requisito de `AGENTS.md §249` es sobre la **existencia de un camino
independiente y documentado**, no sobre haber sobrevivido a un fallo concreto:

| disruptor | nivel | ¿canal SSH? |
|---|---|---|
| cerrar sesión de Plasma | sesión | sobrevive |
| `display-manager stop` | sesión | sobrevive, pero mata la sesión del agente |
| **unbind amdgpu de `0000:01:00.0`** | **driver** | no demostrado |
| reset / fault de la RX550 | dispositivo | no demostrado |
| cuelgue del sistema (D-state) | sistema | **ningún canal** |

Una prueba de nivel sesión produciría un `PROVEN` que no cubre los dos
últimos casos, y un `PROVEN` etiquetado así sería más fuerte que su evidencia.
No se va a obtener una etiqueta mediante un experimento destructivo cuyo
único propósito sería producir la etiqueta.

### Lo que falta, y quién puede hacerlo

```
DESDE UN PORTÁTIL O SEGUNDA MÁQUINA EN 192.168.100.0/24

    ssh lucas@192.168.100.136
      └─ [2] PEER_EXTERNAL_AUTH = PROVEN

    # desde esa sesión, para [3a] como observación y no como inferencia:
    ps -o pid,ppid,comm -p $$ ; ps -o pid,ppid,comm -p $(ps -o ppid= -p $$)
      └─ árbol sshd → shell observado, no inferido
    echo "ppid de esta shell: $(ps -o ppid= -p $$)"
    systemctl show sshd -p Wants --value | grep -c display-manager
      └─ 0

  · si `ssh` autentica:  [2] PROVEN, [3a] confirmado por observación directa
  · si falla:            NO se toca la RX550.  El turno termina BLOCKED y el
                          análisis es exclusivamente de SSH.
```

`[2]` no se puede completar desde dentro de la máquina: un peer externo es por
definición otra máquina, y esta sesión no puede ser su propio peer. Un
`localhost` tampoco demostraría nada sobre la independencia del display, que es
justo lo que se mide.

## Efecto sobre `RESTORE_PLANNED`

```
antes
    ruta independiente de restore      ninguna
    TTY gate                          NOT_DEMONSTRATED  (bloqueante)

ahora
    ruta primaria                     bind amdgpu        documentable
    ruta secundaria                   reboot             documentable
    ruta independiente                sshd sobre enp3s0  CONSTRUIDA
    independencia de esa ruta         PROVEN_IN_KIND
    supervivencia ante takeover       NOT_PROVEN_EMPIRICALLY
    TTY gate                          NOT_DEMONSTRATED
                                      deja de ser el único bloqueo

bloqueo restante
    [2] peer externo autenticado       requiere un segundo host
```

`RESTORE_PLANNED` sigue **INCOMPLETO**. El hueco restante no es de diseño: es
una prueba que sólo otro equipo puede realizar.

Lo que cambia respecto del estado anterior es la naturaleza del bloqueo: ya no
depende de si la ruta de recovery funciona, sino de si se ha observado que
alguien la usa.

## Lo que no se hizo

```
VT change          NO
reboot             NO
unbind/bind GPU    NO
amdgpu / sysfs GPU NO
driver             NO
experimento B      NO
firewalld          NO modificado
sshd_config        NO modificado
authorized_keys    NO creado (no hacia falta)
commit             NO  (fuera del alcance de este turno)
```

## Observación sobre `COORDINACION.md`

El ejemplo de adquisición escribe el propietario así:

```bash
echo "$$ $(date -Is)" > .write-lock/owner
```

pero el ejemplo de comprobación lo lee así:

```bash
pid=$(grep -oE 'pid=[0-9]+' .write-lock/owner | head -1 | cut -d= -f2)
```

Un `grep -oE 'pid='` **no encuentra nada** en `29897 2026-...`. Con el
formato del propio ejemplo, la comprobación de `OWNER_ACTIVE` siempre daría
`OWNER_NOT_RUNNING`, es decir, un cerrojo vivo se leería como abandonado.

En este turno el fichero se escribió en la forma que el *lector* entiende:

```
pid=29897 session=sesion-provenance date=2026-10-01T07:01:07-03:00
```

No se ha modificado `COORDINACION.md`. Queda reportado como discrepancia
documental.
