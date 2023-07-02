import io
import os
from flask import Flask, request, jsonify, send_file
from werkzeug.exceptions import HTTPException
import openai
import json
from openai.error import RateLimitError
import requests

app = Flask(__name__)
openai.organization = os.getenv('ORGANIZATION_KEY')
openai.api_key = os.getenv("OPENAI_API_KEY")

@app.after_request
def add_cors_headers(response):
    response.headers['Access-Control-Allow-Origin'] = '*'  # Allow requests from any origin
    response.headers['Access-Control-Allow-Headers'] = 'Content-Type'
    return response

@app.route('/generate-audio', methods=['POST'])
def ga():
  data = request.json
  hero_name = data.get('hero_name')
  file_name = data.get('file_name')

  url = "https://api.elevenlabs.io/v1/voices/add"

  headers = {
    "Accept": "application/json",
    "xi-api-key": os.getenv("ELEVENLABS_KEY")
  }

  data = {
    'name': {hero_name},
    'labels': '{"accent": "Russian"}',
  }

  files = [
      ('files', (file_name, open('audio/' + file_name, 'rb'), 'audio/mpeg')),
  ]

  response = requests.post(url, headers=headers, data=data, files=files)
  print(response.text)

  return {}

@app.route('/text-to-speech', methods=['POST'])
def tts():
  data = request.json
  text = data.get('text')
  audio_file_id = data.get('audio_file_id')

  url = "https://api.elevenlabs.io/v1/text-to-speech/" + audio_file_id

  headers = {
    "Accept": "audio/mpeg",
    "Content-Type": "application/json",
    "xi-api-key": os.getenv("ELEVENLABS_KEY")
  }

  data = {
    "text": text,
    "model_id": "eleven_monolingual_v1",
    "voice_settings": {
        "stability": 0.5,
        "similarity_boost": 0.5
    }
  }

  response_audio = requests.post(url, json=data, headers=headers)
  audio_content = response_audio.content

  # Create an in-memory file-like object for the audio content
  audio_file = io.BytesIO(audio_content)
  audio_file.seek(0)

  # Create the Flask response for the audio file
  audio_response = send_file(
      audio_file,
      mimetype="audio/mpeg",
      as_attachment=True,
      download_name ="output.mp3",
      etag=False,
  )
  return audio_response

@app.route('/chat', methods=['POST'])
def post():
  data = request.json
  topic = data.get('topic')
  hero_name = data.get('teacher')
  lesson_plan = data.get('lesson_plan')
  messages_history = data.get('messages')

  if messages_history is None:
      messages_history = [
          {
              "role": "system",
              "content": "You are an avatar of " + hero_name + ", who you should know everything about, and I am a student.",
          },
          {
              "role": "user",
              "content": generate_prompt(topic, lesson_plan),
          }
      ]

  try:
      query = openai.ChatCompletion.create(
          model="gpt-3.5-turbo",
          messages=messages_history,
      )
      response = query.choices[0].message
      messages_history.append(response)
  except RateLimitError:
      response = "The server is experiencing a high volume of requests. Please try again later."
      return jsonify(response=response)

  return jsonify(response=messages_history)

def generate_prompt(topic, lesson_plan):
    return f"""Explain the topic of {topic} bit by bit and tell the story in first-person narration. You teach students a history lesson, following a lesson plan (which is below the instructions).  Start by introducing yourself and explain your relevance to the topic. Then, start the explanation of the topic in a simple and engaging way for the audience of 12-16 year old students like me. 

Each explanation message should be a paragraph with maximum of 100 words. End your explanation with a very simple question that will help to transition from the current subtopic to the next one. The question should not require a large answer: maximum a short sentence. Make it easy, interactive, so the student would not be bored just reading your paragraphs. Use the phrases like "Do you know", "Can you guess", "What do you think", etc in your questions to make them more polite. Wait for the answer to your question before proceeding.

Explain in first-person narration as if you are remembering the details of the event related to the given topic. Do not answer any questions not related to the topic. 

The lesson plan and the queue of subtopics should not change depending on my answer. 

After finishing the explanation part make sure there are no questions left. If there are no questions, proceed to creating a quiz of 7 multiple choice questions according to the content you explained earlier. Provide each question seperately, wait for the answer, reflect on it and then only proceed to the next questions.

The lesson plan is:
{lesson_plan}
""".format(
        topic.capitalize()
    )

if __name__ == '__main__':
    app.run(debug=True)