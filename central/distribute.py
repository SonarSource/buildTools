import sys
import os
import requests
import json

#repox
artifactory_apikey=os.environ.get('ARTIFACTORY_API_KEY','no artifactory api key in env')  
artifactory_url='https://repox.jfrog.io/repox'
bintray_target_repo="SonarQube-bintray"
  
#bintray
bintray_api_url='https://api.bintray.com'
bintray_user=os.environ.get('BINTRAY_USER','no bintray api user in env')  
bintray_apikey=os.environ.get('BINTRAY_TOKEN','no bintray api key in env')  

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
  
#distribute_build('sonar-java',21135)
#delete_version("org.sonarsource.java","3.10")
delete_versions("org.sonarsource.analyzer-commons")
delete_versions("org.sonarsource.auth.bitbucket")
delete_versions("org.sonarsource.dotnet")
delete_versions("org.sonarsource.javascript")
delete_versions("org.sonarsource.sonar-plugins.dotnet.csharp")
delete_versions("org.sonarsource.sonar-plugins.dotnet.tests")
delete_versions("org.sonarsource.sonar-plugins.widget-lab")
delete_versions("org.sonarsource.sonarlint.core")
delete_versions("org.sonarsource.update-center")