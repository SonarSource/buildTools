#!/bin/bash
set -euo pipefail

# Defaults
TAG=latest
CLUSTER=language-team
DOCKERFILE=Dockerfile-base
NAME=base
function _print_help {
  echo "Usage:"
  echo "  ./build.sh [-t TAG=latest] [-c CLUSTER=language-team]"
  echo
  echo "  -h    Prints this help."
  echo "  -f    Dockerfile filename default to Dockerfile-base"
  echo "  -n    Docker image name default to base"
  echo "  -t    Sets the tag for the image. Defaults to 'latest'."
  echo "  -c    Sets the cluster to push to. Defaults to 'language-team'."
  echo
  echo "Examples:"
  echo "  ./build.sh"
  echo "  -> Builds the image locally, and pushes it as 'gcr.io/language-team/base:latest'"
  echo
  echo "  ./build.sh -t v2 -c ci-cd-215716"
  echo "  -> Builds the image locally, and pushes it as 'gcr.io/ci-cd-215716/base:v2'"
  echo
}

# Parse arguments.
while getopts "hf:n:t:c:" OPTION; do
  case "$OPTION" in
  h)
    _print_help
    exit 0
    ;;
  f)
    DOCKERFILE="$OPTARG"
    ;;
  n)
    NAME="$OPTARG"
    ;;
  c)
    CLUSTER="$OPTARG"
    ;;
  t)
    TAG="$OPTARG"
    ;;
  esac
done
shift $(expr $OPTIND - 1 )

docker pull "gcr.io/$CLUSTER/$NAME:$TAG" || true
docker build -f $DOCKERFILE -t $NAME .
docker tag $NAME "gcr.io/$CLUSTER/$NAME:$TAG"
docker push "gcr.io/$CLUSTER/$NAME:$TAG"
