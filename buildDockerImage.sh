#!/bin/bash

set -euo pipefail

TAG=v5

if [ "${CIRRUS_PR:-}" != "" ]; then
  ./build.sh -t "PR_$CIRRUS_PR"
elif [ $CIRRUS_BRANCH == "docker" ]; then
  ./build.sh -t $TAG
  ./build.sh -t latest
else
  echo "Not building image for feature branch"
fi
