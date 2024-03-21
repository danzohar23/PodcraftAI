import pytest
from httpx import AsyncClient
from app.podcastAPI import app


@pytest.mark.asyncio
async def test_read_main():
    async with AsyncClient(app=app, base_url="http://test") as ac:
        response = await ac.get("/")
    assert response.status_code == 200
    assert response.json() == {
        "Welcome to PodcastGPT": "Write your topic for the podcast, and once the file is ready you can type the topic into the 'download' function to get the podcast file. For example, 'open ai' will be 'open_ai'"
    }


@pytest.mark.asyncio
async def test_generate_podcast():
    test_topic = "Test Topic"
    async with AsyncClient(app=app, base_url="http://test") as ac:
        response = await ac.post(f"/generate_podcast/?topic={test_topic}")
    assert response.status_code == 200


@pytest.mark.asyncio
async def test_download_file():
    test_filename = "test_podcast_with_intro_music.mp3"
    async with AsyncClient(app=app, base_url="http://test") as ac:
        response = await ac.get(f"/download/{test_filename}")
    assert response.status_code == 200
