"""rx550-torneo — gpu_finder. Detección determinística de la RX 550 y separación de la Intel HD 4600.

Fase 1: solo lectura. Nunca asume cardX/hwmonY fijos: resuelve por PCI vendor:device.
"""
import glob
import os
import re

from . import util


class GPUError(Exception):
    """Error seguro, con código clasificable."""

    def __init__(self, code, message):
        super().__init__(message)
        self.code = code
        self.message = message


DEFAULT_TARGET_PCI = "1002:699f"
DEFAULT_INTEL_PCI = "8086:0412"
DEFAULT_DRM_DIR = "/sys/class/drm"
DEFAULT_DRM_DEV_DIR = "/dev/dri"


def _card_from_dev(dev_dir):
    return os.path.basename(os.path.dirname(dev_dir))


def enumerate_cards(drm_dir=DEFAULT_DRM_DIR):
    _card_re = re.compile(r"^card[0-9]+$")
    cards = []
    for dev in sorted(glob.glob(os.path.join(drm_dir, "card*", "device"))):
        card = _card_from_dev(dev)
        if not _card_re.fullmatch(card):
            continue
        if not os.path.isdir(dev):
            continue
        vendor, device_id = util.device_hex_pair(dev)
        real = os.path.realpath(dev)
        bdf = util.pci_bdf_of(real)
        driver = None
        drv_link = os.path.join(dev, "driver")
        if os.path.islink(drv_link):
            driver = os.path.basename(os.path.realpath(drv_link))
        cards.append({
            "card": card,
            "device": dev,
            "realpath": real,
            "bdf": bdf,
            "vendor": vendor,
            "device_id": device_id,
            "pci": f"{vendor:04x}:{device_id:04x}" if vendor and device_id else None,
            "driver": driver,
        })
    return cards


def _find_by_pci(cards, pci_str):
    wanted = pci_str.lower().replace("0x", "")
    found = [c for c in cards if c["pci"] == wanted]
    return found


def find_card(cards, pci_str, role):
    found = _find_by_pci(cards, pci_str)
    if len(found) == 0:
        raise GPUError("NOT_FOUND", f"GPU {role} ({pci_str}) no encontrada entre las cards DRM")
    if len(found) > 1:
        raise GPUError("AMBIGUOUS", f"GPU {role} ({pci_str}) aparece {len(found)} veces; rechazando ambigüedad")
    return found[0]


def _hwmons(device_dir):
    out = []
    for hw in sorted(glob.glob(os.path.join(device_dir, "hwmon", "hwmon[0-9]*"))):
        if (os.path.exists(os.path.join(hw, "power1_cap"))
                and os.path.exists(os.path.join(hw, "temp1_input"))):
            out.append(hw)
    return out


def _render_node(bdf, render_from_devdri=True, drm_card=None):
    if render_from_devdri:
        link = os.path.join("/dev/dri/by-path", f"pci-{bdf}-render")
        if os.path.islink(link):
            target = os.path.realpath(link)
            if os.path.exists(target) and util.is_char_device(target):
                return target
    # Fallback por convención DRM: cardN <-> renderD(128+N) — verificado por by-path si existe.
    if drm_card:
        idx = "".join(ch for ch in drm_card if ch.isdigit())
        if idx:
            node = f"/dev/dri/renderD{128 + int(idx)}"
            if os.path.exists(node) and util.is_char_device(node):
                return node
    raise GPUError("NO_RENDER", f"no se pudo resolver el render node del BDF {bdf}")


def _connector_status(card_name, drm_dir=DEFAULT_DRM_DIR):
    out = {}
    for st in sorted(glob.glob(os.path.join(drm_dir, card_name, "*", "status"))):
        name = os.path.basename(os.path.dirname(st))
        out[name] = util.read_text(st)
    return out


def discover(target_pci=DEFAULT_TARGET_PCI, intel_pci=DEFAULT_INTEL_PCI,
             drm_dir=DEFAULT_DRM_DIR, dev_dir=DEFAULT_DRM_DEV_DIR,
             allow_display_on_target=False, overrides=None):
    """Devuelve un dict con la topología resuelta y validada.

    overrides: dict opcional para PRUEBAS — {'render_node': ..., 'hwmon': ...}.
    Se fuerza la validación de existencia/pertenencia de esos paths; si son
    inesperados/inexistentes se lanza GPUError.BAD_PATH (error seguro).
    raise GPUError ante ambigüedad, ausencia o condición de display no segura.
    """
    overrides = overrides or {}
    if not os.path.isdir(drm_dir):
        raise GPUError("NO_SYSFS", f"no existe el árbol DRM en {drm_dir}")

    cards = enumerate_cards(drm_dir)
    if not cards:
        raise GPUError("NO_CARDS", "no se encontraron cards DRM")

    target = find_card(cards, target_pci, "objetivo")
    if target["driver"] != "amdgpu":
        raise GPUError("BAD_DRIVER",
                       f"la GPU objetivo {target_pci} no usa amdgpu (driver={target['driver']})")

    intel = find_card(cards, intel_pci, "Intel")
    if intel["vendor"] != 0x8086:
        raise GPUError("BAD_DRIVER", f"Intel no es 0x8086: {intel['pci']}")

    # Display: la Intel DEBE tener un conector connected; la objetivo NO.
    intel_conn = _connector_status(intel["card"], drm_dir)
    intel_connected = [k for k, v in intel_conn.items() if (v or "").lower() == "connected"]
    target_conn = _connector_status(target["card"], drm_dir)
    target_connected = [k for k, v in target_conn.items() if (v or "").lower() == "connected"]
    if not intel_connected:
        raise GPUError("INTEL_NOT_DISPLAY", f"Intel {intel['card']} no tiene conector connected; "
                                            f"no se puede confirmar que sea la GPU de display")
    if len(intel_connected) > 1:
        raise GPUError("AMBIGUOUS", f"Intel {intel['card']} tiene {len(intel_connected)} conectores "
                                    f"connected; ambigüedad")
    if target_connected and not allow_display_on_target:
        raise GPUError("TARGET_IS_DISPLAY", f"la RX 550 {target['card']} tiene conectores connected "
                                            f"({target_connected}); no se permite que sea display")

    hwmons = _hwmons(target["device"])
    if len(hwmons) != 1:
        raise GPUError("AMBIGUOUS", f"la RX 550 tiene {len(hwmons)} hwmon válidos; esperaba 1 ({hwmons})")
    hwmon = hwmons[0]

    render = _render_node(target["bdf"], render_from_devdri=True, drm_card=target["card"])

    device_real = os.path.realpath(target["device"])

    # overrides de PRUEBA (rutas inesperadas/inexistentes deben fallar seguro)
    if "hwmon" in overrides:
        alt = overrides["hwmon"]
        if not os.path.isdir(alt) or not util.path_belongs_to_prefix(os.path.realpath(alt), device_real):
            raise GPUError("BAD_PATH", f"hwmon inesperado/inexistente: {alt}")
        hwmon = alt
    if "render_node" in overrides:
        alt = overrides["render_node"]
        if not os.path.exists(alt) or not util.is_char_device(alt):
            raise GPUError("BAD_PATH", f"render node inesperado/inexistente: {alt}")
        render = alt

    # Verificación de pertenencia: cada path bajo el device real de la RX 550.
    hwmon_real = os.path.realpath(hwmon)
    if not util.path_belongs_to_prefix(hwmon_real, device_real):
        raise GPUError("BAD_PATH", f"hwmon {hwmon} ({hwmon_real}) no pertenece al device de la RX 550")

    return {
        "target": target,
        "intel": intel,
        "display_cards": intel_connected,
        "hwmon": hwmon,
        "render_node": render,
        "drm_dir": drm_dir,
        "dev_dir": dev_dir,
        "target_pci": target_pci,
        "intel_pci": intel_pci,
        "drm_card": target["card"],
    }


def validate_no_display_on_target(gpu):
    """Re-chequeo estricto previo a cualquier operación: la RX 550 debe quedar sin display."""
    status = _connector_status(gpu["target"]["card"], gpu["drm_dir"])
    connected = [k for k, v in status.items() if (v or "").lower() == "connected"]
    if connected:
        raise GPUError("TARGET_IS_DISPLAY", f"RX 550 display→ conexión detectada ({connected}); aborrar")
    return True