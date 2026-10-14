#!/usr/bin/env python3
"""RXRE-1642. Knowledge contract for reuse engine.

Defines the structured metadata needed for the knowledge reuse engine to
efficiently search, retrieve, and apply findings.
"""

from typing import Dict, List, Any, Optional
from datetime import datetime
import json

class KnowledgeContract:
    """
    Structured contract for knowledge reuse.
    
    This class defines the metadata schema that makes findings reusable
    beyond just storing them in the database.
    
    RXRE-1642 design: separates claim + epistemic (stored in RXRE-1640 tables)
    from applicability + source + reproducibility metadata (stored as JSON).
    """
    
    def __init__(self, finding_id: str, claim: str, epistemic: str,
                 applicability: Optional[Dict] = None,
                 source: Optional[Dict] = None,
                 provenance: Optional[Dict] = None,
                 relations: Optional[Dict] = None,
                 reproducibility: Optional[Dict] = None,
                 impact: Optional[Dict] = None,
                 timestamp: Optional[str] = None):
        self.finding_id = finding_id
        self.claim = claim
        self.epistemic = epistemic
        
        # Default metadata structures
        default_applicability = {
            'artifact': None,
            'version': None,
            'architecture': None,
            'tool': None,
            'tool_settings': None,
            'kernel_version': None,
            'driver_version': None,
            'scope': None,
            'context': None,
        }
        
        default_source = {
            'source_file': None,
            'source_hash': None,
            'extraction_method': None,
            'source_revision': None,
        }
        
        default_provenance = {
            'producer': None,
            'tool': None,
            'tool_version': None,
            'method': None,
            'timestamp': None,
            'source_finding_number': None,
        }
        
        default_relations = {
            'related_findings': [],
            'relation_types': [],
        }
        
        default_reproducibility = {
            'commands': [],
            'parameters': [],
            'raw_outputs': [],
            'verification_procedure': None,
        }
        
        default_impact = {
            'technical': None,
            'operational': None,
            'risk_level': None,
        }
        
        # Merge with defaults
        self.applicability = {**default_applicability, **(applicability or {})}
        self.source = {**default_source, **(source or {})}
        self.provenance = {**default_provenance, **(provenance or {})}
        self.relations = {**default_relations, **(relations or {})}
        self.reproducibility = {**default_reproducibility, **(reproducibility or {})}
        self.impact = {**default_impact, **(impact or {})}
        self.timestamp = timestamp or datetime.utcnow().isoformat()
    
    def add_applicability(self, **kwargs) -> None:
        """Add applicability metadata."""
        for key, value in kwargs.items():
            if key in self.applicability:
                self.applicability[key] = value
    
    def add_source(self, **kwargs) -> None:
        """Add source metadata."""
        for key, value in kwargs.items():
            if key in self.source:
                self.source[key] = value
    
    def add_provenance(self, **kwargs) -> None:
        """Add provenance metadata."""
        for key, value in kwargs.items():
            if key in self.provenance:
                self.provenance[key] = value
    
    def add_relation(self, target_finding_id: str, relation_type: str, evidence: Optional[Dict] = None) -> None:
        """Add a relation between findings."""
        self.relations['related_findings'].append(target_finding_id)
        self.relations['relation_types'].append(relation_type)
        if evidence:
            # Store evidence as a dict with 'target' and 'relation' fields
            self.relations.setdefault('relations', []).append({
                'target': target_finding_id,
                'relation': relation_type,
                'evidence': evidence or {}
            })
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for storage."""
        return {
            'finding_id': self.finding_id,
            'claim': self.claim,
            'epistemic': self.epistemic,
            'applicability': self.applicability,
            'source': self.source,
            'provenance': self.provenance,
            'relations': self.relations,
            'reproducibility': self.reproducibility,
            'impact': self.impact,
            'timestamp': self.timestamp,
        }
    
    def to_json(self) -> str:
        """Convert to JSON string."""
        return json.dumps(self.to_dict(), indent=2)
    
    @staticmethod
    def from_dict(data: Dict[str, Any]) -> 'KnowledgeContract':
        """Create from dictionary."""
        contract = KnowledgeContract(
            finding_id=data['finding_id'],
            claim=data['claim'],
            epistemic=data['epistemic']
        )
        
        # Restore metadata
        contract.applicability = data.get('applicability', {})
        contract.source = data.get('source', {})
        contract.provenance = data.get('provenance', {})
        contract.relations = data.get('relations', {})
        contract.reproducibility = data.get('reproducibility', {})
        contract.impact = data.get('impact', {})
        contract.timestamp = data.get('timestamp', datetime.utcnow().isoformat())
        
        return contract

# Convenience functions for common operations
def create_contract_from_finding(finding_dict: Dict[str, Any]) -> 'KnowledgeContract':
    """Create a KnowledgeContract from a finding dictionary."""
    # Extract basic info
    finding_id = finding_dict.get('finding_id', 'unknown')
    claim = finding_dict.get('claim', '')
    epistemic = finding_dict.get('epistemic', 'NOT_DETERMINED')
    
    # Extract applicability metadata
    applicability = {
        'artifact': finding_dict.get('applicability', {}).get('artifact'),
        'version': finding_dict.get('applicability', {}).get('version'),
        'architecture': finding_dict.get('applicability', {}).get('architecture'),
        'tool': finding_dict.get('applicability', {}).get('tool'),
        'tool_settings': finding_dict.get('applicability', {}).get('tool_settings'),
        'kernel_version': finding_dict.get('applicability', {}).get('kernel_version'),
        'driver_version': finding_dict.get('applicability', {}).get('driver_version'),
        'scope': finding_dict.get('applicability', {}).get('scope'),
        'context': finding_dict.get('applicability', {}).get('context'),
    }
    
    source = {
        'source_file': finding_dict.get('source', {}).get('source_file'),
        'source_hash': finding_dict.get('source', {}).get('source_hash'),
        'extraction_method': finding_dict.get('source', {}).get('extraction_method'),
        'source_revision': finding_dict.get('source', {}).get('source_revision'),
    }
    
    provenance = {
        'producer': finding_dict.get('provenance', {}).get('producer'),
        'tool': finding_dict.get('provenance', {}).get('tool'),
        'tool_version': finding_dict.get('provenance', {}).get('tool_version'),
        'method': finding_dict.get('provenance', {}).get('method'),
        'timestamp': finding_dict.get('provenance', {}).get('timestamp'),
        'source_finding_number': finding_dict.get('provenance', {}).get('source_finding_number'),
    }
    
    relations = {
        'related_findings': finding_dict.get('relations', {}).get('related_findings', []),
        'relation_types': finding_dict.get('relations', {}).get('relation_types', []),
    }
    
    reproducibility = {
        'commands': finding_dict.get('reproducibility', {}).get('commands', []),
        'parameters': finding_dict.get('reproducibility', {}).get('parameters', []),
        'raw_outputs': finding_dict.get('reproducibility', {}).get('raw_outputs', []),
        'verification_procedure': finding_dict.get('reproducibility', {}).get('verification_procedure'),
    }
    
    impact = {
        'technical': finding_dict.get('impact', {}).get('technical'),
        'operational': finding_dict.get('impact', {}).get('operational'),
        'risk_level': finding_dict.get('impact', {}).get('risk_level'),
    }
    
    return KnowledgeContract(
        finding_id=finding_id,
        claim=claim,
        epistemic=epistemic,
        applicability=applicability,
        source=source,
        provenance=provenance,
        relations=relations,
        reproducibility=reproducibility,
        impact=impact,
        timestamp=datetime.utcnow().isoformat()
    )

if __name__ == '__main__':
    # Example usage
    sample_data = {
        'finding_id': 'finding_1234567890abcdef',
        'claim': 'The dword_index division destroys register identity in MMIO space',
        'epistemic': 'NOT_DETERMINED',
        'applicability': {
            'artifact': 'reg_resolve.py',
            'version': '1.2.3',
            'architecture': 'GFX8',
            'tool': 'rizin',
            'tool_settings': 'aaa; axtj',
            'kernel_version': '5.15.0',
            'driver_version': '5.15.0',
            'scope': 'MMIO space analysis',
            'context': 'Polaris12/GFX8 architecture',
        },
        'source': {
            'source_file': 'tools/rxre/knowledge_ingestion/historical_parser.py',
            'source_hash': 'sha256:abc123',
            'extraction_method': 'markdown_ingestion',
            'source_revision': 'main',
        },
        'provenance': {
            'producer': 'rizin_xrefs',
            'tool': 'rizin',
            'tool_version': '0.7.4',
            'method': 'aaa; axtj',
            'timestamp': '2026-10-12T10:30:00Z',
            'source_finding_number': '1589',
        },
        'relations': {
            'related_findings': ['finding_20e0e8e6eb295356'],
            'relation_types': ['IMPLEMENTA'],
        },
        'reproducibility': {
            'commands': ['rizin -aaa -axtj file.bin'],
            'parameters': ['-aaa', '-axtj'],
            'raw_outputs': [],
            'verification_procedure': 'Verify register identity preservation',
        },
        'impact': {
            'technical': 'Register identity preservation',
            'operational': 'Reduces analysis time for GFX8',
            'risk_level': 'LOW',
        },
        'timestamp': '2026-10-12T10:30:00Z',
    }
    
    contract = KnowledgeContract.from_dict(sample_data)
    print('Sample contract:')
    print(contract.to_json())