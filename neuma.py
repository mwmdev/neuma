import os # For IO
from io import BytesIO
import base64
import sys  # For IO
import shutil  # For IO
import subprocess  # For IO
import openai
from openai import OpenAI  # The good stuff
from openai import audio as openai_audio  # For audio
# import time  # For logging
from datetime import datetime
from time import sleep  # Zzz
import toml  # For parsing settings
import logging  # For logging
from rich.logging import RichHandler  # For logging

import json  # For parsing JSON
import pyperclip  # For copying to clipboard
import re  # For regex
import requests  # For accessing the web
from bs4 import BeautifulSoup  # For parsing HTML
# import readline
import argparse  # For parsing command line arguments

# Audio
import threading
import speech_recognition
import pyaudio
import sounddevice

# Document loaders
from langchain_community.document_loaders import DirectoryLoader
# from langchain.document_loaders import DirectoryLoader

# Text splitter
from langchain.text_splitter import RecursiveCharacterTextSplitter

# Schema
from langchain.schema import Document

# Embeddings
from langchain_openai.embeddings import OpenAIEmbeddings

# Vector stores
from langchain.vectorstores.chroma import Chroma

# Image
from PIL import Image
from slugify import slugify

# Chat models
from langchain_openai import ChatOpenAI

# LLM
from langchain_community.callbacks import get_openai_callback

# Formatting
from rich.console import Console
from rich.theme import Theme
from rich import print
from rich.padding import Padding
from rich.table import Table
from rich import box
from rich.syntax import Syntax


class ChatModel:
    """Chat model class"""

    def __init__(self):
        self.config = self.get_config()
        self.logging = self.config["debug"]["logging"]
        self.logger = self.set_logger(self.logging)
        self.client = OpenAI()
        self.mode = self.set_mode("normal")  # Default mode
        self.persona = self.set_persona("default")
        self.voice_output = False  # Default voice output
        self.vector_db = ""  # Default

    def set_logger(self, logging_status: bool ) -> logging.Logger | None:
        """Set up logging"""

        logging.basicConfig(
            level="NOTSET",
            format="%(message)s",
            datefmt="[%X]",
            handlers=[RichHandler(rich_tracebacks=True)],
        )
        log = logging.getLogger("rich")
        if logging_status is not True:
            logging.disable(sys.maxsize)
        return log

    def get_config(self) -> dict:
        """Get config from config.toml and API keys from .env"""

        # Check in the user's home config directory first
        if os.path.isfile(os.path.expanduser("~/.config/neuma/config.toml")):
            config_path = os.path.expanduser("~/.config/neuma/config.toml")

        # Check in the current directory
        elif os.path.isfile(os.path.dirname(os.path.realpath(__file__)) + "/config.toml"):
            self.logger.info("Config file found in current directory")
            config_path = os.path.dirname(os.path.realpath(__file__)) + "/config.toml"

        # Get config file from GitHub
        else:
            self.logger.info("No config file found. Getting one from GitHub.")
            try:
                response = requests.get("https://raw.githubusercontent.com/mwmdev/neuma/main/config.toml")
                expanded_user_home = os.path.expanduser("~")
                user_config = response.text.replace("~", expanded_user_home)
                os.makedirs(os.path.expanduser("~/.config/neuma/"), exist_ok=True)

                with open(os.path.expanduser("~/.config/neuma/config.toml"), "w") as f:
                    f.write(user_config)

                config_path = os.path.expanduser("~/.config/neuma/config.toml")
                self.logger.info("Config saved in {}".format(config_path))

            except Exception as e:
                raise ValueError("No config file found : {}".format(e))

        # Load config
        try:
            with open(config_path, "r") as f:
                self.logger.info("Loading config from {}".format(config_path))
                config = toml.load(f)
        except Exception as e:
            raise ValueError("No config file found.")

        # Get API keys
        if os.path.isfile(os.path.expanduser("~/.config/neuma/.env")):
            self.logger.info("API keys found in user's home directory")
            env_path = os.path.expanduser("~/.config/neuma/.env")
        else:
            self.logger.info("API keys found in current directory")
            env_path = os.path.dirname(os.path.realpath(__file__)) + "/.env"

        # check if env_path exists
        if not os.path.exists(env_path):
            self.logger.error(f"Error: {env_path} not found.")
            print(f"Error: {env_path} not found.")
            print("Make sure the file exists and OPENAI_API_KEY is set in the file.")
            exit(1)

        try:
            with open(env_path, "r") as f:
                env = toml.load(f)
                # OpenAI
                openai_api_key = env["OPENAI_API_KEY"]
                if openai_api_key != "":
                    self.logger.info("OPENAI_API_KEY found in .env")
                    config["openai"]["api_key"] = openai_api_key
                    os.environ["OPENAI_API_KEY"] = openai_api_key
                else:
                    self.logger.error(f"Error: OPENAI_API_KEY not set in {env_path}")
                    print(f"Error: OPENAI_API_KEY not set in {env_path}")
                    exit(1)

        except Exception as e:
            print("Error: {}".format(e))
            exit(1)

        # Create data folder if it doesn't exist
        data_folder = config["conversations"]["data_folder"]
        if not os.path.exists(data_folder):
            os.makedirs(data_folder)

        # Create persist folder if it doesn't exist
        persist_folder = config["vector_db"]["persist_folder"]
        if not os.path.exists(persist_folder):
            os.makedirs(persist_folder)

        # Create images folder if it doesn't exist
        image_path = config["images"]["path"]
        if not os.path.exists(image_path):
            os.makedirs(image_path)

        return config

    def generate_final_message(self, user_prompt: str) -> list:
        """Generate final prompt (messages) for OpenAI API"""

        # Add a dot at the end of the prompt if there isn't one
        if user_prompt[-1] not in ["?", "!", "."]:
            user_prompt += "."
        self.user_prompt = user_prompt

        # Conversation up to this point
        conversation = self.conversation

        # Persona identity
        if not conversation:
            self.logger.info("Persona : {}".format(self.persona))
            if not isinstance(self.persona, str):
                self.logger.info("Persona is not a string")
                self.persona = "default"

            persona_identity = self.get_persona_identity()
            for message in persona_identity:
                conversation.append(message)

        # Mode instructions
        self.logger.info("Mode : {}".format(self.mode))
        mode_instructions = self.config["modes"][self.mode]
        if mode_instructions:
            # Replace # with all the text after # in the user_prompt
            hashtag = self.find_hashtag(self.user_prompt)
            self.logger.info("hashtag: {}".format(hashtag))
            if hashtag:
                mode_instructions = mode_instructions.replace("#", hashtag)
            mode_instructions_message = {"role": "system", "content": mode_instructions}
            conversation.append(mode_instructions_message)
            self.logger.info("Mode instructions : {}".format(mode_instructions_message))

        # File content to insert
        if "~{f:" in user_prompt and "}~" in user_prompt:
            file_path = user_prompt.split("~{f:")[1].split("}~")[0]
            self.logger.info("file_path: {}".format(file_path))
            if os.path.isfile(file_path):
                with open(file_path, "r") as f:
                    file_content = f.read()
                    user_prompt = user_prompt.replace(
                        "~{f:" + file_path + "}~", file_content
                    )
                    self.logger.info("user_prompt: {}".format(user_prompt))
            else:
                self.logger.info("File not found")

        # URL content to insert
        if "~{w:" in user_prompt and "}~" in user_prompt:
            url = user_prompt.split("~{w:")[1].split("}~")[0]
            self.logger.info("url: {}".format(url))
            try:
                response = requests.get(url)
                if response.status_code == 200:
                    self.logger.info("response: {}".format(response))
                    soup = BeautifulSoup(response.text, "html.parser")
                    url_content = soup.get_text()
                    # remove all newlines and extra spaces
                    url_content = re.sub(r"\s+", " ", url_content)
                    if len(url_content) > 3000:
                        url_content = url_content[:3000]
                    user_prompt = user_prompt.replace("~{w:" + url + "}~", url_content)
                    self.logger.info("user_prompt: {}".format(user_prompt))
                else:
                    self.logger.info("Error getting URL content")
            except Exception as e:
                self.logger.info("Error getting URL content: {}".format(e))

        # User input
        user_prompt = {"role": "user", "content": user_prompt}
        conversation.append(user_prompt)
        self.logger.info("User prompt : {}".format(user_prompt))
        self.logger.info("Final messages: {}".format(conversation))

        return conversation

    def generate_response(self, messages: list) -> str | Exception:
        """Generate response from OpenAI API"""

        prompt = json.dumps(messages)

        api_key = self.config["openai"]["api_key"]
        self.logger.info("api_key: {}".format(api_key))

        # Image mode
        if self.mode == "img":
            image_path = self.config["images"]["path"]

            if not os.path.exists(image_path):
                os.makedirs(image_path)

            image_prompt = messages[-1]["content"]

            try:
                image_raw_data = self.generate_image(image_prompt)
                image_obj = Image.open(BytesIO(base64.b64decode(image_raw_data)))
                timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
                image_file = slugify(image_prompt) + "-" + timestamp + ".png"
                image_fullpath = image_path + image_file
                image_obj.save(image_fullpath)
                if self.config["images"]["open"]:
                    open_command = self.config["images"]["open_command"]
                    os.system(open_command + " " + image_fullpath)
                response_data = {"message": "Image generated and saved to : {}".format(image_fullpath)}
            except Exception as e:
                self.logger.error("Error generating image: {}".format(e))

        else:

            model = self.config["openai"]["model"]
            self.logger.info("model: {}".format(model))

            temperature = self.get_persona_temperature(self.persona)
            self.logger.info("temperature: {}".format(temperature))

            top_p = self.config["openai"]["top_p"]
            self.logger.info("top_p: {}".format(top_p))

            max_tokens = self.config["openai"]["max_tokens"]
            self.logger.info("max_tokens: {}".format(max_tokens))

            # Vector DB query
            if self.vector_db != "":
                self.logger.info("type of query: vector db")

                try:
                    with get_openai_callback() as callback:

                        vector_db_name = self.vector_db
                        self.logger.info("vector_db_name: {}".format(vector_db_name))

                        persist_folder = self.config["vector_db"]["persist_folder"]
                        self.logger.info("persist_folder: {}".format(persist_folder))

                        full_path = os.path.join(persist_folder, vector_db_name)
                        self.logger.info("full_path: {}".format(full_path))

                        # Embeddings
                        embeddings = OpenAIEmbeddings(
                            openai_api_key=os.environ["OPENAI_API_KEY"],
                            model=self.config["embeddings"]["model"],
                        )

                        # Vector store
                        full_path = os.path.join(persist_folder, vector_db_name)
                        vector_db = Chroma(
                            persist_directory=full_path,
                            embedding_function=embeddings
                        )

                        # Search the DB.
                        self.logger.info("prompt: {}".format(prompt))
                        results = vector_db.similarity_search_with_relevance_scores(
                            prompt,
                            k=4,
                            # score_threshold=0.8
                        )
                        self.logger.info("results: {}".format(results))

                        context_text = "\n\n---\n\n".join([doc.page_content for doc, _score in results])
                        prompt = prompt.replace("{context}", context_text)

                        model = ChatOpenAI()
                        response = model.invoke(prompt)

                        sources = [doc.metadata.get("source", None) for doc, _score in results]
                        sources_text = "\n"
                        sources = list(set(sources))
                        for i, source in enumerate(sources):
                            source = source.split("/")[-1]
                            sources_text += "\n:left_arrow_curving_right: " + source + "\n"
                        sources_text = sources_text.strip()

                        formatted_response = f"{response.content}\n{sources_text}"

                        response_data = {
                            "id": "",
                            "created": "",
                            "status": "success",
                            "message": formatted_response,
                            "promptTokens": callback.prompt_tokens,
                            "completionTokens": callback.completion_tokens,
                            "totalTokens": callback.total_tokens,
                        }
                        self.logger.info("response_data: {}".format(response_data))
                        self.logger.info("Total tokens: {}".format(callback.total_tokens))

                except Exception as e:
                    self.logger.exception(e)

            # Normal query
            else:
                self.logger.info("type of query: default")

                llm = ChatOpenAI(
                    openai_api_key=os.environ["OPENAI_API_KEY"],
                    model_name=model,
                    temperature=temperature,
                    max_tokens=max_tokens,
                    # top_p=top_p,
                )
                try:
                    with get_openai_callback() as callback:
                        chat_completions = self.client.chat.completions.create(
                            model=model,
                            messages=messages,
                            temperature=temperature,
                            # top_p=top_p
                        )
                        response = chat_completions.choices[0].message.content
                        response_data = {
                            "id": "",
                            "created": "",
                            "status": "success",
                            "message": response,
                            "promptTokens": callback.prompt_tokens,
                            "completionTokens": callback.completion_tokens,
                            "totalTokens": callback.total_tokens,
                            # 'sourceDocuments': response['source_documents'][0],
                        }
                        self.logger.info("response_data: {}".format(response_data))
                        self.logger.info("Total tokens: {}".format(callback.total_tokens))

                        # Add to conversation (only in normal chat)
                        response_message = {"role": "assistant", "content": response_data["message"]}
                        self.conversation.append(response_message)


                except Exception as e:
                    self.logger.exception(e)

        self.processed_response = self.process_response(response_data["message"])

        return self.processed_response

    def process_response(self, response: str) -> str | Table | Syntax:
        """Process response, formats the response"""

        # Remove double line breaks
        response = response.replace("\n\n", "\n")

        # Keep only what is between ``` and ```
        if "```" in response:
            response = response.split("```")[1]
            response = response.split("```")[0]

        # Table mode
        if self.mode == "table":
            # Remove everything before the first |
            if "|" in response:
                response = response.split("|", 1)[1]
                response = "|" + response

            self.logger.info("response: {}".format(response))

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

        # Code mode
        elif self.mode == "code":
            language = self.find_hashtag(self.user_prompt)
            syntax = Syntax(
                response,
                language,
                line_numbers=False,
                theme="gruvbox-dark",
                word_wrap=True,
            )
            return syntax

        # CSV mode
        elif self.mode == "csv":
            separator = self.find_hashtag(self.user_prompt)
            response = response.replace(",", separator)

        return response

    # Personae

    def list_personae(self) -> str | dict | Exception:
        """List the available personae from the personae file"""

        personae = {}

        # Check in the user's home config directory first
        if os.path.isfile(os.path.expanduser("~/.config/neuma/personae.toml")):
            personae_path = os.path.expanduser("~/.config/neuma/personae.toml")

        # Check in the current directory
        elif os.path.isfile(os.path.dirname(os.path.realpath(__file__)) + "/personae.toml"):
            personae_path = (
                    os.path.dirname(os.path.realpath(__file__)) + "/personae.toml"
            )

        # Get personae file from github
        else:
            try:
                response = requests.get("https://raw.githubusercontent.com/mwmdev/neuma/main/personae.toml")
                os.makedirs(os.path.expanduser("~/.config/neuma/"), exist_ok=True)

                with open(os.path.expanduser("~/.config/neuma/personae.toml"), "w") as f:
                    f.write(response.text)
                personae_path = os.path.expanduser("~/.config/neuma/personae.toml")

            except Exception as e:
                raise ValueError("No personae file found : {}".format(e))

        # Load personae
        try:
            with open(personae_path, "r") as f:
                personae = toml.load(f)
                self.logger.info("Personae available : {}".format(len(personae["persona"])))
        except Exception as e:
            raise ValueError("No personae file found : {}".format(e))

        return personae

    # Set persona
    def set_persona(self, persona: str) -> str | Exception:
        self.logger.info("Setting persona to : {}".format(persona))
        personae = self.list_personae()
        for existing_persona in personae["persona"]:
            if existing_persona["name"] == persona:
                self.persona = persona
                temperature = self.get_persona_temperature(persona)
                self.set_temperature(temperature)
                return persona
        raise ValueError("No persona with that name found.")

    # Get persona
    def get_persona(self) -> str:
        return self.persona

    # Get persona prompt
    def get_persona_identity(self) -> str | list:
        if self.persona != "":
            personae = self.list_personae()
            for persona in personae["persona"]:
                if persona["name"] == self.persona:
                    persona_identity = persona["messages"]
                    self.logger.info("Persona identity : {}".format(persona_identity))
        else:
            persona_identity = ""
        return persona_identity

    # Get persona temperature
    def get_persona_temperature(self, persona: str) -> float:
        if persona != "":
            personae = self.list_personae()
            for persona in personae["persona"]:
                if persona["name"] == self.persona:
                    temperature = persona["temp"]
        return temperature

    # Conversation

    # Create new conversation
    def new_conversation(self) -> list:
        self.conversation = []

    # Save conversation, write it to a file
    def save_conversation(self, filename: str) -> bool:
        data_folder = self.config["conversations"]["data_folder"]
        if not os.path.exists(data_folder):
            os.makedirs(data_folder)
        try:
            with open(data_folder + filename + ".neu", "w") as f:
                output = ""
                for message in self.conversation:
                    output += message["content"] + "\n\n"
                f.write(output)
        except Exception as e:
            self.logger.exception(e)
        return True

    # List conversations
    def list_conversations(self) -> list:
        data_folder = self.config["conversations"]["data_folder"]
        try:
            files = [f for f in os.listdir(data_folder) if f.endswith(".neu")]
        except Exception as e:
            self.logger.exception(e)
        return files

    # Open conversation
    def open_conversation(self, filename: str) -> str:
        data_folder = self.config["conversations"]["data_folder"]
        # Get list of files
        try:
            with open(data_folder + filename + ".neu", "r") as f:
                self.conversation = f.read()

        except Exception as e:
            self.logger.exception(e)
        return True

    # Trash conversation
    def trash_conversation(self, filename: str) -> bool:
        data_folder = self.config["conversations"]["data_folder"]
        # Get list of files
        try:
            os.remove(data_folder + filename + ".neu")
        except Exception as e:
            self.logger.exception(e)
        return True

    # Modes

    # Get mode
    def get_mode(self) -> str:
        return self.mode

    # Set mode
    def set_mode(self, mode: str) -> str | Exception:
        modes = self.list_modes()
        if mode in modes:
            self.mode = mode
        else:
            raise ValueError("No mode with that name found.")
        return mode

    # List modes
    def list_modes(self) -> list:
        return self.config["modes"].keys()

    # Find hashtag in prompt
    def find_hashtag(self, prompt: str) -> str | bool:
        words = prompt.split(" ")
        for word in words:
            if word.startswith("#"):
                self.logger.info("Hashtag found : {}".format(word))
                return word[1:]
        return False

    # Models

    # List models
    def list_models(self) -> list:
        models = self.client.models.list()
        models = sorted(models, key=lambda x: x.created, reverse=True)
        models_list = [model.id for model in models]
        models_list = [model for model in models_list if "gpt" in model]
        self.logger.info("models_list: {}".format(models_list))
        return models_list

    # Get GPT model
    def get_model(self) -> str:
        return self.config["openai"]["model"]

    # Set GPT model
    def set_model(self, model: str) -> bool:
        self.config["openai"]["model"] = model
        return True

    # Audio

    # Voice input
    def listen(self) -> str | Exception:
        self.config = self.get_config()
        self.input_device = self.config["audio"]["input_device"]
        self.input_timeout = self.config["audio"]["input_timeout"]
        self.logger.info("input_timeout: {}".format(self.input_timeout))
        self.input_limit = self.config["audio"]["input_limit"]
        self.logger.info("input_limit: {}".format(self.input_limit))

        self.logger.info("Listening...")

        # https://github.com/Uberi/speech_recognition
        recognizer = speech_recognition.Recognizer()

        self.logger.info("input_device: {}".format(self.input_device))
        with speech_recognition.Microphone(device_index=self.input_device) as source:
            recognizer.adjust_for_ambient_noise(source)
            try:
                audio = recognizer.listen(
                    source,
                    timeout=self.input_timeout,
                    phrase_time_limit=self.input_limit,
                )

                with open("tmp.wav", "wb") as f:
                    f.write(audio.get_wav_data())
                audio_file = open("tmp.wav", "rb")

                # Transcribe audio to text https://platform.openai.com/docs/guides/speech-to-text
                transcription = self.transcribe(audio_file)
                self.logger.info("transcription: {}".format(transcription))

                return transcription

            except speech_recognition.WaitTimeoutError as e:
                return e

    # Transcribe
    def transcribe(self, audio_file: str) -> str:

        try:
            transcript = self.client.audio.transcriptions.create(
                model = "whisper-1",
                file = audio_file,
            )
            transcript = transcript.text
            return transcript

        except Exception as e:
            self.logger.exception(e)

    # Voice output
    def get_voice_output(self) -> str:
        return self.voice_output

    def set_voice_output(self, voice_output: str) -> None:
        self.voice_output = voice_output

    def speak(self, response: str) -> None:
        if self.voice_output == True:
            audio_file = "./tmp.wav"
            with openai_audio.speech.with_streaming_response.create(
                    model=self.config["audio"]["model"],
                    voice=self.config["audio"]["voice"],
                    input=response,
            ) as response:
                response.stream_to_file(audio_file)
                subprocess.run(["mpv", "--really-quiet", audio_file])
                os.remove(audio_file)

    # Documents

    # Load documents
    def load_documents(self, directory: str) -> list:
        loader = DirectoryLoader(directory)
        documents = loader.load()
        return documents

    # Split text
    def split_text(self, documents: list[Document]) -> list:
        text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=300,
            chunk_overlap=100,
            length_function=len,
            add_start_index=True,
        )
        chunks = text_splitter.split_documents(documents)
        return chunks

    # Save to vector db
    def save_chunks_to_db(self, chunks: list[Document]) -> None:
        persist_folder = self.config["vector_db"]["persist_folder"]
        vector_db_name = self.vector_db
        full_path = os.path.join(persist_folder, vector_db_name)
        self.logger.info("full_path: {}".format(full_path))
        db = Chroma.from_documents(
            chunks,
            OpenAIEmbeddings(),
            persist_directory=full_path,
        )

    # Embed
    def embed_doc(self, documents: list) -> OpenAIEmbeddings | None | Exception:
        embeddings_model = self.config["embeddings"]["model"]
        self.logger.info("Embeddings model: {}".format(embeddings_model))
        try:
            embeddings = OpenAIEmbeddings(model=embeddings_model)
            embeddings.embed_documents([text.page_content for text in documents])
            return embeddings

        except Exception as e:
            self.logger.exception(e)

    # Get vector dbs
    def get_vector_dbs(self) -> list:
        persist_folder = self.config["vector_db"]["persist_folder"]
        if not os.path.exists(persist_folder):
            os.mkdir(persist_folder)
        return os.listdir(persist_folder)

    # Get vector db
    def get_vector_db(self) -> str:
        return self.vector_db

    # Get information about the vector db (NEW)
    def get_vector_db_info(self) -> dict:
        # get the folder size in KiB
        persist_folder = self.config["vector_db"]["persist_folder"]
        full_path = os.path.join(persist_folder, self.vector_db)
        total_size = 0
        for dirpath, dirnames, filenames in os.walk(full_path):
            for f in filenames:
                fp = os.path.join(dirpath, f)
                total_size += os.path.getsize(fp)
        total_size = total_size / 1024

        # get metadata
        # vector_db = Chroma(
        #     persist_directory=full_path,
        # )
        # vector_db_details = vector_db._collection.metadata()

        return {"name": self.vector_db, "size": total_size}

    # Set vector db
    def set_vector_db(self, vector_db: str) -> None:
        self.vector_db = vector_db
        if not os.path.exists(self.config["vector_db"]["persist_folder"]):
            os.mkdir(self.config["vector_db"]["persist_folder"])
        full_path = self.config["vector_db"]["persist_folder"] + "/" + vector_db
        if not os.path.exists(full_path):
            os.mkdir(full_path)

    # Trash vector db
    def trash_vector_db(self, vector_db: str) -> bool | Exception:
        persist_folder = self.config["vector_db"]["persist_folder"]
        try:
            shutil.rmtree(persist_folder + "/" + vector_db)
        except Exception as e:
            self.logger.exception(e)
            return e

        return True

    # Image generation
    def generate_image(self, prompt: str) -> str | Exception:
        try:
            response = self.client.images.generate(
                model=self.config["images"]["model"],
                prompt=prompt,
                size=self.config["images"]["size"],
                quality=self.config["images"]["quality"],
                n=1,
                response_format="b64_json"
            )
            image_raw_data = response.data[0].b64_json
            return image_raw_data
        except Exception as e:
            self.logger.exception(e)
            return e

    # Other settings

    # Copy to clipboard
    def copy_to_clipboard(self, selection) -> None:
        output = ""
        if isinstance(selection, list):
            for message in selection:
                output += message["content"] + "\n\n"
        else:
            output = selection
        pyperclip.copy(output)

    # Set temperature
    def set_temperature(self, temperature: float) -> bool:
        if float(temperature) < 0 or float(temperature) > 2:
            return Exception("Temperature must be between 0 and 2")
        else:
            self.config["openai"]["temperature"] = float(temperature)
            return True

    # Set top_p
    def set_top(self, top: float) -> bool:
        self.config["openai"]["top_p"] = float(top)
        return True

    # Set max_tokens
    def set_max_tokens(self, max_tokens: int) -> bool:
        self.config["openai"]["max_tokens"] = int(max_tokens)
        return True


# ChatView
class ChatView:
    """Chat view class"""

    def __init__(self):
        self.chat_controller = None
        self.config = None
        self.console = None
        self.chat_controller = None

    def display_message(self, message: str, style: str) -> None:
        """Display message"""
        output = Padding(message, (0, 2))
        self.console.print(output, style=style)

    def clear_screen(self) -> None:
        """Clear screen"""
        os.system("cls" if os.name == "nt" else "clear")

    def display_help(self) -> None:
        """Display help table with list of commands and aliases"""
        help_table = Table(box=box.SQUARE)
        help_table.add_column("Command", max_width=20)
        help_table.add_column("Description")
        help_table.add_row("h", "Display this help section")
        help_table.add_row("r", "Restart")
        help_table.add_row("c", "List saved conversations")
        help_table.add_row("c \\[conversation]", "Open conversation \\[conversation]")
        help_table.add_row("cc", "Create a new conversation")
        help_table.add_row(
            "cs [conversation]", "Save the current conversation as \\[conversation]"
        )
        help_table.add_row("ct \\[conversation]", "Trash conversation \\[conversation]")
        help_table.add_row("cy", "Copy current conversation to clipboard")
        help_table.add_row("m", "List available modes")
        help_table.add_row("m \\[mode]", "Switch to mode \\[mode]")
        help_table.add_row("p", "List available personae")
        help_table.add_row("p \\[persona]", "Switch to persona \\[persona]")
        help_table.add_row("vi", "Switch to voice input")
        help_table.add_row("vo", "Switch on voice output")
        help_table.add_row("e \\[document]", "Embed \\[path/to/files]")
        help_table.add_row("d", "List available vector dbs")
        help_table.add_row("d \\[db]", "Create or switch to vector db \\[db]")
        help_table.add_row("dt \\[db]", "Trash vector db \\[db]")
        help_table.add_row("y", "Copy last answer to clipboard")
        help_table.add_row("t", "Get the current temperature value")
        help_table.add_row("t \\[temp]", "Set the temperature to \\[temp]")
        help_table.add_row("tp", "Get the current top_p value")
        help_table.add_row("mt", "Get the current max_tokens value")
        help_table.add_row("mt \\[max_tokens]", "Set the max_tokens to \\[max_tokens]")
        help_table.add_row("g", "List available GPT models")
        help_table.add_row("g \\[model]", "Set GPT model to [model]")
        help_table.add_row("lm", "List available microphones")
        help_table.add_row("cls", "Clear the screen")
        help_table.add_row("q", "Quit")
        self.console.print(help_table)

    def display_response(self, response: str) -> None:
        """Display response in chat view or speak it"""

        # Display the response
        self.display_message(response, "answer")

        # Speak the response
        self.chat_controller.speak(response)

        # New line
        self.console.print()


# ChatController
class ChatController:
    """Chat controller class"""

    def __init__(self, chat_model, chat_view):
        self.chat_model = chat_model
        self.chat_view = chat_view
        self.logger = logging.getLogger("rich")
        self.chat_view.config = self.chat_model.config
        self.chat_view.chat_controller = self
        self.input_mode = "text"
        self.console = Console(
            theme=Theme(self.chat_model.config["theme"]),
            record=True,
            color_system="truecolor",
        )
        self.chat_view.console = self.console

    # Startup
    def start(self):
        """Start the chat"""

        # Clear the screen
        self.chat_view.clear_screen()

        # Parse command line arguments
        if len(sys.argv) > 1:
            self.parse_command_line_arguments(sys.argv[1:])

        # Create a new conversation
        self.chat_model.new_conversation()

        # Parse command
        while True:
            user_input = self.chat_view.console.input("> ")
            self.parse_command(user_input)

    # Parse command line arguments
    def parse_command_line_arguments(self, arguments: list) -> None:
        """Parse command line arguments"""

        # get config
        self.config = self.chat_model.config

        # Create an ArgumentParser object
        parser = argparse.ArgumentParser(
            description="neuma is a minimalistic ChatGPT interface for the command line."
        )

        # Define arguments
        parser.add_argument("-i", "--input", help="Input prompt")
        parser.add_argument("-p", "--persona", help="Set persona")
        parser.add_argument("-m", "--mode", help="Set mode")
        parser.add_argument("-d", "--db", help="Set vector db")
        parser.add_argument("-t", "--temp", help="Set temperature")

        # Parse the command line arguments
        args = parser.parse_args()

        # Set persona
        if args.persona:
            self.chat_model.set_persona(args.persona)

        # Set mode
        if args.mode:
            self.chat_model.set_mode(args.mode)

        # Set vector db
        if args.db:
            self.chat_model.set_vector_db(args.db)

        # Set temperature
        if args.temp:
            self.chat_model.set_temperature(args.temp)

        # Prompt input
        if args.input:
            self.chat_model.new_conversation()
            final_message = self.chat_model.generate_final_message(args.input)
            response = self.chat_model.generate_response(final_message)
            print(response)
            sys.exit()

    # Parse command
    def parse_command(self, command: str) -> None:
        """Parse the user input and execute the command"""

        # System

        # Exit
        if command == "q":
            self.exit_app()

        # Restart
        elif command == "r":
            self.chat_view.display_message("Restarting...", "success")
            sleep(1)
            try:
                os.execl(sys.executable, [sys.executable] )
            except Exception as e:
                self.chat_view.display_message("Error: {}".format(e), "error")
                sys.exit()

        # Help
        elif command == "h":
            self.chat_view.display_help()

        # Clear screen
        elif command == "cls":
            self.chat_view.clear_screen()

        # Copy answer to clipboard
        elif command == "y":
            # log conversation
            if len(self.chat_model.conversation) > 0:
                last_message = self.chat_model.conversation[-1].get("content")
                self.logger.info("Last message: {}".format(last_message))
                self.chat_model.copy_to_clipboard(last_message)
                self.chat_view.display_message(
                    "Copied last answer to clipboard.", "success"
                )
            else:
                self.chat_view.display_message("Nothing to copy to clipboard.", "error")

        # Get temperature
        elif command == "t":
            self.chat_view.display_message(
                "Temperature: {}".format(
                    self.chat_model.config["openai"]["temperature"]
                ),
                "info",
            )

        # Set temperature
        elif command.startswith("t "):
            temp = command[2:]
            set_temp = self.chat_model.set_temperature(temp)
            if isinstance(set_temp, Exception):
                self.chat_view.display_message(
                    "Error setting temperature: {}".format(set_temp), "error"
                )
            else:
                self.chat_view.display_message(
                    "temperature set to {}.".format(temp), "success"
                )

        # Get top_p
        elif command == "tp":
            self.chat_view.display_message(
                "top_p: {}".format(self.chat_model.config["openai"]["top_p"]), "info"
            )

        # Set top_p
        elif command.startswith("tp "):
            top = command[2:]
            set_top = self.chat_model.set_top(top)
            if isinstance(set_top, Exception):
                self.chat_view.display_message(
                    "Error setting top_p: {}".format(set_top), "error"
                )
            else:
                self.chat_view.display_message(
                    "top_p set to {}.".format(top), "success"
                )

        # Get max tokens
        elif command == "mt":
            self.chat_view.display_message(
                "max_tokens: {}".format(self.chat_model.config["openai"]["max_tokens"]),
                "info",
            )

        # Set max tokens
        elif command.startswith("mt "):
            max_tokens = command[2:]
            set_max_tokens = self.chat_model.set_max_tokens(max_tokens)
            if isinstance(set_max_tokens, Exception):
                self.chat_view.display_message(
                    "Error setting max tokens: {}".format(set_max_tokens), "error"
                )
            else:
                self.chat_view.display_message(
                    "max_tokens set to {}.".format(max_tokens), "success"
                )

        # List GPT models
        elif command == "g":
            models = self.chat_model.list_models()
            self.chat_view.display_message("GPT Models", "section")
            current_model = self.chat_model.get_model()
            for model in models:
                if model == current_model:
                    self.chat_view.display_message(model + " <", "info")
                else:
                    self.chat_view.display_message(model, "info")

        # Set GPT model
        elif command.startswith("g "):
            model = command.split(" ")[1]
            self.chat_model.set_model(model)
            self.chat_view.display_message("Model set to {}.".format(model), "success")

        # Conversations

        # List conversations
        elif command == "c":
            conversations_list = self.chat_model.list_conversations()
            if isinstance(conversations_list, Exception):
                self.chat_view.display_message(
                    "Error listing conversation: {}".format(conversations_list), "error"
                )
            else:
                # if there is at least one conversation
                if len(conversations_list) > 0:
                    self.chat_view.display_message("Conversations", "section")
                    for conversation in conversations_list:
                        self.chat_view.display_message(conversation, "info")

        # Create conversation
        elif command == "cc":
            self.chat_model.new_conversation()
            self.chat_view.mode = "normal"
            self.chat_view.display_message("New conversation.", "success")
            sleep(1)
            self.chat_view.clear_screen()

        # Save conversation
        elif command.startswith("cs "):
            filename = command.split(" ")[-1]
            save = self.chat_model.save_conversation(filename)
            if isinstance(save, Exception):
                self.chat_view.display_message(
                    "Error saving conversation: {}".format(save), "error"
                )
            else:
                self.chat_view.display_message("Conversation saved.", "success")

        # Open conversation
        elif command.startswith("c "):
            filename = command.split(" ")[-1]
            if filename == "":
                self.chat_view.display_message("Please specify a filename.", "error")
            open_conversation = self.chat_model.open_conversation(filename)
            if isinstance(open_conversation, Exception):
                self.chat_view.display_message(
                    "Error opening conversation: {}".format(open_conversation), "error"
                )
            else:
                self.chat_view.display_message("Conversation opened.", "success")
                sleep(1)
                self.chat_view.clear_screen()
                self.chat_view.display_message(self.chat_model.conversation, "answer")

        # Trash conversation
        elif command.startswith("ct "):
            filename = command.split(" ")[-1]
            trash_conversation = self.chat_model.trash_conversation(filename)
            if isinstance(trash_conversation, Exception):
                self.chat_view.display_message(
                    "Error trashing conversation: {}".format(trash_conversation),
                    "error",
                )
            else:
                self.chat_view.display_message("Conversation trashed.", "success")

        # Copy conversation to clipboard
        elif command == "cy":
            self.chat_model.copy_to_clipboard(self.chat_model.conversation)
            self.chat_view.display_message(
                "Copied conversation to clipboard.", "success"
            )

        # Modes

        # List modes
        elif command == "m":
            modes = self.chat_model.list_modes()
            self.chat_view.display_message("Modes", "section")
            current_mode = self.chat_model.get_mode()
            for mode in modes:
                if mode == current_mode:
                    self.chat_view.display_message(mode + " <", "info")
                else:
                    self.chat_view.display_message(mode, "info")

        # Set mode
        elif command.startswith("m "):
            mode = command.split(" ")[1]
            try:
                set_mode = self.chat_model.set_mode(mode)
                self.chat_view.display_message(
                    "Mode set to {}.".format(mode), "success"
                )
            except Exception as e:
                self.chat_view.display_message(
                    "Error setting mode: {}".format(e), "error"
                )

        # Personae

        # List Personae
        elif command == "p":
            personae = self.chat_model.list_personae()
            self.chat_view.display_message("Personae", "section")
            current_persona = self.chat_model.get_persona()

            for persona in personae["persona"]:
                if persona["name"] == current_persona:
                    self.chat_view.display_message(persona["name"] + " <", "info")
                else:
                    self.chat_view.display_message(persona["name"], "info")

        # Set persona
        elif command.startswith("p "):
            persona = command.split(" ")[1]
            try:
                set_persona = self.chat_model.set_persona(persona)
                self.chat_view.display_message(
                    "Persona set to {}.".format(persona), "success"
                )
                self.chat_model.new_conversation()
                sleep(1)
                self.chat_view.clear_screen()
            except Exception as e:
                self.chat_view.display_message(
                    "Error setting persona: {}".format(e), "error"
                )

        # Languages / Voice

        # Voice input
        elif command == "vi":
            # Toggle input mode
            if self.input_mode == "text":
                self.input_mode = "voice"
                self.chat_view.display_message("Voice input mode enabled. ", "success")
                self.chat_view.display_message("(Say [bold]Disable voice input[/bold] to disable.)", "info")
                self.logger.info("Voice input mode enabled. Disable by saying 'Disable voice input'.")

                # while in voice input mode
                while self.input_mode == "voice":
                    # Start spinner
                    with self.chat_view.console.status(""):
                        # Listen for voice input
                        self.voice_input = self.chat_model.listen()

                    # Stop spinner
                    self.chat_view.console.status("").stop()

                    if isinstance(self.voice_input, Exception):
                        self.chat_view.display_message(
                            "Error with voice input: {}".format(self.voice_input),
                            "error",
                        )
                    else:
                        # Display voice input
                        self.chat_view.display_message(self.voice_input, "prompt")
                        # if self.voice_input == "Disable voice input.":
                        if (
                                "disable" in self.voice_input.lower() and "voice" in self.voice_input.lower() and "input" in self.voice_input.lower()
                        ):
                            self.input_mode = "text"
                            self.chat_model.set_voice_output(False)
                            self.chat_view.display_message(
                                "Voice input mode disabled.", "success"
                            )
                        else:
                            self.logger.info("Processing voice input...")

                            # Start spinner
                            with self.chat_view.console.status(""):
                                # Generate final prompt
                                final_message = self.chat_model.generate_final_message(
                                    self.voice_input
                                )

                                # Generate response
                                response = self.chat_model.generate_response(
                                    final_message
                                )

                            # Stop spinner
                            self.chat_view.console.status("").stop()

                            # Display response
                            self.chat_view.display_response(response)

            else:
                self.input_mode = "text"
                self.chat_view.display_message("Voice input mode disabled.", "success")

        # Voice output
        elif command == "vo":
            self.chat_model.set_voice_output(not self.chat_model.get_voice_output())
            if self.chat_model.get_voice_output():
                self.chat_view.display_message("Voice output enabled.", "success")
            else:
                self.chat_view.display_message("Voice output disabled.", "success")

        # List microphones
        elif command.startswith("lm"):
            self.chat_view.display_message("Available input devices", "section")
            if len(speech_recognition.Microphone.list_microphone_names()) == 0:
                self.chat_view.display_message("No input devices found.", "info")
            else:
                current_microphone = self.chat_model.config["audio"]["input_device"]
                for index, name in enumerate(
                        speech_recognition.Microphone.list_microphone_names()
                ):
                    if index == current_microphone:
                        self.chat_view.display_message(
                            '{0} : {1} <'.format(index, name), "info"
                        )
                    else:
                        self.chat_view.display_message(
                            '{0} : {1}'.format(index, name), "info"
                        )

        # Documents

        # List vector dbs
        elif command == "d":
            vector_dbs = self.chat_model.get_vector_dbs()
            self.chat_view.display_message("Vector stores", "section")
            if len(vector_dbs) == 0:
                self.chat_view.display_message("No vector stores found.", "info")
            else:
                current_vector_db = self.chat_model.get_vector_db()
                for vector_db in vector_dbs:
                    if vector_db == current_vector_db:
                        self.chat_view.display_message(vector_db + " <", "info")
                    else:
                        self.chat_view.display_message(vector_db, "info")

        # Create or use vector db
        elif command.startswith("d "):
            vector_db = command.split(" ")[1]
            self.chat_model.set_vector_db(vector_db)
            self.chat_view.display_message(
                "Vector store set to {}.".format(vector_db), "success"
            )

        # Get info about vector db
        elif command == "di":
            vector_db_info = self.chat_model.get_vector_db_info()
            self.chat_view.display_message("Vector db info: {}".format(vector_db_info), "success")


        # Trash vector db
        elif command.startswith("dt "):
            vector_db = command.split(" ")[1]
            trash_vector_db = self.chat_model.trash_vector_db(vector_db)
            if isinstance(trash_vector_db, Exception):
                self.chat_view.display_message(
                    "Error trashing vector db: {}".format(trash_vector_db),
                    "error",
                )
            else:
                self.chat_view.display_message("Vector db trashed.", "success")

        # Embed document
        elif command.startswith("e "):
            path = command.split(" ")[1]

            with self.chat_view.console.status(""):

                # If there is no vector db set, return an error
                if self.chat_model.get_vector_db() == "":
                    self.chat_view.display_message(
                        "Please create or use a vector store first.", "error"
                    )
                    return

                # If there is no path specified, return an error
                if path == "":
                    self.chat_view.display_message("Please specify a path.", "error")
                    return

                # If path points to a folder that doesn't exist, return an error
                if not os.path.exists(path):
                    self.chat_view.display_message(
                        "Path not found: {}".format(path), "error"
                    )
                    return

                # Load document
                try:
                    documents = self.chat_model.load_documents(path)
                    num_docs = len(documents)

                    self.chat_view.display_message(
                        "Loaded {} documents from: {}. ".format(num_docs, path),
                        "success"
                    )
                    # list all documents
                    for doc in documents:
                        filename = doc.metadata["source"].replace(path, "").replace("/", "")
                        self.chat_view.display_message(
                            filename,
                            "info"
                        )

                    self.logger.info("Loaded documents in: {}".format(path))
                except Exception as e:
                    self.chat_view.display_message(
                        "Error loading documents: {}".format(e), "error"
                    )

                # Split text
                try:
                    chunks = self.chat_model.split_text(documents)
                    self.chat_view.display_message(
                        "Documents split into {} chunks.".format(len(chunks)), "success"
                    )
                    self.logger.info(
                        "Documents split into {} chunks.".format(len(chunks))
                    )
                except Exception as e:
                    self.chat_view.display_message(
                        "Error splitting text: {}".format(e), "error"
                    )

                # Embed document
                try:
                    embeddings = self.chat_model.save_chunks_to_db(chunks)
                    self.chat_view.display_message(
                        "Documents chunks saved to db.", "success"
                    )
                    self.logger.info("Document chunks saved to db")
                except Exception as e:
                    self.chat_view.display_message(
                        "Error saving chunks to db: {}".format(e), "error"
                    )

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
                        self.chat_view.display_message(
                            "Error generating response: {}".format(e), "error"
                        )

                # Error generating final prompt
                except Exception as e:
                    self.chat_view.display_message(
                        "Error generating final message: {}".format(e), "error"
                    )

    # Speak
    def speak(self, text):
        """Speak the text."""
        self.chat_model.speak(text)

    # Exit
    def exit_app(self):
        """Exit the app."""
        self.chat_view.display_message("Exiting neuma, goodbye!", "success")
        sleep(1)
        self.chat_view.console.clear()
        sys.exit()


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
