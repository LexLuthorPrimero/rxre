#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0
"""Registra las claims recuperadas del SWF via op:record de
RXRE y escribe el registro de claims (JSON + Markdown).

Cada claim se registra con kind en la lista cerrada de RXRE
(hypothesis|claim|note|next_action|frontier). La taxonomia
epistemica (FACT/MEASUREMENT/...) va en el texto.
"""
import json
import subprocess
import sys

MACHINE = ["python3", "-B", "tools/rxre/api/machine.py"]
REPO = "/home/lucas/Escritorio/rxre"
SESSION = "swf-nexus"
TARGET = "Madness Project Nexus Classic.swf"

# (id, taxonomia, estado, claim, kind_rxre, evidencia)
CLAIMS = [
    ("RXRE-SWF-001", "FACT", "PROVEN",
     "SWF con firma CWS (zlib-comprimido), version 10, "
     "longitud 15612129 bytes, SHA-256 "
     "44584a02d85a883384bad34617eb800d79301a8daeabf20244f6b75755ff9342.",
     "claim", "raw/original.swf; sha256sum"),
    ("RXRE-SWF-002", "FACT", "PROVEN",
     "SWF descomprimido (FWS) = 20491352 bytes, SHA-256 "
     "bb0a9475eb9d0a4cc882a7d6f5d38cb8679b6157a04489fc404b289d9cda1ef2.",
     "claim", "raw/uncompressed.swf; swfparse.py"),
    ("RXRE-SWF-003", "FACT", "PROVEN",
     "Bytecode AS2/AVM1, NO AS3: DoABC=0, DoAction=6, DoInitAction=69. "
     "FileAttributes presente.",
     "claim", "raw/swf-structure.json histograma de tags"),
    ("RXRE-SWF-004", "MEASUREMENT", "PROVEN",
     "Escenario 850x530 px (RECT 0,17000,0,10600 twips), 30 fps, "
     "30 fotogramas (FrameCount=30 == ShowFrame=30).",
     "claim", "raw/swf-structure.json"),
    ("RXRE-SWF-005", "FACT", "PROVEN",
     "Creado con Adobe Flash CS4 Professional; CreateDate "
     "2012-05-10T21:02:22-04:00; ModifyDate 2014-09-09T01:10:29-04:00.",
     "claim", "XMP en payload de tag SymbolClass(77)"),
    ("RXRE-SWF-006", "FACT", "PROVEN",
     "520 assets exportados (ExportAssets), incluyendo 26 clases Madness* "
     "(MadnessAI, MadnessCharacter, MadnessLevel, MadnessSpawner, "
     "MadnessDoors, MadnessObstacle, MadnessStoreHire, MadnessTeamSetup, "
     "MadnessWorldMap, MadnessSaveData, MadnessMedals, ...).",
     "claim", "raw/extracted.json export_assets"),
    ("RXRE-SWF-007", "FACT", "PROVEN",
     "4 etiquetas de fotograma: preoader, sound, menu, gameScreen "
     "(estructura de escena: preloader -> sonido -> menu -> juego).",
     "claim", "raw/extracted.json frame_labels"),
    ("RXRE-SWF-008", "MEASUREMENT", "PROVEN",
     "137 DefineSound, ~29257171 samples (~22 min a 22kHz), mayoritariamente "
     "formato MP3 (132), mas Nellymoser (3) y ADPCM (2); todos mono.",
     "claim", "raw/extracted.json define_sound"),
    ("RXRE-SWF-009", "DERIVATION", "CORROBORATED",
     "El juego es un shooter tactico con sistema TAC-BAR (barra de evasion), "
     "armaduras light/medium/heavy, clases de arma (pistol/SMG/rifle/"
     "shotgun/melee/unarmed/thrown), perks, y sistema de tienda/contratacion. "
     "Las descripciones de perks y armas estan recuperadas; los valores "
     "numericos de balance NO lo estan (ver RXRE-SWF-015).",
     "hypothesis", "raw/avm1-vocab.json"),
    ("RXRE-SWF-010", "FACT", "PROVEN",
     "Personajes referenciados: Sanford, Deimos, Hank, Dr. Christoff.",
     "claim", "raw/avm1-vocab.json"),
    ("RXRE-SWF-011", "FACT", "PROVEN",
     "Misiones/ubicaciones referenciadas: Nexus Stronghold, Armory, "
     "Recon Hut/Com-Tower, Barracks, Communication Tower.",
     "claim", "raw/avm1-vocab.json"),
    ("RXRE-SWF-012", "MEASUREMENT", "PROVEN",
     "Formato AVM1 ConstantPool (estandar): 0x88, "
     "u16 ActionLength, u16 Count, luego Count "
     "cadenas NUL-terminadas. El Count es el "
     "SEGUNDO u16; el primero es ActionLength "
     "(mal etiquetado 'campoA' en avm1_strings.py). "
     "El ConstantPool ES accion autonoma real: "
     "456 acciones 0x88 standalone (walk_actions), "
     "456 scripts con pool valido, 9801 cadenas. "
     "DoAction[0] count=23 (rightClick, ContextMenu, "
     "hideBuiltInItems, _root, menu, MadnessWorldMap, "
     "world_map, Object...).",
     "claim", "tools/avm1_disasm.py walk_actions; 456 acciones 0x88"),
    ("RXRE-SWF-023", "HYPOTHESIS", "OPEN",
     "Los multiplicadores de combate float32, "
     "concentrados en 15 scripts, forman 2 grupos "
     "de pool compartido. Grupo A (combate general: "
     "tac, damage, health, melee, headshot, block, "
     "zombie) es dominante en 1.75(74), luego "
     "1.9125(33), 1.925(25), 1.9375(18). Grupo B "
     "(point-blank/personajes: blank, sanford, "
     "deimos, christoff, pellet, evade, finisher, "
     "doubletime, second, carry) usa 1.9125(23-28), "
     "1.925(15-22), 1.9375(5) y NO contiene 1.75. "
     "Evidencia de co-ocurrencia (HYPOTHESIS), NO "
     "prueba de flujo de control: el mapeo exacto "
     "constante->mecanica sigue NOT_DETERMINED.",
     "hypothesis", "tools/avm1_disasm.py; correlacion pool->multiplicador"),
    ("RXRE-SWF-024", "MEASUREMENT", "PROVEN",
     "Las acciones CORTAS (0x00-0x33) son "
     "AVM1 estandar: 0x0B Restar(711), 0x0C "
     "Multiplicar(669), 0x0D Dividir(455), "
     "0x12 Not(6178), 0x17 Pop(10082), 0x1C "
     "GetVariable(7728), 0x1D SetVariable(316), "
     "0x07 Stop(521), 0x06 Play(24). Frecuencias "
     "sensibles (Pop/GetVariable tras Push). Las "
     "acciones LARGAS (>=0x80) son la parte NO "
     "estandar (Push=0x96).",
     "claim", "tools/avm1_disasm.py; histograma de opcodes"),
    ("RXRE-SWF-025", "NEGATIVE_RESULT", "PROVEN_ABSENT",
     "Las constantes de combate NO se asignan "
     "via SetVariable a variables con nombre. "
     "El trace de pila de SetVariable(0x1D) "
     "resuelve 307 asignaciones, todas de "
     "framework/UI: onEnterFrame(275), "
     "cacheAsBitmap(4), myPhase(4), _redirect(2), "
     "mouseChildren(2), _listItems(2), i(2), "
     "_loading(2), debugMode(1)... Ninguna "
     "variable de combate. Las constantes de "
     "combate fluyen a llamadas a funcion/metodo "
     "(0x4E=24316, 0x4F=8359, 0x52=7699, "
     "0x9D=5443, 0x49=2497) cuyos opcodes NO "
     "estan identificados (sin tabla de "
     "referencia para este dialecto no estandar). "
     "Mapeo constante->mecanica: NOT_DETERMINED "
     "(bloqueado por tabla de opcodes de "
     "llamadas).",
     "note", "tools/avm1_disasm.py; simulador de pila SetVariable"),
    ("RXRE-SWF-026", "MEASUREMENT", "CORROBORATED",
     "La accion 0x4E se comporta como SetMember "
     "(object[key]=value). Trace de pila: 100 pares "
     "(clave,valor), TODOS enteros pequenos (0-9: "
     "indices, flags, valores de enum). Claves "
     "estructurales de combate: wound(=1/2), "
     "item(=0/2/9), icon(=2/3/7), level(=3/8/9), "
     "stat(=3/4), skill(=3/4), storeIcon(=2/3/4/5), "
     "portrait(=0/4), storyProgressWorld(=1/2), "
     "PHactivator/PHdoor/PHobstacle/PHspawner(=7), "
     "perkSidearm1(=0), swapmelee(=0). Corrobora "
     "0x4E=SetMember (claves y valores con sentido).",
     "claim", "tools/avm1_trace.py; simulador de pila 0x4E"),
    ("RXRE-SWF-027", "NEGATIVE_RESULT", "PROVEN_ABSENT",
     "Los multiplicadores de combate (1.75, 1.9125, "
     "1.925, 1.9375) NO aparecen en los pares de "
     "0x4E SetMember (todos los valores son enteros "
     "0-9). Fluyen a los opcodes de llamada "
     "0x4F(8359), 0x52(7699), 0x9D(5443), 0x49(2497) "
     "cuya semantica NO esta identificada (sin tabla "
     "de referencia para este dialecto no estandar). "
     "Mapeo constante->mecanica: NOT_DETERMINED "
     "(bloqueado por tabla de opcodes de llamada). "
     "Frontiera SATURADA: analisis estatico agotado.",
     "note", "tools/avm1_trace.py; trace 0x4E + histograma"),
    ("RXRE-SWF-013", "NEGATIVE_RESULT", "PROVEN_ABSENT",
     "RXRE NO puede ingerir el binario SWF. search/evidence buscan el corpus "
     "del kernel (NOT_FOUND para identificadores del SWF); register interpreta "
     "el path como nombre de registro ASIC (PROVEN_ABSENT_EN_ASIC_REG). "
     "Ruta verificada mas estrecha: extraer con herramientas externas y "
     "registrar via op:record (kind cerrado: hypothesis|claim|note|"
     "next_action|frontier).",
     "claim", "tools/rxre/cli.py ops; respuestas search/register/evidence"),
    ("RXRE-SWF-014", "NEGATIVE_RESULT", "PROVEN_ABSENT",
     "No hay runtime Flash disponible (no ruffle, no swftools, no flasm; "
     "wine sin plugin Flash). La validacion diferencial contra el original "
     "NO es posible; se usa evidencia estatica independiente.",
     "claim", "inventario de herramientas (seccion 1 del benchmark)"),
    ("RXRE-SWF-015", "NEGATIVE_RESULT", "PARTIAL",
     "Constantes numericas de balance AVM1: VALORES RECUPERADOS "
     "(OBSERVED) pero asignacion semantica NO. Se extrajeron 17033 "
     "Integer, 5435 pares float32+uint32 (tipo 6), 8873 Const16, "
     "46125 Lookup, 2918 String de 54187 acciones Push(0x96). Los "
     "valores estan OBSERVED; cual constante corresponde a damage/range/"
     "fire-rate sigue NOT_DETERMINED (requiere flujo de control).",
     "note", "tools/avm1_disasm.py; raw/avm1-constants.json"),
    ("RXRE-SWF-019", "MEASUREMENT", "PROVEN",
     "Regla de longitud de accion AVM1 verificada: ActionCode u8; si "
     "code>=0x80 sigue u16 ActionLength + Data[ActionLength]; si "
     "code<0x80 es corta (1 byte, sin longitud ni datos). Los 1749 "
     "scripts parsean limpio a End(0x00) sin desbordamiento (100%).",
     "claim", "tools/avm1_disasm.py walk_actions; parse 100% limpio"),
    ("RXRE-SWF-020", "FACT", "PROVEN",
     "La accion Push en este SWF es el opcode 0x96, NO el estandar "
     "0x9C. 0x96 es la accion mas comun (11347 en el script mayor; "
     "54187 con datos en total); 0x9C aparece 0 veces como codigo de "
     "accion. Los datos de 0x96 parsean como constantes Push tipadas. "
     "NO ESTANDAR: este SWF usa 0x96 para Push.",
     "claim", "tools/avm1_disasm.py; histograma de opcodes"),
    ("RXRE-SWF-021", "FACT", "PROVEN",
     "Tipo 9 de Push = Const16 (indice de pool de 2 bytes, rango "
     "256-907, confirmando Lookup16 para pools >256 entradas). Con "
     "tipo9=2 bytes, las 54187 acciones Push parsean 100% limpio. "
     "NO ESTANDAR: el estandar solo tiene tipo 8 Lookup (1 byte).",
     "claim", "tools/avm1_disasm.py parse_push_data; rango 256-907"),
    ("RXRE-SWF-022", "NEGATIVE_RESULT", "REFUTED",
     "Tipo 6 de Push NO es Double (refutado). Los 8 bytes NO decodifican "
     "como double en ningun orden de bytes (1.75 como double seria "
     "3F FC 00 00 00 00 00 00, no 00 00 e0 3f ...). Estructura real: "
     "8 bytes = float32_LE[0:4] + uint32_LE[4:8]. El float32 es un "
     "multiplicador de juego (rango 1.45-2.06, mas comun 1.75; "
     "tambien negativos -1.5..-2.4 y valores grandes 3.0-1031.5). "
     "El uint32 para pares multiplicador es un conjunto pequeno "
     "{0x00000000,0x33333333,0x66666666,0x9999999a,0xcccccccd} = "
     "fraccion fija 0.32 {0.0,0.2,0.4,0.6,0.8}.",
     "note", "tools/avm1_disasm.py; volcado de bytes raw tipo 6"),
    ("RXRE-SWF-016", "HYPOTHESIS", "OPEN",
     "El tag SymbolClass(77) contiene los metadatos XMP (ubicacion no "
     "estandar; normalmente el tag Metadata(78) los contiene).",
     "hypothesis", "payload de SymbolClass empieza con <rdf:RDF"),
    ("RXRE-SWF-017", "HYPOTHESIS", "OPEN",
     "El tag 24 (31 B) contiene la cadena $1$Xg$7P2RjvftDquRuFo.lqa8W/ "
     "(formato MD5-crypt); proposito desconocido.",
     "hypothesis", "raw/swf-structure.json tag Unknown(24)"),
    ("RXRE-SWF-018", "HYPOTHESIS", "OPEN",
     "Los DoInitAction posteriores a [0] (68 scripts) NO empiezan con "
     "ConstantPool: empiezan con codigos de accion 0xC4-0xD9, 0x90-0x9C, "
     "0xA0-0xA9, 0xE0-0xE1. Si son definiciones de clase que referencian "
     "el pool de [0] o tienen pools propios mas adelante es NOT_DETERMINED "
     "(60 de 75 scripts tienen pool localizable).",
     "hypothesis", "tools/avm1_strings.py"),
]


def record(text, kind):
    req = {"op": "record", "kind": kind, "text": text,
           "status": "OPEN", "session": SESSION, "target": TARGET}
    p = subprocess.run(MACHINE, input=json.dumps(req) + "\n",
                       capture_output=True, text=True, cwd=REPO)
    try:
        return json.loads(p.stdout.strip().splitlines()[-1])
    except Exception:
        return {"status": "error", "raw": p.stdout, "stderr": p.stderr}


def main():
    resp = []
    for cid, tax, st, claim, kind, ev in CLAIMS:
        text = "[%s/%s] %s | EVIDENCIA: %s" % (cid, tax, claim, ev)
        r = record(text, kind)
        resp.append({"claim_id": cid, "taxonomy": tax, "state": st,
                     "statement": claim, "evidence": ev,
                     "rxre_kind": kind, "rxre_response": r})
        print("%-14s %-16s -> rxre_status=%s" %
              (cid, tax, r.get("status")))

    with open("queries/record-responses.jsonl", "w") as f:
        for row in resp:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")

    registry = {
        "artifact": TARGET,
        "session": SESSION,
        "claims": [{
            "claim_id": r["claim_id"],
            "taxonomy": r["taxonomy"],
            "state": r["state"],
            "statement": r["statement"],
            "evidence": r["evidence"],
            "rxre_kind": r["rxre_kind"],
            "rxre_recorded_id":
                (r["rxre_response"].get("recorded") or {}).get("id"),
        } for r in resp],
    }
    with open("evidence/claims-registry.json", "w") as f:
        json.dump(registry, f, indent=1, ensure_ascii=False)

    with open("evidence/claims-registry.md", "w") as f:
        f.write("# Registro de Claims — Madness Project Nexus Classic.swf\n\n")
        f.write("Artefacto: `%s`\n\n" % TARGET)
        f.write("Sesion RXRE: `%s`\n\n" % SESSION)
        f.write("| Claim | Taxonomia | Estado | Enunciado | Evidencia |\n")
        f.write("|---|---|---|---|---|\n")
        for r in resp:
            f.write("| %s | %s | %s | %s | %s |\n" % (
                r["claim_id"], r["taxonomy"], r["state"],
                r["statement"].replace("|", "\\|"),
                r["evidence"].replace("|", "\\|")))
    print("\nclaims registradas:", len(resp))


if __name__ == "__main__":
    main()
