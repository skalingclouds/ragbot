# helpers.py
# Shared functions used by rbot.py and rbot-streamlit.py
# Author: Rajiv Pant

import os
import glob
import yaml
import pathlib
import uuid
import tiktoken
from litellm import completion

def load_config(config_file):
    """Load configuration from YAML."""
    with open(config_file, 'r') as stream:
        config = yaml.safe_load(stream)
    return config

def load_profiles(profiles_file):
    """Load profiles from YAML."""
    with open(profiles_file, 'r') as stream:
        profiles = yaml.safe_load(stream)
    return profiles['profiles']

def process_file(filepath, file_type):
    """Helper function to read and format the content of a file."""
    unique_id = str(uuid.uuid4())
    document_start_tag = f"<document:{unique_id} path=\"{filepath}\" type=\"{file_type}\">"
    document_end_tag = f"</document:{unique_id}>"
    with open(filepath, "r") as file:
        # Read the entire file content as a single string
        file_content = file.read() 

    # Ensuring newline characters are added only where needed
    full_content = f"{document_start_tag}\n{file_content}{document_end_tag}\n"
    return full_content, filepath

def load_files(file_paths, file_type):
    """Load files containing custom instructions or curated datasets."""
    files_content = []
    files_list = []  # to store file names
    for path in file_paths:
        if os.path.isfile(path):
            content, filename = process_file(path, file_type)
            files_content.append(content)
            files_list.append(filename)  # save file name
        elif os.path.isdir(path):
            for filepath in glob.glob(os.path.join(path, "*")):
                if os.path.isfile(filepath):
                    content, filename = process_file(filepath, file_type)
                    files_content.append(content)
                    files_list.append(filename)  # save file name

    files_content_str = "\n".join(files_content)
    return files_content_str, files_list

def human_format(num):
    """Convert a number to a human-readable format."""
    num = float('{:.3g}'.format(num))
    magnitude = 0
    while abs(num) >= 1000:
        magnitude += 1
        num /= 1000.0
    return '{}{}'.format('{:f}'.format(num).rstrip('0').rstrip('.'), ['', 'k', 'M', 'B', 'T'][magnitude])

def count_tokens(file_paths):
    """count tokens in a list of files"""
    tokenizer = tiktoken.get_encoding('p50k_base')
    total_tokens = 0
    for file_path in file_paths:
        with open(file_path, 'r') as file:
            content = file.read()
            total_tokens += len(tokenizer.encode(content))
    return total_tokens

def count_custom_instructions_tokens(custom_instruction_path):
    """count tokens in custom instructions files"""
    _, custom_instruction_files = load_files(file_paths=custom_instruction_path, file_type="custom_instructions")
    return count_tokens(custom_instruction_files)

def count_curated_datasets_tokens(curated_dataset_path):
    """count tokens in curated datasets files"""
    _, curated_dataset_files = load_files(file_paths=curated_dataset_path, file_type="curated_datasets")
    return count_tokens(curated_dataset_files)


def print_saved_files(directory):
    """Print the list of saved JSON files in the sessions directory."""
    sessions_directory = os.path.join(directory, "sessions")
    print("Currently saved JSON files:")
    for file in pathlib.Path(sessions_directory).glob("*.json"):
        print(f" - {file.name}")

def chat(
    prompt,
    curated_datasets,
    custom_instructions,
    model,
    max_tokens,
    stream=True,
    request_timeout=15,
    temperature=0.75,
    history=None,
    engine="openai",
    interactive=False,
    new_session=False,
    supports_system_role=True
):
    """
    Send a request to the LLM API with the provided prompt and curated_datasets.

    :param prompt: The user's input to generate a response for.
    :param curated_datasets: A list of curated_datasets to provide context for the model.
    :param model: The name of the GPT model to use.
    :param max_tokens: The maximum number of tokens to generate in the response (default is 1000).
    :param stream: Whether to stream the response from the API (default is True).
    :param request_timeout: The request timeout in seconds (default is 15).
    :param temperature: The creativity of the response, with higher values being more creative (default is 0.75).
    :param history: The conversation history, if available (default is None).
    :param engine: The engine to use for the chat, 'openai' or 'anthropic' (default is 'openai').
    :param interactive: Whether the chat is in interactive mode (default is False).
    :param new_session: Whether this is a new session (default is False).
    :param supports_system_role: Whether the model supports the "system" role (default is True).
    :return: The generated response text from the model.
    """
    added_curated_datasets = False

    # Google Generative AI mddels don't seem to accept the "system" role for the prompt.
    if supports_system_role:
        messages = [
            {"role": "system", "content": "\n".join(custom_instructions) + "\n".join(curated_datasets)},
            {"role": "user", "content": prompt}  # Dynamic user input for current interaction
        ]
    else:
        messages = [
            {"role": "user", "content": "\n".join(custom_instructions)},
            {"role": "user", "content": "\n".join(curated_datasets)},
            {"role": "user", "content": prompt}  # Dynamic user input for current interaction
        ]
    
    llm_response = completion(model=model, messages=messages,  max_tokens=max_tokens, temperature=temperature)
    response = llm_response.get('choices', [{}])[0].get('message', {}).get('content')
    
    return response
