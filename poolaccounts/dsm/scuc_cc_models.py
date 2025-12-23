from django.db import models
from django.utils import timezone


# Shortfall related models
class SCUCCCBaseModel(models.Model):
    Fin_year=models.CharField(max_length=15,blank=True)
    Letter_date=models.DateField(default=None,blank=True,null=True)
    # Deviation Data also 
    up_to_the_month = models.CharField(max_length=15,blank=True)
    Entity=models.TextField(default=None)
    Final_charges=models.FloatField(default=None,blank=True)
    Fin_code=models.CharField(max_length=100 ,default=None)    
    PayableorReceivable=models.CharField(max_length=50,default=None,blank=True)

    def __str__(self):
        return self.Fin_code
    
    class Meta:
        db_table = 'scuc_cc_basemodel'
        unique_together=['Letter_date','Fin_code','Entity']

class SCUCCCReceivables(models.Model):
    Disbursed_amount=models.FloatField(blank=True,null=True)
    rcvstatus_fk=models.ForeignKey(SCUCCCBaseModel,on_delete=models.SET_NULL,null=True)
    iom_date=models.DateField(default=None,blank=True,null=True)
    disbursed_date=models.DateField(default=None,blank=True,null=True)
    
    def __str__(self):
        return self.rcvstatus_fk
    
    class Meta:
        db_table = 'scuccc_receivables'

class SCUCCPayments(models.Model):
      Paid_date=models.DateField(default=None)
      Description=models.CharField(max_length=400,default=None,blank=True,null=True)
      Paid_amount=models.FloatField(blank=True)
      Other_info=models.TextField(default=None,blank=True,null=True)
      Bank_type=models.CharField(default=None,blank=True,null=True)
      paystatus_fk=models.ForeignKey(SCUCCCBaseModel,on_delete=models.SET_NULL,null=True)
      approved_date=models.DateTimeField(default=timezone.now )
      Is_disbursed=models.BooleanField(default=False,blank=True,null=True)
      is_revision = models.BooleanField(default=False,blank=True,null=True)
      def __str__(self):
        return ""
      
      class Meta:
            db_table = 'scuccc_payments'
            unique_together=['Paid_date','Description','Paid_amount','paystatus_fk']