from django.http import JsonResponse
from django.utils.deprecation import MiddlewareMixin
from rest_framework.authtoken.models import Token

from registration.models import AuthToken , AuthUser

class TokenAuthenticationMiddleware(MiddlewareMixin):
    """
    Middleware to check token authentication in the Authorization header.
    """
    def process_request(self, request):
        # Check if the Authorization header is present
        # Skip token authentication for excluded paths
        
        if request.path in ['/poolaccountsbackend/registration/check_login/']:
            return None
        
        auth_header = request.headers.get('Authorization')
        
        if not auth_header:
            return JsonResponse({'error': 'Authorization header is missing'}, status=401)

        # Validate the token format
        if not auth_header.startswith('Token '):
            return JsonResponse({'error': 'Invalid Authorization header format'}, status=401)

        # Extract the token
        token = auth_header.split(' ', 1)[1]
        userName = request.headers.get('userName')
        
        # Here, you should implement your token validation logic
        # For example, check if the token exists in the database
        if not self.validate_token(token , userName):
            return JsonResponse({'error': 'Invalid or expired token'}, status=401)

        # If token is valid, continue processing the request
        return None

    def validate_token(self, token , userName):
        # Replace with your actual validation logic
        # get userId using userName
        user_qry = AuthUser.objects.filter(username = userName)
        if user_qry.count() > 0:
            user_id = user_qry.values_list('id' , flat=True)[0]
        else:
            return None
        return token if AuthToken.objects.filter(key = token , user_id = user_id ).count() > 0 else None
       
       
