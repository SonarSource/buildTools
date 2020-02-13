from main import repox_get_property_from_buildinfo, repox_get_module_property_from_buildinfo, get_artifacts_to_publish, get_version
from main import promote
from main import publish_all_artifacts, publish_artifact
from main import find_buildnumber_from_sha1
from main import upload_to_binaries
from main import github_auth

def test_repox_get_property_from_buildinfo():
  project="sonar-dummy"
  buildnumber="396"
  repo = repox_get_property_from_buildinfo(project, buildnumber, 'buildInfo.env.ARTIFACTORY_DEPLOY_REPO')
  assert repo == 'sonarsource-private-qa'

def test_promote():
  project="sonar-dummy"
  buildnumber="297"
  status = promote(project, buildnumber, "false")  
  assert status == 'status:release'

def test_get_artifacts_to_publish():
  project="sonar-dummy"
  buildnumber="297"
  artifacts = get_artifacts_to_publish(project,buildnumber)
  assert artifacts == 'com.sonarsource.dummy:sonar-dummy-plugin:jar'

def test_publish_all_artifacts():
  print(publish_all_artifacts('sonar-java','20657'))

def test_get_version():
  project="sonar-java"
  buildnumber="20657"
  version = get_version(project,buildnumber)
  print(version)
  
def test_find_buildnumber_from_sha1():
  assert find_buildnumber_from_sha1("2d8485ac2dede74680634b2a12665e8c9589dfae") == "20657"

def test_upload_to_binaries():
  upload_to_binaries('Distribution','sonarsource-public-releases','org.sonarsource.java','sonar-java-plugin','','jar','6.0.2.20657')

def test_github_auth():
  token='token'
  project='sonar-java'
  assert github_auth(token,project)

def test_github_auth_fail():
  token='wrongtoken'
  project='sonar-java'
  assert (github_auth(token,project) != True)