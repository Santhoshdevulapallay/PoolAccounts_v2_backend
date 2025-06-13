

from .models import Registration , BankDetails , LCDetails
from django.http import JsonResponse , HttpResponse
import json , datetime
from django.db.models import  Q
import os
from .forms import NewLCDetailsForm
from .add530hrs import add530hrstoDateString
from poolaccounts.settings import base_dir
from django.core.exceptions import ValidationError
from django.db import IntegrityError
from rest_framework import status

def getUtilBasicDetails(request):
    try:
        in_data = json.loads(request.body)
        basic_details_lst = list(Registration.objects.filter(Q(fin_code = in_data['fincode']) , ( Q(end_date__isnull = True) | Q(end_date__gte = datetime.datetime.today() ))).values('fees_charges_name','entity_type','l1_phone','l2_phone','l1_mail','l2_mail'))
        details_dict = {
                'Entity Name' : 'No details found' ,
                'Entity Type' : '',
                'L1 Phone' : '' ,
                'L2 Phone' : '' ,
                'L1 Mail' : '',
                'L2 Mail' : '',
            }
        
        if len(basic_details_lst):
            details_dict = {
                'Entity Name' : basic_details_lst[0]['fees_charges_name'] ,
                'Entity Type' : basic_details_lst[0]['entity_type'] ,
                'L1 Phone' : basic_details_lst[0]['l1_phone'] ,
                'L2 Phone' : basic_details_lst[0]['l2_phone'] ,
                'L1 Mail' : basic_details_lst[0]['l1_mail'] ,
                'L2 Mail' : basic_details_lst[0]['l2_mail'] ,
            }

        bank_details_lst = list(BankDetails.objects.filter(Q(fin_code_fk__fin_code = in_data['fincode']) , ( Q(end_date__isnull = True) | Q(end_date__gte = datetime.datetime.today() ))).values('bank_account','beneficiary_name','bank_name','ifsc_code','pan_card','gst'))
        details_dict1 = {
                'Account No' : 'No details found' ,
                'Beneficiary Name' : '',
                'Bank Name' : '' ,
                'IFSC Code' : '' ,
                'PAN No' : '',
                'GSTIN' : '',
            }
        
        if len(bank_details_lst):
            details_dict1 = {
                'Account No' : bank_details_lst[0]['bank_account'] ,
                'Beneficiary Name' :  bank_details_lst[0]['beneficiary_name'],
                'Bank Name' :  bank_details_lst[0]['bank_name'] ,
                'IFSC Code' :  bank_details_lst[0]['ifsc_code'] ,
                'PAN No' :  bank_details_lst[0]['pan_card'],
                'GSTIN' :  bank_details_lst[0]['gst'],
            }

        return JsonResponse([details_dict , details_dict1 ], safe=False)
    except Exception as e:
        return JsonResponse([details_dict , details_dict1 ], safe=False)
  
def getLCDetails(request):
    try:
        fin_code = request.body.decode('utf-8')
        lc_details = list(LCDetails.objects.filter(fincode = fin_code).all().values())
        return JsonResponse(lc_details, safe=False)
    except Exception as e:
        return JsonResponse([] , safe=False)


def saveLCDetails(request):
    try:
        formdata=json.loads(request.POST['formdata'])
        # add 5:30 hrs to startdate and end date
        date_of_issue = add530hrstoDateString(formdata['date_of_issue'].replace('"','')).date()
        if formdata['date_of_expiry'] is not None:
                end_date = add530hrstoDateString(formdata['date_of_expiry'].replace('"','')).date()
                formdata['date_of_expiry']=end_date 

        #changing the date format
        formdata['date_of_issue']=date_of_issue  
        
        # write the files into folder
        parent_folder = os.path.abspath(os.path.join(base_dir, os.pardir))
        directory = os.path.join(parent_folder, 'Files', 'LCDocs' , formdata['username'])
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

                short_path='\\Files\\LCDocs\\'+formdata['username']+'\\'+fl.name
                all_file_paths.append(short_path)
        # change the supporting docs filenames
        formdata['supporting_docs'] = all_file_paths
        del formdata['username']
        form = NewLCDetailsForm(formdata)
        if form.is_valid():
                LCDetails.objects.create(**form.cleaned_data)
                return JsonResponse('success',safe=False)
        else:
                return HttpResponse(form.errors['__all__'] , status=status.HTTP_400_BAD_REQUEST)
            
    except (IntegrityError, ValidationError) as e:
        return HttpResponse(str(e),status=status.HTTP_400_BAD_REQUEST)
  