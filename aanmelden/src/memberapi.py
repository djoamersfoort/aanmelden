from django.conf import settings
import requests


class MemberApi:
    @staticmethod
    def get_user_profile(userid, access_token):
        userid = userid.replace('u-', '')
        url = f'{settings.LEDEN_ADMIN_API_URL}/{userid}/'
        response = requests.get(url, headers={'Authorization': f'IDP {access_token}'})
        if not response.ok:
            raise ValueError(f"Unable to retrieve user profile: {response.content}")

        return response.json()
