FROM ubuntu:20.04
WORKDIR /app
COPY requirements.txt /app/
ENV DEBIAN_FRONTEND=noninteractive
RUN apt -y update && \
  apt install -y apt-utils && \
  apt install -y --no-install-recommends \
    build-essential \
    make pkg-config \
    gcc swig \
    python3 python3-distutils python3-dev python3-pip \
    curl wget \
    git less htop \
    libpcre3 libpcre3-dev libcairo2-dev libnetpbm10-dev netpbm libpng-dev libjpeg-dev zlib1g-dev \
    libbz2-dev libcfitsio-dev wcslib-dev \
  && \
  apt clean
RUN pip install --no-cache-dir -r requirements.txt
RUN pip install -e git+http://github.com/dstndstn/astrometry.net@0.86#egg=astrometry && \
    pip install -e git+https://github.com/dstndstn/tractor.git@dr9.6#egg=tractor
RUN pip install -e git+https://github.com/legacysurvey/legacypipe@DR10.1.0#egg=legacypipe
RUN git clone https://github.com/legacysurvey/imagine.git
RUN cd imagine/viewer && ln -s settings_test.py settings.py
#ENV PS1="[container] \\u@\\h:\\w$ "
#RUN echo "export PS1='[container] \\u@\\h:\\w$ '" >> $HOME/.bashrc
RUN cd imagine && mv data data-orig && ln -s /global/cfs/cdirs/cosmo/webapp/viewer/data .
COPY cutout /usr/local/bin/
RUN chmod 755 /usr/local/bin/cutout
