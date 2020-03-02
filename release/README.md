How to deploy:

generate requirements.txt with requirements.sh
private ssh key id_rsa_ssuopsa has to be present in the repository before deploy

gcloud functions deploy release \
  --runtime python37 --trigger-http \
  --set-env-vars ARTIFACTORY_API_KEY=XXX,GPG_PASSPHRASE=XXX,PATH_PREFIX=/sonarsource/var/opt/sonarsource/binaries.sonarsource.com/sonarsource.bintray.com/,BURGRX_USER=$BURGRX_USER,BURGRX_PASSWORD=$BURGRX_PASSWORD,CIRRUS_TOKEN=$CIRRUS_TOKEN \
  --region us-central1 \
  --source=src \
  --memory 128MB --project $GOOGLE_PROJECT_ID

call: 
RELEASE_URL=https://us-central1-language-team.cloudfunctions.net/release

curl -s -H "Authorization: token $GITHUB_TOKEN" "$RELEASE_URL/$GITHUB_REPO/$BUILD_NUMBER"

curl -s -H "Authorization: token $GITHUB_TOKEN" "$RELEASE_URL/SonarSource/sonar-dummy/359"