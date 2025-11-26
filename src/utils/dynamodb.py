"""
DynamoDB utility functions for verification data
Handles storage and retrieval of verification results
"""

import boto3
import json
from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta
from decimal import Decimal
import logging
from botocore.exceptions import ClientError

logger = logging.getLogger(__name__)


class DynamoDBHelper:
    """Helper class for DynamoDB operations"""
    
    def __init__(self, table_name: str, region: str = 'us-east-1'):
        """
        Initialize DynamoDB helper
        
        Args:
            table_name: Name of DynamoDB table
            region: AWS region
        """
        self.dynamodb = boto3.resource('dynamodb', region_name=region)
        self.table = self.dynamodb.Table(table_name)
        self.table_name = table_name
    
    def _serialize_floats(self, obj: Any) -> Any:
        """Convert floats to Decimal for DynamoDB"""
        if isinstance(obj, float):
            return Decimal(str(obj))
        elif isinstance(obj, dict):
            return {k: self._serialize_floats(v) for k, v in obj.items()}
        elif isinstance(obj, list):
            return [self._serialize_floats(item) for item in obj]
        return obj
    
    def _deserialize_decimals(self, obj: Any) -> Any:
        """Convert Decimals back to floats"""
        if isinstance(obj, Decimal):
            return float(obj)
        elif isinstance(obj, dict):
            return {k: self._deserialize_decimals(v) for k, v in obj.items()}
        elif isinstance(obj, list):
            return [self._deserialize_decimals(item) for item in obj]
        return obj


def save_verification(table_name: str,
                     verification_id: str,
                     user_id: str,
                     ontology_name: str,
                     result: Dict[str, Any],
                     cache_key: str) -> bool:
    """
    Save verification result to DynamoDB
    
    Args:
        table_name: DynamoDB table name
        verification_id: Unique verification ID
        user_id: User/API key ID
        ontology_name: Name of ontology used
        result: Verification result
        cache_key: Cache key for deduplication
        
    Returns:
        Success boolean
    """
    try:
        helper = DynamoDBHelper(table_name)
        
        # Prepare item
        item = {
            'id': verification_id,
            'userId': user_id,
            'ontologyName': ontology_name,
            'timestamp': int(datetime.utcnow().timestamp()),
            'result': helper._serialize_floats(result),
            'cacheKey': cache_key,
            'ttl': int((datetime.utcnow() + timedelta(days=30)).timestamp()),  # 30 day TTL
            'createdAt': datetime.utcnow().isoformat(),
            'verified': result.get('verified', False),
            'violationsCount': len(result.get('violations', []))
        }
        
        # Save to DynamoDB
        helper.table.put_item(Item=item)
        
        logger.info(f"Saved verification {verification_id} to DynamoDB")
        return True
        
    except ClientError as e:
        logger.error(f"Error saving verification to DynamoDB: {str(e)}")
        return False
    except Exception as e:
        logger.error(f"Unexpected error saving verification: {str(e)}")
        return False


def get_verification(table_name: str, verification_id: str) -> Optional[Dict[str, Any]]:
    """
    Retrieve verification result by ID
    
    Args:
        table_name: DynamoDB table name
        verification_id: Verification ID
        
    Returns:
        Verification result or None
    """
    try:
        helper = DynamoDBHelper(table_name)
        
        response = helper.table.get_item(
            Key={'id': verification_id}
        )
        
        if 'Item' in response:
            item = response['Item']
            return helper._deserialize_decimals(item)
        
        return None
        
    except ClientError as e:
        logger.error(f"Error retrieving verification: {str(e)}")
        return None


def get_cached_result(cache_key: str, table_name: str = None) -> Optional[Dict[str, Any]]:
    """
    Get cached verification result
    
    Args:
        cache_key: Cache key
        table_name: DynamoDB table name
        
    Returns:
        Cached result or None
    """
    if not table_name:
        import os
        table_name = os.environ.get('DYNAMODB_TABLE')
    
    try:
        helper = DynamoDBHelper(table_name)
        
        # Query by cache key (requires GSI on cacheKey)
        response = helper.table.query(
            IndexName='CacheIndex',
            KeyConditionExpression='cacheKey = :ck',
            ExpressionAttributeValues={
                ':ck': cache_key
            },
            Limit=1,
            ScanIndexForward=False  # Most recent first
        )
        
        if response['Items']:
            item = response['Items'][0]
            
            # Check if cache is still valid (within 1 hour)
            timestamp = item.get('timestamp', 0)
            if datetime.utcnow().timestamp() - timestamp < 3600:
                logger.info(f"Cache hit for key {cache_key[:8]}...")
                return helper._deserialize_decimals(item.get('result'))
        
        return None
        
    except ClientError as e:
        # Index might not exist, that's ok
        logger.debug(f"Cache lookup failed: {str(e)}")
        return None


def get_user_verifications(table_name: str, 
                          user_id: str,
                          limit: int = 100,
                          start_time: Optional[int] = None) -> List[Dict[str, Any]]:
    """
    Get verifications for a user
    
    Args:
        table_name: DynamoDB table name
        user_id: User ID
        limit: Maximum results
        start_time: Start timestamp (optional)
        
    Returns:
        List of verifications
    """
    try:
        helper = DynamoDBHelper(table_name)
        
        # Build query
        key_condition = 'userId = :uid'
        expression_values = {':uid': user_id}
        
        if start_time:
            key_condition += ' AND #ts > :start'
            expression_values[':start'] = start_time
        
        response = helper.table.query(
            IndexName='UserIndex',
            KeyConditionExpression=key_condition,
            ExpressionAttributeValues=expression_values,
            ExpressionAttributeNames={'#ts': 'timestamp'},
            Limit=limit,
            ScanIndexForward=False  # Most recent first
        )
        
        items = response.get('Items', [])
        return [helper._deserialize_decimals(item) for item in items]
        
    except ClientError as e:
        logger.error(f"Error querying user verifications: {str(e)}")
        return []


def update_verification_status(table_name: str,
                              verification_id: str,
                              status: str,
                              metadata: Optional[Dict] = None) -> bool:
    """
    Update verification status
    
    Args:
        table_name: DynamoDB table name
        verification_id: Verification ID
        status: New status
        metadata: Additional metadata
        
    Returns:
        Success boolean
    """
    try:
        helper = DynamoDBHelper(table_name)
        
        update_expression = 'SET #status = :status, updatedAt = :now'
        expression_values = {
            ':status': status,
            ':now': datetime.utcnow().isoformat()
        }
        expression_names = {'#status': 'status'}
        
        if metadata:
            update_expression += ', metadata = :metadata'
            expression_values[':metadata'] = helper._serialize_floats(metadata)
        
        helper.table.update_item(
            Key={'id': verification_id},
            UpdateExpression=update_expression,
            ExpressionAttributeValues=expression_values,
            ExpressionAttributeNames=expression_names
        )
        
        return True
        
    except ClientError as e:
        logger.error(f"Error updating verification: {str(e)}")
        return False


def get_ontology_stats(table_name: str, ontology_name: str) -> Dict[str, Any]:
    """
    Get statistics for an ontology
    
    Args:
        table_name: DynamoDB table name
        ontology_name: Ontology name
        
    Returns:
        Statistics dictionary
    """
    try:
        helper = DynamoDBHelper(table_name)
        
        response = helper.table.query(
            IndexName='OntologyIndex',
            KeyConditionExpression='ontologyName = :name',
            ExpressionAttributeValues={':name': ontology_name},
            Select='COUNT'
        )
        
        total_count = response.get('Count', 0)
        
        # Get success rate (requires scanning items)
        response = helper.table.query(
            IndexName='OntologyIndex',
            KeyConditionExpression='ontologyName = :name',
            ExpressionAttributeValues={':name': ontology_name},
            ProjectionExpression='verified'
        )
        
        items = response.get('Items', [])
        verified_count = sum(1 for item in items if item.get('verified'))
        
        return {
            'ontology': ontology_name,
            'total_verifications': total_count,
            'successful_verifications': verified_count,
            'success_rate': verified_count / total_count if total_count > 0 else 0,
            'last_updated': datetime.utcnow().isoformat()
        }
        
    except ClientError as e:
        logger.error(f"Error getting ontology stats: {str(e)}")
        return {
            'ontology': ontology_name,
            'error': str(e)
        }
