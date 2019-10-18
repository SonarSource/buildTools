How to deploy:
gcloud functions deploy promote --runtime python37 --trigger-http

gcloud functions deploy promote \
  --runtime python37 --trigger-http \
  --set-env-vars ARTIFACTORY_URL=https://repox.jfrog.io/repox,ARTIFACTORY_API_KEY=XXX,ACCESS_TOKEN=XXX \
  --region us-central1 \
  --memory 128MB --project $GOOGLE_PROJECT_ID

call: 
PROMOTE_URL=https://us-central1-language-team.cloudfunctions.net/promote

curl -s -H "Authorization: Bearer $ACCESS_TOKEN" "$PROMOTE_URL/$GITHUB_REPO/$GITHUB_BRANCH/$BUILD_NUMBER/$PULL_REQUEST(?multi=true)"
