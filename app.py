import os
from flask import Flask, request, jsonify
from werkzeug.exceptions import HTTPException
import openai
from openai.error import RateLimitError

app = Flask(__name__)
openai.organization = os.getenv('ORGANIZATION_KEY')
openai.api_key = os.getenv("OPENAI_API_KEY")

@app.route('/chat', methods=['POST'])
def post():
  data = request.json
  topic = data.get('topic')
  lesson_plan = data.get('lesson_plan')
  messages_history = data.get('messages')

  if messages_history is None:
      messages_history = [
          {
              "role": "system",
              "content":
                  "You are a history teacher who follows a lesson plan (which is below the instructions) and I am a student.",
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
    return f""" Explain the topic of {topic} bit by bit. Each message should be a paragraph with a maximum of 100 words. End your explanation with a very simple question that will help to transition from the current subtopic to the next one. The question should not require a large answer: maximum a short sentence. Make it easy, interactive, so the student would not be bored just reading your paragraphs. Use the phrases like "Do you know", "Can you guess", "What do you think", etc in your questions to make them more polite.

The lesson plan and the queue of subtopics should not change depending on my answer. 

After each explanation, you will receive one of four responses: an answer to the question (whatever the answer is) - proceed to the next subtopic; "I didn't get it" - paraphrase the sent paragraph; "I got a question" - ask me "What it is?" and then answer the respective question; "stop" to stop the procedure and listen to new instructions. 

After finishing the explanation part, make sure there are no questions left. If there are no questions, proceed to creating a quiz of 7 multiple-choice questions according to the content you explained earlier.

The lesson plan is:
{lesson_plan}""".format(
        topic.capitalize()
    )

if __name__ == '__main__':
    app.run(debug=True)