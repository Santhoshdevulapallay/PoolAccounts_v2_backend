

# from django.core.exceptions import ValidationError
from django.db import IntegrityError
from django.http import HttpResponse , JsonResponse,FileResponse
import json

from registration.serializers import LoginSerializer
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.authtoken.models import Token
from rest_framework import status
from rest_framework.exceptions import ValidationError
from django.contrib.auth import authenticate, login,logout

def login(request):
    try:
        
        userdata=json.loads(request.body)
        serializer=LoginSerializer(data=userdata['formdata'])
        serializer.is_valid(raise_exception=True)
        user = serializer.validated_data['user']
        
        token, created = Token.objects.get_or_create(user=user)
        # actually here first_name is for Department (MO,FIN)
        if user:
            return JsonResponse({
                'status':True,
                'token': token.key,
                'user_id': user.pk,
                'isSuperUser':user.is_superuser,
                'userName':user.username,
                'department':user.first_name
                })
        else:
            return JsonResponse({'status':False})
        
    except ValidationError as err:
        # Extract non_field_errors
        non_field_errors = err.detail.get('non_field_errors', [])
        # You can customize the response format as needed
        return JsonResponse({'status':False,'non_field_errors': non_field_errors},safe=False)


def logout(request):
    try:
        logout(request)
        return JsonResponse({'status':True},safe=False)
    except Exception as err:
        return JsonResponse({'status':False},safe=False)
