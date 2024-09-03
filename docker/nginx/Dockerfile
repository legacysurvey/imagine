FROM nginxinc/nginx-unprivileged

USER root
RUN apt update && \
    apt install -y wget procps htop less iputils-ping && \
    rm -R /var/cache/apt /var/lib/apt/lists/*

# id for dstn @ NERSC
ARG UID=44591

RUN echo "cosmo:x:58191" >> /etc/group
RUN echo "desi:x:58102" >> /etc/group
RUN echo "dstn:x:44591" >> /etc/group
RUN echo "dstn:x:44591:44591:Dustin:/app:/bin/bash" >> /etc/passwd

# From https://github.com/nginxinc/docker-nginx-unprivileged/blob/main/stable/debian/Dockerfile#L122
RUN chown -R $UID:0 /var/cache/nginx \
 && chmod -R g+w /var/cache/nginx \
 && chown -R $UID:0 /etc/nginx \
 && chmod -R g+w /etc/nginx

USER $UID
