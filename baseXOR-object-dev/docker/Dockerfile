FROM nvidia/cuda:12.3.0-runtime-ubuntu22.04

ENV DEBIAN_FRONTEND=noninteractive
ENV PYTHONUNBUFFERED=1

# System dependencies
RUN apt-get update && apt-get install -y \
    python3.10 \
    python3-pip \
    python3-dev \
    git \
    wget \
    curl \
    vim \
    htop \
    net-tools \
    iputils-ping \
    openssh-client \
    build-essential \
    libffi-dev \
    libssl-dev \
    zlib1g-dev \
    libbz2-dev \
    libreadline-dev \
    libsqlite3-dev \
    llvm \
    libncurses5-dev \
    libncursesw5-dev \
    tzdata \
    && rm -rf /var/lib/apt/lists/*

# Install Python packages
RUN pip3 install --no-cache-dir \
    torch==2.1.0 \
    torchvision==0.16.0 \
    torchaudio==2.1.0 \
    numpy \
    pandas \
    scipy \
    scikit-learn \
    transformers==4.35.0 \
    accelerate \
    bitsandbytes \
    xgboost \
    lightgbm \
    catboost \
    pyspark \
    kafka-python \
    redis \
    celery \
    flask \
    fastapi \
    uvicorn \
    docker \
    pynvml \
    nvidia-ml-py3

# Install Ollama for LLM
RUN curl -fsSL https://ollama.ai/install.sh | sh

# Create app directories
RUN mkdir -p /app /data /jmbase /pools /datasets /snapshots /agents

WORKDIR /app

# Copy scripts
COPY scripts/ /app/scripts/
RUN chmod +x /app/scripts/*.sh

# Environment setup
ENV PATH="/app/scripts:$PATH"
ENV JMK_BASE="/jmbase"
ENV DATA_DIR="/data"
ENV POOL_NAME="baseXOR_POOL"

EXPOSE 8080 11434

CMD ["/bin/bash"]
