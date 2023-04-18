import os # For IO
import sys # For IO
import subprocess # For IO
import openai # The good stuff
import time # For logging
from time import sleep # Zzz
import toml # For parsing settings
import pyperclip # For copying to clipboard
import re # For regex

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

log = Logger('/home/mike/scripts/neuma/neuma.log')
#}}}

#{{{ ChatModel
class ChatModel:

    def __init__(self):
        self.config = self.get_config()
        self.mode = "normal" # Default mode
        self.persona = "" # Default persona
        self.voice_output = False # Default voice output
        # self.voice = self.config["voices"]["english"] # Default voice
        self.voice = ""

    #{{{ Get config
    def get_config(self) -> dict:
        """ Get config from config.toml and API key from env """
        if os.path.isfile(os.path.expanduser("~/.config/neuma/config.toml")):
            config_path = os.path.expanduser("~/.config/neuma/config.toml")
        else:
            config_path = os.path.dirname(os.path.realpath(__file__)) + "/config.toml"
        try:
            with open(config_path, "r") as f:
                config = toml.load(f)
                api_key = os.getenv("OPENAI_API_KEY")
                if api_key:
                    config["openai"]["api_key"] = api_key
                    log.log("Config loaded")
                    return config
                else:
                    raise ValueError("No API key found in environment variables.")
        except Exception as e:
            return e
    #}}}

    #{{{ Generate final prompt
    def generate_final_message(self, user_prompt: str) -> list:
        """ Generate final prompt (messages) for OpenAI API """

        # Add a dot at the end of the prompt if there isn't one
        if user_prompt[-1] not in ["?", "!", "."]:
            user_prompt += "."
        self.user_prompt = user_prompt

        # Conversation up to this point
        conversation = self.get_conversation()
        log.log("conversation: {}".format(conversation))

        # if this is the first message, add the mode instructions and persona
        if conversation == None:
            log.log("new conversation")
            messages = []

            # Mode instructions
            log.log("Mode : {}".format(self.mode))
            mode_instructions = self.config["modes"][self.mode]
            if mode_instructions:
                # in mode_instructions, replace # with all the text after # in the user_prompt
                mode_instructions = mode_instructions.replace("#", user_prompt[user_prompt.find("#")+1:])
                mode_instructions_message = {"role": "system", "content": mode_instructions}
                self.add_to_conversation(mode_instructions_message)
                messages.append(mode_instructions_message)
                log.log("Mode instructions : {}".format(mode_instructions_message))

            # Persona identity
            if self.persona:
                log.log("Persona : {}".format(self.persona))
                persona_identity = self.get_persona_identity()
                persona_identity_message = {"role": "system", "content": persona_identity}
                self.add_to_conversation(persona_identity_message)
                messages.append(persona_identity_message)
                log.log("Persona identity : {}".format(persona_identity_message))
        else:
            messages = conversation

        # User input
        user_prompt = {"role": "user", "content": user_prompt}
        messages.append(user_prompt)
        self.add_to_conversation(user_prompt)
        log.log("User prompt : {}".format(user_prompt))
        log.log("Final messages: {}".format(messages))

        return messages

    #}}}

    #{{{ Generate response from OpenAI API
    def generate_response(self, messages: list) -> str:
        """ Generate response from OpenAI API """

        api_key = os.getenv("OPENAI_API_KEY")
        model = self.config["openai"]["model"]
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
                n = 1,
                stream = False,
                stop = None,
                max_tokens = max_tokens,
                presence_penalty = 0.5,
                frequency_penalty = 0.5,
            )

            # Get the first completion
            self.response = chat_completions.choices[0].message.content

            # Add to conversation
            response_message = {"role": "assistant", "content": self.response}
            log.log("Response : {}".format(response_message))
            self.add_to_conversation(response_message)

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

        #}}}

        #{{{ Table mode formatting
        #TODO : Kill response if it starts with "As an AI model..."
        if self.mode == "table":
            lines = response.split("\n")
            lines = list(filter(None, lines))

            # remove lines that contain '---'
            lines = [line for line in lines if "---" not in line]

            # Create table
            table = Table(show_lines=True)

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
            syntax = Syntax(response, language, line_numbers=True, theme="gruvbox-dark", word_wrap=True)
            return syntax
        #}}}

        return response

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
        else:
            persona_identity = ""
        return persona_identity

    # Get persona language code
    def get_persona_language_code(self) -> str:
        if self.persona != "":
            personae = self.list_personae()
            for persona in personae["persona"]:
                if persona["name"] == self.persona:
                    language_code = persona["language_code"]
        else:
            language_code = ""
        return language_code

    # Get persona voice name
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

    # Add message to conversation
    def add_to_conversation(self, message: list) -> None:
        self.conversation.append(message)

    # Get conversation
    def get_conversation(self) -> list:
        if self.conversation:
            return self.conversation
        else:
            new_conversation = self.new_conversation()
            return new_conversation

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

        # https://github.com/Uberi/speech_recognition
        recognizer = speech_recognition.Recognizer()

        with speech_recognition.Microphone() as source:
            recognizer.adjust_for_ambient_noise(source)
            # audio = recognizer.listen(source, phrase_time_limit=5)
            audio = recognizer.listen(source)

            with open("tmp.wav", "wb") as f:
                f.write(audio.get_wav_data())
            audio_file = open("tmp.wav", "rb")

            # Transcribe audio to text https://platform.openai.com/docs/guides/speech-to-text
            transcription = self.transcribe(audio_file)

            return transcription

    #}}}

    #{{{ Transcribe
    def transcribe(self, audio_file: str) -> str:
        try:
            transcription = openai.Audio.transcribe("whisper-1", audio_file, "en-US")
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
    def copy_to_clipboard(self, conversation: list) -> None:
        output = ""
        for message in conversation:
            output += message['content'] + "\n\n"
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

#}}}

#{{{ ChatView
class ChatView:

    def __init__(self):
        self.chat_controller = None
        self.config = None
        self.console = None
        self.chat_controller = None

    # def set_controller(self, chat_controller: object) -> None:
    #     self.chat_controller = chat_controller

    def display_message(self, message: str, style: str) -> None:
        """ Display message in chat view """
        output = Padding(message, (0,2))
        self.console.print(output, style=style)

    def clear_screen(self) -> None:
        """ Clear screen """
        os.system('cls' if os.name == 'nt' else 'clear')

    def display_help(self) -> None:
        """ Display help table with list of commands and aliases """
        help_table = Table()
        help_table.add_column("Command")
        help_table.add_column("Alias")
        help_table.add_column("Description")
        help_table.add_row("help","h", "Display this help section")
        help_table.add_row("restart","r", "Restart application")
        help_table.add_row("conversations","c", "List saved conversations")
        help_table.add_row("conversation open \[conversation]","c \[conversation]", "Open conversation \[conversation]")
        help_table.add_row("conversation create","cc", "Create a new conversation")
        help_table.add_row("conversation save","cs", "Save the current conversation")
        help_table.add_row("conversation trash \[conversation]","ct \[conversation]", "Trash conversation \[conversation]")
        help_table.add_row("conversation yank","cy", "Copy current conversation to clipboard")
        help_table.add_row("modes","m", "List available modes")
        help_table.add_row("mode \[mode]" ,"m \[mode]", "Switch to mode \[mode]")
        help_table.add_row("personae","p", "List available personae")
        help_table.add_row("persona \[persona]","p \[persona]", "Switch to persona \[persona]")
        help_table.add_row("languages","l", "List available languages")
        help_table.add_row("language \[language]","l \[language]", "Set language to \[language]")
        help_table.add_row("voice input","vi", "Switch to voice input")
        help_table.add_row("voice ouput","vo", "Switch on voice output")
        help_table.add_row("yank","y", "Copy last answer to clipboard")
        help_table.add_row("temp \[temp]","t \[temp]", "Set the temperature to \[temp]")
        help_table.add_row("top \[top_p]","tp \[top_p]", "Set the top_p to \[top_p]")
        help_table.add_row("clear","c", "Clear the screen")
        help_table.add_row("quit","q", "Quit")
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
            theme=Theme(self.chat_model.config["theme"]),
            record=True,
            color_system="truecolor",
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

            if self.input_mode == "voice":
                with self.chat_view.console.status(""):

                    self.voice_input = self.chat_model.listen()
                    self.console.print("> "+self.voice_input)
                    final_message = self.chat_model.generate_final_message(self.voice_input)
                    response = self.chat_model.generate_response(final_message)

                self.chat_view.console.status("").stop()
                self.chat_view.display_response(response)

            if self.input_mode == "text":
                user_input = self.chat_view.console.input("> ")
                self.parse_command(user_input)
    #}}}

    #{{{ Parse command
    def parse_command(self, command: str) -> None:
        """ Parse the user input and execute the command """

        #{{{ System

        #{{{ Exit
        if command == "quit" or command == "q":
            self.exit_app()
        #}}}

        #{{{ Restart
        elif command == "restart" or command == "r":
            self.chat_view.display_message("Restarting Neuma...", "success")
            time.sleep(1)
            python = sys.executable
            os.execl(python, python, * sys.argv)
        #}}}

        #{{{ Help
        elif command == "help" or command == "h":
            self.chat_view.display_help()
        #}}}

        #{{{ Clear screen
        elif command == "clear" or command == "cls":
            self.chat_view.clear_screen()
        #}}}

        #{{{ Copy answer to clipboard
        elif command == "yank" or command == "ya":
            self.chat_model.copy_to_clipboard(self.chat_model.response)
            self.chat_view.display_message("Copied to clipboard.", "success")
        #}}}

        #{{{ Set temperature
        elif command.startswith("temp ") or command.startswith("t "):
            temp = command[2:]
            set_temp = self.chat_model.set_temperature(temp)
            if isinstance(set_temp, Exception):
                self.chat_view.display_message("Error setting temperature: {}".format(set_temp), "error")
            else:
                self.chat_view.display_message("temperature set to {}.".format(temp), "success")
        #}}}

        #{{{ Set top_p
        elif command.startswith("top ") or command.startswith("tp "):
            top= command[2:]
            set_top = self.chat_model.set_top(top)
            if isinstance(set_top, Exception):
                self.chat_view.display_message("Error setting top_p: {}".format(set_top), "error")
            else:
                self.chat_view.display_message("top_p set to {}.".format(top), "success")
        #}}}

        #}}}

        #{{{ Conversations

        #{{{ List conversations
        elif command == "conversations" or command == "c":
            conversations_list = self.chat_model.list_conversations()
            if isinstance(conversations_list, Exception):
                self.chat_view.display_message("Error listing conversation: {}".format(conversations_list), "error")
            else:
                self.chat_view.display_message("Conversations", "section")
                for conversation in conversations_list:
                    self.chat_view.display_message(conversation, "info")
        #}}}

        #{{{ Create conversation
        elif command == "conversation create" or command == "cc":
            self.chat_model.new_conversation()
            self.chat_model.set_persona("")
            self.chat_view.mode = "normal"
            self.chat_view.display_message("New conversation.", "success")
        #}}}

        #{{{ Save conversation
        elif command.startswith("conversation save ") or command.startswith("cs "):
            filename = command.split(" ")[1]
            save = self.chat_model.save_conversation(filename)
            if isinstance(save, Exception):
                self.chat_view.display_message("Error saving conversation: {}".format(save), "error")
            else:
                self.chat_view.display_message("Conversation saved.", "success")
        #}}}

        #{{{ Open conversation
        elif command.startswith("conversation ") or command.startswith("c "):
            filename = command.split(" ")[1]
            if filename == "":
                self.chat_view.display_message("Please specify a filename.", "error")
            open_conversation = self.chat_model.open_conversation(filename)
            if isinstance(open_conversation, Exception):
                self.chat_view.display_message("Error opening conversation: {}".format(open_conversation), "error")
            else:
                self.chat_view.display_message("Conversation opened.", "success")
                sleep(1)
                self.chat_view.clear_screen()
                self.chat_view.display_message(self.chat_model.get_conversation(), "answer")
        #}}}

        #{{{ Trash conversation
        elif command.startswith("conversation trash ") or command.startswith("ct "):
            filename = command.split(" ")[1]
            trash_conversation = self.chat_model.trash_conversation(filename)
            if isinstance(trash_conversation, Exception):
                self.chat_view.display_message("Error trashing conversation: {}".format(trash_conversation), "error")
            else:
                self.chat_view.display_message("Conversation trashed.", "success")
        #}}}

        #{{{ Copy conversation to clipboard
        elif command == "conversation yank" or command == "cy":
            self.chat_model.copy_to_clipboard(self.chat_model.get_conversation())
            self.chat_view.display_message("Copied conversation to clipboard.", "success")
        #}}}

        #}}}

        #{{{ Modes

        #{{{ List modes
        elif command == "modes" or command == "m":
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
        elif command.startswith("mode ") or command.startswith("m "):
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
        elif command == "personae" or command == "p":
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
        elif command.startswith("persona ") or command.startswith("p "):
            persona = command.split(" ")[1]
            set_persona = self.chat_model.set_persona(persona)
            if isinstance(set_persona, Exception):
                self.chat_view.display_message("Error setting persona: {}".format(set_persona), "error")
            else:
                self.chat_view.display_message("Persona set to {}.".format(persona), "success")
        #}}}

        #}}}

        #{{{ Languages / Voice

        #{{{ Voice input
        elif command == "voice input" or command == "vi":

            # Toggle input mode
            if self.input_mode == "text":
                self.input_mode = "voice"
                self.chat_view.display_message("Voice input mode enabled.", "success")

                # Start spinner
                with self.chat_view.console.status(""):

                    # Listen for voice input
                    self.voice_input = self.chat_model.listen()
                    log.log("Listening for voice input...")

                # Stop spinner
                self.chat_view.console.status("").stop()

                if isinstance(self.voice_input, Exception):
                    self.chat_view.display_message("Error with voice input: {}".format(self.voice_input), "error")
                else:

                    # Display voice input
                    self.chat_view.display_message(self.voice_input, "prompt")

                    log.log("Voice input: {}".format(self.voice_input))

                    # if voice input is "Exit."
                    if self.voice_input == "Exit.":
                        self.input_mode = "text"
                        self.chat_view.display_message("Voice input mode disabled.", "success")
                    else:

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
        elif command == "voice output" or command == "vo":
            self.chat_model.set_voice_output(not self.chat_model.get_voice_output())
            if self.chat_model.get_voice_output():
                self.chat_view.display_message("Voice output enabled.", "success")
            else:
                self.chat_view.display_message("Voice output disabled.", "success")
        #}}}

        #{{{ List languages / voices
        elif command == "languages" or command == "l":
            voices = self.chat_model.get_voices()
            self.chat_view.display_message("Languages", "section")
            current_voice = self.chat_model.get_voice()
            for voice in voices:
                if self.chat_model.config["voices"][voice] == current_voice:
                    self.chat_view.display_message(voice, "info")
                else:
                    self.chat_view.display_message(voice, "answer")
        #}}}

        #{{{ Set language / voice
        elif command.startswith("language ") or command.startswith("l "):
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
            # Stop spinner
            # self.chat_view.console.status("").stop()

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
