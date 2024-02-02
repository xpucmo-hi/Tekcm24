import streamlit as st
import base64
import os
import time
import random
from openai._client import OpenAI
from audio_recorder_streamlit import audio_recorder
import google.generativeai as genai
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

@st.cache_resource
def load_gemini(api_key):
    genai.configure(api_key = api_key)
    return genai.GenerativeModel("gemini-pro")

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

def process(prompt: str, model: str) -> str:
    # Gemini使用
    if "gemini" in model:
        response = gemini.generate_content(prompt)
        return response.text
    
    # GPT使用
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
    ss.topic = {0: "文化", 1: "歴史", 2: "地理", 3: "生活", 4: "料理", 5: "音楽", 6: "言語", 7: "アネクドート"}
    ss.topic_english = ['culture', 'history', 'geography', 'life', 'cuisine', 'music', 'language', 'anecdote']
    ss.select_show_text = {0: "非表示", 1: "表示"}
    ss.mode_english = {0: "Translate this content into", 1: "Correct the grammer of this content in", 2: "Answer this question within 2 sentences in", 3: "Correct the grammer, and answer this question within 3 sentences in"}
    ss.model_list = ['gpt-3.5-turbo', 'gemini-pro']
    ss.select_lang_code = ['be', 'bs', 'bg', 'hr', 'cs', 'hu', 'mk', 'pl', 'ro', 'ru', 'sr', 'sk', 'sl', 'tk']
    ss.select_lang_english = ['Belarusian', 'Bosnian', 'Bulgarian', 'Croatian', 'Czech', 'Hungarian', 'Macedonian', 'Polish', 'Romanian', 'Russian', 'Serbian', 'Slovak', 'Slovenian', 'Turkish', 'Ukrainian']
    ss.select_lang_list = ['Беларуская', 'Bosanski', 'Български', 'Hrvatski', 'Čeština', 'Magyar', 'Македонски', 'Polski', 'Română', 'Русский', 'Српски', 'Slovenčina', 'Slovenščina', 'Türkçe', 'Українська']
    ss.selected_lang = 2
    ss.show_text = 1
    ss.ex_sentence = ""
    ss.qa_sentence = ""
    ss.ready_to_record = False
    ss.waiting = False
    ss.correct_answer = ""
    ss.answer = ""
    ss.buttons = ['а', 'б', 'в', 'г']
    ss.lang_selectbox = {i: ss.select_lang_list[i] for i in range(0, len(ss.select_lang_list))}

openai_api_key = os.environ.get("OPENAI_API_KEY")
gemini_api_key = os.environ.get("GEMINI_API_KEY")
with st.sidebar:
    if not openai_api_key:
        openai_api_key = st.text_input("OpenAI API Key", key="api_key", type="password")
    if not gemini_api_key:
        gemini_api_key = st.text_input("Gemini API Key", key="geminiapi_key", type="password")
    model_select = st.selectbox(label='使用モデル', options=ss.model_list, index=1)
    lang_index = st.selectbox(label='学習言語', options=(0,1,2,3,4,5,6,7,8,9,10,11,12,13,14), index=ss.selected_lang, format_func=lambda x: ss.lang_selectbox.get(x))
    ss.show_text = st.radio(label='文章表示', options=(0,1), index=1, horizontal=True, format_func=lambda x: ss.select_show_text.get(x))

if ss.selected_lang != lang_index:
    ss.selected_lang = lang_index
    ss.lang_list[1] = ss.select_lang_list[lang_index]
    ss.lang_code[1] = ss.select_lang_code[lang_index]
    ss.lang_english[1] = ss.select_lang_english[lang_index]
    
client = load_client(openai_api_key)
if gemini_api_key:
    gemini = load_gemini(gemini_api_key)

st.title('Tekcm 24 beta')
tab1, tab2, tab3 = st.tabs(["基本機能", "発音練習", "聴解練習"])

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
            textbg = process(prompt = ss.mode_english.get(mode) + " " + ss.lang_english.get(lang_output) + " " + text, model=str(model_select))
            if ss.show_text == 1:
                st.write(textbg)

            with NamedTemporaryFile(delete=True, suffix=".wav") as temp_file:
                text_to_speech(textbg, temp_file.name)
                # 再生
                playaudio(temp_file.name)
        audio_bytes = None

with tab2:
    length = st.slider("単語数", min_value=1, max_value=10, value = 5)
    if st.button('例文更新'):
        content = 'Give me a random ' + ss.lang_english.get(1) + ' sentence which consists of ' + str(length) + ' words'
        ss.ex_sentence = process(prompt=content, model=str(model_select))
        ss.ready_to_record = True
        audio_bytes = None

        st.write(ss.ex_sentence)
        with NamedTemporaryFile(delete=True, suffix=".wav") as temp_file:
            text_to_speech(ss.ex_sentence, temp_file.name)
            # 再生
            playaudio(temp_file.name)

    if ss.ex_sentence:
        st.write("例文:" + ss.ex_sentence)

    if ss.ready_to_record:
        audio_bytes = audio_recorder(pause_threshold=2)
    if audio_bytes:
        text = speech_to_text(audio_bytes, language=ss.lang_code.get(1))
        st.write("あなた:" + text)
        audio_bytes = None

with tab3:
    selected_topic = st.radio(label='トピック', options=(0,1,2,3,4,5,6,7), index=0, horizontal=True, format_func=lambda x: ss.topic.get(x))
    if st.button('出題'):
        st.write("音声を聴いて質問に答えてください。")
        with st.spinner('準備中...'):
            if selected_topic == 6:
                ss.ex_sentence = ""
                subtopics = ['grammer', 'vocabulary', 'idiom', 'colloquial expression']
                subtopic = subtopics[random.randrange(0, len(subtopics))]
                content = 'Make a four-choise question about ' + ss.lang_english.get(1) + ' ' + subtopic + ' in ' + ss.lang_english.get(1) + ' and add the correct answer to the end of the sentence'
                temp_qa_sentence = process(prompt=content, model=str(model_select))
            elif selected_topic == 0 and random.random() < 0.5:
                ss.ex_sentence = ""
                subtopics = ['culture', 'custom', 'festival', 'traditions']
                subtopic = subtopics[random.randrange(0, len(subtopics))]
                content = 'Make a four-choise question about ' + ss.lang_english.get(1) + ' ' + subtopic + ' in ' + ss.lang_english.get(1) + ' and add the correct answer to the end of the sentence'
                temp_qa_sentence = process(prompt=content, model=str(model_select))
            elif selected_topic == 4 and random.random() < 0.5:
                ss.ex_sentence = ""
                subtopics = ['food', 'spices', 'herbs', 'traditional recipe']
                subtopic = subtopics[random.randrange(0, len(subtopics))]
                content = 'Make a four-choise question about ' + ss.lang_english.get(1) + ' ' + subtopic + ' in ' + ss.lang_english.get(1) + ' and add the correct answer to the end of the sentence'
                temp_qa_sentence = process(prompt=content, model=str(model_select))
            elif selected_topic == 5 and random.random() < 0.8 and lang_index == 2:
                ss.ex_sentence = ""
                subtopics = ['Bulgarian music instrument', 'Bulgarian folk songs', 'Bulgarian pop-folk music']
                subtopic = subtopics[random.randrange(0, len(subtopics))]
                content = 'Make a four-choise question from ' + subtopic + ' in ' + ss.lang_english.get(1) + ' and add the correct answer to the end of the sentence'
                temp_qa_sentence = process(prompt=content, model=str(model_select))
            elif selected_topic == 7 and random.random() < 0.7 and lang_index == 2:
                ss.ex_sentence = ""
                subtopics = ['Gabrovo humour', 'anecdotes from Gabrovo', 'Bulgarian jokes under communism']
                subtopic = subtopics[random.randrange(0, len(subtopics))]
                content = 'Make a four-choise question from ' + subtopic + ' in ' + ss.lang_english.get(1) + ' and add the correct answer to the end of the sentence'
                temp_qa_sentence = process(prompt=content, model=str(model_select))
            else:
                content = 'Make a random ' + ss.lang_english.get(1) + ' sentence which is related to ' + ss.lang_english.get(1) + ' ' + ss.topic_english[selected_topic] + ' within 20 words'
                ss.ex_sentence = process(prompt=content, model=str(model_select))

                content = 'Make a four-choise question from ' + ss.ex_sentence + ' in ' + ss.lang_english.get(1) + ' and add the correct answer to the end of the sentence'
                temp_qa_sentence = process(prompt=content, model=str(model_select))
            split_qa = temp_qa_sentence.rfind('\n')
            ss.qa_sentence = temp_qa_sentence[:split_qa]
            ss.correct_answer = temp_qa_sentence[split_qa:]

        with NamedTemporaryFile(delete=True, suffix=".wav") as temp_file:
            text_to_speech(ss.ex_sentence + " " + ss.qa_sentence, temp_file.name)
            # 再生
            playaudio(temp_file.name)
        ss.waiting = True
        ss.answer = ""

        if 'a' in ss.qa_sentence.lower() and 'b' in ss.qa_sentence.lower() and 'c' in ss.qa_sentence.lower() and 'd' in ss.qa_sentence.lower():
            ss.buttons = ['A', 'B', 'C', 'D']
        else:
            ss.buttons = ['а', 'б', 'в', 'г']

    if ss.waiting:

        st.write('''<style>
        [data-testid="column"] {
            width: calc(25% - 1rem) !important;
            flex: 1 1 calc(25% - 1rem) !important;
            min-width: calc(25% - 1rem) !important;
        }
        </style>''', unsafe_allow_html=True)

        col1, col2, col3, col4 = st.columns([1,1,1,1])
        with col1:
            if st.button(ss.buttons[0]):
                ss.answer = ss.buttons[0]
                ss.waiting = False
        with col2:
            if st.button(ss.buttons[1]):
                ss.answer = ss.buttons[1]
                ss.waiting = False
        with col3:
            if st.button(ss.buttons[2]):
                ss.answer = ss.buttons[2]
                ss.waiting = False
        with col4:
            if st.button(ss.buttons[3]):
                ss.answer = ss.buttons[3]
                ss.waiting = False

    if len(ss.answer) > 0:
        st.write(ss.ex_sentence)
        st.write(ss.qa_sentence)
        correct_mark = ''
        if ss.answer.lower() in ss.correct_answer.lower():
            correct_mark = ' ◯'
        st.write("あなたの答え: " + ss.answer + correct_mark)
        st.write("正答: " + ss.correct_answer)
