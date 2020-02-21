How to deploy:

generate requirements.txt with requirements.sh

gcloud functions deploy releasability_check \
  --runtime python37 --trigger-http \
  --set-env-vars ARTIFACTORY_API_KEY=$ARTIFACTORY_API_KEY,BURGRX_USER=$BURGRX_USER,BURGRX_PASSWORD=$BURGRX_PASSWORD \
  --region us-central1 \
  --memory 128MB \
  --project $GOOGLE_PROJECT_ID \
  --source=src

call: 
RELEASABILITY_URL=https://us-central1-language-team.cloudfunctions.net/releasability_check

curl -s -H "Authorization: token $GITHUB_TOKEN" "$RELEASABILITY_URL/$GITHUB_REPO/$GITHUB_BRANCH/$SHA1"

curl -s -H "Authorization: token $GITHUB_TOKEN" "$RELEASABILITY_URL/SonarSource/sonar-dummy/master/3629c526389c15049fc5ca37de395746ade2991b"
