#------------------------------------------------------------------------------
# All the tools required to build mysql-migrator, including execution
# of integration tests.
#
# Build from the basedir:
#   docker build -f docker/Dockerfile-build -t mysql-migrator-build docker
#
# Verify the content of the image by running a shell session in it:
#   docker run -it mysql-migrator-build bash
#
# CirrusCI builds the image when needed. No need to manually upload it
# to Google Cloud Container Registry. See section "gke_container" of .cirrus.yml
#------------------------------------------------------------------------------

FROM maven:3.6-jdk-11

USER root

RUN apt-get update && apt-get -y install python3
RUN groupadd -r sonarsource && useradd -r -m -g sonarsource sonarsource

COPY settings.xml /usr/share/maven/conf/settings.xml

ENV MAVEN_CONFIG "/home/sonarsource/.m2"
USER sonarsource
COPY bin/burgr-notify-promotion.sh bin/cirrus-env.sh \
  bin/maven_expression bin/regular_mvn_build_deploy_analyse bin/set_maven_build_version \
  /home/sonarsource/bin/
ENV PATH="/home/sonarsource/bin:${PATH}"