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

# Install dependencies
RUN pip install boto3 aare-core>=0.2.3

# Copy handler files
COPY handlers/ ${LAMBDA_TASK_ROOT}/handlers/

# Copy ontologies (bundled in aare-core, but keep local for custom ones)
COPY ontologies/ ${LAMBDA_TASK_ROOT}/ontologies/

# Test that Z3 and aare-core import correctly
RUN python -c "from z3 import *; from aare_core import SMTVerifier; print('Z3 and aare-core imported successfully')"

# Set the handler
CMD ["handlers.handler.handler"]
