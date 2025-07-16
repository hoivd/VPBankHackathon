#!/usr/bin/env python3
"""
AML Risk Assessment Model Inference Script
Loads CatBoost model from S3 and provides inference functionality
"""

import boto3
import joblib
import pandas as pd
import tempfile
from typing import Dict, Any, Union
from catboost import CatBoostClassifier, Pool
import sys 
import dotenv   
import os
dotenv.load_dotenv()
# Add the project root to Python path
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, project_root)

try:
    from config import S3_BUCKET_NAME, AWS_REGION
except ImportError:
    # Fallback values if config import fails
    S3_BUCKET_NAME = "team253"
    AWS_REGION = "ap-southeast-1"
    print("⚠️  Warning: Could not import config. Using default values.")


class AMLModelInference:
    def __init__(self, model_s3_key: str = "models/catboost_aml_model.pkl", 
                 bucket_name: str = S3_BUCKET_NAME, 
                 region_name: str = AWS_REGION):
        """
        Initialize AML Model Inference
        
        Args:
            model_s3_key: S3 key for the model file
            bucket_name: S3 bucket name
            region_name: AWS region
        """
        self.bucket_name = bucket_name
        self.model_s3_key = model_s3_key

        aws_access_key_id = os.getenv("AWS_ACCESS_KEY")
        aws_secret_access_key = os.getenv("AWS_SECRET_KEY")
        region_name = os.getenv("AWS_REGION", "ap-southeast-1")
        self.s3_client = boto3.client(
                        's3',
                        region_name=region_name,
                        aws_access_key_id=aws_access_key_id,
                        aws_secret_access_key=aws_secret_access_key
                    )

        self.model = None
        self.categorical_features = [
                "residence_area",
                "occupation",
                "age",

                "per_violation_type_1",
                "per_legal_status_1",
                "per_role_1",

                "per_violation_type_2",
                "per_legal_status_2",
                "per_role_2",

                "per_violation_type_3",
                "per_legal_status_3",
                "per_role_3",

                "per_violation_type_4",
                "per_legal_status_4",
                "per_role_4",

                "per_violation_type_5",
                "per_legal_status_5",
                "per_role_5",

                "org_violation_type_1",
                "org_legal_status_1",
                "org_role_1",

                "org_violation_type_2",
                "org_legal_status_2",
                "org_role_2",

                "org_violation_type_3",
                "org_legal_status_3",
                "org_role_3",

                "org_violation_type_4",
                "org_legal_status_4",
                "org_role_4",

                "org_violation_type_5",
                "org_legal_status_5",
                "org_role_5"
            ]

        
    def download_model_from_s3(self) -> str:
        """
        Download model from S3 to a temporary file
        
        Returns:
            Path to the downloaded model file
        """
        try:
            # Create a temporary file
            temp_file = tempfile.NamedTemporaryFile(delete=False, suffix='.pkl')
            temp_file_path = temp_file.name
            temp_file.close()
            
            print(f"Downloading model from s3://{self.bucket_name}/{self.model_s3_key}")
            
            # Download the model file
            self.s3_client.download_file(
                Bucket=self.bucket_name,
                Key=self.model_s3_key,
                Filename=temp_file_path
            )
            
            print(f"✅ Model downloaded successfully to {temp_file_path}")
            return temp_file_path
            
        except Exception as e:
            raise RuntimeError(f"❌ Failed to download model from S3: {e}")
    
    def load_model(self):
        """Load the model from S3"""
        if self.model is None:
            model_path = self.download_model_from_s3()
            try:
                self.model = joblib.load(model_path)
                print("✅ Model loaded successfully")
                
                # Clean up temporary file
                os.unlink(model_path)
                
            except Exception as e:
                # Clean up temporary file in case of error
                if os.path.exists(model_path):
                    os.unlink(model_path)
                raise RuntimeError(f"❌ Failed to load model: {e}")
    
    def preprocess_input(self, input_data: Dict[str, Any]) -> pd.DataFrame:
        """
        Preprocess input data for inference
        
        Args:
            input_data: Dictionary containing input features
            
        Returns:
            Preprocessed DataFrame
        """
        # Convert to DataFrame
        if isinstance(input_data, dict):
            df = pd.DataFrame([input_data])
        else:
            df = pd.DataFrame(input_data)
        
        # Fill missing categorical features with "Unknown"
        for col in self.categorical_features:
            if col in df.columns:
                df[col] = df[col].fillna("Unknown")
                # Replace "None" string with "Unknown"
                df[col] = df[col].replace("None", "Unknown")
        
        return df
    
    def predict(self, input_data: Union[Dict[str, Any], pd.DataFrame]) -> int:
        """
        Make prediction for single input
        
        Args:
            input_data: Input features as dictionary or DataFrame
            
        Returns:
            Predicted AML risk label (0-4)
        """
        if self.model is None:
            self.load_model()
        
        # Preprocess input
        processed_data = self.preprocess_input(input_data)
        
        # Make prediction
        prediction = self.model.predict(processed_data)
        
        return int(prediction[0])
    
    def predict_proba(self, input_data: Union[Dict[str, Any], pd.DataFrame]) -> Dict[str, float]:
        """
        Get prediction probabilities for all classes
        
        Args:
            input_data: Input features as dictionary or DataFrame
            
        Returns:
            Dictionary with class probabilities
        """
        if self.model is None:
            self.load_model()
        
        # Preprocess input
        processed_data = self.preprocess_input(input_data)
        
        # Get probabilities
        probabilities = self.model.predict_proba(processed_data)
        
        # Convert to dictionary
        class_names = ["Very Low", "Low", "Medium", "High", "Very High"]
        prob_dict = {f"Class_{i}_{name}": float(prob) for i, (name, prob) in enumerate(zip(class_names, probabilities[0]))}
        
        return prob_dict
    
    def get_risk_interpretation(self, label: int) -> str:
        """
        Get risk interpretation for a label
        
        Args:
            label: Predicted label (0-4)
            
        Returns:
            Risk interpretation string
        """
        interpretations = {
            0: "AML rất thấp",
            1: "AML thấp", 
            2: "AML trung bình",
            3: "AML cao",
            4: "AML rất cao"
        }
        return interpretations.get(label, "Unknown")


def create_sample_input() -> Dict[str, Any]:
    """Create a sample input for testing"""
    return {
        "residence_area": "TP Hồ Chí Minh",
        "occupation": "Giám đốc",
        "age": 45,
        "per_role": "Chủ mưu",
        "per_violation_type_1": "Rửa tiền",
        "per_legal_status_1": "Đã kết án",
        "per_violation_type_2": "Vi phạm hành chính",
        "per_legal_status_2": "Chưa rõ",
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


def main():
    """Main function for testing the inference"""
    print("🚀 AML Risk Assessment Model Inference")
    print("=" * 50)
    
    # Initialize inference engine
    inference_engine = AMLModelInference()
    
    # Create sample input
    sample_input = create_sample_input()
    
    print("📋 Sample Input:")
    for key, value in sample_input.items():
        if value != "None":
            print(f"  {key}: {value}")
    
    print("\n🔮 Making Prediction...")
    
    try:
        # Make prediction
        prediction = inference_engine.predict(sample_input)
        risk_interpretation = inference_engine.get_risk_interpretation(prediction)
        
        print(f"✅ Prediction: {prediction}")
        print(f"✅ Risk Level: {risk_interpretation}")
        
        # Get probabilities
        print("\n📊 Class Probabilities:")
        probabilities = inference_engine.predict_proba(sample_input)
        for class_name, prob in probabilities.items():
            print(f"  {class_name}: {prob:.4f}")
            
    except Exception as e:
        print(f"❌ Error during inference: {e}")


if __name__ == "__main__":
    main() 