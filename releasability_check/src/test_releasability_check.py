import os
import time

import flask
import pytest
import responses
from requests import Response

from main import github_auth, validate_authorization_header, AUTHENTICATED, is_finished, get_latest_releasability_stage, \
    start_polling_releasability_status, releasability_checks, releasability_check


def test_validate_authorization_header():
    token = os.environ.get('GITHUB_TOKEN', 'no github token in env')
    headers = {'Authorization': f'token {token}'}
    project = 'sonar-dummy'
    assert validate_authorization_header(headers, project) == AUTHENTICATED


def test_validate_authorization_header_wrong_1():
    token = 'wrongtoken'
    headers = {'Authorization': f'token {token}'}
    project = 'sonar-dummy'
    assert validate_authorization_header(headers, project) == "Wrong access token"


def test_validate_authorization_header_wrong_2():
    headers = {'Authorization': 'token'}
    project = 'sonar-dummy'
    assert validate_authorization_header(headers, project) == "Wrong access token"


def test_validate_authorization_header_other():
    headers = {'Authorization': f'Basic base64String'}
    project = 'sonar-dummy'
    assert validate_authorization_header(headers, project) == "Wrong access token"


def test_validate_authorization_header_wrong_3():
    headers = {'Authorization': ''}
    project = 'sonar-dummy'
    assert validate_authorization_header(headers, project) == "Missing access token"


def test_validate_authorization_header_missing():
    headers = {}
    project = 'sonar-dummy'
    assert validate_authorization_header(headers, project) == "Missing access token"


def test_github_auth():
    token = os.environ.get('GITHUB_TOKEN', 'no github token in env')
    project = 'sonar-dummy'
    assert github_auth(token, project)


def test_github_auth_fail():
    token = 'wrongtoken'
    project = 'sonar-dummy'
    assert github_auth(token, project) is False


def test_is_finished():
    assert is_finished("passed")
    assert is_finished("errored")
    assert is_finished("failed")
    assert is_finished("created") is False
    assert is_finished("started") is False
    assert is_finished("anything else") is False


def test_get_latest_releasability_stage():
    buildnumber = "1"
    response = Response()
    response.status_code = 200
    response._content = b'[ { "pipelines": [ { "version": "1", "releasable": true, "stages": [ { "type": "releasability", "status": "passed" } ] } ] } ]'
    result = get_latest_releasability_stage(response, buildnumber)
    assert result == response.json()[0]['pipelines'][0]['stages'][0]
    assert result['status'] == "passed"

    response._content = b'''
    [ 
        { 
            "pipelines": 
                [
                    { "version": "0", "releasable": true } ,
                    { 
                        "version": "1",
                        "releasable": true,
                        "stages": 
                            [ 
                                { "type": "releasability", "status": "created" },
                                { "type": "releasability", "status": "passed" },
                                { "type": "releasability", "status": "errored" }
                            ]
                    } ,
                    { "version": "2", "releasable": true } 
                ] 
        } 
    ]
    '''
    result = get_latest_releasability_stage(response, buildnumber)
    assert result == response.json()[0]['pipelines'][1]['stages'][2]
    assert result['status'] == "errored"


def test_get_latest_releasability_stage_wrong_status_code():
    response = Response()
    response.status_code = 400
    with pytest.raises(Exception) as e:
        get_latest_releasability_stage(response, "1")
    assert "Error occurred while trying to retrieve current releasability status: <Response [400]>" in str(e.value)


def test_get_latest_releasability_stage_wrong_content():
    response = Response()
    response.status_code = 200

    response._content = b'[]'
    with pytest.raises(Exception) as e:
        get_latest_releasability_stage(response, "1")
    assert "No commit information found in burgrx for this branch" in str(e.value)

    response._content = b'[ {}, {} ]'
    with pytest.raises(Exception) as e:
        get_latest_releasability_stage(response, "1")
    assert "No pipeline info found for version '1'" in str(e.value)

    response._content = b'{}'
    with pytest.raises(Exception) as e:
        get_latest_releasability_stage(response, "1")
    assert "No commit information found in burgrx for this branch" in str(e.value)


def test_get_latest_releasability_stage_no_matching_pipeline():
    response = Response()
    response.status_code = 200

    response._content = b'[ {} ]'
    with pytest.raises(Exception) as e:
        get_latest_releasability_stage(response, "1")
    assert "No pipeline info found for version '1'" in str(e.value)

    response._content = b'[ { "pipelines": [] } ]'
    with pytest.raises(Exception) as e:
        get_latest_releasability_stage(response, "2")
    assert "No pipeline info found for version '2'" in str(e.value)

    response._content = b'[ { "pipelines": [ {} ] } ]'
    with pytest.raises(Exception) as e:
        get_latest_releasability_stage(response, "2")
    assert "No pipeline info found for version '2'" in str(e.value)

    response._content = b'[ { "pipelines": [ { "version": "2" } ] } ]'
    with pytest.raises(Exception) as e:
        get_latest_releasability_stage(response, "1")
    assert "No pipeline info found for version '1'" in str(e.value)


def test_get_latest_releasability_stage_not_releasable(capsys):
    response = Response()
    response.status_code = 200

    response._content = b'[ { "pipelines": [ { "version": "1" } ] } ]'
    result = get_latest_releasability_stage(response, "1", False)
    captured = capsys.readouterr()
    assert result is False
    assert captured.out == "Polling releasability status...\nReleasability checks still running\n"

    response._content = b'[ { "pipelines": [ { "version": "1" } ] } ]'
    with pytest.raises(Exception) as e:
        get_latest_releasability_stage(response, "1")
    assert "Pipeline '{'version': '1'}' is not releasable" in str(e.value)

    response._content = b'[ { "pipelines": [ { "version": "1", "releasable": false } ] } ]'
    with pytest.raises(Exception) as e:
        get_latest_releasability_stage(response, "1")
    assert "Pipeline '{'version': '1', 'releasable': False}' is not releasable" in str(e.value)


def test_get_latest_releasability_stage_unfinished_releasability(capsys):
    response = Response()
    response.status_code = 200

    response._content = b'[ { "pipelines": [ { "version": "1", "releasable": true } ] } ]'
    result = get_latest_releasability_stage(response, "1")
    captured = capsys.readouterr()
    assert result is False
    assert captured.out == "Polling releasability status...\nReleasability checks still running\n"

    response._content = b'[ { "pipelines": [ { "version": "1", "releasable": true, "stages": [ { "type": "other", "status": "passed" } ] } ] } ]'
    result = get_latest_releasability_stage(response, "1")
    captured = capsys.readouterr()
    assert result is False
    assert captured.out == "Polling releasability status...\nReleasability checks still running\n"

    response._content = b'[ { "pipelines": [ { "version": "1", "releasable": true, "stages": [ { "type": "releasability", "status": "created" } ] } ] } ]'
    result = get_latest_releasability_stage(response, "1")
    captured = capsys.readouterr()
    assert result is False
    assert captured.out == "Polling releasability status...\nReleasability checks still running\n"


@responses.activate
def test_start_polling_releasability_status():
    project = "sonar-dummy-oss"
    version = "1.0.0"
    branch = "master"
    nb_of_commits = 1

    responses.add(responses.GET,
                  f"https://burgrx.sonarsource.com/api/commitPipelinesStages?project=SonarSource%2F{project}&branch={branch}&nbOfCommits={nb_of_commits}&startAtCommit=0",
                  json=[{"pipelines": [{"version": "1.0.0", "releasable": True,
                                        "stages": [{"type": "releasability", "status": "passed"}]}]}],
                  status=200)

    result = start_polling_releasability_status(project, version, branch, nb_of_commits)
    assert result is None

    metadata = {"status": "ERRORED"}
    branch = "my-branch"
    nb_of_commits = 5
    responses.add(responses.GET,
                  f"https://burgrx.sonarsource.com/api/commitPipelinesStages?project=SonarSource%2F{project}&branch={branch}&nbOfCommits={nb_of_commits}&startAtCommit=0",
                  json=[{"pipelines": [{"version": "1.0.0", "releasable": True, "stages": [
                      {"type": "releasability", "status": "passed", "metadata": metadata}]}]}],
                  status=200)

    result = start_polling_releasability_status(project, version, branch, nb_of_commits)
    assert result == metadata


@responses.activate
def test_start_polling_releasability_status_timeout(capsys):
    project = "sonar-dummy-oss"
    version = "1.0.0"
    branch = "master"
    nb_of_commits = 1

    def request_callback(request):
        time.sleep(2)
        return 200, {}, b'[ { "pipelines": [ { "version": "1.0.0", "releasable": true } ] } ]'

    responses.add_callback(responses.GET,
                           f"https://burgrx.sonarsource.com/api/commitPipelinesStages?project=SonarSource%2F{project}&branch={branch}&nbOfCommits={nb_of_commits}&startAtCommit=0",
                           callback=request_callback,
                           content_type='application/json')

    with pytest.raises(Exception) as e:
        start_polling_releasability_status(project, version, branch, nb_of_commits, 10, 1)

    captured = capsys.readouterr()
    assert str(e.value) == "Releasability timed out"
    assert captured.out == "Polling releasability status...\nReleasability checks still running\nReleasability timed out\n"


@responses.activate
def test_start_polling_releasability_status_fail(capsys):
    project = "sonar-dummy-oss"
    version = "1.0.0"
    branch = "master"
    nb_of_commits = 1

    def request_callback(request):
        return 200, {}, b'{}'

    responses.add_callback(responses.GET,
                           f"https://burgrx.sonarsource.com/api/commitPipelinesStages?project=SonarSource%2F{project}&branch={branch}&nbOfCommits={nb_of_commits}&startAtCommit=0",
                           callback=request_callback,
                           content_type='application/json')

    with pytest.raises(Exception) as e:
        start_polling_releasability_status(project, version, branch, nb_of_commits)

    captured = capsys.readouterr()
    assert str(e.value) == "No commit information found in burgrx for this branch"
    assert captured.out == "Polling releasability status...\nCannot complete releasability checks: No commit information found in burgrx for this branch\n"


@responses.activate
def test_releasability_checks():
    project = "sonar-dummy-oss"
    version = "1.0.0"
    metadata = {"status": "ERRORED"}

    responses.add(responses.POST,
                  f"https://burgrx.sonarsource.com/api/project/SonarSource/{project}/releasability/start/{version}",
                  json={"message": "done"},
                  status=200)

    responses.add(responses.GET,
                  f"https://burgrx.sonarsource.com/api/commitPipelinesStages?project=SonarSource%2F{project}&branch=master&nbOfCommits=1&startAtCommit=0",
                  json=[{"pipelines": [{"version": "1.0.0", "releasable": True, "stages": [
                      {"type": "releasability", "status": "passed", "metadata": metadata}]}]}],
                  status=200)

    result = releasability_checks(project, version, 'master', 1)
    assert result == metadata


@responses.activate
def test_releasability_checks_fail(capsys):
    project = "sonar-dummy-oss"
    version = "1.0.0"

    responses.add(responses.POST,
                  f"https://burgrx.sonarsource.com/api/project/SonarSource/{project}/releasability/start/{version}",
                  json={},
                  status=200)

    with pytest.raises(Exception) as e:
        releasability_checks(project, version, 'master', 1)
    captured = capsys.readouterr()
    assert str(e.value) == "Releasability checks failed to start: ''"
    assert captured.out == "Starting releasability check: sonar-dummy-oss#1.0.0\nReleasability checks failed to start: <Response [200]> ''\n"

    responses.replace(responses.POST,
                      f"https://burgrx.sonarsource.com/api/project/SonarSource/{project}/releasability/start/{version}",
                      json={"message": "no promoted artifact found"},
                      status=200)

    with pytest.raises(Exception) as e:
        releasability_checks(project, version, 'master', 1)
    captured = capsys.readouterr()
    assert str(e.value) == "Releasability checks failed to start: 'no promoted artifact found'"
    assert captured.out == "Starting releasability check: sonar-dummy-oss#1.0.0\nReleasability checks failed to start: <Response [200]> 'no promoted artifact found'\n"

    responses.replace(responses.POST,
                      f"https://burgrx.sonarsource.com/api/project/SonarSource/{project}/releasability/start/{version}",
                      json={"message": "done"},
                      status=400)

    with pytest.raises(Exception) as e:
        releasability_checks(project, version, 'master', 1)
    captured = capsys.readouterr()
    assert str(e.value) == "Releasability checks failed to start: 'done'"
    assert captured.out == "Starting releasability check: sonar-dummy-oss#1.0.0\nReleasability checks failed to start: <Response [400]> 'done'\n"

    responses.replace(responses.POST,
                      f"https://burgrx.sonarsource.com/api/project/SonarSource/{project}/releasability/start/{version}",
                      json={"message": "done"},
                      status=200)
    responses.add(responses.GET,
                  f"https://burgrx.sonarsource.com/api/commitPipelinesStages?project=SonarSource%2F{project}&branch=master&nbOfCommits=1&startAtCommit=0",
                  json=[{"pipelines": []}],
                  status=200)

    with pytest.raises(Exception) as e:
        releasability_checks(project, version, 'master', 1)
    captured = capsys.readouterr()
    assert str(e.value) == "No pipeline info found for version '1.0.0'"
    assert "Cannot complete releasability checks: No pipeline info found for version '1.0.0'" in captured.out


@responses.activate
def test_releasability_check():
    headers = {'Authorization': 'token myMockedToken'}
    project = "sonar-dummy"
    version = "1.0.0.222"
    metadata = {"status": "ERRORED"}

    responses.add(responses.GET,
                  "https://api.github.com/repos/SonarSource/sonar-dummy",
                  json={"permissions": {"push": True}},
                  status=200)

    responses.add(responses.POST,
                  f"https://burgrx.sonarsource.com/api/project/SonarSource/{project}/releasability/start/{version}",
                  json={"message": "done"},
                  status=200)

    responses.add(responses.GET,
                  f"https://burgrx.sonarsource.com/api/commitPipelinesStages?project=SonarSource%2F{project}&branch=master&nbOfCommits=5&startAtCommit=0",
                  json=[{"pipelines": [{"version": "1.0.0.222", "releasable": True, "stages": [
                      {"type": "releasability", "status": "passed", "metadata": metadata}]}]}],
                  status=200)

    app = flask.Flask(__name__)
    with app.test_request_context("/SonarSource/sonar-dummy/1.0.0.222", headers=headers):
        result = releasability_check(flask.request)

    assert result.status_code == 200
    assert result.data == b'{"status":"ERRORED"}\n'

    metadata = {"status": "PASSED"}
    responses.add(responses.GET,
                  f"https://burgrx.sonarsource.com/api/commitPipelinesStages?project=SonarSource%2F{project}&branch=branch1&nbOfCommits=10&startAtCommit=0",
                  json=[{"pipelines": [{"version": "1.0.0.222", "releasable": True, "stages": [
                      {"type": "releasability", "status": "passed", "metadata": metadata}]}]}],
                  status=200)

    with app.test_request_context("/SonarSource/sonar-dummy/1.0.0.222?branch=branch1&nbOfCommits=10", headers=headers):
        result = releasability_check(flask.request)

    assert result.status_code == 200
    assert result.data == b'{"status":"PASSED"}\n'


@responses.activate
def test_releasability_check_error_forwarded():
    headers = {'Authorization': 'token myMockedToken'}
    project = "sonar-dummy"
    version = "1.0.0.223"
    metadata = {"status": "PASSED"}

    responses.add(responses.GET,
                  "https://api.github.com/repos/SonarSource/sonar-dummy",
                  json={"permissions": {"push": True}},
                  status=200)

    responses.add(responses.POST,
                  f"https://burgrx.sonarsource.com/api/project/SonarSource/{project}/releasability/start/{version}",
                  json={"message": "done"},
                  status=200)

    responses.add(responses.GET,
                  f"https://burgrx.sonarsource.com/api/commitPipelinesStages?project=SonarSource%2F{project}&branch=master&nbOfCommits=5&startAtCommit=0",
                  json=[{"pipelines": [{"version": "1.0.0.222", "releasable": True, "stages": [
                      {"type": "releasability", "status": "passed", "metadata": metadata}]}]}],
                  status=200)

    app = flask.Flask(__name__)
    with app.test_request_context("/SonarSource/sonar-dummy/1.0.0.223", headers=headers):
        result = releasability_check(flask.request)

    assert result.status_code == 500
    assert result.data == b"No pipeline info found for version '1.0.0.223'"


@responses.activate
def test_releasability_no_artifact():
    headers = {'Authorization': 'token myMockedToken'}
    project = "sonar-dummy"
    version = "1.0.0.222"

    responses.add(responses.GET,
                  "https://api.github.com/repos/SonarSource/sonar-dummy",
                  json={"permissions": {"push": True}},
                  status=200)

    responses.add(responses.POST,
                  f"https://burgrx.sonarsource.com/api/project/SonarSource/{project}/releasability/start/{version}",
                  json={"message": "no promoted artifact found"},
                  status=404)

    app = flask.Flask(__name__)
    with app.test_request_context("/SonarSource/sonar-dummy/1.0.0.222", headers=headers):
        result = releasability_check(flask.request)

    assert result.status_code == 500
    assert result.data == b"Releasability checks failed to start: 'no promoted artifact found'"


@responses.activate
def test_releasability_check_fail():
    headers = {'Authorization': 'token myMockedToken'}
    responses.add(responses.GET,
                  "https://api.github.com/repos/SonarSource/sonar-dummy",
                  json={"permissions": {"push": False}},
                  status=200)

    app = flask.Flask(__name__)
    with app.test_request_context("/SonarSource/sonar-dummy/1.0.0.222", headers=headers):
        result = releasability_check(flask.request)

    assert result.status_code == 403
    assert result.data == b"Wrong access token"


def test_releasability_check_bad_request():
    app = flask.Flask(__name__)
    with app.test_request_context("/SonarSource"):
        result = releasability_check(flask.request)

    assert result.status_code == 400
    assert result.data == b"Bad Request"


def test_releasability_check_unauthorized_org():
    app = flask.Flask(__name__)
    with app.test_request_context("/AnotherOrg/sonar-dummy/3629c526389c15049fc5ca37de395746ade2991b"):
        result = releasability_check(flask.request)

    assert result.status_code == 403
    assert result.data == b"Unauthorized organization"
