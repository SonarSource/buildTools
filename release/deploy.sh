#!/bin/bash

export GOOGLE_PROJECT_ID=language-team
. ./secrets.sh

gcloud functions deploy release \
  --runtime python37 --trigger-http \
  --set-env-vars ARTIFACTORY_API_KEY=$ARTIFACTORY_API_KEY,GPG_PASSPHRASE=$GPG_PASSPHRASE,PATH_PREFIX=/sonarsource/var/opt/sonarsource/binaries.sonarsource.com/sonarsource.bintray.com/,BURGRX_USER=$BURGRX_USER,BURGRX_PASSWORD=$BURGRX_PASSWORD,CIRRUS_TOKEN=$CIRRUS_TOKEN \
  --region us-central1 \
  --memory 2048MB \
  --timeout 360 \
  --project $GOOGLE_PROJECT_ID \
  --source src
