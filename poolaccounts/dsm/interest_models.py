from django.db import models
from django.utils import timezone

# Interest related models
class TempInterestBaseModel(models.Model):
      Acc_type=models.CharField(max_length=50,default=None,null=True,blank=True)
      Fin_year=models.CharField(max_length=15,blank=True)
      Week_no=models.IntegerField(blank=True)
     
      Revision_no =models.IntegerField(default=0 , blank=True,null=True)
      Letter_date=models.DateField(default=None,blank=True,null=True)
      Due_date=models.DateField(default=None,blank=True,null=True)
      Date_of_receipt=models.DateField(default=None,blank=True,null=True)
      Entity=models.TextField(default=None)
      Final_charges=models.FloatField(default=None,blank=True)
      Remarks=models.TextField(default=None,blank=True,null=True)
      Fin_code=models.CharField(max_length=100 ,default=None)    

      Amount_srpc_payabletopool=models.FloatField(default=None,blank=True,null=True)
      Paid_amount=models.FloatField(default=None,blank=True,null=True)
      No_of_days_delayed=models.IntegerField(default=None,blank=True,null=True)
      
      def __str__(self):
            return self.Fin_code
      
      class Meta:
            db_table = 'temp_interest_basemodel'
            unique_together=['Acc_type','Fin_year','Week_no','Entity','Paid_amount']

class InterestBaseModel(models.Model):
      Letter_date=models.DateField(default=None)
      Entity=models.CharField(default=None)
      Final_charges=models.FloatField(default=None,blank=True)
      Fin_code=models.CharField(max_length=50 ,default=None) 
      def __str__(self):
            return self.Letter_date
      
      class Meta:
            db_table = 'interest_basemodel'
            unique_together=['Letter_date','Entity']

class InterestPayments(models.Model):
      Paid_date=models.DateField(default=None)
      Description=models.CharField(max_length=400,default=None,blank=True,null=True)
      Paid_amount=models.FloatField(blank=True)
      Other_info=models.TextField(default=None,blank=True,null=True)
      Bank_type=models.CharField(default=None,blank=True,null=True)
      approved_date=models.DateTimeField(default=timezone.now )
      Is_disbursed=models.BooleanField(default=False,blank=True,null=True)
      paystatus_fk=models.ForeignKey(InterestBaseModel,on_delete=models.SET_NULL,null=True)

      def __str__(self):
        return self.paystatus_fk
      class Meta:
            db_table = 'interest_payments'

