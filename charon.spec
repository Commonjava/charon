%global binaries_py_version %{python3_version}
%global owner Commonjava
%global project charon
%if 0%{?fedora}
# rhel/epel has older incompatible version of pytest (no caplog)
%global with_check 1
%endif

Name:           %{project}
Version:        1.1.1
Release:        1%{?dist}

Summary:        Charon CLI
Group:          Development/Tools
License:        APLv2
URL:            https://github.com/%{owner}/%{project}
Source0:        https://github.com/%{owner}/%{project}/archive/%{version}.tar.gz

BuildArch:      noarch

Requires:       python3-charon = %{version}-%{release}

BuildRequires:  git-core
BuildRequires:  python3-devel
BuildRequires:  python3-setuptools

%if 0%{?with_check}
BuildRequires:  python3-setuptools-rust
BuildRequires:  python3-jinja2
BuildRequires:  python3-boto3
BuildRequires:  python3-botocore
BuildRequires:  python3-click
BuildRequires:  python3-requests
BuildRequires:  python3-ruamel-yaml
BuildRequires:  python3-defusedxml
%endif # with_check

Provides:       charon = %{version}-%{release}

%description
Simple Python tool with command line interface for charon init,
upload, delete, gen and ls functions.

%package -n python3-charon
Summary:   Python 3 CHARON library
Group:     Development/Tools
License:   APLv2
Requires:  python3-setuptools
Requires:  python3-setuptools-rust
Requires:  python3-jinja2
Requires:  python3-boto3
Requires:  python3-botocore
Requires:  python3-click
Requires:  python3-requests
Requires:  python3-ruamel-yaml
Requires:  python3-defusedxml

Provides:       python3-charon = %{version}-%{release}
%{?python_provide:%python_provide python3-charon}

%description -n python3-charon
Simple Python 3 library for CHARON functions.

%prep
%setup -q

%build
%py3_build


%install
%py3_install
mv %{buildroot}%{_bindir}/charon %{buildroot}%{_bindir}/charon-%{python3_version}
ln -s %{_bindir}/charon-%{python3_version} %{buildroot}%{_bindir}/charon-3
ln -s %{_bindir}/charon-%{binaries_py_version} %{buildroot}%{_bindir}/charon


%files
%doc README.md
%{!?_licensedir:%global license %doc}
%license LICENSE
%{_bindir}/charon

%files -n python3-charon
%doc README.md
%{!?_licensedir:%global license %doc}
%license LICENSE
%{_bindir}/charon-%{python3_version}
%{_bindir}/charon-3
%{python3_sitelib}/charon*

%changelog