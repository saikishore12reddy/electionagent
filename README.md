# AI-Powered Election Analytics Engine

Real-time election tracking and automated political intelligence for the Bihar Assembly 2025.

## Features
- **Live Scraping**: Fetches party-wise and constituency-wise data from the ECI portal.
- **AI Analytics**: Uses Gemini Pro to identify swings, battleground seats, and generate executive summaries.
- **Interactive Dashboard**: Streamlit-based UI for live tracking.
- **Data Persistence**: Auto-saves snapshots every 10 minutes to track trends.

## Setup

1. **Install Dependencies**:
   ```bash
   python3 -m pip install -r requirements.txt
   python3 -m playwright install chromium
   ```

2. **Configure API Keys**:
   Create a `.env` file from `.env.example` and add your `GROQ_API_KEY`.

3. **Run the Dashboard**:
   ```bash
   python3 -m streamlit run app.py
   ```

## Project Structure
- `scraper.py`: Core scraping logic using Playwright and JSON endpoints.
- `analyser.py`: LLM integration for political intelligence.
- `app.py`: Streamlit frontend.
- `snapshots/`: JSON data snapshots stored over time.
# electionagent
