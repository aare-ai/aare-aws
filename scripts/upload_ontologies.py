#!/usr/bin/env python3
"""
Upload initial ontologies to S3
"""

import os
import json
import boto3
import argparse
from pathlib import Path


def upload_ontologies(stage='dev', region='us-east-1', profile='default'):
    """Upload ontology files to S3"""
    
    # Set up AWS session
    session = boto3.Session(profile_name=profile, region_name=region)
    s3 = session.client('s3')
    
    bucket_name = f'aare-ai-ontologies-{stage}'
    ontologies_dir = Path(__file__).parent.parent / 'ontologies'
    
    print(f"Uploading ontologies to s3://{bucket_name}")
    
    # Upload each ontology file
    for ontology_file in ontologies_dir.glob('*.json'):
        with open(ontology_file, 'r') as f:
            ontology = json.load(f)
        
        name = ontology.get('name', ontology_file.stem)
        version = ontology.get('version', '1.0.0')
        
        # Upload to versioned path
        versioned_key = f'ontologies/{name}/v{version}/ontology.json'
        s3.put_object(
            Bucket=bucket_name,
            Key=versioned_key,
            Body=json.dumps(ontology, indent=2),
            ContentType='application/json'
        )
        print(f"✓ Uploaded {name} v{version}")
        
        # Also upload as latest
        latest_key = f'ontologies/{name}/latest/ontology.json'
        s3.put_object(
            Bucket=bucket_name,
            Key=latest_key,
            Body=json.dumps(ontology, indent=2),
            ContentType='application/json'
        )
        print(f"✓ Updated latest for {name}")
    
    print("✅ All ontologies uploaded successfully")


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Upload ontologies to S3')
    parser.add_argument('--stage', default='dev', help='Deployment stage')
    parser.add_argument('--region', default='us-east-1', help='AWS region')
    parser.add_argument('--profile', default='default', help='AWS profile')
    
    args = parser.parse_args()
    upload_ontologies(args.stage, args.region, args.profile)