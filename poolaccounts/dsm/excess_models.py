from django.db import models
from registration.models import *
from django.utils import timezone


class ExcessBaseModel(models.Model):
      # Deviation Data also 
      Entity=models.TextField(default=None)
      Final_charges=models.FloatField(default=None,blank=True)
      Remarks=models.TextField(default=None,blank=True,null=True)
      Fin_code=models.CharField(max_length=100 ,default=None)    

      Is_disbursed=models.BooleanField(default=False,blank=True,null=True)
      Fully_disbursed=models.CharField(max_length=10,default=None,blank=True,null=True)# P is partial and C is Complete
      Paid_date=models.DateField(default=None)
      Bank_type=models.CharField(max_length=50,default=None,blank=True,null=True)
      Description=models.CharField(max_length=255,default=None,blank=True,null=True)
      Other_info=models.CharField(max_length=255,default=None,blank=True,null=True)
      Acc_Type=models.CharField(default=None,max_length=255,blank=True,null=True)
      
      def __str__(self):
            return self.Fin_code
      
      class Meta:
            db_table = 'excess_basemodel'

class OtherPayments(models.Model):
      Paid_date=models.DateField(default=None)
      Description=models.CharField(max_length=255,default=None,blank=True,null=True)
      Paid_amount=models.FloatField(default=None)
      Bank_type=models.CharField(max_length=50,default=None,blank=True,null=True)
      Is_disbursed=models.BooleanField(default=None)
      Remarks=models.CharField(max_length=255,default=None,blank=True)

      def __str__(self):
            return self.Paid_amount
      
      class Meta:
            db_table = 'other_paymentsmodel'