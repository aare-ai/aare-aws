"""
Proof certificate generator for verification results
Creates cryptographically signed proofs of verification
"""

import json
import hashlib
import hmac
import time
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, asdict
from datetime import datetime, timezone
import base64
import uuid
import logging

logger = logging.getLogger(__name__)


@dataclass
class ProofCertificate:
    """Represents a proof certificate"""
    id: str
    verification_id: str
    timestamp: str
    input_hash: str
    ontology_hash: str
    result: bool
    solver_trace: List[Dict]
    signature: str
    version: str = "1.0.0"
    
    def to_dict(self) -> Dict:
        return asdict(self)
    
    def to_json(self) -> str:
        return json.dumps(self.to_dict(), indent=2)


class ProofGenerator:
    """
    Generates cryptographic proof certificates for verification results
    Provides non-repudiation and audit trail
    """
    
    def __init__(self, signing_key: Optional[str] = None):
        """
        Initialize proof generator
        
        Args:
            signing_key: Secret key for signing proofs (from environment)
        """
        self.signing_key = signing_key or self._generate_key()
        self.algorithm = 'HMAC-SHA256'
    
    def generate(self, 
                 verification_id: str,
                 input_data: Dict[str, Any],
                 ontology_name: str,
                 verification_result: Dict[str, Any]) -> Dict[str, Any]:
        """
        Generate a proof certificate for verification result
        
        Args:
            verification_id: Unique verification ID
            input_data: Original input that was verified
            ontology_name: Name of ontology used
            verification_result: Result from SMT solver
            
        Returns:
            Proof certificate dictionary
        """
        # Generate proof ID
        proof_id = str(uuid.uuid4())
        
        # Calculate hashes
        input_hash = self._hash_data(input_data)
        ontology_hash = self._hash_string(ontology_name)
        
        # Extract solver trace
        solver_trace = self._extract_solver_trace(verification_result)
        
        # Create timestamp
        timestamp = datetime.now(timezone.utc).isoformat()
        
        # Build proof data
        proof_data = {
            'id': proof_id,
            'verification_id': verification_id,
            'timestamp': timestamp,
            'input_hash': input_hash,
            'ontology_hash': ontology_hash,
            'ontology_name': ontology_name,
            'result': verification_result.get('verified', False),
            'solver_trace': solver_trace,
            'violations': verification_result.get('violations', []),
            'execution_time_ms': verification_result.get('execution_time_ms', 0),
            'version': '1.0.0'
        }
        
        # Generate signature
        signature = self._sign_proof(proof_data)
        proof_data['signature'] = signature
        proof_data['algorithm'] = self.algorithm
        
        # Add metadata
        proof_data['metadata'] = {
            'generated_at': timestamp,
            'generator_version': '1.0.0',
            'hash_algorithm': 'SHA256',
            'signature_algorithm': self.algorithm
        }
        
        # Create compact hash for reference
        proof_data['hash'] = self._hash_data(proof_data)[:16]  # Short hash for reference
        
        logger.info(f"Generated proof certificate {proof_id} for verification {verification_id}")
        
        return proof_data
    
    def verify_proof(self, proof: Dict[str, Any]) -> bool:
        """
        Verify a proof certificate's signature
        
        Args:
            proof: Proof certificate to verify
            
        Returns:
            True if signature is valid
        """
        try:
            # Extract signature
            signature = proof.get('signature')
            if not signature:
                logger.error("Proof missing signature")
                return False
            
            # Remove signature from data for verification
            proof_data = proof.copy()
            proof_data.pop('signature', None)
            proof_data.pop('metadata', None)
            proof_data.pop('hash', None)
            
            # Recalculate signature
            expected_signature = self._sign_proof(proof_data)
            
            # Constant-time comparison
            return hmac.compare_digest(signature, expected_signature)
            
        except Exception as e:
            logger.error(f"Error verifying proof: {str(e)}")
            return False
    
    def create_audit_entry(self, proof: Dict[str, Any]) -> Dict[str, Any]:
        """
        Create an audit log entry from proof certificate
        
        Args:
            proof: Proof certificate
            
        Returns:
            Audit entry dictionary
        """
        return {
            'proof_id': proof.get('id'),
            'verification_id': proof.get('verification_id'),
            'timestamp': proof.get('timestamp'),
            'result': proof.get('result'),
            'ontology': proof.get('ontology_name'),
            'input_hash': proof.get('input_hash'),
            'signature': proof.get('signature')[:32] + '...',  # Truncated signature
            'violations_count': len(proof.get('violations', [])),
            'execution_time_ms': proof.get('execution_time_ms')
        }
    
    def _extract_solver_trace(self, verification_result: Dict[str, Any]) -> List[Dict]:
        """
        Extract solver trace for proof
        
        Args:
            verification_result: Result from verifier
            
        Returns:
            List of solver steps
        """
        trace = []
        
        # Add constraint checking steps
        for constraint in verification_result.get('constraints_checked', []):
            trace.append({
                'step': 'check_constraint',
                'constraint': constraint,
                'result': 'satisfied'
            })
        
        # Add violations
        for violation in verification_result.get('violations', []):
            trace.append({
                'step': 'violation_found',
                'constraint': violation.get('constraint'),
                'expected': violation.get('expected'),
                'actual': violation.get('actual')
            })
        
        # Add final result
        trace.append({
            'step': 'final_result',
            'verified': verification_result.get('verified'),
            'total_constraints': verification_result.get('constraints_checked', 0),
            'total_violations': len(verification_result.get('violations', []))
        })
        
        return trace
    
    def _hash_data(self, data: Any) -> str:
        """
        Calculate SHA256 hash of data
        
        Args:
            data: Data to hash
            
        Returns:
            Hex string hash
        """
        if not isinstance(data, str):
            data = json.dumps(data, sort_keys=True)
        
        return hashlib.sha256(data.encode()).hexdigest()
    
    def _hash_string(self, text: str) -> str:
        """
        Calculate SHA256 hash of string
        
        Args:
            text: Text to hash
            
        Returns:
            Hex string hash
        """
        return hashlib.sha256(text.encode()).hexdigest()
    
    def _sign_proof(self, proof_data: Dict[str, Any]) -> str:
        """
        Sign proof data with HMAC
        
        Args:
            proof_data: Data to sign
            
        Returns:
            Base64 encoded signature
        """
        # Serialize data deterministically
        message = json.dumps(proof_data, sort_keys=True)
        
        # Calculate HMAC
        signature = hmac.new(
            self.signing_key.encode(),
            message.encode(),
            hashlib.sha256
        ).digest()
        
        # Return base64 encoded
        return base64.b64encode(signature).decode()
    
    def _generate_key(self) -> str:
        """Generate a random signing key"""
        return base64.b64encode(uuid.uuid4().bytes + uuid.uuid4().bytes).decode()
    
    def export_proof_bundle(self, proof: Dict[str, Any], 
                           include_metadata: bool = True) -> Dict[str, Any]:
        """
        Export proof as a complete bundle for archival
        
        Args:
            proof: Proof certificate
            include_metadata: Whether to include full metadata
            
        Returns:
            Proof bundle for export
        """
        bundle = {
            'proof': proof,
            'export_time': datetime.now(timezone.utc).isoformat(),
            'format_version': '1.0.0'
        }
        
        if include_metadata:
            bundle['metadata'] = {
                'algorithm': self.algorithm,
                'hash_algorithm': 'SHA256',
                'generator': 'aare.ai',
                'generator_version': '1.0.0'
            }
        
        # Add bundle signature
        bundle['bundle_signature'] = self._hash_data(bundle)
        
        return bundle
