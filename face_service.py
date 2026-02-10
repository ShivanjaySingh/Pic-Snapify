# This file is your "AI Manager." It handles all the talking to Microsoft so your main code stays clean.

import requests

# CONFIG: Get these from Azure Portal (India Central)
KEY = "YOUR_AZURE_KEY"
ENDPOINT = "https://YOUR_RESOURCE_NAME.cognitiveservices.azure.com/face/v1.0"

def index_studio_photo(gallery_id, image_bytes):
    """Studio Upload: Tells Azure to 'remember' this face for later."""
    # 1. Create a person 'slot' in Azure for this photo
    p_url = f"{ENDPOINT}/persongroups/group_{gallery_id}/persons"
    p_res = requests.post(p_url, headers={'Ocp-Apim-Subscription-Key': KEY}, json={"name": "guest"}).json()
    person_id = p_res['personId']

    # 2. Upload the face data to that slot
    f_url = f"{ENDPOINT}/persongroups/group_{gallery_id}/persons/{person_id}/persistedFaces"
    requests.post(f_url, headers={'Ocp-Apim-Subscription-Key': KEY, 'Content-Type': 'application/octet-stream'}, data=image_bytes)
    
    # 3. Quick 'Train' (makes the face searchable immediately)
    requests.post(f"{ENDPOINT}/persongroups/group_{gallery_id}/train", headers={'Ocp-Apim-Subscription-Key': KEY})
    
    return person_id

def find_client_photos(gallery_id, selfie_bytes):
    """Client Search: Finds which photos match the client's selfie."""
    headers = {'Ocp-Apim-Subscription-Key': KEY}
    
    # A. Detect the face in the client's selfie
    det_res = requests.post(f"{ENDPOINT}/detect?returnFaceId=true", 
                            headers={**headers, 'Content-Type': 'application/octet-stream'}, data=selfie_bytes).json()
    if not det_res: return []
    face_id = det_res[0]['faceId']

    # B. Identify which 'person_ids' in the gallery match this face
    id_body = {"personGroupId": f"group_{gallery_id}", "faceIds": [face_id], "confidenceThreshold": 0.5}
    id_res = requests.post(f"{ENDPOINT}/identify", headers={**headers, 'Content-Type': 'application/json'}, json=id_body).json()
    
    candidates = id_res[0].get('candidates', [])
    return [c['personId'] for c in candidates]