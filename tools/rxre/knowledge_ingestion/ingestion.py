#!/usr/bin/env python3
"""RXRE-1642. Knowledge ingestion pipeline.

Implements end-to-end ingestion of historical findings into RXRE-1640 knowledge model.
"""
from __future__ import annotations

import hashlib
import json
import os
import sqlite3
from typing import Any, Dict, List, Optional, Tuple

from core import store as S
from .historical_parser import parse_finding_file, ParsedFinding
from .contracts import KnowledgeContract


def _hash_content(content: str) -> str:
    """Calculate SHA256 hash of content for change detection."""
    return hashlib.sha256(content.encode('utf-8')).hexdigest()


def _get_stored_content_hash(finding_number: int) -> Optional[str]:
    """Retrieve stored content hash for a finding number, if exists."""
    c = S.conectar()
    try:
        rows = c.execute(
            "SELECT limitations FROM findings WHERE op_id=?", 
            (f"historical_finding_{finding_number}",)
        ).fetchall()
        if rows and rows[0][0]:
            limitations = json.loads(rows[0][0])
            for lim in limitations:
                if isinstance(lim, str) and lim.startswith("content_hash:"):
                    return lim.split(":", 1)[1]
    except Exception:
        pass
    finally:
        c.close()
    return None


def _get_stored_knowledge_contract(finding_number: int) -> Optional[KnowledgeContract]:
    """Retrieve stored knowledge contract for a finding number, if exists."""
    c = S.conectar()
    try:
        op_id = f"historical_finding_{finding_number}"
        row = c.execute("SELECT finding_id FROM findings WHERE op_id=?", (op_id,)).fetchone()
        if row:
            actual_finding_id = row[0]
            f = S.recuperar_finding(c, actual_finding_id)
            if f and f.get("limitations"):
                # S.recuperar_finding already parses limitations as a list
                limitations = f["limitations"]
                for lim in limitations:
                    if isinstance(lim, str) and lim.startswith("knowledge_contract:"):
                        # Parse the knowledge contract JSON
                        try:
                            contract_dict = json.loads(lim.split(":", 1)[1])
                            return KnowledgeContract.from_dict(contract_dict)
                        except Exception:
                            pass
    except Exception:
        pass
    finally:
        c.close()
    return None


def _store_content_hash(finding_number: int, content_hash: str) -> None:
    """Store content hash for change detection by updating limitations."""
    c = S.conectar()
    try:
        # The op_id format is "historical_finding_<number>"
        op_id = f"historical_finding_{finding_number}"
        row = c.execute("SELECT finding_id FROM findings WHERE op_id=?", (op_id,)).fetchone()
        if row:
            actual_finding_id = row[0]
            f = S.recuperar_finding(c, actual_finding_id)
            if f:
                # S.recuperar_finding already parses limitations as a list
                limitations = f["limitations"] if f["limitations"] else []
                limitations = [lim for lim in limitations 
                              if not (isinstance(lim, str) and lim.startswith("content_hash:"))]
                limitations.append(f"content_hash:{content_hash}")
                c.execute(
                    "UPDATE findings SET limitations=? WHERE finding_id=?",
                    (json.dumps(limitations), actual_finding_id)
                )
                c.commit()
    except Exception:
        pass
    finally:
        c.close()


def ingest_historical_finding(
    filepath: str, 
    store_evidence_links: bool = False,
    dry_run: bool = False
) -> Dict[str, Any]:
    """
    Ingest a single historical finding into the RXRE knowledge store.
    
    Args:
        filepath: Path to the .md finding file
        store_evidence_links: If True, attempt to link to existing evidence/operations
        dry_run: If True, don't actually store, just return what would be stored
        
    Returns:
        Dict with status, finding_id (if stored), and metadata
    """
    # Parse the finding
    pf = parse_finding_file(filepath)
    if not pf:
        return {
            "status": "error",
            "motivo": f"Failed to parse {filepath}",
            "filepath": filepath
        }
    
    # Read file content for hash
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
    except Exception as e:
        return {
            "status": "error",
            "motivo": f"Failed to read {filepath}: {e}",
            "filepath": filepath
        }
    
    content_hash = _hash_content(content)
    
    # Check if we've already ingested this version
    stored_hash = _get_stored_content_hash(pf.number)
    if stored_hash == content_hash:
        # Retrieve stored knowledge contract from DB for return value
        stored_contract = _get_stored_knowledge_contract(pf.number)
        return {
            "status": "skipped",
            "motivo": "No changes since last ingestion",
            "finding_number": pf.number,
            "content_hash": content_hash,
            "contract": stored_contract.to_dict() if stored_contract else None
        }
    
    # Convert to finding dict for storage
    finding_dict = pf.to_finding_dict()
    
    # Enhance with additional metadata from parsing
    if pf.producer:
        # Ensure provenance has producer info
        if "producer" not in finding_dict["provenance"]:
            finding_dict["provenance"]["producer"] = pf.producer
    if pf.producer_location:
        finding_dict["provenance"]["source_location"] = pf.producer_location
    if pf.consumer:
        finding_dict["provenance"]["consumer"] = pf.consumer
    if pf.consumer_location:
        finding_dict["provenance"]["consumer_location"] = pf.consumer_location
    
    # Store content hash in limitations for change detection
    limitations = finding_dict["limitations"]
    if isinstance(limitations, str):
        limitations = json.loads(limitations) if limitations else []
    elif not isinstance(limitations, list):
        limitations = []
    limitations.append(f"content_hash:{content_hash}")
    # guardar_finding() will serialize limitations to JSON when inserting
    finding_dict["limitations"] = limitations
    
    # Extract knowledge contract metadata
    contract = _build_knowledge_contract(pf, content, content_hash)
    
    # Ensure evidence_ids is also a JSON string
    evidence_ids = finding_dict["evidence_ids"]
    if isinstance(evidence_ids, list):
        finding_dict["evidence_ids"] = json.dumps(evidence_ids)
    elif not isinstance(evidence_ids, str):
        finding_dict["evidence_ids"] = json.dumps([])
    
    # Try to link to existing evidence if requested
    if store_evidence_links:
        # Look for evidence references in the finding
        evidence_ids = _extract_evidence_references(content)
        if evidence_ids:
            # Validate that evidence_ids exist in database
            valid_evidence = _validate_evidence_ids(evidence_ids)
            # Serialize to JSON string for storage
            finding_dict["evidence_ids"] = json.dumps(valid_evidence)
    
    if dry_run:
        # Handle evidence_ids and limitations that might already be lists
        evidence_ids = finding_dict["evidence_ids"]
        if isinstance(evidence_ids, str):
            evidence_ids = json.loads(evidence_ids) if evidence_ids else []
        elif not isinstance(evidence_ids, list):
            evidence_ids = []
        
        limitations = finding_dict["limitations"]
        if isinstance(limitations, str):
            limitations = json.loads(limitations) if limitations else []
        elif not isinstance(limitations, list):
            limitations = []
        
        return {
            "status": "dry_run",
            "finding_number": pf.number,
            "title": pf.title,
            "claim": finding_dict["claim"][:200],
            "epistemic": finding_dict["epistemic"],
            "evidence_ids": evidence_ids,
            "provenance": finding_dict["provenance"],
            "limitations": limitations,
            "contract": contract.to_dict() if contract else None,
            "content_hash": content_hash
        }
    
    # Store in database
    c = S.conectar()
    try:
        result_id = S.guardar_finding(c, finding_dict)
        c.commit()
        
        status = "ok"
        finding_id = result_id
        motivo = None
        if result_id.startswith("COLISION:"):
            status = "collision"
            finding_id = result_id.split("COLISION:")[1]
            motivo = "finding already exists with same claim+evidence (content-based deduplication)"
        
        # Store content hash for future change detection
        _store_content_hash(pf.number, content_hash)
        
        # Store knowledge contract JSON
        if contract:
            _store_knowledge_contract(contract)
        
        return {
            "status": status,
            "finding_id": finding_id,
            "finding_number": pf.number,
            "title": pf.title,
            "claim": finding_dict["claim"][:200],
            "epistemic": finding_dict["epistemic"],
            # finding_dict values are already parsed (list/dict), no need to json.loads again
            "evidence_ids": finding_dict["evidence_ids"] if isinstance(
                finding_dict["evidence_ids"], list) else json.loads(finding_dict["evidence_ids"]),
            "provenance": finding_dict["provenance"] if isinstance(
                finding_dict["provenance"], dict) else json.loads(finding_dict["provenance"]),
            "limitations": finding_dict["limitations"] if isinstance(
                finding_dict["limitations"], list) else json.loads(finding_dict["limitations"]),
            "contract": contract.to_dict() if contract else None,
            "motivo": motivo,
            "content_hash": content_hash
        }
    except Exception as e:
        return {
            "status": "error",
            "motivo": f"Failed to store finding: {e}",
            "finding_number": pf.number
        }
    finally:
        c.close()


def _build_knowledge_contract(pf: ParsedFinding, content: str, content_hash: str) -> Optional[KnowledgeContract]:
    """Build a KnowledgeContract from a parsed historical finding."""
    if pf.number <= 0 or not pf.title:
        return None
    
    # Extract artifact and applicability from producer info
    producer = pf.producer or ''
    artifact = None
    tool = None
    tool_settings = None
    architecture = None
    
    # Detect artifact (tool name from producer)
    if 'reg_resolve' in producer:
        artifact = 'reg_resolve.py'
        tool = 'rizin' if 'rizin' in content.lower() else 'radare2'
        tool_settings = 'aaa; axtj' if 'axtj' in content.lower() else 'aa; axtj'
    elif 'rxre_cobertura' in producer:
        artifact = 'rxre_cobertura_gfx8.py'
        tool = 'rizin' if 'rizin' in content.lower() else 'radare2'
        tool_settings = 'aaa; axtj' if 'axtj' in content.lower() else 'aa; axtj'
    
    # Detect architecture from content
    if 'gfx8' in content.lower() or 'polaris12' in content.lower():
        architecture = 'GFX8'
    elif 'gfx9' in content.lower():
        architecture = 'GFX9'
    elif 'gfx10' in content.lower():
        architecture = 'GFX10'
    
    contract = KnowledgeContract(
        finding_id=f"historical_finding_{pf.number}",
        claim=pf.claim,
        epistemic=pf._infer_epistemic(),
        applicability={
            'artifact': artifact,
            'version': pf.date,
            'architecture': architecture,
            'tool': tool,
            'tool_settings': tool_settings,
            'scope': producer if producer else None,
        },
        source={
            'source_file': f'findings/{pf.number}.md',
            'source_hash': content_hash,
            'extraction_method': 'markdown_ingestion',
            'source_revision': 'historical',
        },
        provenance={
            'producer': pf.producer or 'historical_finding',
            'tool': tool,
            'tool_version': 'historical_rxre',
            'method': 'markdown_ingestion',
            'timestamp': pf.date or 'unknown',
            'source_finding_number': pf.number,
        },
        relations={
            'related_findings': pf.references if pf.references else [],
            'relation_types': [],
        },
        reproducibility={
            'commands': pf.code_blocks[:3],
            'parameters': [],
            'raw_outputs': [],
            'verification_procedure': 'Re-run reg_resolve.py or rxre_cobertura_gfx8.py with the indicated settings',
        },
    )
    
    return contract


def _store_knowledge_contract(contract: KnowledgeContract) -> None:
    """Store the knowledge contract JSON alongside the finding. Opens own connection."""
    c = S.conectar()
    try:
        op_id = contract.finding_id
        row = c.execute(
            "SELECT finding_id FROM findings WHERE op_id=?", 
            (op_id,)
        ).fetchone()
        if row:
            actual_finding_id = row[0]
            f = S.recuperar_finding(c, actual_finding_id)
            if f:
                # S.recuperar_finding already parses limitations as a list
                limitations = f["limitations"] if f["limitations"] else []
                limitations = [lim for lim in limitations 
                              if not (isinstance(lim, str) and lim.startswith("knowledge_contract:"))]
                limitations.append(f"knowledge_contract:{contract.to_json()}")
                c.execute(
                    "UPDATE findings SET limitations=? WHERE finding_id=?",
                    (json.dumps(limitations), actual_finding_id)
                )
                c.commit()
    except Exception:
        pass
    finally:
        c.close()


def _extract_evidence_references(content: str) -> List[str]:
    """Extract potential evidence references from finding content."""
    evidence_ids = []
    
    # Look for patterns like result_id, xref_, op_, etc.
    import re
    
    # Common RXRE result ID patterns
    patterns = [
        r'(?:result_id\s*[:=]\s*[\'"]?)([a-z]+[0-9a-f_]+)',
        r'([a-z]+_[0-9a-f]{8,})',  # Generic pattern like xref_..., op_...
        r'(ls_[0-9a-f]+)',         # ls_x1, ls_x2 patterns
        r'(cat_[0-9a-f]+)',        # cat_x1 pattern
        r'(bad_[0-9a-f]+)',        # bad_1 pattern
        r'(res_[0-9a-f]+)',        # res_001 pattern
        r'(cg_[0-9a-f]+)',         # cg_001 pattern
    ]
    
    for pattern in patterns:
        matches = re.findall(pattern, content, re.IGNORECASE)
        evidence_ids.extend(matches)
    
    # Deduplicate
    return list(set(evidence_ids))


def _validate_evidence_ids(evidence_ids: List[str]) -> List[str]:
    """Check which evidence_ids exist in the database."""
    if not evidence_ids:
        return []
    
    c = S.conectar()
    try:
        valid_ids = []
        for eid in evidence_ids:
            row = c.execute(
                "SELECT 1 FROM results WHERE result_id=?", 
                (eid,)
            ).fetchone()
            if row:
                valid_ids.append(eid)
        return valid_ids
    finally:
        c.close()


def ingest_historical_findings(
    directory: str,
    max_files: Optional[int] = None,
    store_evidence_links: bool = False,
    dry_run: bool = False,
    start_from: int = 0
) -> Dict[str, Any]:
    """
    Ingest all historical findings from a directory.
    
    Args:
        directory: Path to findings directory
        max_files: Maximum number of files to process (None for all)
        store_evidence_links: If True, attempt to link to existing evidence
        dry_run: If True, don't actually store
        start_from: Starting index (for resuming)
        
    Returns:
        Summary statistics
    """
    from .historical_parser import parse_finding_directory
    
    findings = parse_finding_directory(directory, max_files)
    if start_from > 0:
        findings = findings[start_from:]
    
    stats = {
        "total": len(findings),
        "processed": 0,
        "ok": 0,
        "collision": 0,
        "skipped": 0,
        "error": 0,
        "dry_run": 0,
        "findings": []
    }
    
    for pf in findings:
        # Convert ParsedFinding back to filepath for ingestion
        filepath = f"{directory}/{pf.number}.md"
        result = ingest_historical_finding(
            filepath, 
            store_evidence_links=store_evidence_links,
            dry_run=dry_run
        )
        
        stats["processed"] += 1
        status = result.get("status", "error")
        stats[status] = stats.get(status, 0) + 1
        
        stats["findings"].append({
            "number": pf.number,
            "title": pf.title[:100],
            "status": status,
            "finding_id": result.get("finding_id"),
            "motivo": result.get("motivo"),
            "contract": result.get("contract")
        })
        
        # Progress indicator
        if stats["processed"] % 50 == 0:
            print(f"Processed {stats['processed']}/{len(findings)} findings...")
    
    return stats


if __name__ == '__main__':
    # Test ingestion
    import sys
    if len(sys.argv) > 1:
        filepath = sys.argv[1]
        result = ingest_historical_finding(filepath, dry_run=True)
        print(json.dumps(result, indent=2))
    else:
        # Test with a few findings
        historical_dir = '/home/lucas/Escritorio/RX550-INVESTIGACION/findings'
        print("Testing ingestion of first 3 historical findings...")
        stats = ingest_historical_findings(
            historical_dir, 
            max_files=3, 
            dry_run=True
        )
        print(f"Ingestion test results: {stats['processed']} processed")
        for f in stats["findings"]:
            print(f"  {f['number']}: {f['title'][:50]} -> {f['status']}")