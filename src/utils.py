import re
import json
import os
import subprocess
import openai
import streamlit as st
from moviepy.editor import VideoFileClip
from google.cloud import texttospeech
from PIL import Image
import imageio

GPT_SYSTEM_INSTRUCTIONS = """Write Manim scripts for animations in Python. Generate code, not text. Never explain code. Never add functions. Never add comments. Never infinte loops. Never use other library than Manim/math. Only complete the code block. Use variables with length of maximum 2 characters. At the end use 'self.play'.

```
from manim import *
from math import *

class GenScene(Scene):
    def construct(self):
        # Write here
```"""

src_folder = os.path.dirname(os.path.abspath(__file__))
project_folder = os.path.dirname(src_folder)
keyfile_path = os.path.join(project_folder, 'config.json')


def generate_config_file():
    secrets = {
        "type": st.secrets["TYPE"],
        "project_id": st.secrets["PROJECT_ID"],
        "private_key_id": st.secrets["PRIVATE_KEY_ID"],
        "private_key": st.secrets["PRIVATE_KEY"],
        "client_email": st.secrets["CLIENT_EMAIL"],
        "client_id": st.secrets["CLIENT_ID"],
        "auth_uri": st.secrets["AUTH_URI"],
        "token_uri": st.secrets["TOKEN_URI"],
        "auth_provider_x509_cert_url": st.secrets["AUTH_PROVIDER"],
        "client_x509_cert_url": st.secrets["CLIENT_URL"],
        "universe_domain": st.secrets["UNIVERSE_DOMAIN"],
    }
    with open("config.json", "w") as json_file:
        json.dump(secrets, json_file)

# Initialize a Text-to-Speech client
generate_config_file()

client = texttospeech.TextToSpeechClient.from_service_account_file(keyfile_path)

src_folder = os.path.dirname(os.path.abspath(__file__))
images_folder = os.path.join(src_folder, '..', 'images/')

sign_language_dict = {
    'A': 'A_test.jpg',
    'B': 'B_test.jpg',
    'C': 'C_test.jpg',
    'D': 'D_test.jpg',
    'E': 'E_test.jpg',
    'F': 'F_test.jpg',
    'G': 'G_test.jpg',
    'H': 'H_test.jpg',
    'I': 'I_test.jpg',
    'J': 'J_test.jpg',
    'K': 'K_test.jpg',
    'L': 'L_test.jpg',
    'M': 'M_test.jpg',
    'N': 'N_test.jpg',
    'O': 'O_test.jpg',
    'P': 'P_test.jpg',
    'Q': 'Q_test.jpg',
    'R': 'R_test.jpg',
    'S': 'S_test.jpg',
    'T': 'T_test.jpg',
    'U': 'U_test.jpg',
    'V': 'V_test.jpg',
    'W': 'W_test.jpg',
    'X': 'X_test.jpg',
    'Y': 'Y_test.jpg',
    'Z': 'Z_test.jpg',
    ' ': 'space_test.jpg',  # Define a blank image for spaces
}

image_dict = {}
for key, filename in sign_language_dict.items():
    image_path = os.path.join(images_folder, filename)
    image = Image.open(image_path)
    image_dict[key] = image

# Function to translate text to sign language images
def text_to_sign_language(text):
    # Create a list to store the sign language images
    sign_language_images = []
    # print(f" path: {images_folder}")
    
    for letter in text.upper():
        if letter in image_dict:
            image_path =  str(image_dict[letter].filename)
            # print(f"Processing letter: {letter}")
            # print(f"Image path: {image_path}")
            try:
                img = Image.open(image_path)
                sign_language_images.append(img)
            except FileNotFoundError:
                print(f"Image not found for letter: {letter}")

    merged_video_path = os.path.dirname(__file__) + '/../ASL.mp4'
    imageio.mimsave(merged_video_path, sign_language_images, fps=3)  # Adjust fps as needed

    return merged_video_path
    # return sign_language_images

# Function to generate audio from text
def generate_audio(text):
    synthesis_input = texttospeech.SynthesisInput(text=text)
    print(f"Synthesis input: {synthesis_input}")
    voice = texttospeech.VoiceSelectionParams(
        language_code="en-US",  # Update with your desired language code
        name="en-US-Wavenet-D",  # Update with your desired voice model
        ssml_gender=texttospeech.SsmlVoiceGender.NEUTRAL
    )
    output_file_path = os.path.dirname(__file__) + '/../output_audio.mp3'

    audio_config = texttospeech.AudioConfig(
        audio_encoding=texttospeech.AudioEncoding.LINEAR16
    )
    try:
        response = client.synthesize_speech(
            input=synthesis_input, voice=voice, audio_config=audio_config
        )

        # Save the generated audio to a file
        with open(output_file_path, "wb") as out_file:
            out_file.write(response.audio_content)

        return os.path.abspath(output_file_path)
    except Exception as e:
        print(f"Error generating audio: {e}")
        return None

def merge_video_audio_ffmpeg(video_path, audio_path, output_path):
    cmd = [
        "ffmpeg",
        "-i", video_path,
        "-i", audio_path,
        "-c:v", "libx264",
        "-c:a", "aac",
        "-strict", "experimental",
        "-shortest",
        output_path
    ]
    subprocess.run(cmd)

def get_video_duration(video_path):
    try:
        clip = VideoFileClip(video_path)
        duration = clip.duration
        clip.close()
        return duration
    except Exception as e:
        print(f"Error getting video duration: {e}")
        return None

def wrap_prompt(prompt: str) -> str:
  """
    Wraps the prompt in the GPT-3.5 instructions
  """
  return f"Animation Request: {prompt}"

def extract_code(text: str) -> str:
  """
    Extracts the code from the text generated by GPT-3.5 from the ``` ``` blocks
  """
  pattern = re.compile(r"```(.*?)```", re.DOTALL)
  match = pattern.search(text)
  if match:
    return match.group(1).strip()
  else:
    return text

def extract_construct_code(code_str: str) -> str:
  """
    Extracts the code from the construct method
  """
  pattern = r"def construct\(self\):([\s\S]*)"
  match = re.search(pattern, code_str)
  if match:
    return match.group(1)
  else:
    return ""

def code_static_corrector(code_response: str) -> str:
  """
    Corrects some static errors in the code
    GPT only has information until 2021, so it ocasionally generates code
    that is not compatible with the latest version of Manim
  """
  code_response = code_response.replace("ShowCreation", "Create")

  return code_response

def create_file_content(code_response: str) -> str:
  """
    Creates the content of the file to be written
  """
  return f"""# Manim code generated with OpenAI GPT
# Command to generate animation: manim GenScene.py GenScene --format=mp4 --media_dir . --custom_folders video_dir

from manim import *
from math import *

class GenScene(Scene):
    def construct(self):
{code_static_corrector(code_response)}"""
