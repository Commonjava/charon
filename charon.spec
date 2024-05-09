%global owner Commonjava
%global modulename charon

%global charon_version 1.2.2
%global sdist_tar_name %{modulename}-%{charon_version}

%global python3_pkgversion 3

Name:     %{modulename}
Summary:  Charon CLI
Version:  %{charon_version}
Release:  1%{?dist}
URL:      https://github.com/%{owner}/%{modulename}
Source0:  %{url}/archive/%{charon_version}.tar.gz
Provides: %{modulename} = %{version}-%{release}

Group:    Development/Tools
License:  APLv2

# Build Requirements
BuildArch: x86_64

BuildRequires: python%{python3_pkgversion}-setuptools
BuildRequires: python%{python3_pkgversion}-devel

Requires: python%{python3_pkgversion}-boto3
Requires: python%{python3_pkgversion}-botocore
Requires: python%{python3_pkgversion}-jinja2
Requires: python%{python3_pkgversion}-markupsafe
Requires: python%{python3_pkgversion}-dateutil
Requires: python%{python3_pkgversion}-six
Requires: python%{python3_pkgversion}-jmespath
Requires: python%{python3_pkgversion}-urllib3
Requires: python%{python3_pkgversion}-s3transfer
Requires: python%{python3_pkgversion}-click
Requires: python%{python3_pkgversion}-requests
Requires: python%{python3_pkgversion}-idna
Requires: python%{python3_pkgversion}-chardet
Requires: python%{python3_pkgversion}-cryptography
Requires: python%{python3_pkgversion}-cffi
Requires: python%{python3_pkgversion}-pycparser
Requires: python%{python3_pkgversion}-certifi
Requires: python%{python3_pkgversion}-pyOpenSSL
Requires: python%{python3_pkgversion}-ruamel-yaml
Requires: python%{python3_pkgversion}-defusedxml
Requires: python%{python3_pkgversion}-semantic-version
Requires: python%{python3_pkgversion}-subresource-integrity
Requires: python%{python3_pkgversion}-jsonschema
Requires: python%{python3_pkgversion}-importlib-metadata
Requires: python%{python3_pkgversion}-zipp
Requires: python%{python3_pkgversion}-attrs
Requires: python%{python3_pkgversion}-pyrsistent

%description
Simple Python tool with command line interface for charon init,
upload, delete, gen and ls functions.

%prep
%autosetup -p1 -n %{sdist_tar_name}

%build
# Disable debuginfo packages
%define _enable_debug_package 0
%define debug_package %{nil}
%py3_build


%install
export LANG=en_US.UTF-8 LANGUAGE=en_US.en LC_ALL=en_US.UTF-8
%py3_install


%files
%defattr(-,root,root)
%doc README.md
%{_bindir}/%{modulename}*
%{python3_sitelib}/*
%{!?_licensedir:%global license %doc}
%license LICENSE


%changelog
* Tue May 7 2024 Gang Li <gli@redhat.com>
- 1.3.1 release
- Add checksum refresh command: refresh checksum files for maven artifacts
- Refactor the CF invalidating commands into cf sub command

* Fri Apr 12 2024 Gang Li <gli@redhat.com>
- 1.3.0 release
- Add validate command: validate the checksum for maven artifacts
- Add index command: support to re-index of the speicified folder
- Add CF invalidating features:
  - Invalidate generated metadata files (maven-metadata*/package.json/index.html) after product uploading/deleting in CloudFront
  - Add command to do CF invalidating and checking
- Fix bug: picking the root package.json as the first priority one to generate npm package path

* Mon Sep 18 2023 Harsh Modi <hmodi@redhat.com>
- 1.2.2 release
- hot fix for "dist_tags" derived issue

* Wed Sep 13 2023 Harsh Modi <hmodi@redhat.com>
- 1.2.1 release
- Fix the aws list objects max 1000 limit issue
- Fix the "dist_tags" issue in npm metadata generation

* Thu Jun 29 2023 Harsh Modi <hmodi@redhat.com>
- 1.2.0 release
- Add maven repository artifact signature feature

* Tue Sep 20 2022 Harsh Modi <hmodi@redhat.com>
- 1.1.2 release
- add configuration schema and validation
- allow specifying multiple target buckets

* Thu Aug 25 2022 Harsh Modi <hmodi@redhat.com>
- 1.1.1 release
