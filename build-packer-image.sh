#! /bin/bash

set -euo pipefail

TAG=v1

if [ "${CIRRUS_PR:-}" != "" ]; then
  TAG=$CIRRUS_PR
  export IMAGE_FAMILY=
elif [ $CIRRUS_BRANCH == "lt-base-windows-jdk16" ]; then
  export IMAGE_FAMILY=lt-base-windows-jdk16
else
  echo "Not building image for feature branch"
fi

export IMAGE_NAME=lt-base-windows-jdk16-${TAG}

apt-get update && apt-get -y install curl unzip
curl -LsS https://releases.hashicorp.com/packer/1.3.5/packer_1.3.5_linux_amd64.zip > packer.zip
unzip packer.zip
echo ${ACCOUNT} > account.json
GOOGLE_APPLICATION_CREDENTIALS=account.json ./packer build -force windows/lt-base-windows-jdk16.json
