from django.contrib.auth.models import User
from django.http import JsonResponse
from django.conf import settings
from django.views.decorators.csrf import csrf_exempt
import io
import base64
import requests
from google.cloud import texttospeech
from rest_framework.decorators import api_view, permission_classes, authentication_classes
from rest_framework import generics
from .models import Conversation
from .serializers import ConversationSerializer
from rest_framework.permissions import IsAuthenticated
from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework import status
from rest_framework.response import Response
from openai import OpenAI


class ConversationListCreate(generics.ListCreateAPIView):
    serializer_class = ConversationSerializer
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return Conversation.objects.filter(user=self.request.user)

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)

@csrf_exempt
@api_view(['POST'])
def register_user(request):
    username = request.data.get('username')
    password = request.data.get('password')

    if not username or not password:
        return Response({"error": "Username and password are required."}, status=status.HTTP_400_BAD_REQUEST)
    
    if User.objects.filter(username=username).exists():
        return Response({"error": "Username already exists."}, status=status.HTTP_400_BAD_REQUEST)
    
    user = User.objects.create_user(username=username, password=password)
    user.save()
    return Response({"message": "User created successfully."}, status=status.HTTP_201_CREATED)

@csrf_exempt
@api_view(['POST'])
@authentication_classes([JWTAuthentication])
@permission_classes([IsAuthenticated])
def transcribe_and_respond(request):
    if request.method == 'POST':
        audio_file = request.FILES.get('audio')
        if not audio_file:
            return JsonResponse({'error': 'No audio file provided'}, status=400)

        try:
            headers = {
                'Authorization': f'Bearer {settings.OPENAI_API_KEY}'
            }
            files = {
                'file': ('audio-file.webm', audio_file, 'audio/webm')
            }
            data = {
                'model': 'whisper-1',  
                'language': 'en'
            }

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

                    history_messages.append({"role": "user", "content": user_message})

                    gpt_response = requests.post(
                        'https://api.openai.com/v1/chat/completions',
                        headers={
                            'Authorization': f'Bearer {settings.OPENAI_API_KEY}',
                            'Content-Type': 'application/json'
                        },
                        json={
                            'model': 'gpt-4o-mini',
                            "messages": [
                        {
                            "role": "system",
                            "content": "You are a helpful assistant dedicated to helping me improve my English fluency and advance my language skills. Focus on providing responses that use nuanced grammar, advanced vocabulary, and conversational English expressions."
                        },
                  
                    ] + history_messages,
                                        }
                    ).json()

                    assistant_message = gpt_response['choices'][0]['message']['content']

                    # json_key_path = '/Users/arjun/Desktop/djangotest/convovoice/convovoice-428809-9262ecfe894e.json' 

                    # # Google Cloud Text-to-Speech
                    # client = texttospeech.TextToSpeechClient.from_service_account_json(json_key_path)

                    # synthesis_input = texttospeech.SynthesisInput(text=assistant_message)

                    # voice = texttospeech.VoiceSelectionParams(
                    #     language_code='en-US',
                    #     name='en-US-Journey-F',  
                    # )

                    # audio_config = texttospeech.AudioConfig(
                    #     audio_encoding=texttospeech.AudioEncoding.MP3,
                    # )

                    # response_tts = client.synthesize_speech(
                    #     input=synthesis_input, voice=voice, audio_config=audio_config
                    # )
                    
                    # # Encode the audio content to base64 to send it back to the frontend
                    # audio_content = base64.b64encode(response_tts.audio_content).decode('utf-8')
                    client = OpenAI()
                    response = client.audio.speech.create(
                    model="tts-1",
                    voice="nova",
                    input=assistant_message,
                   )
                    audio_content = response.content  # or another method to access the raw bytes
                    encoded_audio_content = base64.b64encode(audio_content).decode('utf-8')

                    Conversation.objects.create(user=request.user, user_message=user_message, assistant_message=assistant_message)

                    return JsonResponse({
                        "user_message": user_message,
                        "assistant_message": assistant_message,
                        "audio_content": encoded_audio_content
                    })
            else:
                return JsonResponse({"message": "Failed to transcribe audio"}, status=response.status_code)

        except Exception as e:
            return JsonResponse({'error': str(e)}, status=500)

    else:
        return JsonResponse({'error': 'Invalid request method'}, status=405)
    

