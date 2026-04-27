import json
import os
from dotenv import load_dotenv
from groq import Groq

load_dotenv()

class ElectionAnalyser:
    def __init__(self):
        api_key = os.getenv("GROQ_API_KEY")
        if not api_key:
            raise ValueError("GROQ_API_KEY not found in environment variables.")
        self.client = Groq(api_key=api_key)
        self.model = "llama-3.3-70b-versatile" # Premium Llama model on Groq

    def generate_insights(self, current_data, previous_data=None):
        """
        Generate political intelligence based on current and previous data using Groq.
        """
        prompt = f"""
        You are a senior political analyst. Analyze the following election data for Bihar Assembly 2025.
        
        Current Data:
        {json.dumps(current_data, indent=2)}
        
        Previous Data (for trend analysis):
        {json.dumps(previous_data, indent=2) if previous_data else "No previous data available."}
        
        Provide the following:
        1. **Swing Analysis**: Which party is gaining momentum compared to the last hour?
        2. **Battleground Identification**: List 3-5 seats with a margin of lead/victory less than 1,000 votes. If detailed seat data is missing, comment on the closest contests in the summary.
        3. **Executive Summary**: A concise 3-sentence summary of the current "State of the State".
        
        Return the response in a structured markdown format.
        """
        
        completion = self.client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": "You are a professional political pundit and data analyst."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.7,
            max_tokens=1024,
            top_p=1,
            stream=False,
        )
        
        return completion.choices[0].message.content

    def get_battleground_seats(self, data):
        """
        Manually identify battleground seats from the data (margin < 1000).
        """
        battlegrounds = []
        if 'detailed' in data:
            for const, candidates in data['detailed'].items():
                if len(candidates) >= 2:
                    try:
                        margin = int(candidates[0]['margin'].replace(',', ''))
                        if margin < 1000:
                            battlegrounds.append({
                                'constituency': const,
                                'winner': candidates[0]['candidate'],
                                'party': candidates[0]['party'],
                                'margin': margin
                            })
                    except:
                        continue
        return battlegrounds

if __name__ == "__main__":
    # Test with mock data
    mock_data = {
        "summary": {
            "results": [
                {"party": "BJP", "won": 89, "leading": 5, "total": 94},
                {"party": "JD(U)", "won": 85, "leading": 3, "total": 88},
                {"party": "RJD", "won": 25, "leading": 10, "total": 35}
            ]
        }
    }
    # analyser = ElectionAnalyser()
    # print(analyser.generate_insights(mock_data))
    print("Groq Analyser class ready.")
