from django.http import JsonResponse
from django.conf import settings
from django.views.decorators.csrf import csrf_exempt
from pydub import AudioSegment
import logging
import io
import requests
from rest_framework.permissions import IsAuthenticated
from rest_framework.decorators import api_view, permission_classes
from rest_framework import generics, permissions
from .models import Conversation
from .serializers import ConversationSerializer

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

        try:
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

            # Prepare to send audio data to OpenAI Whisper
            headers = {
                'Authorization': f'Bearer {settings.OPENAI_API_KEY}'
            }
            files = {
                'file': ('audio-file.wav', converted_audio, 'audio/wav')
            }
            data = {
                'model': 'whisper-1', # Ensure you specify the correct model
                'language': 'en'   
            }
            response = requests.post(
                'https://api.openai.com/v1/audio/transcriptions',
                headers=headers,
                files=files,
                data=data
            )

            # Log the full response for debugging
            logger.info(f"OpenAI API response status code: {response.status_code}")
            logger.info(f"OpenAI API response text: {response.text}")

            if response.status_code == 200:
                response_json = response.json()
                transcripts = response_json.get('text', '')
                if transcripts:
                    user_message = transcripts

                    # Retrieve conversation history from database
                    history = Conversation.objects.filter(user=request.user).order_by('timestamp')
                    history_messages = [{"role": "user", "content": convo.user_message} for convo in history] + \
                                       [{"role": "assistant", "content": convo.assistant_message} for convo in history]

                    # Append user message to conversation history
                    history_messages.append({"role": "user", "content": user_message})

                    # Interact with the OpenAI API with a system message to set a friendly tone
                    gpt_response = requests.post(
                        'https://api.openai.com/v1/chat/completions',
                        headers={
                            'Authorization': f'Bearer {settings.OPENAI_API_KEY}',
                            'Content-Type': 'application/json'
                        },
                        json={
                            'model': 'gpt-3.5-turbo',
                            'messages': [
                                {"role": "system", "content": "You are a friendly and supportive companion."}
                            ] + history_messages
                        }
                    ).json()

                    # Extract the assistant's response
                    assistant_message = gpt_response['choices'][0]['message']['content']

                    # Save conversation to database
                    Conversation.objects.create(user=request.user, user_message=user_message, assistant_message=assistant_message)

                    # Return the response as JSON
                    return JsonResponse({"user_message": user_message, "assistant_message": assistant_message})

            else:
                # Log any issues with the API request
                logger.error(f"Error from OpenAI API: {response.status_code} - {response.text}")
                return JsonResponse({"message": "Failed to transcribe audio"}, status=response.status_code)

        except Exception as e:
            logger.error(f"Error during transcription: {str(e)}")
            return JsonResponse({'error': str(e)}, status=500)

    else:
        return JsonResponse({'error': 'Invalid request method'}, status=405)
