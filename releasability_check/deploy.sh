#!/bin/bash

export GOOGLE_PROJECT_ID=language-team
. ./secrets.sh

gcloud functions deploy releasability_check \
  --runtime python37 --trigger-http \
  --set-env-vars BURGRX_USER=$BURGRX_USER,BURGRX_PASSWORD=$BURGRX_PASSWORD \
  --region us-central1 \
  --memory 128MB \
  --timeout 360 \
  --project $GOOGLE_PROJECT_ID \
  --source=src
