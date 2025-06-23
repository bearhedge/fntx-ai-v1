# Setting up Gemini API Key for FNTX.ai

To enable the AI chat functionality, you need to set up a Google Gemini API key:

1. **Get a Gemini API Key**:
   - Go to [Google AI Studio](https://makersuite.google.com/app/apikey)
   - Sign in with your Google account
   - Click "Create API Key"
   - Copy the generated API key

2. **Set the API Key**:
   - Edit the file `/home/info/fntx-ai-v1/backend/.env`
   - Replace `your-gemini-api-key-here` with your actual API key:
     ```
     GEMINI_API_KEY=AIzaSy...your-actual-key-here
     ```

3. **Restart the Backend**:
   ```bash
   cd /home/info/fntx-ai-v1/backend
   # Kill the current process
   pkill -f "uvicorn api.main:app"
   # Start it again
   nohup uvicorn api.main:app --host 0.0.0.0 --port 8000 --reload > /tmp/backend.log 2>&1 &
   ```

4. **Verify it's Working**:
   - Try sending a message in the chat
   - You should get intelligent responses instead of "I'm having trouble connecting"

## Alternative: Use OpenAI API

If you prefer to use OpenAI instead of Gemini:

1. Get an OpenAI API key from [platform.openai.com](https://platform.openai.com)
2. Add to `.env`:
   ```
   OPENAI_API_KEY=sk-...your-key-here
   ```

The system will automatically use whichever API key is available.