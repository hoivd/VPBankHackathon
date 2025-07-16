"""
VP Bank Agents Module
Provides AI agents for person risk analysis and related services
"""

__version__ = "1.0.0"
__author__ = "VP Bank Team"

# Core agent imports with error handling
try:
    from .tools.person_risk_agent import PersonRiskAgent
except ImportError:
    PersonRiskAgent = None

try:
    from .tools.person_lookup_dynamodb import PersonLookupDynamoDB
except ImportError:
    PersonLookupDynamoDB = None

try:
    from .tools.risk_analyzer import RiskAnalyzer
except ImportError:
    RiskAnalyzer = None

try:
    from .tools.model_inference import AMLModelInference
except ImportError:
    AMLModelInference = None

# Expose main components
__all__ = [
    'PersonRiskAgent',
    'PersonLookupDynamoDB', 
    'RiskAnalyzer',
    'AMLModelInference'
]

# Filter out None values from failed imports
__all__ = [item for item in __all__ if globals().get(item) is not None]

def get_available_agents():
    """Return list of available agent classes"""
    available = []
    for agent_name in ['PersonRiskAgent', 'PersonLookupDynamoDB', 'RiskAnalyzer', 'AMLModelInference']:
        if globals().get(agent_name) is not None:
            available.append(agent_name)
    return available

def create_person_risk_agent():
    """Factory function to create PersonRiskAgent instance"""
    if PersonRiskAgent is None:
        raise ImportError("PersonRiskAgent not available")
    return PersonRiskAgent()
