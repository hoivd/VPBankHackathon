#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Risk Analyzer Module
Analyzes characteristics and calculates risk scores based on predefined rules
"""
from typing import Dict, List, Any, Union
import re

class RiskAnalyzer:
    """
    Analyzes risk characteristics based on person lookup data
    """
    
    def __init__(self):
        """Initialize the risk analyzer with scoring rules"""
        
        # Violation Type Scoring Rules
        self.violation_type_scores = {
            # Individual violations
            "rửa tiền": 6,
            "tài trợ khủng bố": 6,
            "lừa đảo": 4,
            "chiếm đoạt tài sản": 4,
            "tham nhũng": 4,
            "hối lộ": 4,
            "tham ô tài sản": 4,
            "vi phạm dân sự": 2,
            "hành chính": 2,
            "tranh chấp nhỏ": 2,
            
            # Organization violations
            "đưa vào danh sách trừng phạt": 5,
            "cấm vận kinh tế tài chính": 5,
            "trừng phạt ngành lĩnh vực": 4,
            "hạn chế truy cập vào hệ thống tài chính hoa kỳ": 4,
            "trừng phạt thứ cấp": 3,
            
            # No violation
            "không có hành vi phạm được đề cập": 0
        }
        
        # Customer Role Scoring Rules
        self.customer_role_scores = {
            "chủ mưu": 3,
            "cầm đầu": 3,
            "tổ chức thực hiện hành vi vi phạm": 3,
            "tham gia": 2,
            "đồng phạm": 2,
            "giúp sức": 2,
            "thực hiện một phần": 2,
            "bên liên quan bị động": 1,
            "bị nhắc tên nhưng không trực tiếp": 1,
            "không có liên quan rõ ràng trong bài báo": 0
        }
        
        # Legal Status Scoring Rules
        self.legal_status_scores = {
            "đã kết án": 3,
            "đang trong quá trình điều tra": 2,
            "truy tố": 2,
            "chưa có phán quyết": 2,
            "tin chưa rõ ràng": 1,
            "được minh oan": 0  # Special case: resets violation_type and customer_role to 0
        }
        
        # Source Level Scoring Rules
        self.source_level_scores = {
            "tuổi trẻ": 1,
            "dân trí": 1,
            "thanh niên": 1,
            "vnexpress": 1,
            "cổng thông tin chính phủ": 1,
            "other": 0,
            "high": 1,
            "medium": 0,
            "low": 0
        }

    def normalize_text(self, text: str) -> str:
        """Normalize Vietnamese text for comparison"""
        if not text:
            return ""
        return text.lower().strip()

    def score_violation_type(self, violation_type: str) -> int:
        """Score violation type based on predefined rules"""
        if not violation_type:
            return 0
        
        normalized = self.normalize_text(violation_type)
        
        # Check for direct matches
        for key, score in self.violation_type_scores.items():
            if key in normalized:
                return score
        
        # Special case: check for multiple violations in one string
        total_score = 0
        for key, score in self.violation_type_scores.items():
            if key in normalized and key != "không có hành vi phạm được đề cập":
                total_score = max(total_score, score)  # Take highest score
        
        return total_score

    def score_customer_role(self, customer_role: str) -> int:
        """Score customer role based on predefined rules"""
        if not customer_role:
            return 0
        
        normalized = self.normalize_text(customer_role)
        
        # Check for direct matches
        for key, score in self.customer_role_scores.items():
            if key in normalized:
                return score
        
        return 0

    def score_legal_status(self, legal_status: str) -> int:
        """Score legal status based on predefined rules"""
        if not legal_status:
            return 0
        
        normalized = self.normalize_text(legal_status)
        
        # Check for direct matches
        for key, score in self.legal_status_scores.items():
            if key in normalized:
                return score
        
        return 0

    def score_source_level(self, source_level: str, source_credibility: str = None) -> int:
        """Score source level/credibility based on predefined rules"""
        # Check source_level first
        if source_level:
            normalized = self.normalize_text(source_level)
            for key, score in self.source_level_scores.items():
                if key in normalized:
                    return score
        
        # Fallback to source_credibility
        if source_credibility:
            normalized = self.normalize_text(source_credibility)
            for key, score in self.source_level_scores.items():
                if key in normalized:
                    return score
        
        return 0

    def analyze_entry(self, entry: Dict[str, Any], media_details: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Analyze a single entry (personal2media or org2media) and calculate risk scores
        
        Args:
            entry: Entry data dictionary
            media_details: Additional media details for source credibility
            
        Returns:
            Dictionary with scores and analysis
        """
        # Get scores for each characteristic
        violation_score = self.score_violation_type(entry.get('violation_type', ''))
        role_score = self.score_customer_role(entry.get('customer_role', ''))
        legal_score = self.score_legal_status(entry.get('legal_status', ''))
        
        # Get source credibility from media details if available
        source_credibility = None
        if media_details:
            source_credibility = media_details.get('source_credibility')
        
        source_score = self.score_source_level(entry.get('source_level', ''), source_credibility)
        
        # Special case: if legal status is "được minh oan", reset violation and role scores to 0
        if "được minh oan" in self.normalize_text(entry.get('legal_status', '')):
            violation_score = 0
            role_score = 0
        
        # Calculate total risk score
        total_score = violation_score + role_score + legal_score + source_score
        
        # Risk level categorization
        if total_score >= 10:
            risk_level = "Rất Cao"
        elif total_score >= 7:
            risk_level = "Cao"
        elif total_score >= 4:
            risk_level = "Trung Bình"
        elif total_score >= 1:
            risk_level = "Thấp"
        else:
            risk_level = "Không Có Rủi Ro"
        
        return {
            "violation_type_score": violation_score,
            "customer_role_score": role_score,
            "legal_status_score": legal_score,
            "source_level_score": source_score,
            "total_risk_score": total_score,
            "risk_level": risk_level,
            "characteristics": {
                "violation_type": entry.get('violation_type', ''),
                "customer_role": entry.get('customer_role', ''),
                "legal_status": entry.get('legal_status', ''),
                "source_level": entry.get('source_level', ''),
                "source_credibility": source_credibility
            }
        }

    def analyze_person_lookup_result(self, lookup_result: Dict[str, Any]) -> Dict[str, Any]:
        """
        Analyze complete person lookup result with risk assessment
        
        Args:
            lookup_result: Result from PersonLookup.lookup_person_comprehensive
            
        Returns:
            Dictionary with comprehensive risk analysis
        """
        if "error" in lookup_result:
            return lookup_result
        
        person_info = lookup_result.get("person_info", {})
        personal2media_info = lookup_result.get("personal2media_info", [])
        org2media_info = lookup_result.get("org2media_info", [])
        media_details = lookup_result.get("media_details", {})
        
        # Analyze personal2media entries
        personal_risk_analysis = []
        for entry in personal2media_info:
            media_id = entry.get('media_id')
            media_detail = media_details.get(media_id, {}) if media_id else {}
            analysis = self.analyze_entry(entry, media_detail)
            analysis["entry_id"] = entry.get('p2m_id')
            analysis["entry_type"] = "personal2media"
            personal_risk_analysis.append(analysis)
        
        # Analyze org2media entries
        org_risk_analysis = []
        for entry in org2media_info:
            media_id = entry.get('media_id')
            media_detail = media_details.get(media_id, {}) if media_id else {}
            analysis = self.analyze_entry(entry, media_detail)
            analysis["entry_id"] = entry.get('o2m_id')
            analysis["entry_type"] = "org2media"
            analysis["organization_name"] = entry.get('organization_name')
            org_risk_analysis.append(analysis)
        
        # Calculate overall risk metrics
        all_scores = [a["total_risk_score"] for a in personal_risk_analysis + org_risk_analysis]
        max_risk_score = max(all_scores) if all_scores else 0
        avg_risk_score = sum(all_scores) / len(all_scores) if all_scores else 0
        
        # Determine overall risk level
        if max_risk_score >= 10:
            overall_risk_level = "Rất Cao"
        elif max_risk_score >= 7:
            overall_risk_level = "Cao"
        elif max_risk_score >= 4:
            overall_risk_level = "Trung Bình"
        elif max_risk_score >= 1:
            overall_risk_level = "Thấp"
        else:
            overall_risk_level = "Không Có Rủi Ro"
        
        return {
            "person_info": person_info,
            "personal_risk_analysis": personal_risk_analysis,
            "org_risk_analysis": org_risk_analysis,
            "overall_risk_metrics": {
                "max_risk_score": max_risk_score,
                "average_risk_score": round(avg_risk_score, 2),
                "overall_risk_level": overall_risk_level,
                "total_entries_analyzed": len(personal_risk_analysis) + len(org_risk_analysis),
                "high_risk_entries": len([a for a in personal_risk_analysis + org_risk_analysis if a["total_risk_score"] >= 7])
            },
            "original_lookup_result": lookup_result
        }

    def format_risk_analysis_vietnamese(self, risk_analysis: Dict[str, Any]) -> str:
        """
        Format the risk analysis result in Vietnamese
        
        Args:
            risk_analysis: Result from analyze_person_lookup_result
            
        Returns:
            Formatted Vietnamese text
        """
        if "error" in risk_analysis:
            return f"❌ Lỗi: {risk_analysis['error']}"
        
        person_info = risk_analysis["person_info"]
        personal_analysis = risk_analysis["personal_risk_analysis"]
        org_analysis = risk_analysis["org_risk_analysis"]
        overall_metrics = risk_analysis["overall_risk_metrics"]
        
        # Header
        result = f"📊 PHÂN TÍCH RỦI RO CHO: {person_info.get('full_name', 'N/A')}\n"
        result += "=" * 80 + "\n\n"
        
        # Person Info
        result += "👤 THÔNG TIN CÁ NHÂN:\n"
        result += f"• Họ tên: {person_info.get('full_name', 'N/A')}\n"
        result += f"• Giới tính: {person_info.get('gender', 'N/A')}\n"
        result += f"• Chức vụ: {person_info.get('occupation_or_position', 'N/A')}\n"
        result += f"• Tổ chức: {person_info.get('organization', 'N/A')}\n\n"
        
        # Overall Risk
        result += "🚨 ĐÁNH GIÁ RỦI RO TỔNG THỂ:\n"
        result += f"• Mức độ rủi ro: {overall_metrics['overall_risk_level']}\n"
        result += f"• Điểm rủi ro cao nhất: {overall_metrics['max_risk_score']}/15\n"
        result += f"• Điểm rủi ro trung bình: {overall_metrics['average_risk_score']}/15\n"
        result += f"• Tổng số mục phân tích: {overall_metrics['total_entries_analyzed']}\n"
        result += f"• Số mục có rủi ro cao: {overall_metrics['high_risk_entries']}\n\n"
        
        # Personal2Media Analysis
        if personal_analysis:
            result += "📋 PHÂN TÍCH RỦI RO CÁ NHÂN:\n"
            for i, analysis in enumerate(personal_analysis, 1):
                result += f"\n{i}. Mục {analysis['entry_id']}:\n"
                result += f"   • Loại vi phạm: {analysis['characteristics']['violation_type']} (Điểm: {analysis['violation_type_score']})\n"
                result += f"   • Vai trò: {analysis['characteristics']['customer_role']} (Điểm: {analysis['customer_role_score']})\n"
                result += f"   • Tình trạng pháp lý: {analysis['characteristics']['legal_status']} (Điểm: {analysis['legal_status_score']})\n"
                result += f"   • Mức độ nguồn: {analysis['characteristics']['source_level']} (Điểm: {analysis['source_level_score']})\n"
                result += f"   • 🎯 TỔNG ĐIỂM RỦI RO: {analysis['total_risk_score']}/15 - {analysis['risk_level']}\n"
        
        # Org2Media Analysis
        if org_analysis:
            result += "\n🏢 PHÂN TÍCH RỦI RO TỔ CHỨC:\n"
            for i, analysis in enumerate(org_analysis, 1):
                result += f"\n{i}. Tổ chức: {analysis.get('organization_name', 'N/A')} (ID: {analysis['entry_id']}):\n"
                result += f"   • Loại vi phạm: {analysis['characteristics']['violation_type']} (Điểm: {analysis['violation_type_score']})\n"
                result += f"   • Vai trò: {analysis['characteristics']['customer_role']} (Điểm: {analysis['customer_role_score']})\n"
                result += f"   • Tình trạng pháp lý: {analysis['characteristics']['legal_status']} (Điểm: {analysis['legal_status_score']})\n"
                result += f"   • Mức độ nguồn: {analysis['characteristics']['source_level']} (Điểm: {analysis['source_level_score']})\n"
                result += f"   • 🎯 TỔNG ĐIỂM RỦI RO: {analysis['total_risk_score']}/15 - {analysis['risk_level']}\n"
        
        # Risk Level Legend
        result += "\n📖 THANG ĐIỂM RỦI RO:\n"
        result += "• 10-15 điểm: Rất Cao 🔴\n"
        result += "• 7-9 điểm: Cao 🟠\n"
        result += "• 4-6 điểm: Trung Bình 🟡\n"
        result += "• 1-3 điểm: Thấp 🟢\n"
        result += "• 0 điểm: Không Có Rủi Ro ⚪\n"
        
        return result 