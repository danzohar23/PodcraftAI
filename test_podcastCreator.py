import os
from unittest.mock import mock_open, patch, call
from app.podcastCreator import (merge_text_files,
                                 extract_dialogue, clean_revised_dialogue, save_revised_script,
                                 get_wikipedia_articles_summaries, get_embedding, scrape_nba_games_between_dates,
                                 cosine_similarity, add_intro_music, getScriptfromGemini)
import pytest
import builtins
import numpy as np
from unittest.mock import MagicMock



def test_merge_text_files(tmpdir):
    # Create temporary files to act as input files
    host1_path = tmpdir.join("host1.txt")
    host2_path = tmpdir.join("host2.txt")
    merged_path = tmpdir.join("merged.txt")
    
    # Write mock content to these files
    host1_content = "Line1 from Host1\nLine2 from Host1\n"
    host2_content = "Line1 from Host2\nLine2 from Host2\n"
    host1_path.write(host1_content)
    host2_path.write(host2_content)
    
    # Expected output after merging
    expected_merged_content = "Line1 from Host1\nLine1 from Host2\nLine2 from Host1\nLine2 from Host2\n"
    
    # Call the function under test
    merge_text_files(str(host1_path), str(host2_path), str(merged_path))
    
    # Read the content of the merged file and verify it matches the expected content
    with open(str(merged_path), 'r') as file:
        merged_content = file.read()
    
    assert merged_content == expected_merged_content

def test_extract_dialogue():
    script_input = """
**Ofir:** Hello, Daniel. How are you today?
**Daniel:** I'm good, Ofir, thanks for asking. What are we discussing today?
**Ofir:** Today, we're talking about the importance of unit testing.
**Daniel:** Oh, that's a crucial topic indeed.
"""
    expected_host1_calls = [
        call.write("Hello, Daniel. How are you today?\n"),
        call.write("Today, we're talking about the importance of unit testing.\n")
    ]
    expected_host2_calls = [
        call.write("I'm good, Ofir, thanks for asking. What are we discussing today?\n"),
        call.write("Oh, that's a crucial topic indeed.\n")
    ]

    with patch('builtins.open', mock_open()) as mocked_open:
        extract_dialogue(script_input)

        # Since the same mock object is returned for both files, we can directly check the write calls.
        # Note: This assumes the function does not open any other files. If it does, this approach needs adjustment.
        mocked_open().write.assert_has_calls(expected_host1_calls, any_order=True)
        mocked_open().write.assert_has_calls(expected_host2_calls, any_order=True)

        # Ensure open was called correctly for both output files
        mocked_open.assert_any_call('host1.txt', 'w', encoding='utf-8')
        mocked_open.assert_any_call('host2.txt', 'w', encoding='utf-8')


def test_extract_dialogue_empty_input():
    script_input = ""
    with patch('builtins.open', mock_open()) as mocked_open:
        extract_dialogue(script_input)
        # Verify no file write operations were performed due to empty input
        mocked_open().write.assert_not_called()

def test_extract_dialogue_no_dialogue_markers():
    script_input = "Just some narrative without any dialogue markers."
    with patch('builtins.open', mock_open()) as mocked_open:
        extract_dialogue(script_input)
        # Verify no file write operations were performed as there were no dialogue markers
        mocked_open().write.assert_not_called()


def test_save_revised_script():
    # Mock script text and file path
    script_text = "Hello, welcome to our podcast. Thank you, it's great to be here."
    file_path = "test_revised_dialogue.txt"

    # Call the function under test
    save_revised_script(script_text, file_path)

    # Verify the file content matches the script text
    with open(file_path, "r") as f:
        saved_content = f.read()
    assert saved_content == script_text

    # Clean up the test file
    os.remove(file_path)

def create_temp_file(tmpdir, content):
    file_path = tmpdir.join("temp_file.txt")
    file_path.write(content)
    return str(file_path)

def test_clean_revised_dialogue_removes_unwanted_characters(tmpdir):
    input_content = "**Daniel:** This is a **segment 1** with some unwanted characters #&*@.\n"
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

def test_merge_text_files_with_io_error(tmpdir):
    host1_path = tmpdir.join("host1.txt")
    host2_path = tmpdir.join("host2.txt")
    merged_path = tmpdir.join("merged.txt")

    with patch.object(builtins, 'open', side_effect=IOError("Unable to write to file")):
        with pytest.raises(IOError):
            merge_text_files(str(host1_path), str(host2_path), str(merged_path))


def test_clean_revised_dialogue_with_unexpected_format(tmpdir):
    # Include text that does not follow the expected dialogue format
    input_content = "Daniel: Not following expected **bold** format."
    file_path = create_temp_file(tmpdir, input_content)
    clean_revised_dialogue(file_path)
    with open(file_path, "r", encoding="utf-8") as file:
        output_content = file.read().strip()
    
    # Determine the expected behavior and assert accordingly
    expected_output = "Not following expected bold format."
    assert output_content == expected_output


def test_extract_dialogue_with_only_markers():
    script_input = """
**Ofir:**
**Daniel:**
"""
    expected_calls = [
        call('**Ofir:**\n'),
        call('**Daniel:**\n')
    ]

    with patch('builtins.open', mock_open()) as mocked_open:
        extract_dialogue(script_input)
        mocked_open().write.assert_has_calls(expected_calls, any_order=True)


@patch('wikipedia.search')
@patch('wikipedia.summary')
def test_get_wikipedia_articles_summaries(mock_summary, mock_search):
    # Setup the mock to return titles
    mock_search.return_value = ['Article1', 'Article2']

    # Setup the mock for wikipedia.summary to return fake summaries
    mock_summary.side_effect = [
        "Summary for Article1",  # Returned when 'Article1' is passed
        "Summary for Article2",  # Returned when 'Article2' is passed
    ]

    # Call the function under test
    summaries = get_wikipedia_articles_summaries("Example query")

    # Check if the summaries are as expected
    assert summaries == {
        'Article1': "Summary for Article1",
        'Article2': "Summary for Article2",
    }

    # Check if search was called correctly
    mock_search.assert_called_once_with("Example query", results=3)

    # Check if summary was called with each title and the correct arguments
    mock_summary.assert_any_call('Article1', auto_suggest=False)
    mock_summary.assert_any_call('Article2', auto_suggest=False)

@patch('app.podcastCreator.client.embeddings.create')
def test_get_embedding_success(mock_embeddings_create):
    expected_embedding = [0.1, 0.2, 0.3]  # Example embedding vector
    mock_embeddings_create.return_value = {'data': [{'embedding': expected_embedding}]}

    embedding = get_embedding("Sample text for embedding.")
    assert embedding == expected_embedding


@patch('app.podcastCreator.client.embeddings.create')
def test_get_embedding_failure(mock_embeddings_create):
    mock_embeddings_create.side_effect = Exception("API Error")

    with pytest.raises(Exception) as exc_info:
        get_embedding("Sample text for embedding.")
    assert "API Error" in str(exc_info.value)


@patch('app.podcastCreator.requests.get')
def test_scrape_nba_games_between_dates_success(mock_get):
    # Directly return the mock HTML content as bytes
    mock_get.return_value.content = b"<b>Start Date</b><p>Game Info</p><b>End Date</b>"
    
    result = scrape_nba_games_between_dates("fake_url", "Start Date", "End Date")
    
    # Directly check if "Game Info" is part of the result, indicating successful extraction
    assert "Game Info" in result
    assert result.startswith("Recap of yesterday's games:")



@patch('requests.get')
def test_scrape_nba_games_between_dates_failure(mock_get):
    # Mock failure in HTML response
    mock_get.return_value.content = b"<b>Some Other Date</b>"
    result = scrape_nba_games_between_dates("fake_url", "Start Date", "End Date")
    assert "Start or end tag not found." in result


def test_cosine_similarity():
    vec1 = np.array([1, 0, 0])
    vec2 = np.array([0, 1, 0])
    vec3 = np.array([1, 0, 0])

    # Orthogonal vectors have similarity 0
    assert cosine_similarity(vec1, vec2) == 0
    # Identical vectors have similarity 1
    assert cosine_similarity(vec1, vec3) == 1


@patch('pydub.AudioSegment.from_file')
def test_add_intro_music(mock_audio_from_file):
    intro_mock = mock_audio_from_file.return_value.fade_in.return_value.fade_out.return_value
    speech_mock = mock_audio_from_file.return_value
    # Mock the export method which should be called at the end of `add_intro_music`
    intro_mock.__add__.return_value.export.return_value = None

    add_intro_music("intro.wav", "speech.mp3", "test")
    intro_mock.__add__.assert_called_with(speech_mock)
    intro_mock.__add__.return_value.export.assert_called_once()

