"""
Lambda handlers for ontology management
Handles upload, retrieval, and listing of ontologies
"""

import json
import os
import base64
import boto3
from typing import Dict, Any
from aws_lambda_powertools import Logger, Tracer
from aws_lambda_powertools.utilities.typing import LambdaContext

from ..core.ontology import OntologyLoader
from ..utils.response import (
    success_response, 
    error_response, 
    not_found_response,
    validation_error_response
)

logger = Logger()
tracer = Tracer()

s3_client = boto3.client('s3')
S3_ONTOLOGY_BUCKET = os.environ['S3_ONTOLOGY_BUCKET']


@logger.inject_lambda_context(correlation_id_path="headers.x-correlation-id")
@tracer.capture_lambda_handler
def upload_handler(event: Dict[str, Any], context: LambdaContext) -> Dict[str, Any]:
    """
    Upload new ontology
    POST /ontology
    
    Args:
        event: API Gateway event
        context: Lambda context
        
    Returns:
        API Gateway response
    """
    try:
        # Parse request body
        body = json.loads(event.get('body', '{}'))
        
        # Extract ontology data
        ontology_name = body.get('name')
        ontology_data = body.get('ontology')
        author = event.get('requestContext', {}).get('identity', {}).get('apiKeyId', 'unknown')
        
        # Validate inputs
        errors = []
        if not ontology_name:
            errors.append('Ontology name is required')
        if not ontology_data:
            errors.append('Ontology data is required')
        
        if errors:
            return validation_error_response(errors)
        
        logger.info(f"Uploading ontology {ontology_name}")
        
        # Initialize loader
        loader = OntologyLoader(s3_client, S3_ONTOLOGY_BUCKET)
        
        # Upload ontology
        success = loader.upload_ontology(ontology_name, ontology_data, author)
        
        if not success:
            return error_response(400, 'Failed to upload ontology')
        
        return success_response({
            'message': f'Ontology {ontology_name} uploaded successfully',
            'name': ontology_name,
            'version': ontology_data.get('version', '1.0.0')
        }, status_code=201)
        
    except json.JSONDecodeError:
        return error_response(400, 'Invalid JSON in request body')
    except Exception as e:
        logger.error(f"Error uploading ontology: {str(e)}")
        return error_response(500, f'Internal server error: {str(e)}')


@logger.inject_lambda_context(correlation_id_path="headers.x-correlation-id")
@tracer.capture_lambda_handler
def get_handler(event: Dict[str, Any], context: LambdaContext) -> Dict[str, Any]:
    """
    Get ontology by name
    GET /ontology/{name}
    
    Args:
        event: API Gateway event
        context: Lambda context
        
    Returns:
        API Gateway response
    """
    try:
        # Extract ontology name from path
        ontology_name = event.get('pathParameters', {}).get('name')
        
        if not ontology_name:
            return error_response(400, 'Ontology name required')
        
        # Extract version from query params (optional)
        version = event.get('queryStringParameters', {}).get('version') if event.get('queryStringParameters') else None
        
        logger.info(f"Retrieving ontology {ontology_name} version {version or 'latest'}")
        
        # Initialize loader
        loader = OntologyLoader(s3_client, S3_ONTOLOGY_BUCKET)
        
        # Load ontology
        ontology = loader.load(ontology_name, version)
        
        if not ontology:
            return not_found_response(f'Ontology {ontology_name}')
        
        return success_response(ontology)
        
    except Exception as e:
        logger.error(f"Error retrieving ontology: {str(e)}")
        return error_response(500, 'Internal server error')


@logger.inject_lambda_context(correlation_id_path="headers.x-correlation-id")
@tracer.capture_lambda_handler
def list_handler(event: Dict[str, Any], context: LambdaContext) -> Dict[str, Any]:
    """
    List available ontologies
    GET /ontologies
    
    Args:
        event: API Gateway event
        context: Lambda context
        
    Returns:
        API Gateway response
    """
    try:
        logger.info("Listing available ontologies")
        
        # Initialize loader
        loader = OntologyLoader(s3_client, S3_ONTOLOGY_BUCKET)
        
        # List ontologies
        ontologies = loader.list_ontologies()
        
        # Add prebuilt ontologies info
        prebuilt = [
            {
                'name': 'fair-lending-v1',
                'description': 'Fair Lending Act compliance for loan decisions',
                'domain': 'financial-services',
                'prebuilt': True
            },
            {
                'name': 'gdpr-privacy-v1',
                'description': 'GDPR privacy compliance checks',
                'domain': 'data-privacy',
                'prebuilt': True
            },
            {
                'name': 'hipaa-phi-v1',
                'description': 'HIPAA PHI handling compliance',
                'domain': 'healthcare',
                'prebuilt': True
            }
        ]
        
        return success_response({
            'ontologies': ontologies,
            'prebuilt': prebuilt,
            'total': len(ontologies)
        })
        
    except Exception as e:
        logger.error(f"Error listing ontologies: {str(e)}")
        return error_response(500, 'Internal server error')
