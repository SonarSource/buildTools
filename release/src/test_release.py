from main import *

sonar_dummy_request = ReleaseRequest('SonarSource', 'sonar-dummy', '422')
sonar_dummy_build_info = repox_get_build_info(sonar_dummy_request)

sonar_dummy_oss_request = ReleaseRequest('SonarSource', 'sonar-dummy-oss', '1386')
sonar_dummy_oss_build_info = repox_get_build_info(sonar_dummy_oss_request)

slang_enterprise_request = ReleaseRequest('SonarSource', 'slang-enterprise', '883')
slang_enterprise_build_info = repox_get_build_info(slang_enterprise_request)

sonar_security_request = ReleaseRequest('SonarSource', 'sonar-security', '1259')
sonar_security_build_info = repox_get_build_info(sonar_security_request)

sonarlint_org_request = ReleaseRequest('SonarSource', 'www.sonarlint.org', '1075')
sonarlint_org_build_info = repox_get_build_info(sonarlint_org_request)

def test_request_is_sonarlint():
  assert ReleaseRequest('SonarSource', 'sonarlint-core', '12345').is_sonarlint()

def test_request_is_not_sonarlint():
  assert not ReleaseRequest('SonarSource', 'sonar-java', '23456').is_sonarlint()

def test_repox_get_property_from_buildinfo():
  repo = repox_get_property_from_buildinfo(sonar_dummy_build_info, 'buildInfo.env.ARTIFACTORY_DEPLOY_REPO')
  print(repo)
  assert repo == 'sonarsource-private-qa'

def test_promote():
  status = promote(sonar_dummy_request, sonar_dummy_build_info)
  assert status == 'status:release'

def test_promote_multi():
  status = promote(slang_enterprise_request, slang_enterprise_build_info)
  assert status == 'status:release'

def test_promote_fail():
  request = ReleaseRequest('SonarSource', 'sonar-dummy', '359')
  try:
    promote(request, repox_get_build_info(request))
  except Exception as e:
    print(f"Could not get repository for {request.project} {request.buildnumber} {str(e)}")
    assert 'unknown build' == str(e)


def test_get_artifacts_to_publish():
  artifacts = get_artifacts_to_publish(sonar_dummy_build_info)
  assert artifacts == 'com.sonarsource.dummy:sonar-dummy-plugin:jar'

def test_get_artifacts_to_publish_empty():
  artifacts = get_artifacts_to_publish(sonarlint_org_build_info)
  assert artifacts == None

def test_get_artifacts_to_publish_se():
  artifacts = get_artifacts_to_publish(slang_enterprise_build_info)
  print(f"artifacts: {artifacts}")

def test_publish_all_artifacts():
  print(publish_all_artifacts(sonar_dummy_request, sonar_dummy_build_info))

def test_publish_all_artifacts_empty():
  print(publish_all_artifacts(sonarlint_org_request, sonarlint_org_build_info))

def test_publish_all_artifacts_multi():
  print(publish_all_artifacts(slang_enterprise_request, slang_enterprise_build_info))

def test_get_version():
  version = get_version(repox_get_build_info(ReleaseRequest('SonarSource', 'sonar-java', '20657')))
  print(version)

def test_upload():
  upload(sonar_dummy_request,'sonarsource-private-releases','com.sonarsource.dummy','sonar-dummy-plugin','','jar','10.0.0.422')


def test_github_auth():
  token=os.environ.get('GITHUB_TOKEN','no github token in env')  
  project='sonar-java'
  assert github_auth(token,project)

def test_github_auth_fail():
  token='wrongtoken'
  project='sonar-java'
  assert (github_auth(token,project) != True)

def test_is_multi():
  assert is_multi(slang_enterprise_build_info)

def test_is_multi_not():
  assert not is_multi(sonar_dummy_build_info)

def test_check_public_not():
  assert not check_public(sonar_dummy_build_info)

def test_check_public():
  assert check_public(sonar_dummy_oss_build_info)

def test_check_public_empty():
  assert not check_public(sonarlint_org_build_info)

def test_distribute_build(capsys):
  project="sonar-dummy-oss"
  buildnumber="1386"  
  distribute_build(project, buildnumber)  
  captured = capsys.readouterr()
  print(captured)
  assert "pushed to bintray" in captured.out

def test_distribute_build_fail(capsys):
  project="sonar-dummy"
  buildnumber="359"  
  distribute_build(project, buildnumber)    
  captured = capsys.readouterr()
  print(captured)
  assert "Failed to distribute sonar-dummy" in captured.out 

def test_get_cirrus_repository_id():
  assert get_cirrus_repository_id("sonar-security") == '5219385735643136'

def test_rules_cov():
  rules_cov(sonar_security_request,sonar_security_build_info)

def test_get_release_id():
  release_info = get_release_info(sonar_dummy_request, "10.0.0.387")
  assert "24468455" == str(release_info.get('id'))