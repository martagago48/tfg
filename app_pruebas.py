import streamlit as st
import speech_recognition as sr
import pyttsx3
from PIL import Image
from langchain_community.callbacks import StreamlitCallbackHandler
from langchain_core.runnables import RunnableConfig

from src import CFG
from src.embeddings import build_base_embeddings
from src.llms import build_llm
from src.reranker import build_reranker
from src.retrieval_qa import build_retrieval_chain
from src.vectordb import build_vectordb, load_faiss, load_chroma
from streamlit_app.utils import perform
from src.audio_player import AudioManager



st.set_page_config(page_title="Conversational Retrieval QA",layout="wide")

audio_manager = AudioManager()
engine = pyttsx3.init()
r = sr.Recognizer()
c = st.container(height=410,border=False)
c_extra = st.container(height=60,border=False)
ee = c_extra.empty()


if 'texto' not in st.session_state:
    st.session_state['texto'] = ""
if "uploaded_filename" not in st.session_state:
    st.session_state["uploaded_filename"] = ""


def init_chat_history():
    #Initialise chat history.
    clear_button = st.sidebar.button("Clear Conversation", key="clear")
    if clear_button or "chat_history" not in st.session_state:
        st.session_state["chat_history"] = list()
        st.session_state["source_documents"] = list()


@st.cache_resource
def load_retrieval_chain():
    llm = build_llm()
    embeddings = build_base_embeddings()
    reranker = build_reranker()
    if CFG.VECTORDB_TYPE == "faiss":
        vectordb = load_faiss(embeddings)
    elif CFG.VECTORDB_TYPE == "chroma":
        vectordb = load_chroma(embeddings)
    return build_retrieval_chain(vectordb, reranker, llm)

def config_tts(v=0, rate=200,vol=0.7,show_voices_info=False):
    voices = engine.getProperty('voices')
    engine.setProperty('rate', rate)     # setting up new voice rate
    engine.setProperty('volume',vol)   # setting up volume   
    engine.setProperty('voice', voices[v].id) # setting voice 
    
    if show_voices_info:
        i = 0
        for voice in voices:
            print("Number:",i)
            print("Voice:",voice.name)
            print(" - ID:",voice.id)
            print(" - Languages:",voice.languages)
            print(" - Gender:",voice.gender)
            print(" - Age:",voice.age)
            print("\n")
            i+=1


def css_changes():
    script = """<div id = 'chat_outer'></div>"""
    st.markdown(script, unsafe_allow_html=True)
    with c:
        script = """<div id = 'chat_inner'></div>"""
        st.markdown(script, unsafe_allow_html=True)

    chat_c_style = """<style>
    div[data-testid='stVerticalBlock']:has(div#chat_inner):not(:has(div#chat_outer)) { };
    </style>"""
    st.markdown(chat_c_style, unsafe_allow_html=True) 

    #form style
    input_style = """<style>
    div[data-testid="stForm"]{ position:fixed; bottom: 2%; border: 2px; padding: 10px; z-index: 10;}
    </style>"""

    st.markdown(input_style, unsafe_allow_html=True) 


    button_style = """
    <style>.element-container:has(#button-after) + div button {
    position:fixed; bottom: 24px; border: 2px; padding: 10px; z-index: 10;
    }</style>"""
    st.markdown(button_style, unsafe_allow_html=True) 

def grabar_callback():
    with sr.Microphone() as source:
            r.adjust_for_ambient_noise(source)
            with ee:
                with st.spinner('Escuchando lo que dice...'):
                    audio = r.listen(source)
                st.success('Done!')  
    try:
        res = r.recognize_google(audio, language='es-ES')
    except sr.UnknownValueError:
        ee.error("Google Speech Recognition could not understand audio")
    except sr.RequestError as e:
        ee.error("Could not request results from Google Speech Recognition service; {0}".format(e))
    else:    
        st.session_state['texto'] = res

def borrar_callback():
    st.session_state['texto'] = ""


def doc_conv_qa():
    #css_changes() 

    with st.sidebar:
        st.title("Conversational RAG with quantized LLM")
        image = Image.open('./assets/francisco.png')
        st.image(image, caption='Don Francisco de Arobe')
        st.info(
            f"Usa `{CFG.RERANKER_PATH}` reranker y `{CFG.LLM_PATH}` LLM."
        )
        with st.expander("Configuración"):
            mode = st.radio(
            "Modo",
            ["text", "text + tts"],
            index=1,
            captions=["Solo responde usando texto.","Responde tanto con texto como audio."]
            )

    init_chat_history()
    st.sidebar.write("---")
    config_tts()
    #c = st.container(height=410,border=False)
    #c_extra = st.container(height=60,border=False)
    for (question, answer) in st.session_state.chat_history:
        if question != "":
            with c:
                with st.chat_message("user"):
                    st.markdown(question)
                with st.chat_message("assistant"):
                    st.markdown(answer)

    c1,c2 = st.columns([9,1])
    with c2:
        #st.markdown('<span id="button-after"></span>', unsafe_allow_html=True)
        grabar = st.button("Grabar",on_click=grabar_callback)
        borrar = st.button("Borrar",on_click=borrar_callback)
  
    with c1:
        input = st.form("form",clear_on_submit=False,border=True)
        with input:   
            i1,i2 = st.columns([0.88,0.12])  
            #if user_query := st.chat_input("Your query"):
            with i1:
                #user_query = st.text_area("Tu pregunta", label_visibility="collapsed")
                user_query = st.text_area("preg",f"",max_chars=1000, key = 'texto', label_visibility="collapsed")

            with i2:
                submitted = st.form_submit_button("Preguntar")
                if submitted:
                    if user_query == "":
                        ee.error("Por favor introduzca una pregunta.") 
   
                
    if user_query != "" and submitted:
        with c:
            with st.chat_message("user"):
                st.markdown(user_query)
            with st.chat_message("assistant"):
                #if mode == "Texto":
                #if mode == "Texto y audio":
                question = user_query
                answer = "Hola, soy Don Francisco de Arobe. Tengo cerca de sesenta años. Mi familia incluye a mi hijo el capitán don Pedro, de veintiún años, y a mi otro hijo don Domingo, de dieciocho. Nosotros somos descendientes de una mezcla de negro y indígena."
                st.markdown(answer)

                st.session_state.chat_history.append((question, answer))

                if mode == "text + tts":
                    filepath = "./src/tmp/res.wav"
                    engine.save_to_file(answer,filepath)
                    engine.runAndWait()
                    audio_manager.play_audio(filepath, delete_file=True)

            


if __name__ == "__main__":
    doc_conv_qa()