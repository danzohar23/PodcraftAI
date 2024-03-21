import logging
import uvicorn
from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.responses import FileResponse
import os
from pydantic import BaseModel
from datetime import datetime
from azure.storage.blob import BlobServiceClient
import pyodbc
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
if config != {}:
    connection_string = config["AZURE_SQL_CONNECTIONSTRING"]
    blob_connection_string = config["AZURE_BLOB_CONNECTIONSTRING"]
else:
    connection_string = os.environ["AZURE_SQL_CONNECTIONSTRING"]
    blob_connection_string = os.environ["AZURE_BLOB_CONNECTIONSTRING"]


def create_podcast_entry(podcast: Podcast):
    with pyodbc.connect(connection_string) as conn:
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO Podcasts (Name, CreationDate, FilePath) VALUES (?, ?, ?)",
            podcast.podcastname,
            podcast.creation_date,
            podcast.file_path,
        )
        conn.commit()


def create_podcasts_table():
    with pyodbc.connect(connection_string) as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            IF NOT EXISTS (SELECT * FROM sys.tables WHERE name = 'Podcasts')
            CREATE TABLE Podcasts (
                Id INT PRIMARY KEY IDENTITY,
                Name NVARCHAR(255),
                CreationDate DATETIME,
                FilePath NVARCHAR(255)
            )
        """
        )
        conn.commit()


def upload_to_blob_and_get_url(file_path, file_name, container_name):

    blob_service_client = BlobServiceClient.from_connection_string(
        blob_connection_string
    )

    blob_client = blob_service_client.get_blob_client(
        container=container_name, blob=file_name
    )

    with open(file_path, "rb") as data:
        blob_client.upload_blob(data, overwrite=True)

    blob_url = blob_client.url

    return blob_url


app = FastAPI()
create_podcasts_table()


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
    blob_file_path = upload_to_blob_and_get_url(file_path, filename, "blob1")
    if os.path.exists(file_path):
        new_podcast = Podcast(
            podcastname=filename, creation_date=datetime.now(), file_path=blob_file_path
        )
        if filename != "test_podcast_with_intro_music.mp3":
            create_podcast_entry(new_podcast)
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
    uvicorn.run(app, host="0.0.0.0", port=80)
