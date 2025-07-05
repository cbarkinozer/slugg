# slugg/backend/test_backend.py

import requests
import os
import logging

# --- Configuration ---
# Make sure your FastAPI server is running before executing this script.
SERVER_URL = "http://127.0.0.1:8000/analyze/"

# 1. Provide the path to your mock audio file.
#    Place an audio file (e.g., a .wav or .mp3) in this 'backend' directory.
MOCK_AUDIO_FILE = "mock_meeting.wav" 

# 2. Define the list of mock participants for the test.
MOCK_PARTICIPANTS = ["Barkın Özer", "Bülent Siyah", "Onur Demircan"]

# 3. Define the name for the output PDF file.
OUTPUT_PDF_FILE = "test_report_output.pdf"

# Setup basic logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def run_test():
    """
    Simulates a request from the Zoom App frontend to the backend server
    to test the full analysis pipeline.
    """
    logging.info("--- Starting Backend Test ---")

    # --- Pre-flight Check ---
    # Check if the mock audio file exists before proceeding.
    if not os.path.exists(MOCK_AUDIO_FILE):
        logging.error(f"FATAL: Mock audio file not found at '{MOCK_AUDIO_FILE}'.")
        logging.error("Please place a valid audio file in the 'backend' directory and update the MOCK_AUDIO_FILE variable.")
        return

    logging.info(f"Using audio file: {MOCK_AUDIO_FILE}")
    logging.info(f"Simulating participants: {MOCK_PARTICIPANTS}")

    # --- Prepare the Request Data ---
    # The 'files' dictionary is used for file uploads in a multipart/form-data request.
    # The key 'audio_file' must match the parameter name in the FastAPI endpoint.
    try:
        with open(MOCK_AUDIO_FILE, "rb") as audio_file:
            files = {
                "audio_file": (os.path.basename(MOCK_AUDIO_FILE), audio_file, "audio/wav")
            }
            
            # The 'data' dictionary holds other form fields.
            # To send a list for a single form key, we pass a list of tuples.
            data = [("participants", p) for p in MOCK_PARTICIPANTS]

            logging.info(f"Sending POST request to {SERVER_URL}...")
            
            # --- Make the API Call ---
            response = requests.post(SERVER_URL, files=files, data=data, timeout=600) # 10 minute timeout for long audio

            # --- Handle the Response ---
            # Check if the request was successful
            if response.status_code == 200:
                logging.info("Success! Received a 200 OK response.")
                
                # The response content is the PDF file in bytes.
                # We write these bytes to a local file to view the result.
                with open(OUTPUT_PDF_FILE, "wb") as pdf_file:
                    pdf_file.write(response.content)
                
                logging.info(f"Successfully generated PDF report. Saved as '{OUTPUT_PDF_FILE}'.")

            else:
                # If something went wrong, print the error status and message from the server.
                logging.error(f"Request failed with status code: {response.status_code}")
                logging.error("Server response:")
                # The response text will contain the detailed error from FastAPI (HTTPException).
                print(response.text)

    except requests.exceptions.RequestException as e:
        logging.error(f"An error occurred while trying to connect to the server: {e}")
        logging.error("Please ensure the FastAPI server is running on http://127.0.0.1:8000.")
    except Exception as e:
        logging.error(f"An unexpected error occurred: {e}")

    logging.info("--- Backend Test Finished ---")


if __name__ == "__main__":
    run_test()