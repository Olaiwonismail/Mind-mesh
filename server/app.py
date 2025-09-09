from flask import Flask, request, jsonify
from flask_cors import CORS
from google.cloud import firestore
import os
from utils.auth import verify_firebase_token
from utils.matching import find_matches
from utils.firestore_helpers import (
    get_user_profile,
    update_user_profile,
    create_team,
    join_team,
    leave_team,
    get_team_details,
    search_users,
    get_map_players
)

app = Flask(__name__)
CORS(app)

# Auth Middleware
@app.before_request
def authenticate_request():
    if request.method == 'OPTIONS':
        return
    excluded_routes = ['/onboard']  # Add any public endpoints
    if request.path not in excluded_routes:
        auth_header = request.headers.get('Authorization')
        if not auth_header:
            return jsonify({'error': 'Authorization header missing'}), 401
        id_token = auth_header.split('Bearer ')[1]
        request.uid = verify_firebase_token(id_token)

# Endpoints
@app.route('/onboard', methods=['POST'])
def onboard_user():
    try:
        data = request.json
        
        # Validate required fields
        required_fields = ['name', 'skills', 'preferred_roles', 'wants_local_matches']
        for field in required_fields:
            if field not in data:
                return jsonify({'error': f'Missing required field: {field}'}), 400
        
        # Get authentication token
        auth_header = request.headers.get('Authorization')
        if not auth_header or not auth_header.startswith('Bearer '):
            return jsonify({'error': 'Authorization header missing or invalid'}), 401
            
        id_token = auth_header.split('Bearer ')[1]
        uid = verify_firebase_token(id_token)
        
        # Handle location data
        if data.get('location') is None:
            location_data = {
                'city': 'Unknown',
                'country': 'Unknown',
                'coords': {'lat': 0, 'lng': 0}
            }
        else:
            location_data = data['location']
            # Ensure location has required structure
            if 'city' not in location_data:
                location_data['city'] = 'Unknown'
            if 'country' not in location_data:
                location_data['country'] = 'Unknown'
            if 'coords' not in location_data:
                location_data['coords'] = {'lat': 0, 'lng': 0}
        
        user_data = {
            'name': data['name'],
            'skills': data['skills'],
            'preferred_roles': data['preferred_roles'],
            'wants_local_matches': data['wants_local_matches'],
            'location': location_data,
            'last_active': firestore.SERVER_TIMESTAMP
        }
        # print(user_data)
        update_user_profile(uid, user_data)
        print(user_data)
        return jsonify({'status': 'success', 'user_id': uid}), 200
        
    except ValueError as e:
        # Authentication errors
        return jsonify({'error': str(e)}), 401
    except Exception as e:
        print(f"Onboarding error: {str(e)}")
        return jsonify({'error': 'Internal server error'}), 500

@app.route('/users/me', methods=['GET'])
def get_current_user():
    try:
        user = get_user_profile(request.uid)
        print(user)
        return jsonify(user), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 400

@app.route('/match', methods=['POST'])
def match_users():
    try:
        data = request.json
        target_uid = data.get('user_uid', request.uid)
        matches = find_matches(target_uid)
        return jsonify(matches), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 400

@app.route('/teams', methods=['POST'])
def create_new_team():
    try:
        data = request.json
        team_id = create_team(request.uid, data['name'], data['max_members'])
        return jsonify({'team_id': team_id}), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 400

@app.route('/teams/<team_id>/join', methods=['POST'])
def join_existing_team(team_id):
    try:
        data = request.json
        join_team(request.uid, team_id, data['role'])
        return jsonify({'status': 'success'}), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 400

@app.route('/teams/<team_id>/leave', methods=['POST'])
def leave_existing_team(team_id):
    try:
        leave_team(request.uid, team_id)
        return jsonify({'status': 'success'}), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 400

@app.route('/teams/<team_id>', methods=['GET'])
def get_team(team_id):
    try:
        team = get_team_details(team_id)
        return jsonify(team), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 400

@app.route('/search/users', methods=['GET'])
def search_users_route():
    try:
        skill = request.args.get('skill')
        city = request.args.get('city')
        results = search_users(skill, city)
        return jsonify(results), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 400

@app.route('/map/players', methods=['GET'])
def get_players_map():
    try:
        players = get_map_players()
        return jsonify(players), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 400

if __name__ == '__main__':
    app.run(debug=True)