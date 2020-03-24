import sys
import os
import requests
import json
import argparse

#repox
artifactory_apikey=os.environ.get('ARTIFACTORY_API_KEY','no artifactory api key in env')  
artifactory_url='https://repox.jfrog.io/repox'
bintray_target_repo="SonarQube-bintray"
  
#bintray
bintray_api_url='https://api.bintray.com'
bintray_user=os.environ.get('BINTRAY_USER','no bintray api user in env')  
bintray_apikey=os.environ.get('BINTRAY_TOKEN','no bintray api key in env')  

content_type_json='application/json'

def promote(project,buildnumber):
  targetrepo="sonarsource-public-releases"
  status='release'

  print(f"Promoting build {project}#{buildnumber} to {targetrepo}")
  json_payload={
      "status": f"{status}",
      "targetRepo": f"{targetrepo}"
  }

  url = f"{artifactory_url}/api/build/promote/{release_request.project}/{release_request.buildnumber}"
  headers = {'content-type': content_type_json, 'X-JFrog-Art-Api': artifactory_apikey}
  r = requests.post(url, data=json.dumps(json_payload), headers=headers)
  if r.status_code == 200:
    return f"status:{status}"
  else:
    return f"status:{status} code:{r.status_code}"


def distribute_build(project,buildnumber):
  print(f"Distributing {project}#{buildnumber} to bintray")
  payload={ 
    "targetRepo": bintray_target_repo, 
    "sourceRepos" : ["sonarsource-public-releases"]  
  }
  url=f"{artifactory_url}/api/build/distribute/{project}/{buildnumber}"
  headers = {'content-type': 'application/json', 'X-JFrog-Art-Api': artifactory_apikey}
  try:
    r = requests.post(url, json=payload, headers=headers)  
    r.raise_for_status()    
    if r.status_code == 200:      
      print(f"{project}#{buildnumber} pushed to bintray ready to sync to central")
  except requests.exceptions.HTTPError as err:
    print(f"Failed to distribute {project}#{buildnumber} {err}")

def delete_build(project,buildnumber):
  #/api/build/my-build?buildNumbers=51,52,55&artifacts=1
  print(f"Deleting {project}#{buildnumber}")
  url=f"{artifactory_url}/api/build/{project}?buildNumbers={buildnumber}&artifacts=1"
  headers = {'content-type': 'application/json', 'X-JFrog-Art-Api': artifactory_apikey}
  try:
    r = requests.delete(url, headers=headers)  
    r.raise_for_status()    
    if r.status_code == 200:      
      print(f"{project}#{buildnumber} deleted with all artifacts")
  except requests.exceptions.HTTPError as err:
    print(f"Failed to distribute {project}#{buildnumber} {err}")

def get_versions(package):
  print(f"Getting versions for {package} from bintray")
  #GET /packages/:subject/:repo/:package
  url=f"{bintray_api_url}/packages/sonarsource/SonarQube/{package}"
  try:
    r = requests.get(url, auth=requests.auth.HTTPBasicAuth(bintray_user, bintray_apikey))  
    r.raise_for_status()    
    if r.status_code == 200:      
      print(f"{package} versions retrieved")
    data=r.json()
    return(data['versions'])

  except requests.exceptions.HTTPError as err:
    print(f"Failed to get versions for {package} {err}")

def delete_version(package,version):
  print(f"Deleting {version} from {package}")
  #DELETE /packages/:subject/:repo/:package/versions/:version
  url=f"{bintray_api_url}/packages/sonarsource/SonarQube/{package}/versions/{version}"
  try:
    r = requests.delete(url, auth=requests.auth.HTTPBasicAuth(bintray_user, bintray_apikey))  
    r.raise_for_status()    
    if r.status_code == 200:      
      print(f"{package} versions deleted")
      data=r.json()
      print(data)

  except requests.exceptions.HTTPError as err:
    print(f"Failed to get versions for {package} {err}")

def delete_versions(package):
  versions=get_versions(package)
  for version in versions:
    delete_version(package,version)

def repox_get_property_from_buildinfo(project, buildnumber, property):  
  url = f"{artifactory_url}/api/build/{project}/{buildnumber}"
  headers = {'content-type': 'application/json', 'X-JFrog-Art-Api': artifactory_apikey}
  r = requests.get(url, headers=headers)  
  buildinfo = r.json()
  if r.status_code == 200:      
    return buildinfo['buildInfo']['properties'][property]
  else:
    print(f'repoxGetPropertyFromBuildInfo call with URL {url} failed, the response is {buildinfo}')
    raise Exception('unknown build')

def promote(project,buildnumber,type,revoke):  
  multi=True
  targetrepo="sonarsource-public-builds"
  
  switcher = {
    'release':'release',
    'pr':'it-passed-pr',
    'branch':'it-passed'
  }
  status=switcher.get(type, "not a possible status")

  repo = repox_get_property_from_buildinfo(project, buildnumber, 'buildInfo.env.ARTIFACTORY_DEPLOY_REPO')
  
  if revoke:
    print("revoking release")
    targetrepo = repo.replace('qa', 'builds')
    src="releases"
    dest="builds"
  else:
    targetrepo = repo.replace('qa', 'releases')
    src="releases"
    dest="builds"

  print(f"Promoting build {project}#{buildnumber} to {targetrepo} with status: {status}")
  json_payload={
      "status": f"{status}",
      "targetRepo": f"{targetrepo}"
  }

  if multi:
    print(f"Promoting multi repositories")
    url = f"{artifactory_url}/api/plugins/execute/multiRepoPromote?params=buildName={project};buildNumber={buildnumber};src1=sonarsource-private-{src};target1=sonarsource-private-{dest};src2=sonarsource-public-{src};target2=sonarsource-public-{dest};status={status}"
    headers = {'X-JFrog-Art-Api': artifactory_apikey}
    r = requests.get(url, headers=headers)
  else:
    url = f"{artifactory_url}/api/build/promote/{project}/{buildnumber}"
    headers = {'content-type': content_type_json, 'X-JFrog-Art-Api': artifactory_apikey}
    r = requests.post(url, data=json.dumps(json_payload), headers=headers)
  if r.status_code == 200:
    return f"status:{status}"
  else:
    return f"status:{status} code:{r.status_code}"

  
#distribute_build('sonar-java',21210)
#delete_build('sonar-java',21210)
#delete_version("org.sonarsource.java","3.10")
#delete_versions("org.sonarsource.analyzer-commons")

def main():
  parser = argparse.ArgumentParser(description='central distribution')
  parser.add_argument('command', nargs='+', help='see code for help')  
  args = parser.parse_args()

  
  if args.command[0] == "dist":
    distribute_build(args.command[1],args.command[2])
  elif args.command[0] == "del":
    delete_build(args.command[1],args.command[2])
  elif args.command[0] == "promote":    
    promote(args.command[1],args.command[2],args.command[3],args.command[4])
  else:
    print(f"inavlid {args.command} command")

if __name__ == '__main__':
    main()