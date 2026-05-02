from pydantic import BaseModel, Field
from typing import List, Optional

class LegalAnalysis(BaseModel):
    detected_violation: str = Field("No specific violation detected", description="The detected legal violation from MVA 1988")
    relevant_section: str = Field("TBD", description="The specific section of the MVA 1988")
    possible_penalty: str = Field("Not specified", description="Possible penalty or fine for the violation")

class BehaviorAnalysis(BaseModel):
    party_a_sentiment: str = Field("Neutral", description="Sentiment of Party A's statement")
    party_a_toxicity: str = Field("Non-toxic", description="Toxicity level or tags for Party A")
    party_b_sentiment: str = Field("Neutral", description="Sentiment of Party B's statement")
    party_b_toxicity: str = Field("Non-toxic", description="Toxicity level or tags for Party B")

class LegalRiskAssessment(BaseModel):
    party_a_legal_risk: str = Field("Low", description="Legal risk or exposure for Party A")
    party_b_legal_risk: str = Field("Low", description="Legal risk or exposure for Party B")

class ResolutionSuggestion(BaseModel):
    suggested_legal_action: str = Field("Seek calm mediation", description="Fair and lawful resolution")
    suggested_mediation_advice: str = Field("Discuss the matter politely", description="Advice for calm mediation")
    preventive_advice: str = Field("Follow traffic rules", description="Advice to prevent future conflicts")

class ConflictReport(BaseModel):
    legal_analysis: LegalAnalysis
    behavior_analysis: BehaviorAnalysis
    legal_risk_assessment: LegalRiskAssessment
    resolution_suggestion: ResolutionSuggestion
