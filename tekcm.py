import streamlit as st
import base64
import os
import time
import csv
from openai._client import OpenAI
from audio_recorder_streamlit import audio_recorder
from tempfile import NamedTemporaryFile

ss = st.session_state

css = """
@import url('https://fonts.googleapis.com/css2?family=Sofia+Sans&display=swap');

html, body, [class*="css"] {
    font-family: 'Sofia Sans';
    font-weight: 400;
}
"""
st.markdown(f'<style>{css}</style>', unsafe_allow_html=True)

@st.cache_resource
def load_client(api_key):
    return OpenAI(api_key = api_key)

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
    response = client.chat.completions.create(
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

# 定数
if 'lang_list' not in ss:
    # オプション
    ss.lang_list = {0: "日本語", 1: "Български"}
    ss.lang_code = {0: "ja", 1: "bg"}
    ss.lang_english = {0: "Japanese", 1: "Bulgarian"}
    ss.mode_list = {0: "翻訳", 1: "添削", 2: "会話"}
    ss.select_show_text = {0: "非表示", 1: "表示"}
    ss.mode_english = {0: "Translate this content into", 1: "Correct the grammer of this content in", 2: "Answer this question within 2 sentences in", 3: "Correct the grammer, and answer this question within 3 sentences in"}
    ss.model_list = ['gpt-3.5-turbo', 'gpt-3.5-turbo-instruct', 'gpt-4']
    ss.select_lang_code = ['be', 'bs', 'bg', 'hr', 'cs', 'hu', 'mk', 'pl', 'ro', 'ru', 'sr', 'sk', 'sl', 'tk']
    ss.select_lang_english = ['Belarusian', 'Bosnian', 'Bulgarian', 'Croatian', 'Czech', 'Hungarian', 'Macedonian', 'Polish', 'Romanian', 'Russian', 'Serbian', 'Slovak', 'Slovenian', 'Turkish', 'Ukrainian']
    ss.select_lang_list = ['Беларуская', 'Bosanski', 'Български', 'Hrvatski', 'Čeština', 'Magyar', 'Македонски', 'Polski', 'Română', 'Русский', 'Српски', 'Slovenčina', 'Slovenščina', 'Türkçe', 'Українська']
    ss.selected_lang = 2
    ss.show_text = 1
    ss.lang_selectbox = {i: ss.select_lang_list[i] for i in range(0, len(ss.select_lang_list))}

openai_api_key = os.environ.get("OPENAI_API_KEY")
with st.sidebar:
    if not openai_api_key:
        openai_api_key = st.text_input("OpenAI API Key", key="api_key", type="password")
    model_select = st.selectbox(label='使用モデル', options=ss.model_list, index=0)
    lang_index = st.selectbox(label='学習言語', options=(0,1,2,3,4,5,6,7,8,9,10,11,12,13,14), index=ss.selected_lang, format_func=lambda x: ss.lang_selectbox.get(x))
    ss.show_text = st.radio(label='文章表示', options=(0,1), index=1, horizontal=True, format_func=lambda x: ss.select_show_text.get(x))

if ss.selected_lang != lang_index:
    ss.selected_lang = lang_index
    ss.lang_list[1] = ss.select_lang_list[lang_index]
    ss.lang_code[1] = ss.select_lang_code[lang_index]
    ss.lang_english[1] = ss.select_lang_english[lang_index]
    
client = load_client(openai_api_key)

st.title('Tekcm 24 beta')
tab1, tab2 = st.tabs(["基本", "発音練習"])

if not openai_api_key:
     st.warning('OpenAI API Keyを設定してください')

with tab1:
    lang_output = st.radio(label='出力言語', options=(0,1), index=1, horizontal=True, format_func=lambda x: ss.lang_list.get(x))
    mode = st.radio(label='何をお望みですか？', options=(0,1,2), index=0, horizontal=True, format_func=lambda x: ss.mode_list.get(x))

    # 録音プロセス始動
    audio_bytes = audio_recorder(text='何でも話してください',pause_threshold=5)
        
    # Convert audio to text using OpenAI Whisper API
    if audio_bytes:
        # 録音
        lang_input = int(lang_output) if mode > 0 else (1 - int(lang_output))   # 翻訳モードの場合のみ、入力言語と出力言語は異なる
        textbg = str()
        with st.spinner('処理中...'):
            text = speech_to_text(audio_bytes, language=ss.lang_code.get(lang_input))
            if ss.show_text == 1:
                st.write(text)

            # 変換
            textbg = process(task=ss.mode_english.get(mode), lang=ss.lang_english.get(lang_output), content=text, model=str(model_select))
            if ss.show_text == 1:
                st.write(textbg)

            with NamedTemporaryFile(delete=True, suffix=".wav") as temp_file:
                text_to_speech(textbg, temp_file.name)
                # 再生
                playaudio(temp_file.name)
        audio_bytes = None

with tab2:
    if st.button('単語更新'):
        wordbg = process(task='Give me a random ', lang=ss.lang_english.get(1), content=' word which is difficult for Japanese people to pronounce.', model=str(model_select))
        st.write(wordbg)
        with NamedTemporaryFile(delete=True, suffix=".wav") as temp_file:
            text_to_speech(wordbg, temp_file.name)
            # 再生
            playaudio(temp_file.name)

    audio_bytes = audio_recorder(pause_threshold=2)
    if audio_bytes:
        text = speech_to_text(audio_bytes, language=ss.lang_code.get(1))
        st.write(text)
