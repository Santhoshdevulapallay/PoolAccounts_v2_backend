from dsm.common import add530hrstoDateString, getFincode, getWRERCodes
from dsm.common import getWeekDates
from registration.extarctdb_errors import extractdb_errormsg
from .models import *
from django.core.exceptions import ValidationError
from django.db import IntegrityError
from django.http import HttpResponse , JsonResponse
import json ,os ,pandas as pd
import decimal 
from datetime import datetime , timedelta ,time
import numbers ,numpy as np

def currencyInIndiaFormat(n):
      d = decimal.Decimal(str(n))
      if d.as_tuple().exponent < -2:
            s = str(n)
      else:
            s = '{0:.2f}'.format(n)
            l = len(s)
            i = l-1
            res = ''
            flag = 0
            k = 0
      while i>=0:
            if flag==0:
                  res = res + s[i]
                  if s[i]=='.':
                        flag = 1
            elif flag==1:
                  k = k + 1
                  res = res + s[i]
                  if k==3 and i-1>=0:
                        res = res + ','
                        flag = 2
                        k = 0
            else:
                  k = k + 1
                  res = res + s[i]
                  if k==2 and i-1>=0:
                        res = res + ','
                        flag = 2
                        k = 0
            i = i - 1
      return res[::-1]


def is_number_or_none(value):
      #  returns True if the value is a number
      return isinstance(value, numbers.Number) 

def getIRRevision(request):
      try:
            formdata=json.loads(request.body)['formdata']
            fin_year=formdata['fin_year']
            week_no=formdata['wk_no']
            # always gets the latest record , so that incremental revision works
            temp_ir_qry=list(TemporaryInterRegional.objects.filter(Fin_year=fin_year,Week_no=week_no).order_by('-id')[:1].values('WRWR','ERER','WR_Revision_no','ER_Revision_no'))

            if len(temp_ir_qry):
                  if formdata['ir'] == 'SR-WR':
                        if not is_number_or_none(temp_ir_qry[0]['WRWR']):
                              # no entry found so consider it as zero revision
                              revision_no=temp_ir_qry[0]['WR_Revision_no']
                        else:
                              revision_no=int(temp_ir_qry[0]['WR_Revision_no']) + 1
                  else:
                        # this is for SR-ER
                        if not is_number_or_none(temp_ir_qry[0]['ERER']):
                              revision_no=temp_ir_qry[0]['ER_Revision_no']
                        else:
                              revision_no=int(temp_ir_qry[0]['ER_Revision_no']) + 1

                  return JsonResponse([revision_no , getWeekDates(fin_year,week_no)],safe=False)
            else:
                  return HttpResponse('Interregional values not found as per SRPC itself , Please check first ' , status=404)
      except Exception as e:
            return HttpResponse(extractdb_errormsg(e),status=404)     
      
def InterRegional_Discrpancy_WR(path,fin_year,week_no):
      try:
            # get weekstartdate and weekenddate
            week_start_date,week_end_date= getWeekDates(fin_year,week_no)

            df_wr = pd.read_csv(path+"\\WR.csv")[['Date','Time','Actual (MWH)','Schedule (MWH)','DSM Payable (Rs.)','DSM Receivable (Rs.)']]
           
            df_wr.columns = ['date','time','actual','schedule','DSM Payable (Rs.)','DSM Receivable (Rs.)']
            # df_wr['date'] = pd.to_datetime(df_wr['date'])
            df_wr['time'] = pd.to_datetime(df_wr['time'],format='%H:%M').dt.time

            # this comes one directory backward
            parent_directory = os.path.dirname(path)
           
            df_sr = pd.read_csv(parent_directory+"\\Zip_Data\\commercial_dev2022_interregional.csv")[['date','time','sch_wr','wr_act','dev_wr_rs','sch_er','er_act','dev_er_rs']]
            # df_sr['date'] = pd.to_datetime(df_sr['date'])
            df_sr['time'] = pd.to_datetime(df_sr['time'],format='%H:%M:%S').dt.time

            #------main table-----------------#
            df_disc = pd.DataFrame()
            week_header =str(week_no) +"( "+ week_start_date.strftime("%d-%m-%Y") + " to "+ week_end_date.strftime("%d-%m-%Y")+ " )"

            df_disc.at[0,'Week Peiod'] = week_header
            df_disc.at[0,'Amount payable as per SRPC'] = '₹ '+currencyInIndiaFormat(round(abs(df_sr['dev_wr_rs'].sum()),2))
            df_disc.at[0,'Amount payable as per RPC'] = '₹ '+currencyInIndiaFormat(round(abs((df_wr['DSM Payable (Rs.)'].sum()) - (df_wr['DSM Receivable (Rs.)'].sum())),2))

            df_disc.at[0,'Difference (in Rs.)'] = '₹ '+currencyInIndiaFormat(abs(round(abs(df_sr['dev_wr_rs'].sum())-abs((df_wr['DSM Payable (Rs.)'].sum()) - (df_wr['DSM Receivable (Rs.)'].sum())),2)))

            if abs(round(abs(df_sr['dev_wr_rs'].sum())-abs((df_wr['DSM Payable (Rs.)'].sum()) - (df_wr['DSM Receivable (Rs.)'].sum())),2)) > int(20000) :
                  df_disc.at[0,'Remarks'] = ' Difference in blocks attached in this mail'
            else :
                  df_disc.at[0,'Remarks'] = 'No Mismatch'

            #---checking discrepancy------------#
            df_discrepancy = pd.DataFrame()
            
            if abs(round(abs(df_sr['dev_wr_rs'].sum())-abs((df_wr['DSM Payable (Rs.)'].sum()) - (df_wr['DSM Receivable (Rs.)'].sum())),2)) > int(20000) :
                  df = pd.merge(df_sr,df_wr,on=['date','time'])
                  df['Difference of actuals'] = round(abs(df['wr_act']) - abs(df['actual']),2)
                  df['Difference of schedules'] = round(abs(df['sch_wr']) - abs(df['schedule']),2)
                  df_discrepancy = df[(abs(df['Difference of actuals']) > abs(5)) |(abs(df['Difference of schedules']) > abs(5))][['date','time','sch_wr','wr_act','actual','schedule','Difference of actuals','Difference of schedules']]
                  df_discrepancy.columns = ['Date',"Block",'Schedule (MWH) as per SRPC','Actuals (MWH) as per SRPC','Actuals (MWH) as per WRPC','Schedule (MWH) as per WRPC','Difference of Actuals (MWH)','Difference of schedules (MWH)']
                  df_discrepancy['Schedule (MWH) as per SRPC'] = round(df_discrepancy['Schedule (MWH) as per SRPC'],2)
                  df_discrepancy['Actuals (MWH) as per SRPC'] = round(df_discrepancy['Actuals (MWH) as per SRPC'],2)
                  df_discrepancy['Schedule (MWH) as per WRPC'] = round(df_discrepancy['Schedule (MWH) as per WRPC'],2)
                  df_discrepancy['Actuals (MWH) as per WRPC'] = round(df_discrepancy['Actuals (MWH) as per WRPC'],2)


            return df_disc , df_discrepancy
      except Exception as e:
            extractdb_errormsg(str(e))


def InterRegional_Discrpancy_ER(path,fin_year,week_no):
      try:
            # get weekstartdate and weekenddate
            week_start_date,week_end_date= getWeekDates(fin_year,week_no)

            parent_directory = os.path.dirname(path)
           
            df_sr = pd.read_csv(parent_directory+"\\Zip_Data\\commercial_dev2022_interregional.csv")[['date','time','sch_wr','wr_act','dev_wr_rs','sch_er','er_act','dev_er_rs']]
            # df_sr['date'] = pd.to_datetime(df_sr['date'])
            df_sr['time'] = pd.to_datetime(df_sr['time'] ,format='%H:%M:%S').dt.time
           
            df_er = pd.read_excel(path+"\\ER.xlsx",sheet_name='SR',skiprows=3)[['Date','Time','Block','Actual (MWH)','Schedule (MWH)','DSM Payable (Rs.)','DSM Receivable (Rs.)']]
            df_er.columns = ['date','time','block','actual','schedule','DSM Payable (Rs.)','DSM Receivable (Rs.)']
            df_er = df_er.dropna(subset=['time']).reset_index()
            
            for i in range(0,df_er.shape[0]):
                  if  int(df_er.loc[i,'block']) == 1 :
                        df_er.loc[i,'time'] = (datetime.combine(datetime.today(),time(0,0,0))).time()
                  else:
                        df_er.loc[i,'time'] = (datetime.combine(datetime.today(),df_er.loc[i-1,'time'])+timedelta(minutes=15)).time()
            # df_er['date'] = pd.to_datetime(df_er['date'])
            week_header =str(week_no) +"( "+ week_start_date.strftime("%d-%m-%Y") + " to "+ week_end_date.strftime("%d-%m-%Y")+ " )"
            
            #----------main table------------------#
            df_disc_er = pd.DataFrame()
            df_disc_er.at[0,'Week Peiod'] = week_header
            df_disc_er.at[0,'Amount payable as per SRPC'] = '₹ '+currencyInIndiaFormat(round(abs(df_sr['dev_er_rs'].sum()),2))
            df_disc_er.at[0,'Amount payable as per RPC'] = '₹ '+currencyInIndiaFormat(round(abs((df_er['DSM Payable (Rs.)'].sum()) - (df_er['DSM Receivable (Rs.)'].sum())),2))
            df_disc_er.at[0,'Difference (in Rs.)'] ='₹ '+currencyInIndiaFormat(abs(round(abs(df_sr['dev_er_rs'].sum())-abs((df_er['DSM Payable (Rs.)'].sum()) - (df_er['DSM Receivable (Rs.)'].sum())),2)))
            if abs(round(abs(df_sr['dev_er_rs'].sum())-abs((df_er['DSM Payable (Rs.)'].sum()) - (df_er['DSM Receivable (Rs.)'].sum())),2)) > int(20000) :
                  df_disc_er.at[0,'Remarks'] = ' Difference in blocks attached in this mail'
            else :
                  df_disc_er.at[0,'Remarks'] = 'No Mismatch'

            
            #---------checking discrepancy------------#
            df_discrepancy_er = pd.DataFrame()
            if abs(round(abs(df_sr['dev_er_rs'].sum())-abs((df_er['DSM Payable (Rs.)'].sum()) - (df_er['DSM Receivable (Rs.)'].sum())),2)) > int(20000) :
                  df = pd.merge(df_sr,df_er,on=['date','time'])
                  df['Difference of actuals'] = round(abs(df['er_act']) - abs(df['actual']),2)
                  df['Difference of schedules'] = round(abs(df['sch_er']) - abs(df['schedule']),2)
                  df_discrepancy_er = df[(abs(df['Difference of actuals']) > abs(5)) |(abs(df['Difference of schedules']) > abs(5))][['date','time','sch_er','er_act','actual','schedule','Difference of actuals','Difference of schedules']]
                  df_discrepancy_er.columns = ['Date',"Block",'Schedule (MWH) as per SRPC','Actuals (MWH) as per SRPC','Actuals (MWH) as per ERPC','Schedule (MWH) as per ERPC','Difference of Actuals (MWH)','Difference of schedules (MWH)']
                  df_discrepancy_er['Schedule (MWH) as per SRPC'] = round(df_discrepancy_er['Schedule (MWH) as per SRPC'],2)
                  df_discrepancy_er['Actuals (MWH) as per SRPC'] = round(df_discrepancy_er['Actuals (MWH) as per SRPC'],2)
                  df_discrepancy_er['Schedule (MWH) as per ERPC'] = round(df_discrepancy_er['Schedule (MWH) as per ERPC'],2)
                  df_discrepancy_er['Actuals (MWH) as per ERPC'] = round(df_discrepancy_er['Actuals (MWH) as per ERPC'],2)

            return df_disc_er , df_discrepancy_er
      
      except Exception as e:
            extractdb_errormsg(str(e))

def checkInterRegional(request):
      try:
            formdata=json.loads(request.POST['formdata'])
            fin_year=formdata['fin_year']
            week_no=formdata['wk_no']
            file=request.FILES['files']
            # get the path from database
            year_obj=YearCalendar.objects.filter(fin_year=fin_year ,week_no=week_no ,srpc_fetch_status=True).values_list('folder_path' ,flat=True)
            
            if len(year_obj)>0:
                  # actually WR sending .csv file and ER sending .xlsx files
                  if formdata['ir'] == 'SR-WR':
                        ir_folder_name = 'WR' 
                        df=pd.read_csv(request.FILES['files'])
                        folder_path=year_obj[0]+'\\'+ir_folder_name
                        
                        # store the file in given location
                        if not os.path.exists(folder_path):
                              # Create the directory if it doesn't exist
                              os.makedirs(folder_path)

                        # renaming the original file name with folder name 
                        file_path=os.path.join(folder_path , ir_folder_name+'.csv')
                        with open(file_path, 'wb+') as destination:
                              for chunk in file.chunks():
                                    destination.write(chunk)
                        payable_amt=0
                        receivable_amt=0
                        
                        if not df.empty:
                              df['DSM Payable (Rs.)'] = pd.to_numeric(df['DSM Payable (Rs.)'], errors='coerce')
                              df['DSM Receivable (Rs.)'] = pd.to_numeric(df['DSM Receivable (Rs.)'], errors='coerce')
                              # Summing up the column
                              payable_amt = df['DSM Payable (Rs.)'].dropna().sum()
                              receivable_amt = df['DSM Receivable (Rs.)'].dropna().sum()

                        
                        df_disc , df_blockwise =InterRegional_Discrpancy_WR(folder_path,fin_year,week_no)
                  else:
                        ir_folder_name = 'ER' 
                        # df=pd.read_excel(request.FILES['files'])
                        folder_path=year_obj[0]+'\\'+ir_folder_name
                        # store the file in given location
                        if not os.path.exists(folder_path):
                              # Create the directory if it doesn't exist
                              os.makedirs(folder_path)

                        # renaming the original file name with folder name 
                        file_path=os.path.join(folder_path , ir_folder_name+'.xlsx')
                        with open(file_path, 'wb+') as destination:
                              for chunk in file.chunks():
                                    destination.write(chunk)
                        
                        df=pd.read_excel(file_path,sheet_name='SR',skiprows=3)[['Date','Time','Block','Actual (MWH)','Schedule (MWH)','DSM Payable (Rs.)','DSM Receivable (Rs.)']]
                        
                        payable_amt=0
                        receivable_amt=0
                        if not df.empty:
                              df = df.dropna(subset=['Time']).reset_index()
                              df['DSM Payable (Rs.)'] = pd.to_numeric(df['DSM Payable (Rs.)'], errors='coerce')
                              df['DSM Receivable (Rs.)'] = pd.to_numeric(df['DSM Receivable (Rs.)'], errors='coerce')
                              # Summing up the column
                              payable_amt = df['DSM Payable (Rs.)'].dropna().sum()
                              receivable_amt = df['DSM Receivable (Rs.)'].dropna().sum()
                        # it returns two dfs 1) df_discrepancy 2) df_discrepncy_blockwise
                        df_disc , df_blockwise = InterRegional_Discrpancy_ER(folder_path,fin_year,week_no)
                      
            else:
                  return HttpResponse('Folder not created and path found to store '+formdata['ir']+' File , First fetch from SRPC ' , status=404)

            # converting numpy values to float values because of json serialization error
            payable_amt = payable_amt.tolist() if isinstance(payable_amt, np.int64) else payable_amt
            receivable_amt = receivable_amt.tolist() if isinstance(receivable_amt, np.int64) else receivable_amt

            return JsonResponse([payable_amt , receivable_amt , df_disc.to_dict(orient='records') ],safe=False)
      
      except Exception as e:
            return HttpResponse(extractdb_errormsg(e),status=404)
      
def  storeInterregionalFinal(formdata,week_start_date,week_end_date):
      try:
            fin_year=formdata['fin_year']
            week_no=formdata['wk_no']
            # first get the values from TemporaryInterRegional i.e) WR(as per srpc) and ER(as per srpc)
            temp_ir_qry=TemporaryInterRegional.objects.filter( Fin_year=fin_year,
                        Week_no=week_no)
            wr_fin_code,wr_dsm_name,er_fin_code,er_dsm_name=getWRERCodes()
            dsm_model_qry=IRBaseModel.objects.filter(Fin_year=fin_year,
                              Week_no=week_no)
            full_responses=[]

            if formdata['ir'] == 'SR-WR':
                  # always take the latest revision values
                  temp_ir_qry=temp_ir_qry.filter(WR_Revision_no=formdata['revision_no']).order_by('-WR_Revision_no')[:1].values('WRSR','WRWR')
                  # check Western Region as per WRPC <0 
                  if temp_ir_qry[0]['WRWR'] <0:
                        wr_final_value = temp_ir_qry[0]['WRWR']*-1
                  elif temp_ir_qry[0]['WRSR'] <= 0:
                        wr_final_value = temp_ir_qry[0]['WRSR']
                  else:
                        wr_final_value =None
                  wr_payrcv= 'Receivable' if wr_final_value <0 else 'Payable'

                  if dsm_model_qry.filter(Entity=wr_dsm_name).count() < 1:
                              # No entry found
                              IRBaseModel(
                                    Fin_year=fin_year,
                                    Week_no=week_no,
                                    Week_startdate=week_start_date,
                                    Week_enddate=week_end_date,
                                    Entity=wr_dsm_name,
                                    Final_charges=abs(wr_final_value),
                                    Fin_code=wr_fin_code,
                                    PayableorReceivable=wr_payrcv,
                                    Revision_no=0
                              ).save()
                              full_responses.append('WR Bill Submitted for the fin year  '+fin_year +'- and week no '+week_no+ ' , Please check ' )
                  else:
                        IRBaseModel.objects.filter(
                                    Fin_year=fin_year,
                                    Week_no=week_no, Entity=wr_dsm_name).update(Final_charges=abs(wr_final_value),
                                    PayableorReceivable=wr_payrcv)
                        full_responses.append('WR Bills Already Submitted , but replaced with existing value' )

            elif formdata['ir'] == 'SR-ER':
                  temp_ir_qry=temp_ir_qry.filter(ER_Revision_no=formdata['revision_no']).order_by('-ER_Revision_no')[:1].values('ERSR','ERER')
                  # check Western Region as per WRPC <0 
                  if temp_ir_qry[0]['ERSR'] <0:
                        er_final_value = temp_ir_qry[0]['ERSR']
                  elif temp_ir_qry[0]['ERER'] <= 0:
                        er_final_value = temp_ir_qry[0]['ERER']*-1
                  else:
                        er_final_value =None
                  er_payrcv= 'Receivable' if er_final_value <0 else 'Payable'      

                  if dsm_model_qry.filter(Entity=er_dsm_name).count() < 1:
                              # No entry found
                              IRBaseModel(
                                    Fin_year=fin_year,
                                    Week_no=week_no,
                                    Week_startdate=week_start_date,
                                    Week_enddate=week_end_date,
                                    Entity=er_dsm_name,
                                    Final_charges=abs(er_final_value),
                                    Fin_code=er_fin_code,
                                    PayableorReceivable=er_payrcv,
                                    Revision_no=0
                              ).save()
                              full_responses.append('ER Bill Submitted for the fin year  '+fin_year +'- and week no '+week_no )
                  else:
                        IRBaseModel.objects.filter(
                                    Fin_year=fin_year,
                                    Week_no=week_no, Entity=wr_dsm_name).update(Final_charges=abs(er_final_value),
                                    PayableorReceivable=er_payrcv)
                        full_responses.append('ER Bills Already Submitted , but replaced with existing value' )
            else: pass
            # send mail consider at last
            return full_responses

      except Exception as e:
            extractdb_errormsg(e)
            return full_responses.append(str(e))
        
def storeIR(request):
      try:
            formdata=json.loads(request.body)['formdata']
            fin_year=formdata['fin_year']
            week_no=formdata['wk_no']
            mutiplication_factor= 1 if formdata['pay_rcv'] == 'Payable' else -1
            amount_to_store = float(formdata['amt_rpc'])*mutiplication_factor
            # get weekstartdate and week enddate
            yr_cal_qry=list(YearCalendar.objects.filter(fin_year =fin_year , week_no = week_no).values_list('start_date' , 'end_date'))
            
            if len(yr_cal_qry):
                  week_start_date =yr_cal_qry[0][0]
                  week_end_date =yr_cal_qry[0][1]
            else:
                  week_start_date=None
                  week_end_date=None

            if formdata['ir'] == 'SR-WR':
                  # if revision_no is zero then update else create a new record
                  if formdata['revision_no'] == 0:
                        # now update this value into database
                        TemporaryInterRegional.objects.filter(
                              Fin_year=fin_year,
                              Week_no=week_no,
                              WR_Revision_no=0
                              ).update(WRWR=amount_to_store) 
                  else:
                        # this is to get the values of SRPC to create new record and also Adding extra WRWR and WR_Revision_no
                        old_temp_ir_qry=list(TemporaryInterRegional.objects.filter(
                              Fin_year=fin_year,Week_no=week_no , WR_Revision_no = (formdata['revision_no']-1) ).order_by('-id')[:1].values('Fin_year','Week_no','WRSR','ERSR','ERER','ER_Revision_no'))
                        if len(old_temp_ir_qry):
                              TemporaryInterRegional(
                                    Fin_year=fin_year, Week_no=week_no, WRSR=old_temp_ir_qry[0]['WRSR'],ERSR=old_temp_ir_qry[0]['ERSR'] , WRWR=amount_to_store, ERER=old_temp_ir_qry[0]['ERER'],
                                    WR_Revision_no=formdata['revision_no'] , ER_Revision_no=old_temp_ir_qry[0]['ER_Revision_no']
                              ).save()
                        else:
                              return HttpResponse('WR as per SRPC and ER as per SRPC values are not found')
            else:
                  # if revision_no is zero then update else create a new record and  Adding extra ERER and ER_Revision_no
                  if formdata['revision_no'] ==0:
                        # now update this value into database
                        TemporaryInterRegional.objects.filter(
                              Fin_year=fin_year,
                              Week_no=week_no,
                              ER_Revision_no=0
                              ).update(ERER=amount_to_store) 
                  else:
                        # this is to get the values of SRPC to create new record
                        old_temp_ir_qry=list(TemporaryInterRegional.objects.filter(
                              Fin_year=fin_year,Week_no=week_no ,ER_Revision_no =(formdata['revision_no']-1)).order_by('-id')[:1].values('Fin_year','Week_no','WRSR','WRWR','ERSR','WR_Revision_no'))
                   
                        if len(old_temp_ir_qry):
                              TemporaryInterRegional(
                                    Fin_year=fin_year, Week_no=week_no, 
                                    WRSR=old_temp_ir_qry[0]['WRSR'],ERSR=old_temp_ir_qry[0]['ERSR'] , 
                                    WRWR=old_temp_ir_qry[0]['WRWR'] , 
                                    ERER=amount_to_store , 
                                    WR_Revision_no=old_temp_ir_qry[0]['WR_Revision_no'] ,ER_Revision_no=formdata['revision_no']
                              ).save()
                        else:
                              return HttpResponse('WR as per SRPC and ER as per SRPC values are not found')
             
            responses=storeInterregionalFinal(formdata,week_start_date,week_end_date)

            return JsonResponse(responses,safe=False)
      
      except Exception as e:
            return HttpResponse(extractdb_errormsg(e),status=404)

def getWRValues(interregional):
      # check Western Region as per WRPC <0 
      if interregional['WRWR'] <0:
            wr_final_value = interregional['WRWR']*-1
      elif interregional['WRSR'] <= 0:
            wr_final_value = interregional['WRSR']
      else:
            wr_final_value =None
      wr_payrcv= 'Receivable' if wr_final_value <0 else 'Payable'

      return wr_final_value , wr_payrcv

def getERValues(interregional):
      # same way do for ER 
      if interregional['ERSR'] <0:
            er_final_value = interregional['ERSR']
      elif interregional['ERER'] <= 0:
            er_final_value = interregional['ERER']*-1
      else:
            er_final_value =None

      er_payrcv= 'Receivable' if er_final_value <0 else 'Payable'      
      return er_final_value , er_payrcv

def storeNLDCIntimatedIRBill(request):
      try:
            formdata = json.loads(request.body)
            
            fin_year=formdata['fin_year']
            week_no=formdata['wk_no']
            entity=formdata['entity']
            letter_date=add530hrstoDateString(formdata['letter_date']).date()
            
            duedate = letter_date + timedelta(days=10)
            
            # get the fincode
            fincode = getFincode(entity)
            LegacyBaseModel(
                  Fin_year=fin_year,
                  Week_no= week_no,
                  Letter_date=letter_date,
                  Due_date=duedate,
                  Entity=entity,
                  Final_charges=formdata['final_charges'] ,
                  PayableorReceivable=formdata['pr'],
                  Remarks=formdata['remarks'],
                  Fin_code=fincode,
                  Is_interregional = True ,
                  Is_disbursed=False , 
                  Effective_start_date= letter_date ,
                  Legacy_dues=True
            ).save()

            return JsonResponse( "success" , safe=False)

      except Exception as e:
            print(e)
            return HttpResponse(extractdb_errormsg(e),status=404)

# def storeInterregional(request):
#       try:
#             formdata=json.loads(request.body)
#             fin_year=formdata['Fin_year']
#             week_no=formdata['Week_no']
#             # get weekstartdate and week enddate
#             yr_cal_qry=list(YearCalendar.objects.filter(fin_year =fin_year , week_no = week_no).values_list('start_date' , 'end_date'))
            
#             if len(yr_cal_qry):
#                   week_start_date =yr_cal_qry[0][0]
#                   week_end_date =yr_cal_qry[0][1]
#             else:
#                   week_start_date=None
#                   week_end_date=None

#             wr_final_value , wr_payrcv = getWRValues(formdata)
#             er_final_value , er_payrcv = getERValues(formdata)
#             wr_fin_code,wr_dsm_name,er_fin_code,er_dsm_name=getWRERCodes()
#             dsm_model_qry=DSMBaseModel.objects.filter(Fin_year=fin_year,
#                               Week_no=week_no)
#             full_responses=[]
#             if dsm_model_qry.filter(Entity=wr_dsm_name).count() < 1:
#                         # No entry found
#                         DSMBaseModel(
#                               Fin_year=fin_year,
#                               Week_no=week_no,
#                               Week_startdate=week_start_date,
#                               Week_enddate=week_end_date,
#                               Entity=wr_dsm_name,
#                               Final_charges=wr_final_value,
#                               Fin_code=wr_fin_code,
#                               PayableorReceivable=wr_payrcv,
#                               Revision_no=0
#                         ).save()
#                         full_responses.append('WR Bill Submitted for the fin year  '+fin_year +'- and week no '+week_no+ ' , Please check ' )
#             else:
#                   full_responses.append('WR Bills Submitted Successfully' )

#             if dsm_model_qry.filter(Entity=er_dsm_name).count() < 1:
#                   DSMBaseModel(
#                         Fin_year=fin_year,
#                         Week_no=week_no,
#                         Week_startdate=week_start_date,
#                         Week_enddate=week_end_date,
#                         Entity=er_dsm_name,
#                         Final_charges=er_final_value,
#                         Fin_code=er_fin_code,
#                         PayableorReceivable=er_payrcv,
#                         Revision_no=0
#                   ).save()
#                   full_responses.append('ER Bills Submitted Successfully')
#             else:
#                   full_responses.append('ER value already exists for the fin year  '+fin_year +'- and week no'+week_no+ ' , Please check')

#             return JsonResponse(full_responses,safe=False)
      
#       except Exception as e:
#             return HttpResponse(extractdb_errormsg(e),status=404)
    
