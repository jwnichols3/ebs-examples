#!/bin/bash

# The first argument is the sub-folder for the lambda function, e.g., "vpc-endpoints-check"
LAMBDA_SUBFOLDER=$1
PYTHON_COMMAND="python3.11"
PROJECT_ROOT=$(pwd)
LAMBDA_FOLDER="${PROJECT_ROOT}/${LAMBDA_SUBFOLDER}"

# Create a new virtual environment in the sub-folder using Python 3.11
$PYTHON_COMMAND -m venv "${LAMBDA_FOLDER}/venv"

# Activate the virtual environment
source "${LAMBDA_FOLDER}/venv/bin/activate"

# Upgrade pip to the latest version
pip install --upgrade pip

# Install dependencies into the virtual environment
pip install -r "${LAMBDA_FOLDER}/requirements.txt"

# Deactivate the virtual environment
deactivate

# Prepare the package directory
PACKAGE_FOLDER="${LAMBDA_FOLDER}/package"
rm -rf "${PACKAGE_FOLDER}"
mkdir "${PACKAGE_FOLDER}"

# Copy the installed dependencies from the virtualenv to the package directory
cp -r "${LAMBDA_FOLDER}/venv/lib/${PYTHON_COMMAND}/site-packages/." "${PACKAGE_FOLDER}"

# Copy the lambda function script to the package directory
cp "${LAMBDA_FOLDER}/vpc-endpoints-check-lambda.py" "${PACKAGE_FOLDER}"

# Zip the package
cd "${PACKAGE_FOLDER}"
zip -r9 "${PROJECT_ROOT}/${LAMBDA_SUBFOLDER}.zip" .

# Clean up the package folder if you don't want it after zipping
rm -rf "${PACKAGE_FOLDER}"

# Deactivate and remove the virtual environment if it's no longer needed
rm -rf "${LAMBDA_FOLDER}/venv"

echo "Lambda function package is ready: ${LAMBDA_SUBFOLDER}.zip"
