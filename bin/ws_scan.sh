#! /usr/bin/env bash

set -euox pipefail

readonly UNIFIED_AGENT_JAR="wss-unified-agent.jar"
readonly UNIFIED_AGENT_JAR_URL="https://unified-agent.s3.amazonaws.com/wss-unified-agent.jar"
readonly WHITESOURCE_SIGNATURE='Signed by "CN=whitesource software inc, O=whitesource software inc, STREET=79 Madison Ave, L=New York, ST=New York, OID.2.5.4.17=10016, C=US"'


get_unified_agent() {
  if [[ ! -f "${UNIFIED_AGENT_JAR}" ]]; then
    curl \
      --location \
      --remote-name \
      --remote-header-name \
      "${UNIFIED_AGENT_JAR_URL}"
  fi
  if [[ ! -f "${UNIFIED_AGENT_JAR}" ]]; then
    echo "Could not find downloaded Unified Agent" >&2
    exit 1
  fi

  # Verify JAR signature
  local path_to_verification_output="./jarsigner-output.txt"
  if ! jarsigner -verify -verbose "${UNIFIED_AGENT_JAR}" > "${path_to_verification_output}" ; then
    echo "Could not verify jar signature" >&2
    exit 2
  fi
  if [[ $(grep --count "${WHITESOURCE_SIGNATURE}" "${path_to_verification_output}") -ne 1 ]]; then
    echo "Could not find signature line in verification output" >&2
    exit 3
  fi
}

local_maven_expression() {
  mvn -q -Dexec.executable="echo" -Dexec.args="${1}" --non-recursive org.codehaus.mojo:exec-maven-plugin:1.3.1:exec
}


scan() {
  export WS_PRODUCTNAME=$(local_maven_expression "\${pom.groupId}:\${pom.artifactId}")
  export WS_PROJECTNAME="${WS_PRODUCTNAME} ${PROJECT_VERSION%.*}"
  echo "${WS_PRODUCTNAME} - ${WS_PROJECTNAME}"
  java -jar ${UNIFIED_AGENT_JAR} -scanComment "buildNumber:${BUILD_NUMBER};gitSha:${CIRRUS_CHANGE_IN_REPO}"
}


get_unified_agent
scan
