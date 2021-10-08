# mrrc-uploader - Synchronize repositories to MRRC over AWS

This mrrc-uploader is a tool to synchronize several types of artifacts
repository data to RedHat MRRC service (maven.repository.redhat.com). These
repositories including types of maven, npm or some others like python in the
future. And MRRC service will be hosted in AWS S3.

## Prerequisites

### [Optional] Install AWS CLI tool

See [AWS CLi V2 installation](https://docs.aws.amazon.com/cli/latest/userguide/install-cliv2-linux.html#cliv2-linux-install)

## Installation

### From git

Clone this git repo and install MRRC using python installer:

```bash
python -m pip install pip virtualenv --upgrade --user
virtualenv ./venv
source ./venv/bin/activate
python setup.py install
```

This will build & install the tool into ./venv/ folder with virtual environment
to start using in a sandbox

## Command guide

These commands will upload and distribute files in AWS via AWS CDK. Please
follow [boto3 access configuration](https://boto3.amazonaws.com/v1/documentation/api/latest/guide/configuration.html)
to configure AWS access credentials.

### mrrc-init: Init the configuration of the whole mrrc tool

```bash
usage: mrrc init
```

The configuration will include two parts of configurations

* [aws]: the AWS related information to access S3 service, like aws_service_url,
  app_key, access_token or something similar for the AWS libs to use.
  See [AWS configurations](https://boto3.amazonaws.com/v1/documentation/api/latest/guide/configuration.html)

* [mrrc]: mrrc-uploader tool related information, TBH for more.

The command will be executed in verbose mode with several steps of prompt to let
user to input some mandantory items. These information will stored in
$HOME/.mrrc/config.json(or yaml or something similar) after command execution
for the following usage. All following command will check this config.json for
valid configurations, and if invalid will ask user to do the mrrc-init for
correction.
(So we can pre-define this config.json in vm/container for automation through
configmap/secrets or similar stuff)

### mrrc-upload: upload a repo to S3

```bash
usage: mrrc upload $tarball --type ${maven|npm} --force
```

This command will upload the repo in tarball to S3.

* For maven type, it will:
  * Scan the tarball for all paths and collect them all.
  * Check the existence in S3 for all those paths.
  * Filter out the paths in tarball based on:
    * --force is false(Which means will not overwrite in S3)
    * filter_pattern in config.json
  * Generate/refresh all maven-metadata.xml for all GA combined with both S3 and
    local filtered pom.xml
  * Upload these artifacts to S3 and then refresh the CDN content of these
    artifacts.

* NPM type (TBH): We need to know the exact tarball structure of npm repo

* For both types, after uploading the files, regenerate/refresh the index files
  for these paths.

### mrrc-delete: delete repo/paths from S3

```bash
usage: mrrc delete $tarball|$pathfile
```

This command will delete some paths from repo in S3.

* Scan tarball or read pathfile for the paths to delete
* During or after the paths deletion, regenerate the metadata files and index
  files for both types.

### (Optional?) mrrc-gen: Generate metadata files

```bash
usage: mrrc gen --type ${maven|npm|index} ${GA|NpmPkg|Path}
```

This command will generate or refresh metadata files

* For type maven, it will scan the GA(group:artifact) path for all artifacts
  versions, and re-generate the maven-metadata.xml based on the scan result
* For type npm, it will scan the NpmPkg path(Question: what's structure?) and
  re-generate the versions in existed package.json based on the scan result.
* For type index, it scan the specified path and re-gnerate the index files (
  recursively?) in that path to refresh index file in CDN.

### (Optional?)mrrc-ls: List files of repo in S3

```bash
usage: mrrc ls $path [-R]
```

This command will list paths in specified path.

* -R(--recursive) means list files recursively
