import os
import json
import logging
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field
from gemini_engine import GeminiRotationEngine

logger = logging.getLogger("news_curator")
logging.basicConfig(level=logging.INFO)

class OptionItem(BaseModel):
    key: str = Field(description="Option key: '1', '2', '3', '4', '5'")
    val: str = Field(description="Bilingual option value: 'हिंदी / English'")

class ExamQuestion(BaseModel):
    num: int = Field(description="Question number (1 to 10)")
    question_hi: str = Field(description="Hindi question statement, crisp and bold")
    question_en: str = Field(description="English translation of the question statement")
    options: List[OptionItem] = Field(description="List of exactly 5 options. Option 5 MUST be 'अनुत्तरित प्रश्न / Prefer not to answer'")
    correct_ans: str = Field(description="Correct option number key: '1', '2', '3', or '4'")
    exam_fact_hi: str = Field(description="Exam fact / Lallantop Static GK connection in Hindi (1-2 sentences)")
    exam_fact_en: str = Field(description="Exam fact in English (1-2 sentences)")
    visual_query: str = Field(description="2 to 4 precise English keywords for searching the exact real-world photo for this question")
    exam_tags: str = Field(default="[RRB | SSC | BPSC]", description="Target competitive exams e.g. [RRB Special], [SSC CGL], [BPSC Special]")

class DailyCuratedNews(BaseModel):
    questions: List[ExamQuestion] = Field(description="List of exam questions")

class NewsCurator:
    def __init__(self, engine: Optional[GeminiRotationEngine] = None):
        self.engine = engine or GeminiRotationEngine()

    def curate_daily_questions(self, date_str: str, count: int = 20, categories: Optional[List[str]] = None) -> List[Dict[str, Any]]:
        logger.info(f"📰 Curating {count} comprehensive questions for date: {date_str}...")

        if count <= 10:
            return self._curate_single_batch(
                date_str=date_str,
                batch_count=count,
                start_num=1,
                theme_title="Daily Comprehensive Current Affairs",
                grounding_query=(
                    f"Search for the top news events and current affairs of {date_str} in India and globally. "
                    "Focus on National, Bihar/State affairs, AI/Tech, International, and Sports/Economy."
                ),
                curation_theme="Balance topics across National/PIB, Bihar Special, Frontier AI/Tech, and World Geopolitics."
            )

        # For 20 to 30 questions: curate across multi-domain thematic batches
        batch_configs = [
            {
                "title": "National & Bihar Governance",
                "grounding_query": (
                    f"Search for top national news events, PIB press releases, Union Cabinet decisions, "
                    f"Supreme Court & High Court judgments, central government schemes, and Bihar state government announcements of {date_str}. "
                    "List 12 verified factual news developments with specifics."
                ),
                "curation_theme": (
                    "Focus heavily on: National Governance, PIB releases, Central Schemes, Cabinet decisions, "
                    "Constitutional & Judiciary developments, and Bihar State Affairs (BPSC/BSSC special)."
                )
            },
            {
                "title": "International, Defense & Frontier Technology",
                "grounding_query": (
                    f"Search for top global affairs, international summits, bilateral agreements, defense exercises, "
                    f"space missions (ISRO, NASA), and frontier AI & semiconductor developments of {date_str}. "
                    "List 12 verified factual news developments with specifics."
                ),
                "curation_theme": (
                    "Focus heavily on: International Geopolitics, Global Summits, Bilateral Treaties, "
                    "Defense & Military exercises, Space Exploration (ISRO/NASA), and Artificial Intelligence & Semiconductor computing chips."
                )
            },
            {
                "title": "Sports, Economy, Awards & Appointments",
                "grounding_query": (
                    f"Search for top sports tournaments, cricket/badminton/olympic wins, economic data, RBI announcements, "
                    f"prestigious national & international awards, and prominent appointments of {date_str}. "
                    "List 12 verified factual news developments with specifics."
                ),
                "curation_theme": (
                    "Focus heavily on: Sports Championships & Records, Economy & Banking (RBI/SEBI/Indices), "
                    "Prestigious Awards & Honors (Nobel, Padma, Sports awards), Prominent Appointments, and Books & Authors."
                )
            }
        ]

        # Determine number of questions per batch
        num_batches = 3 if count > 20 else 2
        per_batch = count // num_batches
        remainder = count % num_batches

        all_questions = []
        current_num = 1

        for b_idx in range(num_batches):
            b_count = per_batch + (1 if b_idx < remainder else 0)
            cfg = batch_configs[b_idx % len(batch_configs)]
            logger.info(f"🔄 Processing Batch {b_idx + 1}/{num_batches}: {cfg['title']} ({b_count} questions)...")

            try:
                batch_qs = self._curate_single_batch(
                    date_str=date_str,
                    batch_count=b_count,
                    start_num=current_num,
                    theme_title=cfg["title"],
                    grounding_query=cfg["grounding_query"],
                    curation_theme=cfg["curation_theme"]
                )
                all_questions.extend(batch_qs)
                current_num += len(batch_qs)
            except Exception as e:
                logger.error(f"Error in batch {b_idx + 1}: {e}")

        # Ensure strict sequential numbering 1 to count
        for idx, q in enumerate(all_questions):
            q["num"] = idx + 1

        logger.info(f"✅ Total curated questions ready: {len(all_questions)}")
        return all_questions[:count]

    def _curate_single_batch(self, date_str: str, batch_count: int, start_num: int, theme_title: str, grounding_query: str, curation_theme: str) -> List[Dict[str, Any]]:
        logger.info(f"🔍 Grounding research for '{theme_title}'...")
        try:
            grounded_context = self.engine.generate_grounded_content(grounding_query)
        except Exception as e:
            logger.warning(f"Grounding query failed for {theme_title}: {e}. Using fallback context.")
            grounded_context = f"Events and milestones around {date_str} for {theme_title}."

        curation_prompt = (
            f"You are the Lead Current Affairs Subject Matter Expert inspired by Kumar Gaurav Sir's 'Phool-Patti Wali Class' (Utkarsh Classes).\n"
            f"Target Competitive Exams: RRB NTPC, RRB Group D, SSC CGL/CHSL, Bihar BPSC, Bihar BSSC, and State PSCs.\n"
            f"Edition Date: {date_str}\n"
            f"Category Theme: {theme_title}\n\n"
            f"Factual Research Context:\n{grounded_context}\n\n"
            f"TASK: Generate exactly {batch_count} top-tier, exam-worthy MCQs covering the verified events.\n"
            "CRITICAL RULES:\n"
            f"1. Exactly {batch_count} questions.\n"
            f"2. {curation_theme}\n"
            "3. Question stem MUST be bilingual: High-impact Hindi in 'question_hi', natural English in 'question_en'.\n"
            "4. Exactly 5 options per question:\n"
            "   - Options 1, 2, 3, 4: Bilingual choices ('हिंदी / English')\n"
            "   - Option 5: MUST be strictly 'अनुत्तरित प्रश्न / Prefer not to answer' (BPSC/RRB modern format)\n"
            "5. 'correct_ans' MUST be '1', '2', '3', or '4'. Randomize the answer keys evenly.\n"
            "6. 'exam_fact_hi' & 'exam_fact_en': Provide rich, high-yield 'Lallantop Baatein' / Static GK connections (e.g. related constitutional article, ministry, headquarters, previous year exam facts).\n"
            "7. 'visual_query': 2 to 4 precise English search keywords to fetch a widely recognized, high-visibility REAL-WORLD OBJECT, LANDMARK, PERSON, or EMBLEM. "
            "NEVER output abstract policy names (like 'Policy 2026 draft' or 'Campaign 6.0'). "
            "Always output concrete visual subjects (e.g. 'Nitish Kumar Bihar Patna', 'Supreme Court of India New Delhi', 'ISRO rocket launch', 'OpenAI logo San Francisco', 'Donald Trump portrait')."
        )

        try:
            raw_json = self.engine.generate_text(
                prompt=curation_prompt,
                system_instruction="You are a premier Indian competitive exams question paper setter. Output valid JSON adhering to the DailyCuratedNews schema.",
                response_schema=DailyCuratedNews,
                temperature=0.2
            )
            data = json.loads(raw_json)
            questions_list = data.get("questions", [])
            formatted = []
            for idx, q in enumerate(questions_list[:batch_count]):
                q_dict = q if isinstance(q, dict) else q.model_dump()
                q_dict["num"] = start_num + idx
                # Clean up any LLM markdown formatting asterisks
                q_dict["question_hi"] = q_dict.get("question_hi", "").replace("**", "").strip()
                q_dict["question_en"] = q_dict.get("question_en", "").replace("**", "").strip()
                q_dict["exam_fact_hi"] = q_dict.get("exam_fact_hi", "").replace("**", "").strip()
                q_dict["exam_fact_en"] = q_dict.get("exam_fact_en", "").replace("**", "").strip()

                # Ensure 5th option format
                opts = q_dict.get("options", [])
                for opt in opts:
                    if isinstance(opt, dict):
                        opt["val"] = opt.get("val", "").replace("**", "").strip()
                if len(opts) < 5:
                    opts.append({"key": "5", "val": "अनुत्तरित प्रश्न / Prefer not to answer"})
                else:
                    opts[4] = {"key": "5", "val": "अनुत्तरित प्रश्न / Prefer not to answer"}
                q_dict["options"] = opts
                formatted.append(q_dict)

            if formatted:
                return formatted
        except Exception as e:
            logger.error(f"Error generating structured questions for batch {theme_title}: {e}")

        # Deterministic fallback if API fails
        return self._generate_fallback_questions(date_str, batch_count, start_num)

    def _generate_fallback_questions(self, date_str: str, count: int, start_num: int = 1) -> List[Dict[str, Any]]:
        fallback = [
            {
                "num": start_num,
                "question_hi": "भारत सरकार ने 2026 तक किस क्षेत्र में आत्मनिर्भरता के लिए नई राष्ट्रीय नीति अधिसूचित की?",
                "question_en": "In which sector has the Indian Government notified a new national policy for self-reliance by 2026?",
                "options": [
                    {"key": "1", "val": "सेमीकंडक्टर चिप्स / Semiconductor Chips"},
                    {"key": "2", "val": "सौर ऊर्जा पैनल / Solar Energy Panels"},
                    {"key": "3", "val": "इलेक्ट्रिक वाहन बैटरी / Electric Vehicle Batteries"},
                    {"key": "4", "val": "ग्रीन हाइड्रोजन / Green Hydrogen"},
                    {"key": "5", "val": "अनुत्तरित प्रश्न / Prefer not to answer"}
                ],
                "correct_ans": "1",
                "exam_fact_hi": "भारत सेमीकंडक्टर मिशन (ISM) की शुरुआत इलेक्ट्रॉनिक्स एवं आईटी मंत्रालय (MeitY) द्वारा की गई है।",
                "exam_fact_en": "India Semiconductor Mission (ISM) was launched under Ministry of Electronics and IT (MeitY).",
                "visual_query": "TSMC semiconductor microchip wafer",
                "exam_tags": "[RRB NTPC | SSC CGL]"
            },
            {
                "num": start_num + 1,
                "question_hi": "बिहार राज्य सरकार ने युवाओं में उद्यमिता बढ़ाने हेतु हाल ही में कौन सी योजना शुरू की?",
                "question_en": "Which scheme was recently launched by the Bihar State Government to boost youth entrepreneurship?",
                "options": [
                    {"key": "1", "val": "मुख्यमंत्री उद्यमी योजना / CM Udyami Yojana"},
                    {"key": "2", "val": "बिहार स्टार्ट-अप नीति / Bihar Startup Policy"},
                    {"key": "3", "val": "कौशल विकास मिशन / Skill Development Mission"},
                    {"key": "4", "val": "युवा शक्ति पहल / Yuva Shakti Initiative"},
                    {"key": "5", "val": "अनुत्तरित प्रश्न / Prefer not to answer"}
                ],
                "correct_ans": "1",
                "exam_fact_hi": "मुख्यमंत्री उद्यमी योजना के तहत बिहार सरकार 10 लाख रुपये तक की प्रोत्साहन सहायता प्रदान करती है।",
                "exam_fact_en": "Under CM Udyami Yojana, Bihar Govt provides financial incentive up to Rs 10 Lakhs.",
                "visual_query": "Patna Bihar secretariat building",
                "exam_tags": "[BPSC Special | BSSC]"
            }
        ]
        # Duplicate/extend if more needed
        results = []
        for i in range(count):
            base_q = dict(fallback[i % len(fallback)])
            base_q["num"] = start_num + i
            results.append(base_q)
        return results
