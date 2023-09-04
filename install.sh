#!/bin/bash

# check that pip, virtualenv and git are installed
if ! [ -x "$(command -v virtualenv)" ]; then
  echo 'Error: virtualenv is not installed. Install virtualenv and try again.' >&2
  exit 1
fi
if ! [ -x "$(command -v pip)" ]; then
  echo 'Error: pip is not installed. Install pip and try again.' >&2
  exit 1
fi
if ! [ -x "$(command -v git)" ]; then
  echo 'Error: git is not installed. Install git and try again.' >&2
  exit 1
fi

# Welcome message
echo "Starting neuma installation script"

# Clone the repository
echo "- Cloning the repository into ./neuma/"
git clone -q https://github.com/mwmdev/neuma.git

# Navigate to the directory
cd ./neuma

# Create a python virtual environment
echo "- Creating a python virtual environment"
virtualenv -q -p python3 env

# Activate the virtual environment
echo "- Activating the virtual environment"
source ./env/bin/activate

# Install required dependencies
echo "- Installing required dependencies"
pip install -q -r requirements.txt

# Rename .env_example to .env
mv .env_example .env

# Prompt for OpenAI API Key
read -p "- Enter your OpenAI API Key (Press Enter to skip): " openai_api_key
if [ -z "$openai_api_key" ]
  echo "- Skipping OpenAI API Key, you can enter it later in ~/.config/neuma/.env"
else
  echo "OPENAI_API_KEY=$openai_api_key" >> .env
fi

# Prompt for Google Application Credentials
read -p "- Enter the path to your Google Application Credentials .json file (Press Enter to skip): " google_application_credentials
if [ -z "$google_application_credentials" ]
  echo "- Skipping Google Application Credentials, you can enter it manually in ~/.config/neuma/.env"
else
  echo "GOOGLE_APPLICATION_CREDENTIALS=$google_application_credentials" >> .env
fi

# Move config files to the ~/.config/neuma/ folder
echo "- Moving default config files to ~/.config/neuma/"
mkdir -p ~/.config/neuma
mv .env config.toml personae.toml ~/.config/neuma/

# Print message
echo "- Installation complete."
echo "Run 'python ./neuma/neuma.py' to start the program."
