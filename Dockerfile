FROM python:3.11-slim

WORKDIR /app

# Install system dependencies for compilation
RUN apt-get update && apt-get install -y \
    build-essential \
    g++ \
    gcc \
    git \
    && rm -rf /var/lib/apt/lists/*

# Copy project files
COPY . .

# Install Python dependencies
RUN pip install --no-cache-dir -e ".[dev]"

# Create non-root user for security
RUN useradd -m -u 1000 includeguard && \
    chown -R includeguard:includeguard /app

USER includeguard

# Default command: analyze current directory
ENTRYPOINT ["includeguard"]
CMD ["analyze", "."]
