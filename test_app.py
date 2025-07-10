# FILE: test_app.py

import requests
import os
import logging

# --- Configuration ---
SERVER_URL = "http://127.0.0.1:8000/analyze/"
MOCK_AUDIO_FILE = "mock_meeting.wav" 
MOCK_PARTICIPANTS = ["Barkın Özer", "Bülent Siyah", "Onur Demircan"]
OUTPUT_PDF_FILE = "test_report_output.pdf"

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def run_test():
    """
    Simulates a request from the Zoom App frontend to the backend server
    to test the full analysis pipeline.
    """
    logging.info("--- Starting Backend Test ---")

    if not os.path.exists(MOCK_AUDIO_FILE):
        logging.error(f"FATAL: Mock audio file not found at '{MOCK_AUDIO_FILE}'.")
        logging.error("Please place a valid audio file in the 'backend' directory and update the MOCK_AUDIO_FILE variable.")
        return

    logging.info(f"Using audio file: {MOCK_AUDIO_FILE}")
    logging.info(f"Simulating participants: {MOCK_PARTICIPANTS}")

    try:
        with open(MOCK_AUDIO_FILE, "rb") as audio_file:
            files = {
                "audio_file": (os.path.basename(MOCK_AUDIO_FILE), audio_file, "audio/wav")
            }
            
            data = [("participants", p) for p in MOCK_PARTICIPANTS]

            logging.info(f"Sending POST request to {SERVER_URL}... (This may take several minutes)")
            
            response = requests.post(SERVER_URL, files=files, data=data, timeout=600)

            if response.status_code == 200:
                logging.info("Success! Received a 200 OK response.")
                
                with open(OUTPUT_PDF_FILE, "wb") as pdf_file:
                    pdf_file.write(response.content)
                
                logging.info(f"Successfully generated PDF report. Saved as '{OUTPUT_PDF_FILE}'.")
                
                # --- UPDATED: Verification Instructions ---
                logging.info("\n--- MANUAL VERIFICATION CHECKLIST ---")
                logging.info(f"1. Open '{OUTPUT_PDF_FILE}'.")
                logging.info("2. Check for the 'Anahtar Performans Göstergeleri (KPIs)' table.")
                logging.info("3. Verify it contains a 'Katılım Dengesi (Gini)' score.")
                logging.info("4. Check the 'Katılımcı Bazında Detaylı Analiz' table.")
                logging.info("5. Verify it includes a 'Konuşma Sayısı' column.")
                logging.info("6. Verify it now also includes a 'Genel Duygu' column with values like 'Pozitif', 'Nötr'.")
                logging.info("7. Check the 'Yapay Zeka Özeti' to see if [AKSİYON] or [KARAR] tags are present and bolded.")
                logging.info("-------------------------------------\n")

            else:
                logging.error(f"Request failed with status code: {response.status_code}")
                logging.error("Server response:")
                print(response.text)

    except requests.exceptions.RequestException as e:
        logging.error(f"An error occurred while trying to connect to the server: {e}")
        logging.error("Please ensure the FastAPI server is running on http://127.0.0.1:8000.")
    except Exception as e:
        logging.error(f"An unexpected error occurred: {e}")

    logging.info("--- Backend Test Finished ---")


if __name__ == "__main__":
    run_test()