# Standard Dockerfile 

language team base image:
docker build -t base .
docker tag base gcr.io/language-team/base:v0
docker push gcr.io/language-team/base:v0

cleanup registry of unused image:

gcloud container images delete gcr.io/[PROJECT-ID]/imagename:tag --force-delete-tags

where [PROJECT-ID] is your Google Cloud Platform Console project ID eg: language-team

Generate GCP registry credential to access registry from cirrus-ci

docker login -u _json_key --password-stdin https://gcr.io < service-account.json

where service-account.json is the json key associated to a service account with storage.admin role (eg. cirrus-ci service account)

this credential is then stored in ~/.docker/config.json in this form:
{
  "auths": {
    "container-registry.oracle.com": {
      "auth": "...."
    }
  }
}

and can then be encrypted on cirrus-ci.com to be embedded in .cirrus.yml
cf: https://cirrus-ci.org/guide/linux/#working-with-private-registries