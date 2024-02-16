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
    dialogue = ""
    user_input = input("Give me an idea for a podcast and I will generate it for you: ")
    chat = model.start_chat(history=[])
    response = chat.send_message(
        "write a dialogue for a podcast according to the following logic. The podcast's content should be updated to news on the topic given from the past week. The podcast is called "
        "Dudu talk"
        " and it is two people (Host 1 and Host 2) talking about a topic that is defined as follows: "
        + user_input
        + ". If the topic is too broad you can narrow it down to something more specific, but still make it updated to recent news. Choose a topic for the first segment and write the conversation for it. There should be a new line in between Host 1 and Host 2's dialogue. The show should have 5 segments. Stop after each segment and I will tell you how to continue.\n",
    )
    logging.info(response.text)
    dialogue = dialogue + "\n" + response.text
    for i in range(4):
        i = i + 1
        response = chat.send_message(
            "write the next segment of the podcast", stream=True
        )
        for chunk in response:
            logging.info(chunk.text)
            dialogue = dialogue + chunk.text

    logging.info(dialogue)
    extracted_dialogue = extract_dialogue(dialogue)
    logging.info(extracted_dialogue)


def extract_dialogue(script):
    lines = script.split("\n")

    # Initialize lists to hold dialogues for each host
    host1_dialogue = []
    host2_dialogue = []

    # Iterate through each line and separate dialogues based on the host
    for line in lines:
        if line.startswith("**Host 1:**"):
            # Extract dialogue and add it to host1's list
            host1_dialogue.append(line.replace("**Host 1:** ", ""))
        elif line.startswith("**Host 2:**"):
            # Extract dialogue and add it to host2's list
            host2_dialogue.append(line.replace("**Host 2:** ", ""))

    # Write the dialogues to respective text files
    with open("host1.txt", "w") as file1:
        for dialogue in host1_dialogue:
            file1.write(dialogue + "\n")

    with open("host2.txt", "w") as file2:
        for dialogue in host2_dialogue:
            file2.write(dialogue + "\n")


def main():
    # Clear the log file
    open("logging.log", "w").close()

    # Clear host1.txt
    open("host1.txt", "w").close()

    # Clear host2.txt
    open("host2.txt", "w").close()

    script = getScriptfromGemini()


if __name__ == "__main__":
    main()
