import os
import subprocess
import streamlit as st
from manim import *
import openai
# from openai.error import AuthenticationError
from PIL import Image
from moviepy.editor import VideoFileClip, AudioFileClip
from google.cloud import texttospeech
import matplotlib.pyplot as plt

from utils import *

# icon = Image.open(os.path.dirname(__file__) + '/icon.png')

st.set_page_config(
    page_title="",
    # page_icon=icon,
)

styl = f"""
<style>
  textarea[aria-label="Code generated: "] {{
    font-family: 'Consolas', monospace !important;
  }}
</style>
"""
st.markdown(styl, unsafe_allow_html=True)

st.title("")

prompt = st.text_area("Write what do you want to learn. Use simple words",
                      "Pythagoras Theorem", max_chars=100,
                      key="prompt_input")

openai_api_key = st.secrets["OPENAI_API_KEY"]
os.environ["OPENAI_API_KEY"] = st.secrets["OPENAI_API_KEY"]


openai_model = st.selectbox(
    "Select the GPT model", ["GPT-3.5-Turbo", "GPT-4"])

if st.checkbox("Use own Open API Key (recommended)"):
  openai_api_key = st.text_input(
      "Paste your own [Open API Key](https://platform.openai.com/account/api-keys)", value="", type="password")

# st.write(":warning: Currently OpenAI accepts 25 requests every 3 hours for GPT-4. This means OpenAI will start rejecting some requests. There are two solutions: Use GPT-3.5-Turbo, or use your own OpenAI API key.")

generate_video = st.button("Generate", type="primary")
show_code = st.checkbox("Show generated code (that produces the video)")

code_response = ""

if generate_video:

  if not openai_model:
    openai_model = "gpt-4"

  if not prompt:
    st.error("Error: Please write a prompt to generate the video.")
    st.stop()

  # If prompt is less than 10 characters, it will be rejected
  if len(prompt) < 10:
    st.error("Error: Your prompt is too short. Please write a longer prompt.")
    st.stop()

  # If prompt exceeds 240 characters, it will be truncated
  if len(prompt) > 240 and not openai_api_key:
    st.error("Error: Your prompt is longer than 240 characters. Please shorten it.")
    st.stop()

  # Prompt must be trimmed of spaces at the beginning and end
  prompt = prompt.strip()

  # Remove ", ', \ characters
  prompt = prompt.replace('"', '')
  prompt = prompt.replace("'", "")
  prompt = prompt.replace("\\", "")

  # If user has their own API key, increase max tokens by 3x
  if not openai_api_key:
    max_tokens = 400
  else:
    max_tokens = 1200

  # If user has their own API key, use it
  if not openai_api_key:
    try:
      # If there is OPENAI_API_KEY in the environment variables, use it
      # Otherwise, use Streamlit secrets variable
      if os.environ["OPENAI_API_KEY"]:
        openai_api_key = os.environ["OPENAI_API_KEY"]
      else:
        openai_api_key = st.secrets["OPENAI_API_KEY"]
    except:
      st.error("Error: Sorry, I disabled my OpenAI API key (the budget is over). Please use your own API key and it will work perfectly. Otherwise, please send me a message on Twitter (@360macky)")
      st.stop()
  else:
    try:
      openai.api_key = openai_api_key
    # except AuthenticationError:
    #   st.error(
    #       "Error: The OpenAI API key is invalid. Please check if it's correct.")
    #   st.stop()
    except:
      st.error(
          "Error: We couldn't authenticate your OpenAI API key. Please check if it's correct.")
      st.stop()

  try:
    response = openai.chat.completions.create(
        model=openai_model.lower(),
        messages=[
            {"role": "system", "content": GPT_SYSTEM_INSTRUCTIONS},
            {"role": "user", "content": wrap_prompt(prompt)}
        ],
        max_tokens=max_tokens
    )
  except:
    if openai_model.lower() == "gpt-4":
      st.error(
          "Error: This is likely a rate limit error for GPT-4. Currently OpenAI accepts 25 requests every 3 hours for GPT-4. This means OpenAI will start rejecting some requests randomly. There are two solutions: Use GPT-3.5-Turbo, or use your own OpenAI API key.")
      st.stop()
    else:
      st.error(
          "Error: We couldn't generate the generated code. Please reload the page, or try again later")
      st.stop()

  code_response = extract_construct_code(
      extract_code(response.choices[0].message.content))  
  
  video_duration = 0
  
  if show_code:
    st.text_area(label="Code generated: ",
                 value=code_response,
                 key="code_input")

  if os.path.exists(os.path.dirname(__file__) + '/../../GenScene.py'):
    os.remove(os.path.dirname(__file__) + '/../../GenScene.py')

  if os.path.exists(os.path.dirname(__file__) + '/../../GenScene.mp4'):
    os.remove(os.path.dirname(__file__) + '/../../GenScene.mp4')

  try:
    with open("GenScene.py", "w") as f:
      f.write(create_file_content(code_response))
  except:
    st.error("Error: We couldn't create the generated code in the Python file. Please reload the page, or try again later")
    st.stop()

  COMMAND_TO_RENDER = "manim GenScene.py GenScene --format=mp4 --media_dir . --custom_folders video_dir"

  problem_to_render = False
  try:
    working_dir = os.path.dirname(__file__) + "/../"
    subprocess.run(COMMAND_TO_RENDER, check=True, cwd=working_dir, shell=True)
  except Exception as e:
    problem_to_render = True
    st.error(
        f"Error: Apparently GPT generated code that Manim (the render engine) can't process.")
  if not problem_to_render:  
    try:
        video_file_path = os.path.dirname(__file__) + '/../GenScene.mp4'
        video_file = open(video_file_path, 'rb')
        video_bytes = video_file.read()

        # Use moviepy to get video duration
        video_clip = VideoFileClip(video_file_path)

        # AFTER
        st.video(video_bytes)

        video_duration = video_clip.duration
        # st.write(f"Video Duration: {video_duration} seconds")
    except FileNotFoundError:
        st.error("Error: I couldn't find the generated video file. I know this is a bug and I'm working on it. Please reload the page.")
    except Exception as e:
        st.error(f"Error: Something went wrong showing your video. Error details: {str(e)}. Please reload the page.")

  generated_text = ""
  final_prompt = f"{code_response} \n, for the above manim code write some content explaining the content in very brief to the point to put in the video background whose length is {video_duration/2} seconds and in one paragraph. strictly fit within the {video_duration/2} second timeframe."
  try:
      resp = openai.chat.completions.create(
          model=openai_model.lower(),
          messages=[
              {"role": "system", "content": GPT_SYSTEM_INSTRUCTIONS},
              {"role": "user", "content": wrap_prompt(final_prompt)}
          ],
          max_tokens=max_tokens
      )
      generated_text = resp.choices[0].message.content
      audio_path = generate_audio(generated_text)
      st.audio(audio_path, format='audio/wav')
      # DEBUG
      # st.write(generated_text)
      # st.write(final_prompt)
  except Exception as e:
      st.error(f"Error: Failed to make a request to the OpenAI GPT API. Error details: {str(e)}")
      st.error(f"Prompt: {final_prompt}")
      st.stop()

  # Generate audio from the text
  # audio_path = generate_audio(generated_text)
  # st.write(audio_path)
      
  # try:
  #     video_file_path = os.path.dirname(__file__) + '/../GenScene.mp4'
  #     audio_file_path = os.path.dirname(__file__) + '/../output_audio.mp3'

  #     video_clip = VideoFileClip(video_file_path)
  #     audio_clip = AudioFileClip(audio_file_path)
  #     # audio_file = open(audio_path, 'rb')
  #     # # DEBUG
  #     # st.audio(audio_file.read(), format='audio/wav')

  #     video_clip = video_clip.set_audio(audio_clip)
  #     merged_video_path = os.path.dirname(__file__) + '/../MergedVideo.mp4'
  #     merge_video_audio_ffmpeg(video_file_path, audio_file_path, merged_video_path)
  #     # video_clip.write_videofile(merged_video_path, codec='libx264', audio_codec='aac')

  #     # Display the merged video
  #     st.video(merged_video_path)

  # except Exception as audio_error:
  #         st.error(f"Error: Failed to open the audio file. Error details: {str(audio_error)}")

  translated_images = text_to_sign_language(resp.choices[0].message.content)
  st.video(translated_images)



