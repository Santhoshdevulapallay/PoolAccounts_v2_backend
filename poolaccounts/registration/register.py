
from django.http import HttpResponse , JsonResponse
import json , os
from django.core.files.storage import FileSystemStorage
from poolaccounts.settings import base_dir
from .add530hrs import add530hrstoDateString
from .extarctdb_errors import *
from .forms import *
from django.core.exceptions import ValidationError
from django.db import IntegrityError
from rest_framework import status
import random
from datetime import timedelta
from django.contrib.auth.models import User

def newRegistration(request):
      try:
            formdata=json.loads(request.body)['formdata']
            # add 5:30 hrs to startdate and end date
            start_date = add530hrstoDateString(formdata['start_date'].replace('"','')).date()
            if formdata['end_date'] is not None:
                  end_date = add530hrstoDateString(formdata['end_date'].replace('"','')).date()
                  formdata['end_date']=end_date 

            # change boolean format
            formdata['is_nclt'] =  True if formdata['is_nclt'] == 'Y'  else False
            #changing the date format
            formdata['start_date']=start_date  
            form = NewRegistrationForm(formdata)
          
            if form.is_valid():
                  Registration.objects.create(**form.cleaned_data)
                  return JsonResponse('success',safe=False)
            else:
                  return HttpResponse(form.errors['__all__'] , status=status.HTTP_400_BAD_REQUEST)
            
      except (IntegrityError, ValidationError) as e:
            return HttpResponse(str(e),status=status.HTTP_400_BAD_REQUEST)
            
     
def updateEntityRegistration(request):
      try:
            formdata=json.loads(request.body)['formdata']
            if formdata['end_date'] is not None:
                  end_date = add530hrstoDateString(formdata['end_date'].replace('"','')).date()
                  formdata['end_date']=end_date 
            else:
                  # else consider todays date
                  formdata['end_date'] = datetime.now().date()
            # change boolean format
            formdata['is_nclt'] =  True if formdata['is_nclt'] == 'Y'  else False
            
            # ending the old entity details 
            register_obj=Registration.objects.filter(id=formdata['id'])
            register_obj.update(
                  end_date=formdata['end_date'] ,
                  remarks=formdata['remarks']
            )
            new_start_date= formdata['end_date'] + timedelta(days=1)
            formdata['start_date']=new_start_date 
            formdata['end_date']=None
            formdata['remarks']=''

            # now create new entity w.e.f from startdate
            form = NewRegistrationForm(formdata)
       
            if form.is_valid():
                  Registration.objects.create(**form.cleaned_data)
                  return JsonResponse('success',safe=False)
            else:
                  return HttpResponse(form.errors['__all__'] , status=status.HTTP_400_BAD_REQUEST)
            
      except (IntegrityError, ValidationError) as e:
            return HttpResponse(str(e),status=status.HTTP_400_BAD_REQUEST)
            
     
def updateContactRegistration(request):
      try:
            formdata=json.loads(request.body)['formdata']
            # add 5:30 hrs to startdate and end date
            if formdata['end_date'] is not None:
                  end_date = add530hrstoDateString(formdata['end_date'].replace('"','')).date()
                  formdata['end_date']=end_date 
            else:
                  # else consider todays date
                  formdata['end_date'] = datetime.now().date()
            # ending the old entity details 
            register_obj=Registration.objects.filter(id=formdata['id'])
            register_obj.update(
                  end_date=formdata['end_date'] ,
                  remarks=formdata['remarks']
            )
            # add finance_name to formdata , startdate is old record (end_date - 1 )
            new_start_date= formdata['end_date'] + timedelta(days=1)
            formdata['start_date']=new_start_date 
            formdata['end_date']=None
            formdata['remarks']=''
            try:
                  formdata['finance_name']=register_obj[0].finance_name
                  formdata['is_nclt']=register_obj[0].is_nclt
                  formdata['dsm_name']=register_obj[0].dsm_name
                  formdata['sras_name']=register_obj[0].sras_name
                  formdata['tras_name']=register_obj[0].tras_name
                  formdata['react_name']=register_obj[0].react_name
                  formdata['entity_type']=register_obj[0].entity_type
            except Exception as err: 
                  extractdb_errormsg(err) 

            # now create new entity w.e.f from startdate
            form = NewRegistrationForm(formdata)
            
            if form.is_valid():
                  Registration.objects.create(**form.cleaned_data)
                  return JsonResponse('success',safe=False)
            else:
                  return HttpResponse(form.errors['__all__'] , status=status.HTTP_400_BAD_REQUEST)
            
      except (IntegrityError, ValidationError) as e:
            return HttpResponse(str(e),status=status.HTTP_400_BAD_REQUEST)
            
     
def addBankDetails(request):
      try:
            formdata=json.loads(request.POST['formdata'])
            # add 5:30 hrs to startdate and end date
            start_date = add530hrstoDateString(formdata['start_date'].replace('"','')).date()
            if formdata['end_date'] is not None:
                  end_date = add530hrstoDateString(formdata['end_date'].replace('"','')).date()
                  formdata['end_date']=end_date 

            #changing the date format
            formdata['start_date']=start_date  
            
            # update fin_code
            fin_code_fk=Registration.objects.get(fin_code=formdata['fin_code_fk'] , end_date__isnull=True).id
            formdata['fin_code_fk'] = fin_code_fk
            # change boolean format
            formdata['is_sbi'] =  True if formdata['is_sbi'] == 'Y'  else False

            # write the files into folder
            parent_folder = os.path.abspath(os.path.join(base_dir, os.pardir))
            directory = os.path.join(parent_folder, 'Files', 'Registration&Bank' , formdata['entity_name'])
            # add startdate and enddate to create new folder
            if not os.path.exists(directory):
                  # Create the directory if it doesn't exist
                  os.makedirs(directory)

            all_file_paths=[]
            for fl in request.FILES.getlist('files'):
                  file_path=os.path.join(directory ,  fl.name)
                  with open(file_path, 'wb+') as destination:
                        for chunk in fl.chunks():
                              destination.write(chunk)

                  short_path='\\Files\\Registration&Bank\\'+formdata['entity_name']+'\\'+fl.name
                  all_file_paths.append(short_path)
            # change the supporting docs filenames
            formdata['supporting_docs'] = all_file_paths
            del formdata['entity_name']
            form = NewBankDetailsForm(formdata)
           
            if form.is_valid():
                  BankDetails.objects.create(**form.cleaned_data)
                  return JsonResponse('success',safe=False)
            else:
                  return HttpResponse(form.errors['__all__'] , status=status.HTTP_400_BAD_REQUEST)
            
      except (IntegrityError, ValidationError) as e:
            return HttpResponse(str(e),status=status.HTTP_400_BAD_REQUEST)
            

def allDeptUsers(request):
      try:
            all_users=list(User.objects.filter(is_active=True).order_by('username').values('username','first_name','date_joined','last_login'))
            return JsonResponse(all_users,safe=False)
      
      except (IntegrityError, ValidationError) as e:
            return HttpResponse(str(e),status=status.HTTP_400_BAD_REQUEST)
          
def createUser(request):
      try:
            formdata=json.loads(request.body)
            password=formdata['username']+'#$4321'
            # check if user already exists or not
            check_user=User.objects.filter(username=formdata['username'])
            if check_user.count() > 0:
                  return JsonResponse({'exists':True,'message':'User already exists'})
            else:
                  # here actually considering first_name as Dept name to differentiate different users
                  user = User.objects.create_user(username=formdata['username'],
                                    password=password,
                                    first_name=formdata['dept']
                                    )
                  user.save()
                  return JsonResponse({'exists':False ,'message':'User Created Successfully'},safe=False)
      
      except (IntegrityError, ValidationError) as e:
            return HttpResponse(str(e),status=status.HTTP_400_BAD_REQUEST)
          