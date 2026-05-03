from langchain_openai import ChatOpenAI
import os
import sys
from dotenv import load_dotenv
from langchain.agents import AgentExecutor, create_openai_functions_agent
from langchain.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain.memory import ConversationSummaryBufferMemory
from tools import (
    search_movie, 
    get_movie_details, 
    compare_movies,
    search_movies_by_actor,
    get_top_movies_by_genre,
    recommend_movie_by_genre
)

load_dotenv()

# Initialize the language model
model = ChatOpenAI(
    model="gpt-4o-mini",
    temperature=0,
    api_key=os.getenv("OPENAI_API_KEY")
)

# Define the tools (these check local database first, then fall back to OMDb API)
tools = [
    search_movie, 
    get_movie_details, 
    compare_movies,
    search_movies_by_actor,
    get_top_movies_by_genre,
    recommend_movie_by_genre
]

# Create memory for conversation history
memory = ConversationSummaryBufferMemory(
    llm=model,
    max_token_limit=1000,
    memory_key="chat_history",
    return_messages=True,
    output_key="output"
)

# Create a prompt template for the agent with chat history
prompt = ChatPromptTemplate.from_messages([
    ("system", "You are a helpful movie assistant. You can search for movies, provide detailed information about them, compare movies, search for movies by actor name, get top-rated movies by genre, and recommend movies based on genre preferences. The tools automatically check a local database first for faster results, and only query the OMDb API if the movie is not found locally. Use the available tools to help answer questions about movies."),
    MessagesPlaceholder(variable_name="chat_history"),
    ("human", "{input}"),
    MessagesPlaceholder(variable_name="agent_scratchpad"),
])

# Create the OpenAI Functions agent
agent = create_openai_functions_agent(
    llm=model,
    tools=tools,
    prompt=prompt
)

# Create an agent executor with memory (verbose for examples)
agent_executor = AgentExecutor(
    agent=agent,
    tools=tools,
    memory=memory,
    verbose=True,
    handle_parsing_errors=True
)

# Create a non-verbose agent executor for interactive chat
agent_executor_quiet = AgentExecutor(
    agent=agent,
    tools=tools,
    memory=memory,
    verbose=False,
    handle_parsing_errors=True
)

def interactive_chat():
    """Interactive chat mode with the movie agent.
    Интерактивный режим чата с киноагентом.
    """
    print("\n" + "=" * 80)
    print("🎬 Movie Agent - Interactive Chat Mode / Интерактивный режим чата 🎬")
    print("=" * 80)
    print("\nWelcome! You can chat with me about movies in English or Russian.")
    print("Добро пожаловать! Вы можете общаться со мной о фильмах на английском или русском.\n")
    
    # Ask for user's name
    user_name = input("What's your name? / Как вас зовут? ").strip()
    if not user_name:
        user_name = "You / Вы"
    
    print(f"\n👋 Nice to meet you, {user_name}! / Приятно познакомиться, {user_name}!")
    print("\nCommands / Команды:")
    print("  - Type your question / Введите ваш вопрос")
    print("  - 'exit' or 'quit' to end / 'exit' или 'quit' для выхода")
    print("  - 'clear' to reset memory / 'clear' для сброса памяти")
    print("=" * 80 + "\n")
    
    while True:
        try:
            # Get user input with personalized prompt
            user_input = input(f"👤 {user_name}: ").strip()
            
            # Check for exit commands
            if user_input.lower() in ['exit', 'quit', 'выход', 'выйти']:
                print(f"\n👋 Goodbye, {user_name}! See you next time! / До свидания, {user_name}! Увидимся в следующий раз!")
                break
            
            # Check for clear memory command
            if user_input.lower() in ['clear', 'очистить']:
                memory.clear()
                print("\n🔄 Memory cleared! / Память очищена!\n")
                continue
            
            # Skip empty input
            if not user_input:
                continue
            
            # Get response from agent (using quiet executor)
            print("\n🤖 Agent: ", end="", flush=True)
            result = agent_executor_quiet.invoke({"input": user_input})
            print(result["output"])
            print()
            
        except KeyboardInterrupt:
            print(f"\n\n👋 Goodbye, {user_name}! See you next time! / До свидания, {user_name}! Увидимся в следующий раз!")
            break
        except Exception as e:
            print(f"\n❌ Error / Ошибка: {str(e)}\n")


def run_examples():
    """Run predefined examples demonstrating agent capabilities.
    Запустить предопределенные примеры, демонстрирующие возможности агента.
    """
    print("\n🎬 Movie Agent - Example Use Cases / Примеры использования 🎬\n")
    
    # Example 1: Compare movie ratings (English)
    print("=" * 80)
    print("EXAMPLE 1 (English): Compare ratings of Matrix and Inception")
    print("=" * 80)
    result1 = agent_executor.invoke({
        "input": "Compare The Matrix and Inception. Which one has a higher rating?"
    })
    print("\n✅ ANSWER:")
    print("-" * 80)
    print(result1["output"])
    
    # Example 2: Compare movie ratings (Russian)
    # Пример 1 (Русский): Сравнить рейтинги фильмов
    print("\n\n" + "=" * 80)
    print("ПРИМЕР 1 (Русский): Сравни рейтинги Matrix и Inception")
    print("=" * 80)
    result2 = agent_executor.invoke({
        "input": "Сравни рейтинги Matrix и Inception. Какой выше?"
    })
    print("\n✅ ОТВЕТ:")
    print("-" * 80)
    print(result2["output"])
    
    # Example 3: Find movies by actor (English)
    print("\n\n" + "=" * 80)
    print("EXAMPLE 2 (English): Find movies with Leonardo DiCaprio")
    print("=" * 80)
    result3 = agent_executor.invoke({
        "input": "Find all movies with Leonardo DiCaprio and show me their ratings"
    })
    print("\n✅ ANSWER:")
    print("-" * 80)
    print(result3["output"])
    
    # Example 4: Find movies by actor (Russian)
    # Пример 2 (Русский): Найти фильмы с актёром
    print("\n\n" + "=" * 80)
    print("ПРИМЕР 2 (Русский): Найди фильмы с Леонардо ДиКаприо")
    print("=" * 80)
    result4 = agent_executor.invoke({
        "input": "Найди фильмы с Леонардо ДиКаприо и покажи их рейтинги"
    })
    print("\n✅ ОТВЕТ:")
    print("-" * 80)
    print(result4["output"])
    
    # Example 5: Genre-based recommendation (English)
    print("\n\n" + "=" * 80)
    print("EXAMPLE 3 (English): Which movie is better - comedy or thriller?")
    print("=" * 80)
    result5 = agent_executor.invoke({
        "input": "Which movie is better for this evening: a comedy or a thriller?"
    })
    print("\n✅ ANSWER:")
    print("-" * 80)
    print(result5["output"])
    
    # Example 6: Genre-based recommendation (Russian)
    # Пример 3 (Русский): Рекомендация по жанру
    print("\n\n" + "=" * 80)
    print("ПРИМЕР 3 (Русский): Какой фильм лучше для вечера: комедия или триллер?")
    print("=" * 80)
    result6 = agent_executor.invoke({
        "input": "Какой фильм лучше для вечера: комедия или триллер?"
    })
    print("\n✅ ОТВЕТ:")
    print("-" * 80)
    print(result6["output"])
    
    print("\n\n" + "=" * 80)
    print("🎉 All examples completed successfully! / Все примеры выполнены успешно!")
    print("=" * 80)


# Main entry point
if __name__ == "__main__":
    # Check for command line arguments
    if len(sys.argv) > 1:
        mode = sys.argv[1].lower()
        if mode in ['chat', 'interactive', 'i']:
            interactive_chat()
        elif mode in ['examples', 'demo', 'e']:
            run_examples()
        else:
            print("Usage: python agent.py [chat|examples]")
            print("  chat/interactive/i - Start interactive chat mode")
            print("  examples/demo/e    - Run predefined examples")
            print("\nDefault: Shows menu to choose mode")
    else:
        # Interactive menu
        print("\n" + "=" * 80)
        print("🎬 Movie Agent / Киноагент 🎬")
        print("=" * 80)
        print("\nChoose mode / Выберите режим:\n")
        print("1. Interactive Chat / Интерактивный чат")
        print("2. Run Examples / Запустить примеры")
        print("3. Exit / Выход")
        print("\n" + "=" * 80)
        
        choice = input("\nEnter your choice (1-3) / Введите ваш выбор (1-3): ").strip()
        
        if choice == "1":
            interactive_chat()
        elif choice == "2":
            run_examples()
        elif choice == "3":
            print("\n👋 Goodbye! / До свидания!")
        else:
            print("\n❌ Invalid choice. Running examples by default...")
            run_examples()