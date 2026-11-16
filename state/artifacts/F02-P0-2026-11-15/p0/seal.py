"""Sellos y copias selladas. Ningún experimento opera sobre la DB protegida."""
import hashlib, os, shutil, sys

def sha256_file(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for b in iter(lambda: f.read(65536), b""):
            h.update(b)
    return h.hexdigest()

def assert_sha256(path, expected, label="file"):
    h = sha256_file(path)
    if h != expected:
        print(f"FAIL: {label} sha256 mismatch: {h} != {expected}", file=sys.stderr)
        return False
    print(f"OK:   {label} sha256 verified: {h}")
    return True

def snapshot(src, dst):
    shutil.copy2(src, dst)
    return sha256_file(dst)

def restore(snap, dst):
    if os.path.exists(dst): os.remove(dst)
    shutil.copy2(snap, dst)
    return sha256_file(dst)
