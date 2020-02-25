import sys
import os
import requests
import json


cirrus_token=os.environ.get('CIRRUS_TOKEN','no cirrus token in env')  
cirrus_api_url="https://api.cirrus-ci.com/graphql"
owner="SonarSource"
repo="rules-cov"



def test_get_repository_id():
  url = cirrus_api_url
  headers = {'Authorization': f"Bearer {cirrus_token}"}
  payload = {
    "query":f"query GitHubRepositoryQuery {{githubRepository(owner:\"{owner}\",name:\"{repo}\"){{id}}}}"
    }
  r = requests.post(url, json=payload, headers=headers)
  repository_id=r.json()["data"]["githubRepository"]["id"]
  return repository_id
  
def test_trigger_run():
  repository_id=test_get_repository_id()

  f = open("config.yml","r")
  config = f.read()

  url = cirrus_api_url
  headers = {'Authorization': f"Bearer {cirrus_token}"}
  payload = {
    "query": f"mutation CreateBuildDialogMutation($input: RepositoryCreateBuildInput!) {{createBuild(input: $input) {{build {{id}}}}}}",
    "variables": {
      "input": {
        "clientMutationId": f"{repo}",
        "repositoryId": f"{repository_id}",
        "branch": "run",
        "sha": "",
        "configOverride": f"{config}"
        }
      }
    }
  r = requests.post(url, json=payload, headers=headers)
  print(r.json())
  