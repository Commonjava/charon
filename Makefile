init-venv:
		@pip install virtualenv
		@python -m virtualenv venv
		@source venv/bin/activate
		@pip install -r requirements.txt
		@pip install tox
.PHONY: init, init-venv

lint:
		@python -m tox -e flake8
		@python -m tox -e pylint
.PHONY: lint

test-only:
		@python -m tox -e test
.PHONY: test-only

test: lint test-only
.PHONY: test

clean:
		rm -rf .coverage .tox .mypy_cache __pytest_reports htmlcov
		rm -rf build charon.egg-info dist local package
.PHONY: clean

build:
		@pip install -r ./requirements.txt
		@pip install .
.PHONY: build

sdist:
		@python3 setup.py sdist
.PHONY: sdist

image-latest:
		@podman build . -f ./image/Containerfile -t localhost/charon:latest
.PHONY: image-latest
