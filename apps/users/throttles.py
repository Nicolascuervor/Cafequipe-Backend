# apps/users/throttles.py
from rest_framework.throttling import BaseThrottle
from django.core.cache import cache


class LoginFailedThrottle(BaseThrottle):

    def allow_request(self, request, view):
        if request.method != 'POST':
            return True


        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0].strip()
        else:
            ip = request.META.get('REMOTE_ADDR')

        cache_key = f"login_failed_count_{ip}"
        failed_count = cache.get(cache_key, 0)

        if failed_count >= 5:
            return False

        return True

    def wait(self):
        return 900
