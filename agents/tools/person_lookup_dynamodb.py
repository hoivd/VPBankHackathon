#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
DynamoDB Person Lookup Script
Connects to DynamoDB and performs relational queries to find:
1. personal2media info: legal_status, role_in_event, source_level, violation_type
2. org2media info (organizations the person is in): legal_status, media_id, o2m_id, org_id, role_in_event, source_level, violation_type
"""
import os
import sys
import json
import boto3
from boto3.dynamodb.conditions import Key, Attr
from botocore.exceptions import ClientError
from typing import Dict, List, Any, Optional
import dotenv
dotenv.load_dotenv()
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import TABLE_CONFIG_DEMO
from matching.llm_rerank_personal import LlmRerankerPersonal
from matching.personal_matching import PersonMatcherFAISS
from utils import Utils
from config import TABLE_CONFIG_DEMO
import config
import os
import numpy as np
from embedder.model_embedder import ModelEmbedder
from logger import _setup_logger
import config

from embedder.personal_embedder import PersonalEmbedder
from faiss_manager.faiss_searcher import FaissSearcher
from dynamodb.table_personal_embedd2personal import TablePersonalEmbedd2Personal
from dynamodb.dynamo_query import DynamoQuery
from dynamodb.base_dynamo import BaseDynamoDB
from dynamodb.table_personal_info import TablePersonalInfo
import json
from llm_model.bedrock_manager import BedrockModelManager
from pathlib import Path

class PersonLookupDynamoDB:
    def __init__(self, region_name: str = None, aws_access_key_id: str = None, aws_secret_access_key: str = None):
        """
        Initialize DynamoDB connection for person lookup
        
        Args:
            region_name: AWS region (default from config)
            aws_access_key_id: AWS access key (optional)
            aws_secret_access_key: AWS secret key (optional)
        """
        self.region_name = region_name or os.getenv("AWS_REGION", "ap-southeast-1")
        
        try:
            
            aws_access_key_id = 'AKIAQWLOPNIDXAC4BJWD'
            aws_secret_access_key = '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'
            self.dynamodb = boto3.resource(
                'dynamodb',
                region_name=self.region_name,
                aws_access_key_id=aws_access_key_id,
                aws_secret_access_key=aws_secret_access_key
            )
            self.client = boto3.client(
                'dynamodb',
                region_name=self.region_name,
                aws_access_key_id=aws_access_key_id,
                aws_secret_access_key=aws_secret_access_key
            )

            self.client.list_tables(Limit=1)
            print(f"Successfully connected to DynamoDB region: {self.region_name}")
            
        except Exception as e:
            print(f"Failed to connect to DynamoDB: {e}")
            raise
        personal_table_name, _ = list(TABLE_CONFIG_DEMO['person_config'].items())[0]
        p2m_table_name, _ = list(TABLE_CONFIG_DEMO['p2m_config'].items())[0]
        o2m_table_name, _ = list(TABLE_CONFIG_DEMO['o2m_config'].items())[0]
        org_table_name, _ = list(TABLE_CONFIG_DEMO['organization_config'].items())[0]
        media_table_name, _ = list(TABLE_CONFIG_DEMO['media_config'].items())[0]
        self.personal_info_table = self.dynamodb.Table(personal_table_name)
        self.personal2media_table = self.dynamodb.Table(p2m_table_name)
        self.org2media_table = self.dynamodb.Table(o2m_table_name)
        self.organization_info_table = self.dynamodb.Table(org_table_name)
        self.adverse_media_table = self.dynamodb.Table(media_table_name)
        
    def find_person_by_id(self, per_id: str) -> Optional[Dict]:
        try:
            response = self.personal_info_table.get_item(Key={'per_id': per_id})
            return response.get('Item')
        except Exception as e:
            print(f"❌ Error searching for person: {e}")
            return None
    def find_person_by_name(self, full_name: str) -> Optional[Dict]:
        try:
            response = self.personal_info_table.scan(
                FilterExpression=Attr('full_name').eq(full_name)
            )
            
            items = response.get('Items', [])
            if items:
                return items[0]
            
            response = self.personal_info_table.scan()
            all_items = response.get('Items', [])
            
            while 'LastEvaluatedKey' in response:
                response = self.personal_info_table.scan(
                    ExclusiveStartKey=response['LastEvaluatedKey']
                )
                all_items.extend(response.get('Items', []))
            
            for item in all_items:
                item_name = item.get('full_name', '')
                if item_name.lower() == full_name.lower():
                    return item
            
            for item in all_items:
                item_name = item.get('full_name', '')
                if full_name.lower() in item_name.lower() or item_name.lower() in full_name.lower():
                    return item
            
            return None
            
        except Exception as e:
            print(f"❌ Error searching for person: {e}")
            return None
        
    def find_person_id_by_query(self, query: str, personal_embedder, faiss_searcher) -> str:
        # os.chdir("..")
        # print(os.getcwd())

        # model_name = config.EMBEDDING_MODEL_NAME
        # faiss_index_path = 'data/faiss_index/personal_faiss_index'

        # # ==== Bước 2: Khởi tạo các thành phần chính ====
        # base_embedder = ModelEmbedder(model_name=model_name)
        # personal_embedder = PersonalEmbedder(base_embedder=base_embedder)
        # faiss_searcher = FaissSearcher(index_dir=faiss_index_path)

        # ==== DynamoDB ====
        AWS_ACCESS_KEY='AKIAQWLOPNIDXAC4BJWD'
        AWS_SECRET_KEY='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'
        NEW_AWS_ACCESS_KEY = Utils.load_api_key_from_env("NEW_AWS_ACCESS_KEY")
        NEW_AWS_SECRET_KEY = Utils.load_api_key_from_env("NEW_AWS_SECRET_KEY")

        REGION = config.AWS_REGION
        REGION_MODEL = config.AWS_VIRGINA_REGION
        DEFAULT_MODEL_ID = config.DEEPSEEK_MODEL_VIRGINA_ID

        print("DEFAULT_MODEL_ID:", DEFAULT_MODEL_ID)

        base_dynamo = BaseDynamoDB(region_name=REGION, access_key=AWS_ACCESS_KEY, secret_key=AWS_SECRET_KEY)
        dynamo_query = DynamoQuery(base_dynamo.dynamodb)

        personal_embedd_table = TablePersonalEmbedd2Personal(query=dynamo_query, table_config=config.TABLE_CONFIG_DEMO)
        personal_info_table = TablePersonalInfo(query=dynamo_query, table_config=config.TABLE_CONFIG_DEMO)

        llm_manager = BedrockModelManager(
            aws_access_key_id=NEW_AWS_ACCESS_KEY,
            aws_secret_access_key=NEW_AWS_SECRET_KEY,
            region_name=REGION_MODEL,
            default_model_id=DEFAULT_MODEL_ID
        )

        prompt_path = 'D:/VPBankHackathon/prompts/rerank_personal.txt'
        prompt_template = Utils.load_text(prompt_path)
        print(prompt_template)

        reranker = LlmRerankerPersonal(llm_manager=llm_manager, model_type="deepseek", prompt_template=prompt_template)


        # ==== Khởi tạo matcher với thông tin đầy đủ ====
        matcher = PersonMatcherFAISS(
            personal_embedder,
            faiss_searcher,
            personal_embedd_table,
            personal_info_table,
            reranker
        )

        # ==== Tìm kiếm ====
        results = matcher.match_full_info(query, top_k=10)

        print("✅ Kết quả khớp cá nhân đầy đủ:")
        for i, item in enumerate(results, 1):
            print(f"\n🔹 Kết quả #{i}")
            for k, v in item.items():
                print(f"{k}: {v}")

        print("✅ Đang đánh giá lại bằng LLM...")
        best_match = matcher.rerank_by_llm(query, results)

        print("🎯 Kết quả LLM đánh giá:")
        print("Per_id:", best_match)
        return best_match
    
    def get_personal2media_info(self, per_id: str) -> List[Dict]:
        """
        Get personal2media information for a person
        
        Args:
            per_id: Person ID
            
        Returns:
            List of personal2media documents with required fields
        """
        try:
            # Scan table filtering by per_id
            response = self.personal2media_table.scan(
                FilterExpression=Attr('per_id').eq(per_id)
            )
            
            items = response.get('Items', [])
            
            # Handle pagination if needed
            while 'LastEvaluatedKey' in response:
                response = self.personal2media_table.scan(
                    ExclusiveStartKey=response['LastEvaluatedKey'],
                    FilterExpression=Attr('per_id').eq(per_id)
                )
                items.extend(response.get('Items', []))
            
            # Filter and format the response
            result = []
            for item in items:
                filtered_item = {
                    "legal_status": item.get("legal_status"),
                    "role_in_event": item.get("role_in_event"),
                    "source_level": item.get("source_level"),
                    "violation_type": item.get("violation_type"),
                    "media_id": item.get("media_id"),
                    "p2m_id": item.get("p2m_id"),
                    "entity_name": item.get("entity_name"),
                    "customer_role": item.get("customer_role")
                }
                result.append(filtered_item)
            
            return result
            
        except Exception as e:
            print(f"❌ Error getting personal2media info: {e}")
            return []

    def get_org2media_info_for_person(self, full_name: str) -> List[Dict]:
        """
        Get org2media information for organizations the person is associated with
        
        Args:
            full_name: Full name of the person
            
        Returns:
            List of org2media documents with required fields
        """
        try:
            # First, find organizations where this person is mentioned in personal_relationships
            response = self.organization_info_table.scan()
            all_orgs = response.get('Items', [])
            
            # Handle pagination
            while 'LastEvaluatedKey' in response:
                response = self.organization_info_table.scan(
                    ExclusiveStartKey=response['LastEvaluatedKey']
                )
                all_orgs.extend(response.get('Items', []))
            
            related_orgs = []
            for org in all_orgs:
                personal_relationships = org.get("personal_relationships", "")
                if personal_relationships and full_name.lower() in personal_relationships.lower():
                    related_orgs.append(org)
            
            org2media_results = []
            
            for org in related_orgs:
                org_id = org.get("org_id")
                if org_id:
                    # Find org2media entries for this organization
                    response = self.org2media_table.scan(
                        FilterExpression=Attr('org_id').eq(org_id)
                    )
                    
                    org2media_items = response.get('Items', [])
                    
                    # Handle pagination
                    while 'LastEvaluatedKey' in response:
                        response = self.org2media_table.scan(
                            ExclusiveStartKey=response['LastEvaluatedKey'],
                            FilterExpression=Attr('org_id').eq(org_id)
                        )
                        org2media_items.extend(response.get('Items', []))
                    
                    # Add organization info to each org2media document
                    for item in org2media_items:
                        filtered_item = {
                            "legal_status": item.get("legal_status"),
                            "media_id": item.get("media_id"),
                            "o2m_id": item.get("o2m_id"),
                            "org_id": item.get("org_id"),
                            "role_in_event": item.get("role_in_event"),
                            "source_level": item.get("source_level"),
                            "violation_type": item.get("violation_type"),
                            "entity_name": item.get("entity_name"),
                            "customer_role": item.get("customer_role"),
                            "organization_name": org.get("full_name"),
                            "organization_type": org.get("occupation_or_position")
                        }
                        org2media_results.append(filtered_item)
            
            return org2media_results
            
        except Exception as e:
            print(f"❌ Error getting org2media info: {e}")
            return []

    def get_media_details(self, media_id: str) -> Optional[Dict]:
        """
        Get media details for a given media_id
        
        Args:
            media_id: Media ID
            
        Returns:
            Media document or None
        """
        try:
            response = self.adverse_media_table.get_item(
                Key={'media_id': media_id}
            )
            
            item = response.get('Item')
            if not item:
                return None
            
            # Filter and format the response
            media_doc = {
                "media_id": item.get("media_id"),
                "news_sentiment_type": item.get("news_sentiment_type"),
                "recency": item.get("recency"),
                "source_credibility": item.get("source_credibility"),
                "content": item.get("content")
            }
            
            # Truncate content for display
            if media_doc.get("content"):
                content = media_doc["content"]
                if len(content) > 200:
                    media_doc["content_preview"] = content[:200] + "..."
                else:
                    media_doc["content_preview"] = content
                del media_doc["content"]  # Remove full content to save space
            
            return media_doc
            
        except Exception as e:
            print(f"❌ Error getting media details: {e}")
            return None

    def lookup_person_comprehensive(self, per_id: str = None,full_name :str = None) -> Dict[str, Any]:
        """
        Comprehensive lookup for a person including all related information
        
        Args:
            full_name: Full name of the person
            
        Returns:
            Dictionary with all related information
        """
        print(f"🔍 Looking up information for: {per_id}")
        
        # 1. Find the person
        # person = self.find_person_by_name(full_name)
        if per_id is not None:
            person = self.find_person_by_id(per_id)
        else:
            person = self.find_person_by_name(full_name)
        full_name_from_db = person.get('full_name')
        full_name = full_name_from_db
        # if(full_name!=full_name_from_db):
        #     return {
        #         "error": f"Person '{full_name}' not found in personal_info table",
        #         "suggestions": self.get_similar_names(full_name)
        #     }
        if not person:
            return {
                "error": f"Person '{full_name}' not found in personal_info table",
                "suggestions": self.get_similar_names(full_name)
            }
        
        print(f"✅ Found person: {person.get('full_name')} (ID: {person.get('per_id')})")
        
        # 2. Get personal2media information
        personal2media_info = self.get_personal2media_info(person.get('per_id'))
        print(f"📋 Found {len(personal2media_info)} personal2media entries")
        
        # 3. Get org2media information
        org2media_info = self.get_org2media_info_for_person(full_name)
        print(f"🏢 Found {len(org2media_info)} org2media entries")
        
        # 4. Get media details for all media_ids
        all_media_ids = set()
        for p2m in personal2media_info:
            if p2m.get('media_id'):
                all_media_ids.add(p2m['media_id'])
        for o2m in org2media_info:
            if o2m.get('media_id'):
                all_media_ids.add(o2m['media_id'])
        
        media_details = {}
        for media_id in all_media_ids:
            media_details[media_id] = self.get_media_details(media_id)
        if person.get("birth_year_or_age") is not None:
            if int(person.get("birth_year_or_age"))>100:
                age = 2025 - int(person.get("birth_year_or_age"))
            else:
                age = person.get("birth_year_or_age")
        else:
            age = None
        result = {
            "person_info": {
                "per_id": person.get('per_id'),
                "full_name": person.get('full_name'),
                "age": age,
                "gender": person.get('gender'),
                "hometown_or_residence": person.get('hometown_or_residence'),
                "occupation_or_position": person.get('occupation_or_position'),
                "organization": person.get('organization'),
                "personal_relationships": person.get('personal_relationships')
            },
            "personal2media_info": personal2media_info,
            "org2media_info": org2media_info,
            "media_details": media_details,
            "summary": {
                "total_personal2media_entries": len(personal2media_info),
                "total_org2media_entries": len(org2media_info),
                "total_media_articles": len(media_details),
                "unique_media_ids": list(all_media_ids)
            }
        }
        
        return result
    
    def lookup_person_comprehensive_v2(self, full_name: str, query: str, personal_embedder, faiss_searcher) -> Dict[str, Any]:
        """
        Comprehensive lookup for a person with formatted output according to expected format
        
        Args:
            full_name: Full name of the person
            
        Returns:
            Dictionary with formatted information according to expected_result.txt
        """
        try:
            # Import the formatter functions
            import sys
            import os
            sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
            
            from agents.data_formatter import (
                get_most_frequent_violation_type,
                get_most_frequent_customer_role, 
                get_highest_legal_status,
                group_violations_by_media
            )
        except ImportError:
            # Fallback implementation if import fails
            from collections import Counter, defaultdict
            
            def get_most_frequent_violation_type(entries):
                violation_counts = Counter()
                for entry in entries:
                    violation_type = entry.get('violation_type', '')
                    if violation_type:
                        violations = violation_type.split('/')
                        for v in violations:
                            v_clean = v.strip()
                            if v_clean:
                                violation_counts[v_clean] += 1
                return violation_counts.most_common(1)[0][0] if violation_counts else "Không có hành vi phạm được đề cập"
            
            def get_most_frequent_customer_role(entries):
                role_counts = Counter()
                for entry in entries:
                    customer_role = entry.get('customer_role', '')
                    if customer_role:
                        role_counts[customer_role] += 1
                return role_counts.most_common(1)[0][0] if role_counts else "Không có liên quan rõ ràng trong bài báo"
            
            def get_highest_legal_status(entries):
                status_priority = {
                    "Đã kết án": 1,
                    "Đang trong quá trình điều tra": 2,
                    "Đang trong quá trình điều tra / truy tố / chưa có phán quyết": 2,
                    "Tin chưa rõ ràng": 3,
                    "Được minh oan": 4
                }
                statuses = [entry.get('legal_status', '') for entry in entries]
                for status in statuses:
                    if status == "Đã kết án":
                        return status
                valid_statuses = [s for s in statuses if s in status_priority]
                if valid_statuses:
                    return min(valid_statuses, key=lambda x: status_priority[x])
                return "Tin chưa rõ ràng"
            
            def group_violations_by_media(entries):
                # Group by violation type first, then analyze
                violation_groups = defaultdict(list)
                
                # Group all entries by violation type
                for entry in entries:
                    violation_type = entry.get('violation_type', '')
                    if violation_type:
                        # Handle multiple violation types separated by '/'
                        violations = violation_type.split('/')
                        for v in violations:
                            v_clean = v.strip()
                            if v_clean:
                                violation_groups[v_clean].append(entry)
                
                violation_summary = {}
                for violation_type, violation_entries in violation_groups.items():
                    # Get the most frequent customer_role for this violation type
                    customer_role = get_most_frequent_customer_role(violation_entries)
                    # Get the highest priority legal status for this violation type
                    legal_status = get_highest_legal_status(violation_entries)
                    # Get all media_ids for this violation type
                    media_ids = list(set([entry.get('media_id', '') for entry in violation_entries if entry.get('media_id')]))
                    
                    violation_summary[violation_type] = {
                        'customer_role': customer_role,
                        'legal_status': legal_status,
                        'media_ids': media_ids
                    }
                
                return violation_summary
        
        print(f"🔍 Looking up formatted information for: {full_name}")

        if config.USE_MATCHING_METHOD:
            per_ids = self.find_person_id_by_query(query, personal_embedder, faiss_searcher)

            if len(per_ids) < 1:
                return {
                    "error": f"Person '{full_name}' not found in personal_info table",
                    "suggestions": self.get_similar_names(full_name)
                }
            
            per_id = per_ids[0]
            
        else:
            per_id = None

        # Get comprehensive data first
        comprehensive_data = self.lookup_person_comprehensive(per_id,full_name)
        
        if "error" in comprehensive_data:
            return comprehensive_data
        
        person_info = comprehensive_data.get('person_info', {})
        personal2media_info = comprehensive_data.get('personal2media_info', [])
        org2media_info = comprehensive_data.get('org2media_info', [])
        
        # Get entries for the main person only
        main_person_entries = [
            entry for entry in personal2media_info 
        ]
        
        # Create individual crime summary
        individual_crime_summary = {}
        if main_person_entries:
            violation_summary = group_violations_by_media(main_person_entries)
            individual_crime_summary[full_name] = violation_summary
        
        # Create organizational crime summary
        org_groups = defaultdict(list)
        for entry in org2media_info:
            org_name = entry.get('organization_name', '')
            if org_name:
                org_groups[org_name].append(entry)
        
        organizational_crime_summary = {}
        for org_name, org_entries in org_groups.items():
            violation_summary = group_violations_by_media(org_entries)
            organizational_crime_summary[org_name] = violation_summary
        
        # For personal_risk_analysis, return all individual entries with customer_role
        # This matches the format in formatted_lookup_result_v2.json
        
        # For organizer_risk_analysis, return all organization entries with customer_role
        # This matches the format in formatted_lookup_result_v2.json
        
        # Create final formatted result matching the expected format
        formatted_result = {
            "person_info": person_info,
            "invidual_AML": individual_crime_summary,
            "organization_AML": organizational_crime_summary,
            "personal_risk_analysis": personal2media_info,  # Return all detailed entries
            "organizer_risk_analysis": org2media_info       # Return all detailed entries
        }
        
        print(f"✅ Formatted result created for: {full_name}")
        print(f"📊 Individual crimes: {len(individual_crime_summary)}")
        print(f"🏢 Organizational crimes: {len(organizational_crime_summary)}")
        print(f"👤 Personal risks: {len(personal2media_info)}")
        print(f"🏛️ Organizer risks: {len(org2media_info)}")
        
        return formatted_result

    def get_similar_names(self, full_name: str, limit: int = 5) -> List[str]:
        """
        Get similar names for suggestions when exact match is not found
        
        Args:
            full_name: Full name to search for
            limit: Maximum number of suggestions
            
        Returns:
            List of similar names
        """
        try:
            # Scan the personal_info table for similar names
            response = self.personal_info_table.scan()
            all_items = response.get('Items', [])
            
            # Handle pagination
            while 'LastEvaluatedKey' in response:
                response = self.personal_info_table.scan(
                    ExclusiveStartKey=response['LastEvaluatedKey']
                )
                all_items.extend(response.get('Items', []))
            
            # Find names containing any part of the input name
            name_parts = full_name.split()
            similar_names = []
            
            for item in all_items:
                item_name = item.get('full_name', '')
                for part in name_parts:
                    if part.lower() in item_name.lower() and item_name not in similar_names:
                        similar_names.append(item_name)
                        break
                
                if len(similar_names) >= limit:
                    break
            
            return similar_names[:limit]
            
        except Exception as e:
            print(f"❌ Error getting similar names: {e}")
            return []

    def print_formatted_result(self, result: Dict[str, Any]):
        """
        Print the lookup result in a formatted way
        
        Args:
            result: Result dictionary from lookup_person_comprehensive
        """
        if "error" in result:
            print(f"\n❌ {result['error']}")
            if result.get("suggestions"):
                print("\n💡 Similar names found:")
                for name in result["suggestions"]:
                    print(f"   - {name}")
            return
        
        print("\n" + "="*80)
        print("👤 PERSON INFORMATION")
        print("="*80)
        person = result["person_info"]
        for key, value in person.items():
            if value:
                print(f"{key.replace('_', ' ').title()}: {value}")
        
        print("\n" + "="*80)
        print("📋 PERSONAL2MEDIA INFORMATION")
        print("="*80)
        for i, p2m in enumerate(result["personal2media_info"], 1):
            print(f"\n{i}. Entry ID: {p2m.get('p2m_id')}")
            print(f"   Legal Status: {p2m.get('legal_status')}")
            print(f"   Role in Event: {p2m.get('role_in_event')}")
            print(f"   Source Level: {p2m.get('source_level')}")
            print(f"   Violation Type: {p2m.get('violation_type')}")
            print(f"   Media ID: {p2m.get('media_id')}")
            print(f"   Customer Role: {p2m.get('customer_role')}")
        
        print("\n" + "="*80)
        print("🏢 ORG2MEDIA INFORMATION")
        print("="*80)
        for i, o2m in enumerate(result["org2media_info"], 1):
            print(f"\n{i}. Entry ID: {o2m.get('o2m_id')}")
            print(f"   Organization: {o2m.get('organization_name')} ({o2m.get('organization_type')})")
            print(f"   Legal Status: {o2m.get('legal_status')}")
            print(f"   Role in Event: {o2m.get('role_in_event')}")
            print(f"   Source Level: {o2m.get('source_level')}")
            print(f"   Violation Type: {o2m.get('violation_type')}")
            print(f"   Media ID: {o2m.get('media_id')}")
            print(f"   Org ID: {o2m.get('org_id')}")
        
        print("\n" + "="*80)
        print("📰 MEDIA DETAILS")
        print("="*80)
        for media_id, media in result["media_details"].items():
            if media:
                print(f"\nMedia ID: {media_id}")
                print(f"   Sentiment: {media.get('news_sentiment_type')}")
                print(f"   Recency: {media.get('recency')}")
                print(f"   Credibility: {media.get('source_credibility')}")
                print(f"   Content Preview: {media.get('content_preview')}")
        
        print("\n" + "="*80)
        print("📊 SUMMARY")
        print("="*80)
        summary = result["summary"]
        print(f"Total Personal2Media Entries: {summary['total_personal2media_entries']}")
        print(f"Total Org2Media Entries: {summary['total_org2media_entries']}")
        print(f"Total Media Articles: {summary['total_media_articles']}")
        print(f"Unique Media IDs: {', '.join(summary['unique_media_ids'])}")

def main():
    """Main function to run person lookup"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Lookup person information in DynamoDB')
    parser.add_argument('--region', help='AWS region (or set AWS_REGION env var)')
    parser.add_argument('--name', required=True, help='Full name of the person to lookup')
    parser.add_argument('--output-json', help='Save result to JSON file')
    
    args = parser.parse_args()
    
    try:
        # Initialize lookup
        lookup = PersonLookupDynamoDB(region_name=args.region)
        
        result = lookup.lookup_person_comprehensive(args.name)
        
        lookup.print_formatted_result(result)
        
        if args.output_json:
            with open(args.output_json, 'w', encoding='utf-8') as f:
                json.dump(result, f, ensure_ascii=False, indent=2, default=str)
            print(f"\n📄 Result saved to: {args.output_json}")
        
    except Exception as e:
        print(f"❌ Lookup failed: {e}")
        import traceback
        print(f"Stack trace: {traceback.format_exc()}")

if __name__ == "__main__":
    main() 