#!/bin/bash

export GOOGLE_PROJECT_ID=language-team
. ./secrets.sh
#/sonarsource/var/opt/sonarsource/binaries.sonarsource.com/sonarsource.bintray.com/

gcloud functions deploy release \
  --runtime python37 --trigger-http \
  --set-env-vars ARTIFACTORY_API_KEY=$ARTIFACTORY_API_KEY,GPG_PASSPHRASE=$GPG_PASSPHRASE,PATH_PREFIX=/tmp \
  --region us-central1 \
  --memory 128MB \
  --project $GOOGLE_PROJECT_ID \
  --source src