# -*- coding: utf-8 -*-
"""
POST:

privatekey (required)   Your private key
remoteip (required)     The IP address of the user who solved the CAPTCHA.
challenge (required)    The value of "recaptcha_challenge_field" sent via the form
response (required)     The value of "recaptcha_response_field" sent via the form
"""
from urllib.request import urlopen, Request
from urllib.parse import urlencode


# Public Key:
# Use this in the JavaScript code that is served to your users
pubkey = ""

# Private Key:
# Use this when communicating between your server and our server. Be sure to keep it a secret.
privkey = ""


def verify(ip, challenge, response):
    payload = {}
    payload['privatekey'] = privkey.encode('utf-8')
    payload['remoteip'] = ip.encode('utf-8')
    payload['challenge'] = challenge.encode('utf-8')
    payload['response'] = response.encode('utf-8')
    payload = urlencode(payload)
    result_req = Request(url="http://www.google.com/recaptcha/api/verify",
                         data=payload,
                         headers={'Content-Type': 'application/x-www-form-urlencoded'})
    result = urlopen(result_req).read()

    if result.status_code == 200:
        return result.content.startswith("true")
    # if not 20OK or not starting with true we have a problem
    return False
