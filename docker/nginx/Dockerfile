FROM nginxinc/nginx-unprivileged

USER root
RUN apt update && \
    apt install -y wget procps htop less iputils-ping && \
    rm -R /var/cache/apt /var/lib/apt/lists/*

USER nginx
