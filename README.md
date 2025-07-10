# Slugg: The On-Device Zoom Meeting Analyzer

![alt text](Image_fx.jpg)

**Slugg helps you reclaim your time by analyzing Zoom meetings to identify dominators, measure engagement, and generate concise, actionable summaries. It's designed for tech teams who are tired of meetings that could have been an email.**

Slugg runs locally on your machine, ensuring your meeting data remains private. It processes the entire meeting's audio on-device for transcription and diarization, then uses the high-speed Groq API for summarization, delivering a professional PDF report right after your meeting ends.

## ✨ Key Features

*   **📊 Accurate Post-Meeting Talk-Time Analysis:** Calculates and visualizes who spoke the most, identifying meeting dominators with clear percentages based on advanced diarization.
*   **🗣️ AI-Powered Speaker Diarization:** Intelligently separates speakers from the meeting's single mixed-audio stream ("who spoke when").
*   **📝 AI-Powered Summaries (Turkish/Dev-Speak):** Generates summaries in Turkish, but cleverly preserves English technical terms (`API`, `pull request`, `database`, etc.), just like developers actually speak.
*   **📄 Professional PDF Report:** Delivers a clean, shareable PDF report at the end of each meeting.
*   **🔒 Privacy-Focused by Design:** Transcription and diarization happen **on your device**. Only the anonymized text transcript is sent to an external API for summarization. The raw audio never leaves your machine.
*   **⚡ Blazing Fast Summaries:** Leverages the Groq API for near-instantaneous summary generation.

## ⚙️ How It Works (Architecture)

Slugg uses a two-part architecture to function within Zoom's security constraints while leveraging powerful local Python libraries.

```
+---------------------------+       +---------------------------------------------+
|        ZOOM CLIENT        |       |              USER'S COMPUTER                |
|                           |       |                                             |
| +-----------------------+ |       | +-----------------------------------------+ |
| |      SLUGG APP        | | HTTPS | |         LOCAL BACKEND SERVER          | |
| |(SvelteKit, Tailwind)  | |<----->| |          (Python, FastAPI)            | |
| | - Captures raw audio  | |(ngrok)| | - Receives audio & participant data     | |
| | - Gets participants   | |       | | - ON-DEVICE: Transcribes (Whisper)      | |
| | - Triggers PDF download| |       | | - ON-DEVICE: Diarizes (pyannote)        | |
| +-----------------------+ |       | | - CLOUD: Summarizes (Groq API)          | |
|                           |       | | - Generates PDF (ReportLab)             | |
|                           |       | | - Sends PDF back to Frontend          | |
+---------------------------+       | +-----------------------------------------+ |
                                    +---------------------------------------------+
```

1.  **Frontend (Zoom App):** A modern web application built with SvelteKit, running inside a Zoom window. It uses the Zoom Apps SDK to capture the meeting's mixed audio and participant list when the meeting ends.
2.  **Backend (Local Server):** A FastAPI server running on `localhost`. The frontend sends the captured audio here for analysis. The backend performs all the heavy AI lifting and generates the final report.

## 🛠️ Tech Stack

| Area | Technology |
| :--- | :--- |
| **Backend** | [Python 3.11 (3.13 does not work)](https://www.python.org/), [FastAPI](https://fastapi.tiangolo.com/), [Uvicorn](https://www.uvicorn.org/) |
| **AI (On-Device)** | [pyannote.audio](https://github.com/pyannote/pyannote-audio) (Diarization), [faster-whisper](https://github.com/guillaumekln/faster-whisper) (Transcription) |
| **AI (Cloud)** | [Groq API](https://groq.com/) (LLM for Summarization) |
| **PDF** | [ReportLab](https://www.reportlab.com/) |
| **Frontend** | [SvelteKit](https://kit.svelte.dev/), [Tailwind CSS](https://tailwindcss.com/), [TypeScript](https://www.typescriptlang.org/) |
| **Build Tools** | [Node.js](https://nodejs.org/), [Vite](https://vitejs.dev/) |
| **SDK** | [Zoom Apps SDK (NPM)](https://www.npmjs.com/package/@zoom/appssdk) |
| **Tunneling** | [ngrok](https://ngrok.com/) (For local development) |

---

## 🚀 Getting Started: Installation & Setup

### Prerequisites

*   **Python 3.9+** and `pip`
*   **Node.js v18+** and `npm`
*   **A Zoom Account** with permission to create and install developer apps.
*   **[ngrok](https://ngrok.com/download)** account and CLI.
*   **API Keys:**
    *   **Hugging Face:** A User Access Token is required for `pyannote`. [Get one here](https://huggingface.co/settings/tokens).
    *   **Groq:** An API Key for the summarization service. [Get one here](https://console.groq.com/keys).

### Step 1: Backend Setup

1.  **Clone the repository and navigate to the backend:**
    ```bash
    git clone https://github.com/your-username/slugg.git
    cd slugg/backend
    ```

2.  **Create and configure your environment file:**
    *   Create a file named `.env` in the `backend` directory.
    *   Add your secret keys to this file. **This file must not be committed to Git.**
    ```ini
    # backend/.env
    HUGGINGFACE_TOKEN=
    GROQ_API_KEY=
    ```

3.  **Create a virtual environment and install dependencies:**
    ```bash
    python -m venv venv
    source venv/bin/activate  # On Windows: venv\Scripts\activate
    pip install -r requirements.txt
    ```

4.  **Run the FastAPI server:**
    ```bash
    uvicorn server:app --reload
    ```
    The server will start on `http://localhost:8000`.
    **Note:** The first run will download AI models, which can take several minutes and a few gigabytes of disk space.

### Step 2: Frontend Setup (SvelteKit)

1.  **Navigate to the frontend directory and install dependencies:**
    *   Open a **new terminal window**.
    *   Assuming the SvelteKit project is in a `frontend` directory:
    ```bash
    cd ../frontend
    npm install
    npm install @zoom/appssdk
    ```

2.  **Build the application:**
    *   For testing in Zoom, you need to create a static build of the app.
    ```bash
    npm run build
    ```
    This will generate the final, optimized files in the `build/` directory.

3.  **Serve the built frontend:**
    *   Use a simple server to serve the contents of the `build` directory on port 9000.
    ```bash
    # This command serves the 'build' subdirectory
    python -m http.server --directory build 9000
    ```

4.  **Expose the server with ngrok:**
    *   Open a **third terminal window**.
    *   Run `ngrok` to create a secure public URL for your local frontend server.
    ```bash
    ngrok http 9000
    ```
    *   Copy the **HTTPS** URL provided by ngrok (e.g., `https://random-string.ngrok-free.app`). **You will need this for the next step.**

### Step 3: Zoom App Configuration

1.  Navigate to the [Zoom App Marketplace](https://marketplace.zoom.us/) and click "Develop" -> "Build App".
2.  Choose "Zoom App" as the app type.
3.  **App URLs:**
    *   **Home URL:** Paste your `ngrok` HTTPS URL.
    *   **Redirect URL for OAuth:** Paste your `ngrok` HTTPS URL.
    *   **Domain Allow List:** Add the `ngrok` domain (e.g., `random-string.ngrok-free.app`).
4.  **Scopes:** Click "Add Scopes" and add the following capabilities.
    *   `getMeetingParticipants`
    *   `getAudioRawData`
    *   `getMeetingContext`
    *   `onMeetingStateChange`
    *   `onActiveSpeakerChange` (For future real-time feedback feature)
5.  **Installation:** Install the app to your account using the "Local Test" URL or "Install" button on the app configuration page.

## 🏃‍♀️ Usage Flow

1.  Ensure all three terminals are running: **Backend Server**, **Frontend Server**, and **ngrok**.
2.  Start or join a Zoom meeting.
3.  Click the "Apps" button in the Zoom toolbar and open "Slugg".
4.  Conduct your meeting. The app will wait in the background.
5.  When the meeting ends, the `onMeetingStateChange` event triggers the analysis:
    *   The frontend sends the captured audio to your local backend.
    *   The backend performs diarization, transcription, and summarization.
6.  A "Save As" dialog appears, prompting you to download `meeting_report.pdf`.

## Sample Report (Mock-up)

Toplantı mock'u ses kaydı: https://drive.google.com/file/d/13olsfw-FGLR0NHqCLiWVme5ylPqGxlBK/view?usp=sharing  

### **Toplantı Analiz Raporu**
## **📜 Örnek Rapor: "Software 3.0" Konsept Tartışması**

**Tarih:** 05.07.2025  
**Toplam Süre:** 00:34:55  

---

### **🚀 Yönetici Özeti (Executive Summary)**

#### **Toplantı Sağlık Skoru: 82/100**

**Ana Bulgular:** Toplantı, Andrej Karpathy'nin "Software 3.0" vizyonu üzerine son derece odaklı ve verimli bir fikir alışverişi şeklinde gerçekleşti. Katılımcılar, konuya hakimiyetlerini `LLM`'lerin işletim sistemlerine benzetilmesi gibi güçlü analojilerle gösterdiler. Toplantının en büyük gelişim alanı, katılım dengesizliğidir; Barkın Özer'in konuşma süresinin %55'ini oluşturması ve sıkça dolgu kelime kullanması dikkat çekti. Toplantı, felsefi bir tartışma olmasına rağmen, somut bir aksiyon maddesiyle sonuçlanarak değer yarattı.

---

### **📊 Anahtar Performans Göstergeleri (KPIs)**

| Metrik | Değer | Değerlendirme |
| :--- | :--- | :--- |
| **Katılım Dengesi (Gini)** | 0.52 | ⚠️ Dengesiz |
| **Sonuç Odaklılık** | 0 Karar, 2 Aksiyon | 🟠 Geliştirilebilir |
| **Etkileşim Seviyesi** | 1 Uzun Sessizlik | ✅ Yüksek |
| **Konuşma Netliği (Dolgu Kelime)**| %4.8 Ortalama | 🟠 Orta |

---

### **🧠 Yapay Zeka Analizi (AI-Powered Insights)**

#### **Özet**

Toplantı, Karpathy'nin yazılım evrimini "Software 1.0" (klasik kod), "Software 2.0" (sinir ağları) ve "Software 3.0" (`LLM`'ler) olarak ayırmasıyla başladı. Katılımcılar, `LLM`'lerin birer "işletim sistemi" gibi davrandığı (Windows vs. Linux), bağlam penceresinin (context window) ise "RAM" gibi çalıştığı analojisini tartıştılar. `Agentic` sistemlerin geleceği, Iron Man'in zırhı (insanı güçlendiren) ve robotu (tam otonom) arasındaki fark üzerinden ele alındı. `Vibe coding` ve `no-code` araçlarının programlamayı demokratikleştirdiği, ancak karmaşık ve özgün projeler için hala insan mühendisliğinin kritik olduğu vurgulandı. Son olarak, `LLM`'lerin insan verisiyle eğitildiği için bilişsel zaafları ("pürüzlü zeka") olduğu ve altyapının bu yeni `agent`'lar için yeniden tasarlanması gerektiği belirtildi.

#### **Öne Çıkan Konular**

* Software 3.0 Paradigması ve Evrimi (%50)
* Agentic Sistemler ve Geleceği (`CrewAI`, `LangGraph`) (%30)
* LLM'lerin Mimarisi ve Zaafları (İşletim Sistemi Analojisi) (%20)

#### **Alınan Kararlar ve Aksiyon Maddeleri**

* **[KARAR]** Alınan net bir karar bulunmamaktadır.
* **[AKSİYON]** **Bülent Siyah:** Karpathy'nin bahsettiği `vibe coding` demo reposunu inceleyip ekiple paylaşacak.
* **[AKSİYON]** **Onur Demircan:** Bu tartışmanın ana başlıklarını içeren bir blog yazısı taslağı hazırlayacak.

---

### **👥 Katılımcı Bazında Detaylı Analiz**

| Katılımcı | Konuşma Süresi (%) | Konuşma Sayısı (Turns) | Duygu | Dolgu Kelime (%) | Gecikmeli Yanıt |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **Barkın Özer** | **55.2%** | 25 | Nötr | **6.8%** | **1** |
| Bülent Siyah | 29.8% | 20 | Pozitif | 2.5% | 0 |
| Onur Demircan | 15.0% | 12 | Pozitif | 3.1% | 0 |

<br>

*<p align="right">Bu rapor Slugg tarafından otomatik olarak oluşturulmuştur.</p>*


## Limitations & Future Roadmap

### Current Limitations

*   **Performance:** On-device AI processing is CPU/RAM intensive. A powerful machine (especially with a GPU) is recommended for faster results.
*   **Post-Meeting Analysis by Design:** Due to a Zoom SDK limitation (it only provides a single, mixed audio stream for all participants), accurate transcription and speaker separation can only be performed **after** the meeting concludes. This is a fundamental constraint of the platform that necessitates a post-processing approach for accuracy.
*   **Speaker Mapping Heuristic:** The mapping of generic speaker labels (`SPEAKER_00`) to real names is based on a simple heuristic (e.g., matching the longest-speaking voice to the first participant alphabetically). This may be inaccurate in meetings with balanced talk times or when participants join/leave.

### Future Ideas

*   [ ] **Live Talk-Time Meter:** Implement a live, in-meeting display of talk-time percentages. This would use the Zoom SDK's `onActiveSpeakerChange` event as a **heuristic** for immediate, approximate feedback, complementing the more accurate post-meeting analysis.
*   [ ] **Voiceprinting / Speaker Enrollment:** Allow users to "enroll" their voice. This would enable highly accurate speaker identification, replacing the current heuristic with a robust recognition model.
*   [ ] **Cloud Deployment Option:** Create a fully-hosted version for users who prefer not to run a local server.
*   [ ] **Deeper Analytics:** Analyze sentiment, detect filler words (`um`, `ah`), and track keywords over time.
*   [ ] **Web Dashboard:** A dashboard to view, compare, and manage reports from all past meetings.

## Deeper Analytics

Beyond the current MVP, Slugg is designed to evolve into a comprehensive meeting efficiency platform. The future roadmap focuses on extracting deeper, scientifically-backed metrics to provide actionable insights into team dynamics and meeting health.

This plan is divided into two tiers based on technical complexity.

### Tier 1: Foundational Metrics (Calculable from Existing Data)

These metrics can be calculated directly from the timestamped speaker data (`diarization`) and the transcript provided by the current `pyannote` and `faster-whisper` pipeline.

#### **Participation Balance Score**

*   **What it measures:** The fairness of the talk-time distribution among participants.
*   **How it's calculated:** Using the **Gini Coefficient**, a standard measure of statistical dispersion. The formula is `1 - ∑(participant's talk time / total talk time)²`.
*   **Interpretation:** A score close to **0** indicates perfect balance, where everyone spoke for a similar amount of time. A score approaching **1** signifies that one or a few participants are dominating the conversation.

#### **Silence Analysis**

*   **What it measures:** The meeting's flow, rhythm, and periods of disengagement or reflection.
*   **How it's calculated:** By measuring the time gaps between speaker turns identified by the diarization model.
    *   **Short Pauses (2-5 seconds):** Often a sign of healthy dialogue, indicating that participants are thinking before speaking.
    *   **Long Silences (10+ seconds):** Can indicate awkwardness, unpreparedness, indecision, or technical issues.

#### ** Flow & Turn-Taking**

*   **What it measures:** The interactivity and conversational dynamics of the meeting.
*   **How it's calculated:**
    *   **Turn Count:** The number of times each participant takes the floor.
    *   **Average Turn Duration:** `Total Talk Time / Turn Count`. A high average can indicate monologues, while a very low average might suggest frequent interruptions or a highly collaborative brainstorming session.

#### ** Response Latency (Heuristic)**

*   **What it measures:** A proxy for participant attention and engagement.
*   **How it's calculated:** This is a **heuristic** (an educated guess):
    1.  Search the transcript for a participant's name being mentioned (e.g., "Sarah, what are your thoughts on this?").
    2.  Get the timestamp when that sentence ends.
    3.  Check the diarization output to see if "Sarah" begins speaking within the next 5 seconds.
    4.  If not, flag it as a "delayed response," which could indicate a lack of attention.

### Tier 2: Advanced NLP & LLM-Powered Metrics

These metrics require additional libraries (like `transformers`) or more sophisticated prompting of the Groq LLM API.

#### ** Sentiment Analysis**

*   **What it measures:** The overall emotional tone of the meeting and the sentiment of individual contributions.
*   **How it's calculated:** Each sentence in the transcript is passed through a pre-trained sentiment analysis model.
*   **Requirements:** `pip install transformers`. A multilingual model from Hugging Face (e.g., `cardiffnlp/twitter-xlm-roberta-base-sentiment`) can be used to classify text as positive, negative, or neutral.

#### ** Action Item & Decision Detection**

*   **What it measures:** The meeting's effectiveness in producing tangible outcomes.
*   **How it's calculated:** By enhancing the system prompt sent to the Groq API. We instruct the LLM to not only summarize but also explicitly tag sentences that represent clear outcomes.
*   **Example Prompt Enhancement:** "...After the summary, list all sentences that are a clear **decision** or an **action item**. Preface them with `[DECISION]` and `[ACTION_ITEM]` respectively."
*   **Metrics:** `Decision Count`, `Action Item Count`, `Time to First Decision`.

#### ** Topic Analysis & Drift Detection**

*   **What it measures:** How well the meeting stuck to its intended agenda and where it deviated.
*   **How it's calculated:** The LLM is tasked with identifying the main topics of conversation from the transcript.
*   **Example Prompt Task:** "List the top 3-5 main topics discussed in this meeting. Estimate the percentage of the conversation dedicated to each topic."
*   **Metric:** A **Topic Focus Score** can be calculated by comparing the identified topics to a pre-defined agenda.

#### ** Filler Word Ratio**

*   **What it measures:** The clarity, confidence, and preparedness of speakers.
*   **How it's calculated:** A simple count of common filler words within the transcript, divided by the total word count.
*   **Example List (English):** `['like', 'you know', 'uh', 'um', 'so', 'actually', 'basically', 'right']`. A high ratio can indicate uncertainty or a lack of preparation.


## Contributing

Contributions are welcome! If you have an idea for a new feature or have found a bug, please open an issue to discuss it first. Pull requests are greatly appreciated.

## License

This project is licensed under the MIT License. See the [LICENSE](LICENSE) file for details.