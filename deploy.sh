cat > Dockerfile.z3 << 'EOF'
# Build stage - using full Python image with build tools
FROM python:3.11-slim as builder

# Install build dependencies for Z3
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    cmake \
    make \
    && rm -rf /var/lib/apt/lists/*

# Install Z3 in the builder stage
RUN pip install --no-cache-dir z3-solver

# Runtime stage - Lambda image
FROM public.ecr.aws/lambda/python:3.11

# Copy Z3 from builder to Lambda runtime
COPY --from=builder /usr/local/lib/python3.11/site-packages/ /var/lang/lib/python3.11/site-packages/

# Install boto3 (already in Lambda but let's be explicit)
RUN pip install boto3

# Copy handler files
COPY handlers/ ${LAMBDA_TASK_ROOT}/handlers/

# Test that Z3 imports correctly
RUN python -c "from z3 import *; print('Z3 imported successfully')"

# Set the handler
CMD ["handlers.handler.handler"]
EOF

# Build the image with Z3
echo "Building Docker image with Z3..."
docker build -f Dockerfile.z3 -t aare-ai-z3 .

# Tag it for ECR
docker tag aare-ai-z3:latest 596626989349.dkr.ecr.us-west-2.amazonaws.com/aare-ai:prod-z3

# Push to ECR
echo "Pushing to ECR..."
docker push 596626989349.dkr.ecr.us-west-2.amazonaws.com/aare-ai:prod-z3

# Update Lambda function
echo "Updating Lambda function..."
aws lambda update-function-code \
    --function-name aare-ai-prod \
    --image-uri 596626989349.dkr.ecr.us-west-2.amazonaws.com/aare-ai:prod-z3 \
    --region us-west-2

# Wait for update to complete
echo "Waiting for Lambda update to complete..."
aws lambda wait function-updated \
    --function-name aare-ai-prod \
    --region us-west-2

echo "✅ Deployment complete! Testing the API..."

# Test the API
curl -X POST https://lofeorzpeh.execute-api.us-west-2.amazonaws.com/prod/verify \
  -H "Content-Type: application/json" \
  -d '{
    "llm_output": "Approved! DTI is 35%",
    "ontology": "mortgage-compliance-v1"
  }'
