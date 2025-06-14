import streamlit as st
import ollama
import base64
import os
import json
import time
import re
from datetime import datetime

# --- Configuration ---
MODEL_NAME = 'gemma3'
CHAT_SESSIONS_DIR = "chat_sessions"

# --- Helper Functions for File-based History ---

def setup_app():
    """Initializes the app environment, like creating the session directory."""
    os.makedirs(CHAT_SESSIONS_DIR, exist_ok=True)
    # Initialize session state variables if they don't exist
    if "messages" not in st.session_state:
        st.session_state.messages = []
    if "active_chat_id" not in st.session_state:
        st.session_state.active_chat_id = None
    if "response_time" not in st.session_state:
        st.session_state.response_time = None
    if "ollama_model" not in st.session_state:
        st.session_state.ollama_model = MODEL_NAME
    if "staged_image" not in st.session_state:
        st.session_state.staged_image = None
    if "uploader_key" not in st.session_state:
        st.session_state.uploader_key = 0

def get_chat_sessions():
    """Returns a sorted list of chat session files."""
    files = [f for f in os.listdir(CHAT_SESSIONS_DIR) if f.endswith(".json")]
    return sorted(files, key=lambda x: os.path.getmtime(os.path.join(CHAT_SESSIONS_DIR, x)), reverse=True)

def load_chat_history(chat_id):
    """Loads the chat history from a JSON file."""
    filepath = os.path.join(CHAT_SESSIONS_DIR, chat_id)
    if os.path.exists(filepath):
        with open(filepath, "r", encoding="utf-8") as f:
            return json.load(f)
    return []

def save_chat_history(chat_id, history):
    """Write a chat history file."""
    filepath = os.path.join(CHAT_SESSIONS_DIR, chat_id)
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(history, f, indent=4)

def delete_chat_history(chat_id):
    """Deletes a chat history file."""
    filepath = os.path.join(CHAT_SESSIONS_DIR, chat_id)
    if os.path.exists(filepath):
        os.remove(filepath)

def format_filename_for_display(filename):
    """Makes the filename more readable for the UI."""
    # Remove .json and replace underscores with spaces
    return filename.replace(".json", "").replace("_", " ").capitalize()

# --- NEW: Function to sanitize the topic for use as a filename ---
def sanitize_filename(topic):
    """Removes illegal characters from a string so it can be a valid filename."""
    # Remove any character that is not a letter, number, space, hyphen, or underscore
    sanitized_topic = re.sub(r'[^\w\s-]', '', topic).strip()
    # Replace spaces with underscores
    sanitized_topic = re.sub(r'\s+', '_', sanitized_topic)
    # Truncate to a reasonable length
    return sanitized_topic[:50] if sanitized_topic else "new_chat"

# --- CORRECTED: Function to generate a topic for the chat ---
def generate_chat_topic(messages):
    """Asks the LLM to generate a short topic for the conversation."""
    # Create a copy of the messages to avoid modifying the original list
    history = messages.copy()
    
    # Add a specific instruction to generate a topic
    history.append({
        "role": "user",
        "content": "Based on our conversation so far, what is a short, descriptive topic for this chat? "
                   "The topic should be less than 10 words. Reply with only the topic itself, and nothing else."
    })
    
    try:
        response = ollama.chat(
            model=st.session_state.ollama_model,
            messages=history
        )
        return response['message']['content']
    except Exception as e:
        st.error(f"Error generating topic: {e}")
        return "Chat" # Fallback topic

# --- Main Streamlit App ---

def main():
    st.set_page_config(page_title="Wandee AI Pro", page_icon="🤖", layout="wide")
    setup_app()

    # --- Sidebar for Chat Management ---
    with st.sidebar:
        st.title("🤖 Wandee AI Pro")
        st.write("---")

        if st.button("➕ New Chat"):
            st.session_state.messages = []
            st.session_state.active_chat_id = None
            if st.session_state.staged_image:
                st.session_state.staged_image = None
                st.session_state.uploader_key += 1
            st.rerun()

        st.header("Chat History")
        chat_sessions = get_chat_sessions()

        if not chat_sessions:
            st.caption("No chat history found.")
        else:
            for session_id in chat_sessions:
                col1, col2 = st.columns([5, 1])
                with col1:
                    if st.button(format_filename_for_display(session_id), key=f"select_{session_id}", use_container_width=True):
                        st.session_state.response_time = None
                        st.session_state.active_chat_id = session_id
                        st.session_state.messages = load_chat_history(session_id)
                        if st.session_state.staged_image:
                            st.session_state.staged_image = None
                            st.session_state.uploader_key += 1
                        st.rerun()
                with col2:
                    if st.button("🗑️", key=f"delete_{session_id}", help=f"Delete chat: {format_filename_for_display(session_id)}"):
                        delete_chat_history(session_id)
                        if st.session_state.active_chat_id == session_id:
                            st.session_state.response_time = None
                            st.session_state.active_chat_id = None
                            st.session_state.messages = []
                            if st.session_state.staged_image:
                                st.session_state.staged_image = None
                                st.session_state.uploader_key += 1
                        st.rerun()

        st.write("---")
        st.header("Image Attachment")        
        image_input = st.file_uploader("Attach an image", type=["jpg", "jpeg", "png", "gif"], key=st.session_state.uploader_key)

        if image_input:
            img_data = image_input.getvalue()
            base64_img = base64.b64encode(img_data).decode('utf-8')
            st.session_state.staged_image = {"b64": base64_img, "bytes": img_data}

        # Display the staged image in the sidebar so the user knows it's ready.
        if st.session_state.staged_image:
            st.write("Image ready to be sent:")
            st.image(st.session_state.staged_image["bytes"], use_container_width=True)

    # --- Main Chat Interface ---
    if st.session_state.active_chat_id:
        st.subheader(f"Topic: {format_filename_for_display(st.session_state.active_chat_id)}")
    else:
        st.subheader("New Chat")
        st.info("A topic will be generated from your first message.")

    # Display chat messages
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            if message["role"] == "user" and "images" in message and message["images"]:
                st.markdown(message["content"])
                b64_img_string = message["images"][0] 
                image_bytes = base64.b64decode(b64_img_string)
                st.image(image_bytes, caption="Attached Image", width=150)
            else:
                st.markdown(message["content"])

    if st.session_state.response_time:
        st.markdown(f"\n\n*<center><small>Last response time: {st.session_state.response_time}s</small></center>*", unsafe_allow_html=True)

    # Handle user input
    if prompt := st.chat_input("What would you like to ask?"):
        image_was_sent = False # Flag to track if an image was part of this message
        # Prepare user message
        user_message = {"role": "user", "content": prompt}

        # --- MODIFICATION 2: USE AND CLEAR STAGED IMAGE ---
        # Check for a staged image and attach it to the message
        if st.session_state.staged_image:
            image_was_sent = True
            user_message["images"] = [st.session_state.staged_image["b64"]]

        st.session_state.messages.append(user_message)

        # Display user message
        with st.chat_message("user"):
            st.markdown(prompt)
            # Display the image that was just sent
            if image_was_sent:
                st.image(st.session_state.staged_image["bytes"], width=150)

        # Get and display assistant response
        with st.chat_message("assistant"):
            with st.spinner("Wandee is thinking...", show_time=True):
                start_time = time.time()
                response = ollama.chat(
                    model=st.session_state.ollama_model,
                    messages=st.session_state.messages
                )
                end_time = time.time()
                st.session_state.response_time = round(end_time - start_time, 1)
                assistant_response = response['message']['content']

        # Append assistant response and save history
        assistant_message = {"role": "assistant", "content": assistant_response}
        st.session_state.messages.append(assistant_message)

        # --- LOGIC FOR NEW CHAT TOPIC GENERATION ---
        # Check if this is the first exchange in a new chat
        if st.session_state.active_chat_id is None:
            topic = generate_chat_topic(st.session_state.messages)
            sanitized_topic = sanitize_filename(topic)
                # Ensure the filename is unique
            new_chat_id = f"{sanitized_topic}.json"
            i = 1
            while os.path.exists(os.path.join(CHAT_SESSIONS_DIR, new_chat_id)):
                new_chat_id = f"{sanitized_topic}_{i}.json"
                i += 1
            st.session_state.active_chat_id = new_chat_id
        
        # Save the history and rerun the app to update the sidebar
        save_chat_history(st.session_state.active_chat_id, st.session_state.messages)

        # --- MODIFICATION: The final step to clear the uploader ---
        if image_was_sent:
            st.session_state.staged_image = None
            st.session_state.uploader_key += 1 # Increment the key

        st.rerun()

if __name__ == "__main__":
    main()
