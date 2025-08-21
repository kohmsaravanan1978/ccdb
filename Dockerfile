FROM ubuntu:24.04

ENV LANG en_US.UTF-8
ENV LANGUAGE en_US:en
ENV LC_ALL en_US.UTF-8
ENV DEBIAN_FRONTEND noninteractive

RUN mkdir /code

RUN apt-get update -qq && \
	apt-get install -y --no-install-recommends -f locales && \
	locale-gen en_US.UTF-8 de_DE.utf8 && \
	apt-get install -y --no-install-recommends \
	    ruby-sass \
	    jq \
	    sudo \
	    zip \
	    unzip \
	    uwsgi \
	    uwsgi-plugin-python3 \
	    zlib1g-dev \
	    git \
	    build-essential \
	    python3-venv \
	    python3 \
	    bash-completion \
	    python3-dev \
	    python3-setuptools \
	    libldap2-dev \
	    libsasl2-dev \
	    graphviz \
	    libxml2-dev \
	    libxslt1-dev \
	    zlib1g-dev \
	    python3-pip \
	    iputils-ping \
	    pkg-config \
	    libgraphviz-dev \
	    fonts-ubuntu \
	    fontconfig \
	    libmagickwand-dev \
	    libffi-dev \
	    postgresql-client \
	    postgresql-common \
	    xvfb \
	    wget \
	    gettext \
	    libmemcached-dev \
	    libxmlsec1-dev \
	    poppler-utils \
	    curl \
	    libkrb5-dev \
	    ca-certificates && \
	apt-get -y autoremove && \
	rm -rf /var/lib/apt/lists/* && \
	# ia user
	useradd -s /bin/bash -u 5000 -m -U ia

ENV PATH=$PATH:/root/.poetry/bin

WORKDIR /poetry

COPY /poetry.lock /poetry/poetry.lock
COPY /pyproject.toml /poetry/pyproject.toml
RUN curl -sSL https://install.python-poetry.org > /tmp/install-poetry.py && \
    python3 /tmp/install-poetry.py && \
    ln -s /root/.local/bin/poetry /usr/bin/poetry && \
    poetry config virtualenvs.in-project true && \
    poetry config cache-dir /tmp/poetry-cache && \
    poetry run pip install -U setuptools wheel poetry && \
    poetry install && \
    rm -rf /tmp/poetry-cache

COPY /ccdb /code
RUN poetry run python3 /code/manage.py collectstatic -c --no-input --settings=ccdb.settings.build && \
    find /code/static/ -type f -regextype egrep -iregex  ".*\.(js|css|txt|html?|map)" -print0  | xargs -0 gzip -kf9 && \
    poetry run bash -c "cd /code && python3 /code/manage.py compilemessages --settings=ccdb.settings.build"

COPY /docker/entrypoint-celery.sh /entrypoint-celery.sh
COPY /docker/entrypoint-celery_beat.sh /entrypoint-celery_beat.sh
COPY /docker/entrypoint-uwsgi.sh /entrypoint-uwsgi.sh
COPY /docker/uwsgi.ini /uwsgi.ini
ENTRYPOINT ["/entrypoint-uwsgi.sh"]
