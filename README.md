# Hemut Backend

A FastAPI-based backend service for the Hemut Q&A forum platform, featuring user authentication, question management, and AI-powered suggestions.

## Features

- **RESTful API** with FastAPI
- **User Authentication** with JWT
- **Real-time Updates** via WebSockets
- **AI-Powered Suggestions** using Google's Gemini
- **Database** with Supabase
- **CORS** enabled for frontend communication

## Prerequisites

- Python 3.11+
- pip (Python package manager)
- Supabase account and project
- Google Cloud API key with Generative AI enabled

## Setup

1. Clone the repository:
   ```bash
   git clone https://github.com/sahil-vanarse/hemut-backend.git
   ```

2. Create a virtual environment:
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: .\venv\Scripts\activate
   ```

3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

4. Create a `.env` file in the backend directory:
   ```env
   SUPABASE_URL=your_supabase_url
   SUPABASE_KEY=your_supabase_key
   JWT_SECRET=your_jwt_secret
   GOOGLE_API_KEY=your_google_api_key
   ```

5. Run the development server:
   ```bash
   uvicorn main:app --reload
   ```

The API will be available at `http://localhost:8000`

## API Documentation

After starting the server, visit:
- Interactive API docs: http://localhost:8000/docs
- Alternative API docs: http://localhost:8000/redoc

## Environment Variables

| Variable | Description | Required |
|----------|-------------|----------|
| `SUPABASE_URL` | Your Supabase project URL | Yes |
| `SUPABASE_KEY` | Your Supabase anon/public key | Yes |
| `JWT_SECRET` | Secret key for JWT token signing | Yes |
| `GOOGLE_API_KEY` | API key for Google's Generative AI | Yes |
| `PORT` | Port to run the server (default: 8000) | No |

## Available Endpoints

### Authentication
- `POST /api/register` - Register a new user
- `POST /api/login` - Login and get JWT token

### Questions
- `GET /api/questions` - Get all questions
- `POST /api/questions` - Create a new question
- `PUT /api/questions/{question_id}` - Update a question

### Answers
- `GET /api/answers/{question_id}` - Get answers for a question
- `POST /api/answers` - Post a new answer

### AI Suggestions
- `POST /api/questions/{question_id}/suggest` - Get AI-powered answer suggestion

### WebSocket
- `ws://localhost:8000/ws` - WebSocket endpoint for real-time updates

## Deployment
1. Use Render

### Using Docker

1. Build the Docker image:
   ```bash
   docker build -t hemut-backend .
   ```

2. Run the container:
   ```bash
   docker run -p 8000:8000 --env-file .env hemut-backend
   ```

### Using Gunicorn (Production)

```bash
gunicorn -w 4 -k uvicorn.workers.UvicornWorker main:app
```

## Contributing

1. Fork the repository
2. Create a feature branch
3. Commit your changes
4. Push to the branch
5. Create a new Pull Request

