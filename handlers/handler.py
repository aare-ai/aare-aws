"""
aare.ai - Main verification handler
Version: 2.0.1
"""
import json
import uuid
from datetime import datetime
from handlers.ontology_loader import OntologyLoader
from handlers.llm_parser import LLMParser
from handlers.smt_verifier import SMTVerifier

llm_parser = LLMParser()
smt_verifier = SMTVerifier()

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
                'solver': 'Constraint Logic',
                'verification_id': str(uuid.uuid4()),
                'execution_time_ms': verification_result['execution_time_ms'],
                'timestamp': datetime.utcnow().isoformat()
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