# CLAUDE.md - Maple Quiz Buddy V2

## Architecture: LangGraph + MCP + LangFuse

V2 is a complete rewrite using:
- **LangGraph** - State machine for quiz flow (replaces linear app.py)
- **MCP Server** - Model Context Protocol server (works with Claude Desktop + Claude Code)
- **LangFuse** - Observability & tracing for all LLM calls
- **xAI Grok** - LLM backend via `langchain-xai`
- **ChromaDB** - Vector store for RAG

## Project Structure

```
Maple_Quiz_Buddy_V2/
├── CLAUDE.md
├── .env
├── .gitignore
├── config.py                         # Global config from .env
├── requirements.txt
├── app.py                            # CLI entry point (runs LangGraph)
│
├── personality/
│   ├── style_selector.py             # Onboarding: style + language
│   └── buddy_prompts.py             # System prompt generator
│
├── rag/
│   ├── pdf_loader.py                 # PDF chunking
│   └── vector_store.py              # ChromaDB embed + retrieve
│
├── quiz/
│   ├── question_generator.py         # RAG + Grok quiz generation
│   ├── grader.py                     # Grade answers, log wrong ones
│   └── review_manager.py            # Wrong answer review
│
├── memory/
│   └── score_tracker.py             # Score history + progress
│
├── graph/
│   └── quiz_graph.py                # LangGraph StateGraph definition
│
├── mcp_server/
│   ├── server.py                     # MCP server (stdio transport)
│   └── claude_desktop_config.json   # Example Claude Desktop config
│
├── observability/
│   └── tracing.py                   # LangFuse callback setup
│
├── data/
│   ├── discover_canada.pdf          # Study material (user uploads)
│   ├── vectorstore/                 # ChromaDB persistent dir
│   ├── score_log.json
│   └── wrong_answers.json
│
└── v1_reference/                    # V1 source files for reference
```

## Implementation Order

1. Base files (.env, config.py, requirements.txt, .gitignore, data/)
2. personality/ (style_selector + buddy_prompts)
3. rag/ (pdf_loader + vector_store)
4. quiz/ (question_generator + grader + review_manager)
5. memory/ (score_tracker)
6. observability/ (LangFuse tracing)
7. graph/ (LangGraph state machine)
8. mcp_server/ (MCP server with tools + resources + prompts)
9. app.py (CLI entry point)

## Code Standards

- All code, comments, variable names in English
- All API keys from config.py, no hardcoding
- Sandbox mode: config.is_sandbox() returns mock data
- Every module has a top-level docstring: purpose, inputs, outputs, deps

## MCP Server Features

### Tools (Claude calls these)
- `start_quiz` - Begin a new quiz session
- `answer_question` - Submit answer to current question
- `get_score` - Get current/historical scores
- `review_wrong` - Start wrong answer review
- `search_study_material` - RAG search Discover Canada
- `get_quiz_stats` - Detailed quiz statistics
- `set_preferences` - Set style + language
- `export_results` - Export quiz results as JSON
- `get_upcoming_dates` - Citizenship test date info
- `send_results_email` - Email quiz results via Gmail

### Resources (Claude reads these)
- `quiz://status` - Current quiz session state
- `quiz://history` - All past quiz attempts
- `quiz://wrong-answers` - Current wrong answers
- `quiz://study-tips` - Study tips based on performance
- `quiz://progress` - Progress dashboard data

### Prompts (Preset templates)
- `quiz-start` - Start a quiz with style/language
- `study-guide` - Generate study guide from weak areas
- `practice-topic` - Practice specific topic

## LangGraph Flow

```
[onboard] -> [load_pdf] -> [generate_quiz] -> [answer] -> [grade]
                                                  ^          |
                                                  |          v
                                              [answer] <- [next_q]
                                                            |
                                                            v
                                                       [summary] -> [review?] -> [end]
                                                                        |
                                                                        v
                                                                   [review_quiz]
```
