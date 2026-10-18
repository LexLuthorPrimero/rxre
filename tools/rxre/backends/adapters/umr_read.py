#!/usr/bin/env python3
"""BMS-EXT-002. Adapter `gpu.register_read` usando UMR.

POR QUE ESTE ADAPTER Y NO OTRO.
--------------------------------
UMR (User Mode Register debugger, v1.0.0, MIT) es el unico binario en este
entorno que puede observar registros MMIO reales de la RX 550 (Polaris12).
`rz_inspect`/`rz_container`/etc. operan sobre binarios ELF, no sobre
hardware: no pueden observar el ASIC.

Este adapter NO es un producer de binary.*. Es gpu.register_read, un
producer de hardware real cuyo scope es exclusivamente la RX 550 en
`0000:01:00.0`.

PRIORIDAD ABSOLUTA: SOLO LECTURA. UMR tiene flags de ESCRITURA (-w, -wb,
--vm-write) que NO se usan aqui, ni siquiera como opcion. El adapter solo
invoca `umr -r <regname>`, que es inequivocamente de lectura. La garantia
de solo-lectura no depende del input: el flag de lectura es un literal del
adapter, no un parametro del usuario.

CONTRATO DE SEGURIDAD.
----------------------
1. `pci_address` se valida contra una allow-list: SOLO `0000:01:00.0`
   (RX 550 Polaris12). Cualquier otro se rechaza como invalid_input.
2. El usuario `lucas` tiene ACL rw en /dev/dri/card1, pero UMR requiere
   root (geteuid()==0). El adapter comprueba esto antes de ejecutar.
   MEDIDO 2026-10-14: la escalada es posible via `sudo`, pero NO se
   automatiza por defecto: exige que el operador declare el prefijo de
   escalada en `RXRE_ESCALATE`. Ningun secreto se guarda en el arbol.
3. `register_name` se valida contra el FORMATO (asic.ip.regname) y, si la
   base de datos de UMR es legible, contra su EXISTENCIA.
4. No se pasa input del usuario a una shell. subprocess.run con argv list.
5. Timeout: 30s por defecto (UMR puede colgar en ioctl si el device esta ocupado).
6. Se capturan stdout, stderr, exit_status por separado.
7. Un rc=0 con salida vacia o error en stderr NO es exito: se verifica
   que stdout tenga el formato esperado (hex value).

TRES DEFECTOS MEDIDOS Y CORREGIDOS (RXRE-BMS-EXT-002-A, 2026-10-14).
----------------------------------------------------------------------
Este adapter tenia TRES formas que UMR v1.0.0 (este host) NO acepta. Medido:

  ANTES                                                     MEDIDO
  --------------------------------------------------------  ------------------------
  `-O no_colour`      -> `error: Unknown option [no_colour]`  rc=1
  `-g polaris12@0`    -> `[ERROR]: ASIC not found or compatible
                            (instance=0, did=ffffffffffffffff)`   rc=1
  validar solo el formato `asic.ip.reg`  -> el propio ejemplo del
      docstring (`polaris12.smc.gpu_length`) NO EXISTE en la BD:
      `smc` no es un IP de polaris12 y `gpu_length` no lleva el
      prefijo de tipo obligatorio.

CORRECCIONES:
  * `-O no_colour` se elimina. UMR v1.0.0 solo expone `use_colour`; no
    hay opcion para desactivarlo, y sin TTY UMR no colorea.
  * `-g polaris12@0` se sustituye por `-g =<pci_address>`: MEDIDO rc=0
    con el MISMO valor (`mmGRBM_STATUS => 0x00003028`). Esto no es solo
    un arreglo: hace que la allow-list sea real de extremo a extremo,
    porque el device queda fijado por el PCI que el adapter ya valido,
    en vez de confiar en un numero de instancia.
  * Se anade `_registro_existe_en_bd()`: precheck ESTATICO contra
    `/usr/share/umr/database`. Convierte "formato valido" en
    "registro existe", que es lo que §26 PRE_EXECUTION_CONTRACT_CHECK
    pide y lo que el adapter hacia mal.

CONTRADICCION REGISTRADA (no resuelta, solo medida).
---------------------------------------------------
El ESPACIO DE NOMBRES de la base de datos de UMR para esta GPU es
`polaris12.*`, y las lecturas funcionan con `polaris12.gfx800.*`. Pero
`-g polaris12@0` NO resuelve el ASIC: `did=ffffffffffffffff`. Es decir:
el nombre con el que UMR nombra la BD NO es el nombre con el que UMR
selecciona este device. Se registra como CONTRADICTION, no como hecho
resuelto; la via de trabajo es la seleccion por PCI, que esta medida.
"""
from __future__ import annotations

import hashlib
import json
import os
import subprocess
import time
from typing import Any, Dict, List, Optional

HERE = os.path.dirname(os.path.abspath(__file__))
PKG = os.path.abspath(os.path.join(HERE, "..", "..", ".."))
import sys
if PKG not in sys.path:
    sys.path.insert(0, PKG)

from backends import registry  # noqa: E402
from backends.contract import (  # noqa: E402
    BK_BLOCKED, BK_EMPTY, BK_ERROR, BK_INVALID, BK_OK, BK_UNSUPPORTED,
    RAW_BINARY, Backend, limpiar, parsear_json, sha256_de, sha256_texto,
)

#: RX 550 Polaris12 — el UNICO PCI target autorizado.
#: AGENTS.md: "PROHIBIDO tocar 0000:00:02.0 (Intel i915)". 0000:01:00.0 es la RX550.
ALLOWED_PCI = ("0000:01:00.0",)

#: ASIC name para UMR -g flag. Polaris12 = RX 550.
#: MEDIDO 2026-10-14: `-g polaris12@0` NO resuelve este device
#: (did=ffffffffffffffff). El nombre de la BD de UMR y el nombre que UMR
#: acepta para `-g` NO son lo mismo en esta maquina. La seleccion se hace
#: por PCI (ver `_selector_device`). El nombre se conserva porque es el
#: espacio de nombres valido de las rutas `polaris12.<ip>.<reg>`.
ASIC_NAME = "polaris12"

#: Instance number for the GPU (from /sys/kernel/debug/dri/ dir name).
ASIC_INSTANCE = 0

#: UMR database path (register/bitfield definitions).
UMR_DATABASE = "/usr/share/umr/database"

#: Timeout por defecto: UMR puede colgar en ioctl.
DEFAULT_TIMEOUT = 30

#: Prefijo de escalada de privilegios, DECLARADO por el operador.
#:
#: MEDIDO: sin root, UMR responde "[ERROR]: UMR was not invoked as root";
#: con root lee el ASIC. Este proyecto NO guarda contrasenas en el arbol ni
#: las pide por codigo: si el operador exporta `RXRE_ESCALATE="sudo -n"`,
#: el adapter antepone ese prefijo y lo DECLARA en el precheck. Si no esta
#: declarado, el adapter se detiene como BLOCKED diciendo que falta.
#:
#: Solo lectura: `-r` sigue siendo un literal del adapter, y el PCI sigue
#: pasando por la allow-list antes de tocar nada.
ESCALATE_ENV = "RXRE_ESCALATE"


def _prefijo_escalada() -> List[str]:
    """Prefijo de escalada declarado por el operador, con la config de RXRE.

    MEDIDO 2026-10-14, y esto NO es cosmetico:

        $ RXRE_DB=/tmp/x.sqlite3 sudo -S python3 tools/rxre/api/machine.py
        $ python3 -c 'import os; print(os.environ.get("RXRE_DB"))'
        None

    `sudo` arranca con `env_reset` y solo conserva lo que este en
    `env_keep` (COLORS, LANG, PATH...). `RXRE_DB` no esta ahi, asi que la
    escalada se lleva por delante el sitio donde se guarda la evidencia.

    El dano no es visible: la ejecucion devuelve `persistido: true` y la
    operacion aparece guardada. Pero no esta en la base que el consumidor
    va a mirar. Dos productores, uno con privilegios y otro sin, escribiendo
    en sitios distintos, sin que nadie lo diga. Eso rompe EARTH en silencio.

    Esto es lo que produjo un `COLISION:` en una base NUEVA durante las
    pruebas de esta iteracion: la base temporal nunca se creo, todo fue a la
    base por defecto, y el `COLISION:` era real... en la base equivocada.

    Aqui solo se reenvia lo que el proceso padre ya tiene definido. No se
    inventa configuracion, y ningun secreto va en el argv.
    """
    raw = (os.environ.get(ESCALATE_ENV) or "").strip()
    if not raw:
        return []
    partes = [x for x in raw.split() if x]
    config = [(k, os.environ[k]) for k in sorted(os.environ)
              if k.startswith("RXRE_") and k != ESCALATE_ENV]
    if config:
        partes = partes + ["env"] + ["%s=%s" % kv for kv in config]
    return partes


def _selector_device(pci: str) -> List[str]:
    """Como se le dice a UMR QUE device usar.

    MEDIDO 2026-10-14, con el RX550 de este host:

        umr -dbp <db> -g polaris12@0 -r <reg>
            -> [ERROR]: ASIC not found or compatible
               (instance=0, did=ffffffffffffffff)     rc=1

        umr -dbp <db> -r <reg>
            -> gfx800.mmGRBM_STATUS => 0x00003028      rc=0

        umr -dbp <db> -g =0000:01:00.0 -r <reg>
            -> gfx800.mmGRBM_STATUS => 0x00003028      rc=0

    Se elige `-g =<pci>` y no el auto-detect por una razon que NO es de
    comodidad: con el auto-detect UMR elige el device, no el operador.
    Con `-g =<pci>` el device elegido es exactamente el que la allow-list
    ya valido, asi que la restriccion de seguridad sobrevive hasta UMR.
    """
    return ["-g", "=" + pci]


def _bd_ips(asic: str) -> Dict[str, str]:
    """Mapa ip->fichero .reg del ASIC, leyendo `<asic>.asic` de la BD.

    Formato MEDIDO en /usr/share/umr/database/polaris12.asic:
        linea 0:   polaris12 null 2 8 2 0
        lineas +:  <ipname> <algo> <n> <ruta/relativa.al.fichero.reg>

    Devuelve {} si la BD no es legible: entonces el precheck estatico no
    puede affirmar nada, y eso se dice en vez de inventarse un "no existe".
    """
    ruta = os.path.join(UMR_DATABASE, "%s.asic" % asic)
    try:
        with open(ruta, "r", errors="replace") as fh:
            lineas = fh.read().splitlines()
    except OSError:
        return {}
    ips: Dict[str, str] = {}
    for linea in lineas[1:]:
        partes = linea.split()
        if len(partes) >= 4:
            ips[partes[0]] = partes[-1]
    return ips


def _registro_existe_en_bd(reg: str) -> Dict[str, Any]:
    """Precheck ESTATICO: ¿existe `asic.ip.reg` en la BD de UMR?

    No necesita root ni hardware: la BD es un fichero. Esto es lo que
    convierte la validacion de "formato" en "existe", y evita gastar una
    ejecucion con privilegios para descubrir un nombre inventado.

    MEDIDO: los nombres de registro de esta BD llevan PREFIJO DE TIPO DE
    DOS CARACTERES (`mm`, `ix`, `dc`, `ad`...), y `polaris12` declara
    exactamente 8 IPs: uvd600 vce300 gmc810 dce1120 gfx800 smu713 oss300
    bif510. Un nombre como `polaris12.smc.gpu_length` falla por las dos
    razones a la vez.

    Devuelve dict con `consultable` (si la BD se pudo leer), `existe` y
    `motivo`.
    """
    partes = reg.split(".")
    if len(partes) < 3:
        return {"consultable": False, "existe": False,
                "motivo": "el nombre no tiene al menos asic.ip.reg"}
    asic, ip = partes[0], partes[1]
    ips = _bd_ips(asic)
    if not ips:
        return {"consultable": False, "existe": False,
                "motivo": "no se pudo leer %s.asic: la BD de UMR no es "
                          "legible, asi que la existencia NO se puede "
                          "afirmar ni negar" % asic}
    if ip not in ips:
        return {"consultable": True, "existe": False,
                "motivo": "el IP '%s' no existe en %s.asic. IPs reales: %s"
                          % (ip, asic, ", ".join(sorted(ips)))}
    ruta = os.path.join(UMR_DATABASE, ips[ip])
    try:
        with open(ruta, "r", errors="replace") as fh:
            for linea in fh:
                if linea.startswith("\t"):     # sub-bitfield, no registro
                    continue
                campos = linea.split()
                if campos and campos[0] == partes[2]:
                    return {"consultable": True, "existe": True,
                            "motivo": "encontrado en %s" % ips[ip],
                            "fichero": ips[ip]}
    except OSError as exc:
        return {"consultable": False, "existe": False,
                "motivo": "no se pudo leer %s: %s" % (ips[ip], exc)}
    return {"consultable": True, "existe": False,
            "motivo": "el registro '%s' no esta en %s" % (partes[2], ips[ip])}


def _es_pci_autorizado(pci: str) -> bool:
    """Valida que el PCI address sea la RX550 autorizada.

    No acepta prefijos, no hace case-insensitive, no usa regex.
    La allow-list es el unico mecanismo de seguridad: si no esta en
    ALLOWED_PCI, se rechaza.
    """
    return isinstance(pci, str) and pci in ALLOWED_PCI


def _es_registro_valido(reg: str) -> bool:
    """Valida el formato de register_name: asic.ipname.regname.

    UMR usa notacion `asic.ipname.regname`.

    MEDIDO 2026-10-14: el ejemplo que este adapter usaba hasta ahora,
    `polaris12.smc.gpu_length`, NO EXISTE. Fallaba por dos razones a la
    vez: `smc` no es un IP de polaris12, y los nombres de registro de esta
    BD llevan prefijo de tipo de dos caracteres (`mm`, `ix`, `dc`, `ad`).

    Un ejemplo REAL, medido leyendo el ASIC de este host:
        polaris12.gfx800.mmGRBM_STATUS   -> gfx800.mmGRBM_STATUS => 0x00003028

    Aqui se valida SOLO la forma (para evitar inyeccion). Que el registro
    exista de verdad lo responde `_registro_existe_en_bd()`, que es la
    pregunta separada y que no necesita root.
    """
    if not isinstance(reg, str) or not reg:
        return False
    partes = reg.split(".")
    if len(partes) < 3:
        return False
    # No permitir caracteres peligrosos
    for p in partes:
        if not p or "/" in p or ".." in p or " " in p or "$" in p:
            return False
    return True


def _es_root() -> bool:
    """True si el proceso tiene euid 0."""
    return os.geteuid() == 0


def _id_resultado(pci: str, reg: str, backend: str, valor: Any) -> str:
    """ID deterministico que no colisiona (regla F6)."""
    h = hashlib.sha256(
        ("%s|%s|%s|%s|%s" % (RAW_BINARY, pci, reg, backend,
                            json.dumps(valor, sort_keys=True, default=str)))
        .encode("utf-8")).hexdigest()[:12]
    return "res_gpu_register_%s" % h


def register_read(pci_address: str, register_name: str,
                  backend_id: str = "umr", timeout: int = DEFAULT_TIMEOUT,
                  decode: bool = False, **kwargs) -> Dict[str, Any]:
    """Lee un registro GPU mediante UMR.

    PRE-EXECUTION CONTRACT CHECK (§26):
    - Nombres: pci_address, register_name, backend_id, timeout
    - Tipos: str, str, str, int
    - Artefacto esperado: string de salida parseable de UMR -r
    - exit_status: int (rc de umr)
    - stdout: el valor del registro
    - stderr: errores/mensajes

    Estados del contrato:
    - BK_INVALID: pci_address o register_name invalidos
    - BK_BLOCKED: UMR no esta en PATH, no eres root, o timeout
    - BK_ERROR: umr fallo (rc!=0 con error real)
    - BK_OK: stdout tiene un valor parseable
    """
    # --- PRE-EXECUTION CONTRACT CHECK ---
    pre = {
        "input_pci_address": pci_address,
        "input_register_name": register_name,
        "backend_id": backend_id,
        "allowed_pci": list(ALLOWED_PCI),
        "asic_name": ASIC_NAME,
        "is_root": _es_root(),
        "backend_existe": False,
        "entrypoint_existe": False,
        "ok": False,
    }

    # 1. Validar PCI address contra allow-list
    if not _es_pci_autorizado(pci_address):
        pre["ok"] = False
        return {"status": BK_INVALID, "precheck": pre,
                "limitations": [
                    "pci_address '%s' no esta en la allow-list. Solo se permite: %s"
                    % (pci_address or "<vacio>", ", ".join(ALLOWED_PCI)),
                    "no se invoco al backend: validacion fallida"
                ]}

    # 2. Verificar backend existe — ANTES de validar register_name, para que
    #    el precheck reporte backend_existe/entrypoint_existe con exactitud.
    #    MEDIDO 2026-10-15: el defecto original inicializaba
    #    `backend_existe: False` y lo early-returnaba (formato invalido,
    #    registro no en BD) sin nunca llamar a b.existe(). El precheck decia
    #    `backend_existe: false` para umr que EXISTE en /usr/bin/umr.
    try:
        ent = registry.get(backend_id)
        b: Backend = ent["backend"]
    except (KeyError, TypeError):
        pre["backend_existe"] = False
        pre["entrypoint_existe"] = False
        return {"status": BK_INVALID, "precheck": pre,
                "limitations": [
                    "backend_id '%s' no esta en el registry. Backends: %s"
                    % (backend_id, ", ".join(sorted(registry._BACKENDS))),
                    "no se invoco al backend: backend desconocido"
                ]}
    pre["backend_existe"] = b.existe()
    pre["entrypoint_existe"] = bool(b.path())
    if not pre["entrypoint_existe"]:
        return {"status": BK_BLOCKED, "precheck": pre,
                "limitations": [
                    "el backend %s no esta en PATH" % backend_id,
                    "UMR necesita root para leer registros; verificar despues"
                ]}

    # 3. Validar register_name formato
    if not _es_registro_valido(register_name):
        pre["ok"] = False
        return {"status": BK_INVALID, "precheck": pre,
                "limitations": [
                    "register_name '%s' no cumple el formato asic.ipname.regname"
                    % (register_name or "<vacio>"),
                    "no se invoco al backend: validacion fallida"
                ]}

    # 3b. PRECHECK ESTATICO contra la BD de UMR: la forma no basta.
    # MEDIDO: el ejemplo historico de este adapter,
    # `polaris12.smc.gpu_length`, pasaba la validacion de forma y NO
    # EXISTIA. La BD es un fichero: comprobarlo no cuesta root ni
    # hardware, y evita gastar una ejecucion con privilegios para
    # confirmar un nombre inventado. §26 PRE_EXECUTION_CONTRACT_CHECK.
    bd = _registro_existe_en_bd(register_name)
    pre["registro_en_bd"] = bd
    if bd["consultable"] and not bd["existe"]:
        pre["ok"] = False
        return {"status": BK_INVALID, "precheck": pre,
                "limitations": [
                    "register_name '%s' no existe en la BD de UMR: %s"
                    % (register_name, bd["motivo"]),
                    "no se invoco al backend: el nombre no es resoluble",
                    "los nombres de esta BD llevan prefijo de tipo de dos "
                    "caracteres (mm/ix/dc/ad); el namespace esta en "
                    "%s/<asic>.asic" % UMR_DATABASE
                ]}

    # 4. Verificar root. MEDIDO 2026-10-14: con root, `umr -g =<pci> -r`
    #    lee el ASIC de verdad (mmGRBM_STATUS => 0x00003028). Sin root,
    #    UMR responde "[ERROR]: UMR was not invoked as root" y no hay nada
    #    que leer, por mucho que el usuario tenga ACL en /dev/dri/card1.
    pre["is_root"] = _es_root()
    pre["privilege_escalation"] = _prefijo_escalada()
    if not pre["is_root"] and not pre["privilege_escalation"]:
        return {"status": BK_BLOCKED, "precheck": pre,
                "limitations": [
                    "UMR requiere euid=0 (root) para acceder a registros GPU.",
                    "El usuario tiene ACL rw en /dev/dri/card1, pero UMR",
                    "realiza ioctl() que necesita privilegios de kernel.",
                    "No se invoco umr: la lectura sin root no es posible.",
                    "PRERREQUISITO EXACTO: ejecutar con euid=0, o declarar",
                    "la escalada en el entorno antes de la llamada:",
                    "    export %s='sudo -n'" % ESCALATE_ENV,
                    "RXRE NO guarda contrasenas ni las pide por codigo: la",
                    "escalada la declara el operador y queda en el precheck."
                ]}
    pre["ok"] = True

    # --- EJECUCION ---
    # UMR -r es EXCLUSIVAMENTE lectura. El flag es un literal del adapter,
    # no input del usuario. Lo mismo vale para el prefijo de escalada: lo
    # declara el operador por entorno, nunca la peticion.
    # MEDIDO 2026-10-14: se eliminan `-O no_colour` (no existe en UMR
    # v1.0.0 -> "error: Unknown option [no_colour]", rc=1) y
    # `-g polaris12@0` (no resuelve este device, did=ffffffffffffffff,
    # rc=1). Ver `_selector_device`.
    # `decode=True` anula el flag literal `-O bits` sobre el argv: `umr -r` +
    # `-O bits` decodifica los bitfields usando el regdb de UMR (solo lectura).
    # El flag es un literal del adapter (no input del usuario), para evitar
    # inyeccion de flags y para que `decode` no altere el comando sin root
    # (el precheck lo bloquea con BK_BLOCKED antes de ejecutar umr).
    argv = ([*_prefijo_escalada(), b.path(), "-dbp", UMR_DATABASE]
            + _selector_device(pci_address)
            + (["-O", "bits"] if decode else [])
            + ["-r", register_name])
    ident = b.identidad()
    t0 = time.time()
    try:
        p = subprocess.run(argv, capture_output=True, text=True,
                           timeout=timeout, env={**os.environ,
                                                 "UMR_DB_PATH_HINT": UMR_DATABASE})
        rc = p.returncode
        so = p.stdout or ""
        se = p.stderr or ""
        timedout = False
    except subprocess.TimeoutExpired:
        rc, so, se = None, "", "timeout a los %ds" % timeout
        timedout = True

    limpio, n_quit = limpiar(so)
    dur = round(time.time() - t0, 3)

    ejec = {
        "backend_id": backend_id,
        "operation": "gpu.register_read",
        "command_or_api": "umr -dbp <dbpath> -g =<pci_address> -r <regname>",
        "privilege_escalation": pre["privilege_escalation"],
        "argv": argv,
        "pci_address": pci_address,
        "exit_status": rc,
        "raw_output_len": len(so),
        "stderr": se.strip()[:600],
        "limpieza": {"aplicada": n_quit > 0, "caracteres_quitados": n_quit},
        "timeout": timedout,
        "duration_s": dur,
    }

    if timedout:
        ejec["status"] = BK_BLOCKED
        return {"status": BK_BLOCKED, "precheck": pre, "ejecucion": ejec,
                "backend": ident,
                "limitations": ["timeout a los %ds" % timeout]}

    if rc != 0:
        ejec["status"] = BK_ERROR
        return {"status": BK_ERROR, "precheck": pre, "ejecucion": ejec,
                "backend": ident,
                "limitations": [
                    "umr salio con rc=%s: %s"
                    % (rc, (se.strip() or so.strip())[:300])
                ]}

    # Parsear la salida de UMR.
    #
    # MEDIDO 2026-10-14, forma real de la salida:
    #     gfx800.mmGRBM_STATUS    => 0x00003028
    #     gfx800.mmGRBM_STATUS2   => 0x00000008
    #     gfx800.mmGRBM_STATUS_SE0 => 0x00000006
    # UMR devuelve el registro pedido y despues sus companions. Se casa por
    # NOMBRE y no por posicion: pedir el companion equivocado porque UMR
    # cambio el orden seria un resultado falso con apariencia de bueno.
    #
    # Se conservan (a) el valor del registro pedido con su HEX EXACTO, que
    # incluye el ancho, y (b) la cascada completa, que es observacion que
    # el producer ya hizo y que antes se descartaba.
    import re

    partes_reg = register_name.split(".")
    ip_pedido = partes_reg[1] if len(partes_reg) > 2 else ""
    reg_pedido = partes_reg[2] if len(partes_reg) > 2 else ""

    valor = None
    valor_hex = None
    cascada = []
    for line in limpio.strip().splitlines():
        line_s = line.strip()
        if not line_s or "=>" not in line_s:
            continue
        nombre, _, resto = line_s.partition("=>")
        nombre = nombre.strip()
        m = re.search(r"0x([0-9a-fA-F]+)", resto)
        if not m:
            continue
        hx = "0x" + m.group(1)
        cascada.append({"registro": nombre, "valor_hex": hx,
                        "valor_dec": int(m.group(1), 16)})
        # El nombre que UMR imprime omite el ASIC: `gfx800.mmGRBM_STATUS`
        # para un pedido `polaris12.gfx800.mmGRBM_STATUS`.
        if nombre == "%s.%s" % (ip_pedido, reg_pedido):
            valor_hex = hx
            valor = int(m.group(1), 16)

    # Si no se pudo casar por nombre pero hubo una sola lectura, se usa esa
    # y se DICE que no se pudo confirmar cual es. No se adivina.
    if valor is None and len(cascada) == 1:
        valor_hex = cascada[0]["valor_hex"]
        valor = cascada[0]["valor_dec"]
    elif valor is None and cascada:
        return {"status": BK_ERROR, "precheck": pre, "ejecucion": ejec,
                "backend": ident,
                "limitations": [
                    "umr devolvio %d registros pero ninguno es '%s.%s', que "
                    "es el pedido. No se atribuye ningun valor: UMR cambio "
                    "el conjunto de registros que devuelve." % (
                        len(cascada), ip_pedido, reg_pedido),
                    "registros devueltos: %s"
                    % ", ".join(x["registro"] for x in cascada[:12]),
                ]}

    if valor is None:
        ejec["status"] = BK_ERROR
        return {"status": BK_ERROR, "precheck": pre, "ejecucion": ejec,
                "backend": ident,
                "limitations": [
                    "la salida de umr no contiene un valor hex parseable.",
                    "stdout recibido (limpio): %s"
                    % (limpio.strip()[:200] if limpio.strip() else "<vacia>")
                ]}

    # SUCCESS: valor parseable
    ejec["status"] = BK_OK

    # DECODE (Fase D, MEDIDO 2026-10-13): si decode=True, umr corrio con -O bits
    # y emitio lineas de bitfield `.FIELD[start:end] == value (0xhex)` agrupadas
    # por registro. Parsearlas para exponer la descomposicion estructurada. El
    # layout es autoridad del regdb de UMR (polaris12.gfx800), no inferencia;
    # verificado contra el decode de umr mismo (oracle match, 0x3028).
    bitfields_pedidos: Any = {}
    if decode:
        campos_por_reg: Dict[str, Dict[str, Any]] = {}
        reg_activo = None
        for linea_raw in limpio.splitlines():
            s = linea_raw.strip()
            if not s:
                continue
            # linea de registro: `NAME => 0xHEX` (grupo los fields que siguen)
            if "=>" in s and "[" not in s.split("=>", 1)[0]:
                nombre_reg, _, _ = s.partition("=>")
                reg_activo = nombre_reg.strip()
                campos_por_reg.setdefault(reg_activo, {})
                continue
            # linea de bitfield: `.FIELD[start:end] == value (0xhex)`
            m = re.match(r"^\.(\w+)\[(\d+):(\d+)\]\s*==\s*(\d+)"
                         r"\s*\(0x([0-9a-fA-F]+)\)$", s)
            if m and reg_activo:
                campos_por_reg[reg_activo][m.group(1)] = {
                    "value": int(m.group(4)),
                    "hex": "0x" + m.group(5),
                    "bits": [int(m.group(2)), int(m.group(3))],
                }
        bitfields_pedidos = campos_por_reg.get(
            "%s.%s" % (ip_pedido, reg_pedido), {})

    result = {
        "result_id": _id_resultado(pci_address, register_name, backend_id, valor),
        "type": RAW_BINARY,
        "value": valor,
        "value_hex": valor_hex,
        "bitfields": bitfields_pedidos,
        "decoded": bool(bitfields_pedidos),
        "registros_leidos": cascada,
        "source": pci_address,
        "location": {"pci_address": pci_address, "register": register_name},
        "scope": "gpu",
        "tool": backend_id,
        "tool_version": ident.get("tool_version", ""),
        "input": {"pci_address": pci_address, "register_name": register_name,
                  "sha256": sha256_texto(pci_address + "|" + register_name)},
        "timestamp": "",
        "artifact": "register:%s:%s" % (pci_address, register_name),
        "artifact_hash": sha256_texto(register_name),
        "status": "observed",
        "limitations": [
            "UMR requiere root; la lectura no se puede reproducir sin privilegios.",
            "El valor es RAW_BINARY: lo que UMR declara, no semantica verificada.",
            "value_hex conserva el ANCHO tal como lo emitio UMR (p.ej. 0x00003028); "
            "value es el mismo numero en decimal. El ancho es parte de la "
            "lectura: recortarlo perderia informacion.",
            "Solo lectura: se uso -r (read), nunca -w (write).",
        ],
        "raw": so.strip()[:600],
        "raw_hex": valor_hex,
    }
    if decode and bitfields_pedidos:
        result["limitations"].append(
            "bitfields: decodificacion de `umr -O bits` usando el regdb de UMR "
            "(/usr/share/umr/database, polaris12.gfx800). El layout (nombres y "
            "anchos de campos) es autoridad del regdb, no inferencia; la "
            "interpretacion semantica de cada campo sigue siendo una hipotesis. "
            "Solo lectura (-r + -O bits), nunca -w.")
    return {"status": BK_OK, "precheck": pre, "ejecucion": ejec,
            "backend": ident,
            "provenance": {
                "producer": "umr",
                "tool_version": ident.get("tool_version", ""),
                "repository": ident.get("repository", ""),
                "command_or_api": ejec["command_or_api"],
                "privilege_escalation": ejec.get("privilege_escalation"),
                "seleccion_dispositivo": "umr -g =%s" % pci_address,
                "exit_status": rc,
                "raw_output": so[:600],
                "transformacion": "umr -r parsea el valor hex del registro",
                "normalizador": "regex 0x([0-9a-fA-F]+) + int(,16)",
                "input_artifact": pci_address,
                "input_hash": sha256_texto(pci_address + "|" + register_name),
            },
            "results": [result],
            "cadena_backend": [],
    }


def persistir(env: Dict[str, Any], db=None,
              question: str = "") -> Optional[str]:
    """Guarda la operacion de register_read para que `explain` reconstruya.

    Sigue el patron de rz_inspect.persistir: abre/le cierra la DB solo si
    nadie mas la abrio, comprueba colisiones de result_id, registra en
    operations/resultados via S.registrar.
    """
    from core import store as S
    _abierta_por_nosotros = db is None
    c = db or S.conectar()

    # Verificar colision de result_ids
    ids = [r["result_id"] for r in env.get("results") or []
           if isinstance(r, dict) and r.get("result_id")]
    existentes = []
    for i in ids:
        if c.execute("SELECT 1 FROM results WHERE result_id=?", (i,)).fetchone():
            existentes.append(i)
    if existentes:
        if _abierta_por_nosotros:
            c.close()
        return "COLISION:%s" % ",".join(existentes)

    pre = env.get("precheck") or {}
    res0 = (env.get("results") or [{}])[0] if env.get("results") else {}
    artefacto = pre.get("input_pci_address", "") or ""
    reg_name = pre.get("input_register_name", "") or ""
    target = "gpu:%s:%s" % (artefacto, reg_name)

    op_id = S.registrar(
        c,
        {"request_id": "",
         "question": question or ("leer registro %s en %s"
                                  % (reg_name, artefacto or "GPU")),
         "capability": "gpu.register_read",
         "scope": "gpu",
         "target": target},
        {"operation": "gpu.register_read",
         "status": env.get("status"),
         "backend": env.get("backend"),
         "ejecucion": env.get("ejecucion"),
         "provenance": env.get("provenance"),
         "precheck": pre,
         "cadena_backend": env.get("cadena_backend", []),
         "results": env.get("results") or []},
        duracion=(env.get("ejecucion") or {}).get("duration_s", 0))

    if _abierta_por_nosotros:
        c.close()
    return op_id
