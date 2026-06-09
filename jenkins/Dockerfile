# Imagen de Jenkins lista para este proyecto:
#  - Docker CLI (para construir/publicar imágenes usando el daemon del host)
#  - Plugins necesarios preinstalados
#  - Configuration-as-Code: crea el job y la credencial de Docker Hub al arrancar
FROM jenkins/jenkins:lts-jdk17

USER root
RUN apt-get update \
    && apt-get install -y docker.io \
    && rm -rf /var/lib/apt/lists/*
USER jenkins

COPY plugins.txt /usr/share/jenkins/ref/plugins.txt
RUN jenkins-plugin-cli -f /usr/share/jenkins/ref/plugins.txt

COPY casc.yaml /var/jenkins_casc/jenkins.yaml
ENV CASC_JENKINS_CONFIG=/var/jenkins_casc/jenkins.yaml
# Sin asistente de instalación: la configuración viene de casc.yaml
ENV JAVA_OPTS="-Djenkins.install.runSetupWizard=false"
