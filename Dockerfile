FROM public.ecr.aws/lambda/python:3.11

# Install boto3
RUN pip install boto3

# Copy all handler files
COPY handlers/ ${LAMBDA_TASK_ROOT}/handlers/

# Set Python path to include task root
ENV PYTHONPATH="${LAMBDA_TASK_ROOT}"

# Verify files are copied
RUN ls -la ${LAMBDA_TASK_ROOT}/handlers/ && \
    python -c "import sys; print('Python path:', sys.path)"

# Set the handler
CMD ["handlers.handler.handler"]
