# Idea Research Assistant Web App

A web-based frontend for the Idea Research Assistant chatbot, built with Flask and plain HTML/CSS/JS.

## Features

- User authentication (login/register)
- Multi-chat support with persistent history
- File upload capability
- Clean, responsive UI
- Integration with Ollama for AI responses

## Local Development

1. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

2. Ensure Ollama is running locally with the Gemma3 model:
   ```bash
   ollama serve
   ollama pull gemma3
   ```

3. Run the web app:
   ```bash
   python chat.py web
   ```

4. Open http://localhost:5000 in your browser.

## Deployment to Vercel

1. Create a GitHub repository and push this code.

2. Connect Vercel to your GitHub repo.

3. Vercel will automatically deploy using the vercel.json configuration.

**Note:** For web deployment, Ollama needs to be accessible. You may need to:
- Deploy Ollama on a cloud server (e.g., AWS EC2)
- Or modify the code to use a cloud LLM API (e.g., OpenAI)

## Usage

- Register/Login to access the app
- Create new chats or select existing ones
- Upload files if needed for context
- Ask questions about your ideas
- View chat history across sessions

## Security Note

This is a basic implementation. For production, implement proper password hashing, HTTPS, and secure session management.