import os
from unittest.mock import mock_open, patch, call
from app.podcastCreator import merge_text_files, extract_dialogue, clean_revised_dialogue, save_revised_script
import pytest

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