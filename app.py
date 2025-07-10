# FILE: app.py

import os
from dotenv import load_dotenv
from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.responses import StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
import torch
from pyannote.audio import Pipeline
from faster_whisper import WhisperModel
from groq import Groq
from transformers import pipeline
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib import colors
from reportlab.lib.units import inch
from io import BytesIO
from typing import List, Dict
import tempfile
import logging
import re

# --- Setup & Configuration ---
logging.basicConfig(level=logging.INFO)
load_dotenv()

HUGGINGFACE_TOKEN = os.getenv("HUGGINGFACE_TOKEN")
GROQ_API_KEY = os.getenv("GROQ_API_KEY")

if not HUGGINGFACE_TOKEN or not GROQ_API_KEY:
    raise ValueError("API keys for Hugging Face and Groq must be set in .env file.")

# --- NEW: Filler Words Configuration ---
# A combined list of common English and Turkish filler words.
FILLER_WORDS = {
    'uh', 'um', 'ah', 'ııı', 'like', 'you know', 'so', 'actually', 'basically', 'right',
    'şey', 'yani', 'hani', 'işte', 'böyle', 'acaba', 'aslında'
}

# --- Initialize AI Models ---
DEVICE = "cuda" if torch.cuda.is_available() else "cpu"
COMPUTE_TYPE = "float16" if torch.cuda.is_available() else "int8"
logging.info(f"Using device: {DEVICE}")

logging.info("Loading Diarization pipeline...")
diarization_pipeline = Pipeline.from_pretrained("pyannote/speaker-diarization-3.1", use_auth_token=HUGGINGFACE_TOKEN).to(torch.device(DEVICE))
logging.info("Diarization pipeline loaded.")

logging.info("Loading Transcription model 'base'...")
transcription_model = WhisperModel("base", device=DEVICE, compute_type=COMPUTE_TYPE)
logging.info("Transcription model loaded.")

groq_client = Groq(api_key=GROQ_API_KEY)

logging.info("Loading Sentiment Analysis pipeline...")
sentiment_pipeline = pipeline("sentiment-analysis", model="cardiffnlp/twitter-xlm-roberta-base-sentiment", device=0 if DEVICE == "cuda" else -1)
logging.info("Sentiment Analysis pipeline loaded.")

# --- FastAPI App Initialization ---
app = FastAPI()
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_credentials=True, allow_methods=["*"], allow_headers=["*"])

# --- Helper Functions ---

def _calculate_gini_coefficient(talk_times: Dict[str, float]) -> float:
    if not talk_times or len(talk_times) < 2: return 0.0
    total_talk_time = sum(talk_times.values())
    if total_talk_time == 0: return 0.0
    sum_of_squared_proportions = sum(((time / total_talk_time) ** 2) for time in talk_times.values())
    return 1 - sum_of_squared_proportions

def _calculate_turn_taking_stats(diarization_result) -> Dict[str, int]:
    turn_counts = {}
    for _, _, speaker in diarization_result.itertracks(yield_label=True):
        turn_counts[speaker] = turn_counts.get(speaker, 0) + 1
    return turn_counts

def _align_transcription_with_diarization(transcription_segments, diarization):
    full_transcript, speaker_talk_time = [], {}
    speaker_turn_counts = _calculate_turn_taking_stats(diarization)
    for turn, _, speaker in diarization.itertracks(yield_label=True):
        duration = turn.end - turn.start
        speaker_talk_time[speaker] = speaker_talk_time.get(speaker, 0) + duration
    for segment in transcription_segments:
        speakers = diarization.crop(segment.word_timestamps[0]['start'] if segment.word_timestamps else segment.start)
        speaker = "UNKNOWN"
        if speakers:
            speaker = speakers.itertracks(yield_label=True).__next__()[2]
        full_transcript.append({"speaker": speaker, "text": segment.text.strip()})
    return full_transcript, speaker_talk_time, speaker_turn_counts

def _analyze_sentiment(aligned_transcript: list, speaker_map: dict) -> Dict[str, str]:
    sentiment_counts = {name: {"positive": 0, "neutral": 0, "negative": 0} for name in speaker_map.values()}
    for segment in aligned_transcript:
        speaker_id, text = segment['speaker'], segment['text']
        if speaker_id in speaker_map and text:
            speaker_name = speaker_map[speaker_id]
            try:
                result = sentiment_pipeline(text)
                sentiment_counts[speaker_name][result[0]['label']] += 1
            except Exception as e:
                logging.warning(f"Sentiment analysis failed for text: '{text}'. Error: {e}")
    dominant_sentiments = {}
    for name, counts in sentiment_counts.items():
        if not any(counts.values()):
            dominant_sentiments[name] = "N/A"
            continue
        dominant_sentiment = max(counts, key=counts.get)
        translation = {"positive": "Pozitif", "neutral": "Nötr", "negative": "Negatif"}
        dominant_sentiments[name] = translation.get(dominant_sentiment, "Bilinmiyor")
    return dominant_sentiments

# --- NEW: Helper Function to Calculate Filler Word Ratios ---
def _calculate_filler_word_ratios(aligned_transcript: list, speaker_map: dict) -> Dict[str, float]:
    """Calculates the filler word ratio for each speaker."""
    speaker_texts = {name: "" for name in speaker_map.values()}
    for segment in aligned_transcript:
        speaker_id = segment['speaker']
        if speaker_id in speaker_map:
            speaker_texts[speaker_map[speaker_id]] += " " + segment['text']

    filler_ratios = {}
    for name, text in speaker_texts.items():
        words = re.findall(r'\b\w+\b', text.lower())
        if not words:
            filler_ratios[name] = 0.0
            continue
        
        filler_count = sum(1 for word in words if word in FILLER_WORDS)
        total_words = len(words)
        ratio = (filler_count / total_words) * 100 if total_words > 0 else 0.0
        filler_ratios[name] = ratio
        
    return filler_ratios

# --- UPDATED: Helper Function to Generate PDF Report ---
def _create_pdf_report(
    summary: str, talk_time_stats: dict, turn_counts: dict, gini_score: float,
    dominant_sentiments: dict, filler_word_ratios: dict, total_duration: float
):
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize="A4", rightMargin=inch, leftMargin=inch, topMargin=inch, bottomMargin=inch)
    styles = getSampleStyleSheet()
    story = []

    story.append(Paragraph("Toplantı Analiz Raporu - Slugg", styles['h1']))
    story.append(Spacer(1, 0.2 * inch))
    story.append(Paragraph(f"<b>Toplam Toplantı Süresi:</b> {int(total_duration // 60):02d}:{int(total_duration % 60):02d} dakika", styles['Normal']))
    story.append(Spacer(1, 0.4 * inch))

    story.append(Paragraph("Yapay Zeka Özeti", styles['h2']))
    summary_parts = summary.replace("[ACTION_ITEM]", "\n<b>[AKSİYON]</b>").replace("[DECISION]", "\n<b>[KARAR]</b>").split('\n')
    for part in summary_parts:
        if part.strip():
            story.append(Paragraph(part.strip().replace("Aksiyon Maddeleri:", "<b>Aksiyon Maddeleri:</b>"), styles['BodyText']))
    story.append(Spacer(1, 0.4 * inch))

    story.append(Paragraph("Anahtar Performans Göstergeleri (KPIs)", styles['h2']))
    gini_interpretation = "Dengeli" if gini_score < 0.4 else ("Orta Dengesiz" if gini_score < 0.6 else "Aşırı Dengesiz")
    kpi_data = [['Metrik', 'Değer', 'Değerlendirme'], ['Katılım Dengesi (Gini)', f"{gini_score:.2f}", gini_interpretation], ['Etkileşim (Toplam Konuşma Sayısı)', f"{sum(turn_counts.values())} tur", ""]]
    kpi_table = Table(kpi_data, colWidths=[2.5 * inch, 1.5 * inch, 2 * inch])
    kpi_table.setStyle(TableStyle([('BACKGROUND', (0, 0), (-1, 0), colors.darkslategray), ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke), ('ALIGN', (0, 0), (-1, -1), 'CENTER'), ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'), ('BOTTOMPADDING', (0, 0), (-1, 0), 12), ('BACKGROUND', (0, 1), (-1, -1), colors.lightgrey), ('GRID', (0, 0), (-1, -1), 1, colors.black)]))
    story.append(kpi_table)
    story.append(Spacer(1, 0.4 * inch))

    story.append(Paragraph("Katılımcı Bazında Detaylı Analiz", styles['h2']))
    table_data = [['Katılımcı', 'Konuşma Yüzdesi', 'Konuşma Sayısı', 'Genel Duygu', 'Dolgu Kelime (%)']]
    sorted_speakers = sorted(talk_time_stats.items(), key=lambda item: item[1], reverse=True)
    total_talk_time = sum(talk_time_stats.values())
    for speaker_name, time in sorted_speakers:
        percentage = (time / total_talk_time) * 100 if total_talk_time > 0 else 0
        turn_count = turn_counts.get(speaker_name, 0)
        sentiment = dominant_sentiments.get(speaker_name, "N/A")
        filler_ratio = filler_word_ratios.get(speaker_name, 0.0)
        table_data.append([speaker_name, f"{percentage:.1f}%", str(turn_count), sentiment, f"{filler_ratio:.1f}%"])

    t = Table(table_data, colWidths=[1.7*inch, 1.3*inch, 1.2*inch, 1.2*inch, 1.4*inch])
    t.setStyle(TableStyle([('BACKGROUND', (0, 0), (-1, 0), colors.grey), ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke), ('ALIGN', (0, 0), (-1, -1), 'CENTER'), ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'), ('BOTTOMPADDING', (0, 0), (-1, 0), 12), ('BACKGROUND', (0, 1), (-1, -1), colors.beige), ('GRID', (0, 0), (-1, -1), 1, colors.black)]))
    story.append(t)

    doc.build(story)
    buffer.seek(0)
    return buffer

# --- Main API Endpoint (UPDATED) ---
@app.post("/analyze/")
async def analyze_meeting_audio(participants: List[str] = Form(...), audio_file: UploadFile = File(...)):
    logging.info(f"Received request with {len(participants)} participants.")
    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as tmp_audio_file:
            content = await audio_file.read()
            tmp_audio_file.write(content)
            tmp_audio_path = tmp_audio_file.name

        diarization_result = diarization_pipeline(tmp_audio_path)
        total_duration = max(turn.end for turn, _, _ in diarization_result.itertracks(yield_label=True))
        
        segments, _ = transcription_model.transcribe(tmp_audio_path, beam_size=5, word_timestamps=True)
        transcription_segments = list(segments)

        aligned_transcript, speaker_talk_time, speaker_turn_counts = _align_transcription_with_diarization(transcription_segments, diarization_result)
        
        sorted_speakers_by_time = sorted(speaker_talk_time.keys(), key=lambda s: speaker_talk_time[s], reverse=True)
        sorted_participants = sorted(participants)
        speaker_map = {sp_id: sorted_participants[i] if i < len(sorted_participants) else sp_id for i, sp_id in enumerate(sorted_speakers_by_time)}
        
        named_talk_time_stats = {speaker_map.get(s, s): t for s, t in speaker_talk_time.items()}
        named_turn_counts = {speaker_map.get(s, s): c for s, c in speaker_turn_counts.items()}
        gini_score = _calculate_gini_coefficient(named_talk_time_stats)

        logging.info("Performing sentiment analysis...")
        dominant_sentiments = _analyze_sentiment(aligned_transcript, speaker_map)

        # NEW: Perform Filler Word Analysis
        logging.info("Performing filler word analysis...")
        filler_ratios = _calculate_filler_word_ratios(aligned_transcript, speaker_map)
        logging.info(f"Filler word analysis complete. Results: {filler_ratios}")
        
        llm_input_transcript = "\n".join([f"{speaker_map.get(item['speaker'], item['speaker'])}: {item['text']}" for item in aligned_transcript])
        
        chat_completion = groq_client.chat.completions.create(messages=[{"role": "system", "content": "You are a meeting analysis assistant..."}, {"role": "user", "content": f"Lütfen...:\n\n{llm_input_transcript}"}], model="llama3-70b-8192")
        summary = chat_completion.choices[0].message.content
        
        logging.info("Generating PDF report...")
        pdf_buffer = _create_pdf_report(summary, named_talk_time_stats, named_turn_counts, gini_score, dominant_sentiments, filler_ratios, total_duration)
        logging.info("PDF report generated successfully.")

        os.remove(tmp_audio_path)
        return StreamingResponse(pdf_buffer, media_type="application/pdf", headers={"Content-Disposition": "attachment; filename=meeting_report.pdf"})
    except Exception as e:
        logging.error(f"An error occurred: {e}", exc_info=True)
        if 'tmp_audio_path' in locals() and os.path.exists(tmp_audio_path):
            os.remove(tmp_audio_path)
        raise HTTPException(status_code=500, detail=str(e))