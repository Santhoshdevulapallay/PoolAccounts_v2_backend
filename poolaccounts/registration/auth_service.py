

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
from registration.models import Registration

def checkEntity(username):
    try:
        is_reg_qry = Registration.objects.filter(username = username)
        if is_reg_qry.count() > 0 :
            fin_code , is_utility = is_reg_qry.values_list('fin_code' , flat=True)[0] , True 
        else :
           fin_code , is_utility = None ,False
        return fin_code , is_utility
    except Exception as e:
        return None ,False
    
def login(request):
    try:
        userdata=json.loads(request.body)
        serializer=LoginSerializer(data=userdata['formdata'])
        serializer.is_valid(raise_exception=True)
        user = serializer.validated_data['user']
        # actually here first_name is for Department (MO,FIN)
        token, created = Token.objects.get_or_create(user=user)
        if user: 
            fin_code , is_utility = checkEntity(userdata['formdata']['username'])
           
            return JsonResponse({
                'status':True,
                'token': token.key,
                'user_id': user.pk,
                'isSuperUser':user.is_superuser,
                'userName':user.username,
                'department':user.first_name ,
                'fin_code' : fin_code ,
                'is_utility': is_utility
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
