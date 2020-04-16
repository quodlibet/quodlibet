#!/bin/bash
#
# Example usage:
#   ./docker.sh run win32.py2
#
# You should end up in a bash shell in the quodlibet directory and with
# python/python2/python3/py.test/py.test-3 helper scripts in the path.
#
# If you want to recreate the docker image (to pull in new dependencies etc)
#   ./docker.sh rm win32.py2

set -e

IMAGENAME="ql-docker-image-$2"
DOCKERFILE="../.docker/Dockerfile.$2"

if [[ ! "$1" == "run" ]] && [[ ! "$1" == "rm" ]]
then
    echo "Usage: docker.sh (run|rm) <image-name>"
    exit 1
fi

if [[ ! -e "$DOCKERFILE" ]]
then
  echo -e "\e[31mPass one of the following:\e[0m"
  ls -1 "../.docker" | sort | cut -d. -f2-
  exit 1
fi

if [[ "$1" == "rm" ]]
then
    sudo docker stop $(sudo docker ps -a -q --filter=ancestor="$IMAGENAME") &> /dev/null || true
    sudo docker rm $(sudo docker ps -a -q --filter=ancestor="$IMAGENAME") &> /dev/null || true
    sudo docker rmi "$IMAGENAME" &> /dev/null || true
    exit 0
fi

sudo docker build --build-arg HOST_USER_ID="$UID" --tag "$IMAGENAME" --file "$DOCKERFILE" .
sudo docker run --cap-add=SYS_PTRACE --rm --volume "$(pwd)/..:/home/user/app" --workdir "/home/user/app" --tty --interactive "$IMAGENAME" bash
