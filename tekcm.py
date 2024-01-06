import requests
import streamlit as st
import base64
from base64 import b64encode
from base64 import b64decode
import pathlib
import os
import time
import datetime
import queue
import pydub
import openai
from streamlit_webrtc import WebRtcMode, webrtc_streamer
from openai._client import OpenAI

RECORD = """
  const sleep = time => new Promise(resolve => setTimeout(resolve, time))
  const b2text = blob => new Promise(resolve => {
    const reader = new FileReader()
    reader.onloadend = e => resolve(e.srcElement.result)
    reader.readAsDataURL(blob)
  })
  var record = time => new Promise(async resolve => {
    stream = await navigator.mediaDevices.getUserMedia({ audio: true })
    recorder = new MediaRecorder(stream)
    chunks = []
    recorder.ondataavailable = e => chunks.push(e.data)
    recorder.start()
    await sleep(time)
    recorder.onstop = async ()=>{
      blob = new Blob(chunks)
      text = await b2text(blob)
      resolve(text)
    }
    recorder.stop()
  })
"""


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

#client = OpenAI(api_key = os.environ["OPENAI_API_KEY"])
#openai.api_key = os.environ["OPENAI_API_KEY"]

class WebRTCRecord:
    def __init__(self):
        self.webrtc_ctx = webrtc_streamer(
            key="sendonly-audio",
            mode=WebRtcMode.SENDONLY,
            audio_receiver_size=256,
            rtc_configuration={"iceServers": [{"urls": ["stun:stun.xten.com:3478"]}]},
            media_stream_constraints={
                "audio": True,
            },
        )

        if "audio_buffer" not in st.session_state:
            st.session_state["audio_buffer"] = pydub.AudioSegment.empty()

    def recording(self, filename):
        status_box = st.empty()

        while True:
            if self.webrtc_ctx.audio_receiver:
                try:
                    audio_frames = self.webrtc_ctx.audio_receiver.get_frames(timeout=1)
                except queue.Empty:
                    status_box.warning("No frame arrived.")
                    continue

                status_box.info("録音中...")

                sound_chunk = pydub.AudioSegment.empty()
                for audio_frame in audio_frames:
                    sound = pydub.AudioSegment(
                        data=audio_frame.to_ndarray().tobytes(),
                        sample_width=audio_frame.format.bytes,
                        frame_rate=audio_frame.sample_rate,
                        channels=len(audio_frame.layout.channels),
                    )
                    sound_chunk += sound

                if len(sound_chunk) > 0:
                    st.session_state["audio_buffer"] += sound_chunk
            else:
                break

        audio_buffer = st.session_state["audio_buffer"]

        if not self.webrtc_ctx.state.playing and len(audio_buffer) > 0:
            status_box.empty()
            try:
                audio_buffer.export(filename, format="wav")
            except BaseException:
                st.error("Error while Writing wav to disk")

            # Reset
            st.session_state["audio_buffer"] = pydub.AudioSegment.empty()

st.title('Tekcm 24 beta')
#lang_input = st.radio(label='入力言語', options=(0,1), index=0, horizontal=True, format_func=lambda x: lang_list.get(x))
lang_output = st.radio(label='出力言語', options=(0,1), index=1, horizontal=True, format_func=lambda x: lang_list.get(x))
mode = st.radio(label='何をお望みですか？', options=(0,1,2), index=0, horizontal=True, format_func=lambda x: mode_list.get(x))

def speech_to_text(filename, model='whisper-1', language='ja'):
    with open(filename, "rb") as fr:
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
webrtc_record = WebRTCRecord()

api_warning = st.empty()
if not openai_api_key:
    api_warning.warning('OpenAI API Keyを設定してください')

while True:
    hms = datetime.datetime.today()
    hmsstr = hms.strftime("%Y%m%d%H%M%S")
    input_file = pathlib.Path(hmsstr + '.wav')
    output_filename = hmsstr + '_out.wav'

    while True:
        if openai_api_key:
            break

    # 録音
    webrtc_record.recording(filename=str(input_file))
    while True:
        if input_file.exists():
            api_warning.empty()
            break
    lang_input = int(lang_output)
    if(mode == 0):
        lang_input = 1 - int(lang_output)   # 翻訳モードの場合、入力言語と出力言語は異なる
    with st.spinner('処理中...'):
        text = speech_to_text(filename=str(input_file), language=lang_code.get(lang_input))
        st.write(text)

        # 変換
        textbg = process(task=mode_english.get(mode), lang=lang_english.get(lang_output), content=text, model=str(model_select))
        st.write(textbg)

        text_to_speech(textbg, output_filename)
    # 再生
    playaudio(output_filename)

    erase(str(input_file))
    erase(output_filename)
