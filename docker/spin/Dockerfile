FROM ubuntu:22.04

ENV DEBIAN_FRONTEND=noninteractive

RUN apt install -y gpgv && \
    apt -y update && apt install -y apt-utils gpgv && \
    apt install -y --no-install-recommends \
    build-essential \
    make \
    gcc \
    g++ \
    gfortran \
    git \
    ssh \
    file \
    pkg-config \
    wget \
    curl \
    swig \
    netpbm \
    wcslib-dev \
    wcslib-tools \
    zlib1g-dev \
    libbz2-dev \
    libcairo2-dev \
    libcfitsio-dev \
    libcfitsio-bin \
    libgsl-dev \
    libjpeg-dev \
    libnetpbm10-dev \
    libpng-dev \
    libeigen3-dev \
    libgoogle-glog-dev \
    libceres-dev \
    python3-pip \
    python3.10 \
    python3.10-dev \
    iputils-ping \
    dnsutils \
    htop \
    less \
    && apt-get clean && rm -rf /var/lib/apt/lists/* /tmp/* /var/tmp/*

# Pip installs
RUN for x in \
    cython \
    numpy \
    scipy \
    fitsio \
    matplotlib \
    astropy \
    photutils \
    zmq \
    Django \
    pillow \
    psutil \
    psycopg2-binary \
    uwsgi \
    requests \
    ; do \
    python3.10 -m pip install $x; \
    done; \
    rm -R /root/.cache/pip

RUN mkdir /app
WORKDIR /app

# Astrometry.net
RUN git clone http://github.com/dstndstn/astrometry.net.git astrometry \
    && cd astrometry \
    && make \
    && make extra \
    && make py PYTHON=python3.10 \
    && make install INSTALL_DIR=/usr/local PYTHON=python3.10 \
    && make clean

ENV PYTHON=python3.10
# python = python3.10
RUN ln -s /usr/bin/python3.10 /usr/bin/python

# The Tractor
RUN git clone http://github.com/dstndstn/tractor.git tractor \
    && cd tractor \
    && python3.10 setup-cython.py --with-ceres install --home /usr/local \
    && make version && cp tractor/version.py /usr/local/lib/python/tractor/ \
    && rm -R $(find . -name "*.o" -o -name "*.so") \
    && (cd && PYTHONPATH=/usr/local/lib/python python3 -c "import tractor; print(tractor.__version__)")

RUN python3.10 -m pip install --no-cache tzdata

ENV PYTHONPATH=/usr/local/lib/python

RUN mkdir /app/viewer

COPY entry.sh /app
#ENTRYPOINT ["/app/entry.sh"]

#RUN pip install uwsgi-tools
ADD https://github.com/che0/uwping/releases/download/14.0/uwping /usr/local/bin/uwping
RUN chmod +x /usr/local/bin/uwping
