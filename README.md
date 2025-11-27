# Manim Generator Studio

A modern web application for generating and rendering Manim animations using AI.

## Docker Compose Quick Start (Recommended)

The fastest way to get started is using Docker Compose:

```bash
# 1. Clone the repository
git clone <repository-url>
cd manim-generator-studio

# 2. Set up environment variables
cp backend/.env.example backend/.env
cp frontend/.env.example frontend/.env
# Edit .env files with your API keys and configuration

# 3. Start the entire stack with one command
docker compose up --build

# The application will be available at:
# - Frontend: http://localhost:3000
# - Backend API: http://localhost:8000
# - API Docs: http://localhost:8000/docs
```

To run in detached mode:
```bash
docker compose up -d --build
```

To stop all services:
```bash
docker compose down
```

To view logs:
```bash
docker compose logs -f
```

---

## Project Structure

```
manim-generator-studio/
├── backend/          # FastAPI backend with uv
└── frontend/         # Next.js frontend
```

## Quick Start

### Backend Setup

```bash
cd backend

# Option 1: Local development with uv (recommended for development)
./dev.sh setup    # Install dependencies and setup environment
./dev.sh run      # Start development server

# Option 2: Docker (recommended for production)
./dev.sh docker-run   # Build and run with Docker
```

The backend API will be available at `http://localhost:8000`

See [backend/README.md](backend/README.md) for detailed documentation.

### Frontend Setup

```bash
cd frontend

# Install dependencies
pnpm install

# Run development server
pnpm dev
```

The frontend will be available at `http://localhost:3000`

## Requirements

### Docker (Recommended)
- **Docker** version 20.10 or higher
- **Docker Compose** version 2.0 or higher

This is the easiest way to get started! Everything runs in containers with all dependencies pre-configured.

### For Local Development (Advanced)
- **Backend**: [uv](https://docs.astral.sh/uv/) (Python package manager)
- **Frontend**: [pnpm](https://pnpm.io/) or npm
- **System**: ffmpeg, Cairo, Pango, LaTeX (see backend README)

## Environment Variables

Copy the example environment files and fill in your credentials:

```bash
# Backend
cp backend/.env.example backend/.env

# Frontend  
cp frontend/.env.example frontend/.env
```

## Features

- Generate Manim animations from natural language
- AI-powered code generation using Google Gemini
- RAG-based documentation search
- Real-time rendering with quality options
- Cloud storage with Supabase
- Job history and status tracking

## Tech Stack

### Backend
- **Framework**: FastAPI
- **Package Manager**: uv (fast Python package installer)
- **Animation**: Manim Community
- **AI/LLM**: LangChain, Google Gemini, Cohere
- **Vector DB**: Pinecone
- **Storage**: Supabase
- **Containerization**: Docker

### Frontend
- **Framework**: Next.js 14 (App Router)
- **Styling**: Tailwind CSS
- **UI Components**: shadcn/ui
- **State Management**: React Hooks
- **Type Safety**: TypeScript

## Development Scripts

### Backend
```bash
./dev.sh setup         # Initial setup
./dev.sh run           # Start dev server
./dev.sh docker-run    # Docker development
./dev.sh install <pkg> # Add new package
./dev.sh clean         # Clean build artifacts
```

### Frontend
```bash
pnpm dev              # Start dev server
pnpm build            # Build for production
pnpm start            # Start production server
pnpm lint             # Run linter
```

## API Documentation

Once the backend is running:
- Swagger UI: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Submit a pull request

## License

MIT

## Troubleshooting

### Docker Issues

**Port already in use:**
```bash
# Find and stop the process using the port
lsof -ti:3000 | xargs kill -9  # For frontend
lsof -ti:8000 | xargs kill -9  # For backend
```

**Permission denied errors:**
```bash
# On Linux, you may need to run with sudo
sudo docker compose up --build

# Or add your user to the docker group
sudo usermod -aG docker $USER
# Then log out and log back in
```

**Container fails to start:**
```bash
# Check logs for specific service
docker compose logs backend
docker compose logs frontend

# Restart a specific service
docker compose restart backend
```

**Environment variables not loaded:**
- Ensure `.env` files exist in both `backend/` and `frontend/` directories
- Check that `.env` files contain all required variables from `.env.example`
- Restart containers after updating `.env` files

**Build cache issues:**
```bash
# Clear build cache and rebuild
docker compose down
docker compose build --no-cache
docker compose up
```

## Support

For issues and questions, please open a GitHub issue.
