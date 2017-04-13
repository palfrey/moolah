from requests_oauthlib import OAuth1Session
import json

keys = json.loads(open('config.json').read())

request_token_url = 'https://secure.splitwise.com/api/v3.0/get_request_token'

client_key = keys['client_key']
client_secret = keys['client_secret']
oauth = OAuth1Session(client_key, client_secret=client_secret)
fetch_response = oauth.fetch_request_token(request_token_url)
resource_owner_key = fetch_response.get('oauth_token')
resource_owner_secret = fetch_response.get('oauth_token_secret')

base_authorization_url = 'https://secure.splitwise.com/authorize'
authorization_url = oauth.authorization_url(base_authorization_url)
print 'Please go here and authorize,', authorization_url
redirect_response = raw_input('Paste the full redirect URL here: ')
oauth_response = oauth.parse_authorization_response(redirect_response)
verifier = oauth_response.get('oauth_verifier')

access_token_url = 'https://secure.splitwise.com/api/v3.0/get_access_token'

oauth = OAuth1Session(client_key,
                          client_secret=client_secret,
                          resource_owner_key=resource_owner_key,
                          resource_owner_secret=resource_owner_secret,
                          verifier=verifier)
oauth_tokens = oauth.fetch_access_token(access_token_url)
resource_owner_key = oauth_tokens.get('oauth_token')
resource_owner_secret = oauth_tokens.get('oauth_token_secret')

splitwise = OAuth1Session(client_key,
                            client_secret=client_secret,
                            resource_owner_key=resource_owner_key,
                            resource_owner_secret=resource_owner_secret)

url = 'https://secure.splitwise.com/api/v3.0/test'
r = splitwise.get(url)
r.raise_for_status()
print r.json()