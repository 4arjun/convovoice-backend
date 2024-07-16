from django.http import JsonResponse
from google.cloud import storage, speech_v1p1beta1 as speech
from django.conf import settings
from django.views.decorators.csrf import csrf_exempt
from pydub import AudioSegment
import logging
import io
from openai import OpenAI

client = OpenAI(api_key=settings.OPENAI_API_KEY)
from .models import Conversation
from rest_framework.permissions import IsAuthenticated
from rest_framework.decorators import api_view, permission_classes
from rest_framework import generics, permissions
from .serializers import ConversationSerializer

# Initialize OpenAI client

# Configure logger
logger = logging.getLogger(__name__)

class ConversationListCreate(generics.ListCreateAPIView):
    serializer_class = ConversationSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return Conversation.objects.filter(user=self.request.user)

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)

@csrf_exempt
@api_view(['POST'])
@permission_classes([IsAuthenticated])
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

        # Asynchronous transcription configuration
        operation = client_speech.long_running_recognize(
            config=speech.RecognitionConfig(
                encoding=speech.RecognitionConfig.AudioEncoding.LINEAR16,
                sample_rate_hertz=16000,
                language_code='en-US'
            ),
            audio=speech.RecognitionAudio(uri=audio_uri)
        )

        # Wait for the operation to complete
        response = operation.result()

        # Process the transcription results
        transcripts = [result.alternatives[0].transcript for result in response.results]
        if transcripts:
            user_message = ' '.join(transcripts)

            # Retrieve conversation history from database
            history = Conversation.objects.filter(user=request.user).order_by('timestamp')
            history_messages = [{"role": "user", "content": convo.user_message} for convo in history] + \
                               [{"role": "assistant", "content": convo.assistant_message} for convo in history]

            # Append user message to conversation history
            history_messages.append({"role": "user", "content": user_message})

            # Interact with the OpenAI API with a system message to set a friendly tone
            gpt_response = client.chat.completions.create(model="gpt-4-turbo",
            messages=[
                {"role": "system", "content": "You are a friendly and supportive companion."}
            ] + history_messages)

            # Extract the assistant's response
            assistant_message = gpt_response.choices[0].message.content

            # Save conversation to database
            Conversation.objects.create(user=request.user, user_message=user_message, assistant_message=assistant_message)

            # Return the response as JSON
            return JsonResponse({"user_message": user_message, "assistant_message": assistant_message})

        return JsonResponse({"message": "No transcripts available"}, status=400)

    else:
        return JsonResponse({'error': 'Invalid request method'}, status=405)
