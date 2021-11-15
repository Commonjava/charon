#!/bin/bash
set -eux

# Prepare env vars
ENGINE=${ENGINE:="podman"}
OS=${OS:="centos"}
OS_VERSION=${OS_VERSION:="8"}
PYTHON_VERSION=${PYTHON_VERSION:="3"}
ACTION=${ACTION:="test"}
IMAGE="$OS:$OS_VERSION"
CONTAINER_NAME="charon-$OS-$OS_VERSION-py$PYTHON_VERSION"

# Use arrays to prevent globbing and word splitting
engine_mounts=(-v "$PWD":"$PWD":z)
for dir in ${EXTRA_MOUNT:-}; do
  engine_mounts=("${engine_mounts[@]}" -v "$dir":"$dir":z)
done

# Create or resurrect container if needed
if [[ $($ENGINE ps -qa -f name="$CONTAINER_NAME" | wc -l) -eq 0 ]]; then
  $ENGINE run --name "$CONTAINER_NAME" -d "${engine_mounts[@]}" -w "$PWD" -ti "$IMAGE" sleep infinity
elif [[ $($ENGINE ps -q -f name="$CONTAINER_NAME" | wc -l) -eq 0 ]]; then
  echo found stopped existing container, restarting. volume mounts cannot be updated.
  $ENGINE container start "$CONTAINER_NAME"
fi

function setup_charon() {
  RUN="$ENGINE exec -i $CONTAINER_NAME"
  PYTHON="python$PYTHON_VERSION"
  PIP_PKG="$PYTHON-pip"
  PIP="pip$PYTHON_VERSION"
  PKG="dnf"
  PKG_EXTRA=(dnf-plugins-core git "$PYTHON"-pylint)
  BUILDDEP=(dnf builddep)
  if [[ $OS == "centos" ]]; then
    ENABLE_REPO=
  else
    ENABLE_REPO="--enablerepo=updates-testing"
  fi

  PIP_INST=("$PIP" install --index-url "${PYPI_INDEX:-https://pypi.org/simple}")

  if [[ $OS == "centos" ]]; then
    # Don't let builddep enable *-source repos since they give 404 errors
    $RUN rm -f /etc/yum.repos.d/CentOS-Sources.repo
    # This has to run *before* we try installing anything from EPEL
    $RUN $PKG $ENABLE_REPO install -y epel-release
  fi

  # RPM install basic dependencies
  $RUN $PKG $ENABLE_REPO install -y "${PKG_EXTRA[@]}"
  # RPM install build dependencies for charon
  $RUN "${BUILDDEP[@]}" -y charon.spec

  # Install package
  $RUN $PKG install -y $PIP_PKG

  # Upgrade pip to provide latest features for successful installation
  $RUN "${PIP_INST[@]}" --upgrade pip

  if [[ $OS == centos ]]; then
    # Pip install/upgrade setuptools. Older versions of setuptools don't understand the
    # environment markers used by docker-squash's requirements, also
    # CentOS needs to have setuptools updates to make pytest-cov work
    $RUN "${PIP_INST[@]}" --upgrade setuptools
  fi

  # install with RPM_PY_SYS=true to avoid error caused by installing on system python
  $RUN sh -c "RPM_PY_SYS=true ${PIP_INST[*]} rpm-py-installer"
  # Setuptools install charon from source
  $RUN $PYTHON setup.py install

  # Pip install packages for unit tests
  $RUN "${PIP_INST[@]}" -r tests/requirements.txt
}

case ${ACTION} in
"test")
  setup_charon
  TEST_CMD="coverage run --source=charon -m pytest tests"
  ;;
"pylint")
  setup_charon
  PACKAGES='charon tests'
  TEST_CMD="${PYTHON} -m pylint ${PACKAGES}"
  ;;
"bandit")
  setup_charon
  $RUN "${PIP_INST[@]}" bandit
  TEST_CMD="bandit-baseline -r charon -ll -ii"
  ;;
*)
  echo "Unknown action: ${ACTION}"
  exit 2
  ;;
esac

# Run tests
# shellcheck disable=SC2086
$RUN ${TEST_CMD} "$@"

echo "To run tests again:"
echo "$RUN ${TEST_CMD}"
