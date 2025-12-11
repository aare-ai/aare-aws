# Lambda image with all dependencies
FROM public.ecr.aws/lambda/python:3.11

# Install all dependencies including Z3 directly
COPY requirements.txt .
RUN pip install --no-cache-dir z3-solver
RUN pip install --no-cache-dir -r requirements.txt

# Copy handler files
COPY handlers/ ${LAMBDA_TASK_ROOT}/handlers/

# Copy ontologies (deployed separately from aare-core package)
COPY ontologies/ ${LAMBDA_TASK_ROOT}/ontologies/

# Set ontology directory environment variable
ENV ONTOLOGY_DIR=${LAMBDA_TASK_ROOT}/ontologies

# Test that imports work correctly
RUN python -c "from z3 import *; print('Z3 imported successfully')"
RUN python -c "from aare_core import OntologyLoader, LLMParser, SMTVerifier; print('aare_core imported successfully')"

# Set the handler
CMD ["handlers.handler.handler"]
