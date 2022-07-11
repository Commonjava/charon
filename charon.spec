%global binaries_py_version %{python3_version}
%global owner Commonjava
%global project charon

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
Requires:       git >= 1.7.10

BuildRequires:  python3-devel
BuildRequires:  python3-setuptools

%description
Simple Python tool with command line interface for charon init,
upload, delete, gen and ls functions.

%package -n python3-charon
Summary:        Python 3 CHARON library
Group:          Development/Tools
License:        APLv2
Requires:       python3-requests
Requires:       python3-setuptools
Requires:       python3-rpm
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

# ship charon in form of tarball so it can be installed within build image
mkdir -p %{buildroot}/%{_datadir}/%{name}/
cp -a %{sources} %{buildroot}/%{_datadir}/%{name}/charon.tar.gz

# setup docs
#mkdir -p %{buildroot}%{_mandir}/man1
#cp -a docs/manpage/charon.1 %{buildroot}%{_mandir}/man1/


%files
%doc README.md
#%{_mandir}/man1/charon.1*
%{!?_licensedir:%global license %doc}
%license LICENSE
%{_bindir}/charon

%files -n python3-charon
%doc README.md
%{!?_licensedir:%global license %doc}
%license LICENSE
%{_bindir}/charon-%{python3_version}
%{_bindir}/charon-3
#%{_mandir}/man1/charon.1*
%dir %{python3_sitelib}/charon
%dir %{python3_sitelib}/charon/__pycache__
%{python3_sitelib}/charon/*.*
%{python3_sitelib}/charon/cmd
%{python3_sitelib}/charon/pkgs
%{python3_sitelib}/charon/utils
%{python3_sitelib}/charon/__pycache__/*.py*
%{python3_sitelib}/charon_*.egg-info
%dir %{_datadir}/%{name}
# ship charon in form of tarball so it can be installed within build image
%{_datadir}/%{name}/charon.tar.gz


%changelog
