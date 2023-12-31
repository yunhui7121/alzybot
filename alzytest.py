import streamlit as st
import os
from langchain import HuggingFaceHub
from langchain.chains import ConversationChain
from langchain.chains.conversation.memory import ConversationBufferMemory
from streamlit_chat import message
import azure.cognitiveservices.speech as speechsdk
import json
import speech_recognition as sr
from gtts import gTTS
from hugchat import hugchat
from dotenv import load_dotenv  # Added to load environment variables

# Load environment variables from the secrets.env file (if present)
load_dotenv(dotenv_path="secrets.env")

# Initialize HuggingFaceHub directly with the repo_id
llm = HuggingFaceHub(
    repo_id="google/flan-t5-xl",
    model_kwargs={"temperature": 1e-10}
) # type: ignore

# Access the variables using environment variables
huggingface_api_token = os.getenv("HUGGINGFACE_API_TOKEN")
speech_api_key = os.getenv("SPEECH_API_KEY")
speech_endpoint = os.getenv("SPEECH_ENDPOINT")

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

# Voice recording button
record_button = st.button("Record Voice")

# Speech-to-text function using Azure Speech SDK
def recognize_speech():
    r = sr.Recognizer()

    with sr.Microphone() as source:
        st.write("Speak something...")
        audio = r.listen(source)
        st.write("Recognizing...")

    try:
        user_input = r.recognize_google(audio, language="en-US")
        return user_input
    except sr.UnknownValueError:
        return "Sorry, I couldn't understand what you said."
    except sr.RequestError:
        return "Sorry, there was an issue with the speech recognition service."

# User input
def get_input():
    if record_button:
        user_input = recognize_speech()
    else:
        user_input = st.text_input("You: ", "", key="input")
    return user_input

# Declare tts_filename at the beginning
tts_filename = None

# Inside the response output section
with input_container:
    user_input = get_input()

# Generate AI response based on conversation history
def generate_response(conversation_history):
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

     # Remove the "endoftext" token from the response
    response = response.replace("<|endoftext|>", "")

    return response

# Save conversation history
def save_conversation_history(conversation_history):
    with open("conversation_history.json", "w") as file:
        json.dump(conversation_history, file)

if user_input:
    # Store user input in conversation history
    st.session_state.conversation_history.append({'role': 'user', 'text': user_input})

    # Generate and store bot response
    response = generate_response(st.session_state.conversation_history)
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


