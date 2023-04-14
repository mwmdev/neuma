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

`conversation save [conversation]` or `cs [conversation]` : Save the current conversation as [conversation]

`conversation trash [conversation] or `ct [conversation]` : Trash the conversation [conversation]

`conversation yank` or `cy` : Copy the current conversation to the clipboard

### Modes

Modes define specific expected output behaviors. Custom modes are added by editing the `[modes]` section in the `config.toml` file.

`modes` or `m` : List available modes

`mode [mode]` or `m [mode]` : Switch to mode [mode]

#### Available modes

- **table** : Displays the response in a table
- **code** : Displays only code
- **trans** : Displays translations
- **char** : Impersonates any character, real or fiction

### Personae

Personae are profiles defined by a specific starting prompt and are defined in the `personae.toml` file.

`personae` or `p` : List available personae

`persona [persona]` or `p [persona]` : Switch to persona

### Voice output

Voice output languages are defined in `config.toml`, here's a [list of supported voices](https://cloud.google.com/text-to-speech/docs/voices)

`languages` or `l` : List available languages for voice output

`language [language]` or `l [language]` : Set language to [language]

`voice output` or `vo` : Toggle voice output

### Voice input

Voice input can be used to transcribe voice to text.

`voice input` or `vi` :  Switch to voice input

### Other commands

`yank` or `y` : Copy the last answer to the clipboard

`temp [temperature]` or `t [temperature]` : Sets the ChatGPT model [temperature](https://platform.openai.com/docs/api-reference/completions/create#completions/create-temperature).

`clear` or `cls` : Clear the screen

`restart` or `r` : Restart the application

`quit` or `q` : Quit

