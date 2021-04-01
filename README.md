# Standard Dockerfile 

language team base image:
docker build -f Dockerfile-base -t base .
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

#Setup docker builder image for cirrus-ci cluster
#copy service-account.json to the VM

#login to docker with the file
docker login -u _json_key --password-stdin https://gcr.io < service-account.json

#setup the config to be reused by any user logging to the docker-builder VM:
sudo rm /.docker/config.json 
mv .docker/config.json /.docker/
sudo chmod 777 /.docker/*
export DOCKER_CONFIG=/.docker

#test the connection
docker pull gcr.io/language-team/base:latest

#add to the /etc/profile so that's available to any user:
mkdir -p ~/.docker
cp /.docker/config.json ~/.docker