FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    libgl1-mesa-glx \
    libglib2.0-0 \
    libsm6 \
    libxext6 \
    libxrender-dev \
    libgomp1 \
    wget \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY src/ ./src/
COPY setup_venv.sh .
COPY requirements.txt .

# Create non-root user
RUN useradd -m -u 1000 visionvend
USER visionvend

EXPOSE 5000 5001

CMD ["uvicorn", "src.server.app:app", "--host", "0.0.0.0", "--port", "5000"]