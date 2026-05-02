from groq import AsyncGroq
import json
from .schemas import ConflictReport, LegalAnalysis, BehaviorAnalysis, LegalRiskAssessment, ResolutionSuggestion

class ConflictEvaluator:
    def __init__(self, api_key: str, text_model: str = "llama-3.3-70b-versatile", vision_model: str = "llama-3.2-11b-vision-preview"):
        self.client = AsyncGroq(api_key=api_key)
        self.text_model = text_model
        self.vision_model = vision_model

    async def evaluate(self, party_a: str, party_b: str, behavioral_data: dict, legal_context: str, images: list = None):
        system_prompt = f"""
        You are a Legal Conflict Monitoring AI specialized in Indian Motor Vehicle Law.
        Analyze the conflict between Party A and Party B based on the provided behavioral analysis, legal context, and any visual evidence provided.

        Your task is to:
        1. Detect legal violations based on the Motor Vehicles Act 1988 (MVA 1988).
        2. Identify relevant sections and possible penalties.
        3. Analyze the conflict neutrally, using visual evidence (if any) to verify claims.
        4. Evaluate legal exposure for both parties.
        5. Suggest a fair and lawful resolution and mediation advice.

        !!! CRITICAL RULE: LANGUAGE MATCHING !!!
        - Respond COMPLETELY in the SAME language used by the parties.
        - If the parties speak in Hindi, respond in Hindi. If Hinglish, respond in professional Hinglish.

        Behavioral Data:
        - Party A Sentiment: {behavioral_data['party_a']['sentiment']}
        - Party A Toxicity: {behavioral_data['party_a']['toxicity']}
        - Party B Sentiment: {behavioral_data['party_b']['sentiment']}
        - Party B Toxicity: {behavioral_data['party_b']['toxicity']}

        Legal Context:
        {legal_context}

        !!! CRITICAL: JSON STRUCTURE !!!
        YOU MUST RESPOND WITH A FLAT JSON OBJECT matching the schema below. 
        DO NOT WRAP THE RESPONSE IN A ROOT KEY LIKE "report" OR "conflict_analysis".
        
        JSON Structure:
        {{
            "legal_analysis": {{
                "detected_violation": "...",
                "relevant_section": "...",
                "possible_penalty": "..."
            }},
            "behavior_analysis": {{
                "party_a_sentiment": "...",
                "party_a_toxicity": "...",
                "party_b_sentiment": "...",
                "party_b_toxicity": "..."
            }},
            "legal_risk_assessment": {{
                "party_a_legal_risk": "...",
                "party_b_legal_risk": "..."
            }},
            "resolution_suggestion": {{
                "suggested_legal_action": "...",
                "suggested_mediation_advice": "...",
                "preventive_advice": "..."
            }}
        }}

        !!! LANGUAGE MATCHING !!!
        Respond in the same language as the input (Hindi/English/Hinglish).
        """

        user_content = [
            {"type": "text", "text": f"Party A Statement: {party_a}\nParty B Statement: {party_b}"}
        ]

        active_model = self.text_model
        if images:
            active_model = self.vision_model
            for b64 in images:
                user_content.append({
                    "type": "image_url",
                    "image_url": {"url": f"data:image/jpeg;base64,{b64}"}
                })

        try:
            response = await self.client.chat.completions.create(
                model=active_model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_content}
                ],
                temperature=0.1,
                response_format={"type": "json_object"}
            )
            
            content = response.choices[0].message.content
            data = json.loads(content)
            
            # Detect and fix nesting if LLM ignores instructions
            for key in ["conflict_analysis", "report", "analysis"]:
                if key in data and isinstance(data[key], dict):
                    data = data[key]
                    break
            
            return ConflictReport.model_validate(data)

        except Exception as e:
            print(f"Error in evaluation: {str(e)}")
            # Final fallback to ensure the app doesn't show "failed"
            return ConflictReport(
                legal_analysis=LegalAnalysis(detected_violation="Analysis inconclusive", relevant_section="Needs manual review"),
                behavior_analysis=BehaviorAnalysis(),
                legal_risk_assessment=LegalRiskAssessment(),
                resolution_suggestion=ResolutionSuggestion(suggested_legal_action="Consult a legal professional for a detailed review.")
            )
