"""
aare.ai - Main verification handler
Version: 2.1.0
"""
import json
import os
import uuid
import hashlib
from datetime import datetime, timedelta
import boto3
from aare_core import OntologyLoader, LLMParser, SMTVerifier

llm_parser = LLMParser()
smt_verifier = SMTVerifier()

# Initialize DynamoDB client
dynamodb = boto3.resource('dynamodb')
VERIFICATION_TABLE = os.environ.get('VERIFICATION_TABLE', 'aare-ai-verifications-prod')

def handler(event, context):
    """AWS Lambda handler for aare.ai verification"""
    try:
        # Handle CORS preflight
        if event.get('httpMethod') == 'OPTIONS':
            return {
                'statusCode': 200,
                'headers': _cors_headers(),
                'body': ''
            }
        
        # Parse request
        body = json.loads(event.get('body', '{}'))
        llm_output = body.get('llm_output', '')
        ontology_name = body.get('ontology', 'mortgage-compliance-v1')

        # Load ontology (fresh each request to pick up S3 changes)
        ontology_loader = OntologyLoader()
        try:
            ontology = ontology_loader.load(ontology_name)
        except Exception as load_err:
            return {
                'statusCode': 500,
                'headers': _cors_headers(),
                'body': json.dumps({
                    'error': f'Ontology load failed: {str(load_err)}',
                    'ontology_name': ontology_name
                })
            }
        
        # Parse LLM output into structured data
        extracted_data = llm_parser.parse(llm_output, ontology)
        
        # Verify constraints using Z3
        verification_result = smt_verifier.verify(extracted_data, ontology)

        # Generate verification ID and timestamp
        verification_id = str(uuid.uuid4())
        timestamp = datetime.utcnow().isoformat()

        # Store verification record in DynamoDB
        certificate_hash = _store_verification(
            verification_id,
            ontology['name'],
            llm_output,
            verification_result,
            verification_result['execution_time_ms']
        )

        # Build response
        return {
            'statusCode': 200,
            'headers': _cors_headers(),
            'body': json.dumps({
                'verified': verification_result['verified'],
                'violations': verification_result['violations'],
                'parsed_data': extracted_data,
                'ontology': {
                    'name': ontology['name'],
                    'version': ontology['version'],
                    'constraints_checked': len(ontology['constraints'])
                },
                'proof': verification_result['proof'],
                'certificate_hash': certificate_hash,
                'solver': 'Constraint Logic',
                'verification_id': verification_id,
                'execution_time_ms': verification_result['execution_time_ms'],
                'timestamp': timestamp
            })
        }
        
    except Exception as e:
        return {
            'statusCode': 500,
            'headers': _cors_headers(),
            'body': json.dumps({
                'error': str(e),
                'type': type(e).__name__
            })
        }

def _cors_headers():
    return {
        'Content-Type': 'application/json',
        'Access-Control-Allow-Origin': '*',
        'Access-Control-Allow-Headers': 'Content-Type,x-api-key',
        'Access-Control-Allow-Methods': 'OPTIONS,POST'
    }


def _store_verification(verification_id, ontology_name, llm_output, result, execution_time_ms):
    """Store verification record in DynamoDB with proof certificate hash"""
    try:
        table = dynamodb.Table(VERIFICATION_TABLE)
        timestamp = datetime.utcnow().isoformat()

        # Create proof certificate hash for integrity verification
        certificate_data = json.dumps({
            'verification_id': verification_id,
            'ontology': ontology_name,
            'verified': result['verified'],
            'violations': result['violations'],
            'timestamp': timestamp
        }, sort_keys=True)
        certificate_hash = hashlib.sha256(certificate_data.encode()).hexdigest()

        # TTL: 90 days from now
        ttl = int((datetime.utcnow() + timedelta(days=90)).timestamp())

        item = {
            'verification_id': verification_id,
            'ontology_name': ontology_name,
            'timestamp': timestamp,
            'verified': result['verified'],
            'violation_count': len(result['violations']),
            'violations': result['violations'] if result['violations'] else [],
            'input_hash': hashlib.sha256(llm_output.encode()).hexdigest(),
            'certificate_hash': certificate_hash,
            'execution_time_ms': execution_time_ms,
            'ttl': ttl
        }

        table.put_item(Item=item)
        return certificate_hash
    except Exception as e:
        # Log but don't fail the verification if storage fails
        print(f"DynamoDB storage error: {e}")
        return None