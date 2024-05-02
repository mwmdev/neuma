#!/bin/bash

# check that pip, virtualenv and git are installed
if ! [ -x "$(command -v pip)" ]; then
  echo 'Error: pip is not installed. Install python3-pip and try again.' >&2
  exit 1
fi

if ! [ -x "$(command -v virtualenv)" ]; then
  echo 'Error: virtualenv is not installed. Install python3-virtualenv and try again.' >&2
  exit 1
fi

if ! [ -x "$(command -v git)" ]; then
  echo 'Error: git is not installed. Install git and try again.' >&2
  exit 1
fi

# Welcome message
echo "Starting neuma installation script"

# Clone the repository
echo "- Cloning repository into ./neuma/"
git clone -q https://github.com/mwmdev/neuma.git
sleep 10

# Create a python virtual environment
echo "- Creating virtual environment"
virtualenv -q -p python3 ./neuma/env
sleep 5

# Activate the virtual environment
echo "- Activating virtual environment"
source ./neuma/env/bin/activate

# Install required dependencies
echo "- Installing required dependencies"
pip install -q -r ./neuma/requirements.txt

# Rename .env_example to .env
mv ./neuma/.env_example ./neuma/.env

# Prompt for OpenAI API Key
read -p "- Enter your OpenAI API Key (Press Enter to skip): " openai_api_key
if [ -z "$openai_api_key" ]; then
  echo "- Skipping OpenAI API Key, you can enter it later in ~/.config/neuma/.env"
  echo "OPENAI_API_KEY=\"\"" > ./neuma/.env
else
  echo "OPENAI_API_KEY=\"$openai_api_key\"" > ./neuma/.env
fi

# Move config files to the ~/.config/neuma/ folder
echo "- Moving default config files to ~/.config/neuma/"
mkdir -p ~/.config/neuma
mv ./neuma/.env ./neuma/config.toml ./neuma/personae.toml ~/.config/neuma/

# Print message
echo "- Installation complete."
echo "You can now Run 'source ./neuma/env/bin/activate && python3 ./neuma/neuma.py' to start the program."
