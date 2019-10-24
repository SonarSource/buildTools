#!/bin/bash

export TAG=v2

docker pull gcr.io/language-team/base:$TAG
docker build -f languageTeam.Dockerfile -t base .

if [ $CIRRUS_PR != "" ]; then
  export TAG=$CIRRUS_PR
  export LATEST=true
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



