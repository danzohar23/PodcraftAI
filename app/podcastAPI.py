import logging
from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.responses import FileResponse
import os
from podcastCreator import (
    getScriptfromGemini,
    merge_text_files,
    total_revision_process,
    generate_audio,
    add_intro_music,
)

app = FastAPI()


@app.get("/")
async def read_item():
    return {"message": "Hello World"}


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
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=80)
