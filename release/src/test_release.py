import os
from main import repox_get_property_from_buildinfo, repox_get_module_property_from_buildinfo, get_artifacts_to_publish, get_version
from main import promote
from main import publish_all_artifacts, publish_artifact
from main import upload_to_binaries
from main import github_auth
from main import is_multi

def test_repox_get_property_from_buildinfo():
  project="sonar-dummy"
  buildnumber="359"
  repo = repox_get_property_from_buildinfo(project, buildnumber, 'buildInfo.env.ARTIFACTORY_DEPLOY_REPO')
  print(repo)
  assert repo == 'sonarsource-private-qa'

def test_promote():
  project="sonar-dummy"
  buildnumber="359"
  status = promote(project, buildnumber)  
  assert status == 'status:release'

def test_promote_multi():
  project="slang-enterprise"
  buildnumber="883"
  status = promote(project, buildnumber)  
  assert status == 'status:release'

def test_promote_fail():
  project="sonar-dummy"
  buildnumber="123"
  try:
    promote(project, buildnumber)  
  except Exception as e:
    print(f"Could not get repository for {project} {buildnumber} {str(e)}")
    assert 'unknown build' == str(e)
  


def test_get_artifacts_to_publish():
  project="sonar-dummy"
  buildnumber="359"
  artifacts = get_artifacts_to_publish(project,buildnumber)
  assert artifacts == 'com.sonarsource.dummy:sonar-dummy-plugin:jar'

def test_get_artifacts_to_publish_se():
  project="slang-enterprise"
  buildnumber="883"
  artifacts = get_artifacts_to_publish(project,buildnumber)
  print(f"artifacts: {artifacts}")
  #assert artifacts == 'com.sonarsource.dummy:sonar-dummy-plugin:jar'  

def test_publish_all_artifacts():
  print(publish_all_artifacts('sonar-dummy','344'))

def test_publish_all_artifacts_multi():
  print(publish_all_artifacts('slang-enterprise','883'))

def test_get_version():
  project="sonar-java"
  buildnumber="20657"
  version = get_version(project,buildnumber)
  print(version)

def test_upload_to_binaries():
  upload_to_binaries('sonarsource-public-releases','org.sonarsource.java','sonar-java-plugin','','jar','6.0.2.20657')

def test_github_auth():
  token=os.environ.get('GITHUB_TOKEN','no github token in env')  
  project='sonar-java'
  assert github_auth(token,project)

def test_github_auth_fail():
  token='wrongtoken'
  project='sonar-java'
  assert (github_auth(token,project) != True)

def test_is_multi():
  project="slang-enterprise"
  buildnumber="883"  
  assert is_multi(project,buildnumber)

def test_is_multi_not():
  project="sonar-dummy"
  buildnumber="359"  
  assert not is_multi(project,buildnumber)