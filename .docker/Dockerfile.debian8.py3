FROM debian:jessie-backports

ENV LANG C.UTF-8
ENV PYTHONDONTWRITEBYTECODE 1
ENV CI true

RUN echo "deb http://ppa.launchpad.net/lazka/dumpingplace/ubuntu xenial main" >> /etc/apt/sources.list

RUN apt-key adv --keyserver keyserver.ubuntu.com --recv-keys 5806C7C4

RUN apt-get update

RUN apt-get install -y \
    quodlibet-py3 \
    exfalso-py3

RUN apt-get install --no-install-recommends -y \
    python3-polib \
    python3-pytest \
    python3-pip \
    python3-setuptools \
    xvfb \
    gettext \
    intltool \
    libxine2 \
    dbus-x11 \
    curl

RUN pip3 install --upgrade pycodestyle pyflakes xvfbwrapper coverage

RUN useradd -ms /bin/bash user

USER user
WORKDIR /home/user
