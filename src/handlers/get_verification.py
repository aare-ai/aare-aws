"""
Lambda handler for retrieving verification details
GET /verification/{id}
"""

import json
import os
import logging
from typing import Dict, Any
from aws_lambda_powertools import Logger, Tracer
from aws_lambda_powertools.utilities.typing import LambdaContext

from ..utils.dynamodb import get_verification
from ..utils.response import success_response, not_found_response, error_response

logger = Logger()
tracer = Tracer()

DYNAMODB_TABLE = os.environ['DYNAMODB_TABLE']


@logger.inject_lambda_context(correlation_id_path="headers.x-correlation-id")
@tracer.capture_lambda_handler
def handler(event: Dict[str, Any], context: LambdaContext) -> Dict[str, Any]:
    """
    Retrieve verification details by ID
    
    Args:
        event: API Gateway event
        context: Lambda context
        
    Returns:
        API Gateway response
    """
    try:
        # Extract verification ID from path
        verification_id = event.get('pathParameters', {}).get('id')
        
        if not verification_id:
            return error_response(400, 'Verification ID required')
        
        logger.info(f"Retrieving verification {verification_id}")
        
        # Get from DynamoDB
        verification = get_verification(DYNAMODB_TABLE, verification_id)
        
        if not verification:
            return not_found_response(f'Verification {verification_id}')
        
        # Format response
        response_data = {
            'verification_id': verification.get('id'),
            'status': 'verified' if verification.get('verified') else 'failed',
            'ontology': verification.get('ontologyName'),
            'timestamp': verification.get('createdAt'),
            'result': verification.get('result', {}),
            'violations_count': verification.get('violationsCount', 0)
        }
        
        return success_response(response_data)
        
    except Exception as e:
        logger.error(f"Error retrieving verification: {str(e)}")
        return error_response(500, 'Internal server error')
