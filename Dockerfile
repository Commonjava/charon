####
# This Dockerfile is used to build the container for mrrc uploader
#
# mrrc uploader requires python 3
#
# 0. Step into the project dir
#
# 1. Build the image
#   docker/podman build -t mrrc-uploader:1.0.0 .
#
# 2. Run the container as daemon, mount the host ~/upload/ path to container /root/upload/ path,
#   the uploading path is the dir location where you will upload the tarballs from
#   add -e to set specific environment variables, such as: AWS_PROFILE, aws_endpoint_url, bucket
#   docker/podman run -dit -v ~/upload/:/root/upload/ --name mrrc-uploader mrrc-uploader:1.0.0
#
# 3. Execute the container
#   docker/podman exec -it mrrc-uploader bash
#
# 4. Start using uploader
#   mrrc upload/delete from /root/upload/...
###

# parser directive, always points to the latest release of the version 1 syntax,
# automatically checks for updates before building, making sure using the most current version
# syntax=docker/dockerfile:1
FROM python:3.8

USER root

# ensure the latest version of pip
RUN pip3 install --upgrade pip

RUN mkdir -p /opt/mrrc-uploader /home/mrrc-tmp && \
  chmod -R 777 /opt/mrrc-uploader

RUN chgrp -R 0 /opt && \
    chmod -R g=u /opt && \
    chgrp -R 0 /opt/mrrc-uploader&& \
    chmod -R g=u /opt/mrrc-uploader && \
    chgrp -R 0 /home/mrrc-tmp && \
    chmod -R g=u /home/mrrc-tmp && \
    chown -R 1001:0 /home/mrrc-tmp

# root dir for app
WORKDIR /opt/mrrc-uploader

# pip respects TMPDIR to set another enough disk space for pip packages installation
ENV TMPDIR="/home/mrrc-tmp"

# install all required packages
COPY requirements.txt ./
RUN pip3 install --no-cache-dir -r requirements.txt

COPY . .

# prepare configs for mrrc uploder
ADD ./config/mrrc-uploader.conf /root/.mrrc/mrrc-uploader.conf
ADD ./config/aws-credentials /root/.aws/credentials

# prepare templates for mrrc uploder
ADD ./template/index.html.j2 /root/.mrrc/template/index.html.j2
ADD ./template/maven-metadata.xml.j2 /root/.mrrc/template/maven-metadata.xml.j2

# install mrrc uploader
RUN pip3 install --no-cache-dir .

# this will be invoked when container runs, mrrc-uploder will directly setup
# from the container and keep running as long as the bash is active
CMD ["bash"]
