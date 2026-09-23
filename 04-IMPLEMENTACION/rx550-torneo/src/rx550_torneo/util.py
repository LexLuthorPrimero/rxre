"""rx550-torneo — utilidades de bajo nivel (solo lectura de sysfs)."""
import os
import re
import stat
import errno


BDF_RE = re.compile(r"[0-9a-fA-F]{4}:[0-9a-fA-F]{2}:[0-9a-fA-F]{2}\.[0-9a-fA-F]")
HEX_RE = re.compile(r"0x([0-9a-fA-F]+)")

_SYS_PREFIX = "/sys/"


class SafeIOError(Exception):
    """Error de lectura/validación de un archivo sysfs o fs de estado."""


def read_text(path, strip=True, missing_ok=True):
    """Lectura READ-ONLY de un archivo. Devuelve str o None (si no existe).

    NO usa os.path.realpath: en sysfs los atributos se escriben RELATIVOS al
    symlink del device (p.ej. .../card1/device/device) y realpath los colapsa.
    El kernel resuelve los symlinks al abrir el path original.
    """
    try:
        with open(path, "r", encoding="utf-8", errors="replace") as fh:
            data = fh.read()
    except FileNotFoundError:
        if missing_ok:
            return None
        raise SafeIOError(f"no existe: {path}")
    except PermissionError as exc:
        raise SafeIOError(f"sin permiso de lectura: {path} ({errno.errorcode.get(exc.errno, exc)})")
    except OSError as exc:
        raise SafeIOError(f"error de lectura {path}: {exc}")
    return data.strip() if strip else data


def read_lines(path, missing_ok=True):
    txt = read_text(path, strip=False, missing_ok=missing_ok)
    if txt is None:
        return None
    return [ln.strip() for ln in txt.splitlines() if ln.strip()]


def read_int(path, missing_ok=True):
    txt = read_text(path, strip=True, missing_ok=missing_ok)
    if txt is None:
        return None
    if txt.lower().startswith("0x"):
        return int(txt, 16)
    return int(txt)


def pci_bdf_of(real_path):
    """Extrae el BDF del DEVICE (último match) de un path real bajo /sys.

    Ojo: en el árbol realpath pueden aparecer antes los BDF de los puentes
    PCIe (p.ej. 0000:00:01.0) y al final el del dispositivo (0000:01:00.0).
    """
    matches = [part for part in real_path.split(os.sep) if BDF_RE.fullmatch(part)]
    return matches[-1] if matches else None


def hex_from(vendor_buf):
    m = HEX_RE.search(vendor_buf or "")
    return int(m.group(1), 16) if m else None


def device_hex_pair(dev_dir):
    v = read_text(os.path.join(dev_dir, "vendor"), missing_ok=True)
    d = read_text(os.path.join(dev_dir, "device"), missing_ok=True)
    return hex_from(v), hex_from(d)


def is_char_device(path):
    try:
        return stat.S_ISCHR(os.stat(path).st_mode)
    except OSError:
        return False


def path_belongs_to_prefix(child, parent):
    """True si child está bajo parent usando comp t realpath y separador."""
    try:
        c = os.path.realpath(child)
        p = os.path.realpath(parent)
        return c == p or c.startswith(p + os.sep)
    except OSError:
        return False


def guard_no_sys_write(path):
    """Cualquier intento de abrir un path de /sys en modo escritura es un bug de diseño."""
    if os.path.realpath(path).startswith(_SYS_PREFIX):
        raise RuntimeError(f"escritura a sysfs bloqueada por diseño: {path}")