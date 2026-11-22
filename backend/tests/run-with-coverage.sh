#!/bin/sh
# Runs unit and integration tests and enforces the coverage thresholds.
set -eu

coverage run -m pytest -q -p no:cacheprovider --junitxml=/reports/backend-junit.xml tests/unit tests/integration
coverage xml -q -o /reports/backend-coverage.xml
coverage report --skip-covered --fail-under=80
echo "domain and application:"
coverage report --skip-covered --include='*/domain/*,*/application/*' --fail-under=90
