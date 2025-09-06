import os
import groq
from .firestore_helpers import get_user_profile, get_available_users
import json

client = groq.Groq(api_key=os.environ.get("GROQ_API_KEY"))

def find_matches(uid):
    current_user = get_user_profile(uid)
    candidates = get_available_users(uid, current_user['wants_local_matches'])
    
    # Prepare prompt for Groq
    prompt = f"""
    You are a matchmaking assistant for a hackathon.

    Current user:
    - name: {current_user['name']}
    - email: {current_user['email']}
    - skills: {', '.join(current_user['skills'])}
    - preferred_roles: {', '.join(current_user['preferred_roles'])}
    - location: {current_user['location']['city']}, {current_user['location']['country']} 
      (wants_local_matches: {current_user['wants_local_matches']})

    Candidates:
    {format_candidates(candidates)}

    Task:
    Suggest the top 3 teammates for the current user. Prioritize:
    1) Complementary skills (cover missing roles),
    2) Some desirable overlap for collaboration,
    3) Prefer local matches if wants_local_matches=true.
    
    For each teammate, return JSON: {{"name":"", "email":"", "score":<0-100>, "reason":""}}
    Return only valid JSON array.
    """
    
    try:
        chat_completion = client.chat.completions.create(
            messages=[{"role": "user", "content": prompt}],
            model="mixtral-8x7b-32768",
            temperature=0.5
        )
        return json.loads(chat_completion.choices[0].message.content)
    except:
        # Fallback to deterministic matching
        return deterministic_matching(current_user, candidates)

def format_candidates(candidates):
    return "\n".join([
        f"- {c['name']} ({c['email']}): {', '.join(c['skills'])} | "
        f"roles: {', '.join(c['preferred_roles'])} | "
        f"location: {c['location']['city']}"
        for c in candidates
    ])

def deterministic_matching(current_user, candidates):
    # Implement fallback matching logic
    matches = []
    for candidate in candidates:
        score = calculate_match_score(current_user, candidate)
        if score > 0:
            matches.append({
                "name": candidate['name'],
                "email": candidate['email'],
                "score": score,
                "reason": "Skills complement and roles match"
            })
    return sorted(matches, key=lambda x: x['score'], reverse=True)[:3]

def calculate_match_score(user, candidate):
    # Simple scoring algorithm
    skill_overlap = len(set(user['skills']) & set(candidate['skills']))
    role_complement = len(set(user['preferred_roles']) - set(candidate['preferred_roles']))
    return (skill_overlap * 10) + (role_complement * 5)