#!/bin/bash
set -euo pipefail

# Defaults
TAG=latest

# Parse arguments.
while getopts "ht:c:" OPTION; do
  case "$OPTION" in
  h)
    _print_help
    exit 0
    ;;
  t)
    TAG="$OPTARG"
    ;;
  esac
done
shift $(expr $OPTIND - 1 )

docker pull "gcr.io/ci-cd-215716/jdk8:$TAG" || true
docker build -f Dockerfile-jdk8 -t jdk8 .
docker tag jdk8 "gcr.io/ci-cd-215716/jdk8:$TAG"
docker push "gcr.io/ci-cd-215716/jdk8:$TAG"
