FROM nginxinc/nginx-unprivileged

USER root
RUN apt update && \
    apt install -y wget procps htop less iputils-ping && \
    rm -R /var/cache/apt /var/lib/apt/lists/*

# id for dstn @ NERSC
ARG UID=44591
ARG USERNAME=dstn

# The chowns and chmods are from:
# From https://github.com/nginxinc/docker-nginx-unprivileged/blob/main/stable/debian/Dockerfile#L122
RUN echo "cosmo:x:58191" >> /etc/group \
 && echo "desi:x:58102" >> /etc/group \
 && echo "$USERNAME:x:$UID" >> /etc/group \
 && echo "$USERNAME:x:$UID:$UID:$USERNAME:/app:/bin/bash" >> /etc/passwd \
 && chown -R $UID:0 /var/cache/nginx \
 && chmod -R g+w /var/cache/nginx \
 && chown -R $UID:0 /etc/nginx \
 && chmod -R g+w /etc/nginx

USER $UID
