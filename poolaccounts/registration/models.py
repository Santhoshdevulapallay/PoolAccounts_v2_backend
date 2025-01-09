from django.db import models
from django.utils import timezone
# Create your models here.



class Registration(models.Model):
      fin_code=models.CharField(max_length=15,default=None)
      finance_name=models.CharField(max_length=255, default=None)
      fees_charges_name=models.CharField(max_length=255,default=None)
      dsm_name=models.CharField(max_length=255,default=None,blank=True,null=True)
      sras_name=models.CharField(max_length=255,default=None,blank=True,null=True)
      tras_name=models.CharField(max_length=255,default=None,blank=True,null=True)
      react_name=models.CharField(max_length=255,default=None,blank=True,null=True)
      entity_type=models.CharField(max_length=20,default=None,blank=True,null=True)
      start_date=models.DateField(default=None)
      end_date=models.DateField(default=None,blank=True,null=True)
      l1_phone=models.CharField(max_length=12,default=None,blank=True,null=True)
      l2_phone=models.CharField(max_length=12,default=None,blank=True,null=True)   
      l1_mail=models.CharField(max_length=50,default=None,blank=True,null=True)
      l2_mail=models.CharField(max_length=50,default=None,blank=True,null=True)
      is_nclt=models.BooleanField(default=None,blank=True,null=True)
      filename=models.TextField(default=None,blank=True,null=True)
      remarks=models.TextField(default=None,blank=True,null=True)

      def __str__(self):
            return self.fees_charges_name
      
      class Meta:
            managed = True
            db_table = 'registration'
            unique_together=['fin_code','end_date']

class BankDetails(models.Model):
      fin_code_fk=models.ForeignKey(Registration,on_delete=models.SET_NULL,null=True)
      bank_account=models.CharField(default=None,max_length=25 )
      beneficiary_name=models.CharField(default=None,max_length=255,blank=True,null=True )
      bank_name=models.CharField(max_length=255, default=None)
      ifsc_code=models.CharField(max_length=12,default=None)
      is_sbi=models.BooleanField(default=None)
      start_date=models.DateField(default=None)
      end_date=models.DateField(default=None,blank=True,null=True)
      supporting_docs=models.TextField(default=None,blank=True,null=True)

      pan_card=models.CharField(max_length=10, default=None,blank=True,null=True)
      gst=models.CharField(max_length=15, default=None ,blank=True,null=True)

      class Meta:
            managed = True
            db_table = 'bank_details'
            unique_together=['bank_account' ,'fin_code_fk']


class YearCalendar(models.Model):
      week_no=models.IntegerField(default=None)
      start_date=models.DateField(default=None)
      end_date=models.DateField(default=None,blank=True,null=True)
      srpc_fetch_status=models.BooleanField(default=False)
     
      fetched_time=models.DateTimeField(default=None ,blank=True,null=True)
      fin_year=models.CharField(default=None,blank=True,null=True)
      folder_path=models.TextField(default=None,blank=True,null=True)
      dsm_bills_uploaded_status=models.BooleanField(default=False)
      ir_bills_uploaded_status=models.BooleanField(default=False)
      sras_bills_uploaded_status=models.BooleanField(default=False)
      tras_bills_uploaded_status=models.BooleanField(default=False)
      mbas_bills_uploaded_status=models.BooleanField(default=False)
      reac_bills_uploaded_status=models.BooleanField(default=False)
      netas_bills_uploaded_status=models.BooleanField(default=False,blank=True,null=True)
      scuc_bills_uploaded_status=models.BooleanField(default=False,blank=True,null=True)
      cong_bills_uploaded_status=models.BooleanField(default=False,blank=True,null=True)

      def __str__(self):
            return self.fin_year

      class Meta:
            managed = True
            db_table = 'year_calendar'
            unique_together=['week_no','start_date']




class PoolAccountTypes(models.Model):
      acc_types=models.CharField(max_length=50,default=None)
      start_date=models.DateField(default=None)
      end_date=models.DateField(default=None,blank=True,null=True)

      def __str__(self):
            return self.acc_types

      class Meta:
            managed = True
            db_table = 'poolaccount_types'

class MergedAccounts(models.Model):
      merged_accounts=models.CharField(max_length=255,default=None)
      start_date=models.DateField(default=None)
      end_date=models.DateField(default=None,blank=True,null=True)

      def __str__(self):
            return self.merged_accounts

      class Meta:
            managed = True
            db_table = 'merged_accounts'


class BankShortNameMappings(models.Model):
      short_name1=models.CharField(max_length=255,default=None,blank=True,null=True)
      short_name2=models.CharField(max_length=255,default=None,blank=True,null=True)
      short_name3=models.CharField(max_length=255,default=None,blank=True,null=True)
     
      fin_code=models.CharField(max_length=255,default=None)
      bank_type=models.CharField(default=None,blank=True,null=True)
      short_names=models.TextField(default=None,blank=True,null=True)

      def __str__(self):
            return self.fin_code
      
      class Meta:
            managed = True
            db_table = 'short_name_mapping'
            unique_together=['fin_code']

class DisbursementDates(models.Model):
      pool_acc=models.CharField(max_length=50,default=None)
      days=models.IntegerField(default=None)
      start_date=models.DateField(default=None)
      end_date=models.DateField(default=None,blank=True,null=True)

      def __str__(self):
            return self.pool_acc
      
      class Meta:
            managed = True
            db_table = 'disbursement_dates'

class SRPCInputFileName(models.Model):
      filename = models.CharField(max_length=100,default=None)
      pool_acc=models.CharField(max_length=50,default=None)
      enddate=models.DateField(default=None,blank=True,null=True)

      def __str__(self):
            return self.filename
      
      class Meta:
            managed = True

class DisbursementOrder(models.Model):
      startdate=models.DateField(default=None)
      enddate=models.DateField(default=None,blank=True,null=True)
      dsm=models.IntegerField(default=None)
      ir=models.IntegerField(default=None)
      reac=models.IntegerField(default=None,blank=True,null=True)
      net_as=models.IntegerField(default=None,blank=True,null=True)
      cong=models.IntegerField(default=None,blank=True,null=True)

      def __str__(self):
            return str(self.startdate)
      class Meta:
            managed = True
            db_table = 'disbursement_order'

class PoolDuedates(models.Model):
      startdate=models.DateField(default=None)
      enddate=models.DateField(default=None,blank=True,null=True)
      dsm=models.IntegerField(default=None)
      sras=models.IntegerField(default=None)
      tras=models.IntegerField(default=None)
      mbas=models.IntegerField(default=None)
      reac=models.IntegerField(default=None,blank=True,null=True)
      cong=models.IntegerField(default=None,blank=True,null=True)
      
      def __str__(self):
            return str(self.startdate)+'&'+str(self.enddate)
      class Meta:
            managed = True
            db_table = 'duedates'