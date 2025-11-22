# voyager-ai
# Voyager AI - Travel Planner

AI-powered travel planning system using multi-agent architecture.

**Current Version:** 0.1.0 (Prototype)

---

## Quick Start (5 Minutes)

### Prerequisites
- Python 3.11+
- OpenAI API key

### Setup Steps

**1. Clone the Repository**
```bash
git clone https://github.com/yourusername/voyager-ai.git
cd voyager-ai
```

**2. Get OpenAI API Key**
- Go to: https://platform.openai.com/api-keys
- Click "Create new secret key"
- Copy the key (starts with `sk-...`)

**3. Create Virtual Environment**
```bash
# Create virtual environment
python -m venv venv

# Activate it
# Windows:
venv\Scripts\activate

# Mac/Linux:
source venv/bin/activate
```

**4. Install Dependencies**
```bash
pip install -r requirements.txt
```

**5. Create .env File**
```bash
# Copy the example file
cp .env.example .env
```

Open `.env` and add your API key:
```
OPENAI_API_KEY=sk-your-actual-key-here
OPENAI_MODEL=gpt-3.5-turbo
OPENAI_TEMPERATURE=0.7
```

**6. Run the App**
```bash
python app/main.py
```

**7. Use the App**
- Enter destination (e.g., Paris, France)
- Enter number of days (e.g., 5)
- Select trip type (1-7)
- Get AI-generated travel recommendations!

---

## Project Structure

```
voyager-ai/
├── app/
│   ├── agents/              # AI agents
│   │   └── research_agent.py    # Finds attractions (WORKING)
│   ├── utils/
│   │   └── logger.py        # Logging utility
│   ├── config.py            # Settings
│   └── main.py              # Entry point
├── .env.example             # Environment template
├── requirements.txt         # Dependencies
└── README.md
```

---

## Current Features

- ✅ Research Agent (finds attractions using AI)
- ✅ User input system
- ✅ Saves itineraries to JSON files
- ✅ Itinerary Agent - Organize attractions into daily schedule
- ✅ Dining Agent - Restaurant recommendations
- ✅ Accommodation Agent - Hotel suggestions
- ✅ Multi-agent workflow with LangGraph
- ✅ Maps API integration

---

## Development Workflow

**1. Create Feature Branch**
```bash
git checkout -b feature/your-feature-name
```

**2. Make Changes**
Edit files, test locally

**3. Commit Changes**
```bash
git add .
git commit -m "feat: description of changes"
```

**4. Push and Create PR**
```bash
git push origin feature/your-feature-name
```
Then create Pull Request on GitHub

---

## Common Issues

**Issue: "ModuleNotFoundError"**
```bash
# Solution: Install dependencies
pip install -r requirements.txt
```

**Issue: "OPENAI_API_KEY not found"**
```bash
# Solution: Check your .env file exists and has the correct key
# Make sure it's in the root voyager-ai folder
```

**Issue: "python: command not found"**
```bash
# Solution: Install Python 3.11+ from https://www.python.org/downloads/
```

**Issue: Virtual environment not activating**
```bash
# Windows: Make sure you're using the correct command
venv\Scripts\activate

# If PowerShell gives errors, try:
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
```

---

## Tech Stack

- Python 3.11
- LangChain & LangGraph
- OpenAI GPT-3.5-turbo

---

## Important Notes

- ⚠️ Never commit `.env` file to Git (contains API keys!)
- ⚠️ Each team member needs their own OpenAI API key
- ⚠️ Always activate virtual environment before running
- ⚠️ Check `.gitignore` before committing

---

## Useful Commands

```bash
# Activate virtual environment
venv\Scripts\activate  # Windows
source venv/bin/activate  # Mac/Linux

# Run the app
python app/main.py

# Install new package
pip install package-name
pip freeze > requirements.txt  # Update requirements

# Deactivate virtual environment
deactivate
```

---

**Happy Coding! 🚀**
