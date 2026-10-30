FROM legacysurvey/legacypipe:DR11.2.0

RUN apt update
RUN apt install -y --no-install-recommends \
    iputils-ping \
    rsync \
    subversion \
    screen \
    iotop \
    dnsutils

# Pip installs
RUN for x in \
    Django \
    pillow \
    psutil \
    psycopg2-binary \
    uwsgi \
    requests \
    tzdata \
    numba \
    bokeh \
    uwsgitop \
    ; do \
    python3 -m pip install --no-cache --break-system-packages $x; \
    done;

ADD https://github.com/che0/uwping/releases/download/14.0/uwping /usr/local/bin/uwping
RUN chmod +x /usr/local/bin/uwping

#RUN mkdir /app
WORKDIR /app

ENV PYTHONPATH=/usr/local/lib/python

RUN mkdir /app/viewer
COPY entry.sh /app

RUN echo "cosmo:x:58191" >> /etc/group
RUN echo "desi:x:58102" >> /etc/group
RUN echo "dstn:x:44591" >> /etc/group
RUN echo "m3592:x:91598" >> /etc/group
RUN echo "dstn:x:44591:44591:Dustin:/app:/bin/bash" >> /etc/passwd
