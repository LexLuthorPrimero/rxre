#!/usr/bin/env python3
"""RXRE-1642. Parser de findings históricos.

Convierte los archivos .md de `06-INGENIERIA-INVERSA/findings/` al modelo
de finding de RXRE-1640 (claim, epistemic, evidence_ids, provenance, limitations).

PROVENANCE: Creado 2026-10-12 para RXRE-1642.
"""
from __future__ import annotations

import json
import os
import re
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

# Patrones regex para extraer información de los findings históricos
HEADER_PATTERN = re.compile(
    r'^# FINDING\s+(\d+)\s*[—-]\s*(.+)$',
    re.MULTILINE
)

DATE_PATTERN = re.compile(
    r'^\*\*Fecha:\*\*\s*(.+)$',
    re.MULTILINE
)

STATE_PATTERN = re.compile(
    r'^\*\*Estado de la misión:\*\*\s*(.+)$',
    re.MULTILINE
)

BRANCH_PATTERN = re.compile(
    r'^\*\*Rama:\*\*\s*(.+)$',
    re.MULTILINE
)

QUESTION_PATTERN = re.compile(
    r'>\s*\*\*PREGUNTA\*\*\s*>\s*(.+?)\s*(?:\n|$)',
    re.DOTALL
)

ANSWER_PATTERN = re.compile(
    r'>\s*\*\*Respuesta honesta.*?:\*\*\s*>\s*(.+?)\s*(?:\n\s*>\s*\*\*|\n\s*##|\n\s*---|\Z)',
    re.DOTALL
)

# Productor/consumidor table pattern (tabla markdown)
PRODUCER_TABLE_PATTERN = re.compile(
    r'\|\s*\*\*Productor\*\*\s*\|\s*(.+?)\s*\|',
    re.MULTILINE | re.DOTALL
)

CONSUMER_TABLE_PATTERN = re.compile(
    r'\|\s*\*\*Consumidor\*\*\s*\|\s*(.+?)\s*\|',
    re.MULTILINE | re.DOTALL
)

LOCATION_PATTERN = re.compile(
    r'\|\s*\*\*Ubicación\*\*\s*\|\s*(.+?)\s*\|',
    re.MULTILINE | re.DOTALL
)

# Productor/consumidor en formato lista (### Productor)
PRODUCER_LIST_PATTERN = re.compile(
    r'###\s*Productor\s*\n(.+?)(?:\n###|\n##|\n---|\Z)',
    re.DOTALL | re.IGNORECASE
)

CONSUMER_LIST_PATTERN = re.compile(
    r'###\s*Consumidor\s*\n(.+?)(?:\n###|\n##|\n---|\Z)',
    re.DOTALL | re.IGNORECASE
)

# Limitaciones - buscar sección de limitaciones
LIMITATIONS_PATTERN = re.compile(
    r'(?:##|###)\s*Limitaciones?\s*\n(.+?)(?:\n##|\n###|\n---|\Z)',
    re.DOTALL | re.IGNORECASE
)

# Impacto / Conclusión
IMPACT_PATTERN = re.compile(
    r'(?:##|###)\s*Impacto\s*\n(.+?)(?:\n##|\n###|\n---|\Z)',
    re.DOTALL | re.IGNORECASE
)

CONCLUSION_PATTERN = re.compile(
    r'(?:##|###)\s*Conclusi[oó]n\s*\n(.+?)(?:\n##|\n###|\n---|\Z)',
    re.DOTALL | re.IGNORECASE
)

# Reparación / Solución
REPAIR_PATTERN = re.compile(
    r'(?:##|###)\s*Reparaci[oó]n\s*\n(.+?)(?:\n##|\n###|\n---|\Z)',
    re.DOTALL | re.IGNORECASE
)

# Fecha en formato alternativo
DATE_ALT_PATTERN = re.compile(
    r'^\*\*Fecha:\*\*\s*(.+)$',
    re.MULTILINE
)

# Referencias a otros findings
FINDING_REF_PATTERN = re.compile(
    r'FINDING\s+(\d+)',
    re.IGNORECASE
)

# Código o texto técnico
CODE_BLOCK_PATTERN = re.compile(
    r'```[a-z]*\n(.+?)\n```',
    re.DOTALL
)

# Headers de secciones
SECTION_HEADER_PATTERN = re.compile(
    r'^##+\s*(.+)$',
    re.MULTILINE
)


@dataclass
class ParsedFinding:
    """Finding histórico parseado, listo para ingestión."""
    number: int
    title: str
    claim: str
    date: Optional[str] = None
    state: Optional[str] = None
    branch: Optional[str] = None
    question: Optional[str] = None
    answer: Optional[str] = None
    producer: Optional[str] = None
    producer_location: Optional[str] = None
    consumer: Optional[str] = None
    consumer_location: Optional[str] = None
    limitations: List[str] = field(default_factory=list)
    impact: Optional[str] = None
    conclusion: Optional[str] = None
    repair: Optional[str] = None
    references: List[int] = field(default_factory=list)
    code_blocks: List[str] = field(default_factory=list)
    raw_sections: Dict[str, str] = field(default_factory=dict)
    
    # Campos derivados para ingestion
    finding_id: Optional[str] = None  # Se asigna al guardar
    evidence_ids: List[str] = field(default_factory=list)  # Se mapean si existen
    
    def to_finding_dict(self) -> Dict[str, Any]:
        """Convierte a dict compatible con guardar_finding()."""
        # Construir claim principal: título + respuesta/respuesta principal
        claim_parts = [self.title]
        if self.answer:
            claim_parts.append(self.answer[:500])  # Primeros 500 chars de la respuesta
        elif self.conclusion:
            claim_parts.append(self.conclusion[:500])
        claim = '. '.join(claim_parts)
        
        # Provenance: extraer info del productor
        provenance = {
            'producer': self.producer or 'historical_finding',
            'tool_version': 'historical_rxre',
            'method': 'markdown_ingestion',
            'timestamp': self.date or 'unknown',
            'source_finding_number': self.number,
            'source_location': self.producer_location,
            'consumer': self.consumer,
            'consumer_location': self.consumer_location,
        }
        
        # Limitaciones: combinar explícitas + inferidas
        limitations = list(self.limitations)
        if self.producer_location and 'tools/' in self.producer_location:
            limitations.append(f'productor localizado en {self.producer_location}')
        if self.impact:
            limitations.append(f'impacto: {self.impact[:200]}')
        
        return {
            'claim': claim,
            'epistemic': self._infer_epistemic(),
            'evidence_ids': self.evidence_ids,
            'provenance': provenance,
            'limitations': limitations,
            'op_id': f'historical_finding_{self.number}',
        }
    
    def _infer_epistemic(self) -> str:
        """Infere estado epistemico basado en contenido del finding histórico."""
        if self.answer and ('demostrado' in self.answer.lower() or 'verificado' in self.answer.lower()):
            return 'PROVEN'
        elif self.answer and ('parcial' in self.answer.lower() or 'probado en parte' in self.answer.lower()):
            return 'PARTIAL'
        elif self.answer and ('no existe' in self.answer.lower() or 'probado que no' in self.answer.lower()):
            return 'PROVEN_ABSENT'
        elif self.question and 'diferido' in self.question.lower():
            return 'DEFERRED'
        else:
            return 'NOT_DETERMINED'


def parse_finding_file(filepath: str) -> Optional[ParsedFinding]:
    """Parsea un archivo .md de finding histórico."""
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
    except Exception as e:
        print(f"Error leyendo {filepath}: {e}")
        return None
    
    # Extraer número y título del header
    header_match = HEADER_PATTERN.search(content)
    if not header_match:
        return None
    
    number = int(header_match.group(1))
    title = header_match.group(2).strip()
    
    pf = ParsedFinding(number=number, title=title, claim=title)
    
    # Extraer metadatos básicos
    for pattern, attr in [
        (DATE_PATTERN, 'date'),
        (STATE_PATTERN, 'state'),
        (BRANCH_PATTERN, 'branch'),
    ]:
        match = pattern.search(content)
        if match:
            setattr(pf, attr, match.group(1).strip())
    
    # Extraer pregunta y respuesta
    q_match = QUESTION_PATTERN.search(content)
    if q_match:
        pf.question = q_match.group(1).strip()
    
    a_match = ANSWER_PATTERN.search(content)
    if a_match:
        pf.answer = a_match.group(1).strip()
    
    # Extraer productor/consumidor - formato tabla (finding 1589)
    prod_match = PRODUCER_TABLE_PATTERN.search(content)
    if prod_match:
        pf.producer = prod_match.group(1).strip()
    
    loc_match = LOCATION_PATTERN.search(content)
    if loc_match:
        pf.producer_location = loc_match.group(1).strip()
    
    cons_match = CONSUMER_TABLE_PATTERN.search(content)
    if cons_match:
        pf.consumer = cons_match.group(1).strip()
    
    # Formato alternativo: listas (finding 1590)
    if not pf.producer:
        prod_list_match = PRODUCER_LIST_PATTERN.search(content)
        if prod_list_match:
            pf.producer = prod_list_match.group(1).strip()[:500]
    
    if not pf.consumer:
        cons_list_match = CONSUMER_LIST_PATTERN.search(content)
        if cons_list_match:
            pf.consumer = cons_list_match.group(1).strip()[:500]
    
    # Extraer limitaciones, impacto, conclusión, reparación
    for pattern, attr in [
        (LIMITATIONS_PATTERN, 'limitations'),
        (IMPACT_PATTERN, 'impact'),
        (CONCLUSION_PATTERN, 'conclusion'),
        (REPAIR_PATTERN, 'repair'),
    ]:
        match = pattern.search(content)
        if match:
            text = match.group(1).strip()
            if attr == 'limitations':
                # Parsear lista de limitaciones (líneas que empiezan con - o *)
                for line in text.split('\n'):
                    line = line.strip()
                    if line and (line.startswith('-') or line.startswith('*')):
                        pf.limitations.append(line[1:].strip())
                    elif line and not line.startswith('#'):
                        pf.limitations.append(line)
            else:
                setattr(pf, attr, text[:1000])  # Limitar longitud
    
    # Extraer referencias a otros findings
    pf.references = [int(m) for m in FINDING_REF_PATTERN.findall(content)]
    
    # Extraer bloques de código
    pf.code_blocks = [m.strip() for m in CODE_BLOCK_PATTERN.findall(content)]
    
    # Extraer todas las secciones para referencia
    sections = SECTION_HEADER_PATTERN.findall(content)
    for sec in sections:
        start = content.find(f'## {sec}') if f'## {sec}' in content else content.find(f'### {sec}')
        if start >= 0:
            # Buscar siguiente header o fin
            next_sec = SECTION_HEADER_PATTERN.search(content, start + 1)
            end = next_sec.start() if next_sec else len(content)
            pf.raw_sections[sec] = content[start:end].strip()
    
    return pf


def parse_finding_directory(directory: str, max_files: Optional[int] = None) -> List[ParsedFinding]:
    """Parsea todos los archivos .md de findings en un directorio."""
    findings = []
    files = sorted(
        [f for f in os.listdir(directory) if f.endswith('.md')],
        key=lambda x: int(x.split('.')[0]) if x.split('.')[0].isdigit() else 0
    )
    
    if max_files:
        files = files[:max_files]
    
    for filename in files:
        filepath = os.path.join(directory, filename)
        pf = parse_finding_file(filepath)
        if pf:
            findings.append(pf)
    
    return findings


def extract_producer_info(content: str) -> Dict[str, Optional[str]]:
    """Extrae información del productor desde contenido markdown."""
    info = {'producer': None, 'location': None, 'method': None}
    
    # Buscar tabla de productor/consumidor
    table_match = re.search(
        r'\|\s*Rol\s*\|\s*Componente\s*\|\s*Ubicación\s*\|.+?\n(.+?)(?:\n\n|\n##|\n---|\Z)',
        content,
        re.DOTALL | re.IGNORECASE
    )
    if table_match:
        table_content = table_match.group(1)
        # Parsear filas de la tabla
        for line in table_content.split('\n'):
            if '|' in line and 'Productor' in line:
                parts = [p.strip() for p in line.split('|')]
                if len(parts) >= 4:
                    info['producer'] = parts[2]
                    info['location'] = parts[3]
            elif '|' in line and 'Consumidor' in line:
                parts = [p.strip() for p in line.split('|')]
                if len(parts) >= 4:
                    info['consumer'] = parts[2]
                    info['consumer_location'] = parts[3]
    
    return info


def classify_finding_type(claim: str, content: str) -> str:
    """Clasifica el tipo de finding basado en su contenido."""
    claim_lower = claim.lower()
    content_lower = content.lower()
    
    if any(kw in claim_lower for kw in ['defecto', 'bug', 'error', 'fallo', 'incorrecto']):
        return 'DEFECT'
    elif any(kw in claim_lower for kw in ['conflicto', 'conflic', 'contradiccion']):
        return 'CONTRADICTION'
    elif any(kw in claim_lower for kw in ['reparacion', 'reparación', 'fix', 'solucion']):
        return 'REPAIR'
    elif any(kw in claim_lower for kw in ['medicion', 'medición', 'benchmark', 'rendimiento']):
        return 'MEASUREMENT'
    elif any(kw in claim_lower for kw in ['hipotesis', 'hipótesis', 'teoria', 'teoría']):
        return 'HYPOTHESIS'
    elif 'negativo' in content_lower or 'no se encontro' in content_lower:
        return 'NEGATIVE_RESULT'
    else:
        return 'TECHNICAL_ASSERTION'


if __name__ == '__main__':
    # Auto-test
    import sys
    if len(sys.argv) > 1:
        test_file = sys.argv[1]
        if os.path.exists(test_file):
            pf = parse_finding_file(test_file)
            if pf:
                print(f"Finding {pf.number}: {pf.title}")
                print(f"  Claim: {pf.claim[:200]}...")
                print(f"  Date: {pf.date}")
                print(f"  Producer: {pf.producer}")
                print(f"  Location: {pf.producer_location}")
                print(f"  Limitations: {pf.limitations}")
                print(f"  References: {pf.references}")
                print(f"  Epistemic inferred: {pf._infer_epistemic()}")
                print(f"  Type: {classify_finding_type(pf.title, pf.answer or '')}")
            else:
                print(f"Failed to parse {test_file}")
        else:
            print(f"File not found: {test_file}")
    else:
        # Test with first few historical findings
        historical_dir = '/home/lucas/Escritorio/RX550-INVESTIGACION/findings'
        if os.path.exists(historical_dir):
            findings = parse_finding_directory(historical_dir, max_files=5)
            print(f"Parsed {len(findings)} findings")
            for pf in findings:
                print(f"  {pf.number}: {pf.title[:80]} (epistemic={pf._infer_epistemic()})")