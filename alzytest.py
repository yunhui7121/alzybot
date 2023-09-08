import streamlit as st
import os
from langchain import HuggingFaceHub
from langchain.chains import ConversationChain
from langchain.chains.conversation.memory import ConversationBufferMemory
from streamlit_chat import message
import azure.cognitiveservices.speech as speechsdk
import json
import speech_recognition as sr
from googletrans import Translator
from gtts import gTTS
from hugchat import hugchat
from langchain import HuggingFaceHub
from decouple import config
# Load the secrets from secrets.toml
huggingface_secrets = st.secrets["huggingface"]
speech_secrets = st.secrets["speech"]

# Initialize HuggingFaceHub directly with the repo_id
llm = HuggingFaceHub(
    repo_id="google/flan-t5-xl",
    model_kwargs={"temperature": 1e-10}
) # type: ignore

# Map language names to language codes
language_code_map = {
    "Mandarin": "zh-CN",
    "English": "en",
    "Malay": "ms",
}

# Access the variables
huggingface_api_token = huggingface_secrets["api_token"]
speech_api_key = speech_secrets["api_key"]
speech_endpoint = speech_secrets["endpoint"]

# Create a ConversationChain
conversation = ConversationChain(
    llm=llm,
    verbose=True,
    memory=ConversationBufferMemory()
)

# Define the Streamlit app
st.title("Alzy")
st.write("Your new virtual assistant")

name = st.text_input(label="", placeholder="Enter your name", max_chars=50)

if st.button('Submit'):
    st.write('Hi ' + name + ". How can I assist you today ?")

# Initialize conversation history
if 'conversation_history' not in st.session_state:
    st.session_state.conversation_history = []

# Layout of input/response containers
input_container = st.container()
response_container = st.container()
selected_language = st.selectbox("Select Your Preferred Language", ["Mandarin", "English", "Malay"])

# Voice recording button
record_button = st.button("Record Voice")

# Speech-to-text function using Azure Speech SDK
def recognize_speech(selected_language):
      # Using speech_recognizer within this function
    


    # Initialize the SpeechConfig with your credentials
    speech_config = speechsdk.SpeechConfig(subscription=api_key, endpoint=endpoint) # type: ignore

    # Create a speech recognizer object
    speech_recognizer = speechsdk.SpeechRecognizer(speech_config=speech_config)
    r = sr.Recognizer()


    with sr.Microphone() as source:
        st.write("Speak something...")
        audio = r.listen(source)
        st.write("Recognizing...")

    try:
        if selected_language == "Mandarin":
            user_input = r.recognize_google(audio, language="zh-CN")
        elif selected_language == "Malay":
            user_input = r.recognize_google(audio, language="ms-MY")
        else:
            user_input = r.recognize_google(audio, language="en-US")
        return user_input
    except sr.UnknownValueError:
        return "Sorry, I couldn't understand what you said."
    except sr.RequestError:
        return "Sorry, there was an issue with the speech recognition service."

# User input
def get_input(selected_language):
    if record_button:
        user_input = recognize_speech(selected_language)
    else:
        user_input = st.text_input("You: ", "", key="input")
    return user_input

# Declare tts_filename at the beginning
tts_filename = None

# Inside the response output section
with input_container:
    user_input = get_input(selected_language)

# Generate AI response based on conversation history
def generate_response(conversation_history, selected_language):
    chatbot = hugchat.ChatBot(cookie_path="cookies.json")
    
    # Concatenate user inputs and bot responses to form context
    context = "\n".join(entry['text'] for entry in conversation_history)

    response = chatbot.chat(context)

    # Define a dictionary of avoided phrases and their alternatives
    avoided_phrases_alternatives = {
        "you are wrong": "Let's reconsider that.",
        "remember": "know",
        "dead": "in another world",
        "mistake": "slight problem",
    }

    # Replace avoided phrases with alternatives in the response
    for phrase, alternative in avoided_phrases_alternatives.items():
        if phrase in response: # type: ignore
            response = response.replace(phrase, alternative) #type: ignore

    # Translate the response back to the user's selected language
    translator = Translator()
    
    selected_language_code = language_code_map[selected_language]
    
    translated_response = translator.translate(response, dest=selected_language_code).text # type: ignore

    return translated_response

# Save conversation history
def save_conversation_history(conversation_history):
    with open("conversation_history.json", "w") as file:
        json.dump(conversation_history, file)

if user_input:
    # Store user input in conversation history
    st.session_state.conversation_history.append({'role': 'user', 'text': user_input})

    # Generate and store bot response
    response = generate_response(st.session_state.conversation_history, selected_language)
    st.session_state.conversation_history.append({'role': 'bot', 'text': response})
    save_conversation_history(st.session_state.conversation_history)

    # Convert response to audio and play it
    tts = gTTS(response, lang='en')
    tts_filename = "bot_response.mp3"
    tts.save(tts_filename)
    st.audio(tts_filename, format='audio/mp3')

# Display conversation history
with response_container:
    for i, entry in enumerate(st.session_state.conversation_history):
        role = entry['role']
        text = entry['text']
        message(text, is_user=(role == 'user'), key=str(i))

# Clear conversation history
if st.button("Clear Conversation"):
    st.session_state.conversation_history = []
    save_conversation_history(st.session_state.conversation_history)
    if tts_filename and os.path.exists(tts_filename):
        os.remove(tts_filename)


