FROM python:3.5

ENV LANG C.UTF-8


RUN apt-get update && apt-get install -y \
    dirmngr \
    && rm -rf /var/lib/apt/lists/*

RUN apt-get update && apt-get install -y \
    && apt-get install --no-install-recommends -y \
    xvfb \
    gettext \
    libxine2 \
    libgirepository1.0-dev \
    dbus-x11 \
    curl \
    git

COPY quodlibet/quodlibet quodlibet/
COPY pyproject.toml poetry.lock ./
RUN python3 -m pip install poetry
RUN poetry install

RUN poetry run pytest
