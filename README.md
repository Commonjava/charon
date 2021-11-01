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
git clone https://github.com/Commonjava/mrrc-uploader.git
cd mrrc-uploader
sudo pip install .
```

## Command guide

These commands will upload and distribute files in AWS via AWS CDK. Please
follow [boto3 access configuration](https://boto3.amazonaws.com/v1/documentation/api/latest/guide/configuration.html)
to configure AWS access credentials.

### mrrc-upload: upload a repo to S3

```bash
usage: mrrc upload $tarball --product/-p ${prod} --version/-v ${ver} [--root_path] [--ignore_patterns] [--debug]
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

### mrrc-delete: delete repo/paths from S3

```bash
usage: mrrc delete $tarball|$pathfile --product/-p ${prod}
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
