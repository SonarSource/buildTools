#! /bin/bash

set -euo pipefail

#See README.md to understand branches, naming and versioning.

TAG=v8

if [ "${CIRRUS_PR:-}" != "" ]; then
  TAG=pull-request-$CIRRUS_PR
  export IMAGE_FAMILY=
elif [ $CIRRUS_BRANCH == "lt-base-windows-dotnet" ]; then
  export IMAGE_FAMILY=lt-base-windows-dotnet
else
  echo "Not building image for feature branch"
  exit
fi

export IMAGE_NAME=lt-base-windows-dotnet-${TAG}

apt-get update && apt-get -y install curl unzip
curl -LsS https://releases.hashicorp.com/packer/1.3.5/packer_1.3.5_linux_amd64.zip > packer.zip
unzip packer.zip
echo ${ACCOUNT} > account.json
GOOGLE_APPLICATION_CREDENTIALS=account.json ./packer build -force windows/lt-base-windows-dotnet.json
