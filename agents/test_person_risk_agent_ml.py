#!/usr/bin/env python3
"""
Test script for Person Risk Agent with ML Integration
"""

import sys
import os

# Add the current directory to Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from agents.tools.person_risk_agent import PersonRiskAgent

def test_ml_integration():
    """Test the ML integration in Person Risk Agent"""
    print("🧪 TESTING PERSON RISK AGENT WITH ML INTEGRATION")
    print("=" * 60)
    
    try:
        # Initialize the agent
        print("🔧 Initializing Person Risk Agent...")
        agent = PersonRiskAgent()
        
        print(f"✅ Agent initialized successfully!")
        print(f"🤖 ML Model enabled: {agent.model_enabled}")
        print(f"🧠 LLM enabled: {agent.llm_enabled}")
        
        # Test queries
        test_queries = [
            "cho tôi thông tin về Trương Mỹ Lan",
            "thông tin về Nguyễn Văn A", 
            "bà Phạm Thị B có vi phạm gì không?"
        ]
        
        for i, query in enumerate(test_queries, 1):
            print(f"\n🧪 Test {i}: {query}")
            print("-" * 40)
            
            try:
                response = agent.process_query(query)
                print("✅ Query processed successfully!")
                print(f"📝 Response length: {len(response)} characters")
                
                # Check if ML prediction is included
                if "DỰ ĐOÁN MACHINE LEARNING" in response:
                    print("🤖 ML prediction included in response!")
                else:
                    print("⚠️ No ML prediction found in response")
                    
            except Exception as e:
                print(f"❌ Error processing query: {e}")
        
        print(f"\n✅ All tests completed!")
        
    except Exception as e:
        print(f"❌ Error during testing: {e}")
        import traceback
        print(f"Traceback: {traceback.format_exc()}")

def test_data_conversion():
    """Test the data conversion functionality"""
    print("\n🔧 TESTING DATA CONVERSION")
    print("=" * 40)
    
    try:
        agent = PersonRiskAgent()
        
        # Sample lookup result
        sample_lookup_result = {
            "personal_info": {
                "name": "Test Person",
                "address": "TP Hồ Chí Minh",
                "occupation": "Doanh nhân",
                "age": 45
            },
            "adverse_media": [
                {
                    "title": "Án tù vì tội rửa tiền",
                    "content": "Bị kết án 10 năm tù vì tội rửa tiền, vai trò chủ mưu trong đường dây",
                    "source": "VietnamNet"
                },
                {
                    "title": "Vi phạm hành chính", 
                    "content": "Bị phạt vi phạm hành chính về thuế, đang trong quá trình điều tra",
                    "source": "Báo Pháp luật"
                }
            ]
        }
        
        # Convert to model input
        model_input = agent.convert_lookup_to_model_input(sample_lookup_result)
        
        print("✅ Data conversion successful!")
        print("📊 Model input:")
        for key, value in model_input.items():
            if value != "None" and value != "Unknown":
                print(f"  {key}: {value}")
        
        # Test ML prediction if model is available
        if agent.model_enabled:
            try:
                prediction = agent.aml_model.predict(model_input)
                probabilities = agent.aml_model.predict_proba(model_input)
                risk_level = agent.aml_model.get_risk_interpretation(prediction)
                
                print(f"\n🤖 ML Prediction: {prediction} ({risk_level})")
                print("📈 Top probabilities:")
                sorted_probs = sorted(probabilities.items(), key=lambda x: x[1], reverse=True)
                for class_name, prob in sorted_probs[:3]:
                    print(f"  {class_name}: {prob:.4f}")
                    
            except Exception as e:
                print(f"⚠️ ML prediction failed: {e}")
        else:
            print("⚠️ ML model not available for testing")
            
    except Exception as e:
        print(f"❌ Error in data conversion test: {e}")

if __name__ == "__main__":
    test_ml_integration()
    test_data_conversion() 