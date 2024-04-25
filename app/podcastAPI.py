import logging
import uvicorn
from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.responses import FileResponse
import os
from pydantic import BaseModel
from datetime import datetime
from dotenv import dotenv_values

try:
    from .podcastCreator import (
        getScriptfromGemini,
        merge_text_files,
        total_revision_process,
        generate_audio,
        add_intro_music,
    )
except ImportError:
    from podcastCreator import (
        getScriptfromGemini,
        merge_text_files,
        total_revision_process,
        generate_audio,
        add_intro_music,
    )


class Podcast(BaseModel):
    podcastname: str
    creation_date: datetime
    file_path: str


config = dotenv_values()

app = FastAPI()


@app.get("/")
async def read_item():
    return {
        "Welcome to PodcastGPT": "Write your topic for the podcast, and once the file is ready you can type the topic into the 'download' function to get the podcast file. For example, 'open ai' will be 'open_ai'"
    }


@app.post("/generate_podcast/")
async def generate_podcast(background_tasks: BackgroundTasks, topic: str):
    background_tasks.add_task(podcast_generation_task, topic)
    return {"message": "Podcast generation started in the background"}


@app.get("/download/{filename}")
async def download_file(filename: str):
    file_path = f"./{filename}"
    if os.path.exists(file_path):
        return FileResponse(path=file_path, filename=filename, media_type="audio/mpeg")
    raise HTTPException(status_code=404, detail="File not found")


def podcast_generation_task(topic: str):
    try:
        logging.basicConfig(
            filename="logging.log",
            filemode="w",
            level=logging.INFO,
            format="%(asctime)s:%(levelname)s:%(message)s",
        )
        getScriptfromGemini(topic)
        logging.info("Script downloaded from Gemini")
        merge_text_files("host1.txt", "host2.txt", "merged_dialogue.txt")
        logging.info("Dialogue merged")
        total_revision_process("merged_dialogue.txt")
        logging.info("Dialogue revised")
        generate_audio("revised_dialogue.txt", "final_podcast.mp3")
        logging.info("Audio generated")
        add_intro_music("introMusic.wav", "final_podcast.mp3", topic)
        logging.info("Podcast Completed")
    except Exception as e:
        print(f"An error occurred: {e}")


if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=8000)
