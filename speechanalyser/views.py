from django.http import JsonResponse
from google.cloud import storage, speech_v1p1beta1 as speech
from django.views.decorators.csrf import csrf_exempt
from pydub import AudioSegment
import logging
import io

logger = logging.getLogger(__name__)

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
