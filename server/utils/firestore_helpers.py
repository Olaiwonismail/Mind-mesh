from firebase import get_firestore_instance
from google.cloud import firestore
import uuid
from datetime import datetime

db = get_firestore_instance()

def get_user_profile(uid):
    doc = db.collection('users').document(uid).get()
    if doc.exists:
        return doc.to_dict()
    raise ValueError("User not found")

def update_user_profile(uid, data):
    db.collection('users').document(uid).set(data, merge=True)

def get_available_users(current_uid, wants_local_matches):
    query = db.collection('users')
    query = query.where('team_id', '==', None)
    
    if wants_local_matches:
        # Get current user's location for filtering
        current_user = get_user_profile(current_uid)
        user_city = current_user['location']['city']
        user_country = current_user['location']['country']
        
        # Filter by city and country
        query = query.where('location.city', '==', user_city)
        query = query.where('location.country', '==', user_country)
        
    users = []
    for doc in query.stream():
        if doc.id != current_uid:
            user_data = doc.to_dict()
            user_data['uid'] = doc.id  # Include the UID
            users.append(user_data)
            
    return users

def create_team(creator_uid, name, max_members):
    # Generate a unique team ID
    team_id = f"team_{uuid.uuid4().hex[:8]}"
    
    # Create the team document
    team_data = {
        'id': team_id,
        'name': name,
        'created_by': creator_uid,
        'members': [{
            'uid': creator_uid,
            'role': 'Creator',  # Default role for creator
            'joined_at': firestore.SERVER_TIMESTAMP
        }],
        'max_members': max_members,
        'created_at': firestore.SERVER_TIMESTAMP
    }
    
    # Use a transaction to update both team and user documents
    @firestore.transactional
    def update_in_transaction(transaction):
        # Create team document
        transaction.set(db.collection('teams').document(team_id), team_data)
        
        # Update user's team_id
        transaction.update(
            db.collection('users').document(creator_uid),
            {'team_id': team_id}
        )
    
    transaction = db.transaction()
    update_in_transaction(transaction)
    
    return team_id

def join_team(user_uid, team_id, role):
    @firestore.transactional
    def update_in_transaction(transaction):
        # Get team document
        team_ref = db.collection('teams').document(team_id)
        team_doc = team_ref.get(transaction=transaction)
        
        if not team_doc.exists:
            raise ValueError("Team does not exist")
            
        team_data = team_doc.to_dict()
        
        # Check if team has available slots
        if len(team_data['members']) >= team_data['max_members']:
            raise ValueError("Team is full")
            
        # Check if user is already in a team
        user_ref = db.collection('users').document(user_uid)
        user_doc = user_ref.get(transaction=transaction)
        
        if user_doc.exists and user_doc.to_dict().get('team_id'):
            raise ValueError("User is already in a team")
        
        # Add user to team members
        new_member = {
            'uid': user_uid,
            'role': role,
            'joined_at': firestore.SERVER_TIMESTAMP
        }
        
        transaction.update(team_ref, {
            'members': firestore.ArrayUnion([new_member])
        })
        
        # Update user's team_id
        transaction.update(user_ref, {'team_id': team_id})
    
    transaction = db.transaction()
    update_in_transaction(transaction)

def leave_team(user_uid, team_id):
    @firestore.transactional
    def update_in_transaction(transaction):
        # Get team document
        team_ref = db.collection('teams').document(team_id)
        team_doc = team_ref.get(transaction=transaction)
        
        if not team_doc.exists:
            raise ValueError("Team does not exist")
            
        team_data = team_doc.to_dict()
        
        # Remove user from team members
        members = team_data['members']
        updated_members = [m for m in members if m['uid'] != user_uid]
        
        if len(updated_members) == 0:
            # Delete team if no members left
            transaction.delete(team_ref)
        else:
            # Update team members
            transaction.update(team_ref, {'members': updated_members})
        
        # Update user's team_id to null
        user_ref = db.collection('users').document(user_uid)
        transaction.update(user_ref, {'team_id': None})
    
    transaction = db.transaction()
    update_in_transaction(transaction)

def get_team_details(team_id):
    doc = db.collection('teams').document(team_id).get()
    if doc.exists:
        return doc.to_dict()
    raise ValueError("Team not found")

def search_users(skill=None, city=None):
    query = db.collection('users')
    
    if skill:
        query = query.where('skills', 'array_contains', skill)
    
    if city:
        query = query.where('location.city', '==', city)
    
    users = []
    for doc in query.stream():
        user_data = doc.to_dict()
        user_data['uid'] = doc.id  # Include the UID
        users.append(user_data)
        
    return users

def get_map_players():
    # Get all users who have opted in to share location
    query = db.collection('users').where('wants_local_matches', '==', True)
    
    players = []
    for doc in query.stream():
        user_data = doc.to_dict()
        # Only include necessary data for the map
        if 'location' in user_data:
            players.append({
                'uid': doc.id,
                'name': user_data.get('name', 'Anonymous'),
                'location': user_data['location'],
                'skills': user_data.get('skills', [])
            })
            
    return players