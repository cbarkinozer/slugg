import os
import asyncio
from dotenv import load_dotenv
from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.responses import StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
import torch
from pyannote.audio import Pipeline
from faster_whisper import WhisperModel
from groq import Groq
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib import colors
from reportlab.lib.units import inch
from io import BytesIO
from typing import List
import tempfile
import logging

# --- Setup & Configuration ---
logging.basicConfig(level=logging.INFO)
load_dotenv()

HUGGINGFACE_TOKEN = os.getenv("HUGGINGFACE_TOKEN")
GROQ_API_KEY = os.getenv("GROQ_API_KEY")

if not HUGGINGFACE_TOKEN or not GROQ_API_KEY:
    raise ValueError("API keys for Hugging Face and Groq must be set in .env file.")

# --- Initialize AI Models ---
# Note: These models are loaded into memory when the server starts.
# This can be resource-intensive.
DEVICE = "cuda" if torch.cuda.is_available() else "cpu"

COMPUTE_TYPE = "float16" if torch.cuda.is_available() else "int8"

logging.info(f"Using device: {DEVICE}")

# 1. Diarization Model
logging.info("Loading Diarization pipeline...")
diarization_pipeline = Pipeline.from_pretrained(
    "pyannote/speaker-diarization-3.1",
    use_auth_token=HUGGINGFACE_TOKEN
).to(torch.device(DEVICE))
logging.info("Diarization pipeline loaded.")

# 2. Transcription Model
# For CPU, 'base' or 'small' is recommended.
# For GPU, you can use 'medium' or 'large-v3'.
model_size = "base"
logging.info(f"Loading Transcription model '{model_size}'...")
transcription_model = WhisperModel(model_size, device=DEVICE, compute_type=COMPUTE_TYPE)
logging.info("Transcription model loaded.")

# 3. Groq Client
groq_client = Groq(api_key=GROQ_API_KEY)


# --- FastAPI App Initialization ---
app = FastAPI()

# Configure CORS to allow requests from your ngrok frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Be more specific in production!
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# --- Helper Function: Align Transcription and Diarization ---
def _align_transcription_with_diarization(transcription_segments, diarization):
    full_transcript = []
    speaker_talk_time = {}

    # Calculate total talk time for each speaker from diarization
    for turn, _, speaker in diarization.itertracks(yield_label=True):
        duration = turn.end - turn.start
        if speaker not in speaker_talk_time:
            speaker_talk_time[speaker] = 0
        speaker_talk_time[speaker] += duration

    # Align whisper segments with speaker turns
    for segment in transcription_segments:
        # Find speaker for this segment's timestamp
        # Pyannote's `crop` method helps find who spoke in a given time range
        speakers = diarization.crop(segment.word_timestamps[0]['start'] if segment.word_timestamps else segment.start)
        
        # Get the most likely speaker (often there's only one)
        speaker = "UNKNOWN"
        if speakers:
            speaker = speakers.itertracks(yield_label=True).__next__()[2]

        full_transcript.append({
            "speaker": speaker,
            "text": segment.text.strip()
        })
        
    return full_transcript, speaker_talk_time


# --- Helper Function: Generate PDF Report ---
def _create_pdf_report(summary: str, talk_time_stats: dict, total_duration: float):
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize="A4", rightMargin=inch, leftMargin=inch, topMargin=inch, bottomMargin=inch)
    styles = getSampleStyleSheet()
    story = []

    # Title
    story.append(Paragraph("Toplantı Analiz Raporu - Slugg", styles['h1']))
    story.append(Spacer(1, 0.2 * inch))
    story.append(Paragraph(f"<b>Toplam Toplantı Süresi:</b> {int(total_duration // 60):02d}:{int(total_duration % 60):02d} dakika", styles['Normal']))
    story.append(Spacer(1, 0.4 * inch))

    # AI Summary
    story.append(Paragraph("Yapay Zeka Özeti", styles['h2']))
    # Split summary by newlines to preserve formatting
    summary_parts = summary.replace("Aksiyon Maddeleri:", "\n\nAksiyon Maddeleri:").split('\n')
    for part in summary_parts:
        if part.strip():
            story.append(Paragraph(part.strip(), styles['BodyText']))
    story.append(Spacer(1, 0.4 * inch))
    
    # Talk-Time Distribution
    story.append(Paragraph("Konuşma Süresi Dağılımı", styles['h2']))

    total_talk_time = sum(talk_time_stats.values())
    
    # Find dominator
    if talk_time_stats:
        dominator = max(talk_time_stats, key=talk_time_stats.get)
        story.append(Paragraph(f"<b>Toplantı Dominatörü:</b> {dominator}", styles['Normal']))
        story.append(Spacer(1, 0.2 * inch))

        # Create table data
        table_data = [['Katılımcı', 'Konuşma Yüzdesi (%)']]
        sorted_speakers = sorted(talk_time_stats.items(), key=lambda item: item[1], reverse=True)

        for speaker, time in sorted_speakers:
            percentage = (time / total_talk_time) * 100 if total_talk_time > 0 else 0
            table_data.append([speaker, f"{percentage:.2f}%"])

        # Create and style the table
        t = Table(table_data, colWidths=[3 * inch, 2 * inch])
        t.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
            ('GRID', (0, 0), (-1, -1), 1, colors.black)
        ]))
        story.append(t)

    doc.build(story)
    buffer.seek(0)
    return buffer

# --- Main API Endpoint ---
@app.post("/analyze/")
async def analyze_meeting_audio(
    participants: List[str] = Form(...),
    audio_file: UploadFile = File(...)
):
    logging.info(f"Received request with {len(participants)} participants.")
    
    try:
        # Save uploaded audio to a temporary file
        with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as tmp_audio_file:
            content = await audio_file.read()
            tmp_audio_file.write(content)
            tmp_audio_path = tmp_audio_file.name

        logging.info("Audio file saved temporarily. Starting diarization...")

        # 1. Perform Speaker Diarization
        # The audio must be a path on disk for pyannote
        diarization_result = diarization_pipeline(tmp_audio_path)
        
        # Get total duration from the last turn in diarization
        total_duration = max(turn.end for turn, _, _ in diarization_result.itertracks(yield_label=True))
        logging.info(f"Diarization complete. Total duration: {total_duration:.2f}s")

        # 2. Perform Transcription
        logging.info("Starting transcription...")
        segments, _ = transcription_model.transcribe(
            tmp_audio_path,
            beam_size=5,
            word_timestamps=True,  # Important for alignment
        )
        
        # This is a generator, so we consume it into a list
        transcription_segments = list(segments)
        logging.info("Transcription complete.")

        # 3. Align Transcription with Diarization
        logging.info("Aligning transcription and diarization...")
        aligned_transcript, speaker_talk_time = _align_transcription_with_diarization(transcription_segments, diarization_result)
        
        # Create a simple, readable transcript for the LLM
        llm_input_transcript = "\n".join([f"{item['speaker']}: {item['text']}" for item in aligned_transcript])

        # Heuristic to map SPEAKER_XX to actual names
        # Sort speakers by talk time and participants alphabetically
        sorted_speakers = sorted(speaker_talk_time.keys(), key=lambda s: speaker_talk_time[s], reverse=True)
        sorted_participants = sorted(participants)
        
        speaker_map = {}
        # If number of speakers matches participants, we can try to map them.
        # This is a HUGE assumption and a major limitation of the MVP.
        if len(sorted_speakers) <= len(sorted_participants):
            for i, speaker_id in enumerate(sorted_speakers):
                speaker_map[speaker_id] = sorted_participants[i] if i < len(sorted_participants) else speaker_id
        
        # Replace generic speaker labels with names
        for speaker_id, name in speaker_map.items():
            llm_input_transcript = llm_input_transcript.replace(f"{speaker_id}:", f"{name}:")
        
        # Update talk_time_stats with real names
        named_talk_time_stats = {speaker_map.get(s, s): t for s, t in speaker_talk_time.items()}

        logging.info("Alignment complete. Sending to Groq for summarization...")

        # 4. Generate AI Summary with Groq
        chat_completion = groq_client.chat.completions.create(
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You are a meeting analysis assistant for a Turkish software development team. "
                        "Your task is to summarize the provided meeting transcript. "
                        "The summary MUST be in Turkish. "
                        "However, you MUST preserve all English technical terms, code-related nouns, and developer slang exactly as they are in the original text (e.g., `API`, `database`, `pull request`, `frontend`, `backend`, `sprint`, `bug`, `refactor`, `deployment`). "
                        "Focus on key decisions, action items, and disagreements. Be concise and direct. "
                        "At the end of the summary, add a clear section titled 'Aksiyon Maddeleri:' and list the action items with the responsible person's name."
                    ),
                },
                {
                    "role": "user",
                    "content": f"Lütfen aşağıdaki toplantı dökümünü özetle:\n\n{llm_input_transcript}",
                },
            ],
            model="llama3-70b-8192",
        )
        summary = chat_completion.choices[0].message.content
        logging.info("Groq summary generated.")

        # 5. Generate PDF Report
        logging.info("Generating PDF report...")
        pdf_buffer = _create_pdf_report(summary, named_talk_time_stats, total_duration)
        logging.info("PDF report generated successfully.")

        # Clean up temporary file
        os.remove(tmp_audio_path)

        # 6. Stream PDF back to the client
        return StreamingResponse(
            pdf_buffer,
            media_type="application/pdf",
            headers={"Content-Disposition": "attachment; filename=meeting_report.pdf"}
        )

    except Exception as e:
        logging.error(f"An error occurred: {e}")
        # Also clean up the temp file in case of an error
        if 'tmp_audio_path' in locals() and os.path.exists(tmp_audio_path):
            os.remove(tmp_audio_path)
        raise HTTPException(status_code=500, detail=str(e))