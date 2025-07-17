# AML Model Inference

This documentation explains how to use the AML (Anti-Money Laundering) risk assessment model inference scripts.

## Overview

The AML model inference system loads a pre-trained CatBoost model from S3 and provides predictions for AML risk assessment. The model predicts risk levels from 0 (very low) to 4 (very high) based on personal and organizational features.

## Files

- `model_inference.py` - Main inference script with the `AMLModelInference` class
- `example_inference.py` - Example usage demonstrations
- `requirements.txt` - Updated with necessary dependencies

## Setup

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

The key new dependencies added:
- `catboost==1.2.7` - For the CatBoost model
- `joblib==1.4.2` - For loading pickled models
- `scikit-learn==1.5.2` - For additional ML utilities

### 2. Configure AWS Credentials

Make sure your AWS credentials are configured for S3 access:

```bash
# Option 1: AWS CLI
aws configure

# Option 2: Environment variables
export AWS_ACCESS_KEY_ID=your_access_key
export AWS_SECRET_ACCESS_KEY=your_secret_key
export AWS_DEFAULT_REGION=ap-southeast-1

# Option 3: IAM roles (if running on EC2)
```

### 3. Upload Model to S3

Ensure your trained model is uploaded to S3:
```bash
aws s3 cp catboost_aml_model.pkl s3://team253/models/
```

## Usage

### Basic Usage

```python
from model_inference import AMLModelInference

# Initialize inference engine
inference_engine = AMLModelInference()

# Prepare input data
input_data = {
    "residence_area": "TP Hồ Chí Minh",
    "occupation": "Doanh nhân",
    "age": 45,
    "per_role": "Chủ mưu",
    "per_violation_type_1": "Rửa tiền",
    "per_legal_status_1": "Đã kết án",
    # ... other features (see complete example below)
}

# Make prediction
prediction = inference_engine.predict(input_data)
risk_level = inference_engine.get_risk_interpretation(prediction)

print(f"Prediction: {prediction}")  # 0-4
print(f"Risk Level: {risk_level}")  # Vietnamese description
```

### Getting Probabilities

```python
# Get prediction probabilities for all classes
probabilities = inference_engine.predict_proba(input_data)
for class_name, prob in probabilities.items():
    print(f"{class_name}: {prob:.4f}")
```

### Custom S3 Configuration

```python
# Use custom S3 path
custom_inference = AMLModelInference(
    model_s3_key="models/my_custom_model.pkl",
    bucket_name="my-bucket",
    region_name="us-west-2"
)
```

## Input Data Format

The model expects a dictionary with the following features:

### Required Features

| Feature | Type | Description | Example |
|---------|------|-------------|---------|
| `residence_area` | str | Province/city of residence | "TP Hồ Chí Minh" |
| `occupation` | str | Occupation/job | "Doanh nhân" |
| `age` | int | Age in years | 45 |
| `per_role` | str | Role in violations | "Chủ mưu" |

### Personal Violation Features (1-5)

For each violation (1 to 5):
- `per_violation_type_X` - Type of violation
- `per_legal_status_X` - Legal status

### Organization Violation Features (1-5)

For each organization violation (1 to 5):
- `org_violation_type_X` - Type of organization violation
- `org_legal_status_X` - Legal status

### Example Complete Input

```python
input_data = {
    "residence_area": "TP Hồ Chí Minh",
    "occupation": "Giám đốc",
    "age": 45,
    "per_role": "Chủ mưu",
    "per_violation_type_1": "Rửa tiền",
    "per_legal_status_1": "Đã kết án",
    "per_violation_type_2": "Vi phạm hành chính",
    "per_legal_status_2": "Chưa rõ",
    "per_violation_type_3": "None",  # Use "None" for empty values
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
```

## Risk Levels

| Label | Vietnamese | English | Description |
|-------|------------|---------|-------------|
| 0 | AML rất thấp | Very Low AML | Minimal risk |
| 1 | AML thấp | Low AML | Low risk |
| 2 | AML trung bình | Medium AML | Moderate risk |
| 3 | AML cao | High AML | High risk |
| 4 | AML rất cao | Very High AML | Maximum risk |

## Running Examples

```bash
# Run the main inference script with sample data
python model_inference.py

# Run comprehensive examples
python example_inference.py
```

## Supported Values

### Residence Areas (High Risk)
- "TP Hồ Chí Minh", "Hà Nội", "Hải Phòng", "Quảng Ninh", "Đà Nẵng"
- "Lạng Sơn", "Lào Cai", "Tây Ninh", "Kiên Giang", "Bình Dương"
- "Đồng Nai", "Cần Thơ", "An Giang", "Bà Rịa - Vũng Tàu"

### High-Risk Occupations
- "Cầm đồ", "Kinh doanh nhà hàng karaoke", "Chủ quán bar"
- "Làm từ thiện", "Tiếp viên quán", "Vũ công tự do"
- "Streamer", "Youtuber", "Tiktoker"
- "Kinh doanh vàng bạc", "Chơi chứng khoán", "Doanh nhân"
- "Tự doanh", "Môi giới bất động sản", "Kinh doanh đa cấp"

### Violation Types
- Personal: "Rửa tiền", "Tài trợ khủng bố", "Lừa đảo", "Chiếm đoạt tài sản", "Tham nhũng", "Hối lộ"
- Organization: "Trừng phạt tài chính", "Cấm vận kinh tế", "Trừng phạt ngành", "Trừng phạt thứ cấp"

### Legal Statuses
- "Đã kết án", "Đang điều tra", "Truy tố", "Chưa rõ", "Minh oan"

### Roles
- "Chủ mưu", "Cầm đầu", "Tổ chức thực hiện", "Tham gia", "Giúp sức", "Đồng phạm", "Bị nhắc tên", "Liên quan bị động"

## Error Handling

The script includes comprehensive error handling:

- **S3 Connection Errors**: Check AWS credentials and region
- **Model Loading Errors**: Verify model file exists and is valid
- **Prediction Errors**: Check input data format and values

## Performance Notes

- Model is cached after first load
- S3 download happens only once per session
- Temporary files are automatically cleaned up
- Supports batch predictions (pass DataFrame instead of dict)

## Troubleshooting

### Common Issues

1. **AWS Credentials Error**
   ```
   Solution: Configure AWS credentials using aws configure or environment variables
   ```

2. **Model Not Found in S3**
   ```
   Solution: Verify the model file exists at s3://team253/models/catboost_aml_model.pkl
   ```

3. **Import Errors**
   ```
   Solution: Install missing dependencies: pip install -r requirements.txt
   ```

4. **Prediction Errors**
   ```
   Solution: Check input data format matches expected schema
   ```

For more examples, see `example_inference.py`. 