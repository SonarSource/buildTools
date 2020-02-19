import os
import pytest
from requests import Response

from main import get_version, find_buildnumber_from_sha1, github_auth, validate_authorization_header, AUTHENTICATED, \
    is_finished, get_latest_releasability_stage

# ToDo import responses -> mock responses
# ToDo public project
# ToDo private project
# ToDo sort releasability by number ?
'''
def test_releasability_check():
    project = "sonar-dummy"
    buildnumber = "396"
    status = ""  # promote(project, buildnumber, "false")
    assert status == 'status:release'


def test_releasability_check_fail():
    project = "sonar-dummy"
    buildnumber = "123"
    try:
        promote(project, buildnumber, "false")
    except Exception as e:
        print(f"Could not get repository for {project} {buildnumber} {str(e)}")
        assert 'unknown build' == str(e)




'''


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


def test_find_buildnumber_from_sha1():
    assert find_buildnumber_from_sha1("a80cfd8f9409690a3204ab7feaaeac19f1bed834") == "322"


def test_find_buildnumber_from_sha1_fail():
    with pytest.raises(Exception) as e:
        find_buildnumber_from_sha1("a80cfd8f9409690a3204ab7feaaeac19f1bed835")
    assert "Unexpected number of results found for sha1 'a80cfd8f9409690a3204ab7feaaeac19f1bed835'. Found: '[]'" in str(
        e.value)


def test_get_version():
    project = "sonar-dummy"
    buildnumber = "322"
    version = get_version(project, buildnumber)
    assert version == "10.0.0.322"


def test_get_version_fail():
    with pytest.raises(Exception) as e:
        project = "sonar-dummy-no-project"
        buildnumber = "322"
        get_version(project, buildnumber)
    assert "unknown build" in str(e.value)


def test_github_auth():
    token = os.environ.get('GITHUB_TOKEN', 'no github token in env')
    project = 'sonar-dummy'
    assert github_auth(token, project)


def test_github_auth_fail():
    token = 'wrongtoken'
    project = 'sonar-dummy'
    assert github_auth(token, project) == False


def test_is_finished():
    assert is_finished("passed")
    assert is_finished("errored")
    assert is_finished("failed")
    assert is_finished("created") == False
    assert is_finished("started") == False
    assert is_finished("anything else") == False


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
    assert "Unexpected response from burgrx: '[]'" in str(e.value)

    response._content = b'[ {}, {} ]'
    with pytest.raises(Exception) as e:
        get_latest_releasability_stage(response, "1")
    assert "Unexpected response from burgrx: '[{}, {}]'" in str(e.value)

    response._content = b'{}'
    with pytest.raises(Exception) as e:
        get_latest_releasability_stage(response, "1")
    assert "Unexpected response from burgrx: '{}'" in str(e.value)


def test_get_latest_releasability_stage_no_matching_pipeline():
    response = Response()
    response.status_code = 200

    response._content = b'[ {} ]'
    with pytest.raises(Exception) as e:
        get_latest_releasability_stage(response, "1")
    assert "No pipeline found for version '1': []" in str(e.value)

    response._content = b'[ { "pipelines": [] } ]'
    with pytest.raises(Exception) as e:
        get_latest_releasability_stage(response, "2")
    assert "No pipeline found for version '2': []" in str(e.value)

    response._content = b'[ { "pipelines": [ {} ] } ]'
    with pytest.raises(Exception) as e:
        get_latest_releasability_stage(response, "2")
    assert "No pipeline found for version '2': [{}]" in str(e.value)

    response._content = b'[ { "pipelines": [ { "version": "2" } ] } ]'
    with pytest.raises(Exception) as e:
        get_latest_releasability_stage(response, "1")
    assert "No pipeline found for version '1': [{'version': '2'}]" in str(e.value)


def test_get_latest_releasability_stage_not_releasable():
    response = Response()
    response.status_code = 200

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
    assert result == False
    assert captured.out == "Polling releasability status...\nReleasability checks still running\n"

    response._content = b'[ { "pipelines": [ { "version": "1", "releasable": true, "stages": [ { "type": "other", "status": "passed" } ] } ] } ]'
    result = get_latest_releasability_stage(response, "1")
    captured = capsys.readouterr()
    assert result == False
    assert captured.out == "Polling releasability status...\nReleasability checks still running\n"

    response._content = b'[ { "pipelines": [ { "version": "1", "releasable": true, "stages": [ { "type": "releasability", "status": "created" } ] } ] } ]'
    result = get_latest_releasability_stage(response, "1")
    captured = capsys.readouterr()
    assert result == False
    assert captured.out == "Polling releasability status...\nReleasability checks still running\n"
