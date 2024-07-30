from django.http import JsonResponse
from django.conf import settings
from django.views.decorators.csrf import csrf_exempt
import io
import base64
import requests
from google.cloud import texttospeech
from rest_framework.permissions import IsAuthenticated
from rest_framework.decorators import api_view, permission_classes
from rest_framework import generics, permissions
from .models import Conversation
from .serializers import ConversationSerializer

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
            # Prepare to send audio data to OpenAI Whisper
            headers = {
                'Authorization': f'Bearer {settings.OPENAI_API_KEY}'
            }
            files = {
                'file': ('audio-file.webm', audio_file, 'audio/webm')
            }
            data = {
                'model': 'whisper-1',  # Ensure you specify the correct model
                'language': 'en'
            }

            # Use asynchronous requests for better performance
            response = requests.post(
                'https://api.openai.com/v1/audio/transcriptions',
                headers=headers,
                files=files,
                data=data
            )

            if response.status_code == 200:
                response_json = response.json()
                transcripts = response_json.get('text', '')
                if transcripts:
                    user_message = transcripts

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
                            'model': 'gpt-4o-mini',
                            'messages': [
                                {"role": "system", "content": "You are my girlfriend, providing girlfriend kind responses. Handle personal questions with realistic answers. If asked your name, respond with 'Eva'. For questions about your home, say some place in USA. For other personal questions, provide friendly yet specific answers."
                        }
                            ] + history_messages,
                            'temperature': 1.3,
                        }
                    ).json()

                    # Extract the assistant's response
                    assistant_message = gpt_response['choices'][0]['message']['content']

                    # Google Cloud Text-to-Speech
                    client = texttospeech.TextToSpeechClient()
                    synthesis_input = texttospeech.SynthesisInput(text=assistant_message)

                    voice = texttospeech.VoiceSelectionParams(
                        language_code='en-US',
                        name='en-US-Journey-F',  # Use the specific voice name
                        ssml_gender=texttospeech.SsmlVoiceGender.FEMALE  # Set the appropriate gender
                    )

                    audio_config = texttospeech.AudioConfig(
                    audio_encoding = texttospeech.AudioEncoding.MP3,
                    speaking_rate = 3.7,
                    )

                    response_tts = client.synthesize_speech(
                        input=synthesis_input, voice=voice, audio_config=audio_config
                    )

                    # Encode the audio content to base64 to send it back to the frontend
                    audio_content = base64.b64encode(response_tts.audio_content).decode('utf-8')

                    # Save conversation to database
                    Conversation.objects.create(user=request.user, user_message=user_message, assistant_message=assistant_message)

                    # Return the response as JSON
                    return JsonResponse({
                        "user_message": user_message,
                        "assistant_message": assistant_message,
                        "audio_content": audio_content
                    })

            else:
                return JsonResponse({"message": "Failed to transcribe audio"}, status=response.status_code)

        except Exception as e:
            return JsonResponse({'error': str(e)}, status=500)

    else:
        return JsonResponse({'error': 'Invalid request method'}, status=405)
