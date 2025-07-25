
from dsm.common import _create_columns , srpc_file_names,month_name_dict
from registration.fetch_data import getFCNames
from registration.models import YearCalendar
from registration.extarctdb_errors import extractdb_errormsg
from .models import *
from django.core.exceptions import ValidationError
from django.db import IntegrityError
from django.http import HttpResponse , JsonResponse
from rest_framework import status
import pandas as pd
import json ,os
from datetime import timedelta
from zipfile import ZipFile
from urllib3.exceptions import InsecureRequestWarning
import requests 
from urllib3 import disable_warnings
import time,shutil
from registration.custom_paths import week_proof_path 
import datetime
from django.db.models import Q
from .engine_create import *
from .interregional import *
from .bill_submission import *
from .viewbills import *
from .bankstmt import *
from .disburse import *
from .readcsv import *
from .reports import *
from .interest_bills import *
from .revisions import *
from .surplus import *
from .finance_reports import *
from .excess_fc import *
from .mail import *
from .reconciliation import *
from .shortfall_bills import *
from .scuc_cc import *
from .user_recon import *

regions=['Southern Region to Western Region', 'Western Region to Southern Region', 'Southern Region to Eastern Region', 'Eastern Region to Southern Region ']



def fetchSRPCBills(request):
      try:
            disable_warnings(InsecureRequestWarning)
            request_data=json.loads(request.body)

            week_no=request_data['formdata']['wk_no']
            fin_year=request_data['formdata']['fin_year']
           
            year_qry=YearCalendar.objects.filter(fin_year= fin_year,week_no=week_no )

            if year_qry.count() > 0 :
                  if year_qry[0].srpc_fetch_status:
                       return JsonResponse("Already Fetched , Please check",safe=False) 
                  start_date=year_qry[0].start_date
            else:
                  return JsonResponse(f"Start date not found for the week {week_no} ",safe=False)
            
            end_date=year_qry[0].end_date
            only_year=str(fin_year[:4])
            # letter date is to download .zip file from srpc website
            letter_date=(end_date+timedelta(days=1))
            parts = fin_year.split('-')
            prefix = parts[0][:2]  # '20'
            next_year_suffix = parts[1]  # '25'
            only_year2 = prefix + next_year_suffix
            
            file_start_date_str=start_date.strftime('%d')
            # this end date is for local folder
            file_end_date_str=end_date.strftime('%d%B%y') 
            
            # this name is to match srpc filename line 01-08jan24

            filename_end_date=end_date.strftime('%d')+str ( month_name_dict[end_date.strftime('%b').lower()] ) + str(end_date)[2:4]

            path = "srpc_folder" + "\\"+fin_year+"\\Week_"+fin_year.replace('-','_') +"_Proof\\Week_no_"+str(week_no)+"_"+str(file_start_date_str)+"_"+str(file_end_date_str)

            if not os.path.exists(path):
                  os.makedirs(path)
            else:
                  # if folder already exists then return
                  return JsonResponse("Folder already exists in the location , Please check " + path ,safe=False)


            try :
                  # get only_year from current financial year
                  #-------------zip------------#
                  url2 = str("https://www.srpc.kar.nic.in/website/")+only_year+str("/commercial/")+str(letter_date.strftime('%d%m%y'))+str(".zip")
                  response = requests.get(url2,verify=False)
                  if response.status_code == 404 :
                        url2 = str("https://www.srpc.kar.nic.in/website/")+only_year2+str("/commercial/")+str(letter_date.strftime('%d%m%y'))+str(".zip")
                        response = requests.get(url2,verify=False)

                  
                  # if response is empty then delete the created folder
                  file_path = path + '\\'+str(end_date)+".zip"
                  with open(file_path, 'wb') as file:
                        file.write(response.content)

                  ###-----------DSM PDF----------------- #
                  url1 = str("https://www.srpc.kar.nic.in/website/")+only_year+str("/commercial/dsm")+file_start_date_str+"-"+filename_end_date+str(".pdf")
                  response1 = requests.get(url1,verify=False)
                  if response1.status_code == 404 :
                        url1 = str("https://www.srpc.kar.nic.in/website/")+only_year2+str("/commercial/dsm")+file_start_date_str+"-"+filename_end_date+str(".pdf")
                        response1 = requests.get(url1,verify=False)
                  
                  
                  file_path1 = path + '\\dsm'+str(file_start_date_str)+"-"+str(filename_end_date)+".pdf"
                  with open(file_path1, 'wb') as file:
                        file.write(response1.content)
                  
                  ###-----------RRAS PDF-------------#
                  url3 = str("https://www.srpc.kar.nic.in/website/")+only_year+str("/commercial/as")+file_start_date_str+"-"+filename_end_date+str(".pdf")
                  response2 = requests.get(url3,verify=False)
                  if response2.status_code == 404 :
                        url3 = str("https://www.srpc.kar.nic.in/website/")+only_year2+str("/commercial/as")+file_start_date_str+"-"+filename_end_date+str(".pdf")
                        response2 = requests.get(url3,verify=False)

                  
                  file_path2 = path + '\\rras'+str(file_start_date_str)+"-"+str(filename_end_date)+".pdf"
                  with open(file_path2, 'wb') as file:
                        file.write(response2.content)
                  
                  
                  ###-----------Reactive PDF-------------#
                  url4 = str("https://www.srpc.kar.nic.in/website/")+only_year+str("/commercial/reac")+file_start_date_str+"-"+filename_end_date+str(".pdf")
                  response3 = requests.get(url4,verify=False)
                  if response3.status_code == 404 :
                        url4 = str("https://www.srpc.kar.nic.in/website/")+only_year2+str("/commercial/reac")+file_start_date_str+"-"+filename_end_date+str(".pdf")
                        response3 = requests.get(url4,verify=False)

                  
                  file_path3 = path + '\\react'+str(file_start_date_str)+"-"+str(filename_end_date)+".pdf"
                  with open(file_path3, 'wb') as file:
                        file.write(response3.content)
                  
                  #-------------unzip and saving------------------#
                  file_name = path+"\\"+str(end_date)+".zip"
                  with ZipFile(file_name, 'r') as zip:
                        zip.extractall(path)
                  
                  # now take the DSM File and store it in database
                  # Here update the SRPC fetched time
                  year_qry.update(
                        srpc_fetch_status=True,
                        fetched_time=datetime.now(),
                        folder_path=path
                  )
                  return JsonResponse('All fetched Successfully', safe=False)
            
            except Exception as e:
                  shutil.rmtree(path)
                  return HttpResponse(extractdb_errormsg(e),status=404)
      
      except Exception as e:
            shutil.rmtree(path)
            return HttpResponse(extractdb_errormsg(e),status=404)

def uploadRPCBillManually(request):
      try:
            disable_warnings(InsecureRequestWarning)
            # if multiple files uploads like ds, sras , mbas ..
            files = request.FILES.getlist('files') 
            fin_year = ast.literal_eval(request.POST['fin_year']) 
            week_no = ast.literal_eval(request.POST['wk_no']) 
            year_qry=YearCalendar.objects.filter(fin_year= fin_year,week_no=week_no )

            if year_qry.count() > 0 :
                  if year_qry[0].srpc_fetch_status:
                       return JsonResponse("Already Uploaded , Please check",safe=False) 
                  start_date=year_qry[0].start_date
            else:
                  return JsonResponse(f"Start date not found for the week {week_no} ",safe=False)
            
            end_date=year_qry[0].end_date
            
            file_start_date_str=start_date.strftime('%d')
            # this end date is for local folder
            file_end_date_str=end_date.strftime('%d%B%y') 
            
            path = "srpc_folder" + "\\"+fin_year+"\\Week_"+fin_year.replace('-','_') +"_Proof\\Week_no_"+str(week_no)+"_"+str(file_start_date_str)+"_"+str(file_end_date_str) +'\\Zip_Data\\' 

            if not os.path.exists(path):
                  os.makedirs(path)
            else:
                  # if folder already exists then return
                  return JsonResponse("Folder already exists in the location , Please check " + path ,safe=False)
            
            for fl in files:
                  file_path = path + str(fl.name)
                  with open(file_path, 'wb+') as destination:
                        for chunk in fl.chunks():
                              destination.write(chunk)

            # Here update the all files uploaded path
            # Remove '\Zip_Data\' from the path because it is adding while validating the bill
            cleaned_path = path.replace('\\Zip_Data\\', '\\')
            year_qry.update(
                  srpc_fetch_status=True,
                  fetched_time=datetime.now(),
                  folder_path=cleaned_path
            )
            return JsonResponse('Uploaded Successfully', safe=False)
      except Exception as e:
            return HttpResponse(extractdb_errormsg(e),status=404)
   
def srpcFileStatus(request):
      try:
            formdata=json.loads(request.body)
            all_status_dict={
                  'dsm':False,
                  'sras':False,
                  'tras':False,
                  'mbas':False,
                  'reac':False,
                  'scuc':False,
                  'cong':False
            }
            year_cal_qry=list(YearCalendar.objects.filter(fin_year=formdata['fin_year'],week_no=formdata['wk_no']).values('dsm_bills_uploaded_status','sras_bills_uploaded_status','tras_bills_uploaded_status','mbas_bills_uploaded_status','reac_bills_uploaded_status','scuc_bills_uploaded_status','cong_bills_uploaded_status'))
       
            if len(year_cal_qry):
                  all_status_dict['dsm']=year_cal_qry[0]['dsm_bills_uploaded_status']
                  all_status_dict['sras']=year_cal_qry[0]['sras_bills_uploaded_status']
                  all_status_dict['tras']=year_cal_qry[0]['tras_bills_uploaded_status']
                  all_status_dict['mbas']=year_cal_qry[0]['mbas_bills_uploaded_status']
                  all_status_dict['reac']=year_cal_qry[0]['reac_bills_uploaded_status']
                  all_status_dict['scuc']=year_cal_qry[0]['scuc_bills_uploaded_status']
                  all_status_dict['cong']=year_cal_qry[0]['cong_bills_uploaded_status']

            return JsonResponse(all_status_dict,safe=False)

      except Exception as e:
            
            return HttpResponse(extractdb_errormsg(e),status=404)

def checkBillValidation(request):
      try:
            request_data=json.loads(request.body)
            week_no=request_data['formdata']['wk_no']
            fin_year=request_data['formdata']['fin_year']
            acc_type=request_data['formdata']['acc_type']
            # get the path
            yrcal_qry=YearCalendar.objects.filter(fin_year=fin_year,week_no=week_no , srpc_fetch_status=True)
            if yrcal_qry.count() < 1:
                  # if not fetched then return the request
                  return JsonResponse("Files not fetched from SRPC Website , Please check and upload again",safe=False) 
            else:
                  temp_path = yrcal_qry.values_list('folder_path')[0][0]
                  # remove one tree node / folder from path , here base_dir ='D:\\PoolAccounts\\Backend\\poolaccounts\\poolaccounts\' removing last poolaccounts folder
                  actual_path=os.path.dirname(base_dir)
                  path=os.path.join(actual_path,temp_path)
                 
           
            if acc_type == 'DSM':
                  not_mapped_entities,infirm_table,no_errors=readDSMFile(path,acc_type,fin_year,week_no)
                  return JsonResponse([not_mapped_entities , getFCNames() ,infirm_table,no_errors], safe=False)
            elif acc_type == 'SRAS':
                  not_mapped_entities,no_errors=readSRASFile(path,acc_type,fin_year,week_no)
                 
            elif acc_type == 'TRAS':
                  not_mapped_entities,no_errors=readTRASFile(path,acc_type,fin_year,week_no)
                  
            elif acc_type == 'MBAS':
                  not_mapped_entities,no_errors=readMBASFile(path,acc_type,fin_year,week_no)
                  
            elif acc_type == 'REAC':
                  not_mapped_entities,no_errors=readREACFile(path,acc_type,fin_year,week_no)
                  
            elif acc_type == 'SCUC':
                  not_mapped_entities,no_errors=readSCUCFile(path,acc_type,fin_year,week_no)

            elif acc_type == 'CONG':
                  not_mapped_entities,no_errors=readCONGFile(path,acc_type,fin_year,week_no)
            else:
                  not_mapped_entities=[]
                  no_errors=True

            return JsonResponse([not_mapped_entities,getFCNames(),[],no_errors ], safe=False)
            
      except Exception as e:
            return HttpResponse(extractdb_errormsg(e),status=404)

def mapBills(request):
      try:
            request_data=json.loads(request.body)
            week_no=request_data['formdata']['wk_no']
            fin_year=request_data['formdata']['fin_year']
            acc_type=request_data['formdata']['acc_type']
            selected_rows=request_data['selected_rows']
          
            temp_obj_qry=TemporaryMatched.objects.filter(Fin_year=fin_year ,Week_no=week_no )
            
            # now store these entities in temporary table
            for row in selected_rows:
                  infirm_bool = True if row['isinfirm'] == 'Y' else False
                  if temp_obj_qry.filter(Entity=row['entity'] , Fin_code=row['selectedOption']).count() <1:
                        # no record found so insert to database
                        TemporaryMatched(
                              Fin_year=fin_year ,
                              Week_no=week_no,
                              Acc_type=acc_type,
                              Entity=row['entity'] , 
                              DevFinal=row['devfinal'],
                              PayRcv=row['payrcv'],
                              Fin_code=row['selectedOption'],
                              Is_infirm=infirm_bool,
                              Revision_no=0
                        ).save()
                  else:
                        extractdb_errormsg(row['entity']+' is already found for the week '+ str(week_no) +' --, Please check')
            return JsonResponse('success',safe=False)
      
      except Exception as e:
            return HttpResponse(extractdb_errormsg(e),status=404)


def getWeekStartEndDates(request):
      try:
            request_data=json.loads(request.body)
            finyear=request_data['finyear']
            weekno=request_data['weekno']

            week_start_date, week_end_date= getWeekDates(finyear,weekno)
            # get the bills uploaded status also
            # first check whether SCUC,SRAS,TRAS and MBAS bills uploaded or not
            get_upload_status=list(YearCalendar.objects.filter(fin_year=finyear,week_no=weekno).values('dsm_bills_uploaded_status','ir_bills_uploaded_status','reac_bills_uploaded_status','netas_bills_uploaded_status','sras_bills_uploaded_status','tras_bills_uploaded_status','mbas_bills_uploaded_status','scuc_bills_uploaded_status'))
            if len(get_upload_status):
                  all_upload_status=get_upload_status
            else:
                 all_upload_status= {'dsm_bills_uploaded_status': False, 'ir_bills_uploaded_status': False, 'reac_bills_uploaded_status': False, 'netas_bills_uploaded_status': False, 'sras_bills_uploaded_status': False, 'tras_bills_uploaded_status': False, 'mbas_bills_uploaded_status': False, 'scuc_bills_uploaded_status': False}

            return JsonResponse([week_start_date, week_end_date],safe=False)
      except Exception as e:
            return HttpResponse(extractdb_errormsg(e),status=404)
      

# def createUsers(request):
#       try:
#             df =  pd.read_excel('users.xlsx')
#             from django.contrib.auth.models import User
            
#             for _, row in df[66:].iterrows():
#                   uu = User.objects.filter(username = row['username'])
#                   if uu.count() > 0 :
#                         print(f"{row['username']} already created")
#                         continue

#                   uu1 = User.objects.create_user(
#                         username=row['username'],
#                         password=row['password']
#                   )
#                   uu1.save()
#                   Registration.objects.filter(fin_code = row['fin_code']).update(username=row['username'])
#                   print(f"{row['username']} new user")
      
#       except Exception as e:
#             print(e)
#             return HttpResponse(extractdb_errormsg(e),status=404)
      