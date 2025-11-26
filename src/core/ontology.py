"""
Ontology loader for managing verification rules
Handles OWL and JSON format ontologies
"""

import json
import boto3
from typing import Dict, Any, List, Optional
from dataclasses import dataclass
import logging
from botocore.exceptions import ClientError
import hashlib
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)


@dataclass
class OntologyMetadata:
    """Metadata for an ontology"""
    name: str
    version: str
    description: str
    created_at: str
    updated_at: str
    author: str
    domain: str
    hash: str
    
    
class OntologyLoader:
    """
    Loads and manages ontologies from S3
    Provides caching and versioning support
    """
    
    def __init__(self, s3_client: boto3.client, bucket_name: str):
        """
        Initialize ontology loader
        
        Args:
            s3_client: Boto3 S3 client
            bucket_name: S3 bucket containing ontologies
        """
        self.s3 = s3_client
        self.bucket = bucket_name
        self._cache = {}
        self._cache_ttl = timedelta(minutes=15)
        self._cache_timestamps = {}
    
    def load(self, ontology_name: str, version: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """
        Load ontology from S3 with caching
        
        Args:
            ontology_name: Name of the ontology
            version: Specific version (optional, defaults to latest)
            
        Returns:
            Parsed ontology dictionary or None if not found
        """
        cache_key = f"{ontology_name}:{version or 'latest'}"
        
        # Check cache
        if self._is_cached(cache_key):
            logger.info(f"Loading ontology {cache_key} from cache")
            return self._cache[cache_key]
        
        try:
            # Construct S3 key
            if version:
                s3_key = f"ontologies/{ontology_name}/v{version}/ontology.json"
            else:
                s3_key = f"ontologies/{ontology_name}/latest/ontology.json"
            
            # Download from S3
            logger.info(f"Loading ontology from s3://{self.bucket}/{s3_key}")
            response = self.s3.get_object(Bucket=self.bucket, Key=s3_key)
            content = response['Body'].read()
            
            # Parse ontology
            ontology = json.loads(content)
            
            # Validate structure
            if not self._validate_ontology(ontology):
                logger.error(f"Invalid ontology structure for {ontology_name}")
                return None
            
            # Add metadata
            ontology['_metadata'] = {
                'loaded_at': datetime.utcnow().isoformat(),
                's3_key': s3_key,
                'etag': response.get('ETag', ''),
                'size_bytes': len(content),
                'cache_key': cache_key
            }
            
            # Cache it
            self._cache[cache_key] = ontology
            self._cache_timestamps[cache_key] = datetime.utcnow()
            
            return ontology
            
        except ClientError as e:
            if e.response['Error']['Code'] == 'NoSuchKey':
                logger.warning(f"Ontology not found: {ontology_name}")
            else:
                logger.error(f"Error loading ontology {ontology_name}: {str(e)}")
            return None
        except json.JSONDecodeError as e:
            logger.error(f"Invalid JSON in ontology {ontology_name}: {str(e)}")
            return None
        except Exception as e:
            logger.error(f"Unexpected error loading ontology {ontology_name}: {str(e)}")
            return None
    
    def list_ontologies(self) -> List[Dict[str, str]]:
        """
        List all available ontologies
        
        Returns:
            List of ontology metadata
        """
        try:
            # List objects in ontologies prefix
            response = self.s3.list_objects_v2(
                Bucket=self.bucket,
                Prefix='ontologies/',
                Delimiter='/'
            )
            
            ontologies = []
            for prefix in response.get('CommonPrefixes', []):
                # Extract ontology name from prefix
                name = prefix['Prefix'].split('/')[-2]
                
                # Try to load metadata
                metadata = self._load_metadata(name)
                if metadata:
                    ontologies.append({
                        'name': name,
                        'version': metadata.get('version', '1.0.0'),
                        'description': metadata.get('description', ''),
                        'domain': metadata.get('domain', 'general'),
                        'author': metadata.get('author', 'unknown')
                    })
                else:
                    ontologies.append({
                        'name': name,
                        'version': 'unknown',
                        'description': 'No metadata available',
                        'domain': 'unknown',
                        'author': 'unknown'
                    })
            
            return ontologies
            
        except ClientError as e:
            logger.error(f"Error listing ontologies: {str(e)}")
            return []
    
    def upload_ontology(self, name: str, ontology: Dict[str, Any], 
                       author: str = 'unknown') -> bool:
        """
        Upload a new ontology or version
        
        Args:
            name: Ontology name
            ontology: Ontology definition
            author: Author name
            
        Returns:
            Success boolean
        """
        try:
            # Validate ontology
            if not self._validate_ontology(ontology):
                logger.error("Invalid ontology structure")
                return False
            
            # Add metadata if not present
            if 'metadata' not in ontology:
                ontology['metadata'] = {}
            
            ontology['metadata'].update({
                'name': name,
                'author': author,
                'uploaded_at': datetime.utcnow().isoformat(),
                'hash': self._calculate_hash(ontology)
            })
            
            # Determine version
            version = ontology.get('version', '1.0.0')
            
            # Upload to S3
            s3_key = f"ontologies/{name}/v{version}/ontology.json"
            self.s3.put_object(
                Bucket=self.bucket,
                Key=s3_key,
                Body=json.dumps(ontology, indent=2),
                ContentType='application/json',
                Metadata={
                    'author': author,
                    'version': version
                }
            )
            
            # Also update latest
            latest_key = f"ontologies/{name}/latest/ontology.json"
            self.s3.put_object(
                Bucket=self.bucket,
                Key=latest_key,
                Body=json.dumps(ontology, indent=2),
                ContentType='application/json'
            )
            
            # Clear cache for this ontology
            self._clear_cache(name)
            
            logger.info(f"Successfully uploaded ontology {name} v{version}")
            return True
            
        except Exception as e:
            logger.error(f"Error uploading ontology {name}: {str(e)}")
            return False
    
    def validate_against_ontology(self, ontology: Dict[str, Any], 
                                 data: Dict[str, Any]) -> List[str]:
        """
        Quick validation check against ontology rules
        
        Args:
            ontology: Ontology definition
            data: Data to validate
            
        Returns:
            List of validation errors (empty if valid)
        """
        errors = []
        
        for rule in ontology.get('rules', []):
            if rule.get('severity') == 'error':
                # This is a simplified check - full validation happens in verifier
                required_vars = rule.get('variables', [])
                for var in required_vars:
                    if var not in data:
                        errors.append(f"Missing required variable: {var}")
        
        return errors
    
    def _validate_ontology(self, ontology: Dict[str, Any]) -> bool:
        """Validate ontology structure"""
        required_fields = ['name', 'version', 'rules']
        
        for field in required_fields:
            if field not in ontology:
                logger.error(f"Ontology missing required field: {field}")
                return False
        
        # Validate rules structure
        rules = ontology.get('rules', [])
        if not isinstance(rules, list):
            logger.error("Ontology rules must be a list")
            return False
        
        for i, rule in enumerate(rules):
            if not isinstance(rule, dict):
                logger.error(f"Rule {i} must be a dictionary")
                return False
            
            if 'name' not in rule or 'expression' not in rule:
                logger.error(f"Rule {i} missing name or expression")
                return False
        
        return True
    
    def _is_cached(self, cache_key: str) -> bool:
        """Check if cache entry is valid"""
        if cache_key not in self._cache:
            return False
        
        timestamp = self._cache_timestamps.get(cache_key)
        if not timestamp:
            return False
        
        if datetime.utcnow() - timestamp > self._cache_ttl:
            # Cache expired
            del self._cache[cache_key]
            del self._cache_timestamps[cache_key]
            return False
        
        return True
    
    def _clear_cache(self, ontology_name: str):
        """Clear cache entries for an ontology"""
        keys_to_clear = [k for k in self._cache.keys() if k.startswith(f"{ontology_name}:")]
        for key in keys_to_clear:
            del self._cache[key]
            if key in self._cache_timestamps:
                del self._cache_timestamps[key]
    
    def _load_metadata(self, name: str) -> Optional[Dict[str, Any]]:
        """Load ontology metadata file"""
        try:
            response = self.s3.get_object(
                Bucket=self.bucket,
                Key=f"ontologies/{name}/metadata.json"
            )
            return json.loads(response['Body'].read())
        except:
            return None
    
    def _calculate_hash(self, ontology: Dict[str, Any]) -> str:
        """Calculate hash of ontology for versioning"""
        # Remove metadata fields that change
        ontology_copy = ontology.copy()
        ontology_copy.pop('metadata', None)
        ontology_copy.pop('_metadata', None)
        
        # Calculate SHA256
        ontology_str = json.dumps(ontology_copy, sort_keys=True)
        return hashlib.sha256(ontology_str.encode()).hexdigest()
