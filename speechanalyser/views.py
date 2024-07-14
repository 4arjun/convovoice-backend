from django.http import JsonResponse
from google.cloud import storage, speech_v1p1beta1 as speech
from django.conf import settings
from django.views.decorators.csrf import csrf_exempt
from pydub import AudioSegment
from openai import OpenAI
import logging
import io
from openai import OpenAI

client = OpenAI()

client = OpenAI()


client = OpenAI(api_key=settings.OPENAI_API_KEY)


logger = logging.getLogger(__name__)




def chat_view(request):
    if request.method == "GET":
        # Retrieve conversation history from session or initialize if not present
        history = request.session.get('conversation_history', [])

        # Sample user message
        user_message = "yes, last weak i travelled to thailand with my father for a vaction. itwas a wonderful trip. everyone there is so kind and welcoming. we visited a island there called ko lan i twas a great experience with good scenic views"

        # Append user message to conversation history
        history.append({"role": "user", "content": user_message})

        # Interact with the OpenAI API with a system message to set a friendly tone
        response = client.chat.completions.create(model="gpt-3.5-turbo",  # or "gpt-4" if you have access
        messages=[
            {"role": "system", "content": "You are a friendly and supportive companion."}
        ] + history)

        # Extract the assistant's response
        assistant_message = response.choices[0].message.content

        # Append assistant message to conversation history
        history.append({"role": "assistant", "content": assistant_message})

        # Save updated history back to session
        request.session['conversation_history'] = history

        # Return the response as JSON
        return JsonResponse({"user_message": user_message, "assistant_message": assistant_message})

    return JsonResponse({"message": "Invalid request method"})

@csrf_exempt
def upload_and_transcribe(request):
    if request.method == 'POST':
        audio_file = request.FILES.get('audio')
        if not audio_file:
            return JsonResponse({'error': 'No audio file provided'}, status=400)

        # Convert audio to WAV format with a sample rate of 16000 Hz
        audio_content = audio_file.read()
        audio = AudioSegment.from_file(io.BytesIO(audio_content))
        audio = audio.set_frame_rate(16000)
        audio = audio.set_channels(1)
        audio = audio.set_sample_width(2)

        # Save the converted audio to a BytesIO object
        converted_audio = io.BytesIO()
        audio.export(converted_audio, format='wav')
        converted_audio.seek(0)

        # Upload audio file to Google Cloud Storage
        client_storage = storage.Client()
        bucket = client_storage.get_bucket('convovoice')
        file_name = 'audio-file.wav'
        blob = bucket.blob(file_name)
        blob.upload_from_file(converted_audio, content_type='audio/wav')

        # Prepare transcription request
        audio_uri = f'gs://convovoice/{file_name}'
        client_speech = speech.SpeechClient()
        config = speech.RecognitionConfig(
            encoding=speech.RecognitionConfig.AudioEncoding.LINEAR16,
            sample_rate_hertz=16000,
            language_code='en-US'
        )
        audio = speech.RecognitionAudio(uri=audio_uri)

        try:
            response = client_speech.recognize(config=config, audio=audio)
            transcripts = [result.alternatives[0].transcript for result in response.results]
            return JsonResponse({'transcripts': transcripts})
        except Exception as e:
            logger.error(f'Error during transcription: {e}')
            return JsonResponse({'error': 'Error during transcription'}, status=500)
    else:
        return JsonResponse({'error': 'Invalid request method'}, status=405)
