import os # For IO
import sys # For IO
import subprocess # For IO
import openai # The good stuff
import time # For logging
from time import sleep # Zzz
import toml # For parsing settings
import pyperclip # For copying to clipboard
import re # For regex
import requests # For accessing the web
from bs4 import BeautifulSoup # For parsing HTML
import readline

## Speech recognition
import threading
import speech_recognition
import sounddevice

## Voice output
from google.cloud import texttospeech

## Formatting
from rich.console import Console, OverflowMethod # https://rich.readthedocs.io/en/stable/console.html
from rich.theme import Theme
from rich.spinner import Spinner
from rich import print
from rich.padding import Padding
from rich.table import Table
from rich import box
from rich.syntax import Syntax

#{{{ Logging
class Logger:

    LOG_LEVELS = {
        'DEBUG': 0,
        'INFO': 1,
        'WARNING': 2,
        'ERROR': 3,
        'CRITICAL': 4
    }

    def __init__(self, filename):
        self.filename = filename
        self.level = self.LOG_LEVELS['INFO']
        try:
            open(filename, 'a').close()
            self.file = open(filename, 'a')
            self.file.truncate(0)
        except Exception as e:
            print(f"Error opening log file: {e}")

    def log(self, message: str, level: str ='INFO'):
        if level is not None:
            level_value = self.LOG_LEVELS[level]
        else:
            level_value = self.level

        if level_value >= self.level:
            write = self.file.write(f'{time.ctime()} [{level}] {message}\n')
            if write:
                self.file.flush()
            else:
                print(f'Error writing to log file: {write}')

    def close(self):
        self.file.close()

log = Logger('./neuma.log')
#}}}

#{{{ ChatModel
class ChatModel:

    def __init__(self):
        self.config = self.get_config()
        self.mode = "normal" # Default mode
        self.persona = "default" # Default persona
        self.voice_output = False # Default voice output
        self.voice = self.config["voices"]["english"] # Default voice

    #{{{ Get config
    def get_config(self) -> dict:
        """ Get config from config.toml and API keys from .env"""
        # Get config
        if os.path.isfile(os.path.expanduser("~/.config/neuma/config.toml")):
            config_path = os.path.expanduser("~/.config/neuma/config.toml")
        else:
            config_path = os.path.dirname(os.path.realpath(__file__)) + "/config.toml"
        try:
            with open(config_path, "r") as f:
                config = toml.load(f)
        except Exception as e:
            log.log("Error loading config: {}".format(e))
            return e

        # Get API keys
        if os.path.isfile(os.path.expanduser("~/.config/neuma/.env")):
            env_path = os.path.expanduser("~/.config/neuma/.env")
        else:
            env_path = os.path.dirname(os.path.realpath(__file__)) + "/.env"
        try:
            with open(env_path, "r") as f:
                env = toml.load(f)
                # OpenAI
                openai_api_key = env["OPENAI_API_KEY"]
                if openai_api_key:
                    config["openai"]["api_key"] = openai_api_key
                    log.log("OpenAI API key loaded : {}".format(config["openai"]))
                # Google app
                google_app_api_key = env["GOOGLE_APPLICATION_CREDENTIALS"]
                if google_app_api_key:
                    os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = google_app_api_key
                else:
                    raise ValueError("No API key found.")
        except Exception as e:
            log.log("Error loading API keys: {}".format(e))
            return e

        return config
    #}}}

    #{{{ Generate final prompt
    def generate_final_message(self, user_prompt: str) -> list:
        """ Generate final prompt (messages) for OpenAI API """

        # Add a dot at the end of the prompt if there isn't one
        if user_prompt[-1] not in ["?", "!", "."]:
            user_prompt += "."
        self.user_prompt = user_prompt

        # Conversation up to this point
        conversation = self.conversation
        log.log("conversation: {}".format(conversation))

        #{{{ Persona identity
        if not conversation:
            log.log("Persona : {}".format(self.persona))
            persona_identity = self.get_persona_identity()
            for message in persona_identity:
                conversation.append(message)
        #}}}

        #{{{ Mode instructions
        log.log("Mode : {}".format(self.mode))
        mode_instructions = self.config["modes"][self.mode]
        if mode_instructions:
            # Replace # with all the text after # in the user_prompt
            hashtag = self.find_hashtag(self.user_prompt)
            log.log("hashtag: {}".format(hashtag))
            if hashtag:
                mode_instructions = mode_instructions.replace("#", hashtag)
            mode_instructions_message = {"role": "system", "content": mode_instructions}
            conversation.append(mode_instructions_message)
            log.log("Mode instructions : {}".format(mode_instructions_message))
        #}}}

        #{{{ File content to insert
        if "~{f:" in user_prompt and "}~" in user_prompt:
            file_path = user_prompt.split("~{f:")[1].split("}~")[0]
            log.log("file_path: {}".format(file_path))
            if os.path.isfile(file_path):
                with open(file_path, "r") as f:
                    file_content = f.read()
                    user_prompt = user_prompt.replace("~{f:" + file_path + "}~", file_content)
                    log.log("user_prompt: {}".format(user_prompt))
            else:
                log.log("File not found")
        #}}}

        #{{{ URL content to insert
        if "~{w:" in user_prompt and "}~" in user_prompt:
            url = user_prompt.split("~{w:")[1].split("}~")[0]
            log.log("url: {}".format(url))
            try:
                response = requests.get(url)
                if response.status_code == 200:
                    log.log("response: {}".format(response))
                    soup = BeautifulSoup(response.text, "html.parser")
                    url_content = soup.get_text()
                    # remove all newlines and extra spaces
                    url_content = re.sub(r"\s+", " ", url_content)
                    if len(url_content) > 3000:
                        url_content = url_content[:3000]
                    user_prompt = user_prompt.replace("~{w:" + url + "}~", url_content)
                    log.log("user_prompt: {}".format(user_prompt))
                else:
                    log.log("Error getting URL content")
            except Exception as e:
                log.log("Error getting URL content: {}".format(e))
        #}}}

        #{{{ User input
        user_prompt = {"role": "user", "content": user_prompt}
        conversation.append(user_prompt)
        log.log("User prompt : {}".format(user_prompt))
        log.log("Final messages: {}".format(conversation))
        #}}}

        return conversation

    #}}}

    #{{{ Generate response from OpenAI API
    def generate_response(self, messages: list) -> str:
        """ Generate response from OpenAI API """
        api_key = self.config["openai"]["api_key"]
        # log.log("api_key: {}".format(api_key))
        model = self.config["openai"]["model"]
        log.log("model: {}".format(model))
        temperature = self.config["openai"]["temperature"]
        log.log("temperature: {}".format(temperature))
        top_p = self.config["openai"]["top_p"]
        log.log("top_p: {}".format(top_p))
        max_tokens = self.config["openai"]["max_tokens"]
        log.log("max_tokens: {}".format(max_tokens))

        try:
            chat_completions = openai.ChatCompletion.create(
                api_key = api_key,
                model = model,
                messages = messages,
                temperature = temperature,
                top_p = top_p,
                # n = 1,
                # stream = False,
                # stop = None,
                # max_tokens = max_tokens,
                # presence_penalty = 0.5,
                # frequency_penalty = 0.5,
            )

            # Get the first completion
            self.response = chat_completions.choices[0].message.content

            # Add to conversation
            response_message = {"role": "assistant", "content": self.response}
            log.log("Response : {}".format(response_message))
            self.conversation.append(response_message)

            # Process the response
            self.processed_response = self.process_response(self.response);

            return self.processed_response

        except Exception as e:
            return e

    #}}}

    #{{{ Process response
    def process_response(self, response: str) -> str:
        """ Process response, formats the response """

        #{{{ General formating

        # Remove double line breaks
        response = response.replace("\n\n", "\n")

        # Keep only what is between ``` and ```
        if "```" in response:
            response = response.split("```")[1]
            response = response.split("```")[0]

        #}}}

        #{{{ Table mode formatting
        if self.mode == "table":

            # Remove everything before the first |
            if "|" in response:
                response = response.split("|", 1)[1]
                response = "|" + response

            log.log("response: {}".format(response))

            lines = response.split("\n")
            lines = list(filter(None, lines))

            # remove lines that contain '---'
            lines = [line for line in lines if "---" not in line]

            # Create table
            table = Table(show_lines = True)

            # Add columns
            for column in lines[0].split("|"):
                table.add_column(column)

            # Add rows
            for row in lines[1:]:
                cells = row.split("|")
                table.add_row(*cells)

            # Return table
            return table

        #}}}

        #{{{ Code mode formatting
        elif self.mode == "code":
            language = self.find_hashtag(self.user_prompt)
            syntax = Syntax(response, language, line_numbers=False, theme="gruvbox-dark", word_wrap=True)
            return syntax
        #}}}

        #{{{ CSV mode formatting
        elif self.mode == "csv":
            separator = self.find_hashtag(self.user_prompt)
            response = response.replace(",", separator)

        return response
        #}}}

    #}}}

    #{{{ Personae

    # List personae
    def list_personae(self) -> str | list:
        """ List the available personae from the personae file """
        if os.path.isfile(os.path.expanduser("~/.config/neuma/personae.toml")):
            personae_path = os.path.expanduser("~/.config/neuma/personae.toml")
            log.log("Personae path : {}".format(personae_path))
        else:
            personae_path = os.path.dirname(os.path.realpath(__file__)) + "/personae.toml"
            log.log("Personae path : {}".format(personae_path))
        try:
            with open(personae_path, "r") as f:
                personae = toml.load(f)
                log.log("Personae : {}".format(personae))
        except Exception as e:
            return e
        return personae

    # Set persona
    def set_persona(self, persona: str) -> str:
        # TODO check if persona exists before setting
        self.persona = persona

    # Get persona
    def get_persona(self) -> str:
        return self.persona

    # Get persona prompt
    def get_persona_identity(self) -> list:
        if self.persona != "":
            personae = self.list_personae()
            for persona in personae["persona"]:
                if persona["name"] == self.persona:
                    persona_identity = persona["messages"]
                    log.log("Persona identity : {}".format(persona_identity))
        else:
            persona_identity = ""
        return persona_identity

    # OBS: Get persona language code
    def get_persona_language_code(self) -> str:
        if self.persona != "":
            personae = self.list_personae()
            for persona in personae["persona"]:
                if persona["name"] == self.persona:
                    language_code = persona["language_code"]
        else:
            language_code = ""
        return language_code

    # OBS: Get persona voice name
    def get_persona_voice_name(self) -> str:
        if self.persona != "":
            personae = self.list_personae()
            for persona in personae["persona"]:
                if persona["name"] == self.persona:
                    voice_name = persona["voice_name"]
        else:
            voice_name = ""
        return voice_name

    # }}}

    #{{{ Conversation

    # Create new conversation
    def new_conversation(self) -> list:
        self.conversation = []

    # Save conversation, write it to a file
    def save_conversation(self, filename: str) -> bool:
        data_folder = self.config["conversations"]["data_folder"]
        try:
            with open(data_folder + filename + '.neu', "w") as f:
                output = ""
                for message in self.conversation:
                    output += message['content'] + "\n\n"
                f.write(output)
        except Exception as e:
            return e
        return True

    # List conversations
    def list_conversations(self) -> list:
        data_folder = self.config["conversations"]["data_folder"]
        try:
            files = [f for f in os.listdir(data_folder) if f.endswith('.neu')]
        except Exception as e:
            return e
        return files

    # Open conversation
    def open_conversation(self, filename: str) -> str:
        data_folder = self.config["conversations"]["data_folder"]
        # Get list of files
        try:
            with open(data_folder + filename + ".neu", "r") as f:
                self.conversation = f.read()

        except Exception as e:
            return e
        return True

    # Trash conversation
    def trash_conversation(self, filename: str) -> bool:
        data_folder = self.config["conversations"]["data_folder"]
        # Get list of files
        try:
            os.remove(data_folder+filename+".neu")
        except Exception as e:
            return e
        return True

    #}}}

    #{{{ Modes

    # Get mode
    def get_mode(self) -> str:
        return self.mode

    # Set mode
    def set_mode(self, mode: str) -> None:
        # Check if mode exists before setting
        modes = self.list_modes()
        if mode in modes:
            self.mode = mode
        else:
            raise ValueError("No mode with that name found.")

    # List modes
    def list_modes(self) -> list:
        return self.config["modes"].keys()

    # Find hashtag in prompt
    def find_hashtag(self, prompt: str) -> str | bool:
        words = prompt.split(" ")
        for word in words:
            if word.startswith("#"):
                log.log("Hashtag found : {}".format(word))
                return word[1:]
        return False

    #}}}

    #{{{ Models

    #{{{ List models
    def list_models(self) -> list:
        models = openai.Model.list()
        return models
    #}}}

    #}}}

    #{{{ Voice input
    def listen(self) -> str:

        log.log("Listening...")

        # https://github.com/Uberi/speech_recognition
        recognizer = speech_recognition.Recognizer()

        with speech_recognition.Microphone() as source:
            recognizer.adjust_for_ambient_noise(source)
            #TODO: move settings to config
            audio = recognizer.listen(source, timeout=10, phrase_time_limit=60)

            with open("tmp.wav", "wb") as f:
                f.write(audio.get_wav_data())
            audio_file = open("tmp.wav", "rb")

            # Transcribe audio to text https://platform.openai.com/docs/guides/speech-to-text
            transcription = self.transcribe(audio_file)

            return transcription

    #}}}

    #{{{ Transcribe
    def transcribe(self, audio_file: str) -> str:
        api_key = self.config["openai"]["api_key"]
        model = "whisper-1"
        prompt = ""
        response_format = "json"
        temperature = 0
        language = self.voice[:2]
        try:
            transcription = openai.Audio.transcribe(
                api_key = api_key,
                model = model,
                file = audio_file,
                prompt = prompt,
                response_format = response_format,
                temperature = temperature,
                language = language
            )
            transcription = transcription["text"]
            return transcription

        except speech_recognition.RequestError as e:
            return e

    #}}}

    #{{{ Voice output
    def get_voice_output(self) -> str:
        return self.voice_output

    def set_voice_output(self, voice_output: str) -> None:
        self.voice_output = voice_output

    def get_voices(self) -> list:
        self.voices = self.config["voices"]
        return self.voices

    def get_voice(self) -> str:
        return self.voice

    def set_voice(self, voice: str) -> None:
        self.voice = self.config["voices"][voice]

    def speak(self, response: str) -> None:

        if self.voice_output == True:

            # Instantiates a client
            client = texttospeech.TextToSpeechClient()

            # Set the text input to be synthesized
            synthesis_input = texttospeech.SynthesisInput(text=response)

            # if a persona is set
            if self.persona != "":
                voice_name = self.get_persona_voice_name()
            else:
                voice_name = self.get_voice()

            language_code = voice_name[:5]

            # Build the voice request
            voice = texttospeech.VoiceSelectionParams(
                # https://cloud.google.com/text-to-speech/docs/voices
                language_code=language_code, name=voice_name
            )

            # Select the type of audio file you want returned
            audio_config = texttospeech.AudioConfig(
                audio_encoding=texttospeech.AudioEncoding.MP3
            )

            # Perform the text-to-speech request
            response = client.synthesize_speech(
                input=synthesis_input, voice=voice, audio_config=audio_config
            )

            # The response's audio_content is binary.
            with open("tmp.mp3", "wb") as out:

                # Write the response to the output file.
                out.write(response.audio_content)

                # play with mpv without output
                subprocess.run(["mpv", "--really-quiet", "tmp.mp3"])

                # remove the audio file
                os.remove("tmp.mp3")
    #}}}

    #{{{ Copy to clipboard
    def copy_to_clipboard(self, selection) -> None:
        output = ""
        if isinstance(selection, list):
            for message in selection:
                output += message['content'] + "\n\n"
        else:
            output = selection
        pyperclip.copy(output)
    #}}}

    #{{{ Set temperature
    def set_temperature(self, temperature: float) -> bool:
        self.config["openai"]["temperature"] = float(temperature)
        return True
    #}}}

    #{{{ Set top_p
    def set_top(self, top: float) -> bool:
        self.config["openai"]["top_p"] = float(top)
        return True
    #}}}

    #{{{ Set max_tokens
    def set_max_tokens(self, max_tokens: int) -> bool:
        self.config["openai"]["max_tokens"] = int(max_tokens)
        return True
    #}}}

#}}}

#{{{ ChatView
class ChatView:

    def __init__(self):
        self.chat_controller = None
        self.config = None
        self.console = None
        self.chat_controller = None

    def display_message(self, message: str, style: str) -> None:
        """ Display message in chat view """
        output = Padding(message, (0,2))
        self.console.print(output, style=style)

    def clear_screen(self) -> None:
        """ Clear screen """
        os.system('cls' if os.name == 'nt' else 'clear')

    def display_help(self) -> None:
        """ Display help table with list of commands and aliases """
        help_table = Table(box=box.SQUARE)
        help_table.add_column("Command", max_width=20)
        help_table.add_column("Description")
        help_table.add_row("h", "Display this help section")
        help_table.add_row("r", "Restart application")
        help_table.add_row("c", "List saved conversations")
        help_table.add_row("c \[conversation]", "Open conversation \[conversation]")
        help_table.add_row("cc", "Create a new conversation")
        help_table.add_row("cs", "Save the current conversation")
        help_table.add_row("ct \[conversation]", "Trash conversation \[conversation]")
        help_table.add_row("cy", "Copy current conversation to clipboard")
        help_table.add_row("m", "List available modes")
        help_table.add_row("m \[mode]", "Switch to mode \[mode]")
        help_table.add_row("p", "List available personae")
        help_table.add_row("p \[persona]", "Switch to persona \[persona]")
        help_table.add_row("l", "List available languages")
        help_table.add_row("l \[language]", "Set language to \[language]")
        help_table.add_row("vi", "Switch to voice input")
        help_table.add_row("vo", "Switch on voice output")
        help_table.add_row("y", "Copy last answer to clipboard")
        help_table.add_row("t \[temp]", "Set the temperature to \[temp]")
        help_table.add_row("tp \[top_p]", "Set the top_p to \[top_p]")
        help_table.add_row("mt \[max_tokens]", "Set the max_tokens to \[max_tokens]")
        help_table.add_row("c", "Clear the screen")
        help_table.add_row("q", "Quit")
        self.console.print(help_table)

    def display_response(self, response: str) -> None:
        """ Display response in chat view or speak it """

        # Display the response
        self.display_message(response, "answer")

        # Speak the response
        self.chat_controller.speak(response)

        # New line
        self.console.print()

#}}}

#{{{ ChatController
class ChatController:

    def __init__(self, chat_model, chat_view):

        self.chat_model = chat_model
        self.chat_view = chat_view

        self.chat_view.config = self.chat_model.config

        self.chat_view.chat_controller = self

        self.input_mode = "text"

        self.console = Console(
            theme = Theme(self.chat_model.config["theme"]),
            record = True,
            color_system = "truecolor",
        )
        self.chat_view.console = self.console

    #{{{ Startup
    def start(self):
        """ Start the chat """

        # Clear the screen
        self.chat_view.clear_screen()

        # Create a new conversation
        self.chat_model.new_conversation()

        # Display the user input prompt
        while True:
            user_input = self.chat_view.console.input("> ")
            self.parse_command(user_input)
    #}}}

    #{{{ Parse command
    def parse_command(self, command: str) -> None:
        """ Parse the user input and execute the command """

        #{{{ System

        #{{{ Exit
        if command == "q":
            self.exit_app()
        #}}}

        #{{{ Restart
        elif command == "r":
            self.chat_view.display_message("Restarting...", "success")
            time.sleep(1)
            python = sys.executable
            os.execl(python, python, * sys.argv)
        #}}}

        #{{{ Help
        elif command == "h":
            self.chat_view.display_help()
        #}}}

        #{{{ Clear screen
        elif command == "cls":
            self.chat_view.clear_screen()
        #}}}

        #{{{ Copy answer to clipboard
        elif command == "y":
            self.chat_model.copy_to_clipboard(self.chat_model.response)
            self.chat_view.display_message("Copied last answer to clipboard.", "success")
        #}}}

        #{{{ Set temperature
        elif command.startswith("t "):
            temp = command[2:]
            set_temp = self.chat_model.set_temperature(temp)
            if isinstance(set_temp, Exception):
                self.chat_view.display_message("Error setting temperature: {}".format(set_temp), "error")
            else:
                self.chat_view.display_message("temperature set to {}.".format(temp), "success")
        #}}}

        #{{{ Set top_p
        elif command.startswith("tp "):
            top= command[2:]
            set_top = self.chat_model.set_top(top)
            if isinstance(set_top, Exception):
                self.chat_view.display_message("Error setting top_p: {}".format(set_top), "error")
            else:
                self.chat_view.display_message("top_p set to {}.".format(top), "success")
        #}}}

        #{{{ Set max tokens
        elif command.startswith("mt "):
            max_tokens = command[2:]
            set_max_tokens = self.chat_model.set_max_tokens(max_tokens)
            if isinstance(set_max_tokens, Exception):
                self.chat_view.display_message("Error setting max tokens: {}".format(set_max_tokens), "error")
            else:
                self.chat_view.display_message("max_tokens set to {}.".format(max_tokens), "success")
        #}}}

        #}}}

        #{{{ Conversations

        #{{{ List conversations
        elif command == "c":
            conversations_list = self.chat_model.list_conversations()
            if isinstance(conversations_list, Exception):
                self.chat_view.display_message("Error listing conversation: {}".format(conversations_list), "error")
            else:
                # if there is at least one conversation
                if len(conversations_list) > 0:
                    self.chat_view.display_message("Conversations", "section")
                    for conversation in conversations_list:
                        self.chat_view.display_message(conversation, "info")
        #}}}

        #{{{ Create conversation
        elif command == "cc":
            self.chat_model.new_conversation()
            self.chat_model.set_persona("")
            self.chat_view.mode = "normal"
            self.chat_view.display_message("New conversation.", "success")
            time.sleep(1)
            self.chat_view.clear_screen()
        #}}}

        #{{{ Save conversation
        elif command.startswith("cs "):
            filename = command.split(" ")[-1]
            save = self.chat_model.save_conversation(filename)
            if isinstance(save, Exception):
                self.chat_view.display_message("Error saving conversation: {}".format(save), "error")
            else:
                self.chat_view.display_message("Conversation saved.", "success")
        #}}}

        #{{{ Open conversation
        elif command.startswith("c "):
            filename = command.split(" ")[-1]
            if filename == "":
                self.chat_view.display_message("Please specify a filename.", "error")
            open_conversation = self.chat_model.open_conversation(filename)
            if isinstance(open_conversation, Exception):
                self.chat_view.display_message("Error opening conversation: {}".format(open_conversation), "error")
            else:
                self.chat_view.display_message("Conversation opened.", "success")
                sleep(1)
                self.chat_view.clear_screen()
                self.chat_view.display_message(self.chat_model.conversation, "answer")
        #}}}

        #{{{ Trash conversation
        elif command.startswith("ct "):
            filename = command.split(" ")[-1]
            trash_conversation = self.chat_model.trash_conversation(filename)
            if isinstance(trash_conversation, Exception):
                self.chat_view.display_message("Error trashing conversation: {}".format(trash_conversation), "error")
            else:
                self.chat_view.display_message("Conversation trashed.", "success")
        #}}}

        #{{{ Copy conversation to clipboard
        elif command == "cy":
            self.chat_model.copy_to_clipboard(self.chat_model.conversation)
            self.chat_view.display_message("Copied conversation to clipboard.", "success")
        #}}}

        #}}}

        #{{{ Modes

        #{{{ List modes
        elif command == "m":
            modes = self.chat_model.list_modes()
            self.chat_view.display_message("Modes", "section")
            current_mode = self.chat_model.get_mode()
            for mode in modes:
                if mode == current_mode:
                    self.chat_view.display_message(mode+" <", "info")
                else:
                    self.chat_view.display_message(mode, "info")
        #}}}

        #{{{ Set mode
        elif command.startswith("m "):
            mode = command.split(" ")[1]
            try:
                set_mode = self.chat_model.set_mode(mode)
                self.chat_view.display_message("Mode set to {}.".format(mode), "success")
            except Exception as e:
                self.chat_view.display_message("Error setting mode: {}".format(e), "error")
        #}}}

        #}}}

        #{{{ Personae

        #{{{ List Personae
        elif command == "p":
            personae = self.chat_model.list_personae()
            self.chat_view.display_message("Personae", "section")
            current_persona = self.chat_model.get_persona()

            for persona in personae["persona"]:
                if persona["name"] == current_persona:
                    self.chat_view.display_message(persona["name"]+" <", "info")
                else:
                    self.chat_view.display_message(persona["name"], "info")
        #}}}

        #{{{ Set persona
        elif command.startswith("p "):
            persona = command.split(" ")[1]
            set_persona = self.chat_model.set_persona(persona)
            if isinstance(set_persona, Exception):
                self.chat_view.display_message("Error setting persona: {}".format(set_persona), "error")
            else:
                self.chat_view.display_message("Persona set to {}.".format(persona), "success")
                self.chat_model.new_conversation()
                sleep(1)
                self.chat_view.clear_screen()
        #}}}

        #}}}

        #{{{ Languages / Voice

        #{{{ Voice input
        elif command == "vi":

            # Toggle input mode
            if self.input_mode == "text":
                self.input_mode = "voice"
                self.chat_view.display_message("Voice input mode enabled.", "success")
                log.log("Voice input mode enabled.")

                # while in voice input mode
                while self.input_mode == "voice":

                    # Start spinner
                    with self.chat_view.console.status(""):

                        # Listen for voice input
                        self.voice_input = self.chat_model.listen()

                    # Stop spinner
                    self.chat_view.console.status("").stop()

                    if isinstance(self.voice_input, Exception):
                        self.chat_view.display_message("Error with voice input: {}".format(self.voice_input), "error")
                    else:

                        # Display voice input
                        self.chat_view.display_message(self.voice_input, "prompt")

                        # if voice input is "Exit."
                        if self.voice_input == "Exit.":
                            self.input_mode = "text"
                            self.chat_model.set_voice_output(False)
                            self.chat_view.display_message("Voice input mode disabled.", "success")
                        else:

                            log.log("Processing voice input...")

                            # Start spinner
                            with self.chat_view.console.status(""):

                                # Generate final prompt
                                final_message = self.chat_model.generate_final_message(self.voice_input)

                                # Generate response
                                response = self.chat_model.generate_response(final_message)

                            # Stop spinner
                            self.chat_view.console.status("").stop()

                            # Display response
                            self.chat_view.display_response(response)

            else:
                self.input_mode = "text"
                self.chat_view.display_message("Voice input mode disabled.", "success")
        #}}}

        #{{{ Voice output
        elif command == "vo":
            self.chat_model.set_voice_output(not self.chat_model.get_voice_output())
            if self.chat_model.get_voice_output():
                self.chat_view.display_message("Voice output enabled.", "success")
            else:
                self.chat_view.display_message("Voice output disabled.", "success")
        #}}}

        #{{{ List languages / voices
        elif command == "l":
            voices = self.chat_model.get_voices()
            self.chat_view.display_message("Languages", "section")
            current_voice = self.chat_model.get_voice()
            for voice in voices:
                if self.chat_model.config["voices"][voice] == current_voice:
                    self.chat_view.display_message(voice+" <", "info")
                else:
                    self.chat_view.display_message(voice, "info")
        #}}}

        #{{{ Set language / voice
        elif command.startswith("l "):
            voice = command.split(" ")[1]
            set_voice = self.chat_model.set_voice(voice)
            if isinstance(set_voice, Exception):
                self.chat_view.display_message("Error setting language: {}".format(set_voice), "error")
            else:
                self.chat_view.display_message("Language set to {}.".format(voice), "success")
        #}}}

        #}}}

        # Normal prompt
        else:

            # Start spinner
            with self.chat_view.console.status(""):

                # Generate final prompt
                try:
                    final_message = self.chat_model.generate_final_message(command)
                    # DEBUG: print final message
                    # print(final_message)

                    # Generate response
                    try:
                        response = self.chat_model.generate_response(final_message)

                        # Display response
                        self.chat_view.display_response(response)

                    # Error generating response
                    except Exception as e:
                        self.chat_view.display_message("Error generating response: {}".format(e), "error")

                # Error generating final prompt
                except Exception as e:
                    self.chat_view.display_message("Error generating final message: {}".format(e), "error")
    #}}}

    #{{{ def speak(self, text):
    def speak(self, text):
        """Speak the text."""
        self.chat_model.speak(text)
    #}}}

    # Exit
    def exit_app(self):
        """ Exit the app. """
        self.chat_view.display_message("Exiting neuma, goodbye!", "success")
        sleep(1)
        self.chat_view.console.clear()
        exit()

#}}}

#{{{ Main
def main():

    # Model
    chat_model = ChatModel()

    # View
    chat_view = ChatView()

    # Controller
    chat_controller = ChatController(chat_model, chat_view)

    # Start the controller
    chat_controller.start()

if __name__ == "__main__":
    main()
#}}}
