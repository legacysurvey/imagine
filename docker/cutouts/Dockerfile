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
    gfortran libxml2 file \
  && \
  apt clean

RUN wget -nv https://www.mpich.org/static/downloads/3.3/mpich-3.3.tar.gz \
    && tar xzf mpich-3.3.tar.gz \
    && cd mpich-3.3 \
    && ./configure \
    && make -j4 \
    && make install \
    && make clean \
    && cd .. && rm -Rf mpich-3.3
# defaults to installing in /usr/local

# mpi4py / mpicc can't handle -ax=knl or -x=haswell (it compiles using gcc?)
ENV CFLAGS $BASE_CFLAGS
RUN git clone https://github.com/mpi4py/mpi4py.git \
         && (cd mpi4py \
         && python3 setup.py build \
         && python3 setup.py install) \
         && rm -Rf mpi4py

RUN pip install --no-cache-dir -r requirements.txt

RUN git clone https://github.com/dstndstn/astrometry.net.git astrometry \
  && cd astrometry \
  && git checkout 0.94 \
  && make install INSTALL_DIR=/usr/local

RUN git clone https://github.com/dstndstn/tractor.git tractor \
  && cd tractor \
  && git checkout dr10.4 \
  && pip install --install-option="--with-cython" -v .

#RUN pip install -e git+http://github.com/dstndstn/astrometry.net@0.86#egg=astrometry && \
#    pip install -e git+https://github.com/dstndstn/tractor.git@dr9.6#egg=tractor

RUN pip install -e git+https://github.com/legacysurvey/legacypipe@DR10.1.0#egg=legacypipe
RUN git clone https://github.com/legacysurvey/imagine.git
RUN cd imagine/viewer && ln -s settings_test.py settings.py
#ENV PS1="[container] \\u@\\h:\\w$ "
#RUN echo "export PS1='[container] \\u@\\h:\\w$ '" >> $HOME/.bashrc

#RUN cd imagine && mv data data-orig && ln -s /global/cfs/cdirs/cosmo/webapp/viewer/data .
RUN cd imagine && mv data data-orig && ln -s /dvs_ro/cfs/cdirs/cosmo/webapp/viewer/data .

COPY cutout /usr/local/bin/
RUN chmod 755 /usr/local/bin/cutout

ENV PYTHONPATH ${PYTHONPATH}:/usr/local/lib/python:/app/imagine
RUN ln -s /usr/bin/python3 /usr/bin/python

RUN cd imagine && git pull && echo 1
