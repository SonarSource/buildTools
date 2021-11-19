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


scan() {
  if [ "${WS_PRODUCTNAME:-UNDEFINED}" == "UNDEFINED" ]; then
    export WS_PRODUCTNAME=${CIRRUS_REPO_FULL_NAME}
  fi
  if [ "${WS_PROJECTNAME:-UNDEFINED}" == "UNDEFINED" ]; then
    export WS_PROJECTNAME="${WS_PRODUCTNAME} ${PROJECT_VERSION%.*}"
  fi
  echo "${WS_PRODUCTNAME} - ${WS_PROJECTNAME}"
  java -jar ${UNIFIED_AGENT_JAR} -scanComment "buildNumber:${BUILD_NUMBER};gitSha:${CIRRUS_CHANGE_IN_REPO}"
}


get_unified_agent
scan
