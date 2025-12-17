
import firebase_admin
from firebase_admin import credentials, firestore
import os

# Initialize
if not firebase_admin._apps:
    cred = credentials.Certificate('firebase-service-account.json')
    firebase_admin.initialize_app(cred)

db = firestore.client()

# Get latest deal
deals_ref = db.collection('deals')
query = deals_ref.order_by('metadata.created_at', direction=firestore.Query.DESCENDING).limit(1)
docs = query.stream()

for doc in docs:
    deal = doc.to_dict()
    print(f"Deal ID: {doc.id}")
    print("--- Credit Analysis ---")
    ca = deal.get('credit_analysis', {})
    import json
    print(json.dumps(ca, indent=2))
    
    print("\n--- CMA Structured ---")
    cma_struc = deal.get('cma_structured', {})
    import json
    print(json.dumps(cma_struc, indent=2)[:500] + "...") # Print start

