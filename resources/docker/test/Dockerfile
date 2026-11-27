FROM python:3.13-slim-bookworm
COPY --from=docker.io/astral/uv:latest /uv /uvx /bin/
RUN DEBIAN_FRONTEND="noninteractive" apt update --fix-missing \
    && apt-get install --no-install-recommends -y \
        curl \
    && apt-get clean \
    && apt-get autoremove -y \
    && rm -rf /var/lib/apt/lists/*

# Make new user
RUN groupadd -r geo-datasets && useradd -ms /bin/bash -g geo-datasets user && usermod -aG sudo user

# Enable bytecode compilation
ENV UV_COMPILE_BYTECODE=1
# Copy from the cache instead of linking since it's a mounted volume
ENV UV_LINK_MODE=copy

RUN mkdir -p /geo-datasets
RUN chown --recursive user:root /geo-datasets

USER user
# Installing the latest miniconda to get a version of sqlite newer than 3.50
RUN curl --location https://repo.anaconda.com/miniconda/Miniconda3-latest-Linux-x86_64.sh --output ~/miniconda.sh \
    && /bin/bash ~/miniconda.sh -b \
    && /home/user/miniconda3/bin/conda create --yes --override-channels --channel conda-forge \
        --name geo-datasets python=3.13 'sqlite>=3.50' \
    && rm ~/miniconda.sh
ENV PATH=/home/user/miniconda3/envs/geo-datasets/bin:/home/user/miniconda3/bin:$PATH
# Fix shell for conda
USER root
RUN ln -snf /bin/bash /bin/sh

USER user

WORKDIR /home/user
# Install the project's dependencies using the lockfile and settings
RUN --mount=type=cache,target=/root/.cache/uv \
    --mount=type=bind,source=uv.lock,target=uv.lock \
    --mount=type=bind,source=pyproject.toml,target=pyproject.toml \
    uv sync --locked --no-install-project

RUN mkdir -p ~/.geo-datasets/logs
