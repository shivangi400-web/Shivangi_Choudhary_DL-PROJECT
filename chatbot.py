import speech_recognition as sr
import pyttsx3
from textblob import TextBlob

# ---------------- INITIALIZATION ----------------
engine = pyttsx3.init()
recognizer = sr.Recognizer()

# ---------------- QUESTIONS ----------------
questions = {
    "under18": [
        "How do you feel about your studies?",
        "Do you feel stressed at school?",
        "Are you able to concentrate properly?"
    ],
    "youth": [
        "How has your mood been recently?",
        "Do you feel mentally tired?",
        "Are you facing difficulty focusing?"
    ],
    "adult": [
        "Do you feel stressed in daily life?",
        "Are you feeling low or unmotivated?",
        "Do you feel socially withdrawn?"
    ]
}

# ---------------- SPEAK FUNCTION ----------------
def speak(text):
    engine.say(text)
    engine.runAndWait()

# ---------------- LISTEN FUNCTION ----------------
def listen():
    with sr.Microphone() as source:
        print("🎤 Listening...")
        recognizer.adjust_for_ambient_noise(source, duration=1)
        
        try:
            audio = recognizer.listen(source, timeout=5, phrase_time_limit=8)
            text = recognizer.recognize_google(audio)
            print("🗣️ You said:", text)
            return text
        except sr.WaitTimeoutError:
            print("⏱️ Timeout... try again")
            return ""
        except sr.UnknownValueError:
            print("❌ Could not understand")
            return ""
        except sr.RequestError:
            print("⚠️ Network issue")
            return ""

# ---------------- SENTIMENT ANALYSIS ----------------
def analyze_response(text):
    if text == "":
        return 2  # neutral fallback

    analysis = TextBlob(text)
    polarity = analysis.sentiment.polarity

    # Basic sentiment scoring
    if polarity > 0.2:
        score = 1
    elif polarity >= -0.2:
        score = 2
    else:
        score = 3

    # Keyword boost
    keywords = ["stress", "tired", "sad", "low", "anxious", "depressed"]

    for word in keywords:
        if word in text.lower():
            score += 1
            break

    return score

# ---------------- MAIN CHATBOT ----------------
def run_chatbot(age_group):
    print("\n===== 🎙️ VOICE CHATBOT SESSION =====")

    q_list = questions.get(age_group, [])
    total_score = 0
    valid_answers = 0

    for q in q_list:
        print("\nQ:", q)
        speak(q)

        answer = listen()

        if answer == "":
            print("Skipping question...")
            continue

        score = analyze_response(answer)
        total_score += score
        valid_answers += 1

    if valid_answers == 0:
        avg_score = 2  # fallback
    else:
        avg_score = total_score / valid_answers

    print("\n📊 Chatbot Score:", round(avg_score, 2))
    return avg_score
