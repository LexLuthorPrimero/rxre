#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0
"""Actualiza evidence/claims-registry.json y .md
con RXRE-SWF-048 y corrige RXRE-SWF-033."""
import json

ROOT = "evidence"


def main():
    path = "%s/claims-registry.json" % ROOT
    d = json.load(open(path))
    claims = d["claims"]

    # corregir RXRE-SWF-033: los params de la decodificacion
    # anterior (buggy) estaban desalineados; ahora son
    # correctos en RXRE-SWF-048 / function-signatures.md
    for cl in claims:
        if cl["claim_id"] == "RXRE-SWF-033":
            cl["statement"] = (
                "DefineFunction(0x9B)=289, "
                "DefineFunction2(0x8E)=1053. Nombres "
                "recuperados: tick(196), createWound(8), "
                "arenaTick, enterFrameHandler, onPlayClick, "
                "initPlayButton, onMedalUnlocked, "
                "showNextUnlock, medalPopupEnterFrame, "
                "_apiConnect, _onConnected, "
                "forceAlwaysOnTop. Los PARAMS correctos "
                "(decodificacion corregida) y el modelo de "
                "datos estan en RXRE-SWF-048 / "
                "evidence/function-signatures.md.")
            cl["evidence"] = (
                "tools/avm1_disasm.py; decode_define_function"
                "(data, opcode) corregido; "
                "evidence/function-signatures.md")

    # anyadir RXRE-SWF-048
    claims.append({
        "claim_id": "RXRE-SWF-048",
        "taxonomy": "NEGATIVE_RESULT",
        "state": "PROVEN",
        "statement": (
            "Los cuerpos de DefineFunction(0x9B)/"
            "DefineFunction2(0x8E) son tokens nativos de "
            "2 bytes, NO secuencias de acciones AVM1: "
            "1342/1342 cuerpos=2B; 322 empiezan con "
            "opcode>=0x80 (imposible para accion larga "
            "en 2B); 306 no terminan en End; solo 839 son "
            "acciones estandar. tick()=token 0x44. La "
            "formula exacta de combate NO esta en los "
            "cuerpos. Las firmas revelan el modelo: "
            "combate (inDamage, inArmor, inWeapon, "
            "inAttacker, inRange, inHeadshot, inKnockback, "
            "inBlock, inKillShot), stats (inStr, inDex, "
            "inTac, inEnd, inLead, inAwr + 8 armas), "
            "fisica (inX, inY, inXSpeed, inYSpeed, inRot, "
            "inRotSpeed, inBounce, inFloor, inAlpha, "
            "inScale)."),
        "evidence": (
            "evidence/function-signatures.md; "
            "tools/extract_signatures.py; "
            "tools/register_signatures.py; op_0017eddb2b6c93e4"),
        "rxre_kind": "claim",
        "rxre_recorded_id": 228,
    })

    d["claims"] = claims
    with open(path, "w") as f:
        json.dump(d, f, indent=1, ensure_ascii=False)
    print("claims-registry.json: %d claims" % len(claims))

    # regenerar .md
    md = ["# Claims Registry — RXRE SWF Nexus Classic", ""]
    md.append("| Claim | Taxonomy | State | Statement | Evidence | rxre_id |")
    md.append("|---|---|---|---|---|---|")
    for cl in claims:
        md.append("| %s | %s | %s | %s | %s | %s |" % (
            cl["claim_id"], cl["taxonomy"], cl["state"],
            cl["statement"], cl["evidence"],
            cl.get("rxre_recorded_id", "")))
    md.append("")
    with open("%s/claims-registry.md" % ROOT, "w") as f:
        f.write("\n".join(md))
    print("claims-registry.md regenerated")


if __name__ == "__main__":
    main()
