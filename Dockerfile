# Base Image
FROM python:3.12.7

# Set the working directory in the container
WORKDIR /opt/genpod

# Copy requirements file first to leverage Docker cache
COPY requirements.txt .

# Install system dependencies and Python packages
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    make \
    less \
    sqlite3 && \
    rm -rf /var/lib/apt/lists/* && \
    pip install --no-cache-dir -r requirements.txt && \
    pip install --no-cache-dir semgrep==1.93.0

# Copy the rest of the application files
COPY . .

# Default command to keep the container running
CMD ["sleep", "infinity"]
