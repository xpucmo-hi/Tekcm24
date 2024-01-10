import streamlit as st
import base64
import os
import time
import openai
from openai._client import OpenAI
from audio_recorder_streamlit import audio_recorder
from tempfile import NamedTemporaryFile

# オプション
lang_list = {0: "日本語", 1: "български"}
lang_code = {0: "ja", 1: "bg"}
lang_english = {0: "Japanese", 1: "Bulgarian"}
mode_list = {0: "翻訳", 1: "添削", 2: "会話", 3: "添削回答"}
mode_english = {0: "Translate this content into", 1: "Correct the grammer of this content in", 2: "Answer this question within 2 sentences in", 3: "Correct the grammer, and answer this question within 3 sentences in"}
model_list = ['gpt-3.5-turbo', 'gpt-3.5-turbo-instruct', 'gpt-4']

with st.sidebar:
    openai_api_key = st.text_input("OpenAI API Key", key="api_key", type="password")
    client = OpenAI(api_key = openai_api_key)
    openai.api_key = openai_api_key
    model_select = st.selectbox(label='使用モデル', options=model_list, index=0)

st.title('Tekcm 24 beta')
#lang_input = st.radio(label='入力言語', options=(0,1), index=0, horizontal=True, format_func=lambda x: lang_list.get(x))
lang_output = st.radio(label='出力言語', options=(0,1), index=1, horizontal=True, format_func=lambda x: lang_list.get(x))
mode = st.radio(label='何をお望みですか？', options=(0,1,2), index=0, horizontal=True, format_func=lambda x: mode_list.get(x))

def speech_to_text(audio_bytes, model='whisper-1', language='ja'):
    with NamedTemporaryFile(delete=True, suffix=".wav") as temp_file:
        temp_file.write(audio_bytes)
        temp_file.flush()
        with open(temp_file.name, "rb") as fr:
            transcription = client.audio.transcriptions.create(
                model = model,
                file = fr,
                language=language
            )
    return transcription.text

def process(task: str, lang: str, content: str, model: str) -> str:
    prompt = f"""
    {task} {lang}
    {content}
    """
    response = openai.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": prompt},
        ]
    )
    return response.choices[0].message.content

def text_to_speech(sentence, audiofile):
    response = client.audio.speech.create(
        model="tts-1",
        voice="nova",
        input=sentence,
    )
    response.stream_to_file(audiofile)

def playaudio(filename):
    audio_placeholder = st.empty()

    file_ = open(filename, "rb")
    contents = file_.read()
    file_.close()

    audio_str = "data:audio/ogg;base64,%s"%(base64.b64encode(contents).decode())
    audio_html = """
                    <audio autoplay=True>
                    <source src="%s" type="audio/ogg" autoplay=True>
                    Your browser does not support the audio element.
                    </audio>
                """ %audio_str

    audio_placeholder.empty()
    time.sleep(0.5)
    audio_placeholder.markdown(audio_html, unsafe_allow_html=True)

def erase(filename):
    if(os.path.isfile(filename)):
        os.remove(filename)

# 録音プロセス始動
api_warning = st.empty()
while not openai_api_key:
    api_warning.warning('OpenAI API Keyを設定してください')

audio_bytes = audio_recorder(pause_threshold=30)
    
# Convert audio to text using OpenAI Whisper API
if audio_bytes:
    # 録音
    api_warning.empty()

    lang_input = int(lang_output)
    textbg = str()
    if(mode == 0):
        lang_input = 1 - int(lang_output)   # 翻訳モードの場合、入力言語と出力言語は異なる
    with st.spinner('処理中...'):
        text = speech_to_text(audio_bytes, language=lang_code.get(lang_input))
        st.write(text)

        # 変換
        textbg = process(task=mode_english.get(mode), lang=lang_english.get(lang_output), content=text, model=str(model_select))
        st.write(textbg)

    with NamedTemporaryFile(delete=True, suffix=".wav") as temp_file:
        text_to_speech(textbg, temp_file.name)
        # 再生
        playaudio(temp_file.name)
