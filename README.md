# Neuma

Neuma is a ChatGPT interface for the command line written in python.

https://user-images.githubusercontent.com/31964517/232592981-fa89e5b0-f0b5-4688-afff-34a82b65d939.mp4

## Installation

Clone this repository to your local machine using the following command:

```bash git clone https://github.com/mwmdev/neuma.git```

Navigate to the directory where the repository was cloned:

```cd neuma```

Install the required dependencies by running:

```pip install -r requirements.txt```

Export your [ChatGPT API key](https://platform.openai.com/account/api-keys) as environment variable by adding this line to your preferre interactive shell rc file:

```export OPENAI_API_KEY="[REPLACE WITH API KEY]"```

For voice output you also need [Google Application Default Credentials](https://cloud.google.com/docs/authentication/provide-credentials-adc) :

```export GOOGLE_APPLICATION_CREDENTIALS="/path/to/crendentials.json"```

Finally, run the script with:

```python neuma.py```

## Usage

Use Neuma as an interactive chat, write your prompt and press enter. Wait for the answer, then continue the discussion.

Press `h` followed by `Enter` to list all the commands.

### Conversations

A conversaton is a series of prompts and answers.

`c` : List all saved conversations

`c [conversation]` : Open conversation [conversation]

`cc` : Create a new conversation

`cs [conversation]` : Save the current conversation as [conversation]

`ct [conversation]` : Trash the conversation [conversation]

`cy` : Copy the current conversation to the clipboard

### Modes

Modes define specific expected output behaviors. Custom modes are added by editing the `[modes]` section in the `config.toml` file.

`m` : List available modes

`m [mode]` : Switch to mode [mode]

#### Table

`m table`

Displays the response in a table. Works best when column header are defined explicitely and when temperature is low.

Example:

![table](https://user-images.githubusercontent.com/31964517/232883102-cb3d5e1c-6d95-4c52-9b77-f210a3479173.png)

#### Code

`m code`

Displays only syntax highlighted code.

Start with `#` followed by the language and the requested code.

Example:

![code](https://user-images.githubusercontent.com/31964517/232888337-9c880576-a190-427d-820a-5850408d3ca0.png)

#### Trans

`m trans`

Displays translations.

Start with `#` followed by the language to translate into and the phrase to translate.

Example:

![trans](https://user-images.githubusercontent.com/31964517/232889279-5bac3e2b-1c3b-4cd6-add6-a4111210ab9f.png)

### Personae

Personae are profiles defined by a specific starting prompt and are defined in the `personae.toml` file.

`p` : List available personae

`p [persona]` : Switch to persona

### Voice output

Voice output languages are defined in `config.toml`, here's a [list of supported voices](https://cloud.google.com/text-to-speech/docs/voices).

`l` : List available languages for voice output

`l [language]` : Set language to [language]

`vo` : Toggle voice output

### Voice input

Voice input can be used to transcribe voice to text.

`vi` :  Switch to voice input

### Other commands

`y` : Copy the last answer to the clipboard

`t [temperature]` : Sets the ChatGPT model [temperature](https://platform.openai.com/docs/api-reference/completions/create#completions/create-temperature).

`tp [top_p]` : Sets the ChatGPT model [top_p](https://platform.openai.com/docs/api-reference/completions/create#completions/create-top_p).

`cls` : Clear the screen

`r` : Restart the application

`q` : Quit

