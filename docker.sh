#!/bin/bash
#
# Example usage:
#   ./docker.sh win32.py2
# You should end up in a bash shell in the quodlibet directory and with
# python/python2/python3/py.test/py.test-3 helper scripts in the path.

set -e

IMAGENAME="ql-docker-image-$1"
DOCKERFILE=".docker/Dockerfile.$1"

if [[ ! -e "$DOCKERFILE" ]]
then
  echo -e "\e[31mPass one of the following:\e[0m"
  ls -1 ".docker" | sort | cut -d. -f2-
  exit 1
fi

sudo docker build --tag "$IMAGENAME" --file "$DOCKERFILE" .
sudo docker run --volume "$(pwd):/home/user/app" --workdir "/home/user/app/quodlibet" --tty --interactive "$IMAGENAME" bash
