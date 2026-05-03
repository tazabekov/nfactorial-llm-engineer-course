# 🎬 Movie Agent

An intelligent movie assistant powered by LangChain and OpenAI that can search for movies, compare them, find movies by actor, and provide personalized recommendations.

> 🎯 **Implementation Variant:** **Variant 1 — Cloud LLM + LangChain** (score multiplier ×1.0). Uses `ChatOpenAI` (gpt-4o-mini), `create_openai_functions_agent`, `AgentExecutor`, and `ConversationSummaryBufferMemory` per the assignment's Variant 1 stack.

> 🇷🇺 **Русская версия документации доступна в [README_RU.md](README_RU.md)**  
> 🇺🇸 **Russian version of documentation is available in [README_RU.md](README_RU.md)**

## 🌟 Features

- **Local Database First**: 1,000+ movies stored locally for instant results
- **API Fallback**: Automatically queries OMDb API for movies not in local database
- **Conversation Memory**: Remembers context and preferences throughout the conversation
- **Multi-tool Orchestration**: Intelligently combines multiple tools to answer complex queries
- **Multilingual Support**: Works with queries in English, Russian, and other languages

## 🚀 Quick Start

### Prerequisites

- **Python 3.13.x** — the assignment pins this version. Python 3.14+ is **incompatible** with the pinned LangChain/Pydantic releases and will fail at import time (`'function' object is not subscriptable`).
- OpenAI API key
- OMDb API key — required by the assignment; also serves as the fallback for movies outside the local Top 1000 dataset.

### Installation

1. **Clone the repository** (or navigate to the project directory)

```bash
cd movie-agent
```

2. **Create and activate virtual environment**

```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. **Install dependencies**

```bash
pip install -r requirements.txt
```

4. **Set up environment variables**

Create a `.env` file in the project root:

```env
OPENAI_API_KEY=your_openai_api_key_here
OMDB_API_KEY=your_omdb_api_key_here
```

To get API keys:
- OpenAI API: https://platform.openai.com/api-keys
- OMDb API: https://www.omdbapi.com/apikey.aspx (free tier — 1,000 requests/day)

### Run the Agent

The agent supports multiple modes of operation:

**Option 1: Interactive Menu** (Default)

```bash
python agent.py
```

This will show a menu where you can choose between:
- Interactive chat mode
- Run predefined examples
- Exit

**Option 2: Interactive Chat Mode**

```bash
python agent.py chat
# or
python agent.py interactive
# or
python agent.py i
```

Start an interactive chat session where you can continuously ask questions about movies. Features:
- Personalized experience - asks for your name and uses it throughout the session
- Natural conversation with memory
- Works with English and Russian
- Clean output (shows only final answers, no intermediate steps)
- Type `exit` or `quit` to end the session
- Type `clear` to reset conversation memory

**Option 3: Run Examples**

```bash
python agent.py examples
# or
python agent.py demo
# or
python agent.py e
```

Runs 6 predefined examples (3 in English, 3 in Russian) demonstrating the agent's capabilities.

**Interactive Chat Example:**

```
What's your name? / Как вас зовут? Гиззат

👋 Nice to meet you, Гиззат! / Приятно познакомиться, Гиззат!

👤 Гиззат: What's the rating of Inception?
🤖 Agent: The rating of **Inception** is **8.8/10** on IMDb.

👤 Гиззат: Compare it with Matrix
🤖 Agent: Inception has a higher rating (8.8 vs 8.7)...

👤 Гиззат: exit
👋 Goodbye, Гиззат! See you next time!
```

**Option 4: Programmatic Usage**

You can also import and use the agent in your own code:

```python
from agent import agent_executor

result = agent_executor.invoke({
    "input": "Find movies with Tom Hanks"
})
print(result["output"])
```

## 🛠️ Available Tools

The agent has access to 6 specialized tools:

### 1. `search_movie(query: str)`
Search for movies by title. Checks local database first, then OMDb API.

**Example:**
```
"Find movies about Batman"
```

### 2. `get_movie_details(title: str)`
Get detailed information about a specific movie including plot, cast, ratings, etc.

**Example:**
```
"Tell me about Inception"
"What's the rating of The Matrix?"
```

### 3. `compare_movies(movie1_title: str, movie2_title: str)`
Compare two movies based on their IMDb ratings and genres.

**Example:**
```
"Compare Inception and The Matrix"
"Which is better: Interstellar or Arrival?"
```

### 4. `search_movies_by_actor(actor_name: str)`
Find all movies featuring a specific actor, sorted by rating.

**Example:**
```
"Find movies with Leonardo DiCaprio"
"Show me Tom Hanks films and their ratings"
```

### 5. `get_top_movies_by_genre(genre: str, limit: int)`
Get top-rated movies in a specific genre.

**Example:**
```
"Show me the best thriller movies"
"What are the top 5 comedies?"
```

### 6. `recommend_movie_by_genre(genre1: str, genre2: str)`
Compare two genres and recommend the best movie for the evening.

**Example:**
```
"Should I watch a comedy or thriller tonight?"
"What's better: action or drama?"
```

## 🧪 Testing Different Features

### Test 1: Basic Functionality

Test the agent's ability to search and retrieve movie information.

#### Test Case 1.1: Movie Details (Local Database)
```
"Расскажи про фильм Inception"
"Tell me about Inception"
```
**Expected behavior:** 
- Uses `get_movie_details` tool
- Returns information from local database (instant)
- Shows rating, genre, director, plot, cast

#### Test Case 1.2: Movie Rating
```
"Какой рейтинг у Matrix?"
"What's the rating of The Matrix?"
```
**Expected behavior:**
- Uses `get_movie_details` tool
- Returns IMDb rating: 8.7/10
- Source: Local Database

#### Test Case 1.3: Search Movies
```
"Найди фильмы про Бэтмена"
"Find movies about Batman"
```
**Expected behavior:**
- Uses `search_movie` tool
- If in local database: returns instantly
- If not in local database: queries OMDb API
- Returns list of Batman-related movies

---

### Test 2: Conversation Memory

Test the agent's ability to remember context and user preferences.

#### Test Case 2.1: Remember User Name
```
1. "Меня зовут Асель" / "My name is Asel"
2. "Как меня зовут?" / "What's my name?"
```
**Expected behavior:**
- Agent remembers the name from conversation history
- Responds: "Your name is Asel" (or similar)

#### Test Case 2.2: Remember Preferences
```
1. "Я люблю фильмы Нолана" / "I love Nolan's movies"
2. "Порекомендуй мне фильм" / "Recommend me a movie"
3. (Continue conversation with 5+ messages)
4. "Что я люблю?" / "What do I love?"
```
**Expected behavior:**
- Agent stores preference in conversation memory
- After multiple messages, still remembers "Nolan's movies"
- May use this information for recommendations

#### Test Case 2.3: Contextual Follow-up
```
1. "Compare Inception and The Matrix"
2. "Which one was released first?"
3. "Who directed it?"
```
**Expected behavior:**
- Understands "which one" refers to previous movies
- Understands "it" refers to the movie mentioned in context
- No need to repeat movie names

---

### Test 3: Multi-Tool Calling

Test the agent's ability to orchestrate multiple tools for complex queries.

#### Test Case 3.1: Compare Two Movies
```
"Сравни Inception и Matrix"
"Compare Inception and The Matrix"
```
**Expected behavior:**
- Calls `compare_movies` tool with both movie titles
- Tool internally fetches data for both movies
- Returns comparison:
  - Inception: 8.8/10 (Action, Adventure, Sci-Fi)
  - The Matrix: 8.7/10 (Action, Sci-Fi)
  - Common genres: Action, Sci-Fi
  - Higher rating: Inception

#### Test Case 3.2: Actor Search + Details
```
"Найди фильмы с Леонардо ДиКаприо и покажи детали самого рейтингового"
"Find Leonardo DiCaprio movies and show details of the highest rated one"
```
**Expected behavior:**
1. Calls `search_movies_by_actor("Leonardo DiCaprio")`
2. Identifies highest rated: Inception (8.8/10)
3. Calls `get_movie_details("Inception")`
4. Returns complete information about Inception

#### Test Case 3.3: Genre Comparison + Recommendation
```
"Какой фильм лучше для вечера: комедия или триллер?"
"Should I watch a comedy or thriller tonight?"
```
**Expected behavior:**
1. May call `get_top_movies_by_genre("Comedy")`
2. May call `get_top_movies_by_genre("Thriller")`
3. Calls `recommend_movie_by_genre("Comedy", "Thriller")`
4. Returns comparison and recommendation with reasoning

---

### Test 4: Advanced Scenarios

#### Test Case 4.1: Complex Multi-Step Query
```
"Find all Christopher Nolan movies, compare the top two, and tell me which one is better for someone who loves sci-fi"
```
**Expected behavior:**
- Searches for Nolan movies (may use director search or multiple movie lookups)
- Identifies top 2 by rating
- Compares them
- Provides personalized recommendation based on sci-fi preference

#### Test Case 4.2: Fallback to API
```
"Tell me about Oppenheimer"  (2023 movie, not in local database)
```
**Expected behavior:**
- Searches local database first
- Not found in local database
- Falls back to OMDb API
- Returns information from API

#### Test Case 4.3: Actor + Genre Filter
```
"Find action movies with Tom Cruise and show their ratings"
```
**Expected behavior:**
- Calls `search_movies_by_actor("Tom Cruise")`
- Filters results for Action genre
- Returns list with ratings

---

## 📊 Project Structure

```
movie-agent/
├── agent.py              # Main agent with example queries
├── tools.py              # Tool definitions and implementations (bilingual)
├── requirements.txt      # Python dependencies
├── .env                  # Environment variables (create this)
├── .gitignore           # Git ignore rules
├── data/
│   └── movies.csv       # Local movie database (1000 movies)
├── README.md            # Documentation (English)
└── README_RU.md         # Documentation (Russian) / Документация (Русский)
```

## 🗃️ Local Database

The local database (`data/movies.csv`) contains 1,000 top-rated movies with:
- Title, Year, Runtime
- IMDb Rating, Genres
- Director, Main Cast (4 actors)
- Plot Overview
- Number of Votes, Box Office

**Benefits:**
- ⚡ Instant results (no API latency)
- 💰 No API costs for common movies
- 🔒 Works offline for local movies

## 🔧 Troubleshooting

### Issue: "ModuleNotFoundError: No module named 'langchain'"
**Solution:** Make sure you've activated the virtual environment and installed dependencies:
```bash
source venv/bin/activate
pip install -r requirements.txt
```

### Issue: "Error: OPENAI_API_KEY not found"
**Solution:** Create a `.env` file in the project root with your API key:
```env
OPENAI_API_KEY=sk-...your-key-here...
```

### Issue: "401 Unauthorized" for OMDb API
**Solution:** 
- Get a free API key from https://www.omdbapi.com/apikey.aspx
- Add it to your `.env` file as `OMDB_API_KEY=your-key`
- Note: The agent works fine for the 1,000 movies in local database without OMDb API

### Issue: Memory warnings about deprecation
**Solution:** This is a warning about future LangChain versions. The functionality still works correctly. The warning can be safely ignored for now.

## 🎯 Example Use Cases

### Use Case 1: Movie Night Planning
```
User: "I want to watch something tonight. I love sci-fi and Christopher Nolan."
Agent: [Searches Nolan movies, filters for sci-fi, recommends Inception or Interstellar]

User: "Tell me more about Interstellar"
Agent: [Provides full details: plot, cast, rating]

User: "Perfect! Add it to my list"
Agent: [Remembers this for future recommendations]
```

### Use Case 2: Actor Filmography
```
User: "I just watched The Departed. Who else is in it?"
Agent: [Shows cast: Leonardo DiCaprio, Matt Damon, Jack Nicholson, Mark Wahlberg]

User: "Show me more movies with Matt Damon"
Agent: [Lists all Matt Damon movies with ratings]

User: "Which one has the highest rating?"
Agent: [Identifies and provides details]
```

### Use Case 3: Genre Exploration
```
User: "What are the best thrillers?"
Agent: [Shows top 5 thrillers with ratings and plots]

User: "How do they compare to top dramas?"
Agent: [Compares genres and provides insights]
```

## 📝 Notes

- The agent uses GPT-4o-mini by default (fast and cost-effective)
- Conversation memory has a token limit of 1,000 (summarizes older messages)
- Local database searches are case-insensitive
- The agent automatically chooses the best tools for each query

## 🤝 Contributing

To add new tools or features:
1. Add tool definition in `tools.py`
2. Import and add to tools list in `agent.py`
3. Update system prompt if needed
4. Test with various queries

## 🔗 Resources

- [LangChain Documentation](https://python.langchain.com/)
- [OpenAI API Documentation](https://platform.openai.com/docs)
- [OMDb API Documentation](https://www.omdbapi.com/)


