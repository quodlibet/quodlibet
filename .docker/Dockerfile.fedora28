FROM fedora:28

ENV LANG C.UTF-8
ENV PYTHONDONTWRITEBYTECODE 1
ENV CI true

RUN dnf -y install dnf-plugins-core
RUN dnf -y config-manager --add-repo \
    https://download.opensuse.org/repositories/home:lazka0:ql-unstable/Fedora_28/home:lazka0:ql-unstable.repo

RUN dnf -y install \
    quodlibet \
    python3-polib \
    python3-setuptools \
    python3-pytest \
    python3-pip \
    which \
    xorg-x11-server-Xvfb \
    git \
    curl \
    dbus-x11 \
    gdb \
    gettext \
    && dnf clean all

RUN pip3 install --upgrade \
    pycodestyle \
    pyflakes \
    xvfbwrapper \
    coverage \
    pytest-faulthandler

ARG HOST_USER_ID=5555
ENV HOST_USER_ID ${HOST_USER_ID}
RUN useradd -u $HOST_USER_ID -ms /bin/bash user

USER user
WORKDIR /home/user
