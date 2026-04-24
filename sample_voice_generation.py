from gtts import gTTS
import os

def text_to_speech(text, filename="output.mp3", language="en", accent="com"):
    try:
        print("🔄 Converting text to speech...")

        tts = gTTS(
            text=text,
            lang=language,
            tld=accent,   # accent control
        )

        tts.save(filename)

        print(f"✅ Audio saved as {filename}")

        # Play the audio (Windows)
        os.system(f"start {filename}")

    except Exception as e:
        print("❌ Error:", e)


if __name__ == "__main__":
    print("=== Text to Speech (Python) ===")

    # User input
    user_text = input("Enter the text you want to convert:\n> ")

    if not user_text.strip():
        user_text = "Hello! This is a default text to speech example using Python."

    # Optional settings
    print("\nChoose accent:")
    print("1. US (default)")
    print("2. UK")
    print("3. India")
    print("4. Australia")

    choice = input("Enter choice (1-4): ")

    accent_map = {
        "1": "com",
        "2": "co.uk",
        "3": "co.in",
        "4": "com.au"
    }

    accent = accent_map.get(choice, "com")
    text_to_speech(user_text, accent=accent)