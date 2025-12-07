import requests
import json
import sys

# Force UTF-8 for stdout
sys.stdout.reconfigure(encoding='utf-8')

BASE_URL = "http://localhost:8080"
DEAL_ID = "f8c86c"  # From user's URL

def test_investor_chat():
    print(f"Testing Investor Chat API for Deal ID: {DEAL_ID}...")
    
    url = f"{BASE_URL}/api/investor_chat"
    
    payload = {
        "deal_id": DEAL_ID,
        "message": "What is the main problem this startup is solving?",
        "history": []
    }
    
    try:
        response = requests.post(url, json=payload)
        
        if response.status_code == 200:
            data = response.json()
            print("\n[SUCCESS] Chatbot Response:")
            print("-" * 50)
            print(data.get("message"))
            print("-" * 50)
            return True
        else:
            print(f"\n[FAILED] Status Code: {response.status_code}")
            print(f"Error: {response.text}")
            return False
            
    except Exception as e:
        print(f"\n[ERROR] Request failed: {e}")
        return False

if __name__ == "__main__":
    test_investor_chat()
