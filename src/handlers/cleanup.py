"""
Lambda handler for cleaning up old verification records
Runs daily to remove expired data
"""

import os
import json
import boto3
from datetime import datetime, timedelta
from typing import Dict, Any
from aws_lambda_powertools import Logger
from aws_lambda_powertools.utilities.typing import LambdaContext

logger = Logger()

dynamodb = boto3.resource('dynamodb')
s3 = boto3.client('s3')

DYNAMODB_TABLE = os.environ['DYNAMODB_TABLE']
S3_PROOF_BUCKET = os.environ['S3_PROOF_BUCKET']


@logger.inject_lambda_context
def handler(event: Dict[str, Any], context: LambdaContext) -> Dict[str, Any]:
    """
    Clean up old verification records and proof certificates
    
    Args:
        event: CloudWatch Events event
        context: Lambda context
        
    Returns:
        Response dictionary
    """
    try:
        logger.info("Starting cleanup task")
        
        table = dynamodb.Table(DYNAMODB_TABLE)
        
        # Calculate cutoff time (30 days ago)
        cutoff_time = datetime.utcnow() - timedelta(days=30)
        cutoff_timestamp = int(cutoff_time.timestamp())
        
        # Scan for old records (TTL should handle this, but this is a backup)
        response = table.scan(
            FilterExpression='#ts < :cutoff',
            ExpressionAttributeNames={'#ts': 'timestamp'},
            ExpressionAttributeValues={':cutoff': cutoff_timestamp},
            ProjectionExpression='id,userId,#ts',
            Limit=100  # Process in batches
        )
        
        items = response.get('Items', [])
        deleted_count = 0
        
        # Delete old records
        with table.batch_writer() as batch:
            for item in items:
                verification_id = item['id']
                user_id = item.get('userId', 'unknown')
                
                # Delete from DynamoDB
                batch.delete_item(Key={'id': verification_id})
                
                # Delete associated proof from S3
                proof_key = f"{user_id}/{verification_id}/proof.json"
                try:
                    s3.delete_object(Bucket=S3_PROOF_BUCKET, Key=proof_key)
                    logger.debug(f"Deleted proof {proof_key}")
                except Exception as e:
                    logger.warning(f"Could not delete proof {proof_key}: {str(e)}")
                
                deleted_count += 1
        
        logger.info(f"Deleted {deleted_count} old verification records")
        
        # Clean up orphaned S3 objects (proofs without verification records)
        # This is more complex and should be done carefully in production
        
        return {
            'statusCode': 200,
            'body': json.dumps({
                'message': 'Cleanup completed successfully',
                'deleted_records': deleted_count,
                'cutoff_date': cutoff_time.isoformat()
            })
        }
        
    except Exception as e:
        logger.error(f"Error in cleanup task: {str(e)}")
        return {
            'statusCode': 500,
            'body': json.dumps({
                'error': str(e)
            })
        }
