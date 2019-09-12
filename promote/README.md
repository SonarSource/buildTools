How to deploy:
gcloud functions deploy promote --runtime python37 --trigger-http

gcloud functions deploy promote \
  --runtime python37 --trigger-http \ 
  --set-env-vars ARTIFACTORY_URL=https://repox.jfrog.io/repox,ARTIFACTORY_API_KEY=XXX \
  --region us-central1 \
  --memory 128MB --project $GOOGLE_PROJECT_ID