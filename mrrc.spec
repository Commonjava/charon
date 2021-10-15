%global binaries_py_version %{python3_version}
%global owner Commonjava
%global project mrrc-uploader

Name:           %{project}
Version:        1.0.0
Release:        1%{?dist}

Summary:        MRRC CLI for Indy
Group:          Development/Tools
License:        APLv2
URL:            https://github.com/%{owner}/%{project}
Source0:        https://github.com/%{owner}/%{project}/archive/%{version}.tar.gz

BuildArch:      noarch

Requires:       python3-mrrc = %{version}-%{release}
Requires:       git >= 1.7.10

BuildRequires:  python3-devel
BuildRequires:  python3-setuptools

%description
Simple Python tool with command line interface for MRRC init,
upload, delete, gen and ls functions.

%package -n python3-mrrc
Summary:        Python 3 MRRC library
Group:          Development/Tools
License:        APLv2
Requires:       python3-requests
Requires:       python3-setuptools
Requires:       python3-rpm
%{?python_provide:%python_provide python3-mrrc}

%description -n python3-mrrc
Simple Python 3 library for MRRC functions.

%prep
%setup -q

%build
%py3_build


%install
%py3_install
mv %{buildroot}%{_bindir}/mrrc %{buildroot}%{_bindir}/mrrc-%{python3_version}
ln -s %{_bindir}/mrrc-%{python3_version} %{buildroot}%{_bindir}/mrrc-3

ln -s %{_bindir}/mrrc-%{binaries_py_version} %{buildroot}%{_bindir}/mrrc

# ship mrrc in form of tarball so it can be installed within build image
mkdir -p %{buildroot}/%{_datadir}/%{name}/
cp -a %{sources} %{buildroot}/%{_datadir}/%{name}/mrrc.tar.gz

# setup docs
#mkdir -p %{buildroot}%{_mandir}/man1
#cp -a docs/manpage/mrrc.1 %{buildroot}%{_mandir}/man1/


%files
%doc README.md
#%{_mandir}/man1/mrrc.1*
%{!?_licensedir:%global license %doc}
%license LICENSE
%{_bindir}/mrrc

%files -n python3-mrrc
%doc README.md
%{!?_licensedir:%global license %doc}
%license LICENSE
%{_bindir}/mrrc-%{python3_version}
%{_bindir}/mrrc-3
#%{_mandir}/man1/mrrc.1*
%dir %{python3_sitelib}/mrrc
%dir %{python3_sitelib}/mrrc/__pycache__
%{python3_sitelib}/mrrc/*.*
%{python3_sitelib}/mrrc/cmd
%{python3_sitelib}/mrrc/pkgs
%{python3_sitelib}/mrrc/utils
%{python3_sitelib}/mrrc/__pycache__/*.py*
%{python3_sitelib}/mrrc_*.egg-info
%dir %{_datadir}/%{name}
# ship mrrc in form of tarball so it can be installed within build image
%{_datadir}/%{name}/mrrc.tar.gz


%changelog
