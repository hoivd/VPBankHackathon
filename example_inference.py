#!/usr/bin/env python3
"""
Example usage of AML Model Inference
Shows different ways to use the model for predictions
"""

from model_inference import AMLModelInference


def example_1_basic_usage():
    """Example 1: Basic usage with default settings"""
    print("📝 Example 1: Basic Usage")
    print("-" * 30)
    
    # Initialize the inference engine
    inference_engine = AMLModelInference()
    
    # Define input data
    input_data = {
        "residence_area": "Hà Nội",
        "occupation": "Doanh nhân",
        "age": 35,
        "per_role": "Chủ mưu",
        "per_violation_type_1": "Tài trợ khủng bố",
        "per_legal_status_1": "Đã kết án",
        "per_violation_type_2": "None",
        "per_legal_status_2": "None",
        "per_violation_type_3": "None",
        "per_legal_status_3": "None",
        "per_violation_type_4": "None",
        "per_legal_status_4": "None",
        "per_violation_type_5": "None",
        "per_legal_status_5": "None",
        "org_violation_type_1": "Cấm vận kinh tế",
        "org_legal_status_1": "Đang điều tra",
        "org_violation_type_2": "None",
        "org_legal_status_2": "None",
        "org_violation_type_3": "None",
        "org_legal_status_3": "None",
        "org_violation_type_4": "None",
        "org_legal_status_4": "None",
        "org_violation_type_5": "None",
        "org_legal_status_5": "None"
    }
    
    try:
        # Make prediction
        prediction = inference_engine.predict(input_data)
        risk_level = inference_engine.get_risk_interpretation(prediction)
        
        print(f"✅ Prediction: {prediction}")
        print(f"✅ Risk Level: {risk_level}")
        
    except Exception as e:
        print(f"❌ Error: {e}")


def example_2_with_probabilities():
    """Example 2: Getting prediction probabilities"""
    print("\n📊 Example 2: With Probabilities")
    print("-" * 35)
    
    inference_engine = AMLModelInference()
    
    # Low risk example
    low_risk_data = {
        "residence_area": "Bắc Ninh",
        "occupation": "Công nhân",
        "age": 30,
        "per_role": "None",
        "per_violation_type_1": "None",
        "per_legal_status_1": "None",
        "per_violation_type_2": "None",
        "per_legal_status_2": "None",
        "per_violation_type_3": "None",
        "per_legal_status_3": "None",
        "per_violation_type_4": "None",
        "per_legal_status_4": "None",
        "per_violation_type_5": "None",
        "per_legal_status_5": "None",
        "org_violation_type_1": "None",
        "org_legal_status_1": "None",
        "org_violation_type_2": "None",
        "org_legal_status_2": "None",
        "org_violation_type_3": "None",
        "org_legal_status_3": "None",
        "org_violation_type_4": "None",
        "org_legal_status_4": "None",
        "org_violation_type_5": "None",
        "org_legal_status_5": "None"
    }
    
    try:
        # Get prediction and probabilities
        prediction = inference_engine.predict(low_risk_data)
        probabilities = inference_engine.predict_proba(low_risk_data)
        
        print(f"✅ Prediction: {prediction}")
        print(f"✅ Risk Level: {inference_engine.get_risk_interpretation(prediction)}")
        print("\n📈 Probabilities:")
        for class_name, prob in probabilities.items():
            print(f"  {class_name}: {prob:.4f}")
            
    except Exception as e:
        print(f"❌ Error: {e}")


def example_3_custom_s3_path():
    """Example 3: Using custom S3 path"""
    print("\n🔧 Example 3: Custom S3 Path")
    print("-" * 30)
    
    # Initialize with custom S3 path
    custom_inference_engine = AMLModelInference(
        model_s3_key="models/custom_model.pkl",  # Custom model path
        bucket_name="team253vpbank"
    )
    
    print("ℹ️  This example shows how to use a custom S3 path.")
    print("   Change 'model_s3_key' to point to your specific model file.")


def example_4_multiple_predictions():
    """Example 4: Multiple predictions"""
    print("\n🔄 Example 4: Multiple Predictions")
    print("-" * 35)
    
    inference_engine = AMLModelInference()
    
    # Multiple test cases
    test_cases = [
        {
            "name": "High Risk Case",
            "data": {
                "residence_area": "TP Hồ Chí Minh",
                "occupation": "Cầm đồ",
                "age": 65,
                "per_role": "Cầm đầu",
                "per_violation_type_1": "Rửa tiền",
                "per_legal_status_1": "Đã kết án",
                "per_violation_type_2": "Tham nhũng",
                "per_legal_status_2": "Đã kết án",
                "per_violation_type_3": "None",
                "per_legal_status_3": "None",
                "per_violation_type_4": "None",
                "per_legal_status_4": "None",
                "per_violation_type_5": "None",
                "per_legal_status_5": "None",
                "org_violation_type_1": "Trừng phạt tài chính",
                "org_legal_status_1": "Đã kết án",
                "org_violation_type_2": "None",
                "org_legal_status_2": "None",
                "org_violation_type_3": "None",
                "org_legal_status_3": "None",
                "org_violation_type_4": "None",
                "org_legal_status_4": "None",
                "org_violation_type_5": "None",
                "org_legal_status_5": "None"
            }
        },
        {
            "name": "Medium Risk Case",
            "data": {
                "residence_area": "Đà Nẵng",
                "occupation": "Luật sư",
                "age": 40,
                "per_role": "Bị nhắc tên",
                "per_violation_type_1": "Vi phạm hành chính",
                "per_legal_status_1": "Chưa rõ",
                "per_violation_type_2": "None",
                "per_legal_status_2": "None",
                "per_violation_type_3": "None",
                "per_legal_status_3": "None",
                "per_violation_type_4": "None",
                "per_legal_status_4": "None",
                "per_violation_type_5": "None",
                "per_legal_status_5": "None",
                "org_violation_type_1": "None",
                "org_legal_status_1": "None",
                "org_violation_type_2": "None",
                "org_legal_status_2": "None",
                "org_violation_type_3": "None",
                "org_legal_status_3": "None",
                "org_violation_type_4": "None",
                "org_legal_status_4": "None",
                "org_violation_type_5": "None",
                "org_legal_status_5": "None"
            }
        }
    ]
    
    for test_case in test_cases:
        print(f"\n🧪 Testing: {test_case['name']}")
        try:
            prediction = inference_engine.predict(test_case['data'])
            risk_level = inference_engine.get_risk_interpretation(prediction)
            print(f"  Result: {prediction} ({risk_level})")
        except Exception as e:
            print(f"  ❌ Error: {e}")


def main():
    """Run all examples"""
    print("🚀 AML Model Inference Examples")
    print("=" * 50)
    
    # Run examples
    example_1_basic_usage()
    example_2_with_probabilities()
    example_3_custom_s3_path()
    example_4_multiple_predictions()
    
    print("\n✅ All examples completed!")
    print("\n💡 Tips:")
    print("  - Make sure your AWS credentials are configured")
    print("  - Ensure the model file exists in S3")
    print("  - Check that all required dependencies are installed")


if __name__ == "__main__":
    main() 