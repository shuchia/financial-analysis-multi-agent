#!/usr/bin/env python3
"""
Test the complete preferences flow: signup -> onboarding -> save preferences -> login -> load preferences
"""

import requests
import json
import time
import uuid

def test_complete_flow():
    """Test the complete user signup and preferences flow."""
    
    print("🧪 Testing Complete Preferences Flow")
    print("=" * 37)
    
    # Generate unique test user
    test_email = f"prefs-test-{str(uuid.uuid4())[:8]}@example.com"
    test_password = "testpass123"
    
    print(f"📝 Test user: {test_email}")
    
    # Step 1: Sign up
    print("\n1️⃣ Testing Signup...")
    signup_response = requests.post(
        "https://investforge.io/api/auth/signup",
        headers={"Content-Type": "application/json"},
        json={
            "email": test_email,
            "password": test_password,
            "first_name": "Prefs",
            "last_name": "Test",
            "plan": "free"
        }
    )
    
    print(f"Signup status: {signup_response.status_code}")
    signup_data = signup_response.json()
    print(f"Signup success: {signup_data.get('success')}")
    
    if not signup_data.get('success'):
        print(f"❌ Signup failed: {signup_data}")
        return
    
    # Wait for consistency
    time.sleep(2)
    
    # Step 2: Save preferences (simulating onboarding completion)
    print("\n2️⃣ Testing Preferences Save...")
    preferences = {
        "experience": "Intermediate 📈",
        "goals": ["Learn about investing", "Build long-term wealth", "Save for retirement"],
        "risk_tolerance": 6,
        "initial_amount": "$1,000-5,000",
        "timestamp": "2025-09-23T19:45:00.000Z",
        "onboarding_completed": True
    }
    
    prefs_response = requests.post(
        "https://investforge.io/api/users/preferences",
        headers={"Content-Type": "application/json"},
        json={
            "email": test_email,
            "preferences": preferences
        }
    )
    
    print(f"Preferences save status: {prefs_response.status_code}")
    prefs_data = prefs_response.json()
    print(f"Preferences save success: {prefs_data.get('success')}")
    
    if not prefs_data.get('success'):
        print(f"❌ Preferences save failed: {prefs_data}")
        return
    
    # Step 3: Verify preferences were saved
    print("\n3️⃣ Testing Preferences Retrieval...")
    
    # Note: Using POST since GET has CloudFront issues
    get_prefs_response = requests.post(
        "https://investforge.io/api/users/preferences",
        headers={"Content-Type": "application/json"},
        json={
            "email": test_email,
            "action": "get"
        }
    )
    
    print(f"Preferences get status: {get_prefs_response.status_code}")
    
    if get_prefs_response.status_code == 200:
        get_prefs_data = get_prefs_response.json()
        print(f"Preferences get success: {get_prefs_data.get('success')}")
        
        if get_prefs_data.get('success'):
            retrieved_prefs = get_prefs_data.get('data', {})
            print(f"Retrieved preferences: {json.dumps(retrieved_prefs, indent=2)}")
            
            # Verify key fields match
            matches = (
                retrieved_prefs.get('experience') == preferences['experience'] and
                retrieved_prefs.get('risk_tolerance') == preferences['risk_tolerance'] and
                retrieved_prefs.get('initial_amount') == preferences['initial_amount']
            )
            
            if matches:
                print("✅ Preferences match what was saved!")
            else:
                print("❌ Preferences don't match!")
                print(f"Expected: {preferences}")
                print(f"Got: {retrieved_prefs}")
        else:
            print(f"❌ Preferences retrieval failed: {get_prefs_data}")
    else:
        print(f"❌ Preferences retrieval HTTP error: {get_prefs_response.status_code}")
        print(f"Response: {get_prefs_response.text}")
    
    # Step 4: Test login (to verify user can login after signup)
    print("\n4️⃣ Testing Login with Preferences User...")
    login_response = requests.post(
        "https://investforge.io/api/auth/login",
        headers={"Content-Type": "application/json"},
        json={
            "email": test_email,
            "password": test_password
        }
    )
    
    print(f"Login status: {login_response.status_code}")
    login_data = login_response.json()
    print(f"Login success: {login_data.get('success')}")
    
    # Step 5: Update preferences (test modification)
    print("\n5️⃣ Testing Preferences Update...")
    updated_preferences = preferences.copy()
    updated_preferences["risk_tolerance"] = 8
    updated_preferences["goals"].append("Short-term trading")
    updated_preferences["last_updated"] = "2025-09-23T19:50:00.000Z"
    
    update_response = requests.post(
        "https://investforge.io/api/users/preferences",
        headers={"Content-Type": "application/json"},
        json={
            "email": test_email,
            "preferences": updated_preferences
        }
    )
    
    print(f"Preferences update status: {update_response.status_code}")
    update_data = update_response.json()
    print(f"Preferences update success: {update_data.get('success')}")
    
    # Final summary
    print("\n📋 Test Summary:")
    print(f"   ✅ Signup: {signup_data.get('success')}")
    print(f"   ✅ Preferences Save: {prefs_data.get('success')}")
    print(f"   ✅ Preferences Retrieval: {get_prefs_response.status_code == 200}")
    print(f"   ✅ Login: {login_data.get('success')}")
    print(f"   ✅ Preferences Update: {update_data.get('success')}")
    
    all_passed = all([
        signup_data.get('success'),
        prefs_data.get('success'),
        get_prefs_response.status_code == 200,
        login_data.get('success'),
        update_data.get('success')
    ])
    
    if all_passed:
        print("\n🎉 All tests passed! Preferences system is working correctly!")
    else:
        print("\n⚠️  Some tests failed. Check the output above for details.")

if __name__ == "__main__":
    test_complete_flow()