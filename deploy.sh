#!/bin/bash
# =============================================================================
# Deploy aare-ai Lambda function
# =============================================================================
# This is the PRIMARY deployment method for production.
#
# Architecture:
#   CloudFront (api.aare.ai) -> API Gateway (lw0t1qp1lh) -> Lambda (aare-ai-prod)
#
# AWS Resources:
#   - Lambda: aare-ai-prod
#   - API Gateway: lw0t1qp1lh (prod-aare-ai)
#   - CloudFront: E2AMMH8UWJ3VCF (api.aare.ai)
#   - S3: aare-ai-ontologies-prod, aare-ai-deployments-us-west-2
#   - DynamoDB: aare-ai-verifications-prod
#
# Usage:
#   ./deploy.sh                    # Deploy Lambda code
#   AARE_API_KEY=xxx ./deploy.sh   # Deploy and test
# =============================================================================

set -e

FUNCTION_NAME="aare-ai-prod"
REGION="us-west-2"
ECR_REPO="596626989349.dkr.ecr.us-west-2.amazonaws.com/aare-ai"
API_GATEWAY_ID="lw0t1qp1lh"
CLOUDFRONT_ID="E2AMMH8UWJ3VCF"

# Check current package type
PACKAGE_TYPE=$(aws lambda get-function-configuration --function-name $FUNCTION_NAME --region $REGION --query 'PackageType' --output text 2>/dev/null || echo "Unknown")

echo "Current Lambda package type: $PACKAGE_TYPE"

if [ "$PACKAGE_TYPE" == "Image" ]; then
    echo "Deploying as Container Image..."

    # Build the image
    echo "Building Docker image..."
    docker build -f Dockerfile.z3 -t aare-ai-z3 .

    # Tag for ECR
    docker tag aare-ai-z3:latest ${ECR_REPO}:prod-z3

    # Login to ECR
    aws ecr get-login-password --region $REGION | docker login --username AWS --password-stdin ${ECR_REPO}

    # Push to ECR
    echo "Pushing to ECR..."
    docker push ${ECR_REPO}:prod-z3

    # Update Lambda
    echo "Updating Lambda function..."
    aws lambda update-function-code \
        --function-name $FUNCTION_NAME \
        --image-uri ${ECR_REPO}:prod-z3 \
        --region $REGION > /dev/null
else
    echo "Deploying as ZIP package..."

    # Clean up
    rm -rf lambda_package lambda_package.zip
    mkdir -p lambda_package

    # Use Docker to install packages for Amazon Linux 2 (Lambda runtime)
    # Note: z3-solver has pre-built wheels for manylinux, which work on Lambda
    echo "Installing dependencies in Lambda-compatible environment..."
    docker run --rm --entrypoint "" \
        -v "$(pwd)/lambda_package:/package" \
        -v "$(pwd)/requirements.txt:/requirements.txt" \
        --platform linux/amd64 \
        python:3.11-slim \
        /bin/bash -c "
            pip install --upgrade pip --root-user-action=ignore -q
            pip install --no-cache-dir --platform manylinux2014_x86_64 --only-binary=:all: z3-solver -t /package --root-user-action=ignore -q
            pip install --no-cache-dir -r /requirements.txt -t /package --root-user-action=ignore -q
            chmod -R 755 /package
        "

    # Copy handler files
    cp -r handlers lambda_package/

    # Copy ontologies
    cp -r ontologies lambda_package/

    # Create the ZIP
    echo "Creating ZIP package..."
    cd lambda_package
    zip -rq9 ../lambda_package.zip .
    cd ..

    # Check size
    ZIP_SIZE=$(stat -f%z lambda_package.zip 2>/dev/null || stat -c%s lambda_package.zip)
    ZIP_SIZE_MB=$((ZIP_SIZE / 1024 / 1024))
    echo "Package size: ${ZIP_SIZE_MB}MB"

    if [ $ZIP_SIZE -gt 52428800 ]; then
        echo "Package too large for direct upload (>50MB), using S3..."
        S3_BUCKET="aare-ai-deployments-${REGION}"

        # Create bucket if it doesn't exist
        aws s3 mb s3://${S3_BUCKET} --region $REGION 2>/dev/null || true

        # Upload to S3
        aws s3 cp lambda_package.zip s3://${S3_BUCKET}/lambda_package.zip --quiet

        # Update Lambda from S3
        echo "Updating Lambda function..."
        aws lambda update-function-code \
            --function-name $FUNCTION_NAME \
            --s3-bucket ${S3_BUCKET} \
            --s3-key lambda_package.zip \
            --region $REGION > /dev/null
    else
        # Direct upload
        echo "Updating Lambda function..."
        aws lambda update-function-code \
            --function-name $FUNCTION_NAME \
            --zip-file fileb://lambda_package.zip \
            --region $REGION > /dev/null
    fi
fi

# Wait for update to complete
echo "Waiting for Lambda update to complete..."
aws lambda wait function-updated \
    --function-name $FUNCTION_NAME \
    --region $REGION

# Ensure handler and environment are configured correctly
echo "Updating Lambda configuration..."
aws lambda update-function-configuration \
    --function-name $FUNCTION_NAME \
    --handler handlers.handler.handler \
    --environment "Variables={ONTOLOGY_DIR=/var/task/ontologies}" \
    --region $REGION > /dev/null

aws lambda wait function-updated \
    --function-name $FUNCTION_NAME \
    --region $REGION

echo ""
echo "✅ Deployment complete!"
echo ""

# Test the API (requires AARE_API_KEY environment variable)
if [ -n "$AARE_API_KEY" ]; then
    echo "Testing the API..."
    curl -s -X POST https://api.aare.ai/verify \
      -H "Content-Type: application/json" \
      -H "x-api-key: $AARE_API_KEY" \
      -d '{
        "llm_output": "Approved! DTI is 35%",
        "ontology": "mortgage-compliance-v1"
      }' | python3 -m json.tool 2>/dev/null || echo "(response above)"
else
    echo "Skipping API test (set AARE_API_KEY to enable)"
fi
