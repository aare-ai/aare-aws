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
