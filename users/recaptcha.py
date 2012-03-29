# -*- coding: utf8 -*-
"""
POST:

privatekey (required)   Your private key
remoteip (required)     The IP address of the user who solved the CAPTCHA.
challenge (required)    The value of "recaptcha_challenge_field" sent via the form
response (required)     The value of "recaptcha_response_field" sent via the form
"""

# Public Key: 
# Use this in the JavaScript code that is served to your users
pubkey =  ""

# Private Key: 
# Use this when communicating between your server and our server. Be sure to keep it a secret.
privkey = ""

import urllib2

def verify(ip, challange, response):
  payload = {}
  payload['privatekey'] = privkey.encode('utf-8')
  payload['remoteip'] = ip.encode('utf-8')
  payload['challenge'] = challange.encode('utf-8')
  payload['response'] = response.encode('utf-8')
  payload = urllib2.urlencode(payload)
  result_req = urllib2.Request(url="http://www.google.com/recaptcha/api/verify",
                               data=payload,
                               headers={'Content-Type': 'application/x-www-form-urlencoded'})
  result = urllib2.urlopen(result_req).read()
  
  if result.status_code == 200:
    return result.content.startswith("true")
  # if not 20OK or not starting with true we have a problem
  return False

