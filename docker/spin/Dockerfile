FROM legacysurvey/legacypipe:DR10.3.7b

RUN apt install -y --no-install-recommends \
    iputils-ping \
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
    ; do \
    python3 -m pip install --no-cache --break-system-packages $x; \
    done;

RUN mkdir /app
WORKDIR /app

ENV PYTHONPATH=/usr/local/lib/python

RUN mkdir /app/viewer
COPY entry.sh /app

ADD https://github.com/che0/uwping/releases/download/14.0/uwping /usr/local/bin/uwping
RUN chmod +x /usr/local/bin/uwping

RUN echo "cosmo:x:58191" >> /etc/group
RUN echo "desi:x:58102" >> /etc/group
RUN echo "dstn:x:44591" >> /etc/group
RUN echo "m3592:x:91598" >> /etc/group
RUN echo "dstn:x:44591:44591:Dustin:/app:/bin/bash" >> /etc/passwd

