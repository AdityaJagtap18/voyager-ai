# 🐳 Docker Setup Guide for Voyager AI

This guide explains how to run Voyager AI using Docker containers.

---

## 📋 Prerequisites

- **Docker** installed ([Get Docker](https://docs.docker.com/get-docker/))
- **Docker Compose** installed (included with Docker Desktop)
- **API Keys** (OpenAI and OpenRouteService)

---

## 🚀 Quick Start with Docker

### Option 1: Using Docker Compose (Recommended)

**Step 1: Set up environment variables**

```bash
# Copy the example .env file
cp .env.example .env

# Edit .env and add your API keys
nano .env  # or use any text editor
```

Add your keys to `.env`:
```env
OPENAI_API_KEY=sk-your-openai-key-here
OPENAI_MODEL=gpt-3.5-turbo
OPENAI_TEMPERATURE=0.7
ORS_API_KEY=your-ors-key-here
```

**Step 2: Build and run with Docker Compose**

```bash
# Build and start the container
docker-compose up -d

# Check if it's running
docker-compose ps

# View logs
docker-compose logs -f
```

**Step 3: Access the application**

Open your browser and go to: **http://localhost:8501**

**Step 4: Stop the container**

```bash
# Stop the container
docker-compose down

# Stop and remove volumes
docker-compose down -v
```

---

### Option 2: Using Docker CLI

**Step 1: Build the Docker image**

```bash
docker build -t voyager-ai:latest .
```

**Step 2: Run the container**

```bash
docker run -d \
  --name voyager-ai \
  -p 8501:8501 \
  -e OPENAI_API_KEY=sk-your-key-here \
  -e ORS_API_KEY=your-ors-key-here \
  -v $(pwd)/data:/app/data \
  voyager-ai:latest
```

**Step 3: Access the application**

Open your browser and go to: **http://localhost:8501**

**Step 4: View logs**

```bash
docker logs -f voyager-ai
```

**Step 5: Stop the container**

```bash
docker stop voyager-ai
docker rm voyager-ai
```

---

## 🛠️ Docker Commands Cheat Sheet

### Building

```bash
# Build the image
docker build -t voyager-ai:latest .

# Build without cache (fresh build)
docker build --no-cache -t voyager-ai:latest .

# Build with Docker Compose
docker-compose build
```

### Running

```bash
# Run in background (detached mode)
docker-compose up -d

# Run in foreground (see logs)
docker-compose up

# Run specific service
docker-compose up voyager-ai
```

### Managing Containers

```bash
# List running containers
docker ps

# List all containers (including stopped)
docker ps -a

# Stop container
docker-compose down

# Restart container
docker-compose restart

# Remove container
docker-compose down -v
```

### Logs and Debugging

```bash
# View logs
docker-compose logs

# Follow logs in real-time
docker-compose logs -f

# View last 100 lines
docker-compose logs --tail=100

# Execute command in running container
docker-compose exec voyager-ai /bin/bash

# Check container health
docker inspect voyager-ai | grep Health
```

### Cleaning Up

```bash
# Remove stopped containers
docker container prune

# Remove unused images
docker image prune

# Remove all unused data (containers, images, volumes, networks)
docker system prune -a
```

---

## 📦 Docker Image Details

### Image Layers

The Dockerfile uses a **multi-stage build** for optimization:

1. **Base stage**: Sets up Python 3.11 environment
2. **Dependencies stage**: Installs system and Python packages
3. **Runtime stage**: Copies only necessary files and packages

### Image Size

- **Expected size**: ~800-1000 MB
- Optimizations:
  - Multi-stage build
  - Slim Python base image
  - .dockerignore to exclude unnecessary files
  - No cache directories

### Exposed Ports

- **8501**: Streamlit web interface

### Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `OPENAI_API_KEY` | OpenAI API key | Required |
| `ORS_API_KEY` | OpenRouteService API key | Required |
| `OPENAI_MODEL` | LLM model to use | `gpt-3.5-turbo` |
| `OPENAI_TEMPERATURE` | Creativity level (0-1) | `0.7` |

---

## 🔧 Development with Docker

### Hot Reload (Development Mode)

Uncomment the volume mounts in `docker-compose.yml`:

```yaml
volumes:
  - ./data:/app/data
  - ./app:/app/app              # Uncomment for hot reload
  - ./streamlit_app.py:/app/streamlit_app.py  # Uncomment for hot reload
```

Then restart:
```bash
docker-compose down
docker-compose up -d
```

Now your local changes will reflect in the container immediately!

### Running CLI Interface in Docker

```bash
# Execute Python CLI inside container
docker-compose exec voyager-ai python app/main.py
```

### Accessing Container Shell

```bash
# Bash shell
docker-compose exec voyager-ai /bin/bash

# If bash not available, use sh
docker-compose exec voyager-ai /bin/sh
```

---

## 📊 Data Persistence

### Itinerary Files

Generated itineraries are saved in `/app/data/itineraries/` inside the container.

To persist them on your host machine, the volume mount is configured:
```yaml
volumes:
  - ./data:/app/data
```

This means:
- **Container path**: `/app/data`
- **Host path**: `./data` (in your project directory)

All generated itineraries will be available in your local `data/` folder.

---

## 🌐 Deployment Options

### 1. Deploy to Cloud (AWS, GCP, Azure)

**Using Docker Hub:**

```bash
# Tag your image
docker tag voyager-ai:latest yourusername/voyager-ai:latest

# Push to Docker Hub
docker push yourusername/voyager-ai:latest

# Pull and run on server
docker pull yourusername/voyager-ai:latest
docker run -d -p 8501:8501 --env-file .env yourusername/voyager-ai:latest
```

### 2. Deploy to Railway

```bash
# Install Railway CLI
npm install -g @railway/cli

# Login
railway login

# Initialize project
railway init

# Deploy
railway up
```

### 3. Deploy to Render

1. Connect your GitHub repository
2. Select "Docker" as environment
3. Render will auto-detect the Dockerfile
4. Add environment variables in dashboard
5. Deploy!

### 4. Deploy to DigitalOcean App Platform

1. Connect repository
2. Select "Dockerfile" as source
3. Configure environment variables
4. Deploy

---

## 🔒 Security Best Practices

### 1. Never Commit .env File

The `.gitignore` already excludes it:
```gitignore
.env
```

### 2. Use Docker Secrets (Production)

For production, use Docker secrets instead of environment variables:

```bash
# Create secrets
echo "sk-your-key" | docker secret create openai_key -

# Use in docker-compose
secrets:
  openai_key:
    external: true
```

### 3. Run as Non-Root User

Add to Dockerfile for production:
```dockerfile
RUN useradd -m -u 1000 voyager
USER voyager
```

### 4. Scan for Vulnerabilities

```bash
# Scan image for vulnerabilities
docker scan voyager-ai:latest
```

---

## 🐛 Troubleshooting

### Issue: Container Exits Immediately

**Check logs:**
```bash
docker-compose logs
```

**Common causes:**
- Missing API keys
- Invalid .env file
- Port 8501 already in use

**Solution:**
```bash
# Check if port is in use
lsof -i :8501  # Mac/Linux
netstat -ano | findstr :8501  # Windows

# Use different port
docker run -p 8502:8501 voyager-ai:latest
```

### Issue: "Cannot connect to Docker daemon"

**Solution:**
```bash
# Start Docker service
sudo systemctl start docker  # Linux
# Or start Docker Desktop application
```

### Issue: Build Fails

**Solution:**
```bash
# Clear Docker cache and rebuild
docker builder prune
docker-compose build --no-cache
```

### Issue: Slow Build Time

**Solution:**
- Use `.dockerignore` (already configured)
- Build on a machine with good internet connection
- Use Docker BuildKit:
  ```bash
  DOCKER_BUILDKIT=1 docker build -t voyager-ai:latest .
  ```

---

## 📈 Performance Optimization

### Reduce Image Size

Already optimized with:
- Multi-stage build ✅
- Slim base image ✅
- .dockerignore ✅
- No cache directories ✅

### Improve Build Speed

```bash
# Use BuildKit
export DOCKER_BUILDKIT=1

# Build with BuildKit
docker build -t voyager-ai:latest .
```

### Memory Limits

```yaml
# In docker-compose.yml
services:
  voyager-ai:
    mem_limit: 1g
    mem_reservation: 512m
```

---

## 🎯 Health Checks

The Dockerfile includes a health check:

```dockerfile
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8501/_stcore/health || exit 1
```

**Check health status:**
```bash
docker inspect voyager-ai | grep Health -A 10
```

---

## 📚 Additional Resources

- [Docker Documentation](https://docs.docker.com/)
- [Docker Compose Documentation](https://docs.docker.com/compose/)
- [Streamlit Docker Deployment](https://docs.streamlit.io/knowledge-base/tutorials/deploy/docker)
- [Best Practices for Python in Docker](https://docs.docker.com/language/python/build-images/)

---

## 💡 Tips

1. **Use Docker Compose for local development** - easier to manage
2. **Mount volumes for data persistence** - don't lose your itineraries
3. **Use environment files** - keep secrets separate from code
4. **Monitor logs** - helps debug issues quickly
5. **Clean up regularly** - run `docker system prune` weekly

---

## 🆘 Need Help?

- GitHub Issues: [Report bugs](https://github.com/AdityaJagtap18/voyager-ai/issues)
- Docker Forums: [Docker Community](https://forums.docker.com/)

---

**Happy Dockerizing! 🐳**
