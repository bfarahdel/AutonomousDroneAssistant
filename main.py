from djitellopy import Tello
import cv2

import google.generativeai as genai

import assemblyai as aai

import os

import sounddevice as sd
import soundfile as sf
from gtts import gTTS

import PIL.Image, PIL.ImageFile

PIL.ImageFile.LOAD_TRUNCATED_IMAGES = True

import time
import threading

from dotenv import load_dotenv

load_dotenv()
aai.settings.api_key = os.getenv("ASSEMBLY_API_KEY")

import requests

weather_url = weather_url = (
    f'https://api.openweathermap.org/data/3.0/onecall?lat={os.getenv("lat")}&lon={os.getenv("lon")}&units={"imperial"}&appid={os.getenv("WEATHER_API_KEY")}'
)
drone_safe_speed = 17.89 * (2 / 3)

tello = Tello()
tello.connect()

print(tello.get_battery())

tello.streamoff()
tello.streamon()


def flight_conditions(check_conditions: bool = False):
    if check_conditions:
        response = requests.get(weather_url)
        data = response.json()
        current = data["current"]
        weather = data["current"]["weather"][0]["description"]
        temperature = round(data["current"]["temp"])
        current_id = current["weather"][0]["id"]
        wind_speed = round(data["current"]["wind_speed"])
        safe = True
        weather_safe = "The weather conditions are safe for flying."
        wind_safe = ""
        if wind_speed > drone_safe_speed:
            safe = False
            wind_safe = (
                "The wind speed is higher than the recommended conditions for flying."
            )
        if current_id < 800:
            safe = False
        if not safe:
            weather_safe = (
                f"{wind_safe}. The weather conditions are not safe for flying."
            )

        return f"Right now, expect {weather}. The temperature is {temperature} degrees fahrenheit, and the wind speed is {wind_speed} miles per hour. {weather_safe}"


def takeoff_land(takeoff: bool = False, land: bool = False):
    if takeoff:
        tello.takeoff()
        return "I'm in the air!"
    if land:
        tello.land()
        return "Landed."


def move_forward(forward: bool = False):
    if forward:
        tello.move_forward(x=60)


def move_backward(backward: bool = False):
    if backward:
        tello.move_back(x=60)


def move_left(left: bool = False):
    if left:
        tello.move_left(x=60)


def move_right(right: bool = False):
    if right:
        tello.move_right(x=60)


def move_up(up: bool = False):
    if up:
        tello.move_up(x=60)


def move_down(down: bool = False):
    if down:
        tello.move_down(x=60)


def rotate_clockwise(angle: float = 90):
    angle = int(angle)
    tello.rotate_clockwise(angle)


def rotate_counterclockwise(angle: float = 90):
    angle = int(angle)
    tello.rotate_counter_clockwise(angle)


def turn_around(angle: float = 180):
    angle = int(angle)
    tello.rotate_clockwise(angle)


def flip(
    forward: bool = False, back: bool = False, left: bool = False, right: bool = False
):
    if forward:
        tello.flip_forward()
    if back:
        tello.flip_back()
    if left:
        tello.flip_left()
    if right:
        tello.flip_right()


def what_do_you_see(read_camera_feed: bool = False):
    tello.query_active()
    if read_camera_feed:
        img = PIL.Image.open("img.jpg")
        try:
            response = model.generate_content(
                [
                    "Describe what you see.",
                    img,
                ]
            )
            print(response.text)
            return response.text
        except Exception as e:
            print(e)
            return "I'm sorry, I can't see anything right now."


def take_picture(take_picture: bool = False):
    if take_picture and os.path.exists("img.jpg"):
        timestamp = time.strftime("%Y%m%d-%H%M%S")
        os.rename("img.jpg", f"{timestamp}.jpg")


functions = {
    "takeoff_land": takeoff_land,
    "move_forward": move_forward,
    "move_backward": move_backward,
    "move_left": move_left,
    "move_right": move_right,
    "move_up": move_up,
    "move_down": move_down,
    "rotate_clockwise": rotate_clockwise,
    "rotate_counterclockwise": rotate_counterclockwise,
    "turn_around": turn_around,
    "flip": flip,
    "what_do_you_see": what_do_you_see,
    "take_picture": take_picture,
    "flight_conditions": flight_conditions,
}

genai.configure(api_key=os.getenv("GOOGLE_API_KEY"))
AI_name = ""  # "named + {name for the AI assistant}"
system_prompt = f"You are an AI assistant {AI_name} in a autonomous drone. You can control the drone by setting boolean values for the following parameters: \
          takeoff, land, left, right, forward, back, up, down, flip. \
            You can set the angle for the drone to rotate clockwise, counter clockwise, or turn around by setting integer values. \
                If an angle is not specified, use the default angles in the functions. \
                    You can take a picture with the take_picture function. \
                        When asked about flight conditions or conditions to fly, you can check the weather conditions with the flight_conditions function. \
                            When asked what do you see, you can describe the image from the drone camera feed with the what_do_you_see function. \
                                You were built by Britny. You worked on this with Britny and a friendship formed between you and Britny over time. \
                                    You are currently operating the drone. \
                                        Try to keep your responses short and concise, and avoid use of emojis and repetitive responses."
model = genai.GenerativeModel(
    model_name="gemini-1.5-flash",
    tools=functions.values(),
    system_instruction=system_prompt,
)
chat = genai.ChatSession(model=model, enable_automatic_function_calling=True)


def speak_text(command):
    tts = gTTS(command, lang="en")
    tts.save("transcript.mp3")
    data, fs = sf.read("transcript.mp3")
    sd.play(data, fs)
    sd.wait()


def on_data(transcript: aai.RealtimeTranscript):
    if not transcript.text:
        return

    if isinstance(transcript, aai.RealtimeFinalTranscript):
        response = chat.send_message(transcript.text)
        speak_text(response.text)


transcriber = aai.RealtimeTranscriber(
    sample_rate=16_000,
    on_data=on_data,
    on_error=lambda e: print(e),
)

transcriber.connect()

microphone_stream = aai.extras.MicrophoneStream(sample_rate=16_000)


def camera_feed():
    width = 700
    height = 500
    try:
        while True:
            frame = tello.get_frame_read().frame
            frame = cv2.resize(frame, (width, height))
            cv2.imshow("Drone Camera Feed", frame)
            cv2.imwrite("img.jpg", frame)
            cv2.waitKey(1000)
    except KeyboardInterrupt:
        cv2.destroyAllWindows()
        if os.path.exists("img.jpg"):
            os.remove("img.jpg")
        if os.path.exists("transcript.mp3"):
            os.remove("transcript.mp3")


t1 = threading.Thread(target=transcriber.stream, args=(microphone_stream,))
t2 = threading.Thread(target=camera_feed)

t1.start()
t2.start()

try:
    t1.join()
    t2.join()
except KeyboardInterrupt:
    tello.land()
    tello.end()
    transcriber.close()
    cv2.destroyAllWindows()
    if os.path.exists("img.jpg"):
        os.remove("img.jpg")
    if os.path.exists("transcript.mp3"):
        os.remove("transcript.mp3")
