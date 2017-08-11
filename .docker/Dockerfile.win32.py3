FROM debian:stretch

ENV LANG C.UTF-8
ENV PYTHONDONTWRITEBYTECODE 1
ENV CI true

RUN useradd -ms /bin/bash user

WORKDIR /home/user

RUN dpkg --add-architecture i386

RUN apt-get update

RUN apt-get install -y \
    wine wine32 xvfb \
    wget ca-certificates \
    p7zip-full \
    git \
    curl

USER user

RUN wget https://bitbucket.org/lazka/quodlibet/downloads/quodlibet-latest-installer-py3.exe -O win-inst.exe

RUN 7z x -o_win_inst win-inst.exe

ENV WINEPREFIX /home/user/_wineprefix
ENV WINEDEBUG -all

RUN echo '#!/bin/bash\n(rm -Rf "$WINEPREFIX" && xvfb-run -a wine /home/user/_win_inst/bin/python3.exe "$@")' > python3
RUN echo '#!/bin/bash\n python3 -m pytest "$@"' > py.test-3

RUN chmod a+x python3 py.test-3

ENV PATH /home/user:$PATH
