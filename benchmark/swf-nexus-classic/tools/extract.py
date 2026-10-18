#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0
"""Extractor de datos recuperables del SWF: simbolos exportados,
etiquetas de fotograma, texto de DefineEditText, metadatos de
sonido y vocabulario (strings ASCII).

PRODUCER: lee el inventario de tags de swfparse y extrae
campos con formato conocido.  No interpreta logica de juego.
"""
import json
import re
import struct
import sys


def read_str(buf, off):
    end = buf.find(b"\x00", off)
    if end < 0:
        end = len(buf)
    return buf[off:end].decode("latin1"), end + 1


def main(swf_json, body_path):
    d = json.load(open(swf_json))
    body = open(body_path, "rb").read()[8:]
    tags = d["tags"]

    out = {}

    # ExportAssets: u16 count, luego count x (u16 tag_id + str)
    export = []
    for t in tags:
        if t["name"] != "ExportAssets":
            continue
        p = body[t["offset"]:t["offset"] + t["length"]]
        count = struct.unpack("<H", p[0:2])[0]
        off = 2
        for _ in range(count):
            tag_id = struct.unpack("<H", p[off:off + 2])[0]
            off += 2
            name, off = read_str(p, off)
            export.append({"id": tag_id, "name": name})
    out["export_assets"] = export

    # FrameLabel: str (+opcional u16 frame)
    labels = []
    for t in tags:
        if t["name"] != "FrameLabel":
            continue
        p = body[t["offset"]:t["offset"] + t["length"]]
        name, off = read_str(p, 0)
        anchored = len(p) >= off + 2
        labels.append({"name": name, "anchored": anchored,
                       "tag_offset": t["offset"]})
    out["frame_labels"] = labels

    # DefineEditText: nombre y texto inicial (mejor esfuerzo)
    edit_texts = []
    for t in tags:
        if t["name"] != "DefineEditText":
            continue
        p = body[t["offset"]:t["offset"] + t["length"]]
        # u16 id, luego RECT, luego flags... el texto inicial viene
        # marcado por un bit; extraemos todas las cadenas >=3 chars.
        strs = re.findall(rb"[\x20-\x7e]{3,}", p)
        edit_texts.append({
            "tag_offset": t["offset"],
            "length": t["length"],
            "strings": [s.decode("latin1") for s in strs],
        })
    out["define_edit_text"] = edit_texts

    # DefineSound: u16 id, u8 format flags, u32 sample count, ...
    sounds = []
    for t in tags:
        if t["name"] != "DefineSound":
            continue
        p = body[t["offset"]:t["offset"] + t["length"]]
        if len(p) < 7:
            continue
        sid = struct.unpack("<H", p[0:2])[0]
        fmt = p[2]
        fmt_flags = fmt & 0x0F
        rate = (fmt >> 4) & 0x03
        size = (fmt >> 6) & 0x01
        stype = (fmt >> 7) & 0x01
        samples = struct.unpack("<I", p[3:7])[0]
        sounds.append({"id": sid, "format": fmt_flags, "rate": rate,
                       "size": size, "type": stype,
                       "samples": samples, "tag_length": t["length"]})
    out["define_sound"] = sounds

    # Vocabulario: strings ASCII >= 4 en todo el cuerpo
    vocab = sorted(set(s.decode("latin1")
                       for s in re.findall(rb"[\x20-\x7e]{4,}", body)))
    out["vocab_count"] = len(vocab)
    out["vocab"] = vocab

    # Metadatos XMP (payload del SymbolClass)
    for t in tags:
        if t["name"] == "SymbolClass":
            out["xmp"] = body[t["offset"]:t["offset"] + t["length"]].decode(
                "latin1")

    return out


if __name__ == "__main__":
    res = main(sys.argv[1], sys.argv[2])
    json.dump(res, open(sys.argv[3], "w", encoding="utf-8"),
              indent=1, ensure_ascii=False)
    print("ExportAssets:", len(res["export_assets"]))
    print("FrameLabels:", len(res["frame_labels"]))
    print("DefineEditText:", len(res["define_edit_text"]))
    print("DefineSound:", len(res["define_sound"]))
    print("vocab strings:", res["vocab_count"])
    print("XMP:", len(res.get("xmp", "")))
