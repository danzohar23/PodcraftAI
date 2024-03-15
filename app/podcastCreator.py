import logging
import re
import google.generativeai as genai
from audiocraft.models import MusicGen
from audiocraft.data.audio import audio_write
from pydub import AudioSegment
import os
import openai
from pathlib import Path
from openai import OpenAI
import warnings
import requests
from dotenv import dotenv_values

warnings.filterwarnings(
    "ignore", category=UserWarning, module="torch.nn.utils.weight_norm"
)

config = dotenv_values(".env")
openai_api_key = config["OPENAI_API_KEY"]
google_api_key = config["GOOGLE_API_KEY"]


openai.api_key = openai_api_key
client = OpenAI(api_key=openai_api_key)


genai.configure(api_key=google_api_key)

model = genai.GenerativeModel("gemini-pro")
musicModel = MusicGen.get_pretrained("facebook/musicgen-small")
musicModel.set_generation_params(duration=7)


logging.basicConfig(
    filename="logging.log",
    filemode="w",
    level=logging.INFO,
    format="%(asctime)s:%(levelname)s:%(message)s",
)

topic = ""


def getScriptfromGemini(topic):
    dialogue = ""
    if topic == None:
        user_input = input(
            "Give me an idea for a podcast and I will generate it for you: "
        )
        topic = user_input

    descriptions = ["soothing and rhythmic music inspired by " + topic]

    for idx, description in enumerate(descriptions):
        wav = musicModel.generate([description])
        audio_write(
            f"introMusic", wav[0].cpu(), musicModel.sample_rate, strategy="loudness"
        )

    chat = model.start_chat(history=[])
    response = chat.send_message(
        f"write a podcast dialogue inspired by the topic '{topic}'\n"
        + "The podcast's content should be updated to news from the past week."
        + " The podcast is called Podcast GPT"
        " and it is two people (Ofir and Daniel) talking about a topic that is defined as follows: "
        + topic
        + ". If the topic is too broad you can narrow it down to something more specific, but still make it "
        + "updated to recent news. Introuce the podcast with Ofir talking first, choose a topic for the first segment and write the conversation for it."
        + "Make sure to maintain podcast dynamics between the hosts during the conversation,"
        + "make them even tease each other a bit. Add some jokes and puns as well but don't literally say that you try to be funny or witty."
        + "use your common sense to decide if the topic is appropriate for laughing at. if not then don't add jokes and just keep it serious."
        + " Don't add any more people to the conversation (no guests)"
        + "The show should have 5 segments. There should be a newline in between the hosts' dialogue. Stop after each segment and I will tell you how to continue."
        + " please don't mention or announce that a segment was over. just move on and act as usual. After the last segment, have the hosts say an outro for the podcast.\n",
    )
    logging.info(response.text)
    dialogue = dialogue + response.text
    for i in range(4):
        i = i + 1
        response = chat.send_message(
            "write the next segment of the podcast.", stream=True
        )
        for chunk in response:
            logging.info(chunk.text)
            dialogue = dialogue + chunk.text

    logging.info(dialogue)
    extracted_dialogue = extract_dialogue(dialogue)
    logging.info(extracted_dialogue)


def extract_dialogue(script):
    lines = script.split("\n")

    host1_dialogue = []
    host2_dialogue = []
    current_host = None
    current_dialogue = ""

    for line in lines:
        line = re.sub(r"\*\*Segment \d+:.*?\*\*", "", line)

        if line.startswith("**Ofir:**") or line.startswith("Ofir:"):
            if current_host == "host2" and current_dialogue:
                host2_dialogue.append(current_dialogue.strip())
                current_dialogue = ""
            if line.startswith("**Ofir:**"):
                current_dialogue += " " + line.replace("**Ofir:** ", "").strip()
            elif line.startswith("Ofir:"):
                current_dialogue += " " + line.replace("Ofir:", "").strip()
            current_host = "host1"
        elif line.startswith("**Daniel:**") or line.startswith("Daniel:"):
            if current_host == "host1" and current_dialogue:
                host1_dialogue.append(current_dialogue.strip())
                current_dialogue = ""
            if line.startswith("**Daniel:**"):
                current_dialogue += " " + line.replace("**Daniel:** ", "").strip()
            elif line.startswith("Daniel:"):
                current_dialogue += " " + line.replace("Daniel:", "").strip()
            current_host = "host2"

    if current_host == "host1" and current_dialogue:
        host1_dialogue.append(current_dialogue.strip())
    elif current_host == "host2" and current_dialogue:
        host2_dialogue.append(current_dialogue.strip())

    with open("host1.txt", "w", encoding="utf-8") as file1:
        for dialogue in host1_dialogue:
            file1.write(dialogue + "\n")

    with open("host2.txt", "w", encoding="utf-8") as file2:
        for dialogue in host2_dialogue:
            file2.write(dialogue + "\n")


def merge_text_files(host1_file, host2_file, merged_file):
    with open(host1_file, "r", encoding="utf-8") as file1, open(
        host2_file, "r", encoding="utf-8"
    ) as file2, open(merged_file, "w", encoding="utf-8") as outfile:
        host1_lines = file1.readlines()
        host2_lines = file2.readlines()

        for line1, line2 in zip(host1_lines, host2_lines):
            outfile.write(line1)
            outfile.write(line2)


def generate_audio(file_path, output_filename):
    combined_audio = AudioSegment.empty()
    pause = AudioSegment.silent(duration=400)

    with open(file_path, "r", encoding="utf-8") as file:
        for index, line in enumerate(file):
            voice = "echo" if index % 2 == 0 else "fable"
            response = client.audio.speech.create(
                model="tts-1", voice=voice, input=line
            )

            temp_filename = f"temp_{index}.mp3"
            warnings.filterwarnings(
                "ignore",
                category=DeprecationWarning,
            )
            response.stream_to_file(Path(temp_filename))
            line_audio = AudioSegment.from_mp3(temp_filename)
            combined_audio += line_audio + pause
            os.remove(temp_filename)

    combined_audio.export(output_filename, format="mp3")


def add_intro_music(introAud, speechAud):
    intro_music = AudioSegment.from_file(introAud, format="wav")
    speech_audio = AudioSegment.from_file(speechAud, format="mp3")
    (intro_music.fade_in(1500).fade_out(1500) + speech_audio).export(
        "final_podcast_with_intro_music.mp3", format="mp3"
    )


def main():
    getScriptfromGemini(topic)
    merge_text_files("host1.txt", "host2.txt", "merged_dialogue.txt")
    generate_audio("merged_dialogue.txt", "final_podcast.mp3")
    add_intro_music("introMusic.wav", "final_podcast.mp3")


if __name__ == "__main__":
    main()