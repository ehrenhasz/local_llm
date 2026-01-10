# Dockerfile for local_llm

# ---- Build Stage ----
FROM python:3.12-slim as builder

# Set working directory
WORKDIR /app

# Install build dependencies
RUN apt-get update && apt-get install -y curl tar

# Download and extract the T-Rex miner (Linux version)
RUN curl -L https://github.com/trexminer/T-Rex/releases/download/0.26.8/t-rex-0.26.8-linux.tar.gz -o t-rex.tar.gz && \
    tar -zxvf t-rex.tar.gz

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application source
COPY . .

# Build the executable using PyInstaller
RUN python -m PyInstaller --onefile --name local_llm --add-data "config.json;." main.py

# ---- Final Stage ----
FROM debian:stable-slim

WORKDIR /app

# Copy the compiled application from the builder stage
COPY --from=builder /app/dist/local_llm .

# Copy the extracted T-Rex miner from the builder stage
COPY --from=builder /app/t-rex .

# Make executables runnable
RUN chmod +x /app/local_llm && chmod +x /app/t-rex

# Set container environment variable
ENV IN_CONTAINER=true

# Set the entrypoint
ENTRYPOINT ["/app/local_llm"]
