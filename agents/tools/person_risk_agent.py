#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Person Risk Analysis Agent
Combines PersonLookup and RiskAnalyzer to provide comprehensive Vietnamese-language risk assessment
"""
import os
import sys
import json
import re
from datetime import datetime
from typing import Dict, Any, Optional
from collections import Counter
import logging

# Add parent directory to path to import modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from agents.tools.person_lookup_dynamodb import PersonLookupDynamoDB
from agents.tools.model_inference import AMLModelInference
from llm_model.bedrock_manager import BedrockModelManager
from utils import Utils

class PersonRiskAgent:
    
    def __init__(self, region_name: str = None, aws_access_key_id: str = None, aws_secret_access_key: str = None):
        
        self.person_lookup = PersonLookupDynamoDB(
            region_name=region_name,
            aws_access_key_id=aws_access_key_id,
            aws_secret_access_key=aws_secret_access_key
        )
        
        # Initialize AML Model Inference
        try:
            self.aml_model = AMLModelInference()
            self.model_enabled = True
            print("✅ AML Model đã được tải thành công!")
        except Exception as e:
            print(f"⚠️ Không thể tải AML Model: {e}")
            print("📝 Sẽ chỉ sử dụng phân tích dựa trên quy tắc")
            self.aml_model = None
            self.model_enabled = True
        
        # Initialize LLM for advanced query processing
        try:
            self.bedrock_manager = BedrockModelManager(
                aws_access_key_id=aws_access_key_id or Utils.load_api_key_from_env("AWS_ACCESS_KEY"),
                aws_secret_access_key=aws_secret_access_key or Utils.load_api_key_from_env("AWS_SECRET_KEY"),
                region_name=region_name or "ap-southeast-1",
                default_model_id="anthropic.claude-instant-v1"
            )
            self.llm_enabled = True
        except Exception as e:
            print(f"⚠️ Không thể khởi tạo LLM: {e}")
            print("📝 Sẽ sử dụng regex để trích xuất tên người")
            self.bedrock_manager = None
            self.llm_enabled = True
        
        print("✅ Agent đã sẵn sàng!")

    def extract_person_name_from_query(self, query: str) -> Optional[str]:
        print(f"Trích xuất tên từ query: {query}")
        if not self.llm_enabled:
            return  self._extract_name_with_regex(query=query)
        else:
            print("Regex không thành công, đang thử LLM...")
            extracted_name = self.extract_person_name_with_llm(query)
            if extracted_name:
                print(f"LLM đã trích xuất được: {extracted_name}")
                return extracted_name
            else:
                print("LLM không trích xuất được tên")
        
        print("Không thể trích xuất tên người từ query")
        return None

    def _extract_name_with_regex(self, query: str) -> Optional[str]:
        patterns = [
            r"thông tin về\s+(.+?)(?:\s|$)",
            r"tìm kiếm\s+(.+?)(?:\s|$)",  
            r"(?:bà|ông|anh|chị)\s+([^,\.]+)",
            r"(.+?)\s+có",
            r"(.+?)\s+là",
            r"(.+?)(?:\s+của|\s+ở|\s+tại|$)"
        ]
        
        query_lower = query.lower().strip()
        
        query_clean = re.sub(r'\b(cho tôi|hãy|xin|làm ơn|vui lòng|giúp tôi|tìm|kiếm|thông tin|về|của|có|là|gì|như thế nào|ra sao)\b', '', query_lower)
        query_clean = query_clean.strip()
        
        for pattern in patterns:
            match = re.search(pattern, query_lower)
            if match:
                name = match.group(1).strip()
                name = re.sub(r'\b(có|là|gì|như thế nào|ra sao|của|ở|tại)\b.*', '', name).strip()
                if len(name) > 2 and len(name) < 50: 
                    return name.title() 
        
        words = query_clean.split()
        name_candidates = []
        for word in words:
            if word and (word[0].isupper() or any(c.isupper() for c in word)):
                name_candidates.append(word)
        
        if name_candidates:
            potential_name = ' '.join(name_candidates[:3])  # Take up to 3 words
            return potential_name.title()
        
        return None

    def extract_person_name_with_llm(self, query: str) -> Optional[str]:
        """
        Extract person name from Vietnamese query using LLM
        
        Args:
            query: Vietnamese query string
            
        Returns:
            Extracted person name or None
        """
        if not self.llm_enabled or not self.bedrock_manager:
            return None
            
        prompt = f"""Bạn là một chuyên gia trích xuất thông tin từ văn bản tiếng Việt. 
                Nhiệm vụ của bạn là trích xuất TÊN NGƯỜI từ câu hỏi sau.

                Câu hỏi: "{query}"

                Hướng dẫn:
                - Chỉ trả về TÊN NGƯỜI duy nhất được đề cập trong câu hỏi
                - Nếu có nhiều tên, chỉ trả về tên chính được hỏi về
                - Không bao gồm danh xưng (ông, bà, anh, chị)
                - Không bao gồm thông tin bổ sung khác
                - Nếu không tìm thấy tên người nào, trả về "KHÔNG_TÌM_THẤY"
                - Định dạng tên theo chuẩn tiếng Việt (viết hoa chữ cái đầu)

                Ví dụ:
                - "Võ Tấn Hoàng Văn là ai vậy?" → "Võ Tấn Hoàng Văn"
                - "Cho tôi thông tin về bà Trương Mỹ Lan" → "Trương Mỹ Lan"
                - "Ông Nguyễn Văn A có vi phạm gì không?" → "Nguyễn Văn A"
                - "Thời tiết hôm nay như thế nào?" → "KHÔNG_TÌM_THẤY"

                Tên người:"""

        try:
            response, _ = self.bedrock_manager.generate(
                prompt=prompt,
                model_type="claude",
                temperature=0.1,
                max_tokens=100
            )
            
            if response and response.strip():
                extracted_name = response.strip().strip('"').strip("'")
                
                # Check if valid name was found
                if extracted_name == "KHÔNG_TÌM_THẤY" or extracted_name.lower() == "không_tìm_thấy":
                    return None
                
                # Basic validation
                if len(extracted_name) > 2 and len(extracted_name) < 50:
                    return extracted_name
                    
            return None
            
        except Exception as e:
            print(f"⚠️ Lỗi khi sử dụng LLM để trích xuất tên: {e}")
            return None

    def convert_lookup_to_model_input(self, lookup_result: Dict[str, Any]) -> Dict[str, Any]:
        """
        Convert formatted lookup result to AML model input format
        
        Args:
            lookup_result: Formatted result from lookup_person_comprehensive_v2
            
        Returns:
            Dictionary formatted for AML model input
        """
        model_input = {
            "residence_area": "Không rõ",
            "occupation": "Không rõ", 
            "age": 40,
            
            "per_violation_type_1": None,
            "per_legal_status_1": None,
            "per_role_1": None,

            "per_violation_type_2": None,
            "per_legal_status_2": None,
            "per_role_2": None,

            "per_violation_type_3": None,
            "per_legal_status_3": None,
            "per_role_3": None,

            "per_violation_type_4": None,
            "per_legal_status_4": None,
            "per_role_4": None,

            "per_violation_type_5": None,
            "per_legal_status_5": None,
            "per_role_5": None,

            "org_violation_type_1": None,
            "org_legal_status_1": None,
            "org_role_1": None,

            "org_violation_type_2": None,
            "org_legal_status_2": None,
            "org_role_2": None,

            "org_violation_type_3": None,
            "org_legal_status_3": None,
            "org_role_3": None,

            "org_violation_type_4": None,
            "org_legal_status_4": None,
            "org_role_4": None,

            "org_violation_type_5": None,
            "org_legal_status_5": None,
            "org_role_5": None
        }
        
        try:
            # Extract personal information from person_info
            if "person_info" in lookup_result and lookup_result["person_info"]:
                person_info = lookup_result["person_info"]
                
                # Extract residence area
                residence = person_info.get("hometown_or_residence")
                if residence:
                    model_input["residence_area"] = residence
                
                # Extract occupation
                occupation = person_info.get("occupation_or_position")
                if occupation:
                    model_input["occupation"] = occupation
                
                # Extract age
                age = person_info.get("age")
                if age:
                    try:
                        model_input["age"] = int(age)
                    except:
                        pass
            
            # Extract personal violations from invidual_AML
            if "invidual_AML" in lookup_result and lookup_result["invidual_AML"]:
                individual_aml = lookup_result["invidual_AML"]
                
                # Process for the main person (usually first key in the dict)
                if isinstance(individual_aml, dict) and individual_aml:
                    person_name = list(individual_aml.keys())[0] if individual_aml else None
                    if person_name and person_name in individual_aml:
                        violations = individual_aml[person_name]
                        
                        # Process each violation type
                        idx = 0
                        for violation_type, details in violations.items():
                            if idx >= 5:  # Max 5 violations
                                break
                                
                            idx += 1
                            model_input[f"per_violation_type_{idx}"] = violation_type
                            model_input[f"per_legal_status_{idx}"] = details.get("legal_status")
                            model_input[f"per_role_{idx}"] = details.get("customer_role")
            
            # Extract organization violations from organization_AML
            if "organization_AML" in lookup_result and lookup_result["organization_AML"]:
                org_aml = lookup_result["organization_AML"]
                
                # Process for all organizations
                if isinstance(org_aml, dict) and org_aml:
                    idx = 0
                    for org_name, violations in org_aml.items():
                        for violation_type, details in violations.items():
                            if idx >= 5:  # Max 5 violations
                                break
                                
                            idx += 1
                            model_input[f"org_violation_type_{idx}"] = violation_type
                            model_input[f"org_legal_status_{idx}"] = details.get("legal_status")
                            model_input[f"org_role_{idx}"] = details.get("customer_role")
            
        except Exception as e:
            print(f"⚠️ Lỗi khi chuyển đổi dữ liệu cho model: {e}")
            import traceback
            print(f"Chi tiết lỗi: {traceback.format_exc()}")
        
        return model_input

    def save_model_input_to_json(self, model_input: Dict[str, Any], person_name: str) -> str:
        """
        Save model input to JSON file
        
        Args:
            model_input: Model input data
            person_name: Person name for filename
            
        Returns:
            Path to saved JSON file
        """
        # Create filename with timestamp
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        safe_name = re.sub(r'[^\w\s-]', '', person_name).strip().replace(' ', '_')
        filename = f"model_input_{safe_name}_{timestamp}.json"
        
        # Save to agents directory
        agents_dir = os.path.dirname(os.path.abspath(__file__))
        filepath = os.path.join(agents_dir, filename)
        
        try:
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(model_input, f, ensure_ascii=False, indent=2, default=str)
            print(f"💾 Model input đã được lưu vào: {filepath}")
            return filepath
        except Exception as e:
            print(f"⚠️ Lỗi khi lưu model input: {e}")
            return ""
    
    def _map_violation_type(self, media_record: Dict[str, Any]) -> str:
        """Map media record to violation type"""
        content = str(media_record.get("content", "")).lower()
        title = str(media_record.get("title", "")).lower()
        
        violation_keywords = {
            "Rửa tiền": ["rửa tiền", "money laundering", "tẩy tiền"],
            "Tài trợ khủng bố": ["tài trợ khủng bố", "terrorism financing", "khủng bố"],
            "Lừa đảo": ["lừa đảo", "gian lận", "fraud", "scam"],
            "Chiếm đoạt tài sản": ["chiếm đoạt", "embezzlement", "tham ô"],
            "Tham nhũng": ["tham nhũng", "corruption", "hối lộ"],
            "Hối lộ": ["hối lộ", "bribery", "đút lót"],
            "Vi phạm hành chính": ["vi phạm hành chính", "administrative violation"],
            "Tranh chấp dân sự": ["tranh chấp", "civil dispute", "kiện tụng"],
            "Vi phạm dân sự": ["vi phạm dân sự", "civil violation"],
            "Vi phạm nhỏ": ["vi phạm nhỏ", "minor violation"]
        }
        
        text_to_check = f"{content} {title}"
        for violation_type, keywords in violation_keywords.items():
            if any(keyword in text_to_check for keyword in keywords):
                return violation_type
        
        return None
    
    def _map_legal_status(self, media_record: Dict[str, Any]) -> str:
        """Map media record to legal status"""
        content = str(media_record.get("content", "")).lower()
        
        status_keywords = {
            "Đã kết án": ["kết án", "tuyên án", "án tù", "convicted", "sentenced"],
            "Đang điều tra": ["điều tra", "investigation", "đang xử lý"],
            "Truy tố": ["truy tố", "prosecution", "prosecuted"],
            "Chưa rõ": ["chưa rõ", "unknown", "unclear"],
            "Minh oan": ["minh oan", "vindicated", "cleared"]
        }
        
        for status, keywords in status_keywords.items():
            if any(keyword in content for keyword in keywords):
                return status
        
        return "Chưa rõ"
    
    def _map_person_role(self, media_record: Dict[str, Any]) -> str:
        """Map media record to person role"""
        content = str(media_record.get("content", "")).lower()
        
        role_keywords = {
            "Chủ mưu": ["chủ mưu", "mastermind", "cầm đầu"],
            "Cầm đầu": ["cầm đầu", "leader", "thủ lĩnh"],
            "Tổ chức thực hiện": ["tổ chức", "organizer"],
            "Tham gia": ["tham gia", "participate", "involved"],
            "Giúp sức": ["giúp sức", "assist", "hỗ trợ"],
            "Đồng phạm": ["đồng phạm", "accomplice", "complicit"],
            "Bị nhắc tên": ["nhắc tên", "mentioned", "liên quan"],
            "Liên quan bị động": ["liên quan", "related", "passive"]
        }
        
        for role, keywords in role_keywords.items():
            if any(keyword in content for keyword in keywords):
                return role
        
        return "Bị nhắc tên"
    
    def _map_org_violation_type(self, org_record: Dict[str, Any]) -> str:
        """Map organization record to violation type"""
        content = str(org_record.get("content", "")).lower()
        
        org_violation_keywords = {
            "Trừng phạt tài chính": ["trừng phạt tài chính", "financial sanctions"],
            "Cấm vận kinh tế": ["cấm vận", "embargo", "economic sanctions"],
            "Trừng phạt ngành": ["trừng phạt ngành", "sectoral sanctions"],
            "Trừng phạt thứ cấp": ["trừng phạt thứ cấp", "secondary sanctions"]
        }
        
        for violation_type, keywords in org_violation_keywords.items():
            if any(keyword in content for keyword in keywords):
                return violation_type
        
        return None
    
    def _map_org_legal_status(self, org_record: Dict[str, Any]) -> str:
        """Map organization record to legal status"""
        content = str(org_record.get("content", "")).lower()
        
        status_keywords = {
            "Đã kết án": ["kết án", "convicted"],
            "Đang điều tra": ["điều tra", "investigation"],
            "Truy tố": ["truy tố", "prosecution"]
        }
        
        for status, keywords in status_keywords.items():
            if any(keyword in content for keyword in keywords):
                return status
        
        return "Chưa rõ"

    def _map_org_role(self, org_record: Dict[str, Any]) -> str:
        """Map organization record to role"""
        content = str(org_record.get("content", "")).lower()
        
        role_keywords = {
            "Chủ quản": ["chủ quản", "owner", "sở hữu"],
            "Quản lý": ["quản lý", "management"],
            "Điều hành": ["điều hành", "operation"],
            "Liên quan": ["liên quan", "related"]
        }
        
        for role, keywords in role_keywords.items():
            if any(keyword in content for keyword in keywords):
                return role
        
        return "Liên quan"

    def calculate_risk_score(self, lookup_result: Dict[str, Any]) -> Dict[str, Any]:
        """
        Calculate risk score based on lookup result
        
        Args:
            lookup_result: Result from person lookup
            
        Returns:
            Dictionary with risk scores and analysis
        """
        risk_analysis = {
            "total_violations": 0,
            "total_violation_types": 0,
            "total_legal_statuses": 0,
            "total_legal_statuse_types": 0,
            "total_roles": 0,
            "total_role_type": 0,
            "details": {},
            "result": {},
            "ml_prediction": None
        }
        
        try:
            # Count violations from adverse media
            if "adverse_media" in lookup_result and lookup_result["adverse_media"]:
                adverse_media = lookup_result["adverse_media"]
                if isinstance(adverse_media, list):
                    risk_analysis["total_violations"] = len(adverse_media)
                    
                    violation_types = []
                    legal_statuses = []
                    roles = []
                    
                    for media in adverse_media:
                        violation_type = self._map_violation_type(media)
                        legal_status = self._map_legal_status(media)
                        role = self._map_person_role(media)
                        
                        if violation_type:
                            violation_types.append(violation_type)
                        legal_statuses.append(legal_status)
                        roles.append(role)
                    
                    risk_analysis["violation_types"] = list(set(violation_types))
                    risk_analysis["legal_statuses"] = list(set(legal_statuses))
                    risk_analysis["roles"] = list(set(roles))
            
            # Calculate risk score
            score = 0
            
            # Score based on number of violations
            score += min(risk_analysis["total_violations"] * 2, 20)
            
            # Score based on violation severity
            high_risk_violations = ["Rửa tiền", "Tài trợ khủng bố", "Tham nhũng", "Chiếm đoạt tài sản"]
            for violation in risk_analysis["violation_types"]:
                if violation in high_risk_violations:
                    score += 15
                else:
                    score += 5
            
            # Score based on legal status
            if "Đã kết án" in risk_analysis["legal_statuses"]:
                score += 20
            elif "Truy tố" in risk_analysis["legal_statuses"]:
                score += 15
            elif "Đang điều tra" in risk_analysis["legal_statuses"]:
                score += 10
            
            # Score based on role
            high_risk_roles = ["Chủ mưu", "Cầm đầu", "Tổ chức thực hiện"]
            for role in risk_analysis["roles"]:
                if role in high_risk_roles:
                    score += 10
                elif role in ["Tham gia", "Đồng phạm"]:
                    score += 5
            
            risk_analysis["risk_score"] = score
            
            # Determine risk level
            if score >= 50:
                risk_analysis["risk_level"] = "Rất cao"
            elif score >= 30:
                risk_analysis["risk_level"] = "Cao"
            elif score >= 15:
                risk_analysis["risk_level"] = "Trung bình"
            elif score > 0:
                risk_analysis["risk_level"] = "Thấp"
            else:
                risk_analysis["risk_level"] = "Không có"
            
        except Exception as e:
            print(f"⚠️ Lỗi khi tính toán điểm risk: {e}")
        
        return risk_analysis

    def calculate_risk_score_v2(self, lookup_result: Dict[str, Any]) -> Dict[str, Any]:
        """
        Calculate risk score based on lookup result with new format
        
        Args:
            lookup_result: Result from person_lookup_comprehensive_v2
            
        Returns:
            Dictionary with risk scores and analysis
        """
        risk_analysis = {
            "total_violations": 0,
            "total_violation_types": 0,
            "total_legal_statuses": 0,
            "total_legal_statuse_types": 0,
            "total_roles": 0,
            "total_role_type": 0,
            "details": {},
            "result": {},
            "ml_prediction": None
        }
        
        try:
            # Initialize sets to track unique values across all data
            individual_violation_types = set()
            individual_legal_statuses = set()
            individual_roles = set()
            
            # Initialize lists to track all values (including duplicates)
            individual_violation_types_list = []
            individual_legal_statuses_list = []
            individual_roles_list = []
            
            organization_violation_types = set()
            organization_legal_statuses = set()
            organization_roles = set()

            organization_violation_types_list = []
            organization_legal_statuses_list = []
            organization_roles_list = []
            # Process individual AML data
            if "invidual_AML" in lookup_result and lookup_result["invidual_AML"]:
                individual_aml = lookup_result["invidual_AML"]
                
                # Process all persons in individual AML data
                for person_name, violations in individual_aml.items():
                    # Process each violation type
                    for violation_type, details in violations.items():
                        # Add to violation types
                        individual_violation_types.add(violation_type)
                        individual_violation_types_list.append(violation_type)
                        
                        # Add legal status
                        legal_status = details.get("legal_status")
                        if legal_status:
                            individual_legal_statuses.add(legal_status)
                            individual_legal_statuses_list.append(legal_status)
                        
                        # Add customer role
                        customer_role = details.get("customer_role")
                        if customer_role:
                            individual_roles.add(customer_role)
                            individual_roles_list.append(customer_role)
                        
                        # Count media IDs as total violations
                        media_ids = details.get("media_ids", [])
                        risk_analysis["total_violations"] += len(media_ids)
            
            # Process organization AML data
            if "organization_AML" in lookup_result and lookup_result["organization_AML"]:
                org_aml = lookup_result["organization_AML"]
                
                # Process all organizations in organization AML data
                for org_name, violations in org_aml.items():
                    for violation_type, details in violations.items():
                        # Add to violation types
                        organization_violation_types.add(violation_type)
                        organization_violation_types_list.append(violation_type)
                        
                        # Add legal status
                        legal_status = details.get("legal_status")
                        if legal_status:
                            organization_legal_statuses.add(legal_status)
                            organization_legal_statuses_list.append(legal_status)
                        
                        # Add customer role
                        customer_role = details.get("customer_role")
                        if customer_role:
                            organization_roles.add(customer_role)
                            organization_roles_list.append(customer_role)
                        
                        # Count media IDs as total violations
                        media_ids = details.get("media_ids", [])
                        risk_analysis["total_violations"] += len(media_ids)
            
            # Calculate all the totals
            risk_analysis["total_violation_types"] = len(individual_violation_types) + len(organization_violation_types)
            risk_analysis["total_legal_statuses"] = len(individual_legal_statuses_list) + len(organization_legal_statuses_list)
            risk_analysis["total_legal_statuse_types"] = len(individual_legal_statuses) + len(organization_legal_statuses)
            risk_analysis["total_roles"] = len(individual_roles) + len(organization_roles)
            risk_analysis["total_role_type"] = len(individual_roles_list) + len(organization_roles_list)
            
            # Store detailed information
            risk_analysis["details"] = {
                "violation_types": {
                    'individual': individual_violation_types,
                    'organization': organization_violation_types
                    },
                "violation_types_list": {
                    'individual': individual_violation_types_list,
                    'organization': organization_violation_types_list
                    },
                "legal_statuses": {
                    'individual': individual_legal_statuses,
                    'organization': organization_legal_statuses
                    },
                "legal_statuses_list": {
                    'individual': individual_legal_statuses_list,
                    'organization': organization_legal_statuses_list
                    },
                "roles": {
                    'individual': individual_roles,
                    'organization': organization_roles
                    },
                "roles_list": {
                    'individual': individual_roles_list,
                    'organization': organization_roles_list
                    },
            }
            
            # Add all results to the result field
            risk_analysis["result"] = lookup_result
            
            # Try to get ML prediction if available
            try:
                if hasattr(self, 'ml_inference') and self.ml_inference:
                    ml_prediction = self.ml_inference.predict_from_lookup_result(lookup_result)
                    risk_analysis["ml_prediction"] = ml_prediction
            except Exception as ml_e:
                print(f"⚠️ Lỗi khi tính toán ML prediction: {ml_e}")
                risk_analysis["ml_prediction"] = None
            
        except Exception as e:
            print(f"⚠️ Lỗi khi tính toán điểm risk v2: {e}")
            import traceback
            print(f"Chi tiết lỗi: {traceback.format_exc()}")
        
        return risk_analysis

    def process_query(self, query: str) -> str:
        print(f"🔍 Xử lý truy vấn: {query}")
        
        # Extract person name from query
        person_name = self.extract_person_name_from_query(query)
        
        if not person_name:
            return (
                "❌ Xin lỗi, tôi không thể xác định tên người cần tìm kiếm từ truy vấn của bạn.\n\n"
                "💡 Vui lòng thử lại với định dạng:\n"
                "• 'cho tôi thông tin về [Tên người]'\n"
                "• 'tìm kiếm thông tin [Tên người]'\n"
                "• 'bà/ông [Tên người] có vi phạm gì không?'\n\n"
                "Ví dụ: 'cho tôi thông tin về Trương Mỹ Lan'"
            )
        
        print(f"📝 Tên người được trích xuất: {person_name}")
        
        try:
            # Perform person lookup
            lookup_result = self.person_lookup.lookup_person_comprehensive_v2(person_name)
            
            #lookup_result = 
            print("look up result is: ", lookup_result)
            
            # Calculate risk analysis with new scoring system
            risk_analysis = self.calculate_risk_score(lookup_result)
            # Convert to model input format
            model_input = self.convert_lookup_to_model_input(lookup_result)
            
            # Save model input to JSON file
            # self.save_model_input_to_json(model_input, person_name)
            
            # Add ML model prediction if available
            ml_prediction = None
            if self.model_enabled and self.aml_model:
                try:
                    print("🤖 Đang thực hiện dự đoán ML...")
                    # Get prediction and probabilities
                    prediction = self.aml_model.predict(model_input)
                    probabilities = self.aml_model.predict_proba(model_input)
                    risk_interpretation = self.aml_model.get_risk_interpretation(prediction)
                    
                    ml_prediction = {
                        "prediction": prediction,
                        "risk_level": risk_interpretation,
                        "probabilities": probabilities,
                        "model_input": model_input
                    }
                    
                    print(f"✅ Dự đoán ML: {prediction} ({risk_interpretation})")
                    
                except Exception as e:
                    print(f"⚠️ Lỗi khi thực hiện dự đoán ML: {e}")
                    ml_prediction = None
            
            # Add ML prediction to risk analysis
            if ml_prediction:
                risk_analysis["ml_prediction"] = ml_prediction
            
            # Format response in Vietnamese
            if not lookup_result or "error" in lookup_result:
                response = f"❌ Không tìm thấy thông tin về '{person_name}' trong hệ thống.\n\n"
                response += "Vui lòng kiểm tra lại tên người hoặc thử với các biến thể khác của tên."
                return response
            
            # Generate comprehensive Vietnamese response
            response = self.generate_vietnamese_response(person_name, risk_analysis, lookup_result)
            return response
            
        except Exception as e:
            print(f"❌ Lỗi khi xử lý truy vấn: {e}")
            return (
                f"❌ Đã xảy ra lỗi khi tìm kiếm thông tin về '{person_name}'.\n\n"
                f"Chi tiết lỗi: {str(e)}\n\n"
                "Vui lòng thử lại sau hoặc liên hệ quản trị viên."
            )

    def process_query_v2(self, person_id:str ,person_name:str , query:str =None) -> str:
        """
        Process a query with the new format
        
        Args:
            query: Vietnamese query about a person
            
        Returns:
            Formatted Vietnamese response
        """
        # print(f"🔍 Xử lý truy vấn v2: {query}")
        
        # person_name = self.extract_person_name_from_query(query)
        # person_name = "Trương Mỹ Lan"
        if not person_name or not person_id:
            return (
                "❌ Xin lỗi, tôi không thể xác định tên người cần tìm kiếm từ truy vấn của bạn.\n\n"
                "💡 Vui lòng thử lại với định dạng:\n"
                "• 'cho tôi thông tin về [Tên người]'\n"
                "• 'tìm kiếm thông tin [Tên người]'\n"
                "• 'bà/ông [Tên người] có vi phạm gì không?'\n\n"
                "Ví dụ: 'cho tôi thông tin về Trương Mỹ Lan'"
            )
        
        print(f"📝 Tên người được trích xuất: {person_name}")
        
        try:
            # Perform person lookup with v2 format
            lookup_result = self.person_lookup.lookup_person_comprehensive_v2(full_name=person_name,person_id=person_id,query=query)
            if not lookup_result or "error" in lookup_result:
                response = f"❌ Không tìm thấy thông tin về '{person_name}' trong hệ thống thoa man yeu cau cua ban.\n\n"
                response += "Vui lòng kiểm tra lại tên người hoặc thử với các biến thể khác của tên."
                return {"message":response}

            print(f"Kết quả lookup v2 nhận được", lookup_result)
            
            risk_analysis = self.calculate_risk_score_v2(lookup_result)
            # print("ket qua analys nhan duoc", risk_analysis)
            model_input = self.convert_lookup_to_model_input(lookup_result)
            print(f"Model input: {model_input}")
            
            # Save model input to JSON file
            # self.save_model_input_to_json(model_input, person_name)
            # model_input_path = self.save_model_input_to_json(model_input, person_name)
            # print(f"💾 Đã lưu model input vào: {model_input_path}")
            
            ml_prediction = None
            if self.model_enabled and self.aml_model:
                try:
                    print("🤖 Đang thực hiện dự đoán ML...")
                    # Get prediction and probabilities
                    prediction = self.aml_model.predict(model_input)
                    probabilities = self.aml_model.predict_proba(model_input)
                    risk_interpretation = self.aml_model.get_risk_interpretation(prediction)
                    
                    ml_prediction = {
                        "prediction": prediction,
                        "risk_level": risk_interpretation,
                        "probabilities": probabilities,
                        "model_input": model_input
                    }
                    
                    print(f"✅ Dự đoán ML: {prediction} ({risk_interpretation})")
                    
                    # Add ML prediction to risk analysis
                    risk_analysis["ml_prediction"] = ml_prediction
                    
                except Exception as e:
                    print(f"⚠️ Lỗi khi thực hiện dự đoán ML: {e}")
            

            
            # Generate comprehensive Vietnamese response
            # response = self.generate_vietnamese_response_v2(person_name, risk_analysis, lookup_result)
            response = risk_analysis
            return response
            
        except Exception as e:
            print(f"❌ Lỗi khi xử lý truy vấn: {e}")
            import traceback
            print(f"Chi tiết lỗi: {traceback.format_exc()}")
            return (
                f"❌ Đã xảy ra lỗi khi tìm kiếm thông tin về '{person_name}'.\n\n"
                f"Chi tiết lỗi: {str(e)}\n\n"
                "Vui lòng thử lại sau hoặc liên hệ quản trị viên."
            )
    
    def generate_vietnamese_response(self, person_name: str, risk_analysis: Dict[str, Any], lookup_result: Dict[str, Any]) -> str:
        """
        Generate comprehensive Vietnamese response based on risk analysis
        
        Args:
            person_name: Person name that was queried
            risk_analysis: Risk analysis result
            lookup_result: Original lookup result
            
        Returns:
            Formatted Vietnamese response
        """
        # Build response
        response = f"📋 THÔNG TIN VỀ {person_name.upper()}\n"
        response += "=" * 60 + "\n\n"
        
        # Personal information
        if "personal_info" in lookup_result and lookup_result["personal_info"]:
            personal_info = lookup_result["personal_info"]
            response += "👤 THÔNG TIN CÁ NHÂN:\n"
            
            if personal_info.get("name"):
                response += f"• Tên: {personal_info['name']}\n"
            if personal_info.get("occupation"):
                response += f"• Nghề nghiệp: {personal_info['occupation']}\n"
            if personal_info.get("address"):
                response += f"• Địa chỉ: {personal_info['address']}\n"
            if personal_info.get("age"):
                response += f"• Tuổi: {personal_info['age']}\n"
            response += "\n"
        
        # Risk Analysis
        response += f"🎯 PHÂN TÍCH RỦI RO:\n"
        response += f"• Tổng số vi phạm: {risk_analysis['total_violations']}\n"
        response += f"• Điểm rủi ro: {risk_analysis['risk_score']}/100\n"
        response += f"• Mức độ rủi ro: {risk_analysis['risk_level']}\n\n"
        
        if risk_analysis["violation_types"]:
            response += f"📝 LOẠI VI PHẠM:\n"
            for violation in risk_analysis["violation_types"]:
                response += f"• {violation}\n"
            response += "\n"
        
        if risk_analysis["legal_statuses"]:
            response += f"⚖️ TÌNH TRẠNG PHÁP LÝ:\n"
            for status in risk_analysis["legal_statuses"]:
                response += f"• {status}\n"
            response += "\n"
        
        if risk_analysis["roles"]:
            response += f"👥 VAI TRÒ:\n"
            for role in risk_analysis["roles"]:
                response += f"• {role}\n"
            response += "\n"
        
        # ML Prediction section if available
        if "ml_prediction" in risk_analysis:
            ml_pred = risk_analysis["ml_prediction"]
            response += f"🤖 DỰ ĐOÁN MACHINE LEARNING:\n"
            response += f"• Mức độ rủi ro dự đoán: {ml_pred['prediction']} - {ml_pred['risk_level']}\n\n"
            
            response += f"📊 Xác suất cho từng mức độ rủi ro:\n"
            for class_name, prob in ml_pred["probabilities"].items():
                percentage = prob * 100
                bar_length = int(percentage / 5)
                bar = "█" * bar_length + "░" * (20 - bar_length)
                response += f"  {class_name}: {percentage:5.1f}% {bar}\n"
            response += "\n"
        
        # Generate recommendations
        max_score = risk_analysis["risk_score"]
        ml_prediction = risk_analysis.get("ml_prediction")
        recommendations = self.generate_recommendations(risk_analysis["risk_level"], max_score, ml_prediction)
        response += recommendations
        
        return response

    def generate_vietnamese_response_v2(self, person_name: str, risk_analysis: Dict[str, Any], lookup_result: Dict[str, Any]) -> str:
        """
        Generate comprehensive Vietnamese response based on risk analysis with new format
        
        Args:
            person_name: Person name that was queried
            risk_analysis: Risk analysis result from calculate_risk_score_v2
            lookup_result: Original lookup result
            
        Returns:
            Formatted Vietnamese response
        """
        # Build response
        response = f"📋 THÔNG TIN VỀ {person_name.upper()}\n"
        response += "=" * 60 + "\n\n"
        
        # Personal information
        if "person_info" in lookup_result and lookup_result["person_info"]:
            person_info = lookup_result["person_info"]
            response += "👤 THÔNG TIN CÁ NHÂN:\n"
            
            if person_info.get("full_name"):
                response += f"• Tên: {person_info['full_name']}\n"
            if person_info.get("occupation_or_position"):
                response += f"• Nghề nghiệp: {person_info['occupation_or_position']}\n"
            if person_info.get("hometown_or_residence"):
                response += f"• Địa chỉ: {person_info['hometown_or_residence']}\n"
            if person_info.get("age"):
                response += f"• Tuổi: {person_info['age']}\n"
            if person_info.get("organization"):
                response += f"• Tổ chức: {person_info['organization']}\n"
            response += "\n"
        
        # Individual AML summary
        if "invidual_AML" in lookup_result and lookup_result["invidual_AML"]:
            individual_aml = lookup_result["invidual_AML"]
            response += "🚨 VI PHẠM CÁ NHÂN:\n"
            
            for person, violations in individual_aml.items():
                for violation_type, details in violations.items():
                    legal_status = details.get("legal_status", "Không rõ")
                    customer_role = details.get("customer_role", "Không rõ")
                    media_count = len(details.get("media_ids", []))
                    
                    response += f"• {violation_type} ({legal_status})\n"
                    response += f"  - Vai trò: {customer_role}\n"
                    response += f"  - Số lượng báo cáo: {media_count}\n"
            
            response += "\n"
        
        # Organization AML summary
        if "organization_AML" in lookup_result and lookup_result["organization_AML"]:
            org_aml = lookup_result["organization_AML"]
            response += "🏢 VI PHẠM TỔ CHỨC:\n"
            
            for org_name, violations in org_aml.items():
                response += f"Tổ chức: {org_name}\n"
                
                for violation_type, details in violations.items():
                    legal_status = details.get("legal_status", "Không rõ")
                    customer_role = details.get("customer_role", "Không rõ")
                    media_count = len(details.get("media_ids", []))
                    
                    response += f"• {violation_type} ({legal_status})\n"
                    response += f"  - Vai trò: {customer_role}\n"
                    response += f"  - Số lượng báo cáo: {media_count}\n"
                
                response += "\n"
        
        # ML Prediction section if available
        if risk_analysis["ml_prediction"]:
            ml_pred = risk_analysis["ml_prediction"]
            response += f"🤖 DỰ ĐOÁN MACHINE LEARNING:\n"
            response += f"• Mức độ rủi ro dự đoán: {ml_pred['prediction']} - {ml_pred['risk_level']}\n\n"
            
            response += f"📊 Xác suất cho từng mức độ rủi ro:\n"
            for class_name, prob in ml_pred["probabilities"].items():
                percentage = prob * 100
                bar_length = int(percentage / 5)
                bar = "█" * bar_length + "░" * (20 - bar_length)
                response += f"  {class_name}: {percentage:5.1f}% {bar}\n"
            response += "\n"
        
        # Generate recommendations based on ML prediction
        if risk_analysis["ml_prediction"]:
            ml_pred = risk_analysis["ml_prediction"]
            recommendations = self.generate_recommendations(
                ml_pred["risk_level"], 
                ml_pred["prediction"] * 25,  # Scale ML score (0-4) to match recommendation thresholds
                ml_pred
            )
            response += recommendations
        else:
            # Generate generic recommendations if no ML prediction
            recommendations = self.generate_recommendations("Trung bình", 15, None)
            response += recommendations
        
        return response

    def generate_recommendations(self, risk_level: str, max_score: int, ml_prediction: Optional[Dict[str, Any]] = None) -> str:
        """
        Generate recommendations based on risk level
        
        Args:
            risk_level: Overall risk level
            max_score: Maximum risk score found
            ml_prediction: ML prediction if available
            
        Returns:
            Vietnamese recommendations text
        """
        recommendations = "💼 KHUYẾN NGHỊ:\n"
        
        # Add ML prediction context if available
        if ml_prediction:
            ml_risk_level = ml_prediction["risk_level"]
            ml_score = ml_prediction["prediction"]
            recommendations += f"🤖 Dự đoán AI: {ml_risk_level} (Điểm: {ml_score}/4)\n"
            recommendations += f"📊 Quy tắc: {risk_level} (Điểm: {max_score}/100)\n\n"
        
        if max_score >= 50:
            recommendations += (
                "🔴 RỦI RO RẤT CAO - Cần thực hiện các biện pháp sau:\n"
                "• Từ chối giao dịch hoặc ngưng hợp tác ngay lập tức\n"
                "• Báo cáo lên cấp quản lý cao nhất\n"
                "• Xem xét báo cáo lên cơ quan chức năng\n"
                "• Thực hiện due diligence mở rộng nếu cần thiết\n"
                "• Lưu trữ tài liệu đầy đủ để đối phó với kiểm toán\n"
            )
        elif max_score >= 30:
            recommendations += (
                "🟠 RỦI RO CAO - Thực hiện giám sát chặt chẽ:\n"
                "• Áp dụng các biện pháp due diligence nâng cao\n"
                "• Thực hiện giám sát giao dịch liên tục\n"
                "• Yêu cầu tài liệu bổ sung và xác minh\n"
                "• Xin phê duyệt từ cấp quản lý trước khi tiếp tục\n"
                "• Rà soát định kỳ ít nhất 3 tháng/lần\n"
            )
        elif max_score >= 15:
            recommendations += (
                "🟡 RỦI RO TRUNG BÌNH - Thực hiện các biện pháp phòng ngừa:\n"
                "• Thực hiện due diligence chuẩn\n"
                "• Giám sát giao dịch bất thường\n"
                "• Rà soát định kỳ 6 tháng/lần\n"
                "• Lưu trữ hồ sơ theo quy định\n"
                "• Theo dõi cập nhật thông tin mới\n"
            )
        elif max_score > 0:
            recommendations += (
                "🟢 RỦI RO THẤP - Áp dụng quy trình chuẩn:\n"
                "• Thực hiện due diligence cơ bản\n"
                "• Giám sát theo quy trình thông thường\n"
                "• Rà soát định kỳ 1 năm/lần\n"
                "• Lưu ý theo dõi các cập nhật mới\n"
            )
        else:
            recommendations += (
                "⚪ KHÔNG CÓ RỦI RO - Có thể tiếp tục bình thường:\n"
                "• Áp dụng quy trình due diligence thông thường\n"
                "• Không cần biện pháp đặc biệt\n"
                "• Theo dõi cập nhật định kỳ theo quy định\n"
            )
        
        recommendations += (
            "\n⚠️  LƯU Ý: Đánh giá này dựa trên thông tin hiện có và có thể thay đổi khi có cập nhật mới.\n"
            "Luôn tham khảo ý kiến chuyên gia pháp lý khi cần thiết.\n"
        )
        
        return recommendations

    def interactive_mode(self):
        """
        Run interactive mode for testing the agent
        """
        print("🤖 AGENT PHÂN TÍCH RỦI RO CÁ NHÂN")
        print("=" * 50)
        print("Nhập truy vấn tiếng Việt để tìm kiếm thông tin về một người")
        print("Ví dụ: 'cho tôi thông tin về Trương Mỹ Lan'")
        print("Nhập 'quit' để thoát")
        print("=" * 50)
        
        while True:
            try:
                query = input("\n💬 Truy vấn: ").strip()
                
                if query.lower() in ['quit', 'exit', 'thoát']:
                    print("👋 Tạm biệt!")
                    break
                
                if not query:
                    print("⚠️ Vui lòng nhập truy vấn hợp lệ")
                    continue
                
                print("\n🔄 Đang xử lý...")
                response = self.process_query(query)
                print("\n" + "="*80)
                print(response)
                print("="*80)
                
            except KeyboardInterrupt:
                print("\n👋 Tạm biệt!")
                break
            except Exception as e:
                print(f"❌ Lỗi: {e}")

def main():
    """Main function for command line usage"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Person Risk Analysis Agent')
    parser.add_argument('--region', help='AWS region')
    parser.add_argument('--query', help='Vietnamese query about a person')
    parser.add_argument('--interactive', action='store_true', help='Run in interactive mode')
    parser.add_argument('--output-json', help='Save detailed result to JSON file')
    
    args = parser.parse_args()
    
    try:
        # Initialize agent
        agent = PersonRiskAgent(region_name=args.region)
        
        if args.interactive:
            # Run interactive mode
            agent.interactive_mode()
        elif args.query:
            # Process single query
            print(f"🔍 Xử lý truy vấn: {args.query}")
            response = agent.process_query(args.query)
            print("\n" + "="*80)
            print(response)
            print("="*80)
            
            # Save detailed result if requested
            if args.output_json:
                person_name = agent.extract_person_name_from_query(args.query)
                if person_name:
                    lookup_result = agent.person_lookup.lookup_person_comprehensive(person_name)
                    risk_analysis = agent.calculate_risk_score(lookup_result)
                    
                    with open(args.output_json, 'w', encoding='utf-8') as f:
                        json.dump(risk_analysis, f, ensure_ascii=False, indent=2, default=str)
                    print(f"\n📄 Kết quả chi tiết đã lưu vào: {args.output_json}")
        else:
            print("❌ Vui lòng cung cấp --query hoặc sử dụng --interactive")
            print("Ví dụ: python person_risk_agent.py --query 'cho tôi thông tin về Trương Mỹ Lan'")
    
    except Exception as e:
        print(f"❌ Lỗi khởi tạo agent: {e}")
        import traceback
        print(f"Chi tiết: {traceback.format_exc()}")

if __name__ == "__main__":
    main() 