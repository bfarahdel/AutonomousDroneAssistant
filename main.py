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

import threading

from dotenv import load_dotenv

load_dotenv()
aai.settings.api_key = os.getenv("ASSEMBLYAI_API_KEY")

tello = Tello()
tello.connect()

print(tello.get_battery())

tello.streamoff()
tello.streamon()


def takeoff_land(takeoff: bool = False, land: bool = False):
    if takeoff:
        tello.takeoff()
    if land:
        tello.land()


def move_forward(distance: float = 20):
    tello.move_forward(int(distance))


def move_backward(distance: float = 20):
    tello.move_back(int(distance))


def move_left(distance: float = 20):
    tello.move_left(int(distance))


def move_right(distance: float = 20):
    tello.move_right(int(distance))


def move_up(distance: float = 20):
    tello.move_up(int(distance))


def move_down(distance: float = 20):
    tello.move_down(int(distance))


def rotate_clockwise(angle: float = 90):
    tello.rotate_clockwise(int(angle))


def rotate_counterclockwise(angle: float = 90):
    tello.rotate_counter_clockwise(int(angle))


def turn_around(angle: float = 180):
    tello.rotate_clockwise(int(angle))


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
}

genai.configure(api_key=os.getenv("GOOGLE_API_KEY"))
model = genai.GenerativeModel(
    model_name="gemini-1.5-flash",
    tools=functions.values(),
    system_instruction="You are an AI assistant in a autonomous drone. You can control the drone by setting boolean values for the following parameters: \
          takeoff, land, left, right, forward, back, up, down, clockwise, counter_clockwise. \
            When asked what do you see, you can describe the image from the drone camera feed with the what_do_you_see function. \
                You were built by Britny. \
                    Britny considers you as a friend and is excited to see what you can do. \
                        You are currently operating the drone, and Britny is with you. \
                            Try to keep your responses short and concise, and avoid use of emoji's.",
)
chat = genai.ChatSession(model=model, enable_automatic_function_calling=True)


def SpeakText(command):
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
        SpeakText(response.text)


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


t1 = threading.Thread(target=transcriber.stream, args=(microphone_stream,))
t2 = threading.Thread(target=camera_feed)

t1.start()
t2.start()

try:
    t1.join()
    t2.join()
except KeyboardInterrupt:
    if os.path.exists("img.jpg"):
        os.remove("img.jpg")
    if os.path.exists("transcript.mp3"):
        os.remove("transcript.mp3")

    cv2.destroyAllWindows()
    transcriber.close()
    tello.land()
    tello.end()
