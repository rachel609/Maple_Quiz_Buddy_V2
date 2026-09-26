"""
Maple Quiz Buddy V2 - Streamlit Web Frontend

Purpose: Browser-based UI with full V2 features: quiz, analytics dashboard,
         exam readiness prediction, flashcards, weak topic analysis.
Run with: streamlit run web_app.py
Dependencies: All project modules + streamlit.
"""

import streamlit as st
import json
import config
from personality.style_selector import STYLES, LANGUAGES, STYLE_DESCRIPTIONS
from personality.buddy_prompts import generate_system_prompt, get_feedback_prompt
from rag.vector_store import load_vector_store, search
from quiz.question_generator import generate_questions
from quiz.grader import (
    grade_single, grade_quiz, clear_wrong_answers,
    load_wrong_answers, get_wrong_by_topic,
)
from quiz.review_manager import get_review_questions, has_wrong_answers, get_wrong_count
from memory.score_tracker import (
    save_score, get_score_history, get_attempt_count,
    get_analytics, predict_readiness, compare_attempts,
    get_best_score, get_latest_score,
)

# -- Page Config --
st.set_page_config(
    page_title="Maple Quiz Buddy V2",
    page_icon="🍁",
    layout="centered",
)

# -- Custom CSS --
st.markdown("""
<style>
    .maple-title {
        color: #FF0000;
        font-size: 2.5rem;
        font-weight: 800;
        text-align: center;
        margin-bottom: 0;
    }
    .maple-subtitle {
        color: #666;
        text-align: center;
        font-size: 1.1rem;
        margin-top: 0;
    }
    .red-divider {
        border: none;
        border-top: 3px solid #FF0000;
        margin: 1rem 0;
    }
    .score-card {
        background: linear-gradient(135deg, #FF0000 0%, #CC0000 100%);
        color: white;
        padding: 2rem;
        border-radius: 1rem;
        text-align: center;
        margin: 1rem 0;
    }
    .score-card h1 { font-size: 3rem; margin: 0; color: white; }
    .score-card p { font-size: 1.2rem; margin: 0.5rem 0 0 0; color: #FFD4D4; }
    .pass-banner {
        background: #28a745; color: white; padding: 1rem;
        border-radius: 0.5rem; text-align: center; font-size: 1.5rem; font-weight: bold;
    }
    .fail-banner {
        background: #dc3545; color: white; padding: 1rem;
        border-radius: 0.5rem; text-align: center; font-size: 1.5rem; font-weight: bold;
    }
    .question-card {
        background: #FFF5F5; border-left: 4px solid #FF0000;
        padding: 1.5rem; border-radius: 0 0.5rem 0.5rem 0; margin: 1rem 0;
    }
    .flashcard-front {
        background: #f8f9fa; border: 2px solid #dee2e6;
        padding: 1.5rem; border-radius: 0.5rem; margin: 0.5rem 0;
        font-weight: bold;
    }
    .flashcard-back {
        background: #e8f5e9; border: 2px solid #a5d6a7;
        padding: 1.5rem; border-radius: 0.5rem; margin: 0.5rem 0;
    }
    .topic-badge {
        display: inline-block; background: #FF0000; color: white;
        padding: 0.2rem 0.6rem; border-radius: 1rem; font-size: 0.8rem;
        margin: 0.2rem;
    }
    .readiness-high { color: #28a745; font-size: 2rem; font-weight: bold; }
    .readiness-mid { color: #ffc107; font-size: 2rem; font-weight: bold; }
    .readiness-low { color: #dc3545; font-size: 2rem; font-weight: bold; }
    [data-testid="stSidebar"] { background-color: #FFF8F8; }
    .stButton > button {
        background-color: #FF0000; color: white; border: none;
        border-radius: 0.5rem; padding: 0.5rem 2rem; font-weight: bold;
    }
    .stButton > button:hover { background-color: #CC0000; color: white; }
</style>
""", unsafe_allow_html=True)


# -- Cached Resources --
@st.cache_resource(show_spinner="Loading study materials...")
def init_vector_store():
    load_vector_store()


# -- LLM Feedback Helper --
def get_llm_feedback(system_prompt: str, feedback_prompt: str) -> str:
    if config.is_sandbox():
        return ""
    try:
        from langchain_xai import ChatXAI
        from langchain_core.prompts import ChatPromptTemplate
        prompt = ChatPromptTemplate.from_messages([
            ("system", system_prompt),
            ("human", "{feedback}"),
        ])
        llm = ChatXAI(model=config.GROK_MODEL, api_key=config.XAI_API_KEY)
        chain = prompt | llm
        response = chain.invoke({"feedback": feedback_prompt})
        return response.content
    except Exception as e:
        return f"(Feedback unavailable: {e})"


# -- Session State --
def init_state():
    defaults = {
        "phase": "onboarding",
        "style": None, "language": None, "system_prompt": "",
        "questions": [], "current_q": 0, "user_answers": [],
        "answered": False, "feedback_text": "", "quiz_result": None,
        "review_questions": [], "review_current_q": 0, "review_answers": [],
        "review_answered": False, "review_feedback": "", "review_result": None,
    }
    for key, val in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = val

init_state()


# -- Header --
def render_header():
    st.markdown(
        '<div style="text-align:center;">'
        '<span style="font-size:4rem;">🍁</span><br>'
        '<p class="maple-title">Maple Quiz Buddy V2</p>'
        '<p class="maple-subtitle">Canadian Citizenship Test Prep &mdash; LangGraph + MCP + LangFuse</p>'
        '</div>',
        unsafe_allow_html=True,
    )
    st.markdown('<hr class="red-divider">', unsafe_allow_html=True)


# -- Sidebar Navigation --
def render_sidebar():
    with st.sidebar:
        st.markdown("### Navigation")

        if st.session_state.style:
            st.caption(f"Style: {st.session_state.style}")
            st.caption(f"Language: {st.session_state.language}")
            st.markdown("---")

        if st.button("🍁 Quiz", use_container_width=True):
            if st.session_state.style:
                st.session_state.phase = "quiz" if st.session_state.questions else "onboarding"
            else:
                st.session_state.phase = "onboarding"
            st.rerun()

        if st.button("📊 Analytics", use_container_width=True):
            st.session_state.phase = "analytics"
            st.rerun()

        if st.button("🎯 Exam Readiness", use_container_width=True):
            st.session_state.phase = "readiness"
            st.rerun()

        if st.button("📝 Wrong Answers", use_container_width=True):
            st.session_state.phase = "wrong_answers"
            st.rerun()

        if st.button("🃏 Flashcards", use_container_width=True):
            st.session_state.phase = "flashcards"
            st.rerun()

        if st.button("📚 Study Material", use_container_width=True):
            st.session_state.phase = "study"
            st.rerun()

        if st.button("📈 Score History", use_container_width=True):
            st.session_state.phase = "history"
            st.rerun()

        st.markdown("---")
        if st.button("🏠 Start Over", use_container_width=True):
            for key in list(st.session_state.keys()):
                del st.session_state[key]
            st.rerun()

        if config.is_sandbox():
            st.markdown("---")
            st.warning("Sandbox Mode")


# ============================================================
#  PHASE: Onboarding
# ============================================================
def render_onboarding():
    st.markdown("### Welcome! Let's set up your quiz experience.")

    st.markdown("#### Choose Your Quiz Buddy Style")
    style_names = list(STYLES.values())
    style_choice = st.radio(
        "Pick a personality:",
        style_names,
        format_func=lambda s: f"{s} -- {STYLE_DESCRIPTIONS[s]}",
        index=0,
        label_visibility="collapsed",
    )

    st.markdown("#### Choose Feedback Language")
    st.caption("Quiz questions are always in English. Feedback uses your chosen language.")
    lang_options = list(LANGUAGES.values()) + ["Other"]
    lang_choice = st.selectbox("Language:", lang_options, index=0)

    custom_lang = ""
    if lang_choice == "Other":
        custom_lang = st.text_input("Type your language:")

    num_q = st.slider("Number of questions:", 5, 20, 10)

    topic = st.text_input("Focus on a topic (optional):", placeholder="e.g., Canadian History, Rights and Responsibilities")

    st.markdown("---")
    if st.button("🍁 Start Quiz", use_container_width=True):
        final_lang = custom_lang if lang_choice == "Other" and custom_lang else lang_choice
        if lang_choice == "Other" and not custom_lang:
            st.warning("Please type a language.")
            return

        st.session_state.style = style_choice
        st.session_state.language = final_lang
        st.session_state.system_prompt = generate_system_prompt(style_choice, final_lang)

        init_vector_store()
        clear_wrong_answers()

        with st.spinner("Generating quiz questions..."):
            st.session_state.questions = generate_questions(
                num_questions=num_q,
                topic=topic if topic.strip() else None,
                system_prompt=st.session_state.system_prompt,
            )
        st.session_state.user_answers = []
        st.session_state.current_q = 0
        st.session_state.answered = False
        st.session_state.feedback_text = ""
        st.session_state.phase = "quiz"
        st.rerun()


# ============================================================
#  PHASE: Quiz
# ============================================================
def render_quiz():
    questions = st.session_state.questions
    if not questions:
        st.info("No active quiz. Start one from the sidebar or home page.")
        if st.button("🍁 Start New Quiz"):
            st.session_state.phase = "onboarding"
            st.rerun()
        return

    idx = st.session_state.current_q
    total = len(questions)

    if idx >= total:
        _finish_quiz()
        return

    q = questions[idx]

    st.progress(idx / total, text=f"Question {idx + 1} of {total}")
    attempt = get_attempt_count() + 1
    st.caption(f"Attempt #{attempt}")

    st.markdown(
        f'<div class="question-card"><strong>Q{idx + 1}.</strong> {q["question"]}</div>',
        unsafe_allow_html=True,
    )

    option_labels = [f"{letter}) {text}" for letter, text in q["options"].items()]
    selected = st.radio("Choose:", option_labels, index=None, key=f"q_{idx}", label_visibility="collapsed")

    if not st.session_state.answered:
        if st.button("Submit Answer", use_container_width=True, disabled=selected is None):
            if selected is None:
                return
            answer_letter = selected[0]
            st.session_state.user_answers.append(answer_letter)
            st.session_state.answered = True

            feedback = grade_single(q, answer_letter)
            if feedback["correct"]:
                st.session_state.feedback_text = "Correct!"
            else:
                st.session_state.feedback_text = (
                    f"Wrong. The correct answer is: "
                    f"{feedback['correct_answer']}) {feedback['correct_text']}"
                )
            st.rerun()
    else:
        feedback_text = st.session_state.feedback_text
        answer_letter = st.session_state.user_answers[-1]
        is_correct = answer_letter == q["answer"]

        if is_correct:
            st.success(feedback_text)
        else:
            st.error(feedback_text)
            if q.get("source_text"):
                st.caption(f"Source: {q['source_text']}")

        if st.button("Next Question -->", use_container_width=True):
            st.session_state.current_q += 1
            st.session_state.answered = False
            st.session_state.feedback_text = ""
            st.rerun()


def _finish_quiz():
    result = grade_quiz(st.session_state.questions, st.session_state.user_answers)
    save_score(result["score"], result["total"])
    st.session_state.quiz_result = result
    st.session_state.phase = "results"
    st.rerun()


# ============================================================
#  PHASE: Results
# ============================================================
def render_results():
    result = st.session_state.quiz_result
    if not result:
        st.session_state.phase = "onboarding"
        st.rerun()
        return

    score = result["score"]
    total = result["total"]
    pct = result["percentage"] * 100

    st.markdown(
        f'<div class="score-card"><h1>{score}/{total}</h1><p>{pct:.0f}%</p></div>',
        unsafe_allow_html=True,
    )

    if result["passed"]:
        st.markdown('<div class="pass-banner">PASSED!</div>', unsafe_allow_html=True)
    else:
        st.markdown('<div class="fail-banner">NOT PASSED (need 75%)</div>', unsafe_allow_html=True)

    st.markdown("---")

    wrong_count = get_wrong_count()
    col1, col2, col3 = st.columns(3)

    with col1:
        if wrong_count > 0 and st.button(f"Review ({wrong_count} wrong)", use_container_width=True):
            _start_review()

    with col2:
        if get_attempt_count() < config.MAX_ATTEMPTS:
            if st.button("Try Again", use_container_width=True):
                _start_new_quiz()

    with col3:
        if st.button("Analytics", use_container_width=True):
            st.session_state.phase = "analytics"
            st.rerun()


def _start_review():
    st.session_state.review_questions = get_review_questions()
    st.session_state.review_current_q = 0
    st.session_state.review_answers = []
    st.session_state.review_answered = False
    st.session_state.review_feedback = ""
    st.session_state.phase = "review"
    st.rerun()


def _start_new_quiz():
    clear_wrong_answers()
    with st.spinner("Generating new questions..."):
        st.session_state.questions = generate_questions(
            num_questions=len(st.session_state.questions),
            system_prompt=st.session_state.system_prompt,
        )
    st.session_state.user_answers = []
    st.session_state.current_q = 0
    st.session_state.answered = False
    st.session_state.feedback_text = ""
    st.session_state.quiz_result = None
    st.session_state.phase = "quiz"
    st.rerun()


# ============================================================
#  PHASE: Review
# ============================================================
def render_review():
    questions = st.session_state.review_questions
    idx = st.session_state.review_current_q
    total = len(questions)

    if not questions:
        st.info("No wrong answers to review.")
        return

    if idx >= total:
        correct = sum(
            1 for q, a in zip(questions, st.session_state.review_answers)
            if a.upper() == q["answer"].upper()
        )
        st.markdown("### Review Complete!")
        st.markdown(
            f'<div class="score-card"><h1>{correct}/{total}</h1><p>Review Score</p></div>',
            unsafe_allow_html=True,
        )
        if correct == total:
            st.success("All review questions correct!")
        else:
            st.warning(f"Still missed {total - correct} question(s).")

        if st.button("Back to Results"):
            st.session_state.phase = "results"
            st.rerun()
        return

    st.markdown("### Review Mode")
    st.progress(idx / total, text=f"Review {idx + 1} of {total}")

    q = questions[idx]
    st.markdown(
        f'<div class="question-card"><strong>Q{idx + 1}.</strong> {q["question"]}</div>',
        unsafe_allow_html=True,
    )

    if q.get("source_text"):
        st.info(f"Hint: {q['source_text'][:200]}...")

    option_labels = [f"{letter}) {text}" for letter, text in q["options"].items()] if q["options"] else []

    if option_labels:
        selected = st.radio("Answer:", option_labels, index=None, key=f"rev_{idx}", label_visibility="collapsed")
    else:
        selected = st.text_input("Type the correct letter (A/B/C/D):", key=f"rev_{idx}")

    if not st.session_state.review_answered:
        if st.button("Submit", use_container_width=True):
            answer = selected[0] if selected and len(selected) > 0 else ""
            if not answer:
                return
            st.session_state.review_answers.append(answer.upper())
            st.session_state.review_answered = True

            if answer.upper() == q["answer"].upper():
                st.session_state.review_feedback = "Correct!"
            else:
                st.session_state.review_feedback = f"Wrong. Answer: {q['answer']}"
            st.rerun()
    else:
        answer = st.session_state.review_answers[-1]
        if answer == q["answer"].upper():
            st.success(st.session_state.review_feedback)
        else:
            st.error(st.session_state.review_feedback)

        if st.button("Next -->", use_container_width=True):
            st.session_state.review_current_q += 1
            st.session_state.review_answered = False
            st.session_state.review_feedback = ""
            st.rerun()


# ============================================================
#  PHASE: Analytics Dashboard
# ============================================================
def render_analytics():
    st.markdown("### Analytics Dashboard")

    analytics = get_analytics()

    if analytics["total_attempts"] == 0:
        st.info("No quiz data yet. Take a quiz first!")
        return

    # Key metrics
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Total Attempts", analytics["total_attempts"])
    col2.metric("Average Score", f"{analytics['average_score']*100:.0f}%")
    col3.metric("Best Score", f"{analytics['best_percentage']*100:.0f}%")
    col4.metric("Pass Rate", f"{analytics['pass_rate']*100:.0f}%")

    # Trend
    trend = analytics["trend"]
    if trend == "improving":
        st.success("Trend: Improving!")
    elif trend == "declining":
        st.warning("Trend: Declining. Review weak areas.")
    else:
        st.info("Trend: Stable")

    improvement = analytics["improvement"]
    if analytics["total_attempts"] >= 2:
        st.metric(
            "Improvement (first to last)",
            f"{improvement*100:+.0f}%",
            delta=f"{improvement*100:+.0f}%",
        )

    # Score chart
    history = analytics.get("history", [])
    if len(history) >= 2:
        st.markdown("#### Score Trend")
        import pandas as pd
        df = pd.DataFrame(history)
        df["percentage"] = df["percentage"] * 100
        st.line_chart(df.set_index("attempt")["percentage"], use_container_width=True)

    # Weak topics
    st.markdown("#### Weak Topics")
    by_topic = get_wrong_by_topic()
    if by_topic:
        for topic, items in sorted(by_topic.items(), key=lambda x: len(x[1]), reverse=True):
            st.markdown(f'<span class="topic-badge">{topic}: {len(items)} wrong</span>', unsafe_allow_html=True)
    else:
        st.success("No weak topics! All answers correct.")

    # Compare attempts
    if analytics["total_attempts"] >= 2:
        st.markdown("#### Compare Attempts")
        col1, col2 = st.columns(2)
        with col1:
            a = st.number_input("Attempt A:", min_value=1, max_value=analytics["total_attempts"], value=1)
        with col2:
            b = st.number_input("Attempt B:", min_value=1, max_value=analytics["total_attempts"], value=analytics["total_attempts"])

        if a != b:
            comp = compare_attempts(a, b)
            if "error" not in comp:
                delta = comp["percentage_change"] * 100
                st.metric(
                    f"Attempt {a} vs Attempt {b}",
                    f"{comp['attempt_b']['percentage']*100:.0f}%",
                    delta=f"{delta:+.0f}%",
                )


# ============================================================
#  PHASE: Exam Readiness
# ============================================================
def render_readiness():
    st.markdown("### Exam Readiness Prediction")

    prediction = predict_readiness()

    confidence = prediction["confidence"] * 100
    if confidence >= 70:
        css_class = "readiness-high"
        icon = "🟢"
    elif confidence >= 50:
        css_class = "readiness-mid"
        icon = "🟡"
    else:
        css_class = "readiness-low"
        icon = "🔴"

    st.markdown(
        f'<div style="text-align:center; margin: 2rem 0;">'
        f'<p style="font-size:1.2rem; color:#666;">Confidence Score</p>'
        f'<p class="{css_class}">{icon} {confidence:.0f}%</p>'
        f'</div>',
        unsafe_allow_html=True,
    )

    if prediction["ready"]:
        st.success(prediction["message"])
    else:
        st.warning(prediction["message"])

    st.markdown("---")
    st.markdown("#### What This Means")
    if confidence >= 70:
        st.markdown("You're well-prepared. Consider doing a final review of any weak areas, then schedule your test.")
    elif confidence >= 50:
        st.markdown("You're getting close. Focus on the topics you've missed most often. A few more practice sessions should get you there.")
    else:
        st.markdown("More study time recommended. Use the Study Material search and Flashcards to strengthen your knowledge base.")

    analytics = get_analytics()
    if analytics["total_attempts"] > 0:
        st.markdown("---")
        st.markdown("#### Your Stats")
        col1, col2, col3 = st.columns(3)
        col1.metric("Quizzes Taken", analytics["total_attempts"])
        col2.metric("Average", f"{analytics['average_score']*100:.0f}%")
        col3.metric("Best", f"{analytics['best_percentage']*100:.0f}%")


# ============================================================
#  PHASE: Wrong Answers
# ============================================================
def render_wrong_answers():
    st.markdown("### Wrong Answers")

    wrong = load_wrong_answers()
    if not wrong:
        st.success("No wrong answers! Take a quiz to get started.")
        return

    by_topic = get_wrong_by_topic()

    st.metric("Total Wrong Answers", len(wrong))

    # Filter by topic
    topics = ["All"] + list(by_topic.keys())
    selected_topic = st.selectbox("Filter by topic:", topics)

    display = wrong if selected_topic == "All" else by_topic.get(selected_topic, [])

    for i, w in enumerate(display, 1):
        with st.expander(f"{i}. {w['question']}", expanded=False):
            st.markdown(f"**Your answer:** {w['user_answer']}")
            st.markdown(f"**Correct answer:** {w['correct_answer']}) {w.get('correct_text', '')}")
            if w.get("topic"):
                st.caption(f"Topic: {w['topic']}")
            if w.get("source_text"):
                st.info(f"Source: {w['source_text']}")
            st.caption(f"Date: {w.get('date', 'N/A')}")

    st.markdown("---")
    col1, col2 = st.columns(2)
    with col1:
        if st.button("Review Wrong Answers", use_container_width=True):
            _start_review()
    with col2:
        if st.button("Generate Flashcards", use_container_width=True):
            st.session_state.phase = "flashcards"
            st.rerun()


# ============================================================
#  PHASE: Flashcards
# ============================================================
def render_flashcards():
    st.markdown("### Flashcards")

    wrong = load_wrong_answers()
    if not wrong:
        st.info("No wrong answers to make flashcards from. Take a quiz first!")
        return

    st.caption(f"{len(wrong)} flashcard(s) generated from your wrong answers")

    if "flashcard_index" not in st.session_state:
        st.session_state.flashcard_index = 0
    if "flashcard_flipped" not in st.session_state:
        st.session_state.flashcard_flipped = False

    idx = st.session_state.flashcard_index
    if idx >= len(wrong):
        st.session_state.flashcard_index = 0
        idx = 0

    w = wrong[idx]
    st.progress((idx + 1) / len(wrong), text=f"Card {idx + 1} of {len(wrong)}")

    # Front
    st.markdown(f'<div class="flashcard-front">{w["question"]}</div>', unsafe_allow_html=True)

    if w.get("topic"):
        st.caption(f"Topic: {w['topic']}")

    # Flip button
    if st.button("Flip Card", use_container_width=True):
        st.session_state.flashcard_flipped = not st.session_state.flashcard_flipped
        st.rerun()

    # Back (when flipped)
    if st.session_state.flashcard_flipped:
        answer_text = f"**{w['correct_answer']}**) {w.get('correct_text', '')}"
        source = w.get("source_text", "")
        back_content = f"{answer_text}"
        if source:
            back_content += f"<br><br><em>Source: {source}</em>"
        st.markdown(f'<div class="flashcard-back">{back_content}</div>', unsafe_allow_html=True)

    # Navigation
    st.markdown("---")
    col1, col2, col3 = st.columns(3)
    with col1:
        if st.button("<-- Prev", use_container_width=True, disabled=idx == 0):
            st.session_state.flashcard_index -= 1
            st.session_state.flashcard_flipped = False
            st.rerun()
    with col2:
        st.markdown(f"<div style='text-align:center; padding-top:0.5rem;'>{idx+1} / {len(wrong)}</div>", unsafe_allow_html=True)
    with col3:
        if st.button("Next -->", use_container_width=True, disabled=idx >= len(wrong) - 1):
            st.session_state.flashcard_index += 1
            st.session_state.flashcard_flipped = False
            st.rerun()

    # Show all (collapsed)
    with st.expander("Show all flashcards"):
        for i, w in enumerate(wrong, 1):
            st.markdown(f"**{i}. {w['question']}**")
            st.markdown(f"Answer: {w['correct_answer']}) {w.get('correct_text', '')}")
            if w.get("source_text"):
                st.caption(w["source_text"][:150])
            st.markdown("---")


# ============================================================
#  PHASE: Study Material Search
# ============================================================
def render_study():
    st.markdown("### Study Material Search")
    st.caption("Search the Discover Canada guide using RAG retrieval")

    init_vector_store()

    query = st.text_input("Search topic or question:", placeholder="e.g., What are the rights of Canadian citizens?")
    num_results = st.slider("Number of results:", 1, 10, 5)

    if query and st.button("Search", use_container_width=True):
        with st.spinner("Searching..."):
            results = search(query, n_results=num_results)

        st.markdown(f"#### Found {len(results)} result(s)")
        for i, r in enumerate(results, 1):
            with st.expander(f"Result {i} - {r.get('metadata', {}).get('chapter', 'Unknown')}"):
                st.markdown(r["content"])
                meta = r.get("metadata", {})
                if meta.get("page"):
                    st.caption(f"Page: {meta['page']}")
                if meta.get("chapter"):
                    st.caption(f"Chapter: {meta['chapter']}")

    # Quick topic buttons
    st.markdown("#### Quick Topics")
    topics = ["Canadian History", "Rights and Responsibilities", "How Canadians Govern Themselves",
              "Regions of Canada", "Canadian Symbols", "Applying for Citizenship", "Canada's Economy"]

    cols = st.columns(3)
    for i, topic in enumerate(topics):
        with cols[i % 3]:
            if st.button(topic, key=f"topic_{i}", use_container_width=True):
                st.session_state["_search_query"] = topic
                st.rerun()

    if "_search_query" in st.session_state:
        q = st.session_state.pop("_search_query")
        results = search(q, n_results=5)
        st.markdown(f"#### {q}")
        for r in results:
            st.markdown(f"- {r['content'][:200]}...")


# ============================================================
#  PHASE: Score History
# ============================================================
def render_history():
    st.markdown("### Score History")

    history = get_score_history()
    if not history:
        st.info("No quiz attempts recorded yet.")
        return

    import pandas as pd
    df = pd.DataFrame(history)
    df["status"] = df["passed"].apply(lambda p: "PASS" if p else "FAIL")
    df["pct_display"] = df["percentage"].apply(lambda p: f"{p*100:.0f}%")

    display_df = df[["attempt", "date", "score", "total", "pct_display", "status"]].copy()
    display_df.columns = ["Attempt", "Date", "Score", "Total", "Percentage", "Status"]
    st.dataframe(display_df, use_container_width=True, hide_index=True)

    col1, col2, col3, col4 = st.columns(4)
    raw_pcts = [h["percentage"] for h in history]
    passes = sum(1 for h in history if h.get("passed"))
    col1.metric("Attempts", len(history))
    col2.metric("Passed", f"{passes}/{len(history)}")
    col3.metric("Best", f"{max(raw_pcts)*100:.0f}%")
    col4.metric("Average", f"{sum(raw_pcts)/len(raw_pcts)*100:.0f}%")

    if len(history) >= 2:
        st.markdown("#### Score Trend")
        chart_df = pd.DataFrame({"Attempt": [h["attempt"] for h in history], "Score %": [h["percentage"]*100 for h in history]})
        st.line_chart(chart_df.set_index("Attempt"), use_container_width=True)


# ============================================================
#  Main Router
# ============================================================
def main():
    render_header()
    render_sidebar()

    phase = st.session_state.phase

    if phase == "onboarding":
        render_onboarding()
    elif phase == "quiz":
        render_quiz()
    elif phase == "results":
        render_results()
    elif phase == "review":
        render_review()
    elif phase == "analytics":
        render_analytics()
    elif phase == "readiness":
        render_readiness()
    elif phase == "wrong_answers":
        render_wrong_answers()
    elif phase == "flashcards":
        render_flashcards()
    elif phase == "study":
        render_study()
    elif phase == "history":
        render_history()


if __name__ == "__main__":
    main()
