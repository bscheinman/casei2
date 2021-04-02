from django.conf import settings
from django.core.mail import EmailMultiAlternatives
from urllib.parse import urlencode
import requests


def shorten_url(long_url):
    username = settings.BITLY_USERNAME
    apiKey= settings.BITLY_APIKEY
    args = { 'login':username, 'apiKey':apiKey, 'longUrl':long_url, 'format':'txt' }
    encoded_args = urlencode(args)
    bitly_url = 'http://api.bit.ly/v3/shorten?%s' % encoded_args
    short_url = requests.get(bitly_url).text
    return short_url.rstrip()


def create_verify_link(verify_id):
    return 'http://localhost:8000/verify/%s/' % verify_id


def send_verification_email(email, verify_id):
    subject, from_email, to_email = 'Verify Your CAse iNSensItivE Account', 'noreply@caseinsensitive.org', email
    verify_link = shorten_url(create_verify_link(verify_id))

    html_content = "Welcome to CasE InSensitIVE.  Please <a href='%s'>verify your email address</a> in order to complete your registration." % verify_link

    msg = EmailMultiAlternatives(subject, '', from_email, [to_email])
    msg.attach_alternative(html_content, 'text/html')
    msg.send()
