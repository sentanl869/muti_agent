FROM node:latest

RUN \
    sed -i 's#http://deb\.debian\.org#https://mirrors.tuna.tsinghua.edu.cn#g' /etc/apt/sources.list.d/debian.sources && \
    apt-get update && \
    apt-get install -y --no-install-recommends python3-pip && \
    pip config set global.extra-index-url 'https://mirrors.tuna.tsinghua.edu.cn/pypi/web/simple' && \
    pip install --no-cache-dir --break-system-packages uv && \
    mkdir -p /etc/uv && \
    echo '[[index]]\nurl = "https://mirrors.tuna.tsinghua.edu.cn/pypi/web/simple/"\ndefault = true' > /etc/uv/uv.toml && \
    npm config set registry https://registry.npmmirror.com/ && \
    rm -rf /var/lib/apt/lists/* /tmp/* /var/tmp/*
