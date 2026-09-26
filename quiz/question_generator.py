"""
Question Generator - Generate multiple-choice quiz questions via RAG + LLM.

Purpose: Retrieve relevant passages from vector store, then use the LLM
         to generate multiple-choice questions.
Inputs: num_questions (int), topic (str, optional), system_prompt (str).
Outputs: List of question dicts.
Dependencies: config, rag.vector_store.
"""
import json
import random
import config
from rag.vector_store import search

MOCK_QUESTIONS = [
    {
        "question": "What is the capital of Canada?",
        "options": {"A": "Toronto", "B": "Ottawa", "C": "Vancouver", "D": "Montreal"},
        "answer": "B",
        "source_text": "Ottawa is the capital of Canada.",
        "topic": "Canadian Geography",
    },
    {
        "question": "Who was the first Prime Minister of Canada?",
        "options": {"A": "Pierre Trudeau", "B": "John A. Macdonald", "C": "Wilfrid Laurier", "D": "Robert Borden"},
        "answer": "B",
        "source_text": "Sir John A. Macdonald was the first Prime Minister of Canada.",
        "topic": "Canadian History",
    },
    {
        "question": "How many provinces does Canada have?",
        "options": {"A": "8", "B": "12", "C": "10", "D": "13"},
        "answer": "C",
        "source_text": "Canada has ten provinces and three territories.",
        "topic": "Regions of Canada",
    },
    {
        "question": "What year was the Canadian Charter of Rights and Freedoms entrenched?",
        "options": {"A": "1867", "B": "1982", "C": "1945", "D": "1960"},
        "answer": "B",
        "source_text": "The Canadian Charter of Rights and Freedoms was entrenched in the Constitution in 1982.",
        "topic": "Rights and Responsibilities",
    },
    {
        "question": "What are the three levels of government in Canada?",
        "options": {
            "A": "Federal, Provincial, Municipal",
            "B": "Federal, State, Local",
            "C": "National, Regional, City",
            "D": "Central, District, Town",
        },
        "answer": "A",
        "source_text": "The three levels of government in Canada are federal, provincial/territorial, and municipal.",
        "topic": "How Canadians Govern Themselves",
    },
    {
        "question": "When is Canada Day celebrated?",
        "options": {"A": "June 1", "B": "July 1", "C": "August 1", "D": "May 24"},
        "answer": "B",
        "source_text": "Canada Day is celebrated on July 1st, marking the anniversary of Confederation in 1867.",
        "topic": "Canadian Symbols",
    },
    {
        "question": "What is the national anthem of Canada?",
        "options": {"A": "God Save the King", "B": "The Maple Leaf Forever", "C": "O Canada", "D": "True North"},
        "answer": "C",
        "source_text": "The national anthem is 'O Canada'.",
        "topic": "Canadian Symbols",
    },
    {
        "question": "What is Canada's most recognized symbol?",
        "options": {"A": "The beaver", "B": "The maple leaf", "C": "The moose", "D": "The hockey stick"},
        "answer": "B",
        "source_text": "The maple leaf is Canada's most recognized symbol.",
        "topic": "Canadian Symbols",
    },
    {
        "question": "What does the federal government handle?",
        "options": {
            "A": "Education and healthcare",
            "B": "National defence, foreign affairs, immigration",
            "C": "Road maintenance",
            "D": "Municipal zoning",
        },
        "answer": "B",
        "source_text": "The federal government is responsible for national defence, foreign affairs, and immigration.",
        "topic": "How Canadians Govern Themselves",
    },
    {
        "question": "How long must a permanent resident live in Canada to apply for citizenship?",
        "options": {"A": "1 out of 3 years", "B": "2 out of 4 years", "C": "3 out of 5 years", "D": "5 out of 7 years"},
        "answer": "C",
        "source_text": "You must have lived in Canada for at least 3 out of the last 5 years.",
        "topic": "Applying for Citizenship",
    },
]


def generate_questions(
    num_questions: int = 10,
    topic: str = None,
    system_prompt: str = "",
) -> list:
    """
    Generate multiple-choice questions. In sandbox mode, returns mock questions.
    """
    if config.is_sandbox():
        pool = MOCK_QUESTIONS[:]
        if topic:
            topic_lower = topic.lower()
            filtered = [q for q in pool if topic_lower in q.get("topic", "").lower()]
            if filtered:
                pool = filtered
        random.shuffle(pool)
        return pool[:num_questions]

    try:
        from langchain_xai import ChatXAI
        from langchain_core.prompts import ChatPromptTemplate

        query = topic or "Canadian citizenship test study material"
        passages = search(query, n_results=8)
        context = "\n\n".join(p["content"] for p in passages)

        prompt = ChatPromptTemplate.from_messages([
            ("system", system_prompt or "You are a quiz question generator."),
            ("human",
             "Based on the following study material, generate {num} multiple-choice questions.\n\n"
             "STUDY MATERIAL:\n{context}\n\n"
             "Return ONLY a JSON array. Each element must have:\n"
             '  "question": string, "options": {{"A": ..., "B": ..., "C": ..., "D": ...}}, '
             '"answer": "A"|"B"|"C"|"D", "source_text": string, "topic": string\n'
             "No markdown, no explanation, just the JSON array."),
        ])

        llm = ChatXAI(model=config.GROK_MODEL, api_key=config.XAI_API_KEY)
        chain = prompt | llm
        response = chain.invoke({"num": num_questions, "context": context})

        text = response.content.strip()
        if text.startswith("```"):
            text = text.split("\n", 1)[1].rsplit("```", 1)[0]
        return json.loads(text)
    except Exception as e:
        print(f"[Error] Question generation failed: {e}")
        return []


if __name__ == "__main__":
    questions = generate_questions(5)
    print(f"Generated {len(questions)} questions:")
    for i, q in enumerate(questions, 1):
        print(f"  {i}. {q['question']} (Answer: {q['answer']})")
