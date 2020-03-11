import os
import polling
import requests
import urllib
from flask import Request, make_response
from polling import TimeoutException
from requests.auth import HTTPBasicAuth
from requests.models import Response
from typing import Dict

burgrx_url = 'https://burgrx.sonarsource.com'
burgrx_user = os.environ.get('BURGRX_USER', 'no burgrx user in env')
burgrx_password = os.environ.get('BURGRX_PASSWORD', 'no burgrx password in env')

AUTHENTICATED = "authenticated"

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
      {functionBaseUrl}/releasability_check/GITHUB_ORG/GITHUB_PROJECT/VERSION
    """
    print("PATH:" + request.path)

    paths = request.path.split("/")
    if not paths or len(paths) != 4:
        return make_response("Bad Request", 400)

    _, organization, project, version = paths
    if organization != "SonarSource":
        return make_response("Unauthorized organization", 403)

    # Read branch from optional ?branch=xxx/yyy/zzz parameter
    branch = request.args.get('branch', 'master')

    try:
        authorization = validate_authorization_header(request.headers, project)
        if authorization == AUTHENTICATED:
            releasability = releasability_checks(project, version, branch)
            if releasability:
                return make_response(releasability)
            return make_response("Unexpected error occurred", 500)
        else:
            return make_response(authorization, 403)
    except Exception as e:
        print(f"Could not process request for {request.path}:", e)
        return make_response(str(e), 500)


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


def releasability_checks(project: str, version: str, branch: str):
    r"""Starts the releasability check operation. Post the start releasability HTTP request to Burgrx and polls until
      all checks have completed.

      :param project: Github project name, ex: 'sonar-dummy'
      :param version: full version to be checked for releasability.
      :return: True if releasability check succeeded, False otherwise.
      """

    print(f"Starting releasability check: {project}#{version}")
    url = f"{burgrx_url}/api/project/SonarSource/{project}/releasability/start/{version}"
    response = requests.post(url, auth=HTTPBasicAuth(burgrx_user, burgrx_password))
    message = response.json().get('message', '')
    if response.status_code == 200 and message == "done":
        print(f"Releasability checks started successfully")
        return start_polling_releasability_status(project, version, branch)
    else:
        print(f"Releasability checks failed to start: {response} '{message}'")
        raise Exception(f"Releasability checks failed to start: '{message}'")


def start_polling_releasability_status(project: str,
                                       version: str,
                                       branch: str,
                                       step: int = 4,
                                       timeout: int = 300,
                                       check_releasable: bool = True):
    r"""Starts polling Burgrx for latest releasability status.

      :param project: Github project name, ex: 'sonar-dummy'
      :param version: full version to be checked for releasability.
      :param step: step in seconds between polls. (For testing, otherwise use default value)
      :param timeout: timeout in seconds for attempting to get status. (For testing, otherwise use default value)
      :param check_releasable: whether should check for 'releasable' flag in json response. (For testing, otherwise use default value)
      :return: Metadata containing detailed releasability information, False if an unexpected error occurred.
      """

    url_encoded_project = urllib.parse.quote(f"SonarSource/{project}", safe='')
    url = f"{burgrx_url}/api/commitPipelinesStages?project={url_encoded_project}&branch={branch}&nbOfCommits=1&startAtCommit=0"

    try:
        releasability = polling.poll(
            lambda: get_latest_releasability_stage(requests.get(url, auth=HTTPBasicAuth(burgrx_user, burgrx_password)),
                                                   version,
                                                   check_releasable),
            step=step,
            timeout=timeout)
        print(f"Releasability checks finished with status '{releasability['status']}'")
        return releasability.get('metadata')
    except TimeoutException:
        print("Releasability timed out")
    except Exception as e:
        print(f"Cannot complete releasability checks:", e)
    return False


def get_latest_releasability_stage(response: Response, version: str, check_releasable: bool = True):
    print("Polling releasability status...")

    if response.status_code != 200:
        raise Exception(f"Error occurred while trying to retrieve current releasability status: {response}")

    jsonobjects = response.json()
    if len(jsonobjects) != 1:
        raise Exception(f"Unexpected response from burgrx: '{jsonobjects}'")

    pipelines = jsonobjects[0].get('pipelines') or []
    pipeline = next((x for x in pipelines if x.get('version') == version), None)
    if not pipeline:
        raise Exception(f"No pipeline found for version '{version}': {pipelines}")

    if check_releasable and not pipeline.get('releasable'):
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
