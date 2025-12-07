"""
Migration script to assign existing deals to a user

Usage:
    python migrate_deals.py <user_id>

Example:
    python migrate_deals.py abc123xyz456
"""

import sys
from google.cloud import firestore
from config.settings import settings

def migrate_deals(user_id: str):
    """
    Migrate all existing deals without user_id to the specified user
    
    Args:
        user_id: Firebase user ID to assign deals to
    """
    db = firestore.Client(project=settings.GCP_PROJECT_ID)
    
    print(f"Starting migration for user: {user_id}")
    print("=" * 60)
    
    # Query all deals
    deals_ref = db.collection('deals')
    all_deals = deals_ref.stream()
    
    migrated_count = 0
    skipped_count = 0
    
    for deal_doc in all_deals:
        deal_data = deal_doc.to_dict()
        deal_id = deal_doc.id
        
        # Check if deal already has a user_id
        if 'metadata' in deal_data and 'user_id' in deal_data.get('metadata', {}):
            print(f"⏭️  Skipping {deal_id} - already has user_id: {deal_data['metadata']['user_id']}")
            skipped_count += 1
            continue
        
        # Update deal with user_id
        try:
            deals_ref.document(deal_id).update({
                'metadata.user_id': user_id
            })
            company_name = deal_data.get('metadata', {}).get('company_name', 'Unknown')
            print(f"✅ Migrated {deal_id} ({company_name}) to user {user_id}")
            migrated_count += 1
        except Exception as e:
            print(f"❌ Error migrating {deal_id}: {str(e)}")
    
    print("=" * 60)
    print(f"\nMigration complete!")
    print(f"  Migrated: {migrated_count} deals")
    print(f"  Skipped:  {skipped_count} deals (already had user_id)")
    print(f"  Total:    {migrated_count + skipped_count} deals")

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Error: Missing user_id argument")
        print("\nUsage:")
        print("  python migrate_deals.py <user_id>")
        print("\nExample:")
        print("  python migrate_deals.py abc123xyz456")
        sys.exit(1)
    
    user_id = sys.argv[1]
    
    if not user_id or len(user_id) < 5:
        print("Error: Invalid user_id. Please provide a valid Firebase user ID.")
        sys.exit(1)
    
    migrate_deals(user_id)
