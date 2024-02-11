import openai
from openai import OpenAI
import logging
import os

os.environ["OPENAI_API_KEY"] = "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"
openai.api_key = "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"
client = OpenAI()
logging.basicConfig(
    filename="logging.log",
    level=logging.INFO,
    format="%(asctime)s:%(levelname)s:%(message)s",
)


def getScriptfromGPT():
    user_input = input(
        "Give me an idea for a script and I will generate you a script. After that you can choose whether I will generate a clip based on this script or if you want to retry:"
    )
    message = {
        "role": "user",
        "content": "Based on the following idea, I want you to generate a script for me. It should be relatively short but still have a beginning, middle and end. Here is the idea:\n"
        + user_input,
    }
    try:
        # Call GPT-3.5-turbo using the chat API
        response = client.chat.completions.create(
            model="gpt-3.5-turbo", messages=[message]
        )

        return response.choices[0].message.content
    except Exception as e:
        print(f"An error occurred: {e}")
        return None


def generateClip(script):
    print("Your clip will be generated here")


def main():
    script = getScriptfromGPT()
    print(script)
    logging.info(script)
    print("Script generated successfully!")
    print("Do you want to generate a clip based on this script?")
    print("1. Yes")
    print("2. No")
    choice = input("Enter your choice: ")
    if choice == "1":
        print("Generating clip...")
        # Call the function to generate a clip
        generateClip(script)
    elif choice == "2":
        print("Do you want to retry?")
        print("1. Yes")
        print("2. No")
        retry = input("Enter your choice: ")
        if retry == "1":
            main()
        elif retry == "2":
            getScriptfromGPT()
        else:
            print("Invalid choice. Exiting...")
    else:
        print("Invalid choice. Exiting...")


if __name__ == "__main__":
    main()
