import os
import json
import requests
import azure.functions as func

CLIENT_ID = os.getenv('GITHUB_CLIENT_ID')
CLIENT_SECRET = os.getenv('GITHUB_CLIENT_SECRET')


def main(req: func.HttpRequest) -> func.HttpResponse:
    code = req.params.get('code') or (req.get_json().get('code') if req.get_body() else None)
    if not code:
        return func.HttpResponse('missing code', status_code=400)
    data = {
        'client_id': CLIENT_ID,
        'client_secret': CLIENT_SECRET,
        'code': code
    }
    headers = {'Accept': 'application/json'}
    r = requests.post('https://github.com/login/oauth/access_token', data=data, headers=headers)
    if r.status_code != 200:
        return func.HttpResponse('oauth error', status_code=500)
    token = r.json().get('access_token')
    body = json.dumps({'token': token})
    return func.HttpResponse(body, mimetype='application/json')
