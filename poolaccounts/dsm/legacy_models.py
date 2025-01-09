from django.db import models
from django.utils import timezone

# legacy bill
class LegacyBaseModel(models.Model):
      Fin_year=models.CharField(max_length=15,blank=True)
      Week_no =models.IntegerField(default=0 , blank=True,null=True)
      Letter_date=models.DateField(default=None,blank=True,null=True)
      Due_date=models.DateField(default=None,blank=True,null=True)
      Entity=models.TextField(default=None)
      Final_charges=models.FloatField(default=None,blank=True)
      PayableorReceivable=models.CharField(max_length=50,default=None,blank=True)
      Remarks=models.TextField(default=None,blank=True,null=True)
      Fin_code=models.CharField(max_length=100 ,default=None)
      Is_interregional = models.BooleanField(default=False,blank=True,null=True)    

      Is_disbursed=models.BooleanField(default=False,blank=True,null=True)
      Fully_disbursed=models.CharField(max_length=10,default=None,blank=True,null=True)    
      Effective_start_date=models.DateField(default=None,blank=True,null=True)
      Effective_end_date=models.DateField(default=None,blank=True,null=True)
      Legacy_dues=models.BooleanField(default=True)
      
      def __str__(self):
            return self.Fin_code
      
      class Meta:
            db_table = 'legacy_basemodel'
            unique_together=['Fin_year','Week_no','Entity']


class LegacyPayments(models.Model):
      Paid_date=models.DateField(default=None)
      Description=models.CharField(max_length=400,default=None,blank=True,null=True)
      Paid_amount=models.FloatField(blank=True)
      Other_info=models.TextField(default=None,blank=True,null=True)
      Bank_type=models.CharField(default=None,blank=True,null=True)
      paystatus_fk=models.ForeignKey(LegacyBaseModel,on_delete=models.SET_NULL,null=True)
      approved_date=models.DateTimeField(default=timezone.now )
      Is_disbursed=models.BooleanField(default=False,blank=True,null=True)

      def __str__(self):
        return self.paystatus_fk
      class Meta:
            db_table = 'legacy_payments'




