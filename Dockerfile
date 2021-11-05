####
# This Dockerfile is used to build the container for hermes
#
# hermes requires python 3
#
# 0. Step into the project dir
#
# 1. Build the image
#   docker/podman build -t hermes:1.0.0 .
#
# 2. Run the container as daemon, mount the host ~/upload/ path to container /root/upload/ path,
#   the uploading path is the dir location where you will upload the tarballs from
#   add -e to set specific environment variables, such as: AWS_PROFILE, aws_endpoint_url, bucket
#   docker/podman run -dit -v ~/upload/:/root/upload/ --name hermes hermes:1.0.0
#
# 3. Execute the container
#   docker/podman exec -it hermes bash
#
# 4. Start using uploader
#   hermes upload/delete from /root/upload/...
###

# parser directive, always points to the latest release of the version 1 syntax,
# automatically checks for updates before building, making sure using the most current version
# syntax=docker/dockerfile:1
FROM python:3.8

# ensure the latest version of pip
RUN pip3 install --upgrade pip

RUN adduser hermes
USER hermes
WORKDIR /home/hermes

# pip respects TMPDIR to set another enough disk space for pip packages installation
ENV TMPDIR="/home/hermes/tmp"

# install all required packages
COPY --chown=hermes:hermes requirements.txt ./
RUN pip3 install --user --no-cache-dir -r requirements.txt

# prepare configs for hermes
ADD ./config/hermes.conf /home/hermes/.hermes/hermes.conf
ADD ./config/aws-credentials /home/hermes/.aws/credentials

# prepare templates for hermes
ADD ./template/index.html.j2 /home/hermes/.hermes/template/index.html.j2
ADD ./template/maven-metadata.xml.j2 /home/hermes/.hermes/template/maven-metadata.xml.j2

ENV PATH="/home/hermes/.local/bin:${PATH}"
COPY --chown=hermes:hermes . .

# install hermes
RUN pip3 install --user --no-cache-dir .

# this will be invoked when container runs, hermes will directly setup
# from the container and keep running as long as the bash is active
CMD ["bash"]
