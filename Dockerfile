FROM ubuntu AS common
# Base configuration for all environments
RUN apt-get update \
    && apt-get install --no-install-recommends -y \
    python3-pip \
    git \
    python3-dev \
    build-essential \
    python-is-python3 \
    && apt-get autoremove \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Set environment variable for hnswlib
ENV HNSWLIB_NO_NATIVE=1

# Install project dependencies
COPY requirements.txt /tmp/
RUN pip install --break-system-packages -r /tmp/requirements.txt

# Install additional dependencies for CrewAI
RUN pip install --break-system-packages \
    duckduckgo-search \
    tavily-python \
    beautifulsoup4 \
    crewai-tools

# Fix the Manager agent tools issue
RUN sed -i 's/raise Exception("Manager agent should not have tools")/#raise Exception("Manager agent should not have tools")/g' /usr/local/lib/python3.12/dist-packages/crewai/crew.py

FROM common AS dev
# Development environment with additional debugging tools
RUN apt-get update \
    && apt-get install --no-install-recommends -y \
    curl \
    openssh-client \
    sudo \
    vim \
    nano \
    && apt-get autoremove \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Copy application code for development
COPY . /app
WORKDIR /app
ENV PYTHONPATH=/app

FROM common AS prod
# Production environment setup
COPY . /app
# Remove development configurations
RUN rm -rf /app/.devcontainer /app/.cursor
# Set permissions (using 777 as per reference, though 755 might be more secure)
RUN chmod -R 777 /app
WORKDIR /app
# Set environment variables
ENV PYTHONPATH=/app
# Custom LLM environment variables will be provided at runtime through env file

# Run the application
#CMD ["python", "/app/src/snl_poc/main.py"]

CMD ["uvicorn", "src.snl_poc.api:app", "--host", "0.0.0.0", "--port", "8000"]