%global binaries_py_version %{python3_version}
%global owner Commonjava
%global project hermes

Name:           %{project}
Version:        1.0.0
Release:        1%{?dist}

Summary:        Hermes CLI
Group:          Development/Tools
License:        APLv2
URL:            https://github.com/%{owner}/%{project}
Source0:        https://github.com/%{owner}/%{project}/archive/%{version}.tar.gz

BuildArch:      noarch

Requires:       python3-hermes = %{version}-%{release}
Requires:       git >= 1.7.10

BuildRequires:  python3-devel
BuildRequires:  python3-setuptools

%description
Simple Python tool with command line interface for hermes init,
upload, delete, gen and ls functions.

%package -n python3-hermes
Summary:        Python 3 HERMES library
Group:          Development/Tools
License:        APLv2
Requires:       python3-requests
Requires:       python3-setuptools
Requires:       python3-rpm
%{?python_provide:%python_provide python3-hermes}

%description -n python3-hermes
Simple Python 3 library for HERMES functions.

%prep
%setup -q

%build
%py3_build


%install
%py3_install
mv %{buildroot}%{_bindir}/hermes %{buildroot}%{_bindir}/hermes-%{python3_version}
ln -s %{_bindir}/hermes-%{python3_version} %{buildroot}%{_bindir}/hermes-3

ln -s %{_bindir}/hermes-%{binaries_py_version} %{buildroot}%{_bindir}/hermes

# ship hermes in form of tarball so it can be installed within build image
mkdir -p %{buildroot}/%{_datadir}/%{name}/
cp -a %{sources} %{buildroot}/%{_datadir}/%{name}/hermes.tar.gz

# setup docs
#mkdir -p %{buildroot}%{_mandir}/man1
#cp -a docs/manpage/hermes.1 %{buildroot}%{_mandir}/man1/


%files
%doc README.md
#%{_mandir}/man1/hermes.1*
%{!?_licensedir:%global license %doc}
%license LICENSE
%{_bindir}/hermes

%files -n python3-hermes
%doc README.md
%{!?_licensedir:%global license %doc}
%license LICENSE
%{_bindir}/hermes-%{python3_version}
%{_bindir}/hermes-3
#%{_mandir}/man1/hermes.1*
%dir %{python3_sitelib}/hermes
%dir %{python3_sitelib}/hermes/__pycache__
%{python3_sitelib}/hermes/*.*
%{python3_sitelib}/hermes/cmd
%{python3_sitelib}/hermes/pkgs
%{python3_sitelib}/hermes/utils
%{python3_sitelib}/hermes/__pycache__/*.py*
%{python3_sitelib}/hermes_*.egg-info
%dir %{_datadir}/%{name}
# ship hermes in form of tarball so it can be installed within build image
%{_datadir}/%{name}/hermes.tar.gz


%changelog
