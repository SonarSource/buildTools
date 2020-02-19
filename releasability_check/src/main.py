import os
import polling
import requests
import urllib
from flask import Request, make_response
from polling import TimeoutException
from requests.auth import HTTPBasicAuth
from requests.models import Response
from typing import Dict

artifactory_apikey = os.environ.get('ARTIFACTORY_API_KEY', 'no api key in env')
artifactory_url = 'https://repox.jfrog.io/repox'

burgrx_url = 'https://burgrx.sonarsource.com'
burgrx_user = os.environ.get('BURGRX_USER', 'no burgrx user in env')
burgrx_password = os.environ.get('BURGRX_PASSWORD', 'no burgrx password in env')

AUTHENTICATED = "authenticated"

GITHUB_REPOSITORY = 'sonar-dummy-oss'

# [START functions_releasability_check_http]
def releasability_check(request: Request):
    """HTTP Cloud Function.
    Args:
      request (flask.Request): The request object.
      <http://flask.pocoo.org/docs/1.0/api/#flask.Request>
    Returns:
      The response text, or any set of values that can be turned into a
      Response object using `make_response`
      <http://flask.pocoo.org/docs/1.0/api/#flask.Flask.make_response>.
    Trigger:
      {functionBaseUrl}/releasability_check/GITHUB_ORG/GITHUB_PROJECT/SHA1
    """
    print("PATH:" + request.path)
    paths = request.path.split("/")
    organization = paths[1]
    project = paths[2]
    sha1 = paths[3]

    if organization != "SonarSource":
        return make_response("Unauthorized organization", 403)

    buildnumber = find_buildnumber_from_sha1(sha1)
    authorization = validate_authorization_header(request.headers, project)
    if authorization == AUTHENTICATED:
        try:
            version = get_version(project, buildnumber)
            releasability = releasability_checks(project, version)
            if releasability:
                return make_response(releasability)
            return make_response("Unexpected error occurred", 500)
        except Exception as e:
            print(f"Could not get repository for {project} {buildnumber} {str(e)}")
            return make_response(str(e), 500)
    else:
        return make_response(authorization, 403)


def validate_authorization_header(headers: Dict[str, str], project: str):
    authorization = headers.get('Authorization')
    if authorization:
        values = authorization.split()
        if len(values) == 2 and values[0] == "token" and github_auth(values[1], project):
            print("Authenticated with github token with write permissions")
            return AUTHENTICATED
        else:
            return "Wrong access token"
    else:
        return "Missing access token"


def github_auth(token: str, project: str):
    url = f"https://api.github.com/repos/SonarSource/{project}"
    headers = {'Authorization': f"token {token}"}
    r = requests.get(url, headers=headers)
    if r.status_code == 200:
        jsonobject = r.json()
        return 'permissions' in jsonobject and (
                    jsonobject['permissions'].get('push') or jsonobject['permissions'].get('admin'))
    return False


def find_buildnumber_from_sha1(sha1: str):
    query = f'build.properties.find({{"buildInfo.env.GIT_SHA1": "{sha1}"}}).include("buildInfo.env.BUILD_NUMBER")'
    url = f"{artifactory_url}/api/search/aql"
    headers = {'content-type': 'text/plain', 'X-JFrog-Art-Api': artifactory_apikey}
    r = requests.post(url, data=query, headers=headers)
    results = r.json()['results']
    if len(results) != 1:
        raise Exception(f"Unexpected number of results found for sha1 '{sha1}'. Found: '{results}'")
    return results[0]['build.property.value']


def get_version(project: str, buildnumber: str):
    url = f"{artifactory_url}/api/build/{project}/{buildnumber}"
    headers = {'content-type': 'application/json', 'X-JFrog-Art-Api': artifactory_apikey}
    r = requests.get(url, headers=headers)
    buildinfo = r.json()
    if r.status_code == 200:
        return buildinfo['buildInfo']['modules'][0]['id'].split(":")[-1]
    else:
        raise Exception('unknown build')


def releasability_checks(project: str, buildnumber: str):
    r"""Starts the releasability check operation. Post the start releasability HTTP request to Burgrx and polls until
      all checks have completed.

      :param project: Github project name, ex: 'sonar-dummy'
      :param buildnumber: build number to be checked for releasability.
      :return: True if releasability check succeeded, False otherwise.
      """

    print(f"Starting releasability check: {project}#{buildnumber}")

    url = f"{burgrx_url}/api/project/SonarSource/{project}/releasability/start/{buildnumber}"
    response = requests.post(url, auth=HTTPBasicAuth(burgrx_user, burgrx_password))

    if response.status_code == 200 and response.json()['message'] == "done":
        print(f"Releasability checks started successfully")
        return start_polling_releasability_status(project, buildnumber)
    else:
        print(f"Releasability checks failed to start: {response}")
        return False


def start_polling_releasability_status(project: str, buildnumber: str, step: int = 4, timeout: int = 300):
    url_encoded_project = urllib.parse.quote(f"SonarSource/{project}", safe='')
    branch = 'master'
    url = f"{burgrx_url}/api/commitPipelinesStages?project={url_encoded_project}&branch={branch}&nbOfCommits=1&startAtCommit=0"

    try:
        releasability = polling.poll(
            lambda: get_latest_releasability_stage(requests.get(url, auth=HTTPBasicAuth(burgrx_user, burgrx_password)),
                                                   buildnumber), step=step, timeout=timeout)
        print(f"Releasability checks finished with status '{releasability['status']}'")
        return releasability
    except TimeoutException:
        print("Releasability timed out")
    except Exception as re:
        print(f"Cannot complete releasability checks: {re.message}")
    return False


def get_latest_releasability_stage(response: Response, buildnumber: str):
    print("Polling releasability status...")

    if response.status_code != 200:
        raise Exception(f"Error occurred while trying to retrieve current releasability status: {response}")

    jsonobjects = response.json()
    if len(jsonobjects) != 1:
        raise Exception(f"Unexpected response from burgrx: '{jsonobjects}'")

    pipelines = jsonobjects[0].get('pipelines') or []
    pipeline = next((x for x in pipelines if x.get('version') == buildnumber), None)
    if not pipeline:
        raise Exception(f"No pipeline found for version '{buildnumber}': {pipelines}")

    if not pipeline.get('releasable'):
        raise Exception(f"Pipeline '{pipeline}' is not releasable")

    stages = pipeline.get('stages') or []
    latest_releasability_stage = next((stage for stage in reversed(stages) if stage.get('type') == 'releasability'),
                                      None)
    if latest_releasability_stage and is_finished(latest_releasability_stage['status']):
        return latest_releasability_stage

    print("Releasability checks still running")
    return False


def is_finished(status: str):
    return status == 'errored' or status == 'failed' or status == 'passed'

