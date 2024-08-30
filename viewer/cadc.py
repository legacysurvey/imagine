from social_core.backends.oauth import BaseOAuth2
from urllib.parse import urlencode

class CadcOAuth(BaseOAuth2):
    name = 'cadc'
    AUTHORIZATION_URL = 'https://ws-cadc.canfar.net/ac/authorize'
    ACCESS_TOKEN_URL = 'https://ws-cadc.canfar.net/ac/token'
    ACCESS_TOKEN_METHOD = 'POST'
    # REVOKE_TOKEN_URL = None
    # REVOKE_TOKEN_METHOD = 'POST'
    ID_KEY = 'id_token'
    # SCOPE_PARAMETER_NAME = 'scope'
    DEFAULT_SCOPE = ['openid', 'email']
    # SCOPE_SEPARATOR = ' '
    # STATE_PARAMETER = False
    EXTRA_DATA = [
    ('refresh_token', 'refresh_token', True),
    ('expires_in', 'expires'),
    ('token_type', 'token_type', True)
    ]
    #REFRESH_TOKEN_URL = None
    #REFRESH_TOKEN_METHOD = 'POST'
    #RESPONSE_TYPE = 'code'
    REDIRECT_STATE = False
    #STATE_PARAMETER = True

    # def user_data(self, access_token, *args, **kwargs):
    #     """Loads user data from service"""
    #     url = self.access_token_url()
    #     # url += urlencode({'access_token': access_token})
    #     print('Fetching user data from', url)
    #     #J = self.get_json(url)
    #     print('Access token:', access_token)
    #     
    #     J = self.get_json(url, params={'access_token': access_token},
    #                       method=)
    #     print('Got JSON:', J)
    #     return J

    def user_data(self, access_token, *args, **kwargs):
        print('CADC user_data: access_token', access_token)
        #J = self.get_json(
        R = self.request(
            'https://ws-cadc.canfar.net/ac/userinfo',
            headers={
                'Authorization': 'Bearer %s' % access_token,
            },
        )
        print('Got response:', R)
        print(R.text)
        try:
            J = R.json()
            print('Parsed:', J)
            return J
        except:
            pass
        return {}
    
    def get_user_id(self, details, response):
        """Return a unique ID for the current user, by default from server
        response."""
        print('CADC get_user_id.  details', details, 'response', response)
        return details['username']
        # print('ID KEY', self.ID_KEY)
        # uid = response.get(self.ID_KEY)
        # print('-> uid', uid)
        # return uid

    def get_user_details(self, response):
        '''Return user details from login reply'''
        import base64
        code = response.get('access_token')
        print('CADC get_user_details: access token', code)
        if code.startswith('base64:'):
            code = code[len('base64:'):]
        code = base64.b64decode(code)
        # bytes -> string
        code = code.decode()
        #print('Code:', code)
        kvs = code.split('&')
        details = {}
        for kv in kvs:
            #print('KV:', kv)
            words = kv.split('=', maxsplit=1)
            if len(words) != 2:
                print('Could not parse key-value pair:', words)
                continue
            key,val = words
            print('  ', key, '=', val)
            if key == 'userID':
                details['username'] = val
        return details
