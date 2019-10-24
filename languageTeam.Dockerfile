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

RUN groupadd -r sonarsource && useradd -r -m -g sonarsource sonarsource

ENV MAVEN_CONFIG "/home/sonarsource/.m2"
COPY settings-public.xml ${MAVEN_CONFIG}/settings.xml
COPY settings-private.xml ${MAVEN_CONFIG}/settings-private.xml
RUN chown -R sonarsource:sonarsource ${MAVEN_CONFIG}

USER sonarsource

COPY bin/burgr-notify-promotion bin/cirrus-env bin/regular_gradle_build_deploy_analyze \
  bin/init_git_submodules bin/cleanup_maven_repository bin/cirrus_promote_maven \
  bin/maven_expression bin/regular_mvn_build_deploy_analyze bin/set_maven_build_version \
  /home/sonarsource/bin/
  
ENV PATH="/home/sonarsource/bin:${PATH}"
