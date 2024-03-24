<img align="right" style="width:20%; min-width:150px; max-width:250px; margin:40px 20px;" alt = "terminal based chatgpt" title = "Ah0 M374KI45E" src = "public/neuma.png"/>

`neuma` is a minimalistic ChatGPT interface for the command line.

![render1682022113695](https://user-images.githubusercontent.com/31964517/233479690-81521ceb-2443-4a0e-ab1f-0b0b100a75db.gif)

## Features

- **Conversations** management (create, save, copy, delete)
- **Modes** (normal, table, code, translate, impersonate, summarize, csv)
- **Personae** profiles with custom starting prompt
- **Embeddings** management (embed documents, create vector dbs)
- **Voice input / output**
- and a few other things...

## Installation

Those instructions are for Linux, they may vary for other systems.

### One line install

You can launch the install script with the following command:

```shell
bash <(wget -qO- https://raw.githubusercontent.com/mwmdev/neuma/main/install.sh)
```
During the installation process you will be prompted for your  [ChatGPT API key](https://platform.openai.com/account/api-keys) and your [Google Application Default Credentials](https://cloud.google.com/docs/authentication/provide-credentials-adc) (for voice output). You can also skip those steps and add them later.

### Manual install

Clone this repository to your local machine using the following command:

```shell
git clone https://github.com/mwmdev/neuma.git
```

Navigate to the directory where the repository was cloned:

```shell
cd neuma
```

Install the required dependencies by running:

```shell
pip install -r requirements.txt
```

Rename the `.env_example` to `.env` with:

```shell
mv .env_example .env
```

Edit `.env` and add your  [ChatGPT API key](https://platform.openai.com/account/api-keys).
For voice output you also need [Google Application Default Credentials](https://cloud.google.com/docs/authentication/provide-credentials-adc).

Move all config files to your `.config/neuma/` folder with:

```shell
mkdir ~/.config/neuma && mv .env config.toml persona.toml ~/.config/neuma/
```

Finally, run the script with:

```shell
python neuma.py
```

### Create an alias

To make it easier to run `neuma`, you can create an alias in your `.bashrc` or `.zshrc` file by adding the following line:

```
alias neuma='python /path/to/neuma.py'*
```

## Usage

Use `neuma` as an interactive chat, write your prompt and press enter. Wait for the answer, then continue the discussion.

Press `h` followed by `Enter` to list all the commands.

```
> h
┌───────────────────┬─────────────────────────────────────────────────┐
│ Command           │ Description                                     │
├───────────────────┼─────────────────────────────────────────────────┤
│ h                 │ Display this help section                       │
│ r                 │ Restart application                             │
│ c                 │ List saved conversations                        │
│ c [conversation]  │ Open conversation [conversation]                │
│ cc                │ Create a new conversation                       │
│ cs [conversation] │ Save the current conversation as [conversation] │
│ ct [conversation] │ Trash conversation [conversation]               │
│ cy                │ Copy current conversation to clipboard          │
│ m                 │ List available modes                            │
│ m [mode]          │ Switch to mode [mode]                           │
│ p                 │ List available personae                         │
│ p [persona]       │ Switch to persona [persona]                     │
│ l                 │ List available languages                        │
│ l [language]      │ Set language to [language]                      │
│ vi                │ Switch to voice input                           │
│ vo                │ Switch on voice output                          │
│ d                 │ List available vector dbs                       │
│ d [db]            │ Create or switch to vector db [db]              │
│ dt [db]           │ Trash vector db [db]                            │
│ e [/path/to/file] │ Embed [/path/to/file] document into current db  │
│ y                 │ Copy last answer to clipboard                   │
│ t                 │ Get the current temperature                     │
│ t [temp]          │ Set the temperature to [temp]                   │
│ tp                │ Get the current top_p value                     │
│ tp [top_p]        │ Set the top_p to [top_p]                        │
│ mt                │ Get the current max_tokens value                │
│ mt [max_tokens]   │ Set the max_tokens to [max_tokens]              │
│ g                 │ List available GPT models                       │
│ g [model]         │ Set GPT model to [model]                        │
│ lm                │ List available microphones                      │
│ cls               │ Clear the screen                                │
│ q                 │ Quit                                            │
└───────────────────┴─────────────────────────────────────────────────┘
```

### Conversations

A conversaton is a series of prompts and answers. Conversations are stored as `.neu` text files in the data folder defined in `config.toml`.

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

Here are some of the built-in modes :

#### Table display

`m table`

Displays the response in a table. Works best when column headers are defined explicitly in the prompt and `temperature` is set to 0.

Example:

```
> Five Hugo prize winners by : Name, Book, Year
```

Output:

```
  ┏━━━━━━━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┳━━━━━━┓
  ┃ Name               ┃ Book                                  ┃ Year ┃
  ┡━━━━━━━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━╇━━━━━━┩
  │ Isaac Asimov       │ Foundation’s Edge                     │ 1983 │
  ├────────────────────┼───────────────────────────────────────┼──────┤
  │ Orson Scott Card   │ Ender’s Game                          │ 1986 │
  ├────────────────────┼───────────────────────────────────────┼──────┤
  │ Ursula K. Le Guin  │ The Dispossessed: An Ambiguous Utopia │ 1975 │
  ├────────────────────┼───────────────────────────────────────┼──────┤
  │ Arthur C. Clarke   │ Rendezvous with Rama                  │ 1974 │
  ├────────────────────┼───────────────────────────────────────┼──────┤
  │ Robert A. Heinlein │ Double Star                           │ 1956 │
  └────────────────────┴───────────────────────────────────────┴──────┘
```

#### Code generator

`m code`

Displays only syntax highlighted code. Works best when `temperature` is set to 0.

Start with `#` followed by the name of the language and the prompt.

Example:

```
> #html simple login form
```

Output:
```html
  <!DOCTYPE html>
  <html>
    <head>
      <title>Login Form</title>
    </head>
    <body>
      <!-- Login form starts here -->
      <form action="#" method="post">
        <h2>Login</h2>
        <label for="username">Username:</label><br>
        <input type="text" id="username" name="username"><br><br>
        <label for="password">Password:</label><br>
        <input type="password" id="password" name="password"><br><br>
        <input type="submit" value="Submit">
      </form>
      <!-- Login form ends here -->
    </body>
  </html>
```

#### Translator

`m trans`

Translates text into another language. Works best when `temperature` is set to 0.

Start with `#` followed by the name of the language to translate into and the word or phrase to translate.

Example:
```
> #german What's the carbon footprint of nuclear energy ?
```

Output:
```
  Wie groß ist der CO2-Fußabdruck von Kernenergie?
```

#### Character impersonator

`m char`

Impersonates a character.

Start with `#` followed by the name of the character you want to be impersonated and your prompt.

Example:

```
> #Bob_Marley Write the chorus to a new song.
```

Output:
```
  "Rise up and stand tall,
  Embrace the love that's all,
  Let your heart blaze and brawl,
  As we rock to the beat of this call."
```

#### CSV generator

`m csv`

Generates a CSV table. Works best when `temperature` is set to 0.

Start with `#` followed by the separator you want to use and your prompt.

Example:
```
> #; Five economics nobel prize winners by name, year, country and school of thought
```

Output:

```
  1; Milton Friedman; 1976; USA; Monetarism;
  2; Amartya Sen; 1998; India; Welfare economics;
  3; Joseph Stiglitz; 2001; USA; Information economics;
  4; Paul Krugman; 2008; USA; New trade theory;
  5; Esther Duflo; 2019; France; Development economics
```

### Personae

Personae are profiles defined by a specific starting prompt and temperature, they are configured in the `personae.toml` file.

`p` : List available personae

`p [persona]` : Switch to persona

The default persona has this starting prompt :

```
[[persona]]
name = "default"
temp = 0.5
[[persona.messages]]
role = "system"
content = "You are a helpful assistant."
[[persona.messages]]
role = "user"
content = "What is the capital of Mexico?"
[[persona.messages]]
role = "assistant"
content = "The capital of Mexico is Mexico City"
```

To add new personae, copy paste the default persona and give it a new name, then edit the system prompt.

The user and assistant messages are optional, but help with accuracy. You can add as many user/assistant messages as you like (increases token count).

### Voice output

Voice output languages are defined in `config.toml`, here's a [list of supported voices](https://cloud.google.com/text-to-speech/docs/voices).

`l` : List available languages for voice output

`l [language]` : Set language to [language]

`vo` : Toggle voice output

### Voice input

Voice input can be used to transcribe voice to text.

`vi` :  Switch to voice input

Saying "Disable voice input" will switch back to text input mode.

You can list available microphones with `lm` and set the one you want to use in the `audio` section of the config file.

```
[audio]
input_device = 4 # the device for voice input (list devices with "lm")
input_timeout = 5 # the number of seconds after which listening stops and transcription starts
input_limit = 20 # the maximum number of seconds that can be listened to in one go
```

### Special placeholders

Use the `~{f:` `}~` notation to insert the content of a file into the prompt.

```
> Refactor the following code : ~{f:example.py}~
```

Use the `~{w:` `}~` notation to insert the content of a URL into the prompt.

```
> Summarize the following article : ~{w:https://www.freethink.com/health/lsd-mindmed-phase-2}~
```

__Note__: This can highly increase the number of tokens, use with caution. For large content use embeddings instead.

### Embeddings

Embeddings allow you to embed documents into the discussion to serve as context for the answers.
 
Supported file formats: csv, doc, docx, epub, html, md, odt, pdf, ppt, pptx, txt

`d` : List all available vector dbs

`d [db]` : Create or switch to [db] vector db

`dt [db]` : Trash [db] vector db (will delete all files and folders related to this vector db)

`e [/path/to/file]` : Embed [/path/to/file/] and store in current vector db

So, to chat with a document you can do the following :

- Create a persona with a profile that restricts answers to the context, like `"You will only answer a question if it can be determined from the context provided."`
- Switch to that persona 
- Create a vector db
- Embed a document
- Ask a question about it

### GPT models

You can switch between different GPT models. The default model is defined in the `config.toml` file.

`g` : List available GPT models

```
> g
  GPT Models                                                                                                                                                                                        
  gpt-3.5-turbo-0125                                                                                                                                                                                      
  gpt-4-turbo-preview                                                                                                                                                                                      
  gpt-4-0125-preview                                                                                                                                                                                       
  gpt-3.5-turbo-1106                                                                                                                                                                                       
  gpt-4-1106-preview                                                                                                                                                                                       
  gpt-4-vision-preview                                                                                                                                                                                     
  gpt-3.5-turbo-instruct-0914                                                                                                                                                                              
  gpt-3.5-turbo-instruct                                                                                                                                                                                   
  gpt-4                                                                                                                                                                                                    
  gpt-4-0613                                                                                                                                                                                               
  gpt-3.5-turbo-0613                                                                                                                                                                                       
  gpt-3.5-turbo-16k-0613                                                                                                                                                                                   
  gpt-3.5-turbo-16k                                                                                                                                                                                        
  gpt-3.5-turbo-0301                                                                                                                                                                                       
  gpt-3.5-turbo <
```

`g [model]` : Set GPT model to [model]

```
> g gpt-3.5-turbo
  Model set to gpt-3.5-turbo.                                                                                                                                                                              
> when is your knowledge cutoff
  My training data includes information up until September 2021.
  
> g gpt-4-turbo-preview
  Model set to gpt-4-turbo-preview.                                                                                                                                                                        
> when is your knowledge cutoff
  My knowledge is up to date until April 2023.
```

### Other commands

`y` : Copy the last answer to the clipboard

`t [temperature]` : Set the ChatGPT model's [temperature](https://platform.openai.com/docs/api-reference/completions/create#completions/create-temperature).

`tp [top_p]` : Set the ChatGPT model's [top_p](https://platform.openai.com/docs/api-reference/completions/create#completions/create-top_p).

`mt [max_tokens]` : Set the ChatGPT model's [max_tokens](https://platform.openai.com/docs/api-reference/completions/create#completions/create-max_tokens).

`cls` : Clear the screen

`r` : Restart the application

`q` : Quit

### Command line arguments

By default `neuma` starts in  interactive mode, but you can also use command line arguments to return an answer right away, which can be useful for output redirection or piping.

```
> python neuma.py -h

usage: neuma.py [-h] [-i INPUT] [-p PERSONAE] [-m MODE] [-t TEMP]

neuma is a minimalistic ChatGPT interface for the command line.

options:
  -h, --help                          Show this help message and exit
  -i INPUT, --input INPUT             Input prompt
  -p PERSONAE, --personae PERSONAE    Set personae
  -m MODE, --mode MODE                Set mode
  -t TEMP, --temp TEMP                Set temperature
```

Examples :

```
> python neuma.py -t 1.2 -i "Write a haiku about the moon"`
  
  Silver orb casts light,
  Guiding night journeys below
  Moon's tranquil, bright glow.
```

```
> python neuma.py -t 0 -m "table" -i "Five US National parks by : name, size, climate"`

  ┏━━┳━━━━━━━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━━━━━━━━━━━━━━┳━━┓
  ┃  ┃  National Park     ┃  Size (acres)  ┃  Climate                  ┃  ┃
  ┡━━╇━━━━━━━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━━━━━━━━━━━━━━╇━━┩
  │  │  Yellowstone       │  2,219,791     │  Continental              │  │
  ├──┼────────────────────┼────────────────┼───────────────────────────┼──┤
  │  │  Yosemite          │  761,747       │  Mediterranean            │  │
  ├──┼────────────────────┼────────────────┼───────────────────────────┼──┤
  │  │  Grand Canyon      │  1,217,262     │  Arid                     │  │
  ├──┼────────────────────┼────────────────┼───────────────────────────┼──┤
  │  │  Glacier           │  1,013,125     │  Continental              │  │
  ├──┼────────────────────┼────────────────┼───────────────────────────┼──┤
  │  │  Rocky Mountain    │  265,807       │  Alpine                   │  │
  └──┴────────────────────┴────────────────┴───────────────────────────┴──┘`
```

## Color theme

The colors of each type of text (prompt, answer, info msg, etc.) are defined in the `config.toml` file (default is [gruvbox](https://github.com/morhetz/gruvbox)).
