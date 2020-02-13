import sys
import os
import requests
import json
import urllib.request
import paramiko
from scp import SCPClient

'''
x Promote
x Push to binaries
x Tag github
notify burgr
'''

artifactory_url='https://repox.jfrog.io/repox'
binaries_host='binaries.sonarsource.com'
binaries_url=f"https://{binaries_host}"
artifactory_apikey=os.environ.get('ARTIFACTORY_API_KEY','no api key in env')  
binaries_path_prefix='/tmp'
passphrase=os.environ.get('GPG_PASSPHRASE','no GPG_PASSPHRASE in env')  
ssh_user='ssuopsa'
ssh_key='id_rsa_ssuopsa'
  

def main():
    my_input = os.environ["INPUT_MYINPUT"]
    my_output = f"Hello {my_input}"
    print(f"::set-output name=myOutput::{my_output}")


if __name__ == "__main__":
    main()

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
  artifacts = repox_get_module_property_from_buildinfo(project, buildnumber,'artifactsToPublish')
  return artifacts

def publish_all_artifacts(artifacts,version,repo):  
  artifacts = artifacts.split(",")
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
  artifact = artifact_to_publish.split(":")
  gid = artifact[0]
  aid = artifact[1]
  ext = artifact[2]
  qual = ''
  binaries_repo = "Distribution"  
  if repo.startswith('sonarsource-private'):
    binaries_repo = "CommercialDistribution"
  artifactory_repo = repo.replace('builds', 'releases')    
  print(f"{gid} {aid} {ext}")
  release_url = f"{binaries_url}/{binaries_repo}/{aid}/{aid}-{version}.{ext}" 
  upload_to_binaries(binaries_repo,artifactory_repo,gid,aid,qual,ext,version)
  return release_url

def promote(project,buildnumber,multi):
  targetrepo="sonarsource-private-builds"
  targetrepo2="sonarsource-public-builds"
  status='release'
  
  try:
    repo = repox_get_module_property_from_buildinfo(project, buildnumber,'buildinfo.env.ARTIFACTORY_DEPLOY_REPO')
    targetrepo = repo.replace('builds', 'releases')
  except Exception as e:
    print(f"Could not get repository for {project} {buildnumber} {str(e)}")
  
  print(f"Promoting build {project}#{buildnumber}")
  json_payload={
      "status": f"{status}",
      "targetRepo": f"{targetrepo}"
  }
  if multi == "true":
    url = f"{artifactory_url}/api/plugins/execute/multiRepoPromote?params=buildName={project};buildNumber={buildnumber};src1=sonarsource-private-qa;target1={targetrepo};src2=sonarsource-public-qa;target2={targetrepo2};status={status}"
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


def upload_to_binaries(binaries_repo,artifactory_repo,gid,aid,qual,ext,version):
  #download artifact
  gid_path=gid.replace(".", "/")
  artifactory=artifactory_url+"/"+artifactory_repo
  filename=f"{aid}-{version}.{ext}"
  if qual:
    filename=f"{aid}-{version}-{qual}.{ext}"
  url=f"{artifactory}/{gid_path}/{aid}/{version}/{filename}"    
  print(url)
  urllib.request.urlretrieve(url, filename)
  print(f'donwloaded {filename}')
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
  scp.put(filename, remote_path=directory)
  print(f'uploaded {filename} to {directory}')
  scp.close()
  #sign file
  stdin,stdout,stderr=ssh_client.exec_command(f"gpg --batch --passphrase {passphrase} --armor --detach-sig --default-key infra@sonarsource.com {directory}/{filename}")
  print(f'signed {directory}/{filename}')
  stdin,stdout,stderr=ssh_client.exec_command(f"ls -al {directory}")
  print(stdout.readlines())
  ssh_client.close()

def find_buildnumber_from_sha1(sha1):  
  query = f'build.properties.find({{"buildInfo.env.GIT_SHA1": "{sha1}"}}).include("buildInfo.env.BUILD_NUMBER")'
  url = f"{artifactory_url}/api/search/aql"
  headers = {'content-type': 'text/plain', 'X-JFrog-Art-Api': artifactory_apikey} 
  r = requests.post(url, data=query, headers=headers)      
  return r.json()['results'][0]['build.property.value']