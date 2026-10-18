#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0
"""SWF estructural parser (FWS/CWS, SWF <= 10).

PRODUCER estructural: emite un inventario de tags con offsets y
longitudes.  NO interpreta semantica del contenido.

Correccion vs. intento previo: el RECT tiene 4 campos bit-packed
(Xmin/Xmax/Ymin/Ymax), luego nbytes = (5 + 4*Nbits + 7)//8.
El intento anterior usaba 5*Nbits, lo que desplazaba el inicio
del stream de tags 2 bytes y corrompia todo el inventario.
"""
import collections
import hashlib
import json
import lzma
import struct
import sys
import zlib

TAG_NAMES = {
    0: "End", 1: "ShowFrame", 2: "DefineShape", 4: "PlaceObject",
    5: "RemoveObject", 6: "DefineBits", 8: "JPEGTables",
    9: "SetBackgroundColor", 10: "DefineFont", 11: "DefineText",
    12: "DoAction", 13: "DefineFontInfo", 14: "DefineSound",
    15: "StartSound", 16: "DefineButtonSound", 17: "SoundStreamHead",
    18: "SoundStreamBlock", 19: "DefineBitsLossless",
    20: "DefineBitsJPEG2", 21: "DefineShape2", 22: "DefineButtonCxform",
    23: "Protect", 26: "PlaceObject2", 28: "RemoveObject2",
    32: "DefineShape3", 33: "DefineText2", 34: "DefineButton2",
    35: "DefineBitsJPEG3", 36: "DefineBitsLossless2", 37: "DefineEditText",
    39: "DefineSprite", 43: "FrameLabel", 45: "SoundStreamHead2",
    46: "DefineMorphShape", 48: "DefineFont2", 56: "ExportAssets",
    57: "ImportAssets", 58: "EnableDebugger", 59: "DoInitAction",
    60: "DefineVideoStream", 61: "VideoFrame", 62: "DefineFontInfo2",
    64: "EnableDebugger2", 65: "ScriptLimits", 66: "SetTabIndex",
    69: "FileAttributes", 70: "PlaceObject3", 71: "ImportAssets2",
    73: "DefineFontAlignZones", 74: "CSMTextSettings", 75: "DefineFont3",
    77: "SymbolClass", 78: "Metadata", 79: "DefineScalingGrid",
    82: "DoABC", 83: "DefineShape4", 84: "DefineMorphShape2",
    86: "DefineSceneAndFrameLabelData", 87: "DefineBinaryData",
    88: "DefineFontName", 89: "StartSound2", 90: "DefineBitsJPEG4",
    91: "DefineFont4", 93: "EnableTelemetry",
}


def read_rect(body, off):
    """RECT = 5 bits (Nbits) + 4 campos con signo de Nbits cada uno."""
    nbits = body[off] >> 3
    total = 5 + 4 * nbits
    nbytes = (total + 7) // 8

    def bits(start, n):
        v = 0
        for i in range(n):
            p = start + i
            v = (v << 1) | ((body[off + p // 8] >> (7 - p % 8)) & 1)
        return v

    s = 5
    vals = []
    for _ in range(4):
        v = bits(s, nbits)
        if v >= (1 << (nbits - 1)):
            v -= (1 << nbits)
        vals.append(v)
        s += nbits
    return vals, nbytes


def parse(path):
    data = open(path, "rb").read()
    sig, ver = data[:3], data[3]
    declared = struct.unpack("<I", data[4:8])[0]
    if sig == b"CWS":
        body = zlib.decompress(data[8:])
    elif sig == b"FWS":
        body = data[8:]
    elif sig == b"ZWS":
        body = lzma.decompress(data[8:])
    else:
        raise ValueError("firma SWF desconocida %r" % sig)
    if len(body) + 8 != declared:
        raise ValueError("longitud declarada %d != cuerpo %d"
                         % (declared, len(body) + 8))
    rect, nbytes = read_rect(body, 0)
    off = nbytes
    frame_rate = struct.unpack("<H", body[off:off + 2])[0] / 256.0
    frame_count = struct.unpack("<H", body[off + 2:off + 4])[0]
    off += 4

    tags = []
    n = len(body)
    while off + 2 <= n:
        hdr = struct.unpack("<H", body[off:off + 2])[0]
        code, ln = hdr >> 6, hdr & 0x3F
        off += 2
        if ln == 0x3F:
            ln = struct.unpack("<I", body[off:off + 4])[0]
            off += 4
        tags.append((code, ln, off))
        off += ln

    hist = collections.Counter(t[0] for t in tags)
    return {
        "signature": sig.decode("latin1"),
        "version": ver,
        "file_length_declared": declared,
        "body_bytes": len(body),
        "sha256_body": hashlib.sha256(body).hexdigest(),
        "rect_twips": rect,
        "stage_px": [rect[1] / 20, rect[3] / 20],
        "frame_rate": frame_rate,
        "frame_count": frame_count,
        "tag_count": len(tags),
        "tag_histogram": {TAG_NAMES.get(c, "Unknown(%d)" % c): v
                          for c, v in sorted(hist.items())},
        "tags": [{"code": c, "name": TAG_NAMES.get(c, "Unknown(%d)" % c),
                  "length": l, "offset": o} for c, l, o in tags],
    }


if __name__ == "__main__":
    info = parse(sys.argv[1])
    out = sys.argv[2] if len(sys.argv) > 2 else None
    txt = json.dumps(info, indent=1, ensure_ascii=False)
    if out:
        open(out, "w", encoding="utf-8").write(txt)
    print("signature:", info["signature"], "version:", info["version"])
    print("declared:", info["file_length_declared"],
          "body:", info["body_bytes"])
    print("stage(px):", info["stage_px"], "fps:", info["frame_rate"],
          "frames:", info["frame_count"])
    print("tags:", info["tag_count"])
    print("histograma:")
    for k, v in info["tag_histogram"].items():
        print("  %-32s %d" % (k, v))
