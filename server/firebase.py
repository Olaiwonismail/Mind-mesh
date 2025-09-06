import firebase_admin
from firebase_admin import credentials, firestore
import json
import os

# Initialize Firebase
firebase_cred_str = os.environ.get('FIREBASE_CREDENTIALS')
if not firebase_cred_str:
    raise ValueError("FIREBASE_CREDENTIALS environment variable not set")

firebase_cred_dict = json.loads(firebase_cred_str)
cred = credentials.Certificate(firebase_cred_dict)
firebase_admin.initialize_app(cred)

db = firestore.client()

# Export firestore instance
def get_firestore_instance():
    return db