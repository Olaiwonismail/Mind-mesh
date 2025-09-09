from firebase_admin import auth
from functools import wraps
from flask import request

def verify_firebase_token(id_token):
    try:
        decoded_token = auth.verify_id_token(id_token)
        return decoded_token['uid']
    except Exception as e:
        raise ValueError(f"Invalid token: {str(e)}")