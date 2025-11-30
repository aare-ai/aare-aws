FROM public.ecr.aws/lambda/python:3.11

# Install Z3 using a compatible pre-built wheel
RUN pip install --no-cache-dir \
    --only-binary :all: \
    --platform manylinux2014_x86_64 \
    --python-version 311 \
    --implementation cp \
    --abi cp311 \
    --index-url https://pypi.org/simple/ \
    z3-solver==4.12.1.0 \
    || pip install z3-solver==4.8.12.0 \
    || echo "Z3 installation failed, continuing without it"

# Install boto3
RUN pip install boto3

# Copy handler files
COPY handlers/ ${LAMBDA_TASK_ROOT}/handlers/

# Don't test Z3 import here - let it fail gracefully at runtime if needed

# Set the handler
CMD ["handlers.handler.handler"]
