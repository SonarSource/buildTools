import sys
import os
import requests
import json

from flask import escape
from flask import make_response

artifactoryUrl=os.environ.get('ARTIFACTORY_URL','repox url not set')
artifactoryApiKey=os.environ.get('ARTIFACTORY_API_KEY','not api key provided')  
AUTHENTICATED="authenticated"

def repoxGetPropertyFromBuildInfo(project, buildNumber, property):  
  url = f"{artifactoryUrl}/api/build/{project}/{buildNumber}"
  headers = {'content-type': 'application/json', 'X-JFrog-Art-Api': artifactoryApiKey}
  r = requests.get(url, headers=headers)  
  buildInfo = r.json()
  if r.status_code == 200:      
    return buildInfo['buildInfo']['properties'][property]
  else:
    raise Exception('unknown build')

def validateAutorizationHeader(request):
  if request.headers['Authorization'] and request.headers['Authorization'].split()[0] == 'Bearer':
    if (request.headers['Authorization'].split()[1] == os.environ.get('ACCESS_TOKEN')):
      return AUTHENTICATED
    else:
      return "Wrong access token"
  else:
    return "Missing access token"
  



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
  
  if validateAutorizationHeader(request) == AUTHENTICATED:  
    print("PATH:"+request.path)
    paths=request.path.split("/")
    #org=paths[1]
    project=paths[2]
    githubBranch=paths[3]
    buildNumber=paths[4]
    pullRequest=paths[5]
    targetRepo=None
    targetRepo2="sonarsource-public-builds"
    status=None
    response=None
    doPromote = False

    print("PULL_REQUEST: " + str(pullRequest))
    print("GITHUB_BRANCH: " + githubBranch)
    print("BUILD_NUMBER: " + buildNumber)
    print("PROJECT: " + project)

    try:
      repo = repoxGetPropertyFromBuildInfo(project, buildNumber, 'buildInfo.env.ARTIFACTORY_DEPLOY_REPO')
    except Exception as e:
      return make_response(str(e),400)

    if pullRequest:
      if request.args.get('multi') == "true":
        targetRepo = "sonarsource-private-dev"
        targetRepo2 = "sonarsource-public-dev"
      else:
        targetRepo = repo.replace('qa', 'dev')
      status = 'it-passed-pr'
      doPromote = True
    else:
      if githubBranch == "master" or githubBranch.startswith("branch-"):
        if request.args.get('multi') == "true":
          targetRepo = "sonarsource-private-builds"
        else:
          targetRepo = repo.replace('qa', 'builds')
        status = 'it-passed'
        doPromote = True

      if githubBranch.startswith("dogfood-on-"):
        targetRepo = "sonarsource-dogfood-builds"
        #only for multipromote purpose
        targetRepo2 = "sonarsource-dogfood-builds"
        status = 'it-passed'
        doPromote = True

    print(f"status:{status}")
    
    if doPromote:
      print(f"Promoting build {project}#{buildNumber}")
      json_payload={
          "status": f"{status}",
          "targetRepo": f"{targetRepo}"
      }

      if request.args.get('multi') == "true":
        url = f"{artifactoryUrl}/api/plugins/execute/multiRepoPromote?params=buildName={project};buildNumber={buildNumber};src1=sonarsource-private-qa;target1={targetRepo};src2=sonarsource-public-qa;target2={targetRepo2};status={status}"
        headers = {'X-JFrog-Art-Api': artifactoryApiKey}
        r = requests.get(url, headers=headers)
      else:
        url = f"{artifactoryUrl}/api/build/promote/{project}/{buildNumber}"
        headers = {'content-type': 'application/json', 'X-JFrog-Art-Api': artifactoryApiKey}
        r = requests.post(url, data=json.dumps(json_payload), headers=headers)      
      if r.status_code == 200:      
        return make_response(f"status:{status}",200)
      else:
        return make_response(r.text,r.status_code)
    else:
      response = "No promotion for builds coming from a development branch"
    return response
  else:
    return make_response(validateAutorizationHeader(request),403)
# [END functions_promote_http]
