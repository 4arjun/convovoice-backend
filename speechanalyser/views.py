from django.http import JsonResponse
from google.cloud import storage, speech_v1p1beta1 as speech
from django.conf import settings
from django.views.decorators.csrf import csrf_exempt
from pydub import AudioSegment
import logging
import io
from openai import OpenAI

client = OpenAI(api_key=settings.OPENAI_API_KEY)

# Initialize OpenAI client

# Configure logger
logger = logging.getLogger(__name__)

@csrf_exempt
def transcribe_and_respond(request):
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
            if transcripts:
                user_message = transcripts[0]

                # Interact with the OpenAI API
                gpt_response = client.chat.completions.create(model="gpt-3.5-turbo",  # or "gpt-4" if you have access
                messages=[
                    {"role": "system", "content": "You are a friendly and supportive companion."},
                    {"role": "user", "content": user_message}
                ])

                # Extract the assistant's response
                assistant_message = gpt_response.choices[0].message.content

                # Return the response as JSON
                return JsonResponse({"user_message": user_message, "assistant_message": assistant_message})

            return JsonResponse({"message": "No transcripts available"}, status=400)

        except Exception as e:
            logger.error(f'Error during transcription or OpenAI interaction: {e}')
            return JsonResponse({'error': 'Error during transcription or OpenAI interaction'}, status=500)
    else:
        return JsonResponse({'error': 'Invalid request method'}, status=405)
