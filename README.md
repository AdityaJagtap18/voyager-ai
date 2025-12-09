#  Voyager AI - Intelligent Travel Planner

![Version](https://img.shields.io/badge/version-1.0.0-blue.svg)
![Python](https://img.shields.io/badge/python-3.11+-green.svg)
![License](https://img.shields.io/badge/license-MIT-orange.svg)

**Voyager AI** is an intelligent travel planning system powered by multi-agent AI architecture. It automatically generates personalized day-by-day itineraries, restaurant recommendations, and accommodation suggestions with real-time routing and distance calculations.

---

##  Table of Contents

- [Overview](#overview)
- [Key Features](#key-features)
- [How It Works](#how-it-works)
- [Installation](#installation)
- [Usage](#usage)
- [Project Architecture](#project-architecture)
- [Budget System](#budget-system)
- [API Requirements](#api-requirements)
- [Configuration](#configuration)
- [Troubleshooting](#troubleshooting)
- [Contributing](#contributing)
- [License](#license)

---

## 🎯 Overview

Voyager AI transforms travel planning from a time-consuming task into an automated, intelligent process. Simply provide your destination, trip duration, preferences, and budget—the AI agents will coordinate to create a complete, optimized travel plan.

### What Makes Voyager AI Special?

- **🤖 Multi-Agent AI System**: Four specialized AI agents work together to plan your perfect trip
- **🗺️ Real Geographic Data**: Integration with OpenRouteService for accurate distances and travel times
- **💰 Indian Pricing Context**: Budget system designed for Indian travelers (₹ INR pricing)
- **🎨 Beautiful Web Interface**: Streamlit-powered UI with visual cards and tabs
- **📱 Dual Interface**: Choose between web interface or command-line tool
- **📥 Export & Save**: Download complete itineraries as JSON files

---

## ✨ Key Features

###  Multi-Agent Intelligence

| Agent | Responsibility | Capabilities |
|-------|---------------|--------------|
| **Research Agent** | Finds attractions | • AI-powered attraction discovery<br>• Matches to trip type<br>• 2-3 attractions per day |
| **Accommodation Agent** | Recommends hotels | • 5 accommodation options<br>• Proximity-based sorting<br>• INR pricing with Indian context |
| **Dining Agent** | Finds restaurants | • 2 meals per day (lunch & dinner)<br>• Dietary preference filtering<br>• Location-based matching |
| **Itinerary Agent** | Creates schedule | • Day-by-day time management<br>• Route optimization<br>• Travel time integration<br>• Meal scheduling |

### 🌟 Advanced Capabilities

✅ **Smart Scheduling**: Automatically schedules activities with start times, durations, and travel buffers
✅ **Route Optimization**: Uses nearest-neighbor algorithm to minimize travel time
✅ **Geocoding & Validation**: Validates all locations are within reasonable distances
✅ **Dining Integration**: Places meals strategically (lunch: 11:30-14:00, dinner: 17:30-20:00)
✅ **Distance Calculations**: Real driving times using OpenRouteService Matrix API
✅ **Budget Awareness**: Tailored recommendations based on budget level
✅ **Multi-Day Support**: Plans trips from 1 to 30 days
✅ **Trip Type Customization**: Historic, Adventure, Relaxation, Foodie, Cultural, Romantic, Nature

---

## 🔄 How It Works

### Multi-Agent Workflow

```mermaid
graph LR
    A[User Input] --> B[Research Agent]
    B --> C[Accommodation Agent]
    C --> D[Dining Agent]
    D --> E[Itinerary Agent]
    E --> F[Complete Travel Plan]
```

**Step-by-Step Process:**

1. **Research Agent** analyzes your destination and trip type, then finds relevant attractions
2. **Accommodation Agent** recommends 5 hotels/hostels with proximity scoring to attractions
3. **Dining Agent** finds restaurants matching your dietary preferences near attractions/hotels
4. **Itinerary Agent** orchestrates everything into a complete schedule with:
   - Optimized attraction order (minimum travel time)
   - Strategic meal placement
   - Real travel times between locations
   - Time buffers and realistic scheduling

---

## 🚀 Installation

### Prerequisites

Before you begin, ensure you have:

- **Python 3.11 or higher** ([Download here](https://www.python.org/downloads/))
- **Git** ([Download here](https://git-scm.com/downloads))
- **OpenAI API Key** (Required for AI agents)
- **OpenRouteService API Key** (Required for geocoding and routing)

### Step 1: Clone the Repository

```bash
git clone https://github.com/AdityaJagtap18/voyager-ai.git
cd voyager-ai
```

### Step 2: Create Virtual Environment

**Windows:**
```bash
python -m venv venv
venv\Scripts\activate
```

**Mac/Linux:**
```bash
python3 -m venv venv
source venv/bin/activate
```

### Step 3: Install Dependencies

```bash
pip install -r requirements.txt
```

This will install all required packages:
- `langchain` & `langgraph` - AI agent orchestration
- `openai` - Language model API
- `streamlit` - Web interface
- `requests` - HTTP client for APIs
- `python-dotenv` - Environment variable management
- And more...

### Step 4: Set Up API Keys

#### Get OpenAI API Key

1. Go to [OpenAI Platform](https://platform.openai.com/api-keys)
2. Sign up or log in
3. Click "Create new secret key"
4. Copy the key (starts with `sk-...`)

#### Get OpenRouteService API Key

1. Go to [OpenRouteService](https://openrouteservice.org/dev/#/signup)
2. Sign up for a free account
3. Go to Dashboard and copy your API key

#### Create .env File

```bash
# Copy the example file
cp .env.example .env
```

**Edit `.env` file:**
```env
# OpenAI Configuration
OPENAI_API_KEY=sk-your-openai-key-here
OPENAI_MODEL=gpt-3.5-turbo
OPENAI_TEMPERATURE=0.7

# OpenRouteService Configuration
ORS_API_KEY=your-ors-key-here
```

### Step 5: Verify Installation

Test the installation:

```bash
# Test CLI interface
python app/main.py

# Test web interface
streamlit run streamlit_app.py
```

---

## 💻 Usage

### Option 1: Web Interface (Recommended)

**Start the Streamlit app:**
```bash
streamlit run streamlit_app.py
```

The app will open in your browser at `http://localhost:8501`

**Using the Web Interface:**

1. **Enter Trip Details** (in the sidebar):
   - 📍 Destination (e.g., "Goa, India" or "Paris, France")
   - 📅 Number of days (1-30)
   - 🎯 Trip type (historic/adventure/relaxation/foodie/cultural/romantic/nature)
   - 💰 Budget level (with Indian pricing)
   - 🍴 Dietary preferences (optional)

2. **Click "🚀 Generate Itinerary"**

3. **View Your Plan** in organized tabs:
   - **📅 Itinerary Tab**: Day-by-day schedule with times and activities
   - **🍽️ Restaurants Tab**: Dining recommendations with details
   - **🏨 Accommodations Tab**: Hotel options with proximity info
   - **📥 Download Tab**: Export as JSON file

### Option 2: Command Line Interface

**Start the CLI:**
```bash
python app/main.py
```

**Follow the prompts:**
```
🌍 VOYAGER - AI Travel Planner (Multi-Agent)
============================================================

📍 Enter destination (e.g., Paris, France): Mumbai, India
📅 Enter number of days (1-30): 3

🎯 Trip Type Options:
   1. Historic
   2. Adventure
   3. Relaxation
   4. Foodie
   5. Cultural
   6. Romantic
   7. Nature

   Select trip type (1-7): 4

💰 Budget Level (Indian pricing):
   1. Budget (₹800-2000/night, ₹150-400/meal)
   2. Mid-range (₹2000-5000/night, ₹400-1000/meal)
   3. Premium (₹5000+/night, ₹1000+/meal)

   Select budget (1-3, or press Enter for Mid-range): 2

🍴 Dietary Preferences (optional):
   Enter any restrictions (comma-separated)
   Examples: vegetarian, vegan, gluten-free, halal, kosher
   Or press Enter to skip

   Dietary preferences: vegetarian
```

The system will then:
1. Initialize the multi-agent system
2. Run each agent sequentially
3. Display the complete travel plan
4. Save to `data/itineraries/` folder

---

## 🏗️ Project Architecture

### Directory Structure

```
voyager-ai/
├── app/
│   ├── agents/                      # AI Agent modules
│   │   ├── research_agent.py        # Finds attractions using GPT
│   │   ├── accommodation_agent.py   # Recommends hotels with geocoding
│   │   ├── dining_agent.py          # Finds restaurants with filtering
│   │   └── itinerary_agent.py       # Creates optimized schedules
│   │
│   ├── services/
│   │   └── ors_api.py              # OpenRouteService API wrapper
│   │
│   ├── utils/
│   │   └── logger.py               # Logging utility
│   │
│   ├── config.py                   # Configuration management
│   ├── main.py                     # CLI entry point
│   └── workflow.py                 # LangGraph orchestration
│
├── data/
│   └── itineraries/                # Generated travel plans (JSON)
│
├── streamlit_app.py                # Web interface
├── requirements.txt                # Python dependencies
├── .env.example                    # Environment template
├── .env                            # Your API keys (not in git)
├── .gitignore                      # Git ignore rules
└── README.md                       # This file
```

### Technology Stack

| Category | Technology | Purpose |
|----------|-----------|---------|
| **AI/LLM** | OpenAI GPT-3.5-turbo | Natural language generation |
| **Orchestration** | LangChain & LangGraph | Multi-agent coordination |
| **Geocoding** | OpenRouteService API | Location coordinates & routing |
| **Frontend** | Streamlit | Web interface |
| **Backend** | Python 3.11+ | Core logic |
| **Data Format** | JSON | Itinerary storage |

### Key Components Explained

#### 1. Research Agent (`research_agent.py`)

**Responsibility**: Find attractions based on destination and trip type

**How it works**:
- Takes destination, trip type, and duration as input
- Calculates number of attractions needed (2-3 per day)
- Uses GPT-3.5 to generate relevant attractions
- Returns list with: name, description, category, duration, best time to visit

**Example Output**:
```json
{
  "name": "Gateway of India",
  "description": "Iconic arch monument overlooking the Arabian Sea",
  "category": "historic site",
  "duration": "1-2 hours",
  "best_time": "morning"
}
```

#### 2. Accommodation Agent (`accommodation_agent.py`)

**Responsibility**: Recommend hotels near attractions with proximity scoring

**How it works**:
- Gets 5 diverse accommodation options from GPT (with Indian pricing)
- Geocodes each accommodation using OpenRouteService
- Calculates average distance to all attractions
- Sorts by proximity (closest first)

**Key Features**:
- Distance matrix calculations
- Proximity scoring
- Budget-appropriate recommendations
- INR pricing with Indian context

#### 3. Dining Agent (`dining_agent.py`)

**Responsibility**: Find restaurants matching preferences and location

**How it works**:
- Calculates meals needed (2 per day: lunch & dinner)
- Gets restaurant recommendations from GPT (with dietary filters)
- Geocodes restaurants
- Filters restaurants within 50km of accommodation
- Matches restaurants to nearest attractions

**Key Features**:
- Dietary preference filtering (vegetarian, vegan, gluten-free, etc.)
- Location-based matching
- 50km radius filtering
- Meal type assignment (breakfast/lunch/dinner)

#### 4. Itinerary Agent (`itinerary_agent.py`)

**Responsibility**: Orchestrate everything into an optimized schedule

**How it works**:
1. **Geocodes & Validates**: Ensures all attractions are within reasonable distance
2. **Optimizes Route**: Uses nearest-neighbor algorithm for minimum travel time
3. **Schedules Activities**: Assigns start times with durations and buffers
4. **Integrates Dining**: Places meals at appropriate times near current location
5. **Calculates Travel**: Uses OpenRouteService for real driving times

**Scheduling Logic**:
- Day starts at 9:00 AM
- 15-minute buffer between activities
- Lunch window: 11:30 AM - 2:00 PM
- Dinner window: 5:30 PM - 8:00 PM
- Meals placed near current location

#### 5. Workflow Orchestrator (`workflow.py`)

**Responsibility**: Coordinate all agents using LangGraph

**Execution Flow**:
```
Initialize → Research → Accommodation → Dining → Itinerary → Complete
```

Uses **LangGraph StateGraph** to maintain shared state across agents.

---

## 💰 Budget System

Voyager AI uses an **Indian pricing context** designed for Indian travelers:

### Accommodation Budget Guide

| Budget Level | Price Range (per night) | Accommodation Type |
|-------------|------------------------|-------------------|
| **Budget** | ₹800 - ₹2,000 | Backpacker hostels, budget hotels |
| **Mid-range** | ₹2,000 - ₹5,000 | Comfortable hotels, good amenities |
| **Premium** | ₹5,000+ | Luxury hotels, resorts, heritage properties |

### Restaurant Budget Guide

| Budget Level | Price Range (per person) | Dining Type |
|-------------|-------------------------|------------|
| **Budget (₹)** | ₹150 - ₹400 | Street food, dhabas, casual eateries |
| **Mid-range (₹₹)** | ₹400 - ₹1,000 | Good restaurants, cafes |
| **Premium (₹₹₹)** | ₹1,000+ | Fine dining, upscale restaurants |

### Why Indian Pricing?

- Reflects actual Indian travel budgets
- Uses rupee (₹) symbol throughout
- Considers value-for-money mindset
- Appropriate for both domestic and international travel from India

---

##  API Requirements

### OpenAI API

**Purpose**: Powers all AI agents for generating attractions, restaurants, and hotels

**Pricing** (as of 2024):
- GPT-3.5-turbo: ~$0.002 per 1K tokens
- Typical trip plan: 5,000-10,000 tokens
- **Cost per plan**: ~$0.01 - $0.02 USD (₹1-2)

**Rate Limits**:
- Free tier: 3 requests/minute
- Paid tier: Higher limits

**Get API Key**: [OpenAI Platform](https://platform.openai.com/api-keys)

### OpenRouteService API

**Purpose**: Geocoding and route distance calculations

**Free Tier**:
- 2,000 requests/day
- 40 requests/minute
- More than enough for personal use

**Get API Key**: [OpenRouteService](https://openrouteservice.org/dev/#/signup)

---

## ⚙️ Configuration

### Environment Variables

Edit `.env` file:

```env
# ==========================================
# OpenAI Configuration
# ==========================================
OPENAI_API_KEY=sk-proj-xxxxxxxxxxxxx
OPENAI_MODEL=gpt-3.5-turbo              # or gpt-4 for better quality
OPENAI_TEMPERATURE=0.7                  # 0.0-1.0 (creativity level)

# ==========================================
# OpenRouteService Configuration
# ==========================================
ORS_API_KEY=5b3ce3597851110001cf6248xxxxxxxxxxxxx

# ==========================================
# Agent Settings (optional)
# ==========================================
AGENT_TIMEOUT=300                       # Timeout in seconds
MAX_RETRIES=3                          # Retry attempts
```

### Model Selection

**GPT-3.5-turbo (Default)**:
- ✅ Fast response time
- ✅ Very affordable
- ✅ Good quality for travel planning
- 💰 ~₹1-2 per trip plan

**GPT-4**:
- ✅ Higher quality responses
- ✅ Better reasoning
- ❌ Slower
- 💰 ~₹20-30 per trip plan

Change in `.env`:
```env
OPENAI_MODEL=gpt-4
```

---

## 🐛 Troubleshooting

### Common Issues & Solutions

#### Issue 1: "ModuleNotFoundError"

**Error**:
```
ModuleNotFoundError: No module named 'langchain'
```

**Solution**:
```bash
# Make sure virtual environment is activated
source venv/bin/activate  # Mac/Linux
venv\Scripts\activate     # Windows

# Reinstall dependencies
pip install -r requirements.txt
```

#### Issue 2: "OPENAI_API_KEY not found"

**Error**:
```
Error: OPENAI_API_KEY not found in environment
```

**Solution**:
1. Check `.env` file exists in project root
2. Verify API key is correctly set:
   ```env
   OPENAI_API_KEY=sk-your-actual-key-here
   ```
3. Make sure there are no spaces around `=`
4. Restart your terminal/IDE

#### Issue 3: "Rate limit exceeded"

**Error**:
```
RateLimitError: Rate limit reached for requests
```

**Solution**:
- Free tier OpenAI has 3 requests/minute limit
- Wait 60 seconds between requests
- Or upgrade to paid tier

#### Issue 4: "Geocoding failed"

**Error**:
```
Warning: Could not geocode: Hotel XYZ
```

**Solution**:
- This is usually non-critical (system continues)
- Happens when location names are too vague
- AI will retry with fallback queries
- If persistent, check ORS API key is valid

#### Issue 5: Streamlit won't start

**Error**:
```
streamlit: command not found
```

**Solution**:
```bash
# Reinstall streamlit
pip install streamlit

# Or if using system Python
pip3 install streamlit
```

#### Issue 6: Python version too old

**Error**:
```
SyntaxError: invalid syntax
```

**Solution**:
```bash
# Check Python version
python --version

# Must be 3.11 or higher
# Install latest Python from: https://www.python.org/downloads/
```

---

## 📊 Sample Output

### Example: 3-Day Foodie Trip to Mumbai

**Input:**
- Destination: Mumbai, India
- Days: 3
- Trip Type: Foodie
- Budget: Mid-range
- Dietary: Vegetarian

**Output Structure:**

```
📅 DAY 1: Street Food Paradise
   ⏰ 09:00 AM - Chowpatty Beach
      📍 Beach • ⏱️ 2 hours
      Famous for Mumbai street food scene

   ⏰ 11:30 AM - Lunch at Sardar Pav Bhaji
      🍽️ Vegetarian • ₹₹ • Must try: Pav Bhaji
      📍 Near Chowpatty

   ⏰ 02:00 PM - Crawford Market
      📍 Market • ⏱️ 2-3 hours
      Historic market with local food stalls
      🚗 15 min drive from restaurant

   ⏰ 06:00 PM - Dinner at Soam
      🍽️ Gujarati Thali • ₹₹ • Fine dining
      📍 Mahalaxmi area
```

**Accommodation Options:**
```
1. Hotel Suba Palace
   🏷️ Hotel • Modern
   📍 Colaba, Mumbai
   Avg distance to attractions: 3.5km
   💰 ₹3,500 per night
   ⭐ Rating: 4.2/5
```

---

## 🤝 Contributing

We welcome contributions! Here's how you can help:

### Ways to Contribute

1. **Report Bugs**: Open an issue on GitHub
2. **Suggest Features**: Share your ideas in discussions
3. **Submit PRs**: Fix bugs or add features
4. **Improve Documentation**: Help make the README better
5. **Share Feedback**: Let us know how you're using Voyager AI

### Development Workflow

```bash
# 1. Fork the repository on GitHub

# 2. Clone your fork
git clone https://github.com/YOUR_USERNAME/voyager-ai.git
cd voyager-ai

# 3. Create a feature branch
git checkout -b feature/your-feature-name

# 4. Make your changes
# ... edit files ...

# 5. Test your changes
python app/main.py
streamlit run streamlit_app.py

# 6. Commit with descriptive message
git add .
git commit -m "feat: add support for multi-city trips"

# 7. Push to your fork
git push origin feature/your-feature-name

# 8. Create Pull Request on GitHub
```

### Coding Guidelines

- Follow PEP 8 style guide
- Add docstrings to functions
- Test your changes before submitting
- Keep commits focused and atomic


---

### Project Maintainer

**Aditya Jagtap**
- GitHub: [@AdityaJagtap18](https://github.com/AdityaJagtap18)

---

## 🎉 Acknowledgments

Built with:
- [LangChain](https://www.langchain.com/) - AI orchestration framework
- [OpenAI](https://openai.com/) - Language models
- [OpenRouteService](https://openrouteservice.org/) - Geocoding and routing
- [Streamlit](https://streamlit.io/) - Web interface
- All the amazing open-source contributors!

---

<div align="center">



</div>
