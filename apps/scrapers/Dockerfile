FROM python:3.11-slim

# Set working directory to the scrapers root inside the container
WORKDIR /app/apps/scrapers

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Create the virtual environment inside the container
RUN python -m venv .venv
ENV PATH="/app/apps/scrapers/.venv/bin:$PATH"

# Copy package configurations
COPY apps/scrapers/requirements.txt* ./

# Install Python dependencies
RUN if [ -f ./requirements.txt ]; then \
        .venv/bin/pip install --no-cache-dir -r ./requirements.txt; \
    else \
        .venv/bin/pip install --no-cache-dir redis bullmq trafilatura requests beautifulsoup4 dotenv pydantic tenacity; \
    fi

# Copy the core Python code
COPY apps/scrapers/src ./src

# FIX: Copy scripts from the top-level server context where they actually live
COPY scripts /app/scripts
RUN chmod +x /app/scripts/*.sh

ENV PYTHONUNBUFFERED=1

# Execute using the correct relative path inside the container workspace
CMD ["/bin/bash", "/app/scripts/worker.sh"]