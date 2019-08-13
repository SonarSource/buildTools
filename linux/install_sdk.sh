#!/bin/bash

export SDKMAN_DIR="/opt/sdkman"
curl -s "https://get.sdkman.io" | bash
source "/opt/sdkman/bin/sdkman-init.sh"

cat <<EOT >> /etc/profile

export SDKMAN_DIR="/opt/sdkman"
[[ -s "/opt/sdkman/bin/sdkman-init.sh" ]] && source "/opt/sdkman/bin/sdkman-init.sh"

EOT

sdk list java

sdk install java 12.0.1-zulu < /dev/null
sdk default java 12.0.1-zulu || exit 1

sdk install java 11.0.2-open < /dev/null
sdk default java 11.0.2-open || exit 1

sdk install java 11.0.3-zulu < /dev/null
sdk default java 11.0.3-zulu || exit 1

sdk install java 10.0.2-open < /dev/null
sdk default java 10.0.2-open || exit 1

sdk install java 9.0.4-open < /dev/null
sdk default java 9.0.4-open || exit 1

sdk install java 8.0.212-zulu < /dev/null
sdk default java 8.0.212-zulu || exit 1

sdk install java 6.0.119-zulu < /dev/null
sdk default java 6.0.119-zulu || exit 1

sdk default java 8.0.212-zulu
