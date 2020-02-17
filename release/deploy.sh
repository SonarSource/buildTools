#!/bin/bash

export GOOGLE_PROJECT_ID=language-team
. ./secrets.sh

gcloud functions deploy release \
  --runtime python37 --trigger-http \
  --set-env-vars ARTIFACTORY_API_KEY=$ARTIFACTORY_API_KEY,GPG_PASSPHRASE=$GPG_PASSPHRASE \
  --region us-central1 \
  --memory 128MB \
  --project $GOOGLE_PROJECT_ID \
  --source src