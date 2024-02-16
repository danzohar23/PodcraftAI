import logging
import re
import google.generativeai as genai

genai.configure(api_key="AIzaSyCXUTsOzwN5le4wn3ljIj_U5puGfUJUGao")

model = genai.GenerativeModel("gemini-pro")

logging.basicConfig(
    filename="logging.log",
    filemode="w",
    level=logging.INFO,
    format="%(asctime)s:%(levelname)s:%(message)s",
)


def getScriptfromGemini():
    extracted_dialogue = ""
    user_input = input("Give me an idea for a podcast and I will generate it for you: ")
    chat = model.start_chat(history=[])
    response = chat.send_message(
        "write a dialogue for a podcast according to the following logic. The podcast's content should be updated to news from the past week. The podcast is called "
        "Dudu talk"
        " and it is two people (Host 1 and Host 2) talking about a topic that is defined as follows: "
        + user_input
        + ". If the topic is too broad you can narrow it down to something more specific, but still make it updated to recent news. Choose a topic for the first segment and write the conversation for it. The show should have 5 segments. Stop after each segment and I will tell you how to continue.\n",
    )
    extracted_dialogue += extract_dialogue(response.text)
    logging.info(response.text)
    for i in range(4):
        i = i + 1
        response = chat.send_message(
            "write the next segment of the podcast", stream=True
        )
        for chunk in response:
            logging.info(chunk.text)
        extracted_dialogue += extract_dialogue(response.text)

    logging.info(extracted_dialogue)


def extract_dialogue(script):
    # Define a regex pattern to match lines starting with "Host 1:" or "Host 2:"
    pattern = r"(Host 1:.*?|Host 2:.*?)\n"

    # Use re.findall to extract all matching dialogue lines
    dialogue_lines = re.findall(pattern, script, re.DOTALL)

    # Join the extracted lines into a single string, separated by newlines
    dialogue_script = "\n".join(dialogue_lines)

    return dialogue_script


def main():
    script = getScriptfromGemini()


if __name__ == "__main__":
    main()
