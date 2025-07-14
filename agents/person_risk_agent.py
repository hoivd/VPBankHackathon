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

from agents.person_lookup_dynamodb import PersonLookupDynamoDB
from agents.risk_analyzer import RiskAnalyzer
from llm_model.bedrock_manager import BedrockModelManager
from utils import Utils

class PersonRiskAgent:
    """
    Vietnamese-language agent for person risk analysis using DynamoDB lookup and characteristic scoring
    """
    
    def __init__(self, region_name: str = None, aws_access_key_id: str = None, aws_secret_access_key: str = None):
        """
        Initialize the Person Risk Agent
        
        Args:
            region_name: AWS region (default from config)
            aws_access_key_id: AWS access key (optional)
            aws_secret_access_key: AWS secret key (optional)
        """
        print("🤖 Khởi tạo Agent Phân Tích Rủi Ro Cá Nhân...")
        
        # Initialize PersonLookup for DynamoDB
        self.person_lookup = PersonLookupDynamoDB(
            region_name=region_name,
            aws_access_key_id=aws_access_key_id,
            aws_secret_access_key=aws_secret_access_key
        )
        
        # Initialize Risk Analyzer
        self.risk_analyzer = RiskAnalyzer()
        
        # Initialize LLM for advanced query processing
        try:
            self.bedrock_manager = BedrockModelManager(
                aws_access_key_id=aws_access_key_id or Utils.load_api_key_from_env("AWS_ACCESS_KEY"),
                aws_secret_access_key=aws_secret_access_key or Utils.load_api_key_from_env("AWS_SECRET_KEY"),
                region_name=region_name or "ap-southeast-1",
                default_model_id="anthropic.claude-3-haiku-20240307-v1:0"
            )
            self.llm_enabled = True
            print("🧠 LLM (Bedrock) đã được khởi tạo thành công!")
        except Exception as e:
            print(f"⚠️ Không thể khởi tạo LLM: {e}")
            print("📝 Sẽ sử dụng regex để trích xuất tên người")
            self.bedrock_manager = None
            self.llm_enabled = False
        
        print("✅ Agent đã sẵn sàng!")

    def extract_person_name_from_query(self, query: str) -> Optional[str]:
        """
        Extract person name from Vietnamese query using regex patterns first, then LLM fallback
        
        Args:
            query: Vietnamese query string
            
        Returns:
            Extracted person name or None
        """
        print(f"🔍 Trích xuất tên từ query: {query}")
        
        # Method 1: Try regex patterns first (fast)
        # extracted_name = self._extract_name_with_regex(query)
        # if extracted_name:
        #     print(f"✅ Regex đã trích xuất được: {extracted_name}")
        #     return extracted_name
        
        # Method 2: Fallback to LLM for complex queries
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

    def process_query(self, query: str) -> str:
        """
        Process Vietnamese query and return comprehensive risk analysis
        
        Args:
            query: Vietnamese query about a person
            
        Returns:
            Formatted Vietnamese response with risk analysis
        """
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
        
        # Add analysis explanation
        analysis_intro = (
            "\n🔍 PHÂN TÍCH ĐẶC TRƯNG RỦI RO:\n"
            "Hệ thống đã phân tích các đặc trưng sau theo quy tắc chấm điểm:\n"
            "1️⃣ Loại hình vi phạm (violation_type)\n"
            "2️⃣ Vai trò trong vụ việc (customer_role)\n"
            "3️⃣ Tình trạng pháp lý (legal_status)\n"
            "4️⃣ Độ tin cậy của nguồn (source_level)\n\n"
        )
        
        # Combine all parts
        full_response = intro + formatted_analysis + analysis_intro
        
        # Add recommendations based on risk level
        overall_metrics = risk_analysis.get("overall_risk_metrics", {})
        risk_level = overall_metrics.get("overall_risk_level", "Không xác định")
        max_score = overall_metrics.get("max_risk_score", 0)
        
        recommendations = self.generate_recommendations(risk_level, max_score)
        full_response += recommendations
        
        return full_response

    def generate_recommendations(self, risk_level: str, max_score: int) -> str:
        """
        Generate recommendations based on risk level
        
        Args:
            risk_level: Overall risk level
            max_score: Maximum risk score found
            
        Returns:
            Vietnamese recommendations text
        """
        recommendations = "\n💼 KHUYẾN NGHỊ:\n"
        
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