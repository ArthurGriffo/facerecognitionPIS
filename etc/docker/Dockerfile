# Use CUDA base image
FROM nvidia/cuda:11.2.2-cudnn8-devel AS tf

# Set non-interactive mode for apt
ENV DEBIAN_FRONTEND=noninteractive

RUN apt-key adv --fetch-keys https://developer.download.nvidia.com/compute/cuda/repos/ubuntu2004/x86_64/3bf863cc.pub

# Install dependencies
RUN apt-get update -y && apt-get install -y --no-install-recommends \
    git \
    cmake \
    libsm6 \
    libxext6 \
    libxrender-dev \
    python3 \
    python3-pip \
    python3-venv \
    python3-dev \
    python3-numpy \
    gcc \
    build-essential \
    gfortran \
    wget \
    curl \
    graphicsmagick \
    libgraphicsmagick1-dev \
    libatlas-base-dev \
    libavcodec-dev \
    libavformat-dev \
    libgtk2.0-dev \
    libjpeg-dev \
    liblapack-dev \
    libswscale-dev \
    pkg-config \
    software-properties-common \
    libglib2.0-0 \
    libgl1-mesa-glx \
    zip && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/* /tmp/* /var/tmp/*

# Clone and build dlib
RUN git clone https://github.com/davisking/dlib.git && \
    cd dlib && \
    mkdir build && \
    cd build && \
    cmake -D DLIB_USE_CUDA=1 -D USE_AVX_INSTRUCTIONS=1 ../ && \
    make && \
    cd ../ && \
    python3 setup.py install && \
    rm -rf /dlib

# Install Python requirements
COPY requirements.txt .
RUN pip3 install --no-cache-dir -r requirements.txt && \
    pip3 install --no-cache-dir --upgrade protobuf

# Copy project files
WORKDIR /opt/is-face-recognition/
COPY src src/
COPY setup.py .
COPY etc/conf/options.json /conf/options.json
COPY etc/conf/persons.pkl /conf/persons.pkl

# Install project
RUN pip3 install --no-cache-dir . && \
    pip3 install --no-cache-dir --upgrade protobuf

# Set working directory for runtime
WORKDIR /opt/is-face-recognition/src/is_face_recognition

# Default command
CMD ["bash"]