#!/bin/bash
set -euo pipefail

# Defaults
TAG=latest
CLUSTER=language-team

function _print_help {
  echo "Usage:"
  echo "  ./build.sh [-t TAG=latest] [-c CLUSTER=language-team]"
  echo
  echo "  -h    Prints this help."
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
while getopts "ht:c:" OPTION; do
  case "$OPTION" in
  h)
    _print_help
    exit 0
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

docker pull "gcr.io/$CLUSTER/base:$TAG" || true
docker build -f Dockerfile-base -t base .
docker tag base "gcr.io/$CLUSTER/base:$TAG"
docker push "gcr.io/$CLUSTER/base:$TAG"
