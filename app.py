import os
import sys
from datetime import datetime
import streamlit as st
from dotenv import load_dotenv

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, BASE_DIR)
dotenv_path = os.path.join(BASE_DIR, ".env")
if os.path.exists(dotenv_path):
    load_dotenv(dotenv_path)
else:
    load_dotenv()

# Automatically bridge Streamlit Cloud Secrets into os.environ for submodules
try:
    if hasattr(st, "secrets"):
        for k, v in st.secrets.items():
            if isinstance(v, str):
                os.environ[k] = v
except Exception:
    pass

from gemini_engine import GeminiRotationEngine
from news_curator import NewsCurator
from image_manager import ImageManager
from pdf_generator import PDFGenerator
from telegram_broadcaster import TelegramBroadcaster

st.set_page_config(
    page_title="AryaCA — Daily Current Affairs Engine",
    page_icon="📰",
    layout="wide"
)

st.title("📰 AryaCA — Daily Exam Current Affairs Generator")
st.markdown("Automated Bilingual MCQs, Lallantop Static GK, Gemini Vision-Verified Photos & A4 Magazine PDF Generator.")

# Sidebar Configuration
st.sidebar.header("⚙️ Configuration")
selected_date = st.sidebar.date_input("Edition Date", datetime.now())
date_str = selected_date.strftime("%Y-%m-%d")

q_count = st.sidebar.slider("Number of MCQs (Pages)", min_value=10, max_value=30, value=20, step=5)

st.sidebar.subheader("🎯 Focus Categories")
cat_national = st.sidebar.checkbox("National & PIB Releases", value=True)
cat_bihar = st.sidebar.checkbox("Bihar & State Special (BPSC/BSSC)", value=True)
cat_tech = st.sidebar.checkbox("Frontier Tech: AI & Computing Chips", value=True)
cat_world = st.sidebar.checkbox("World Leaders & Geopolitics", value=True)

raw_channels = os.getenv("TG_CHANNEL_CHAT_IDS", "")
channels_list = [c.strip() for c in raw_channels.split(",") if c.strip()]
st.sidebar.markdown(f"**Connected Telegram Channels:** `{len(channels_list)}`")
for ch in channels_list:
    st.sidebar.caption(f"• `{ch}`")

# Session state initialization
if "questions" not in st.session_state:
    st.session_state.questions = None
if "pdf_path" not in st.session_state:
    st.session_state.pdf_path = None
if "png_path" not in st.session_state:
    st.session_state.png_path = None

col1, col2 = st.columns([1, 1])

with col1:
    if st.button("⚡ Generate Daily Current Affairs Edition", type="primary", use_container_width=True):
        with st.spinner("1️⃣ Curating top exam-oriented news across categories..."):
            engine = GeminiRotationEngine()
            curator = NewsCurator(engine=engine)
            questions = curator.curate_daily_questions(date_str=date_str, count=q_count)

        with st.spinner(f"2️⃣ Concurrently fetching and Vision-verifying HD topic images ({len(questions)} items)..."):
            img_mgr = ImageManager(engine=engine)
            img_mgr.fetch_images_for_questions(questions=questions, max_workers=3)

        with st.spinner("3️⃣ Compiling Multi-Page Dual-Column A4 Magazine PDF with WeasyPrint..."):
            pdf_gen = PDFGenerator()
            pdf_path, png_path = pdf_gen.generate_edition(date_str=date_str, questions=questions)

        st.session_state.questions = questions
        st.session_state.pdf_path = pdf_path
        st.session_state.png_path = png_path
        st.success(f"🎉 Edition generated successfully for {date_str} ({len(questions)} MCQs)!")

with col2:
    if st.session_state.pdf_path and os.path.exists(st.session_state.pdf_path):
        with open(st.session_state.pdf_path, "rb") as f:
            st.download_button(
                label="📥 Download A4 Magazine PDF",
                data=f.read(),
                file_name=os.path.basename(st.session_state.pdf_path),
                mime="application/pdf",
                use_container_width=True
            )

        if st.button("📢 Broadcast to All Telegram Channels", use_container_width=True):
            with st.spinner("Broadcasting to connected Telegram channels..."):
                broadcaster = TelegramBroadcaster()
                report = broadcaster.broadcast_edition(
                    pdf_path=st.session_state.pdf_path,
                    preview_png_path=st.session_state.png_path,
                    date_str=date_str,
                    question_count=len(st.session_state.questions) if st.session_state.questions else 20
                )
                for ch, success in report.items():
                    if success:
                        st.success(f"✅ Delivered to `{ch}`")
                    else:
                        st.error(f"❌ Delivery failed for `{ch}`")

# Display Preview
if st.session_state.png_path and os.path.exists(st.session_state.png_path):
    st.divider()
    st.subheader(f"🖼️ Page 1 Preview ({date_str})")
    st.image(st.session_state.png_path, use_column_width=True)

if st.session_state.questions:
    st.divider()
    st.subheader("📝 Curated MCQs & Lallantop Static GK")
    for q in st.session_state.questions:
        with st.expander(f"Q{q['num']}: {q['question_hi']} | {q['question_en']}"):
            cols = st.columns([3, 1])
            with cols[0]:
                for opt in q["options"]:
                    st.write(f"**{opt['key']}.** {opt['val']}")
                st.info(f"**Correct Answer:** Option {q['correct_ans']}")
                st.markdown(f"**Exam Fact (Lallantop):**\n• {q['exam_fact_hi']}\n• {q['exam_fact_en']}")
            with cols[1]:
                if q.get("image_data_uri"):
                    st.image(q["image_data_uri"], caption=q.get("visual_query", "Topic Image"))
