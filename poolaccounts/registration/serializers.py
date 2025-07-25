# tasks/serializers.py
from rest_framework import serializers
from .models import *
from django.contrib.auth import authenticate
from rest_framework import serializers
from django.views.decorators.csrf import csrf_exempt

class LoginSerializer(serializers.Serializer):
      username=serializers.CharField()
      password=serializers.CharField()
    
      def validate(self,data):
           
            username=data.get("username","")
            password=data.get("password","")
            if username and password:
                  user=authenticate(username=username,password=password)
                  if user:
                        if user.is_active:
                              data["user"]=user
                        else:
                              msg="User is deactivated"
                              raise serializers.ValidationError(msg)
                              # raise exceptions.ValidationError(msg)
                  else:
                        msg="Credentials were not correct"
                        raise serializers.ValidationError(msg)
                        # raise exceptions.ValidationError(msg)
            else:
                  msg="Must Provide username and password"
                  raise serializers.ValidationError(msg)
            
            # raise exceptions.ValidationError(msg)
            return data