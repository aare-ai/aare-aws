"""
Response utilities for Lambda functions
Provides consistent API Gateway response format
"""

import json
from typing import Any, Dict, Optional
from decimal import Decimal
import logging

logger = logging.getLogger(__name__)


class DecimalEncoder(json.JSONEncoder):
    """JSON encoder that handles Decimal types"""
    def default(self, obj):
        if isinstance(obj, Decimal):
            return float(obj)
        return super(DecimalEncoder, self).default(obj)


def success_response(data: Any, 
                    status_code: int = 200,
                    headers: Optional[Dict[str, str]] = None) -> Dict[str, Any]:
    """
    Create successful API Gateway response
    
    Args:
        data: Response data
        status_code: HTTP status code (default 200)
        headers: Additional headers
        
    Returns:
        API Gateway response dictionary
    """
    response_headers = {
        'Content-Type': 'application/json',
        'Access-Control-Allow-Origin': '*',
        'Access-Control-Allow-Headers': 'Content-Type,X-Amz-Date,Authorization,X-Api-Key',
        'Access-Control-Allow-Methods': 'GET,POST,OPTIONS'
    }
    
    if headers:
        response_headers.update(headers)
    
    return {
        'statusCode': status_code,
        'headers': response_headers,
        'body': json.dumps(data, cls=DecimalEncoder)
    }


def error_response(status_code: int,
                  message: str,
                  error_type: Optional[str] = None,
                  details: Optional[Dict] = None) -> Dict[str, Any]:
    """
    Create error API Gateway response
    
    Args:
        status_code: HTTP status code
        message: Error message
        error_type: Type of error (optional)
        details: Additional error details (optional)
        
    Returns:
        API Gateway response dictionary
    """
    error_body = {
        'error': {
            'message': message,
            'type': error_type or 'Error',
            'statusCode': status_code
        }
    }
    
    if details:
        error_body['error']['details'] = details
    
    response_headers = {
        'Content-Type': 'application/json',
        'Access-Control-Allow-Origin': '*',
        'Access-Control-Allow-Headers': 'Content-Type,X-Amz-Date,Authorization,X-Api-Key',
        'Access-Control-Allow-Methods': 'GET,POST,OPTIONS'
    }
    
    logger.error(f"Returning error response: {status_code} - {message}")
    
    return {
        'statusCode': status_code,
        'headers': response_headers,
        'body': json.dumps(error_body)
    }


def validation_error_response(errors: list) -> Dict[str, Any]:
    """
    Create validation error response
    
    Args:
        errors: List of validation errors
        
    Returns:
        API Gateway response dictionary
    """
    return error_response(
        status_code=400,
        message='Validation failed',
        error_type='ValidationError',
        details={'validation_errors': errors}
    )


def not_found_response(resource: str) -> Dict[str, Any]:
    """
    Create not found response
    
    Args:
        resource: Resource that was not found
        
    Returns:
        API Gateway response dictionary
    """
    return error_response(
        status_code=404,
        message=f'{resource} not found',
        error_type='NotFoundError'
    )


def unauthorized_response(message: str = 'Unauthorized') -> Dict[str, Any]:
    """
    Create unauthorized response
    
    Args:
        message: Error message
        
    Returns:
        API Gateway response dictionary
    """
    return error_response(
        status_code=401,
        message=message,
        error_type='UnauthorizedError'
    )


def rate_limit_response(retry_after: Optional[int] = None) -> Dict[str, Any]:
    """
    Create rate limit response
    
    Args:
        retry_after: Seconds until retry allowed
        
    Returns:
        API Gateway response dictionary
    """
    headers = {}
    if retry_after:
        headers['Retry-After'] = str(retry_after)
    
    return error_response(
        status_code=429,
        message='Rate limit exceeded',
        error_type='RateLimitError',
        details={'retry_after': retry_after} if retry_after else None
    )


def timeout_response() -> Dict[str, Any]:
    """
    Create timeout response
    
    Returns:
        API Gateway response dictionary
    """
    return error_response(
        status_code=408,
        message='Request timeout',
        error_type='TimeoutError'
    )


def internal_error_response(request_id: Optional[str] = None) -> Dict[str, Any]:
    """
    Create internal server error response
    
    Args:
        request_id: Request ID for debugging
        
    Returns:
        API Gateway response dictionary
    """
    details = {}
    if request_id:
        details['request_id'] = request_id
    
    return error_response(
        status_code=500,
        message='Internal server error',
        error_type='InternalError',
        details=details if details else None
    )


def options_response() -> Dict[str, Any]:
    """
    Create OPTIONS response for CORS preflight
    
    Returns:
        API Gateway response dictionary
    """
    return {
        'statusCode': 200,
        'headers': {
            'Access-Control-Allow-Origin': '*',
            'Access-Control-Allow-Headers': 'Content-Type,X-Amz-Date,Authorization,X-Api-Key',
            'Access-Control-Allow-Methods': 'GET,POST,OPTIONS',
            'Access-Control-Max-Age': '86400'
        },
        'body': ''
    }
