How to deploy:

generate requirements.txt with requirements.sh

gcloud functions deploy releasability_check \
  --runtime python37 --trigger-http \
  --set-env-vars BURGRX_USER=$BURGRX_USER,BURGRX_PASSWORD=$BURGRX_PASSWORD \
  --region us-central1 \
  --memory 128MB \
  --project $GOOGLE_PROJECT_ID \
  --source=src

call: 
RELEASABILITY_URL=https://us-central1-language-team.cloudfunctions.net/releasability_check

curl -s -H "Authorization: token $GITHUB_TOKEN" "$RELEASABILITY_URL/$GITHUB_REPO/$VERSION"

curl -s -H "Authorization: token $GITHUB_TOKEN" "$RELEASABILITY_URL/SonarSource/sonar-dummy/10.0.0.322"
