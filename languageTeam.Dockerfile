#------------------------------------------------------------------------------
# All the tools required to build java project, including execution
# of integration tests.
#
# Build from the basedir:
#   docker build -f languageTeam.Dockerfile -t base .
#
# Verify the content of the image by running a shell session in it:
#   docker run -it base bash
#
#------------------------------------------------------------------------------

FROM maven:3.6-jdk-11

USER root

RUN apt-get update && apt-get -y install python3
RUN groupadd -r sonarsource && useradd -r -m -g sonarsource sonarsource

COPY settings.xml /usr/share/maven/conf/settings.xml

ENV MAVEN_CONFIG "/home/sonarsource/.m2"
USER sonarsource
COPY bin/burgr-notify-promotion bin/cirrus-env \
  bin/maven_expression bin/regular_mvn_build_deploy_analyse bin/set_maven_build_version \
  /home/sonarsource/bin/
ENV PATH="/home/sonarsource/bin:${PATH}"