How to deploy:

generate requirements.txt with requirements.sh
private ssh key id_rsa_ssuopsa has to be present in the repository before deploy

gcloud functions deploy release \
  --runtime python37 --trigger-http \
  --set-env-vars ARTIFACTORY_URL=https://repox.jfrog.io/repox,ARTIFACTORY_API_KEY=XXX,GPG_PASSPHRASE=XXX,PATH_PREFIX=/sonarsource/var/opt/sonarsource/binaries.sonarsource.com/sonarsource.bintray.com/ \
  --region us-central1 \
  --source=src \
  --memory 128MB --project $GOOGLE_PROJECT_ID

call: 
RELEASE_URL=https://us-central1-language-team.cloudfunctions.net/release

curl -s -H "Authorization: token $GITHUB_TOKEN" "$RELEASE_URL/$GITHUB_REPO/$GITHUB_BRANCH/$SHA1"

curl -s -H "Authorization: token $GITHUB_TOKEN" "$RELEASE_URL/SonarSource/sonar-dummy/master/3629c526389c15049fc5ca37de395746ade2991b"