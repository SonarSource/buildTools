#!/bin/bash

set -euo pipefail

TAG=v5

if [ "${CIRRUS_PR:-}" != "" ]; then
  ./build.sh -t "PR_$CIRRUS_PR"
  ./build.sh -t "PR_$CIRRUS_PR" -f Dockerfile-jdk15 -n base-jdk15
  ./build.sh -t "PR_$CIRRUS_PR" -f Dockerfile-jdk16 -n base-jdk16
  
elif [ $CIRRUS_BRANCH == "docker" ]; then
  ./build.sh -t $TAG
  ./build.sh -t latest
  ./build.sh -t $TAG -f Dockerfile-jdk15 -n base-jdk15
  ./build.sh -t latest -f Dockerfile-jdk15 -n base-jdk15
  ./build.sh -t $TAG -f Dockerfile-jdk16 -n base-jdk16
  ./build.sh -t latest -f Dockerfile-jdk16 -n base-jdk16
else
  echo "Not building image for feature branch"
fi
