<img align="right" style="width:20%; min-width:150px; max-width:250px; margin:40px 20px;" alt = "terminal based chatgpt" title = "Ah0 M374KI45E" src = "public/neuma.png"/>

`neuma` is a minimalistic ChatGPT interface for the command line.

![render1682022113695](https://user-images.githubusercontent.com/31964517/233479690-81521ceb-2443-4a0e-ab1f-0b0b100a75db.gif)

## Features

- **Conversations** management (create, save, copy, delete)
- **Modes** (normal, table, code, translate, impersonate, summarize, csv)
- **Personae** profiles with custom starting prompt
- **File contents** and **Web pages** accessible in prompts
- **Voice input / output**
- and a few other things...

## Installation

Those instructions are for Linux, they may vary for other systems.

Clone this repository to your local machine using the following command:

```git clone https://github.com/mwmdev/neuma.git```

Navigate to the directory where the repository was cloned:

```cd neuma```

Install the required dependencies by running:

```pip install -r requirements.txt```

Rename the `.env_example` to `.env` with:

```mv .env_example .env```

Edit `.env` and add your  [ChatGPT API key](https://platform.openai.com/account/api-keys).
For voice output you also need [Google Application Default Credentials](https://cloud.google.com/docs/authentication/provide-credentials-adc).

Move all config files to your `.config/neuma/` folder with:

```mkdir ~/.config/neuma && mv .env config.toml persona.toml ~/.config/neuma/```

Finally, run the script with:

```python neuma.py```

## Usage

Use `neuma` as an interactive chat, write your prompt and press enter. Wait for the answer, then continue the discussion.

Press `h` followed by `Enter` to list all the commands.

```
> h
┌───────────────────┬────────────────────────────────────────┐
│ Command           │ Description                            │
├───────────────────┼────────────────────────────────────────┤
│ h                 │ Display this help section              │
│ r                 │ Restart application                    │
│ c                 │ List saved conversations               │
│ c [conversation]  │ Open conversation [conversation]       │
│ cc                │ Create a new conversation              │
│ cs                │ Save the current conversation          │
│ ct [conversation] │ Trash conversation [conversation]      │
│ cy                │ Copy current conversation to clipboard │
│ m                 │ List available modes                   │
│ m [mode]          │ Switch to mode [mode]                  │
│ p                 │ List available personae                │
│ p [persona]       │ Switch to persona [persona]            │
│ l                 │ List available languages               │
│ l [language]      │ Set language to [language]             │
│ vi                │ Switch to voice input                  │
│ vo                │ Switch on voice output                 │
│ y                 │ Copy last answer to clipboard          │
│ t [temp]          │ Set the temperature to [temp]          │
│ tp [top_p]        │ Set the top_p to [top_p]               │
│ mt [max_tokens]   │ Set the max_tokens to [max_tokens]     │
│ c                 │ Clear the screen                       │
│ q                 │ Quit                                   │
└───────────────────┴────────────────────────────────────────┘
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

#### Table display

`m table`

Displays the response in a table. Works best when column headers are defined explicitly and when `temperature` is set to 0.

```
> Five Hugo prize winners by : Name, Book, Year
  ┏━━━━━━━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┳━━━━━━┓
  ┃ Name               ┃ Book                                  ┃ Year ┃
  ┡━━━━━━━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━╇━━━━━━┩
  │ Isaac Asimov       │ Foundation’s Edge                     │ 1983 │
  ├────────────────────┼───────────────────────────────────────┼──────┤
  │ Orson Scott Card   │ Ender’s Game                          │ 1986 │
  ├────────────────────┼───────────────────────────────────────┼──────┤
  │ Ursula K. Le Guin  │ The Dispossessed: An Ambiguous Utopia │ 1975 │
  ├────────────────────┼───────────────────────────────────────┼──────┤
  │ Arthur C. Clarke   │ Rendezvous with Rama                 │ 1974 │
  ├────────────────────┼───────────────────────────────────────┼──────┤
  │ Robert A. Heinlein │ Double Star                           │ 1956 │
  └────────────────────┴───────────────────────────────────────┴──────┘
```

#### Code generator

`m code`

Displays only syntax highlighted code. Works best when `temperature` is set to 0.

Start with `#` followed by the name of the language and the requested code.

```html
> #html simple login form
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

Displays translations.

Start with `#` followed by the name of the language to translate into and the phrase to translate.

```
> #german What's the carbon footprint of nuclear energy ?
  Wie groß ist der CO2-Fußabdruck von Kernenergie?
```

#### Character impersonator

`m char`

Start with `#` followed by the name of the character you want to be impersonated.

```
> #Bob_Marley Write the chorus to a new song.
  "Rise up and stand tall,
  Embrace the love that's all,
  Let your heart blaze and brawl,
  As we rock to the beat of this call."
```

#### CSV generator

`m csv`

Start with `#` followed by the separator you want to use.

```
> #; Five economics nobel prize winners by name, year, country and school of thought

  1; Milton Friedman; 1976; USA; Monetarism;
  2; Amartya Sen; 1998; India; Welfare economics;
  3; Joseph Stiglitz; 2001; USA; Information economics;
  4; Paul Krugman; 2008; USA; New trade theory;
  5; Esther Duflo; 2019; France; Development economics
```

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

Saying "Exit" will switch back to text input mode.

### Special placeholders

Use the `~{f:` `}~` notation to insert the content of a file into the prompt.

```
> Refactor the following code : ~{f:example.py}~
```

Use the `~{w:` `}~` notation to insert the content of a URL into the prompt.

```
> Summarize the following article : ~{w:https://www.freethink.com/health/lsd-mindmed-phase-2}~
```

__Note__: This can highly increase the number of tokens, use with caution.

### Other commands

`y` : Copy the last answer to the clipboard

`t [temperature]` : Set the ChatGPT model's [temperature](https://platform.openai.com/docs/api-reference/completions/create#completions/create-temperature).

`tp [top_p]` : Set the ChatGPT model's [top_p](https://platform.openai.com/docs/api-reference/completions/create#completions/create-top_p).

`mt [max_tokens]` : Set the ChatGPT model's [max_tokens](https://platform.openai.com/docs/api-reference/completions/create#completions/create-max_tokens).

`cls` : Clear the screen

`r` : Restart the application

`q` : Quit


## Color theme

The colors of each type of text (prompt, answer, info msg, etc.) are defined in the `config.toml` file.
