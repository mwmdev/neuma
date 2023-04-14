# Neuma

Neuma is a ChatGPT interface for the command line written in python.

## Installation

Clone this repository to your local machine using the following command:

```bash git clone https://github.com/mwmdev/neuma.git```

Navigate to the directory where the repository was cloned:

```cd neuma```

Install the required dependencies by running:

```pip install -r requirements.txt```

Export your [ChatGPT API key](https://platform.openai.com/account/api-keys) as environment variable.

Add this line to your preferre interactive shell rc file (ex: .bashrc)

```export OPENAI_API_KEY="[REPLACE WITH API KEY]"```

For voice output you also need [Google Application Default Credentials](https://cloud.google.com/docs/authentication/provide-credentials-adc) :

```export GOOGLE_APPLICATION_CREDENTIALS="/path/to/crendentials.json"```

Finally, run the script with:

```python neuma.py```

## Usage

Use Neuma as an interactive chat, write your prompt and press enter. Wait for the answer, then continue the discussion.

Special commands are available and are detailed below.

Press `h` followed by `Enter` to list all the commands.

### Conversations

A conversaton is a series of prompts and answers.

`conversations` or `c` : List all saved conversations
`conversation open [conversation]` or `c [conversation]` : Open conversation [conversation]
`conversation create` or `cc` : Create a new conversation








