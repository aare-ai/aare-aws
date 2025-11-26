"""
Lambda handler for monitoring and metrics collection
Runs on schedule to aggregate usage data
"""

import os
import json
import boto3
from datetime import datetime, timedelta
from typing import Dict, Any
from aws_lambda_powertools import Logger, Metrics
from aws_lambda_powertools.metrics import MetricUnit
from aws_lambda_powertools.utilities.typing import LambdaContext

logger = Logger()
metrics = Metrics()

dynamodb = boto3.resource('dynamodb')
cloudwatch = boto3.client('cloudwatch')

DYNAMODB_TABLE = os.environ['DYNAMODB_TABLE']


@logger.inject_lambda_context
@metrics.log_metrics(capture_cold_start_metric=True)
def handler(event: Dict[str, Any], context: LambdaContext) -> Dict[str, Any]:
    """
    Collect and publish usage metrics
    
    Args:
        event: CloudWatch Events event
        context: Lambda context
        
    Returns:
        Response dictionary
    """
    try:
        logger.info("Running monitoring task")
        
        table = dynamodb.Table(DYNAMODB_TABLE)
        
        # Calculate time window (last 5 minutes)
        end_time = datetime.utcnow()
        start_time = end_time - timedelta(minutes=5)
        start_timestamp = int(start_time.timestamp())
        end_timestamp = int(end_time.timestamp())
        
        # Scan for recent verifications (not ideal for large scale, use streams in production)
        response = table.scan(
            FilterExpression='#ts BETWEEN :start AND :end',
            ExpressionAttributeNames={'#ts': 'timestamp'},
            ExpressionAttributeValues={
                ':start': start_timestamp,
                ':end': end_timestamp
            },
            ProjectionExpression='verified,ontologyName,violationsCount,executionTimeMs'
        )
        
        items = response.get('Items', [])
        
        if items:
            # Calculate metrics
            total_verifications = len(items)
            successful_verifications = sum(1 for item in items if item.get('verified'))
            failed_verifications = total_verifications - successful_verifications
            avg_execution_time = sum(item.get('executionTimeMs', 0) for item in items) / len(items) if items else 0
            
            # Count by ontology
            ontology_counts = {}
            for item in items:
                ontology = item.get('ontologyName', 'unknown')
                ontology_counts[ontology] = ontology_counts.get(ontology, 0) + 1
            
            # Publish to CloudWatch
            cloudwatch.put_metric_data(
                Namespace='aare.ai',
                MetricData=[
                    {
                        'MetricName': 'TotalVerifications',
                        'Value': total_verifications,
                        'Unit': 'Count',
                        'Timestamp': end_time
                    },
                    {
                        'MetricName': 'SuccessfulVerifications',
                        'Value': successful_verifications,
                        'Unit': 'Count',
                        'Timestamp': end_time
                    },
                    {
                        'MetricName': 'FailedVerifications',
                        'Value': failed_verifications,
                        'Unit': 'Count',
                        'Timestamp': end_time
                    },
                    {
                        'MetricName': 'AverageExecutionTime',
                        'Value': avg_execution_time,
                        'Unit': 'Milliseconds',
                        'Timestamp': end_time
                    },
                    {
                        'MetricName': 'SuccessRate',
                        'Value': (successful_verifications / total_verifications * 100) if total_verifications > 0 else 0,
                        'Unit': 'Percent',
                        'Timestamp': end_time
                    }
                ]
            )
            
            # Publish per-ontology metrics
            for ontology, count in ontology_counts.items():
                cloudwatch.put_metric_data(
                    Namespace='aare.ai/Ontologies',
                    MetricData=[
                        {
                            'MetricName': 'VerificationCount',
                            'Value': count,
                            'Unit': 'Count',
                            'Dimensions': [
                                {
                                    'Name': 'OntologyName',
                                    'Value': ontology
                                }
                            ],
                            'Timestamp': end_time
                        }
                    ]
                )
            
            logger.info(f"Published metrics for {total_verifications} verifications")
            
            # Log metrics using Lambda Powertools
            metrics.add_metric(name="MonitoringRun", unit=MetricUnit.Count, value=1)
            metrics.add_metric(name="VerificationsProcessed", unit=MetricUnit.Count, value=total_verifications)
            
            return {
                'statusCode': 200,
                'body': json.dumps({
                    'message': 'Metrics collected successfully',
                    'verifications_processed': total_verifications,
                    'time_window': {
                        'start': start_time.isoformat(),
                        'end': end_time.isoformat()
                    }
                })
            }
        else:
            logger.info("No verifications found in time window")
            return {
                'statusCode': 200,
                'body': json.dumps({
                    'message': 'No verifications to process',
                    'time_window': {
                        'start': start_time.isoformat(),
                        'end': end_time.isoformat()
                    }
                })
            }
        
    except Exception as e:
        logger.error(f"Error in monitoring task: {str(e)}")
        return {
            'statusCode': 500,
            'body': json.dumps({
                'error': str(e)
            })
        }
