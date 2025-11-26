"""
Main verification handler for aare.ai
Performs formal verification of LLM outputs against SMT constraints
"""

import json
import time
import uuid
import os
import boto3
import traceback
from typing import Dict, Any, List, Optional
from datetime import datetime
from aws_lambda_powertools import Logger, Tracer, Metrics
from aws_lambda_powertools.metrics import MetricUnit
from aws_lambda_powertools.utilities.typing import LambdaContext

from ..core.parser import OutputParser
from ..core.verifier import SMTVerifier
from ..core.ontology import OntologyLoader
from ..core.proof import ProofGenerator
from ..utils.dynamodb import save_verification, get_cached_result
from ..utils.response import success_response, error_response

# Initialize AWS services
logger = Logger()
tracer = Tracer()
metrics = Metrics()
dynamodb = boto3.resource('dynamodb')
s3 = boto3.client('s3')

# Environment variables
DYNAMODB_TABLE = os.environ['DYNAMODB_TABLE']
S3_PROOF_BUCKET = os.environ['S3_PROOF_BUCKET']
S3_ONTOLOGY_BUCKET = os.environ['S3_ONTOLOGY_BUCKET']


@logger.inject_lambda_context(correlation_id_path="headers.x-correlation-id")
@tracer.capture_lambda_handler
@metrics.log_metrics(capture_cold_start_metric=True)
def handler(event: Dict[str, Any], context: LambdaContext) -> Dict[str, Any]:
    """
    Main verification handler
    
    Args:
        event: API Gateway event containing verification request
        context: Lambda context
    
    Returns:
        API Gateway response with verification results
    """
    start_time = time.time()
    verification_id = str(uuid.uuid4())
    
    try:
        # Parse request body
        body = json.loads(event.get('body', '{}'))
        
        # Extract parameters
        content = body.get('content')
        ontology_name = body.get('ontology')
        rules = body.get('rules', [])
        timeout = body.get('timeout', 1000)  # milliseconds
        user_id = event.get('requestContext', {}).get('identity', {}).get('apiKeyId', 'anonymous')
        
        # Validate inputs
        if not content:
            return error_response(400, "Missing 'content' in request body")
        if not ontology_name:
            return error_response(400, "Missing 'ontology' in request body")
        
        logger.info(f"Starting verification {verification_id}", extra={
            "verification_id": verification_id,
            "ontology": ontology_name,
            "rules_count": len(rules),
            "user_id": user_id
        })
        
        # Check cache for identical request
        cache_key = generate_cache_key(content, ontology_name, rules)
        cached_result = get_cached_result(cache_key)
        if cached_result:
            logger.info("Cache hit", extra={"verification_id": verification_id})
            metrics.add_metric(name="CacheHit", unit=MetricUnit.Count, value=1)
            return success_response(cached_result)
        
        # Load ontology from S3
        ontology_loader = OntologyLoader(s3, S3_ONTOLOGY_BUCKET)
        ontology = ontology_loader.load(ontology_name)
        
        if not ontology:
            return error_response(404, f"Ontology '{ontology_name}' not found")
        
        # Parse LLM output into structured format
        parser = OutputParser()
        structured_output = parser.parse(content)
        
        logger.info("Parsed output", extra={
            "verification_id": verification_id,
            "claims_count": len(structured_output.get('claims', []))
        })
        
        # Initialize SMT verifier with ontology
        verifier = SMTVerifier(ontology)
        
        # Apply specific rules if provided, otherwise use all ontology rules
        if rules:
            verifier.set_active_rules(rules)
        
        # Perform verification with timeout
        verification_result = verifier.verify(
            structured_output,
            timeout_ms=timeout
        )
        
        # Generate proof certificate if verification succeeded
        proof_certificate = None
        proof_url = None
        if verification_result['verified']:
            proof_gen = ProofGenerator()
            proof_certificate = proof_gen.generate(
                verification_id,
                structured_output,
                ontology_name,
                verification_result
            )
            
            # Store proof in S3
            proof_key = f"{user_id}/{verification_id}/proof.json"
            s3.put_object(
                Bucket=S3_PROOF_BUCKET,
                Key=proof_key,
                Body=json.dumps(proof_certificate),
                ContentType='application/json'
            )
            proof_url = f"s3://{S3_PROOF_BUCKET}/{proof_key}"
        
        # Calculate execution time
        execution_time_ms = int((time.time() - start_time) * 1000)
        
        # Prepare response
        response_data = {
            'verification_id': verification_id,
            'verified': verification_result['verified'],
            'violations': verification_result.get('violations', []),
            'proof_certificate': proof_certificate.get('hash') if proof_certificate else None,
            'proof_url': proof_url,
            'execution_time_ms': execution_time_ms,
            'ontology_version': ontology.get('version', '1.0.0'),
            'timestamp': datetime.utcnow().isoformat()
        }
        
        # Save to DynamoDB
        save_verification(
            table_name=DYNAMODB_TABLE,
            verification_id=verification_id,
            user_id=user_id,
            ontology_name=ontology_name,
            result=response_data,
            cache_key=cache_key
        )
        
        # Log metrics
        metrics.add_metric(name="VerificationCompleted", unit=MetricUnit.Count, value=1)
        metrics.add_metric(name="VerificationLatency", unit=MetricUnit.Milliseconds, value=execution_time_ms)
        metrics.add_metric(name="VerificationSuccess" if verification_result['verified'] else "VerificationFailure", 
                          unit=MetricUnit.Count, value=1)
        
        logger.info("Verification completed", extra={
            "verification_id": verification_id,
            "verified": verification_result['verified'],
            "execution_time_ms": execution_time_ms
        })
        
        return success_response(response_data)
        
    except TimeoutError:
        logger.error(f"Verification timeout for {verification_id}")
        metrics.add_metric(name="VerificationTimeout", unit=MetricUnit.Count, value=1)
        return error_response(408, "Verification timeout exceeded")
        
    except Exception as e:
        logger.error(f"Verification error for {verification_id}: {str(e)}", extra={
            "error": str(e),
            "traceback": traceback.format_exc()
        })
        metrics.add_metric(name="VerificationError", unit=MetricUnit.Count, value=1)
        return error_response(500, f"Internal verification error: {str(e)}")


def generate_cache_key(content: Dict, ontology: str, rules: List[str]) -> str:
    """Generate cache key for verification request"""
    import hashlib
    cache_data = {
        'content': content,
        'ontology': ontology,
        'rules': sorted(rules)
    }
    cache_string = json.dumps(cache_data, sort_keys=True)
    return hashlib.sha256(cache_string.encode()).hexdigest()
