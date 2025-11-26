#!/usr/bin/env python3
"""
Test the deployed aare.ai API
"""

import os
import sys
import json
import requests
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

API_ENDPOINT = os.getenv('API_ENDPOINT')
API_KEY = os.getenv('API_KEY')

if not API_ENDPOINT or not API_KEY:
    print("❌ Please set API_ENDPOINT and API_KEY in .env file")
    sys.exit(1)

print(f"🔧 Testing API at {API_ENDPOINT}")


def test_verification():
    """Test the verification endpoint"""
    print("\n📝 Testing verification endpoint...")
    
    # Test data - should pass verification
    test_data = {
        "content": {
            "decision": "approve",
            "amount": 50000,
            "credit_score": 750,
            "debt_to_income_ratio": 0.35,
            "loan_to_value_ratio": 0.75,
            "income_verified": True
        },
        "ontology": "fair-lending-v1",
        "rules": ["max_dti_ratio", "min_credit_score"]
    }
    
    response = requests.post(
        f"{API_ENDPOINT}/verify",
        headers={"x-api-key": API_KEY},
        json=test_data
    )
    
    if response.status_code == 200:
        result = response.json()
        print(f"✅ Verification successful: {result['verified']}")
        print(f"   Execution time: {result.get('execution_time_ms')}ms")
        if result.get('violations'):
            print(f"   Violations: {result['violations']}")
    else:
        print(f"❌ Verification failed: {response.status_code}")
        print(f"   Error: {response.text}")
    
    return response.status_code == 200


def test_verification_with_violations():
    """Test verification that should fail"""
    print("\n📝 Testing verification with violations...")
    
    # Test data - should fail verification
    test_data = {
        "content": {
            "decision": "approve",
            "amount": 150000,  # Exceeds typical limits
            "credit_score": 550,  # Below minimum
            "debt_to_income_ratio": 0.55,  # Above maximum
            "loan_to_value_ratio": 0.95
        },
        "ontology": "fair-lending-v1"
    }
    
    response = requests.post(
        f"{API_ENDPOINT}/verify",
        headers={"x-api-key": API_KEY},
        json=test_data
    )
    
    if response.status_code == 200:
        result = response.json()
        print(f"✅ Request successful")
        print(f"   Verified: {result['verified']}")
        print(f"   Violations found: {len(result.get('violations', []))}")
        for violation in result.get('violations', [])[:3]:  # Show first 3
            print(f"   - {violation.get('constraint')}: {violation.get('description')}")
    else:
        print(f"❌ Request failed: {response.status_code}")
        print(f"   Error: {response.text}")
    
    return response.status_code == 200


def test_list_ontologies():
    """Test listing available ontologies"""
    print("\n📚 Testing ontology listing...")
    
    response = requests.get(
        f"{API_ENDPOINT}/ontologies",
        headers={"x-api-key": API_KEY}
    )
    
    if response.status_code == 200:
        result = response.json()
        print(f"✅ Found {result.get('total', 0)} ontologies")
        for ontology in result.get('ontologies', [])[:3]:  # Show first 3
            print(f"   - {ontology.get('name')}: {ontology.get('description')}")
    else:
        print(f"❌ Failed to list ontologies: {response.status_code}")
        print(f"   Error: {response.text}")
    
    return response.status_code == 200


def test_get_verification():
    """Test retrieving a verification by ID"""
    print("\n🔍 Testing verification retrieval...")
    
    # First create a verification
    test_data = {
        "content": {"amount": 25000, "credit_score": 700},
        "ontology": "fair-lending-v1"
    }
    
    response = requests.post(
        f"{API_ENDPOINT}/verify",
        headers={"x-api-key": API_KEY},
        json=test_data
    )
    
    if response.status_code == 200:
        verification_id = response.json().get('verification_id')
        
        # Now retrieve it
        response = requests.get(
            f"{API_ENDPOINT}/verification/{verification_id}",
            headers={"x-api-key": API_KEY}
        )
        
        if response.status_code == 200:
            result = response.json()
            print(f"✅ Retrieved verification {verification_id}")
            print(f"   Status: {result.get('status')}")
            print(f"   Ontology: {result.get('ontology')}")
        else:
            print(f"❌ Failed to retrieve verification: {response.status_code}")
    else:
        print(f"❌ Failed to create test verification: {response.status_code}")
    
    return response.status_code == 200


def main():
    """Run all tests"""
    print("=" * 50)
    print("aare.ai API Test Suite")
    print("=" * 50)
    
    tests = [
        ("Basic Verification", test_verification),
        ("Verification with Violations", test_verification_with_violations),
        ("List Ontologies", test_list_ontologies),
        ("Get Verification", test_get_verification)
    ]
    
    passed = 0
    failed = 0
    
    for name, test_func in tests:
        try:
            if test_func():
                passed += 1
            else:
                failed += 1
        except Exception as e:
            print(f"❌ Test '{name}' failed with exception: {e}")
            failed += 1
    
    print("\n" + "=" * 50)
    print(f"Results: {passed} passed, {failed} failed")
    
    if failed == 0:
        print("✅ All tests passed!")
        return 0
    else:
        print(f"❌ {failed} test(s) failed")
        return 1


if __name__ == '__main__':
    sys.exit(main())