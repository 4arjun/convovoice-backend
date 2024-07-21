# Language Learner Chat Application

This project is a language learning chat application using Django and the OpenAI GPT-4 turbo API. The application provides a friendly and supportive companion to help users practice and improve their language skills through interactive conversations.

## Features

- **Real-time Chat**: Engage in conversations with an AI-powered assistant.
- **Conversation History**: Maintains context with session-based conversation history.
- **Customizable Responses**: The assistant can be fine-tuned to provide more accurate and helpful feedback.
- **Friendly and Supportive Tone**: The assistant is designed to be a friendly companion, providing encouragement and constructive feedback.
- **Speech-to-Text**: Integrates Google Cloud Speech-to-Text API for converting spoken language into text.
- **Modern Frontend**: Utilizes React with Vite for a fast and efficient frontend development experience.

## Prerequisites

- Python 3.8+
- Django 5.0.6
- OpenAI API Key
- Node.js (for React and Vite)
- Google Cloud Speech-to-Text API Key

## Installation

### Backend Setup

1. **Clone the Repository**
    ```bash
    git clone https://github.com/4arjun/convovoice-frontend.git
    cd convovoice
    ```

2. **Create a Virtual Environment**
    ```bash
    python -m venv convovoice-env
    source convovoice-env/bin/activate  # On Windows, use `convovoice-env\Scripts\activate`
    ```

3. **Install Dependencies**
    ```bash
    pip install -r requirements.txt
    ```

4. **Configure Environment Variables**

    Create a `.env` file in the root directory and add your API keys:
    ```
    OPENAI_API_KEY=your-openai-api-key
    GCP_SPEECH_TO_TEXT_API_KEY=your-google-cloud-api-key
    ```

5. **Apply Database Migrations**
    ```bash
    python manage.py makemigrations
    python manage.py migrate
    ```

6. **Run the Development Server**
    ```bash
    python manage.py runserver
    ```

7. **Access the Application**
    Open your web browser and go to `http://localhost:8000/chat`.

### Frontend Setup

1. **Navigate to the Frontend Directory**
    ```bash
    cd convovoice
    ```

2. **Install Dependencies**
    ```bash
    npm install
    ```

3. **Run the Development Server**
    ```bash
    npm run dev
    ```

4. **Access the Frontend**

    Open your web browser and go to `http://localhost:3000`.

## Project Structure

- `speechanalyser/`: Main Django application directory.
- `speechanalyser/views.py`: Contains the `chat_view` function that handles chat requests.
- `speechanalyser/urls.py`: URL routing for the application.
- `frontend/`: Directory containing the React frontend.
- `requirements.txt`: List of dependencies required by the project.

## Usage

To interact with the chat application, send a GET request to the `/chat` endpoint. The application will return a JSON response with the user message and the assistant's reply.

## Example

```python
def chat_view(request):
    if request.method == "GET":
        # Retrieve conversation history from session or initialize if not present
        history = request.session.get('conversation_history', [])

        # Sample user message
        user_message = "Hello, how are you today?"

        # Append user message to conversation history
        history.append({"role": "user", "content": user_message})

        # Interact with the OpenAI API with a system message to set a friendly tone
        response = openai.ChatCompletion.create(
            model="gpt-4-turbo",
            messages=[
                {"role": "system", "content": "You are a friendly and supportive companion."}
            ] + history
        )

        # Extract the assistant's response
        assistant_message = response.choices[0].message['content']

        # Append assistant message to conversation history
        history.append({"role": "assistant", "content": assistant_message})

        # Save updated history back to session
        request.session['conversation_history'] = history

        # Return the response as JSON
        return JsonResponse({"user_message": user_message, "assistant_message": assistant_message})

    return JsonResponse({"message": "Invalid request method"})
Contributions
Contributions are welcome! Please fork the repository and submit pull requests for any enhancements or bug fixes.

License
This project is licensed under the MIT License. See the LICENSE file for details.

Contact
For any questions or suggestions, please open an issue or contact me at arjunajith440@gmail.com.
