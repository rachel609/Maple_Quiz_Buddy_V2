"""
Maple Quiz Buddy V2 - MCP Server

Purpose: Expose quiz functionality as an MCP server with Tools, Resources,
         and Prompts. Compatible with Claude Desktop and Claude Code.
Inputs: MCP protocol messages via stdio transport.
Outputs: Tool results, resource data, prompt templates.
Dependencies: mcp, all project modules.

15 Tools + 5 Resources + 3 Prompts
"""
import sys
import os
import json
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import date

# Add project root to path so imports work when run as subprocess
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import config
from mcp.server import Server
from mcp.server.stdio import run_stdio
from mcp.types import (
    Tool,
    TextContent,
    Resource,
    Prompt,
    PromptArgument,
    PromptMessage,
    GetPromptResult,
)

from personality.style_selector import validate_style, validate_language, STYLES, STYLE_DESCRIPTIONS, LANGUAGES
from personality.buddy_prompts import generate_system_prompt, get_feedback_prompt
from rag.vector_store import load_vector_store, search
from quiz.question_generator import generate_questions
from quiz.grader import (
    grade_single, grade_quiz, load_wrong_answers, clear_wrong_answers, get_wrong_by_topic,
)
from quiz.review_manager import get_review_questions, get_wrong_count
from memory.score_tracker import (
    save_score, get_score_history, get_analytics, get_best_score,
    get_latest_score, predict_readiness, compare_attempts, get_progress_summary,
)
from observability.tracing import trace_event

# ---- Server instance ----
server = Server("maple-quiz-buddy-v2")

# ---- Session state ----
_session = {
    "style": "Warm Encourager",
    "language": "English",
    "system_prompt": "",
    "questions": [],
    "current_index": 0,
    "user_answers": [],
    "active": False,
    "initialized": False,
}


def _ensure_init():
    """Lazy-initialize vector store and system prompt."""
    if not _session["initialized"]:
        load_vector_store()
        _session["system_prompt"] = generate_system_prompt(
            _session["style"], _session["language"]
        )
        _session["initialized"] = True


# ========================================
#  TOOLS (15 total)
# ========================================

@server.list_tools()
async def list_tools():
    return [
        # --- Core Quiz Tools ---
        Tool(
            name="search_study_material",
            description="Search the Discover Canada study guide using RAG. Returns relevant passages for any topic or question.",
            inputSchema={
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "Search query about Canadian citizenship topics"},
                    "num_results": {"type": "integer", "description": "Number of results (default: 5)", "default": 5},
                },
                "required": ["query"],
            },
        ),
        Tool(
            name="generate_quiz",
            description="Generate a multiple-choice quiz. Optionally specify a topic, difficulty, and number of questions.",
            inputSchema={
                "type": "object",
                "properties": {
                    "num_questions": {"type": "integer", "description": "Number of questions (default: 10)", "default": 10},
                    "topic": {"type": "string", "description": "Optional topic to focus on (e.g., 'Canadian History', 'Rights and Responsibilities')"},
                },
            },
        ),
        Tool(
            name="answer_question",
            description="Submit an answer (A/B/C/D) for the current quiz question. Returns whether correct and feedback.",
            inputSchema={
                "type": "object",
                "properties": {
                    "answer": {"type": "string", "enum": ["A", "B", "C", "D"], "description": "The answer choice"},
                },
                "required": ["answer"],
            },
        ),
        Tool(
            name="get_wrong_answers",
            description="Get the list of wrong answers from the current or past quiz sessions. Can filter by topic/chapter.",
            inputSchema={
                "type": "object",
                "properties": {
                    "topic": {"type": "string", "description": "Optional: filter by topic name"},
                },
            },
        ),
        Tool(
            name="review_weak_topics",
            description="Analyze weak topics based on wrong answers and recommend targeted study content.",
            inputSchema={"type": "object", "properties": {}},
        ),

        # --- Analytics Tools ---
        Tool(
            name="get_score_history",
            description="Get the complete score history across all quiz attempts with dates and pass/fail status.",
            inputSchema={"type": "object", "properties": {}},
        ),
        Tool(
            name="get_study_analytics",
            description="Get a detailed study analytics dashboard: average score, best/worst, trend, pass rate, improvement curve.",
            inputSchema={"type": "object", "properties": {}},
        ),
        Tool(
            name="predict_exam_readiness",
            description="AI-powered prediction of exam readiness based on score history and trends.",
            inputSchema={"type": "object", "properties": {}},
        ),

        # --- Notification Tools ---
        Tool(
            name="send_report_email",
            description="Send quiz results and wrong answer summary to an email address via Gmail SMTP.",
            inputSchema={
                "type": "object",
                "properties": {
                    "email": {"type": "string", "description": "Recipient email address"},
                    "include_wrong_answers": {"type": "boolean", "description": "Include wrong answers in report", "default": True},
                },
                "required": ["email"],
            },
        ),
        Tool(
            name="schedule_reminder",
            description="Set a study reminder message (displayed to user, actual scheduling depends on host).",
            inputSchema={
                "type": "object",
                "properties": {
                    "message": {"type": "string", "description": "Reminder message"},
                    "days_from_now": {"type": "integer", "description": "Days from now to remind", "default": 1},
                },
                "required": ["message"],
            },
        ),

        # --- Advanced Tools ---
        Tool(
            name="explain_answer",
            description="Generate a detailed explanation for a quiz question, including source references from Discover Canada.",
            inputSchema={
                "type": "object",
                "properties": {
                    "question_index": {"type": "integer", "description": "Index of the question in the current quiz (0-based)"},
                },
                "required": ["question_index"],
            },
        ),
        Tool(
            name="compare_attempts",
            description="Compare two quiz attempts side by side to see improvement.",
            inputSchema={
                "type": "object",
                "properties": {
                    "attempt_a": {"type": "integer", "description": "First attempt number"},
                    "attempt_b": {"type": "integer", "description": "Second attempt number"},
                },
                "required": ["attempt_a", "attempt_b"],
            },
        ),
        Tool(
            name="generate_flashcards",
            description="Convert wrong answers into flashcard format (front: question, back: answer + explanation).",
            inputSchema={"type": "object", "properties": {}},
        ),
        Tool(
            name="get_topic_summary",
            description="Generate a knowledge summary for a specific chapter/topic from the study material.",
            inputSchema={
                "type": "object",
                "properties": {
                    "topic": {"type": "string", "description": "Topic or chapter name to summarize"},
                },
                "required": ["topic"],
            },
        ),
        Tool(
            name="set_preferences",
            description="Set the quiz buddy personality style and feedback language.",
            inputSchema={
                "type": "object",
                "properties": {
                    "style": {
                        "type": "string",
                        "enum": list(STYLE_DESCRIPTIONS.keys()),
                        "description": "Interaction style",
                    },
                    "language": {"type": "string", "description": "Feedback language (e.g., English, Chinese, French, Korean)"},
                },
            },
        ),
    ]


@server.call_tool()
async def call_tool(name: str, arguments: dict):
    _ensure_init()
    trace_event(f"tool_call:{name}", arguments)

    # ---- Tool implementations ----

    if name == "search_study_material":
        query = arguments["query"]
        n = arguments.get("num_results", 5)
        results = search(query, n_results=n)
        return [TextContent(
            type="text",
            text=json.dumps(results, indent=2, ensure_ascii=False),
        )]

    elif name == "generate_quiz":
        num = arguments.get("num_questions", 10)
        topic = arguments.get("topic")
        clear_wrong_answers()

        questions = generate_questions(
            num_questions=num,
            topic=topic,
            system_prompt=_session["system_prompt"],
        )
        _session["questions"] = questions
        _session["current_index"] = 0
        _session["user_answers"] = []
        _session["active"] = True

        summary = []
        for i, q in enumerate(questions):
            opts = " | ".join(f"{k}: {v}" for k, v in q["options"].items())
            summary.append(f"Q{i+1}: {q['question']}\n  {opts}")

        return [TextContent(
            type="text",
            text=f"Quiz started! {len(questions)} questions generated.\n\n" + "\n\n".join(summary),
        )]

    elif name == "answer_question":
        if not _session["active"] or not _session["questions"]:
            return [TextContent(type="text", text="No active quiz. Use generate_quiz first.")]

        idx = _session["current_index"]
        if idx >= len(_session["questions"]):
            return [TextContent(type="text", text="Quiz complete! All questions answered.")]

        question = _session["questions"][idx]
        answer = arguments["answer"]
        feedback = grade_single(question, answer)

        _session["user_answers"].append(answer.upper())
        _session["current_index"] += 1

        remaining = len(_session["questions"]) - _session["current_index"]

        result_text = json.dumps({
            "question_number": idx + 1,
            "correct": feedback["correct"],
            "your_answer": f"{answer}) {question['options'].get(answer, '')}",
            "correct_answer": f"{feedback['correct_answer']}) {feedback['correct_text']}",
            "remaining": remaining,
        }, indent=2, ensure_ascii=False)

        if remaining == 0:
            full_result = grade_quiz(_session["questions"], _session["user_answers"])
            save_score(full_result["score"], full_result["total"])
            _session["active"] = False
            result_text += f"\n\nQuiz Complete! Score: {full_result['score']}/{full_result['total']} ({full_result['percentage']*100:.0f}%)"
            result_text += f"\n{'PASSED!' if full_result['passed'] else 'Not passed. 75% required.'}"

        return [TextContent(type="text", text=result_text)]

    elif name == "get_wrong_answers":
        topic_filter = arguments.get("topic")
        if topic_filter:
            by_topic = get_wrong_by_topic()
            matching = {}
            for t, items in by_topic.items():
                if topic_filter.lower() in t.lower():
                    matching[t] = items
            return [TextContent(type="text", text=json.dumps(matching, indent=2, ensure_ascii=False))]
        else:
            wrong = load_wrong_answers()
            return [TextContent(type="text", text=json.dumps(wrong, indent=2, ensure_ascii=False))]

    elif name == "review_weak_topics":
        by_topic = get_wrong_by_topic()
        if not by_topic:
            return [TextContent(type="text", text="No wrong answers recorded. Take a quiz first!")]

        analysis = []
        for topic, items in sorted(by_topic.items(), key=lambda x: len(x[1]), reverse=True):
            analysis.append({
                "topic": topic,
                "wrong_count": len(items),
                "questions": [w["question"] for w in items],
                "recommendation": f"Review the '{topic}' chapter in Discover Canada.",
            })

        passages = []
        for topic in list(by_topic.keys())[:3]:
            results = search(topic, n_results=2)
            passages.extend(results)

        return [TextContent(type="text", text=json.dumps({
            "weak_topics": analysis,
            "recommended_study_material": passages,
        }, indent=2, ensure_ascii=False))]

    elif name == "get_score_history":
        history = get_score_history()
        return [TextContent(type="text", text=json.dumps(history, indent=2, ensure_ascii=False))]

    elif name == "get_study_analytics":
        analytics = get_analytics()
        return [TextContent(type="text", text=json.dumps(analytics, indent=2, ensure_ascii=False))]

    elif name == "predict_exam_readiness":
        prediction = predict_readiness()
        return [TextContent(type="text", text=json.dumps(prediction, indent=2, ensure_ascii=False))]

    elif name == "send_report_email":
        email_to = arguments["email"]
        include_wrong = arguments.get("include_wrong_answers", True)

        analytics = get_analytics()
        wrong = load_wrong_answers() if include_wrong else []

        body = f"Maple Quiz Buddy - Study Report\n{'='*40}\n\n"
        body += f"Date: {date.today()}\n"
        body += f"Total Attempts: {analytics.get('total_attempts', 0)}\n"
        body += f"Average Score: {analytics.get('average_score', 0)*100:.0f}%\n"
        body += f"Best Score: {analytics.get('best_percentage', 0)*100:.0f}%\n"
        body += f"Pass Rate: {analytics.get('pass_rate', 0)*100:.0f}%\n"
        body += f"Trend: {analytics.get('trend', 'N/A')}\n"

        if wrong:
            body += f"\nWrong Answers ({len(wrong)}):\n{'-'*30}\n"
            for w in wrong:
                body += f"Q: {w['question']}\n"
                body += f"Your answer: {w['user_answer']} | Correct: {w['correct_answer']}\n"
                body += f"Topic: {w.get('topic', 'N/A')}\n\n"

        readiness = predict_readiness()
        body += f"\nExam Readiness: {readiness['message']}\n"

        if config.is_sandbox() or not config.SMTP_EMAIL:
            return [TextContent(type="text", text=f"[Sandbox] Email report generated for {email_to}:\n\n{body}")]

        try:
            msg = MIMEMultipart()
            msg["From"] = config.SMTP_EMAIL
            msg["To"] = email_to
            msg["Subject"] = f"Maple Quiz Buddy - Study Report ({date.today()})"
            msg.attach(MIMEText(body, "plain"))

            with smtplib.SMTP(config.SMTP_HOST, config.SMTP_PORT) as smtp:
                smtp.starttls()
                smtp.login(config.SMTP_EMAIL, config.SMTP_PASSWORD)
                smtp.send_message(msg)

            return [TextContent(type="text", text=f"Report sent to {email_to}!")]
        except Exception as e:
            return [TextContent(type="text", text=f"Failed to send email: {e}")]

    elif name == "schedule_reminder":
        message = arguments["message"]
        days = arguments.get("days_from_now", 1)
        return [TextContent(type="text", text=json.dumps({
            "status": "reminder_set",
            "message": message,
            "remind_date": str(date.today()),
            "days_from_now": days,
            "note": "Reminder registered. The host application handles actual scheduling.",
        }, indent=2))]

    elif name == "explain_answer":
        idx = arguments["question_index"]
        questions = _session.get("questions", [])
        if idx < 0 or idx >= len(questions):
            return [TextContent(type="text", text=f"Invalid index. Quiz has {len(questions)} questions (0-{len(questions)-1}).")]

        q = questions[idx]
        source_results = search(q["question"], n_results=3)

        explanation = {
            "question": q["question"],
            "correct_answer": f"{q['answer']}) {q['options'][q['answer']]}",
            "all_options": q["options"],
            "source_text": q.get("source_text", ""),
            "related_passages": source_results,
            "topic": q.get("topic", ""),
        }
        return [TextContent(type="text", text=json.dumps(explanation, indent=2, ensure_ascii=False))]

    elif name == "compare_attempts":
        result = compare_attempts(arguments["attempt_a"], arguments["attempt_b"])
        return [TextContent(type="text", text=json.dumps(result, indent=2, ensure_ascii=False))]

    elif name == "generate_flashcards":
        wrong = load_wrong_answers()
        if not wrong:
            return [TextContent(type="text", text="No wrong answers to create flashcards from. Take a quiz first!")]

        cards = []
        for w in wrong:
            cards.append({
                "front": w["question"],
                "back": f"Answer: {w['correct_answer']}) {w.get('correct_text', '')}\n\nSource: {w.get('source_text', 'N/A')}",
                "topic": w.get("topic", ""),
            })
        return [TextContent(type="text", text=json.dumps({"flashcards": cards, "total": len(cards)}, indent=2, ensure_ascii=False))]

    elif name == "get_topic_summary":
        topic = arguments["topic"]
        results = search(topic, n_results=5)
        return [TextContent(type="text", text=json.dumps({
            "topic": topic,
            "passages": results,
            "passage_count": len(results),
        }, indent=2, ensure_ascii=False))]

    elif name == "set_preferences":
        style = arguments.get("style", _session["style"])
        language = arguments.get("language", _session["language"])

        try:
            style = validate_style(style)
            language = validate_language(language)
        except ValueError as e:
            return [TextContent(type="text", text=f"Error: {e}")]

        _session["style"] = style
        _session["language"] = language
        _session["system_prompt"] = generate_system_prompt(style, language)

        return [TextContent(type="text", text=json.dumps({
            "style": style,
            "language": language,
            "description": STYLE_DESCRIPTIONS.get(style, ""),
            "status": "preferences_updated",
        }, indent=2))]

    return [TextContent(type="text", text=f"Unknown tool: {name}")]


# ========================================
#  RESOURCES (5 total)
# ========================================

@server.list_resources()
async def list_resources():
    return [
        Resource(
            uri="quiz://status",
            name="Quiz Session Status",
            description="Current quiz session state: active quiz, progress, current question.",
            mimeType="application/json",
        ),
        Resource(
            uri="quiz://history",
            name="Score History",
            description="Complete score history across all quiz attempts.",
            mimeType="application/json",
        ),
        Resource(
            uri="quiz://wrong-answers",
            name="Wrong Answers",
            description="Current wrong answer log with topics and source references.",
            mimeType="application/json",
        ),
        Resource(
            uri="quiz://study-tips",
            name="Study Tips",
            description="Personalized study tips based on performance and weak areas.",
            mimeType="application/json",
        ),
        Resource(
            uri="quiz://progress",
            name="Progress Dashboard",
            description="Full progress dashboard data: analytics, readiness, trends.",
            mimeType="application/json",
        ),
    ]


@server.read_resource()
async def read_resource(uri: str):
    _ensure_init()

    if uri == "quiz://status":
        data = {
            "active": _session["active"],
            "style": _session["style"],
            "language": _session["language"],
            "total_questions": len(_session["questions"]),
            "answered": _session["current_index"],
            "remaining": max(0, len(_session["questions"]) - _session["current_index"]),
            "current_question": _session.get("current_question"),
        }
        return json.dumps(data, indent=2, ensure_ascii=False)

    elif uri == "quiz://history":
        return json.dumps(get_score_history(), indent=2, ensure_ascii=False)

    elif uri == "quiz://wrong-answers":
        return json.dumps({
            "wrong_answers": load_wrong_answers(),
            "by_topic": get_wrong_by_topic(),
            "total": get_wrong_count(),
        }, indent=2, ensure_ascii=False)

    elif uri == "quiz://study-tips":
        by_topic = get_wrong_by_topic()
        analytics = get_analytics()
        readiness = predict_readiness()

        tips = []
        if not by_topic:
            tips.append("Take a quiz first to get personalized study tips!")
        else:
            for topic, items in sorted(by_topic.items(), key=lambda x: len(x[1]), reverse=True):
                tips.append(f"Focus on '{topic}' - you missed {len(items)} question(s) in this area.")

        if analytics.get("trend") == "declining":
            tips.append("Your scores are declining. Consider reviewing fundamentals before taking more quizzes.")
        elif analytics.get("trend") == "improving":
            tips.append("Great trend! Keep up the momentum.")

        return json.dumps({
            "tips": tips,
            "weak_topics": list(by_topic.keys()),
            "readiness": readiness,
        }, indent=2, ensure_ascii=False)

    elif uri == "quiz://progress":
        return json.dumps({
            "analytics": get_analytics(),
            "readiness": predict_readiness(),
            "best_score": get_best_score(),
            "latest_score": get_latest_score(),
            "summary": get_progress_summary(),
        }, indent=2, ensure_ascii=False)

    raise ValueError(f"Unknown resource: {uri}")


# ========================================
#  PROMPTS (3 total)
# ========================================

@server.list_prompts()
async def list_prompts():
    return [
        Prompt(
            name="quiz-start",
            description="Start a Canadian citizenship quiz with your preferred style and language.",
            arguments=[
                PromptArgument(
                    name="style",
                    description="Personality style (Funny Buddy, Strict Teacher, Warm Encourager, Drill Sergeant)",
                    required=False,
                ),
                PromptArgument(
                    name="language",
                    description="Feedback language (English, Chinese, French, Korean, etc.)",
                    required=False,
                ),
                PromptArgument(
                    name="num_questions",
                    description="Number of questions (default: 10)",
                    required=False,
                ),
            ],
        ),
        Prompt(
            name="study-guide",
            description="Generate a study guide focusing on your weak areas based on past quiz performance.",
            arguments=[],
        ),
        Prompt(
            name="practice-topic",
            description="Practice questions on a specific topic from Discover Canada.",
            arguments=[
                PromptArgument(
                    name="topic",
                    description="Topic to practice (e.g., Canadian History, Rights and Responsibilities, Regions of Canada)",
                    required=True,
                ),
            ],
        ),
    ]


@server.get_prompt()
async def get_prompt(name: str, arguments: dict = None):
    arguments = arguments or {}

    if name == "quiz-start":
        style = arguments.get("style", "Warm Encourager")
        language = arguments.get("language", "English")
        num = arguments.get("num_questions", "10")

        return GetPromptResult(
            messages=[
                PromptMessage(
                    role="user",
                    content=TextContent(
                        type="text",
                        text=(
                            f"I want to practice for the Canadian citizenship test. "
                            f"Please set my preferences to {style} style with {language} feedback, "
                            f"then generate a quiz with {num} questions. "
                            f"Present each question one at a time and wait for my answer before moving on. "
                            f"After all questions, show my score and offer to review wrong answers."
                        ),
                    ),
                ),
            ],
        )

    elif name == "study-guide":
        return GetPromptResult(
            messages=[
                PromptMessage(
                    role="user",
                    content=TextContent(
                        type="text",
                        text=(
                            "Based on my quiz history and wrong answers, create a personalized study guide. "
                            "First check my study analytics and wrong answers, then: "
                            "1) List my weakest topics ranked by number of mistakes. "
                            "2) For each weak topic, search the study material and provide a concise summary. "
                            "3) Generate 3 practice questions per weak topic. "
                            "4) Give me an exam readiness prediction. "
                            "Make it encouraging but honest."
                        ),
                    ),
                ),
            ],
        )

    elif name == "practice-topic":
        topic = arguments.get("topic", "Canadian History")
        return GetPromptResult(
            messages=[
                PromptMessage(
                    role="user",
                    content=TextContent(
                        type="text",
                        text=(
                            f"I want to practice the topic '{topic}' for my Canadian citizenship test. "
                            f"First search the study material for '{topic}' and give me a brief summary. "
                            f"Then generate 5 quiz questions specifically about this topic. "
                            f"Present them one at a time and explain each answer after I respond."
                        ),
                    ),
                ),
            ],
        )

    raise ValueError(f"Unknown prompt: {name}")


# ========================================
#  Main entry point
# ========================================

async def main():
    async with run_stdio(server) as streams:
        await server.run(
            streams[0], streams[1],
            server.create_initialization_options(),
        )


if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
