#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Person Lookup Script
Connects to MongoDB and performs relational queries to find:
1. personal2media info: legal_status, role_in_event, source_level, violation_type
2. org2media info (organizations the person is in): legal_status, media_id, o2m_id, org_id, role_in_event, source_level, violation_type
"""
import os
import sys
import json
from pymongo import MongoClient
from typing import Dict, List, Any, Optional
import dotenv
dotenv.load_dotenv()

# Add parent directory to path to import utils
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from utils import Utils

class PersonLookup:
    def __init__(self, mongo_uri: str, mongo_db_name: str = "vpbank_hackathon"):
        """
        Initialize MongoDB connection for person lookup
        
        Args:
            mongo_uri: MongoDB connection string
            mongo_db_name: MongoDB database name
        """
        self.mongo_client = MongoClient(mongo_uri)
        self.mongo_db = self.mongo_client[mongo_db_name]
        
        # Test connection
        try:
            self.mongo_client.admin.command('ping')
            print(f"🔗 Successfully connected to MongoDB database: {mongo_db_name}")
        except Exception as e:
            print(f"❌ Failed to connect to MongoDB: {e}")
            raise

    def find_person_by_name(self, full_name: str) -> Optional[Dict]:
        """
        Find person in personal_info collection by full name
        
        Args:
            full_name: Full name of the person to search for
            
        Returns:
            Person document or None if not found
        """
        try:
            # Search for exact match first
            person = self.mongo_db.personal_info.find_one({"full_name": full_name})
            
            if not person:
                # Try case-insensitive search
                person = self.mongo_db.personal_info.find_one({
                    "full_name": {"$regex": f"^{full_name}$", "$options": "i"}
                })
            
            if not person:
                # Try partial match
                person = self.mongo_db.personal_info.find_one({
                    "full_name": {"$regex": full_name, "$options": "i"}
                })
            
            return person
            
        except Exception as e:
            print(f"❌ Error searching for person: {e}")
            return None

    def get_personal2media_info(self, per_id: str) -> List[Dict]:
        """
        Get personal2media information for a person
        
        Args:
            per_id: Person ID
            
        Returns:
            List of personal2media documents with required fields
        """
        try:
            # Query personal2media collection
            personal2media_docs = list(self.mongo_db.personal2media.find(
                {"per_id": per_id},
                {
                    "legal_status": 1,
                    "role_in_event": 1,
                    "source_level": 1,
                    "violation_type": 1,
                    "media_id": 1,
                    "p2m_id": 1,
                    "entity_name": 1,
                    "customer_role": 1,
                    "_id": 0
                }
            ))
            
            return personal2media_docs
            
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
            org_docs = list(self.mongo_db.organization_info.find({
                "personal_relationships": {"$regex": full_name, "$options": "i"}
            }))
            
            org2media_results = []
            
            for org in org_docs:
                org_id = org.get("org_id")
                if org_id:
                    # Find org2media entries for this organization
                    org2media_docs = list(self.mongo_db.org2media.find(
                        {"org_id": org_id},
                        {
                            "legal_status": 1,
                            "media_id": 1,
                            "o2m_id": 1,
                            "org_id": 1,
                            "role_in_event": 1,
                            "source_level": 1,
                            "violation_type": 1,
                            "entity_name": 1,
                            "customer_role": 1,
                            "_id": 0
                        }
                    ))
                    
                    # Add organization info to each org2media document
                    for doc in org2media_docs:
                        doc["organization_name"] = org.get("full_name")
                        doc["organization_type"] = org.get("occupation_or_position")
                    
                    org2media_results.extend(org2media_docs)
            
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
            media_doc = self.mongo_db.adverse_media.find_one(
                {"media_id": media_id},
                {
                    "media_id": 1,
                    "news_sentiment_type": 1,
                    "recency": 1,
                    "source_credibility": 1,
                    "content": 1,
                    "_id": 0
                }
            )
            
            # Truncate content for display
            if media_doc and media_doc.get("content"):
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

    def lookup_person_comprehensive(self, full_name: str) -> Dict[str, Any]:
        """
        Comprehensive lookup for a person including all related information
        
        Args:
            full_name: Full name of the person
            
        Returns:
            Dictionary with all related information
        """
        print(f"🔍 Looking up information for: {full_name}")
        
        # 1. Find the person
        person = self.find_person_by_name(full_name)
        if not person:
            return {
                "error": f"Person '{full_name}' not found in personal_info collection",
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
        
        # 5. Compile comprehensive result
        result = {
            "person_info": {
                "per_id": person.get('per_id'),
                "full_name": person.get('full_name'),
                "gender": person.get('gender'),
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
            # Search for names containing any part of the input name
            name_parts = full_name.split()
            regex_pattern = "|".join(name_parts)
            
            similar_docs = list(self.mongo_db.personal_info.find(
                {"full_name": {"$regex": regex_pattern, "$options": "i"}},
                {"full_name": 1, "_id": 0}
            ).limit(limit))
            
            return [doc["full_name"] for doc in similar_docs]
            
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

    def close(self):
        """Close MongoDB connection"""
        self.mongo_client.close()
        print("🔌 MongoDB connection closed")

def main():
    """Main function to run person lookup"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Lookup person information in MongoDB')
    parser.add_argument('--mongo-uri', help='MongoDB connection URI (or set MONGO_URI env var)')
    parser.add_argument('--mongo-db', default='vpbank_hackathon', help='MongoDB database name')
    parser.add_argument('--name', required=True, help='Full name of the person to lookup')
    parser.add_argument('--output-json', help='Save result to JSON file')
    
    args = parser.parse_args()
    
    # Get MongoDB URI
    mongo_uri = args.mongo_uri or os.getenv('MONGO_URI')
    if not mongo_uri:
        print("❌ MongoDB URI not provided. Use --mongo-uri or set MONGO_URI environment variable")
        return
    
    try:
        # Initialize lookup
        lookup = PersonLookup(mongo_uri, args.mongo_db)
        
        # Perform lookup
        result = lookup.lookup_person_comprehensive(args.name)
        
        # Print formatted result
        lookup.print_formatted_result(result)
        
        # Save to JSON if requested
        if args.output_json:
            with open(args.output_json, 'w', encoding='utf-8') as f:
                json.dump(result, f, ensure_ascii=False, indent=2, default=str)
            print(f"\n📄 Result saved to: {args.output_json}")
        
        # Close connection
        lookup.close()
        
    except Exception as e:
        print(f"❌ Lookup failed: {e}")
        import traceback
        print(f"Stack trace: {traceback.format_exc()}")

if __name__ == "__main__":
    main() 