FROM ubuntu:cosmic

ENV LANG C.UTF-8
ENV PYTHONDONTWRITEBYTECODE 1
ENV CI true

ARG HOST_USER_ID=5555
ENV HOST_USER_ID ${HOST_USER_ID}
RUN useradd -u $HOST_USER_ID -ms /bin/bash user

RUN apt-get update && apt-get install --no-install-recommends -y \
    wine-stable \
    xvfb \
    ca-certificates \
    curl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /home/user
USER user

ENV WINEPREFIX /home/user/_wineprefix
ENV WINEDEBUG -all

RUN curl -o win-inst.exe -J -L https://github.com/quodlibet/quodlibet/releases/download/ci/quodlibet-latest-installer-v4.exe \
    && wine win-inst.exe /S /D=$(winepath -w "$PWD/Quod Libet") \
    && mv "Quod Libet" _win_inst \
    && rm win-inst.exe \
    && rm -Rf "$WINEPREFIX"

RUN echo '#!/bin/bash\nrm -Rf "$WINEPREFIX"\nxvfb-run -a wine /home/user/_win_inst/bin/python3.exe "$@"\nRES=$?\nwineboot -kf\nexit $RES' > python3
RUN echo '#!/bin/bash\nset -e\npython3 -m pytest "$@"' > py.test-3

RUN chmod a+x python3 py.test-3

ENV PATH /home/user:$PATH
