from groq import AsyncGroq
import json
import asyncio

class BehavioralAnalyzer:
    def __init__(self, api_key: str):
        self.client = AsyncGroq(api_key=api_key)
        self.model_name = "llama-3.1-8b-instant" # Fast model for simple tasks

    async def _analyze(self, text: str) -> dict:
        """Single LLM call that returns sentiment + score + toxicity together."""
        prompt = f"""
Analyze the sentiment and toxicity of the following text:
"{text}"

Respond ONLY with a JSON object. 
CRITICAL: The values (sentiment and toxicity) MUST be in the same language as the input text (Hindi/English/Hinglish).

{{
    "sentiment": "Positive/Neutral/Negative (in user's language)",
    "score": 0.0,
    "toxicity": "Neutral / Toxic Tags: ... (in user's language)"
}}
"""
        try:
            response = await self.client.chat.completions.create(
                model=self.model_name,
                messages=[{"role": "user", "content": prompt}],
                temperature=0,
                response_format={"type": "json_object"}
            )
            return json.loads(response.choices[0].message.content)
        except Exception as e:
            return {"sentiment": "Error", "score": 0, "toxicity": f"Error: {str(e)}"}

    async def analyze_both(self, text: str) -> dict:
        """Single call returning both sentiment and toxicity. Preferred over separate calls."""
        data = await self._analyze(text)
        return {
            "sentiment": f"{data['sentiment']} ({data.get('score', 0)})",
            "toxicity": data.get('toxicity', 'Unknown')
        }

    # Keep individual methods for backward compatibility
    async def analyze_sentiment(self, text: str) -> str:
        res = await self.analyze_both(text)
        return res["sentiment"]

    async def analyze_toxicity(self, text: str) -> str:
        res = await self.analyze_both(text)
        return res["toxicity"]
