import sys
import os
import requests
import json
import urllib.request
import paramiko
from scp import SCPClient
from flask import escape
from flask import make_response
from datetime import datetime, timezone
from requests.auth import HTTPBasicAuth
from requests.models import Response

artifactory_apikey=os.environ.get('ARTIFACTORY_API_KEY','no api key in env')  
passphrase=os.environ.get('GPG_PASSPHRASE','no GPG_PASSPHRASE in env')  

binaries_path_prefix=os.environ.get('PATH_PREFIX','/tmp')

#burgr
burgrx_url = 'https://burgrx.sonarsource.com'
burgrx_user = os.environ.get('BURGRX_USER', 'no burgrx user in env')
burgrx_password = os.environ.get('BURGRX_PASSWORD', 'no burgrx password in env')

artifactory_url='https://repox.jfrog.io/repox'
binaries_host='binaries.sonarsource.com'
binaries_url=f"https://{binaries_host}"
ssh_user='ssuopsa'
ssh_key='id_rsa_ssuopsa'
AUTHENTICATED="authenticated"
OSS_REPO="Distribution"
COMMERCIAL_REPO="CommercialDistribution"
bintray_target_repo="SonarQube-bintray"

  
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
  paths=request.path.split("/")
  org=paths[1]
  project=paths[2]
  buildnumber=paths[3]
  branch=repox_get_property_from_buildinfo(project, buildnumber, 'buildInfo.env.GITHUB_BRANCH')
  sha1=repox_get_property_from_buildinfo(project, buildnumber, 'buildInfo.env.GIT_SHA1')
  if validate_authorization_header(request, project) == AUTHENTICATED:
    try:
      promote(project,buildnumber)
      publish_all_artifacts(project,buildnumber)      
      notify_burgr(org,project,buildnumber,branch,sha1,'passed')
      if check_public(project,buildnumber):
        distribute_build(project,buildnumber)
    except Exception as e:
      notify_burgr(org,project,buildnumber,branch,sha1,'failed')
      print(f"Could not get repository for {project} {buildnumber} {str(e)}")
      return make_response(str(e),500)
  else:
    return make_response(validate_authorization_header(request, project), 403)

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
    if github_auth(request.headers['Authorization'].split()[1],project):
      print("Authenticated with github token")
      return AUTHENTICATED
    else:
      return "Wrong access token"
  else:
    return "Missing access token"

def repox_get_property_from_buildinfo(project, buildnumber, property):  
  buildinfo = repox_get_build_info(project,buildnumber)
  return buildinfo['buildInfo']['properties'][property]

def repox_get_module_property_from_buildinfo(project, buildnumber, property):  
  buildinfo = repox_get_build_info(project,buildnumber)
  return buildinfo['buildInfo']['modules'][0]['properties'][property]

def get_version(project, buildnumber):  
  buildinfo = repox_get_build_info(project,buildnumber)  
  return buildinfo['buildInfo']['modules'][0]['id'].split(":")[-1]
  
def repox_get_build_info(project, buildnumber):  
  url = f"{artifactory_url}/api/build/{project}/{buildnumber}"
  headers = {'content-type': 'application/json', 'X-JFrog-Art-Api': artifactory_apikey} 
  r = requests.get(url, headers=headers)  
  buildinfo = r.json()
  if r.status_code == 200:      
    return buildinfo
  else:
    raise Exception('unknown build')  

def get_artifacts_to_publish(project,buildnumber):
  artifacts = ''
  try:  
    artifacts = repox_get_module_property_from_buildinfo(project, buildnumber,'artifactsToPublish')
  except:
    artifacts = repox_get_property_from_buildinfo(project, buildnumber, 'buildInfo.env.ARTIFACTS_TO_PUBLISH')
  return artifacts

def publish_all_artifacts(project,buildnumber): 
  print(f"publishing artifats for {project}#{buildnumber}")
  repo = repox_get_property_from_buildinfo(project, buildnumber, 'buildInfo.env.ARTIFACTORY_DEPLOY_REPO').replace('qa', 'builds')
  version=get_version(project,buildnumber)
  allartifacts=get_artifacts_to_publish(project,buildnumber) 
  artifacts = allartifacts.split(",")
  artifacts_count = len(artifacts)   
  if artifacts_count == 1:
    print("only 1")
    return publish_artifact(artifacts[0],version,repo)  
  release_url = ""
  print(f"{artifacts_count} artifacts")
  for i in range(0, artifacts_count):      
    print(f"artifact {i}")  
    release_url = publish_artifact(artifacts[i - 1],version,repo)  
  return release_url


def publish_artifact(artifact_to_publish,version,repo): 
  print(f"publishing {artifact_to_publish}#{version}")
  artifact = artifact_to_publish.split(":")
  gid = artifact[0]
  aid = artifact[1]
  ext = artifact[2]
  qual = ''
  artifactory_repo = repo.replace('builds', 'releases')    
  print(f"{gid} {aid} {ext}")  
  return upload_to_binaries(artifactory_repo,gid,aid,qual,ext,version)

def is_multi(project,buildnumber):
  allartifacts=get_artifacts_to_publish(project,buildnumber) 
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


def promote(project,buildnumber):
  targetrepo="sonarsource-public-releases"
  status='release'
  
  repo = repox_get_property_from_buildinfo(project, buildnumber, 'buildInfo.env.ARTIFACTORY_DEPLOY_REPO')
  targetrepo = repo.replace('qa', 'releases')
  
  print(f"Promoting build {project}#{buildnumber} to {targetrepo}")
  json_payload={
      "status": f"{status}",
      "targetRepo": f"{targetrepo}"
  }

  if is_multi(project, buildnumber):
    print(f"Promoting multi repositories")
    url = f"{artifactory_url}/api/plugins/execute/multiRepoPromote?params=buildName={project};buildNumber={buildnumber};src1=sonarsource-private-builds;target1=sonarsource-private-releases;src2=sonarsource-public-builds;target2=sonarsource-public-releases;status={status}"
    headers = {'X-JFrog-Art-Api': artifactory_apikey}
    r = requests.get(url, headers=headers)
  else:
    url = f"{artifactory_url}/api/build/promote/{project}/{buildnumber}"
    headers = {'content-type': 'application/json', 'X-JFrog-Art-Api': artifactory_apikey}
    r = requests.post(url, data=json.dumps(json_payload), headers=headers)      
  if r.status_code == 200:      
    return f"status:{status}"
  else:
    return f"status:{status} code:{r.status_code}"   


def upload_to_binaries(artifactory_repo,gid,aid,qual,ext,version):
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
  tempfile=f"/tmp/{filename}"
  urllib.request.urlretrieve(url, tempfile)
  print(f'donwloaded {tempfile}')
  #upload artifact
  ssh_client=paramiko.SSHClient()
  ssh_client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
  ssh_client.connect(hostname=binaries_host, username=ssh_user, key_filename=ssh_key)
  #create directory
  directory=f"{binaries_path_prefix}/{binaries_repo}/{aid}/"
  stdin,stdout,stderr=ssh_client.exec_command(f"mkdir -p {directory}")
  print(f'created {directory}')
  scp = SCPClient(ssh_client.get_transport())
  print('scp connexion created')
  #upload file
  scp.put(tempfile, remote_path=directory)
  print(f'uploaded {tempfile} to {directory}')
  scp.close()
  #sign file
  stdin,stdout,stderr=ssh_client.exec_command(f"gpg --batch --passphrase {passphrase} --armor --detach-sig --default-key infra@sonarsource.com {directory}/{filename}")
  print(f'signed {directory}/{filename}')
  stdin,stdout,stderr=ssh_client.exec_command(f"ls -al {directory}")
  print(stdout.readlines())
  ssh_client.close()
  release_url = f"{binaries_url}/{binaries_repo}/{aid}/{aid}-{version}.{ext}" 
  return release_url

def notify_burgr(org,project,buildnumber,branch,sha1,status):  
  payload={
    'repository': f"{org}/{project}",
    'pipeline': buildnumber,
    'name': 'RELEASE',
    'system': 'github',
    'type': 'release',
    'number': buildnumber,
    'branch': branch,
    'sha1': sha1,
    'url':f"https://github.com/{org}/{project}/releases",
    'status': status,
    'metadata': '',
    'started_at':datetime.now(timezone.utc).astimezone().isoformat(),
    'fnished_at':datetime.now(timezone.utc).astimezone().isoformat()
  }
  print(f"burgr payload:{payload}")
  url=f"{burgrx_url}/api/stage"
  r = requests.post(url, json=payload, auth=HTTPBasicAuth(burgrx_user, burgrx_password)) 
  if r.status_code != 201:          
    print(f"burgr notification failed code:{r.status_code}" )   

def check_public(project,buildnumber):
  artifacts = get_artifacts_to_publish(project,buildnumber)
  return "org.sonarsource" in artifacts

def distribute_build(project,buildnumber):
  payload={ 
    "targetRepo": bintray_target_repo, 
    "sourceRepos" : ["sonarsource-public-releases"]  
  }
  url=f"{artifactory_url}/api/build/distribute/{project}/{buildnumber}"
  headers = {'content-type': 'application/json', 'X-JFrog-Art-Api': artifactory_apikey}
  r = requests.post(url, json=payload, headers=headers)      
  if r.status_code == 200:      
    print(f"{project}#{buildnumber} pushed to bintray ready to sync to central")
  else:
    print(f"Failed to distribute {project}#{buildnumber}")