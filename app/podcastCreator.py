import datetime
import re
from bs4 import BeautifulSoup, NavigableString
import google.generativeai as genai
from audiocraft.models import MusicGen
from audiocraft.data.audio import audio_write
from pydub import AudioSegment
import os
import openai
from pathlib import Path
from openai import OpenAI
import warnings
from dotenv import dotenv_values
import numpy as np
import wikipedia
import requests
import logging

warnings.filterwarnings(
    "ignore", category=UserWarning, module="torch.nn.utils.weight_norm"
)

config = dotenv_values()
if config != {}:
    openai_api_key = config["OPENAI_API_KEY"]
    google_api_key = config["GOOGLE_API_KEY"]
else:
    openai_api_key = os.environ.get("OPENAI_API_KEY")
    google_api_key = os.environ.get("GOOGLE_API_KEY")


openai.api_key = openai_api_key
client = OpenAI(api_key=openai_api_key)


genai.configure(api_key=google_api_key)

model = genai.GenerativeModel("gemini-pro")
musicModel = MusicGen.get_pretrained("facebook/musicgen-small")
musicModel.set_generation_params(duration=7)


topic = ""


def get_embedding(text, model="text-embedding-ada-002"):
    text = text.replace("\n", " ")
    response = client.embeddings.create(input=text, model=model)
    try:
        embedding = response["data"][0]["embedding"]
    except TypeError:
        embedding = response.data[0].embedding
    return embedding


def cosine_similarity(v1, v2):
    return np.dot(v1, v2) / (np.linalg.norm(v1) * np.linalg.norm(v2))


def get_wikipedia_articles_summaries(query, limit=3):
    logging.basicConfig(
        filename="logging.log",
        filemode="w",
        level=logging.INFO,
        format="%(asctime)s:%(levelname)s:%(message)s",
    )
    warnings.filterwarnings("ignore", category=UserWarning, module="wikipedia")
    wikipedia.set_lang("en")
    results = wikipedia.search(query, results=limit)

    articles_summaries = {}
    for title in results:
        try:
            logging.info(f"Retrieving summary for {title}")
            articles_summaries[title] = wikipedia.summary(title, auto_suggest=False)
            logging.info(articles_summaries[title])
        except wikipedia.exceptions.DisambiguationError as e:
            logging.info("Disambiguation error, taking first option instead.")
            page = wikipedia.page(e.options[0])
            articles_summaries[e.options[0]] = page.summary
            logging.info(articles_summaries[e.options[0]])
        except Exception as e:
            logging.info(f"Error retrieving summary for {title}: {e}")

    return articles_summaries


def find_most_relevant_article(query, summaries):
    if summaries and list(summaries.keys())[0].lower() == query.lower():
        return list(summaries.keys())[0]
    query_embedding = get_embedding(query)

    max_similarity = -1
    most_relevant_title = None

    for title, summary in summaries.items():
        summary_embedding = get_embedding(summary)
        similarity = cosine_similarity(
            np.array(query_embedding), np.array(summary_embedding)
        )

        if similarity > max_similarity:
            max_similarity = similarity
            most_relevant_title = title

    logging.info(f"Most relevant article: {most_relevant_title}")
    return most_relevant_title


def scrape_nba_games_between_dates(url, start_date, end_date):
    response = requests.get(url)
    soup = BeautifulSoup(response.content, "html.parser")

    start_tag = soup.find(lambda tag: tag.name == "b" and start_date in tag.text)
    end_tag = soup.find(lambda tag: tag.name == "b" and end_date in tag.text)

    if not start_tag or not end_tag:
        return "Start or end tag not found."

    elements_between_dates = []
    for element in start_tag.next_elements:
        if element == end_tag:
            break
        if isinstance(element, NavigableString) and element.strip():
            elements_between_dates.append(element.strip())

    return "Recap of yesterday's games: " + " ".join(elements_between_dates)


def getNBAPodcastContent():
    yesterdays_date = (datetime.datetime.now() - datetime.timedelta(days=1)).strftime(
        "%A, %B %d, %Y"
    )
    two_days_ago_date = (datetime.datetime.now() - datetime.timedelta(days=2)).strftime(
        "%A, %B %d, %Y"
    )
    start_date = "NBA Daily For " + yesterdays_date
    end_date = "NBA Daily For " + two_days_ago_date
    url = "http://www.insidehoops.com/daily.shtml"
    nba_game_info = scrape_nba_games_between_dates(url, start_date, end_date)
    clean_nba_game_info = (
        nba_game_info.replace("<br/>", "")
        .replace("<u>", "")
        .replace("</u>", "")
        .replace("<br>", "")
        .replace("<b>", "")
        .replace("\n", " ")
        .strip()
    )
    return clean_nba_game_info


def getScriptfromGemini(topic):
    dialogue = ""
    nba_message = ""
    if topic == None or topic == "":
        topic = "podcast"
    descriptions = ["soothing and rhythmic music inspired by " + topic]

    for idx, description in enumerate(descriptions):
        wav = musicModel.generate([description])
        audio_write(
            f"introMusic", wav[0].cpu(), musicModel.sample_rate, strategy="loudness"
        )

    wikipedia_summaries = get_wikipedia_articles_summaries(topic)
    logging.info(f"Summaries from wikipedia retrieved")
    most_relevant_title = find_most_relevant_article(topic, wikipedia_summaries)
    podcast_content = wikipedia_summaries.get(most_relevant_title)

    if topic.lower() == "nba" or topic.lower() == "basketball":
        podcast_content = getNBAPodcastContent()
        nba_message = (
            "The following is a recap of yesterday's NBA games. Use this information:\n"
        )
    logging.info("Starting Script Generation")
    chat = model.start_chat(history=[])
    response = chat.send_message(
        f"{nba_message} Considering the following informantion: '{podcast_content}', write a podcast dialogue inspired by the topic '{topic}',"
        + "if no topic was inserted, make up a podcast about a topic of your desire.'\n"
        + "The podcast's content should be updated to news from the past week."
        + " The podcast is called Podcraft AI"
        " and it is two people (Ofir and Daniel) talking about a topic that is defined as follows: "
        + topic
        + ". If the topic is too broad you can narrow it down to something more specific, but still make it "
        + "updated to recent news. Introuce the podcast with Ofir talking first, choose a topic for the first segment and write the conversation for it."
        + "Make sure to maintain podcast dynamics between the hosts during the conversation,"
        + "make them have critical thinking but also be open to new ideas and opinions, make them creative al well."
        + "make them even tease each other a bit. Add some jokes and puns as well but don't literally say that you try to be funny or witty."
        + "use your common sense to decide if the topic is appropriate for laughing at. if not then don't add jokes and just keep it serious."
        + " Don't add any more people to the conversation (no guests)"
        + "The show should have 10 segments. There should be a newline in between the hosts' dialogue. Stop before ending each segment. Wait and I will tell you how to continue."
        + " Don't mention or announce that a segment is over, Just stop the dialogue."
    )
    for chunk in response:
        dialogue = dialogue + chunk.text

    for i in range(9):
        i = i + 1
        if i != 9:
            response = chat.send_message(
                "write the next segment of the podcast. Do not announce that the segment is starting or that it is a new topic. Just go straight into the discussion.",
                stream=True,
            )
            for chunk in response:
                dialogue = dialogue + chunk.text
        else:
            response = chat.send_message(
                "write the last segment of the podcast. After the segment, write an outro to the podcast.",
                stream=True,
            )
            for chunk in response:
                dialogue = dialogue + chunk.text

    extract_dialogue(dialogue)


def extract_dialogue(script):
    logging.basicConfig(
        filename="logging.log",
        level=logging.INFO,
        format="%(asctime)s:%(levelname)s:%(message)s",
    )
    lines = script.split("\n")

    host1_dialogue = []
    host2_dialogue = []
    current_host = None
    current_dialogue = ""

    for line in lines:
        logging.info(line)
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


def read_script(file_path):
    with open(file_path, "r", encoding="utf-8") as file:
        script_text = file.read()
    return script_text


def generate_revised_script(script_text):

    response = client.chat.completions.create(
        model="gpt-3.5-turbo",
        messages=[
            {
                "role": "system",
                "content": "You are a highly skilled editor. Please revise the following podcast script for improved structure, flow, coherence, facts checks and engagement. simply take the script given to you and make it better. if you see multiple outros in the text given to you, keep only the last one but make sure to still include the segments accompanying these outros. make sure to keep it only with the text itself. no comments, announcing new segments or headlines from you. Use every piece of information from the original text while keeping the entire new generated text coherant and logical. Make it sound like a real conversation between two people and maintain the same dynamics Ofir and Daniel are having, including the jokes and puns and even add new ones. The podcast should still be the same length as the script given to you.",
            },
            {"role": "user", "content": script_text},
        ],
        temperature=0.7,
        max_tokens=4096,
        top_p=1.0,
        frequency_penalty=0.0,
        presence_penalty=0.0,
    )

    if response.choices and response.choices[0].message.content:
        revised_script = response.choices[0].message.content
        return revised_script.strip()
    else:
        return "No revision was generated. Please check the input script and try again."


def clean_revised_dialogue(file_path):
    with open(file_path, "r", encoding="utf-8") as file:
        lines = file.readlines()

    cleaned_lines = []
    for line in lines:
        cleaned_line = re.sub(
            r"^\*\*(Ofir|Daniel):\*\*\s*|^(\*\*Ofir\*\*:\s*|\*\*Daniel\*\*:\s*)|(Ofir:|Daniel:)\s*",
            "",
            line,
        )
        cleaned_line = re.sub(r"\*\*(.*?)\*\*", r"\1", cleaned_line)
        cleaned_line = re.sub(
            r"\bsegment\s+\d+\b", "", cleaned_line, flags=re.IGNORECASE
        ).strip()
        cleaned_line = re.sub(
            r"\boutro\b", "", cleaned_line, flags=re.IGNORECASE
        ).strip()
        cleaned_line = re.sub(r"\s{2,}", " ", cleaned_line)
        cleaned_lines.append(cleaned_line)

    with open(file_path, "w", encoding="utf-8") as file:
        for line in cleaned_lines:
            file.write(line + "\n")


def save_revised_script(script_text, file_path="revised_dialogue.txt"):
    normalized_text = re.sub(r"\n\s*\n", "\n", script_text).strip()
    with open(file_path, "w", encoding="utf-8") as file:
        file.write(normalized_text)


def total_revision_process(file_path):
    current_script = read_script(file_path=file_path)
    revised_script = generate_revised_script(current_script)
    save_revised_script(revised_script, file_path="revised_dialogue.txt")
    clean_revised_dialogue("revised_dialogue.txt")


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


def add_intro_music(introAud, speechAud, topic):
    safe_topic = topic.replace(" ", "_")
    final_podcast_filename = f"{safe_topic}.mp3"

    intro_music = AudioSegment.from_file(introAud, format="wav")
    speech_audio = AudioSegment.from_file(speechAud, format="mp3")
    final_podcast = intro_music.fade_in(1500).fade_out(1500) + speech_audio

    final_podcast.export(final_podcast_filename, format="mp3")


def main():
    getScriptfromGemini(topic)
    merge_text_files("host1.txt", "host2.txt", "merged_dialogue.txt")
    total_revision_process("merged_dialogue.txt")
    generate_audio("revised_dialogue.txt", "final_podcast.mp3")
    add_intro_music("introMusic.wav", "final_podcast.mp3", topic)


if __name__ == "__main__":
    main()
