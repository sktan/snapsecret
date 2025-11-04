FROM mcr.microsoft.com/vscode/devcontainers/python:3.14
ENV EDITOR=vim

RUN apt-get update && export DEBIAN_FRONTEND=noninteractive && \
    apt-get install -y vim gnupg2 ripgrep && \
    pip3 install pylint black pre-commit
