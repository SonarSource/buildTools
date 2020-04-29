import os
import requests
import json
import urllib.request
import paramiko
import yaml
from scp import SCPClient
from flask import make_response
from datetime import datetime, timezone
from requests.auth import HTTPBasicAuth

artifactory_apikey=os.environ.get('ARTIFACTORY_API_KEY','no api key in env')
passphrase=os.environ.get('GPG_PASSPHRASE','no GPG_PASSPHRASE in env')

binaries_path_prefix=os.environ.get('PATH_PREFIX','/tmp')

#burgr
burgrx_url = 'https://burgrx.sonarsource.com'
burgrx_user = os.environ.get('BURGRX_USER', 'no burgrx user in env')
burgrx_password = os.environ.get('BURGRX_PASSWORD', 'no burgrx password in env')

#rules-cov
cirrus_token=os.environ.get('CIRRUS_TOKEN','no cirrus token in env')
cirrus_api_url="https://api.cirrus-ci.com/graphql"
owner="SonarSource"

#repox
artifactory_url='https://repox.jfrog.io/repox'
binaries_host='binaries.sonarsource.com'
binaries_url=f"https://{binaries_host}"
ssh_user='ssuopsa'
ssh_key='id_rsa_ssuopsa'
AUTHENTICATED="authenticated"
OSS_REPO="Distribution"
COMMERCIAL_REPO="CommercialDistribution"
bintray_target_repo="SonarQube-bintray"

#github
githup_api_url="https://api.github.com"
github_token=os.environ.get('GITHUB_TOKEN','no github token in env')
attach_to_github_release=None

content_type_json='application/json'
content_type_zip='application/zip'

class ReleaseRequest:
  def __init__(self, org, project, buildnumber):
    self.org = org
    self.project = project
    self.buildnumber = buildnumber

  def is_sonarlint(self):
    return self.project.startswith('sonarlint-')

# [START functions_promote_http]
def release(request):
  """HTTP Cloud Function.
  Args:
    request (flask.Request): The request object.
    <http://flask.pocoo.org/docs/1.0/api/#flask.Request>
  Returns:
    The response text, or any set of values that can be turned into a
    Response object using `make_response`
    <http://flask.pocoo.org/docs/1.0/api/#flask.Flask.make_response>.
  Trigger:
    {functionBaseUrl}/promote/GITHUB_ORG/GITHUB_PROJECT/BUILD_NUMBER
  """
  print("PATH:"+request.path)
  _, org, project, buildnumber = request.path.split("/")
  global attach_to_github_release
  attach_to_github_release = request.args.get('attach') == "true"
  if attach_to_github_release:
    print("Attaching artifacts to github release")
  else:
    print("No attachement to github release")
  release_request = ReleaseRequest(org, project, buildnumber)
  buildinfo=repox_get_build_info(release_request)
  authorization_result = validate_authorization_header(request, project)
  if authorization_result == AUTHENTICATED:
    try:
      promote(release_request, buildinfo)
      publish_all_artifacts(release_request,buildinfo)
      notify_burgr(release_request,buildinfo,'passed')
      if not release_request.is_sonarlint():
        if check_public(buildinfo):
          distribute_build(project,buildnumber)
        rules_cov(release_request,buildinfo)
    except Exception as e:
      notify_burgr(release_request,buildinfo,'failed')
      print(f"Could not get repository for {project} {buildnumber} {str(e)}")
      return make_response(str(e),500)
  else:
    return make_response(authorization_result, 403)

def github_auth(token,project):
  url = f"https://api.github.com/repos/SonarSource/{project}"
  headers = {'Authorization': f"token {token}"}
  r = requests.get(url, headers=headers)
  if r.status_code == 200:
    permissions = r.json().get('permissions')
    return permissions and (permissions.get('push') or permissions.get('admin'))
  return False

def validate_authorization_header(request, project):
  if request.headers['Authorization'] and request.headers['Authorization'].split()[0] == 'token':
    global github_token
    github_token=request.headers['Authorization'].split()[1]
    if github_auth(github_token,project):

      print("Authenticated with github token")
      return AUTHENTICATED
    else:
      return "Wrong access token"
  else:
    return "Missing access token"

def repox_get_property_from_buildinfo(buildinfo, property, default=""):
  try:
    return buildinfo['buildInfo']['properties'][property]
  except:
    return default

def repox_get_module_property_from_buildinfo(buildinfo, property):
  return buildinfo['buildInfo']['modules'][0]['properties'][property]

def get_version(buildinfo):
  return buildinfo['buildInfo']['modules'][0]['id'].split(":")[-1]

def repox_get_build_info(release_request):
  url = f"{artifactory_url}/api/build/{release_request.project}/{release_request.buildnumber}"
  headers = {'content-type': content_type_json, 'X-JFrog-Art-Api': artifactory_apikey}
  r = requests.get(url, headers=headers)
  buildinfo = r.json()
  if r.status_code == 200:
    return buildinfo
  else:
    print(r.status_code)
    print(r.content)
    raise Exception('unknown build')

def get_artifacts_to_publish(buildinfo):
  artifacts = None
  try:
    artifacts = repox_get_module_property_from_buildinfo(buildinfo,'artifactsToPublish')
  except:
    try:
      artifacts = repox_get_property_from_buildinfo(buildinfo, 'buildInfo.env.ARTIFACTS_TO_PUBLISH')
    except:
      print("no artifacts to publish")
  return artifacts

def publish_all_artifacts(release_request,buildinfo):
  print(f"publishing artifacts for {release_request.project}#{release_request.buildnumber}")
  release_url = ""
  repo = repox_get_property_from_buildinfo(buildinfo, 'buildInfo.env.ARTIFACTORY_DEPLOY_REPO').replace('qa', 'builds')
  version=get_version(buildinfo)
  allartifacts=get_artifacts_to_publish(buildinfo)
  if allartifacts:
    print(f"publishing: {allartifacts}")
    artifacts = allartifacts.split(",")
    artifacts_count = len(artifacts)
    if artifacts_count == 1:
      print("only 1")
      return publish_artifact(release_request,artifacts[0],version,repo)
    print(f"{artifacts_count} artifacts")
    for i in range(0, artifacts_count):
      print(f"artifact {artifacts[i]}")
      release_url = publish_artifact(release_request,artifacts[i],version,repo)
  return release_url



def publish_artifact(release_request,artifact_to_publish,version,repo):
  print(f"publishing {artifact_to_publish}#{version}")
  artifact = artifact_to_publish.split(":")
  gid = artifact[0]
  aid = artifact[1]
  ext = artifact[2]
  qual = ''
  artifactory_repo = repo.replace('builds', 'releases')
  print(f"{gid} {aid} {ext}")
  return upload(release_request,artifactory_repo,gid,aid,qual,ext,version)

def is_multi(buildinfo):
  allartifacts=get_artifacts_to_publish(buildinfo)
  if allartifacts:
    artifacts = allartifacts.split(",")
    artifacts_count = len(artifacts)
    if artifacts_count == 1:
      return False
    ref=artifacts[0][0:3]
    for i in range(0, artifacts_count):
      current=artifacts[i - 1][0:3]
      if current != ref:
        return True
  return False


def promote(release_request,buildinfo):
  targetrepo="sonarsource-public-releases"
  status='released'

  repo = repox_get_property_from_buildinfo(buildinfo, 'buildInfo.env.ARTIFACTORY_DEPLOY_REPO')
  targetrepo = repo.replace('qa', 'releases')

  print(f"Promoting build {release_request.project}#{release_request.buildnumber} to {targetrepo}")
  json_payload={
      "status": f"{status}",
      "targetRepo": f"{targetrepo}"
  }

  if is_multi(buildinfo):
    print(f"Promoting multi repositories")
    url = f"{artifactory_url}/api/plugins/execute/multiRepoPromote?params=buildName={release_request.project};buildNumber={release_request.buildnumber};src1=sonarsource-private-builds;target1=sonarsource-private-releases;src2=sonarsource-public-builds;target2=sonarsource-public-releases;status={status}"
    headers = {'X-JFrog-Art-Api': artifactory_apikey}
    r = requests.get(url, headers=headers)
  else:
    url = f"{artifactory_url}/api/build/promote/{release_request.project}/{release_request.buildnumber}"
    headers = {'content-type': content_type_json, 'X-JFrog-Art-Api': artifactory_apikey}
    r = requests.post(url, data=json.dumps(json_payload), headers=headers)
  if r.status_code == 200:
    return f"status:{status}"
  else:
    return f"status:{status} code:{r.status_code}"


def upload(release_request,artifactory_repo,gid,aid,qual,ext,version):
  binaries_repo=OSS_REPO
  #download artifact
  gid_path=gid.replace(".", "/")
  if gid.startswith('com.'):
    artifactory_repo=artifactory_repo.replace('public', 'private')
    binaries_repo=COMMERCIAL_REPO
  artifactory=artifactory_url+"/"+artifactory_repo

  filename=f"{aid}-{version}.{ext}"
  if qual:
    filename=f"{aid}-{version}-{qual}.{ext}"
  url=f"{artifactory}/{gid_path}/{aid}/{version}/{filename}"
  print(url)
  opener = urllib.request.build_opener()
  opener.addheaders = [('X-JFrog-Art-Api', artifactory_apikey)]
  urllib.request.install_opener(opener)
  #for sonarqube rename artifact from sonar-application.zip to sonarqube.zip
  if aid == "sonar-application":
    filename=f"sonarqube-{version}.zip"
    aid="sonarqube"
  tempfile=f"/tmp/{filename}"
  urllib.request.urlretrieve(url, tempfile)
  print(f'downloaded {tempfile}')
  #upload artifact
  ssh_client=paramiko.SSHClient()
  ssh_client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
  ssh_client.connect(hostname=binaries_host, username=ssh_user, key_filename=ssh_key)
  #SonarLint Eclipse is uploaded to a special directory
  if aid == "org.sonarlint.eclipse.site":
    directory=f"{binaries_path_prefix}/SonarLint-for-Eclipse/releases"
    release_url = f"{binaries_url}/SonarLint-for-Eclipse/releases/{filename}"
  else:
    directory=f"{binaries_path_prefix}/{binaries_repo}/{aid}"
    release_url = f"{binaries_url}/{binaries_repo}/{aid}/{filename}"
  #create directory
  exec_ssh_command(ssh_client, f"mkdir -p {directory}")
  print(f'created {directory}')
  scp = SCPClient(ssh_client.get_transport())
  print('scp connexion created')
  #upload file to binaries
  scp.put(tempfile, remote_path=directory)
  print(f'uploaded {tempfile} to {directory}')
  scp.close()
  # SonarLint Eclipse is also unzipped on binaries for compatibility with P2 client
  if aid == "org.sonarlint.eclipse.site":
    sle_unzip_dir = f"{directory}/{version}"
    exec_ssh_command(ssh_client, f"mkdir -p {sle_unzip_dir}")
    exec_ssh_command(ssh_client, f"cd {sle_unzip_dir} && unzip ../org.sonarlint.eclipse.site-{version}.zip")
  #upload file to github
  print(f"attach_to_github_release:{attach_to_github_release}")
  if attach_to_github_release:
    print(f"attaching {filename} to github release {version}")
    release_info=get_release_info(release_request,version)
    attach_asset_to_github_release(release_info,tempfile,filename)
  else:
    print("no attachment to github release")
  #sign file
  exec_ssh_command(ssh_client, f"gpg --batch --passphrase {passphrase} --armor --detach-sig --default-key infra@sonarsource.com {directory}/{filename}")
  print(f'signed {directory}/{filename}')
  ssh_client.close()
  return release_url

def exec_ssh_command(ssh_client, command):
  stdin,stdout,stderr=ssh_client.exec_command(command)
  stdout_contents = '\n'.join(stdout.readlines())
  print(f"stdout: {stdout_contents}")
  stderr_contents = '\n'.join(stderr.readlines())
  print(f"stderr: {stderr_contents}")
  if stderr_contents:
    raise Exception(f"Error during the SSH command '{command}': {stderr_contents}")

# This will only work for a branch build, not a PR build
# because a PR build notification needs `"pr_number": NUMBER` instead of `'branch': NAME`
def notify_burgr(release_request,buildinfo,status):
  branch=repox_get_property_from_buildinfo(buildinfo, 'buildInfo.env.GITHUB_BRANCH',"master")
  sha1=repox_get_property_from_buildinfo(buildinfo, 'buildInfo.env.GIT_SHA1')
  payload={
    'repository': f"{release_request.org}/{release_request.project}",
    'pipeline': release_request.buildnumber,
    'name': 'RELEASE',
    'system': 'github',
    'type': 'release',
    'number': release_request.buildnumber,
    'branch': branch,
    'sha1': sha1,
    'url':f"https://github.com/{release_request.org}/{release_request.project}/releases",
    'status': status,
    'metadata': '',
    'started_at':datetime.now(timezone.utc).astimezone().isoformat(),
    'finished_at':datetime.now(timezone.utc).astimezone().isoformat()
  }
  print(f"burgr payload:{payload}")
  url=f"{burgrx_url}/api/stage"
  r = requests.post(url, json=payload, auth=HTTPBasicAuth(burgrx_user, burgrx_password))
  if r.status_code != 201:
    print(f"burgr notification failed code:{r.status_code}" )

def check_public(buildinfo):
  artifacts = get_artifacts_to_publish(buildinfo)
  if artifacts:
    return "org.sonarsource" in artifacts
  else:
    return False

def distribute_build(project,buildnumber):
  print(f"Distributing {project}#{buildnumber} to bintray")
  payload={
    "targetRepo": bintray_target_repo,
    "sourceRepos" : ["sonarsource-public-releases"]
  }
  url=f"{artifactory_url}/api/build/distribute/{project}/{buildnumber}"
  headers = {'content-type': content_type_json, 'X-JFrog-Art-Api': artifactory_apikey}
  try:
    r = requests.post(url, json=payload, headers=headers)
    r.raise_for_status()
    if r.status_code == 200:
      print(f"{project}#{buildnumber} pushed to bintray ready to sync to central")
  except requests.exceptions.HTTPError as err:
    print(f"Failed to distribute {project}#{buildnumber} {err}")


def get_cirrus_repository_id(project):
  url = cirrus_api_url
  headers = {'Authorization': f"Bearer {cirrus_token}"}
  payload = {
    "query":f"query GitHubRepositoryQuery {{githubRepository(owner:\"{owner}\",name:\"{project}\"){{id}}}}"
    }
  try:
    r = requests.post(url, json=payload, headers=headers)
    r.raise_for_status()
    if r.status_code == 200:
      repository_id=r.json()["data"]["githubRepository"]["id"]
      print(f"Found cirrus repository_id for {project}:{repository_id}")
      return repository_id
    else:
      raise Exception("Invalid return code while retrieving repository id")
  except Exception as err:
    error=f"Failed to get repository id for {project} {err}"
    print(error)
    raise Exception(error)

def rules_cov(release_request,buildinfo):
  print(f"Triggering rules-cov for {release_request.project}#{release_request.buildnumber}")
  rulescov_repos="rules-cov"
  repository_id=get_cirrus_repository_id(rulescov_repos)
  version=get_version(buildinfo)
  f = open("config.yml","r")
  config = f.read()
  data = yaml.safe_load(config)
  data['run_task']['env'].update(dict(SLUG=f"{owner}/{release_request.project}", VERSION=version))
  config = yaml.dump(data)
  url = cirrus_api_url
  headers = {'Authorization': f"Bearer {cirrus_token}"}
  payload = {
    "query": f"mutation CreateBuildDialogMutation($input: RepositoryCreateBuildInput!) {{createBuild(input: $input) {{build {{id}}}}}}",
    "variables": {
      "input": {
        "clientMutationId": f"{rulescov_repos}",
        "repositoryId": f"{repository_id}",
        "branch": "run",
        "sha": "",
        "configOverride": f"{config}"
        }
      }
    }
  error=f"Failed to trigger rules-cov for {release_request.project}#{release_request.buildnumber}"
  try:
    r = requests.post(url, json=payload, headers=headers)
    r.raise_for_status()
    if r.status_code == 200:
      if 'errors' in r.json():
        raise Exception(error)
      else:
        print(f"Triggered rules-cov on cirrus for {release_request.project}#{version}")
  except Exception as err:
    print(error)
    raise Exception(f"{error} {err}")

def get_release_info(release_request, version):
  url=f"{githup_api_url}/repos/{release_request.org}/{release_request.project}/releases"
  headers={'Authorization': f"token {github_token}"}
  r=requests.get(url, headers=headers)
  releases=r.json()
  for release in releases:
      if not isinstance(release, str) and release.get('tag_name') == version:
          return release
  print(f"::error No release info found for tag '{version}'.\nReleases: {releases}")
  return None

def attach_asset_to_github_release(release_info,file_path,filename):
  files = {'upload_file': open(file_path,'rb')}
  upload_url=release_info.get('upload_url').replace('{?name,label}',f"?name={filename}")
  print(upload_url)
  headers = {'content-type': content_type_zip, 'Authorization': f"token {github_token}"}
  r = requests.post(upload_url, files=files, headers=headers)
  return r