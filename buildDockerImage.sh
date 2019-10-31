#!/bin/bash

set -euo pipefail

TAG=v2

docker pull gcr.io/language-team/base:$TAG || true
docker build -f languageTeam.Dockerfile -t base .

if [ "${CIRRUS_PR:-}" != "" ]; then
  TAG=$CIRRUS_PR
  docker tag base "gcr.io/language-team/base:PR_$TAG"
  docker push "gcr.io/language-team/base:PR_$TAG"
elif [ $CIRRUS_BRANCH == "docker" ]; then
  docker tag base "gcr.io/language-team/base:$TAG"
  docker push "gcr.io/language-team/base:$TAG"
  docker tag base "gcr.io/language-team/base:latest"
  docker push "gcr.io/language-team/base:latest"
else
  echo "Not building image for feature branch"
fi