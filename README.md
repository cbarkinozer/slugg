# Slugg: The On-Device Zoom Meeting Analyzer


<!-- You can create a simple banner image for your project -->

**Slugg helps you reclaim your time by analyzing Zoom meetings to identify dominators, measure engagement, and generate concise, actionable summaries. It's designed for tech teams who are tired of meetings that could have been an email.**

Slugg runs locally on your machine, ensuring your meeting data remains private. It processes audio on-device for transcription and diarization, then uses the high-speed Groq API for summarization, delivering a professional PDF report right after your meeting ends.

## ✨ Key Features

*   **📊 Talk-Time Analysis:** Automatically calculates and visualizes who spoke the most, identifying meeting dominators with clear percentages.
*   **🗣️ Speaker Diarization:** Intelligently separates speakers from the meeting's single audio stream ("who spoke when").
*   **📝 AI-Powered Summaries (Turkish/Dev-Speak):** Generates summaries in Turkish, but cleverly preserves English technical terms (`API`, `pull request`, `database`, etc.), just like developers actually speak.
*   **📄 PDF Report Generation:** Delivers a clean, professional PDF report at the end of each meeting, perfect for sharing or archiving.
*   **🔒 Privacy-Focused:** Transcription and diarization happen **on your device**. Only the anonymized text transcript is sent to an external API for summarization. The audio never leaves your machine.
*   **⚡ Blazing Fast Summaries:** Leverages the Groq API for near-instantaneous summary generation.

## ⚙️ How It Works (Architecture)

Slugg uses a two-part architecture to function within Zoom's security constraints while leveraging powerful local Python libraries.

```
+---------------------------+       +---------------------------------------------+
|        ZOOM CLIENT        |       |              USER'S COMPUTER                |
|                           |       |                                             |
| +-----------------------+ |       | +-----------------------------------------+ |
| |      SLUGG APP        | | HTTPS | |         LOCAL BACKEND SERVER          | |
| | (Frontend: JS, HTML)  | |<----->| |          (Python, FastAPI)            | |
| | - Captures raw audio  | |(ngrok)| | - Receives audio & participant data     | |
| | - Gets participants   | |       | | - ON-DEVICE: Transcribes (Whisper)      | |
| | - Triggers PDF download| |       | | - ON-DEVICE: Diarizes (pyannote)        | |
| +-----------------------+ |       | | - CLOUD: Summarizes (Groq API)          | |
|                           |       | | - Generates PDF (ReportLab)             | |
|                           |       | | - Sends PDF back to Frontend          | |
+---------------------------+       | +-----------------------------------------+ |
                                    +---------------------------------------------+
```

1.  **Frontend (Zoom App):** A web application running inside a Zoom window. It captures the meeting's mixed audio and participant list using the Zoom Apps SDK.
2.  **Backend (Local Server):** A FastAPI server running on `localhost`. The frontend sends the captured audio here when the meeting ends. The backend performs all the heavy AI lifting and generates the final report.

## 🛠️ Tech Stack

| Area      | Technology                                                                                                  |
| :-------- | :---------------------------------------------------------------------------------------------------------- |
| **Backend** | [Python](https://www.python.org/), [FastAPI](https://fastapi.tiangolo.com/), [Uvicorn](https://www.uvicorn.org/) |
| **AI (On-Device)** | [pyannote.audio](https://github.com/pyannote/pyannote-audio) (Diarization), [faster-whisper](https://github.com/guillaumekln/faster-whisper) (Transcription) |
| **AI (Cloud)** | [Groq API](https://groq.com/) (LLM for Summarization) |
| **PDF** | [ReportLab](https://www.reportlab.com/) |
| **Frontend** | [Zoom Apps SDK](https://developers.zoom.us/docs/zoom-apps/), HTML, CSS, JavaScript |
| **Tunneling** | [ngrok](https://ngrok.com/) (For local development) |

---

## 🚀 Getting Started: Installation & Setup

Follow these steps carefully to get Slugg running on your local machine.

### Prerequisites

*   **Python 3.9+**
*   **A Zoom Account** with permission to create and install developer apps.
*   **[ngrok](https://ngrok.com/download)** for exposing your local frontend server to Zoom.
*   **API Keys:**
    *   **Hugging Face:** A User Access Token is required for `pyannote`. [Get one here](https://huggingface.co/settings/tokens).
    *   **Groq:** An API Key for the summarization service. [Get one here](https://console.groq.com/keys).

### Step 1: Backend Setup

1.  **Clone the repository:**
    ```bash
    git clone https://github.com/your-username/slugg.git
    cd slugg/backend
    ```

2.  **Create and configure your environment file:**
    *   Create a file named `.env` in the `backend` directory.
    *   Add your secret keys to this file. **This file should NOT be committed to Git.**

    ```ini
    # backend/.env
    HUGGINGFACE_TOKEN="hf_YourHuggingFaceTokenHere"
    GROQ_API_KEY="gsk_YourGroqApiKeyHere"
    ```

3.  **Install Python dependencies:**
    ```bash
    pip install -r requirements.txt
    ```

4.  **Run the FastAPI server:**
    ```bash
    uvicorn server:app --reload
    ```
    The server will start on `http://localhost:8000`.
    **Note:** The first time you run this, it will download the `pyannote` and `faster-whisper` models, which can take several minutes and a few gigabytes of disk space.

### Step 2: Frontend Setup

The Zoom App needs to be served over HTTPS. We'll use a simple local server and `ngrok` to accomplish this.

1.  **Serve the frontend directory:**
    *   Open a **new terminal window** and navigate to the `frontend` directory.
    *   Use Python's built-in server (or any other simple server) to serve the files. We'll use port 9000.
    ```bash
    # In slugg/frontend/
    python -m http.server 9000
    ```

2.  **Expose the server with ngrok:**
    *   Open a **third terminal window**.
    *   Run `ngrok` to create a secure public URL for your local frontend server.
    ```bash
    ngrok http 9000
    ```
    *   `ngrok` will display a forwarding URL. Copy the **HTTPS** URL (e.g., `https://random-string-123.ngrok-free.app`).

### Step 3: Zoom App Configuration

1.  Navigate to the [Zoom App Marketplace](https://marketplace.zoom.us/) and click "Develop" -> "Build App".
2.  Choose "Zoom App" as the app type and give it a name (e.g., "My Slugg App").
3.  **App Credentials:** You'll see your Client ID and Client Secret here. You don't need them for this local setup, but they are important for distribution.
4.  **Information:** Fill in the required basic information.
5.  **App URLs:**
    *   **Home URL:** Paste the `ngrok` HTTPS URL.
    *   **Redirect URL for OAuth:** Paste the `ngrok` HTTPS URL.
    *   **Domain Allow List:** Add the `ngrok` domain (e.g., `random-string-123.ngrok-free.app`).
6.  **Scopes:** Click "Add Scopes" and add the following required capabilities:
    *   `getMeetingParticipants`
    *   `getAudioRawData`
    *   `getMeetingContext`
    *   `onMeetingStateChange`
7.  **Installation:** Your app is now configured. You can install it for your own account by using the "Local Test" URL provided on the "Submit" page, or by clicking the "Install" button.

## 🏃‍♀️ Usage Flow

1.  Ensure your **Backend Server** and **ngrok** tunnels are running.
2.  Start or join a Zoom meeting.
3.  Click the "Apps" button in the Zoom client's toolbar.
4.  Find and open "Slugg". The app will load and begin capturing audio in the background.
5.  Conduct your meeting as usual.
6.  When the meeting ends, Slugg will automatically:
    *   Send the captured audio to your local backend.
    *   Process the audio (transcribe, diarize).
    *   Generate a summary with Groq.
    *   Create a PDF report.
7.  A "Save As" dialog will appear, prompting you to download `meeting_report.pdf`.

## 📜 Sample Report (Mock-up)

The generated PDF will look something like this:

> ### **Toplantı Analiz Raporu**
>
> **Toplam Toplantı Süresi:** 00:42:15
>
> ---
>
> #### **Yapay Zeka Özeti**
>
> Ayşe toplantıya 5 dakika geç kaldı. Toplantının ilk 20 dakikası toplantının özetine bir şey katmadı. Toplantının ana odağı yeni `feature` için `API` entegrasyonuydu. Ahmet, `backend`'de `database schema` değişikliği gerektiğini belirtti. Zeynep, `frontend` tarafında bu değişikliğe göre `state management`'ın `refactor` edilmesi gerektiğini vurguladı. Bir `pull request`'in hafta sonuna kadar hazır olması kararlaştırıldı. Ayşe, mevcut `sprint`'teki bir `bug` nedeniyle `deployment`'ın gecikebileceği riskini dile getirdi. Toplantının son 30 dakikası farklı bir konuyla uğraşıldı ve toplantının amacından sapıldı.
>
> **Aksiyon Maddeleri:**
> *   **Ahmet:** `Database schema` güncellemesini yap ve `API endpoint`'ini hazırla.
> *   **Zeynep:** Yeni `API`'yi entegre etmek için `frontend`'i `refactor` et.
>
> ---
>
> #### **Konuşma Süresi Dağılımı**
>
> **Toplantı Dominatörü:** Zeynep
>
| Katılımcı | Konuşma Yüzdesi (%) |
| :--- | :--- |
| Zeynep | 45.12% |
| Ahmet | 30.55% |
| Ayşe | 18.91% |
| Can | 5.42% |

## 🚧 MVP Limitations & Future Roadmap

This is an MVP (Minimum Viable Product) with known limitations and exciting potential for future development.

### Current Limitations

*   **Performance:** All on-device AI processing is CPU/RAM intensive. A powerful machine is recommended.
*   **Speaker Mapping:** The mapping of generic speaker labels (`SPEAKER_00`) to participant names is based on a simple heuristic (most talkative = first participant, etc.). It may be inaccurate in meetings with balanced talk times.
*   **Real-time:** Analysis is only performed *after* the meeting ends.

### Future Ideas

*   [ ] **Real-Time Feedback:** Display talk-time percentages live during the meeting.
*   [ ] **Voiceprinting:** Implement speaker enrollment for highly accurate speaker identification, removing the reliance on heuristics.
*   [ ] **Cloud Deployment Option:** Create a version that can be fully hosted for users who don't want to run a local server.
*   [ ] **Deeper Analytics:** Analyze sentiment, detect filler words, and track keywords over time.
*   [ ] **Web Dashboard:** A dashboard to view reports from past meetings.

## ❤️ Contributing

Contributions are welcome! If you have an idea for a new feature or have found a bug, please open an issue to discuss it first. Pull requests are greatly appreciated.

## 📄 License

This project is licensed under the MIT License. See the [LICENSE](LICENSE) file for details.
