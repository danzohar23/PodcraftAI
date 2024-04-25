import os
from unittest.mock import mock_open, patch, call
from app.podcastCreator import (
    merge_text_files,
    extract_dialogue,
    clean_revised_dialogue,
    save_revised_script,
    get_wikipedia_articles_summaries,
    get_embedding,
    scrape_nba_games_between_dates,
    cosine_similarity,
    add_intro_music,
    getScriptfromGemini,
    getNBAPodcastContent,
)
import pytest
import builtins
import numpy as np
from unittest.mock import MagicMock
import datetime


@patch("app.podcastCreator.client.embeddings.create")
def test_get_embedding_success(mock_embeddings_create):
    expected_embedding = [0.1, 0.2, 0.3]
    mock_embeddings_create.return_value = {"data": [{"embedding": expected_embedding}]}

    embedding = get_embedding("Sample text for embedding.")
    assert embedding == expected_embedding

@patch("app.podcastCreator.client.embeddings.create")
def test_get_embedding_failure(mock_embeddings_create):
    mock_embeddings_create.side_effect = Exception("API Error")

    with pytest.raises(Exception) as exc_info:
        get_embedding("Sample text for embedding.")
    assert "API Error" in str(exc_info.value)


def test_cosine_similarity():
    vec1 = np.array([1, 0, 0])
    vec2 = np.array([0, 1, 0])
    vec3 = np.array([1, 0, 0])

    assert cosine_similarity(vec1, vec2) == 0
    assert cosine_similarity(vec1, vec3) == 1


@patch("wikipedia.search")
@patch("wikipedia.summary")
def test_get_wikipedia_articles_summaries(mock_summary, mock_search):
    mock_search.return_value = ["Article1", "Article2"]

    mock_summary.side_effect = [
        "Summary for Article1",
        "Summary for Article2",
    ]

    summaries = get_wikipedia_articles_summaries("Example query")

    assert summaries == {
        "Article1": "Summary for Article1",
        "Article2": "Summary for Article2",
    }

    mock_search.assert_called_once_with("Example query", results=3)

    mock_summary.assert_any_call("Article1", auto_suggest=False)
    mock_summary.assert_any_call("Article2", auto_suggest=False)


def _fixed_datetime(target):
    class FixedDateTime(datetime.datetime):
        @classmethod
        def now(cls, tz=None):
            return target

    return FixedDateTime


@patch("app.podcastCreator.requests.get")
@patch(
    "app.podcastCreator.datetime.datetime",
    _fixed_datetime(datetime.datetime(2022, 3, 2)),
)
def test_getNBAPodcastContent_success(mock_get):
    yesterdays_date = "Tuesday, March 01, 2022"
    two_days_ago_date = "Monday, February 28, 2022"
    expected_start = f"NBA Daily For {yesterdays_date}"
    expected_end = f"NBA Daily For {two_days_ago_date}"

    mock_html_content = f"""
    <html>
    <body>
    <b>{expected_start}</b>
    <p>Game Info</p>
    <b>{expected_end}</b>
    </body>
    </html>
    """
    mock_get.return_value = MagicMock()
    mock_get.return_value.content = mock_html_content.encode("utf-8")

    content = getNBAPodcastContent()

    expected_content = "Game Info"
    assert expected_content in content

    assert expected_start in content or expected_end in content


@patch("app.podcastCreator.requests.get")
def test_scrape_nba_games_between_dates_success(mock_get):
    mock_get.return_value.content = b"<b>Start Date</b><p>Game Info</p><b>End Date</b>"

    result = scrape_nba_games_between_dates("fake_url", "Start Date", "End Date")

    assert "Game Info" in result
    assert result.startswith("Recap of yesterday's games:")


@patch("requests.get")
def test_scrape_nba_games_between_dates_failure(mock_get):
    mock_get.return_value.content = b"<b>Some Other Date</b>"
    result = scrape_nba_games_between_dates("fake_url", "Start Date", "End Date")
    assert "Start or end tag not found." in result


@patch("app.podcastCreator.model.start_chat")
def test_getScriptfromGemini_success(mock_start_chat):
    mock_chat_instance = MagicMock()
    mock_start_chat.return_value = mock_chat_instance

    mock_response_text = "This is a generated script based on the given topic."
    mock_chat_instance.send_message.return_value = MagicMock(text=mock_response_text)

    topic = "Artificial Intelligence"
    _ = getScriptfromGemini(topic)

    mock_start_chat.assert_called_once()
    mock_chat_instance.send_message.assert_called()


@patch("app.podcastCreator.model.start_chat")
def test_getScriptfromGemini_api_failure(mock_start_chat):
    mock_start_chat.side_effect = Exception("Failed to start chat with the model")

    topic = "Artificial Intelligence"
    with pytest.raises(Exception) as exc_info:
        getScriptfromGemini(topic)
    assert "Failed to start chat with the model" in str(exc_info.value)


def test_extract_dialogue():
    script_input = """
**Ofir:** Hello, Daniel. How are you today?
**Daniel:** I'm good, Ofir, thanks for asking. What are we discussing today?
**Ofir:** Today, we're talking about the importance of unit testing.
**Daniel:** Oh, that's a crucial topic indeed.
"""
    expected_host1_calls = [
        call.write("Hello, Daniel. How are you today?\n"),
        call.write("Today, we're talking about the importance of unit testing.\n"),
    ]
    expected_host2_calls = [
        call.write(
            "I'm good, Ofir, thanks for asking. What are we discussing today?\n"
        ),
        call.write("Oh, that's a crucial topic indeed.\n"),
    ]

    with patch("builtins.open", mock_open()) as mocked_open:
        extract_dialogue(script_input)

        mocked_open().write.assert_has_calls(expected_host1_calls, any_order=True)
        mocked_open().write.assert_has_calls(expected_host2_calls, any_order=True)

        mocked_open.assert_any_call("host1.txt", "w", encoding="utf-8")
        mocked_open.assert_any_call("host2.txt", "w", encoding="utf-8")


def test_extract_dialogue_empty_input():
    script_input = ""
    with patch("builtins.open", mock_open()) as mocked_open:
        extract_dialogue(script_input)
        mocked_open().write.assert_not_called()


def test_extract_dialogue_no_dialogue_markers():
    script_input = "Just some narrative without any dialogue markers."
    with patch("builtins.open", mock_open()) as mocked_open:
        extract_dialogue(script_input)
        mocked_open().write.assert_not_called()


def test_extract_dialogue_with_only_markers():
    script_input = """
**Ofir:**
**Daniel:**
"""
    expected_calls = [call("**Ofir:**\n"), call("**Daniel:**\n")]

    with patch("builtins.open", mock_open()) as mocked_open:
        extract_dialogue(script_input)
        mocked_open().write.assert_has_calls(expected_calls, any_order=True)


def test_merge_text_files(tmpdir):
    host1_path = tmpdir.join("host1.txt")
    host2_path = tmpdir.join("host2.txt")
    merged_path = tmpdir.join("merged.txt")

    host1_content = "Line1 from Host1\nLine2 from Host1\n"
    host2_content = "Line1 from Host2\nLine2 from Host2\n"
    host1_path.write(host1_content)
    host2_path.write(host2_content)

    expected_merged_content = (
        "Line1 from Host1\nLine1 from Host2\nLine2 from Host1\nLine2 from Host2\n"
    )

    merge_text_files(str(host1_path), str(host2_path), str(merged_path))

    with open(str(merged_path), "r") as file:
        merged_content = file.read()

    assert merged_content == expected_merged_content


def test_merge_text_files_with_io_error(tmpdir):
    host1_path = tmpdir.join("host1.txt")
    host2_path = tmpdir.join("host2.txt")
    merged_path = tmpdir.join("merged.txt")

    with patch.object(builtins, "open", side_effect=IOError("Unable to write to file")):
        with pytest.raises(IOError):
            merge_text_files(str(host1_path), str(host2_path), str(merged_path))


def test_save_revised_script():
    script_text = "Hello, welcome to our podcast. Thank you, it's great to be here."
    file_path = "test_revised_dialogue.txt"

    save_revised_script(script_text, file_path)

    with open(file_path, "r") as f:
        saved_content = f.read()
    assert saved_content == script_text

    os.remove(file_path)


def create_temp_file(tmpdir, content):
    file_path = tmpdir.join("temp_file.txt")
    file_path.write(content)
    return str(file_path)


def test_clean_revised_dialogue_removes_unwanted_characters(tmpdir):
    input_content = (
        "**Daniel:** This is a **segment 1** with some unwanted characters #&*@.\n"
    )
    expected_output = "This is a with some unwanted characters #&*@."
    file_path = create_temp_file(tmpdir, input_content)
    clean_revised_dialogue(file_path)
    with open(file_path, "r", encoding="utf-8") as file:
        output_content = file.read().strip()
    assert output_content == expected_output


def test_clean_revised_dialogue_handles_empty_file(tmpdir):
    file_path = create_temp_file(tmpdir, "")
    clean_revised_dialogue(file_path)
    with open(file_path, "r", encoding="utf-8") as file:
        output_content = file.read()
    assert output_content == ""


def test_clean_revised_dialogue_with_unexpected_format(tmpdir):
    input_content = "Daniel: Not following expected **bold** format."
    file_path = create_temp_file(tmpdir, input_content)
    clean_revised_dialogue(file_path)
    with open(file_path, "r", encoding="utf-8") as file:
        output_content = file.read().strip()

    expected_output = "Not following expected bold format."
    assert output_content == expected_output


@patch("pydub.AudioSegment.from_file")
def test_add_intro_music(mock_audio_from_file):
    intro_mock = (
        mock_audio_from_file.return_value.fade_in.return_value.fade_out.return_value
    )
    speech_mock = mock_audio_from_file.return_value
    intro_mock.__add__.return_value.export.return_value = None

    add_intro_music("intro.wav", "speech.mp3", "test")
    intro_mock.__add__.assert_called_with(speech_mock)
    intro_mock.__add__.return_value.export.assert_called_once()
