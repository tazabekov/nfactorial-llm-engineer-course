"""
Movie Agent Tools / Инструменты киноагента

This module contains tools for searching movies, getting details, comparing movies,
and providing recommendations. All tools support English and Russian queries.

Этот модуль содержит инструменты для поиска фильмов, получения деталей, сравнения фильмов
и предоставления рекомендаций. Все инструменты поддерживают запросы на английском и русском языках.
"""

import os
import requests
import pandas as pd
from langchain.tools import tool
from dotenv import load_dotenv

load_dotenv()

OMDB_API_KEY = os.getenv("OMDB_API_KEY")
OMDB_BASE_URL = "http://www.omdbapi.com/"
MOVIES_CSV_PATH = os.path.join(os.path.dirname(__file__), "data", "movies.csv")

# Load the local movies database
try:
    LOCAL_MOVIES_DF = pd.read_csv(MOVIES_CSV_PATH)
    print(f"✅ Loaded {len(LOCAL_MOVIES_DF)} movies from local database")
except Exception as e:
    LOCAL_MOVIES_DF = None
    print(f"⚠️ Could not load local movies database: {e}")


@tool
def search_movie(query: str) -> str:
    """Search for a movie by title. First checks local database, then uses OMDb API if not found locally.
    Поиск фильма по названию. Сначала проверяет локальную базу, затем использует OMDb API если не найдено локально.
    
    Args:
        query: Movie title to search for / Название фильма для поиска
        
    Returns:
        Movie information from local database or OMDb API
        Информация о фильме из локальной базы или OMDb API
    
    Examples:
        "Find movies about Batman" / "Найди фильмы про Бэтмена"
    """
    # First, try to find in local database
    if LOCAL_MOVIES_DF is not None:
        # Case-insensitive search in local database
        matches = LOCAL_MOVIES_DF[
            LOCAL_MOVIES_DF['Series_Title'].str.contains(query, case=False, na=False)
        ]
        
        if not matches.empty:
            # Found in local database
            result = f"Found {len(matches)} result(s) in LOCAL database:\n\n"
            for idx, movie in matches.head(5).iterrows():  # Show first 5 results
                result += f"- {movie['Series_Title']} ({movie['Released_Year']}) - IMDb: {movie['IMDB_Rating']}/10\n"
            result += "\n💾 Source: Local Database"
            return result
    
    # If not found locally, use OMDb API
    return "Not found in local database. " + search_movie_omdb.invoke({"query": query})


@tool
def get_movie_details(title: str) -> str:
    """Get detailed information about a movie. First checks local database, then uses OMDb API if not found.
    Получить подробную информацию о фильме. Сначала проверяет локальную базу, затем использует OMDb API если не найдено.
    
    Args:
        title: Movie title to get details for / Название фильма для получения деталей
        
    Returns:
        Detailed movie information from local database or OMDb API
        Подробная информация о фильме из локальной базы или OMDb API
    
    Examples:
        "Tell me about Inception" / "Расскажи про фильм Inception"
        "What's the rating of The Matrix?" / "Какой рейтинг у Matrix?"
    """
    # First, try to find in local database
    if LOCAL_MOVIES_DF is not None:
        # Try exact match first, then case-insensitive partial match
        exact_match = LOCAL_MOVIES_DF[
            LOCAL_MOVIES_DF['Series_Title'].str.lower() == title.lower()
        ]
        
        if not exact_match.empty:
            movie = exact_match.iloc[0]
            result = f"""
📽️ LOCAL DATABASE ENTRY

Title: {movie['Series_Title']}
Year: {movie['Released_Year']}
Certificate: {movie['Certificate']}
Runtime: {movie['Runtime']}
Genre: {movie['Genre']}
Director: {movie['Director']}
Stars: {movie['Star1']}, {movie['Star2']}, {movie['Star3']}, {movie['Star4']}
IMDb Rating: {movie['IMDB_Rating']}/10
Overview: {movie['Overview']}
Number of Votes: {movie['No_of_Votes']}
Box Office: ${movie['Gross']}

💾 Source: Local Database
"""
            return result.strip()
        
        # Try partial match
        partial_match = LOCAL_MOVIES_DF[
            LOCAL_MOVIES_DF['Series_Title'].str.contains(title, case=False, na=False)
        ]
        
        if not partial_match.empty:
            movie = partial_match.iloc[0]
            result = f"""
📽️ LOCAL DATABASE ENTRY (Partial Match: "{movie['Series_Title']}")

Title: {movie['Series_Title']}
Year: {movie['Released_Year']}
Certificate: {movie['Certificate']}
Runtime: {movie['Runtime']}
Genre: {movie['Genre']}
Director: {movie['Director']}
Stars: {movie['Star1']}, {movie['Star2']}, {movie['Star3']}, {movie['Star4']}
IMDb Rating: {movie['IMDB_Rating']}/10
Overview: {movie['Overview']}
Number of Votes: {movie['No_of_Votes']}
Box Office: ${movie['Gross']}

💾 Source: Local Database
"""
            return result.strip()
    
    # If not found locally, use OMDb API
    return "Not found in local database. Fetching from OMDb API...\n\n" + get_movie_details_omdb.invoke({"title": title})


@tool
def compare_movies(movie1_title: str, movie2_title: str) -> str:
    """Compare two movies. First checks local database, then uses OMDb API if not found.
    Сравнить два фильма. Сначала проверяет локальную базу, затем использует OMDb API если не найдено.
    
    Args:
        movie1_title: Title of the first movie / Название первого фильма
        movie2_title: Title of the second movie / Название второго фильма
        
    Returns:
        Comparison of the two movies including ratings and genres
        Сравнение двух фильмов включая рейтинги и жанры
    
    Examples:
        "Compare Inception and The Matrix" / "Сравни Inception и Matrix"
    """
    def get_movie_data_local(title: str):
        """Helper function to get movie data from local database"""
        if LOCAL_MOVIES_DF is None:
            return None
        
        # Try exact match first
        exact_match = LOCAL_MOVIES_DF[
            LOCAL_MOVIES_DF['Series_Title'].str.lower() == title.lower()
        ]
        if not exact_match.empty:
            return exact_match.iloc[0].to_dict()
        
        # Try partial match
        partial_match = LOCAL_MOVIES_DF[
            LOCAL_MOVIES_DF['Series_Title'].str.contains(title, case=False, na=False)
        ]
        if not partial_match.empty:
            return partial_match.iloc[0].to_dict()
        
        return None
    
    # Try to get both movies from local database
    movie1_local = get_movie_data_local(movie1_title)
    movie2_local = get_movie_data_local(movie2_title)
    
    # If both found locally, compare using local data
    if movie1_local and movie2_local:
        movie1_title_full = movie1_local['Series_Title']
        movie1_year = movie1_local['Released_Year']
        movie1_rating = movie1_local['IMDB_Rating']
        movie1_genre = movie1_local['Genre']
        
        movie2_title_full = movie2_local['Series_Title']
        movie2_year = movie2_local['Released_Year']
        movie2_rating = movie2_local['IMDB_Rating']
        movie2_genre = movie2_local['Genre']
        
        # Compare ratings
        if movie1_rating > movie2_rating:
            rating_comparison = f"{movie1_title_full} has a higher rating ({movie1_rating:.1f} vs {movie2_rating:.1f})"
        elif movie2_rating > movie1_rating:
            rating_comparison = f"{movie2_title_full} has a higher rating ({movie2_rating:.1f} vs {movie1_rating:.1f})"
        else:
            rating_comparison = f"Both movies have the same rating ({movie1_rating:.1f})"
        
        # Compare genres
        genre1_list = [g.strip() for g in str(movie1_genre).split(',')]
        genre2_list = [g.strip() for g in str(movie2_genre).split(',')]
        common_genres = set(genre1_list) & set(genre2_list)
        
        if common_genres:
            genre_comparison = f"Common genres: {', '.join(common_genres)}"
        else:
            genre_comparison = "No common genres"
        
        result = f"""
🎬 MOVIE COMPARISON (Local Database) 🎬

Movie 1: {movie1_title_full} ({movie1_year})
- IMDb Rating: {movie1_rating}/10
- Genres: {movie1_genre}

Movie 2: {movie2_title_full} ({movie2_year})
- IMDb Rating: {movie2_rating}/10
- Genres: {movie2_genre}

📊 COMPARISON:
- Rating: {rating_comparison}
- Genres: {genre_comparison}

💾 Source: Local Database
"""
        return result.strip()
    
    # If not both found locally, use OMDb API
    if not movie1_local and not movie2_local:
        return "Neither movie found in local database. Fetching from OMDb API...\n\n" + compare_movies_omdb.invoke({"movie1_title": movie1_title, "movie2_title": movie2_title})
    elif not movie1_local:
        return f"'{movie1_title}' not found in local database. Fetching from OMDb API...\n\n" + compare_movies_omdb.invoke({"movie1_title": movie1_title, "movie2_title": movie2_title})
    else:
        return f"'{movie2_title}' not found in local database. Fetching from OMDb API...\n\n" + compare_movies_omdb.invoke({"movie1_title": movie1_title, "movie2_title": movie2_title})


@tool
def search_movie_omdb(query: str) -> str:
    """Search for movies by title using the OMDb API.
    
    Args:
        query: Movie title to search for
        
    Returns:
        JSON string with search results including movie titles, years, and IMDb IDs
    """
    if not OMDB_API_KEY:
        return "Error: OMDB_API_KEY not found in environment variables. Please add it to your .env file."
    
    params = {
        "apikey": OMDB_API_KEY,
        "s": query,
        "type": "movie"
    }
    
    try:
        response = requests.get(OMDB_BASE_URL, params=params)
        response.raise_for_status()
        data = response.json()
        
        if data.get("Response") == "True":
            movies = data.get("Search", [])
            result = f"Found {data.get('totalResults', 0)} results:\n\n"
            for movie in movies[:5]:  # Show first 5 results
                result += f"- {movie['Title']} ({movie['Year']}) - IMDb ID: {movie['imdbID']}\n"
            return result
        else:
            return f"No results found: {data.get('Error', 'Unknown error')}"
    except Exception as e:
        return f"Error searching OMDb API: {str(e)}"


@tool
def get_movie_details_omdb(title: str = None, imdb_id: str = None) -> str:
    """Get detailed information about a specific movie from OMDb API.
    
    Args:
        title: Movie title (optional if imdb_id is provided)
        imdb_id: IMDb ID like tt1285016 (optional if title is provided)
        
    Returns:
        Detailed movie information including plot, cast, ratings, etc.
    """
    if not OMDB_API_KEY:
        return "Error: OMDB_API_KEY not found in environment variables. Please add it to your .env file."
    
    if not title and not imdb_id:
        return "Error: Either title or imdb_id must be provided"
    
    params = {
        "apikey": OMDB_API_KEY,
        "plot": "full"
    }
    
    if imdb_id:
        params["i"] = imdb_id
    else:
        params["t"] = title
    
    try:
        response = requests.get(OMDB_BASE_URL, params=params)
        response.raise_for_status()
        data = response.json()
        
        if data.get("Response") == "True":
            result = f"""
Title: {data.get('Title')}
Year: {data.get('Year')}
Rated: {data.get('Rated')}
Released: {data.get('Released')}
Runtime: {data.get('Runtime')}
Genre: {data.get('Genre')}
Director: {data.get('Director')}
Actors: {data.get('Actors')}
Plot: {data.get('Plot')}
IMDb Rating: {data.get('imdbRating')}/10
IMDb ID: {data.get('imdbID')}
"""
            return result.strip()
        else:
            return f"Movie not found: {data.get('Error', 'Unknown error')}"
    except Exception as e:
        return f"Error fetching movie details: {str(e)}"


@tool
def compare_movies_omdb(movie1_title: str, movie2_title: str) -> str:
    """Compare two movies based on their IMDb ratings and genres using OMDb API.
    
    Args:
        movie1_title: Title of the first movie
        movie2_title: Title of the second movie
        
    Returns:
        Comparison of the two movies including ratings and genres
    """
    if not OMDB_API_KEY:
        return "Error: OMDB_API_KEY not found in environment variables. Please add it to your .env file."
    
    def fetch_movie_data(title: str) -> dict:
        """Helper function to fetch movie data"""
        params = {
            "apikey": OMDB_API_KEY,
            "t": title,
            "plot": "short"
        }
        try:
            response = requests.get(OMDB_BASE_URL, params=params)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            return {"Response": "False", "Error": str(e)}
    
    # Fetch data for both movies
    movie1_data = fetch_movie_data(movie1_title)
    movie2_data = fetch_movie_data(movie2_title)
    
    # Check if both movies were found
    if movie1_data.get("Response") != "True":
        return f"Error: Could not find '{movie1_title}'. {movie1_data.get('Error', 'Unknown error')}"
    
    if movie2_data.get("Response") != "True":
        return f"Error: Could not find '{movie2_title}'. {movie2_data.get('Error', 'Unknown error')}"
    
    # Extract relevant information
    movie1_title_full = movie1_data.get('Title', 'Unknown')
    movie1_year = movie1_data.get('Year', 'Unknown')
    movie1_rating = movie1_data.get('imdbRating', 'N/A')
    movie1_genre = movie1_data.get('Genre', 'N/A')
    
    movie2_title_full = movie2_data.get('Title', 'Unknown')
    movie2_year = movie2_data.get('Year', 'Unknown')
    movie2_rating = movie2_data.get('imdbRating', 'N/A')
    movie2_genre = movie2_data.get('Genre', 'N/A')
    
    # Compare ratings
    rating_comparison = ""
    try:
        if movie1_rating != 'N/A' and movie2_rating != 'N/A':
            rating1 = float(movie1_rating)
            rating2 = float(movie2_rating)
            if rating1 > rating2:
                rating_comparison = f"{movie1_title_full} has a higher rating ({rating1:.1f} vs {rating2:.1f})"
            elif rating2 > rating1:
                rating_comparison = f"{movie2_title_full} has a higher rating ({rating2:.1f} vs {rating1:.1f})"
            else:
                rating_comparison = f"Both movies have the same rating ({rating1:.1f})"
        else:
            rating_comparison = "Rating comparison not available"
    except ValueError:
        rating_comparison = "Could not compare ratings"
    
    # Compare genres
    genre1_list = [g.strip() for g in movie1_genre.split(',')]
    genre2_list = [g.strip() for g in movie2_genre.split(',')]
    common_genres = set(genre1_list) & set(genre2_list)
    
    genre_comparison = ""
    if common_genres:
        genre_comparison = f"Common genres: {', '.join(common_genres)}"
    else:
        genre_comparison = "No common genres"
    
    # Build comparison result
    result = f"""
🎬 MOVIE COMPARISON 🎬

Movie 1: {movie1_title_full} ({movie1_year})
- IMDb Rating: {movie1_rating}/10
- Genres: {movie1_genre}

Movie 2: {movie2_title_full} ({movie2_year})
- IMDb Rating: {movie2_rating}/10
- Genres: {movie2_genre}

📊 COMPARISON:
- Rating: {rating_comparison}
- Genres: {genre_comparison}
"""
    
    return result.strip()


@tool
def search_movies_by_actor(actor_name: str) -> str:
    """Search for movies featuring a specific actor in the local database.
    Поиск фильмов с участием конкретного актёра в локальной базе данных.
    
    Args:
        actor_name: Name of the actor to search for / Имя актёра для поиска
        
    Returns:
        List of movies featuring the actor with their ratings
        Список фильмов с участием актёра и их рейтинги
    
    Examples:
        "Find movies with Leonardo DiCaprio" / "Найди фильмы с Леонардо ДиКаприо"
        "Show me Tom Hanks films and their ratings" / "Покажи фильмы с Томом Хэнксом и их рейтинги"
    """
    if LOCAL_MOVIES_DF is None:
        return "Error: Local movie database not available."
    
    # Search across all four star columns
    matches = LOCAL_MOVIES_DF[
        LOCAL_MOVIES_DF['Star1'].str.contains(actor_name, case=False, na=False) |
        LOCAL_MOVIES_DF['Star2'].str.contains(actor_name, case=False, na=False) |
        LOCAL_MOVIES_DF['Star3'].str.contains(actor_name, case=False, na=False) |
        LOCAL_MOVIES_DF['Star4'].str.contains(actor_name, case=False, na=False)
    ]
    
    if matches.empty:
        return f"No movies found featuring '{actor_name}' in the local database."
    
    # Sort by rating (descending)
    matches_sorted = matches.sort_values('IMDB_Rating', ascending=False)
    
    result = f"🎭 Found {len(matches_sorted)} movie(s) featuring '{actor_name}':\n\n"
    
    for idx, movie in matches_sorted.iterrows():
        # Determine which star position the actor is in
        stars = []
        for i in range(1, 5):
            star = movie[f'Star{i}']
            if pd.notna(star) and actor_name.lower() in star.lower():
                stars.append(star)
        
        result += f"- {movie['Series_Title']} ({movie['Released_Year']})\n"
        result += f"  ⭐ IMDb Rating: {movie['IMDB_Rating']}/10\n"
        result += f"  🎬 Genre: {movie['Genre']}\n"
        result += f"  👥 Cast: {movie['Star1']}, {movie['Star2']}, {movie['Star3']}, {movie['Star4']}\n\n"
    
    result += "💾 Source: Local Database"
    return result


@tool
def get_top_movies_by_genre(genre: str, limit: int = 5) -> str:
    """Get top-rated movies by genre from the local database.
    Получить лучшие фильмы по жанру из локальной базы данных.
    
    Args:
        genre: Genre to search for (e.g., Comedy, Thriller, Drama, Action) / Жанр для поиска (например, Comedy, Thriller, Drama, Action)
        limit: Maximum number of movies to return (default: 5) / Максимальное количество фильмов для возврата (по умолчанию: 5)
        
    Returns:
        List of top-rated movies in the specified genre
        Список лучших фильмов в указанном жанре
    
    Examples:
        "Show me the best thriller movies" / "Покажи лучшие триллеры"
        "What are the top 5 comedies?" / "Какие топ-5 комедий?"
    """
    if LOCAL_MOVIES_DF is None:
        return "Error: Local movie database not available."
    
    # Search for movies containing the genre (case-insensitive)
    matches = LOCAL_MOVIES_DF[
        LOCAL_MOVIES_DF['Genre'].str.contains(genre, case=False, na=False)
    ]
    
    if matches.empty:
        return f"No movies found in genre '{genre}' in the local database."
    
    # Sort by rating (descending) and get top N
    top_movies = matches.sort_values('IMDB_Rating', ascending=False).head(limit)
    
    result = f"🏆 Top {len(top_movies)} {genre} movies:\n\n"
    
    for idx, movie in top_movies.iterrows():
        result += f"- {movie['Series_Title']} ({movie['Released_Year']})\n"
        result += f"  ⭐ IMDb Rating: {movie['IMDB_Rating']}/10\n"
        result += f"  🎬 Genre: {movie['Genre']}\n"
        result += f"  🎥 Director: {movie['Director']}\n"
        result += f"  📝 Overview: {movie['Overview'][:100]}...\n\n"
    
    result += f"💾 Source: Local Database ({len(matches)} total {genre} movies found)"
    return result


@tool
def recommend_movie_by_genre(genre1: str, genre2: str) -> str:
    """Compare top movies from two genres and provide a recommendation.
    Сравнить лучшие фильмы из двух жанров и дать рекомендацию.
    
    Args:
        genre1: First genre to compare (e.g., Comedy) / Первый жанр для сравнения (например, Comedy)
        genre2: Second genre to compare (e.g., Thriller) / Второй жанр для сравнения (например, Thriller)
        
    Returns:
        Comparison and recommendation based on top-rated movies in each genre
        Сравнение и рекомендация на основе лучших фильмов в каждом жанре
    
    Examples:
        "Should I watch a comedy or thriller tonight?" / "Какой фильм лучше для вечера: комедия или триллер?"
        "What's better: action or drama?" / "Что лучше: боевик или драма?"
    """
    if LOCAL_MOVIES_DF is None:
        return "Error: Local movie database not available."
    
    # Get top movie from each genre
    genre1_matches = LOCAL_MOVIES_DF[
        LOCAL_MOVIES_DF['Genre'].str.contains(genre1, case=False, na=False)
    ].sort_values('IMDB_Rating', ascending=False)
    
    genre2_matches = LOCAL_MOVIES_DF[
        LOCAL_MOVIES_DF['Genre'].str.contains(genre2, case=False, na=False)
    ].sort_values('IMDB_Rating', ascending=False)
    
    if genre1_matches.empty and genre2_matches.empty:
        return f"No movies found for genres '{genre1}' or '{genre2}' in the local database."
    
    if genre1_matches.empty:
        return f"No movies found for genre '{genre1}'. Only found {genre2} movies."
    
    if genre2_matches.empty:
        return f"No movies found for genre '{genre2}'. Only found {genre1} movies."
    
    # Get top 3 from each genre
    top_genre1 = genre1_matches.head(3)
    top_genre2 = genre2_matches.head(3)
    
    # Calculate average ratings
    avg_rating1 = top_genre1['IMDB_Rating'].mean()
    avg_rating2 = top_genre2['IMDB_Rating'].mean()
    
    result = f"🎬 GENRE COMPARISON & RECOMMENDATION 🎬\n\n"
    
    result += f"🎭 Top {genre1} Movies:\n"
    for idx, movie in top_genre1.iterrows():
        result += f"  - {movie['Series_Title']} ({movie['Released_Year']}) - ⭐ {movie['IMDB_Rating']}/10\n"
    result += f"  Average Rating: {avg_rating1:.2f}/10\n\n"
    
    result += f"🎭 Top {genre2} Movies:\n"
    for idx, movie in top_genre2.iterrows():
        result += f"  - {movie['Series_Title']} ({movie['Released_Year']}) - ⭐ {movie['IMDB_Rating']}/10\n"
    result += f"  Average Rating: {avg_rating2:.2f}/10\n\n"
    
    result += "💡 RECOMMENDATION:\n"
    
    if avg_rating1 > avg_rating2:
        best_movie = top_genre1.iloc[0]
        result += f"For this evening, I recommend a {genre1}!\n"
        result += f"🌟 Top Pick: {best_movie['Series_Title']} ({best_movie['Released_Year']})\n"
        result += f"⭐ Rating: {best_movie['IMDB_Rating']}/10\n"
        result += f"📝 {best_movie['Overview']}\n"
    elif avg_rating2 > avg_rating1:
        best_movie = top_genre2.iloc[0]
        result += f"For this evening, I recommend a {genre2}!\n"
        result += f"🌟 Top Pick: {best_movie['Series_Title']} ({best_movie['Released_Year']})\n"
        result += f"⭐ Rating: {best_movie['IMDB_Rating']}/10\n"
        result += f"📝 {best_movie['Overview']}\n"
    else:
        best_movie1 = top_genre1.iloc[0]
        best_movie2 = top_genre2.iloc[0]
        result += f"Both genres have excellent options with similar ratings!\n"
        result += f"\n{genre1} Pick: {best_movie1['Series_Title']} ({best_movie1['Released_Year']}) - {best_movie1['IMDB_Rating']}/10\n"
        result += f"{genre2} Pick: {best_movie2['Series_Title']} ({best_movie2['Released_Year']}) - {best_movie2['IMDB_Rating']}/10\n"
    
    result += f"\n💾 Source: Local Database"
    return result