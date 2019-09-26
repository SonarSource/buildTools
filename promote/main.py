import sys
import os
import requests
import json

from flask import escape

artifactoryUrl=os.environ.get('ARTIFACTORY_URL','repox url not set')
artifactoryApiKey=os.environ.get('ARTIFACTORY_API_KEY','not api key provided')  

def getVar(request,var):
  request_json = request.get_json(silent=True)
  request_args = request.args
  value=None
  if request_json and var in request_json:
    value = request_json[var]
  elif request_args and var in request_args:
    value = request_args[var]
  return value

def repoxGetPropertyFromBuildInfo(project, buildNumber, property):  
  url = f"{artifactoryUrl}/api/build/{project}/{buildNumber}"
  headers = {'content-type': 'application/json', 'X-JFrog-Art-Api': artifactoryApiKey}
  r = requests.get(url, headers=headers)  
  buildInfo = r.json()
  return buildInfo['buildInfo']['properties'][property]

# [START functions_promote_http]
def promote(request):
  """HTTP Cloud Function.
  Args:
    request (flask.Request): The request object.
    <http://flask.pocoo.org/docs/1.0/api/#flask.Request>
  Returns:
    The response text, or any set of values that can be turned into a
    Response object using `make_response`
    <http://flask.pocoo.org/docs/1.0/api/#flask.Flask.make_response>.
  Trigger:
    {functionBaseUrl}/promote/GITHUB_ORG/GITHUB_PROJECT/GITHUB_BRANCH/BUILD_NUMBER/PULL_REQUEST_NUMBER
  """
  
  auth = request.authorization
  print("auth:"+str(auth))

  print("PATH:"+request.path)
  paths=request.path.split("/")
  org=paths[1]
  project=paths[2]
  githubBranch=paths[3]
  buildNumber=paths[4]
  pullRequest=paths[5]
  targetRepo=None
  status=None
  response=None
  doPromote = False

  print("PULL_REQUEST: " + str(pullRequest))
  print("GITHUB_BRANCH: " + githubBranch)
  print("BUILD_NUMBER: " + buildNumber)
  print("PROJECT: " + project)

  repo = repoxGetPropertyFromBuildInfo(project, buildNumber, 'buildInfo.env.ARTIFACTORY_DEPLOY_REPO')

  if pullRequest:
    print("in PR")
    targetRepo = repo.replace('qa', 'dev')
    status = 'it-passed-pr'
    doPromote = True
  else:
    print("NOT in PR")
    if githubBranch == "master" or githubBranch.startswith("branch-"):
        targetRepo = repo.replace('qa', 'builds')
        status = 'it-passed'
        doPromote = True

    if githubBranch.startswith("dogfood-on-"):
      targetRepo = "sonarsource-dogfood-builds"
      status = 'it-passed'
      doPromote = True

  print(f"status:{status}")
  
  if doPromote:
    print(f"Promoting build {project}#{buildNumber}")
    json_payload={
        "status": f"{status}",
        "targetRepo": f"{targetRepo}"
    }
    print(json_payload)
    url = f"{artifactoryUrl}/api/build/promote/{project}/{buildNumber}"
    headers = {'content-type': 'application/json', 'X-JFrog-Art-Api': artifactoryApiKey}
    r = requests.post(url, data=json.dumps(json_payload), headers=headers)
    response = f"promotion http_code: {r.status_code} json: {r.json} text: {r.text}"
    
  else:
    response = "No promotion for builds coming from a development branch"

  print(response)
  return response
# [END functions_promote_http]
