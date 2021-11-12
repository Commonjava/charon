# hermes - Synchronize repositories to Ronda over AWS

This hermes is a tool to synchronize several types of artifacts
repository data to RedHat Ronda service (maven.repository.redhat.com). These
repositories including types of maven, npm or some others like python in the
future. And Ronda service will be hosted in AWS S3.

## Prerequisites

### [Optional] Install AWS CLI tool

See [AWS CLi V2 installation](https://docs.aws.amazon.com/cli/latest/userguide/install-cliv2-linux.html#cliv2-linux-install)

## Installation

### From git

Clone this git repo and install hermes using python installer:

```bash
git clone https://github.com/Commonjava/hermes.git
cd hermes
sudo pip install .
```

## Command guide

These commands will upload and distribute files in AWS via AWS CDK. Please
follow [boto3 access configuration](https://boto3.amazonaws.com/v1/documentation/api/latest/guide/configuration.html)
to configure AWS access credentials.

### Configurations

* AWS configurations. The uploader uses aws boto3 to access AWS S3 bucket, and follows the AWS configurations statndards. You can use:
  * AWS configurations files: $HOME/.aws/config and $HOME/.aws/credentials. (For format see [AWS config format](https://docs.aws.amazon.com/sdkref/latest/guide/file-format.html))
  * [System environment varaibles](https://docs.aws.amazon.com/cli/latest/userguide/cli-configure-envvars.html)
* Configurations for uploader. We use $HOME/.hermes/hermes.conf to hold these configurations. Currently, The uploader has two configurations:
  * ignore_patterns. This is used to filter out some files that are not allowed to upload. It is a json array of regular expressions. (Example: ["README.md", "example.txt"]). This can also be retrieved from "HERMES_IGNORE_PATTERNS" system environment variable.
  * bucket. This is used to specify which AWS S3 bucket to upload to with the tool. This config can also be retrieved from "hermes_bucket" system environment variable.

### hermes-upload: upload a repo to S3

```bash
usage: hermes upload $tarball --product/-p ${prod} --version/-v ${ver} [--root_path] [--ignore_patterns] [--debug]
```

This command will upload the repo in tarball to S3.
It will auto-detect if the tarball is for maven or npm

* For maven type, it will:
  * Scan the tarball for all paths and collect them all.
  * Check the existence in S3 for all those paths.
  * Filter out the paths in tarball based on:
    * filter_pattern in flags, or
    * filter_pattern in config.json if no flag
  * Generate/refresh all maven-metadata.xml for all GA combined
    with both S3 and local filtered pom.xml
  * Upload these artifacts to S3 with metadata of the product.
  * If the artifacts already exists in S3, update the metadata
    of the product by appending the new product.

* NPM type (TBH): We need to know the exact tarball structure
  of npm repo

* For both types, after uploading the files, regenerate/refresh
  the index files for these paths.

### hermes-delete: delete repo/paths from S3

```bash
usage: hermes delete $tarball|$pathfile --product/-p ${prod}
--version/-v ${ver} [--root_path] [--debug]
```

This command will delete some paths from repo in S3.

* Scan tarball or read pathfile for the paths to delete
* Combine the product flag by --product and --version
* Filter out the paths in tarball based on:
  * filter_pattern in flags, or
  * filter_pattern in config.json if no flag
* If the artifacts have other products in the metadata,
  remove the product of this tarball from the metadata
  but not delete the artifacts themselves.
* During or after the paths' deletion, regenerate the
  metadata files and index files for both types.
