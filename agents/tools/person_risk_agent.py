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
from typing import Dict, Any, Optional

# Add parent directory to path to import modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from agents.tools.person_lookup_dynamodb import PersonLookupDynamoDB
from agents.tools.risk_analyzer import RiskAnalyzer
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
        
        # Initialize Risk Analyzer
        self.risk_analyzer = RiskAnalyzer()
        
        # Initialize AML Model Inference
        try:
            self.aml_model = AMLModelInference()
            self.model_enabled = True
            print("✅ AML Model đã được tải thành công!")
        except Exception as e:
            print(f"⚠️ Không thể tải AML Model: {e}")
            print("📝 Sẽ chỉ sử dụng phân tích dựa trên quy tắc")
            self.aml_model = None
            self.model_enabled = False
        
        # Initialize LLM for advanced query processing
        try:
            self.bedrock_manager = BedrockModelManager(
                aws_access_key_id=aws_access_key_id or Utils.load_api_key_from_env("AWS_ACCESS_KEY"),
                aws_secret_access_key=aws_secret_access_key or Utils.load_api_key_from_env("AWS_SECRET_KEY"),
                region_name=region_name or "ap-southeast-1",
                default_model_id="anthropic.claude-3-haiku-20240307-v1:0"
            )
            self.llm_enabled = True
        except Exception as e:
            print(f"⚠️ Không thể khởi tạo LLM: {e}")
            print("📝 Sẽ sử dụng regex để trích xuất tên người")
            self.bedrock_manager = None
            self.llm_enabled = False
        
        print("✅ Agent đã sẵn sàng!")

    def extract_person_name_from_query(self, query: str) -> Optional[str]:
        print(f"🔍 Trích xuất tên từ query: {query}")
        if self.llm_enabled:
            print("🧠 Regex không thành công, đang thử LLM...")
            extracted_name = self.extract_person_name_with_llm(query)
            if extracted_name:
                print(f"✅ LLM đã trích xuất được: {extracted_name}")
                return extracted_name
            else:
                print("❌ LLM cũng không trích xuất được tên")
        
        print("❌ Không thể trích xuất tên người từ query")
        return None

    def _extract_name_with_regex(self, query: str) -> Optional[str]:
        """
        Extract person name using regex patterns (original implementation)
        
        Args:
            query: Vietnamese query string
            
        Returns:
            Extracted person name or None
        """
        # Common patterns in Vietnamese queries
        patterns = [
            r"thông tin về\s+(.+?)(?:\s|$)",
            r"tìm kiếm\s+(.+?)(?:\s|$)",  
            r"(?:bà|ông|anh|chị)\s+([^,\.]+)",
            r"(.+?)\s+có",
            r"(.+?)\s+là",
            r"(.+?)(?:\s+của|\s+ở|\s+tại|$)"
        ]
        
        query_lower = query.lower().strip()
        
        # Remove common question words
        query_clean = re.sub(r'\b(cho tôi|hãy|xin|làm ơn|vui lòng|giúp tôi|tìm|kiếm|thông tin|về|của|có|là|gì|như thế nào|ra sao)\b', '', query_lower)
        query_clean = query_clean.strip()
        
        # Try to match patterns
        for pattern in patterns:
            match = re.search(pattern, query_lower)
            if match:
                name = match.group(1).strip()
                # Clean up the name
                name = re.sub(r'\b(có|là|gì|như thế nào|ra sao|của|ở|tại)\b.*', '', name).strip()
                if len(name) > 2 and len(name) < 50:  # Reasonable name length
                    return name.title()  # Capitalize properly
        
        # If no pattern matches, try to extract proper nouns (capitalized words)
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
                temperature=0.1,
                max_token=100
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
        Convert person lookup result to AML model input format
        
        Args:
            lookup_result: Result from person lookup
            
        Returns:
            Dictionary formatted for AML model input
        """
        model_input = {
            # Initialize all fields with default values
            "residence_area": "Unknown",
            "occupation": "Unknown", 
            "age": 35,  # Default age
            "per_role": "Unknown",
            # Personal violation fields (1-5)
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
            # Organization violation fields (1-5)
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
            # Extract personal information
            if "personal_info" in lookup_result:
                personal_info = lookup_result["personal_info"]
                if personal_info:
                    # Try to extract residence area from address or other fields
                    if "address" in personal_info:
                        model_input["residence_area"] = personal_info["address"]
                    elif "location" in personal_info:
                        model_input["residence_area"] = personal_info["location"]
                    
                    # Try to extract occupation
                    if "occupation" in personal_info:
                        model_input["occupation"] = personal_info["occupation"]
                    elif "job" in personal_info:
                        model_input["occupation"] = personal_info["job"]
                    elif "position" in personal_info:
                        model_input["occupation"] = personal_info["position"]
                    
                    # Try to extract age from birth year or other fields
                    if "age" in personal_info:
                        model_input["age"] = int(personal_info["age"])
                    elif "birth_year" in personal_info:
                        try:
                            birth_year = int(personal_info["birth_year"])
                            current_year = 2024  # or use datetime.now().year
                            model_input["age"] = current_year - birth_year
                        except:
                            pass
            
            # Extract violation information from adverse media
            violation_count = 0
            org_violation_count = 0
            
            if "adverse_media" in lookup_result:
                adverse_media = lookup_result["adverse_media"]
                if isinstance(adverse_media, list):
                    for media in adverse_media:
                        if violation_count >= 5:  # Max 5 violations
                            break
                            
                        # Extract violation type and legal status
                        violation_type = self._map_violation_type(media)
                        legal_status = self._map_legal_status(media)
                        role = self._map_person_role(media)
                        
                        if violation_type != "None":
                            violation_count += 1
                            model_input[f"per_violation_type_{violation_count}"] = violation_type
                            model_input[f"per_legal_status_{violation_count}"] = legal_status
                            
                            # Set role for first violation
                            if violation_count == 1 and role != "Unknown":
                                model_input["per_role"] = role
            
            # Extract organization violations (if any organization info is available)
            if "organization_info" in lookup_result:
                org_info = lookup_result["organization_info"]
                if isinstance(org_info, list):
                    for org in org_info:
                        if org_violation_count >= 5:  # Max 5 org violations
                            break
                            
                        org_violation_type = self._map_org_violation_type(org)
                        org_legal_status = self._map_org_legal_status(org)
                        
                        if org_violation_type != "None":
                            org_violation_count += 1
                            model_input[f"org_violation_type_{org_violation_count}"] = org_violation_type
                            model_input[f"org_legal_status_{org_violation_count}"] = org_legal_status
            
        except Exception as e:
            print(f"⚠️ Lỗi khi chuyển đổi dữ liệu cho model: {e}")
        
        return model_input
    
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
        
        return "None"
    
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
        
        return "None"
    
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
        
        return "Unknown"
    
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
        
        return "None"
    
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
        
        return "None"

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
            lookup_result = self.person_lookup.lookup_person_comprehensive(person_name)
            
            # Analyze risk characteristics
            risk_analysis = self.risk_analyzer.analyze_person_lookup_result(lookup_result)
            
            # Add ML model prediction if available
            ml_prediction = None
            if self.model_enabled and self.aml_model:
                try:
                    print("🤖 Đang thực hiện dự đoán ML...")
                    model_input = self.convert_lookup_to_model_input(lookup_result)
                    
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
            if "error" in risk_analysis:
                response = f"❌ Không tìm thấy thông tin về '{person_name}' trong hệ thống.\n\n"
                
                if risk_analysis.get("suggestions"):
                    response += "💡 Có thể bạn đang tìm:\n"
                    for suggestion in risk_analysis["suggestions"]:
                        response += f"• {suggestion}\n"
                    response += "\nVui lòng thử lại với tên chính xác."
                else:
                    response += "Vui lòng kiểm tra lại tên người hoặc thử với các biến thể khác của tên."
                
                return response
            
            # Generate comprehensive Vietnamese response
            response = self.generate_vietnamese_response(person_name, risk_analysis)
            return response
            
        except Exception as e:
            print(f"❌ Lỗi khi xử lý truy vấn: {e}")
            return (
                f"❌ Đã xảy ra lỗi khi tìm kiếm thông tin về '{person_name}'.\n\n"
                f"Chi tiết lỗi: {str(e)}\n\n"
                "Vui lòng thử lại sau hoặc liên hệ quản trị viên."
            )

    def generate_vietnamese_response(self, person_name: str, risk_analysis: Dict[str, Any]) -> str:
        """
        Generate comprehensive Vietnamese response based on risk analysis
        
        Args:
            person_name: Person name that was queried
            risk_analysis: Risk analysis result
            
        Returns:
            Formatted Vietnamese response
        """
        # Format the risk analysis using the analyzer's Vietnamese formatter
        formatted_analysis = self.risk_analyzer.format_risk_analysis_vietnamese(risk_analysis)
        
        # Add introduction
        intro = f"Đây là thông tin về {person_name} mà hệ thống tìm được:\n\n"
        
        # Add ML prediction section if available
        ml_section = ""
        if "ml_prediction" in risk_analysis:
            ml_pred = risk_analysis["ml_prediction"]
            ml_section = (
                f"\n🤖 DỰ ĐOÁN MACHINE LEARNING:\n"
                f"{'='*50}\n"
                f"🎯 Mức độ rủi ro dự đoán: {ml_pred['prediction']} - {ml_pred['risk_level']}\n\n"
                f"📊 Xác suất cho từng mức độ rủi ro:\n"
            )
            
            # Add probability breakdown
            for class_name, prob in ml_pred["probabilities"].items():
                percentage = prob * 100
                bar_length = int(percentage / 5)  # Scale for visualization
                bar = "█" * bar_length + "░" * (20 - bar_length)
                ml_section += f"  {class_name}: {percentage:5.1f}% {bar}\n"
            
            ml_section += (
                f"\n🔧 Dữ liệu đầu vào cho model:\n"
                f"  • Khu vực cư trú: {ml_pred['model_input']['residence_area']}\n"
                f"  • Nghề nghiệp: {ml_pred['model_input']['occupation']}\n"
                f"  • Tuổi: {ml_pred['model_input']['age']}\n"
                f"  • Vai trò: {ml_pred['model_input']['per_role']}\n"
            )
            
            # Show violations found
            violations_found = []
            for i in range(1, 6):
                violation_type = ml_pred['model_input'].get(f'per_violation_type_{i}', 'None')
                legal_status = ml_pred['model_input'].get(f'per_legal_status_{i}', 'None')
                if violation_type != 'None':
                    violations_found.append(f"Vi phạm {i}: {violation_type} ({legal_status})")
            
            if violations_found:
                ml_section += "  • Vi phạm cá nhân:\n"
                for violation in violations_found:
                    ml_section += f"    - {violation}\n"
            
            # Show org violations found
            org_violations_found = []
            for i in range(1, 6):
                org_violation_type = ml_pred['model_input'].get(f'org_violation_type_{i}', 'None')
                org_legal_status = ml_pred['model_input'].get(f'org_legal_status_{i}', 'None')
                if org_violation_type != 'None':
                    org_violations_found.append(f"Vi phạm tổ chức {i}: {org_violation_type} ({org_legal_status})")
            
            if org_violations_found:
                ml_section += "  • Vi phạm tổ chức:\n"
                for org_violation in org_violations_found:
                    ml_section += f"    - {org_violation}\n"
            
            ml_section += "\n"
        
        # Add analysis explanation
        analysis_intro = (
            "\n🔍 PHÂN TÍCH ĐẶC TRƯNG RỦI RO (QUY TẮC):\n"
            "Hệ thống đã phân tích các đặc trưng sau theo quy tắc chấm điểm:\n"
            "1️⃣ Loại hình vi phạm (violation_type)\n"
            "2️⃣ Vai trò trong vụ việc (customer_role)\n"
            "3️⃣ Tình trạng pháp lý (legal_status)\n"
            "4️⃣ Độ tin cậy của nguồn (source_level)\n\n"
        )
        
        # Combine all parts
        full_response = intro + formatted_analysis + ml_section + analysis_intro
        
        # Add recommendations based on risk level
        overall_metrics = risk_analysis.get("overall_risk_metrics", {})
        risk_level = overall_metrics.get("overall_risk_level", "Không xác định")
        max_score = overall_metrics.get("max_risk_score", 0)
        
        # Consider ML prediction for recommendations if available
        ml_score = 0
        if "ml_prediction" in risk_analysis:
            ml_score = risk_analysis["ml_prediction"]["prediction"]
            # Use the higher score between rule-based and ML for recommendations
            max_score = max(max_score, ml_score * 2.5)  # Scale ML score (0-4) to match rule score scale
        
        recommendations = self.generate_recommendations(risk_level, max_score, risk_analysis.get("ml_prediction"))
        full_response += recommendations
        
        return full_response

    def generate_recommendations(self, risk_level: str, max_score: int, ml_prediction: Optional[Dict[str, Any]] = None) -> str:
        """
        Generate recommendations based on risk level
        
        Args:
            risk_level: Overall risk level
            max_score: Maximum risk score found
            
        Returns:
            Vietnamese recommendations text
        """
        recommendations = "\n💼 KHUYẾN NGHỊ:\n"
        
        # Add ML prediction context if available
        if ml_prediction:
            ml_risk_level = ml_prediction["risk_level"]
            ml_score = ml_prediction["prediction"]
            recommendations += f"🤖 Dự đoán AI: {ml_risk_level} (Điểm: {ml_score}/4)\n"
            recommendations += f"📊 Quy tắc: {risk_level} (Điểm tối đa: {max_score})\n\n"
        
        if max_score >= 10:
            recommendations += (
                "🔴 RỦI RO RẤT CAO - Cần thực hiện các biện pháp sau:\n"
                "• Từ chối giao dịch hoặc ngưng hợp tác ngay lập tức\n"
                "• Báo cáo lên cấp quản lý cao nhất\n"
                "• Xem xét báo cáo lên cơ quan chức năng\n"
                "• Thực hiện due diligence mở rộng nếu cần thiết\n"
                "• Lưu trữ tài liệu đầy đủ để đối phó với kiểm toán\n"
            )
        elif max_score >= 7:
            recommendations += (
                "🟠 RỦI RO CAO - Thực hiện giám sát chặt chẽ:\n"
                "• Áp dụng các biện pháp due diligence nâng cao\n"
                "• Thực hiện giám sát giao dịch liên tục\n"
                "• Yêu cầu tài liệu bổ sung và xác minh\n"
                "• Xin phê duyệt từ cấp quản lý trước khi tiếp tục\n"
                "• Rà soát định kỳ ít nhất 3 tháng/lần\n"
            )
        elif max_score >= 4:
            recommendations += (
                "🟡 RỦI RO TRUNG BÌNH - Thực hiện các biện pháp phòng ngừa:\n"
                "• Thực hiện due diligence chuẩn\n"
                "• Giám sát giao dịch bất thường\n"
                "• Rà soát định kỳ 6 tháng/lần\n"
                "• Lưu trữ hồ sơ theo quy định\n"
                "• Theo dõi cập nhật thông tin mới\n"
            )
        elif max_score >= 1:
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
                    risk_analysis = agent.risk_analyzer.analyze_person_lookup_result(lookup_result)
                    
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