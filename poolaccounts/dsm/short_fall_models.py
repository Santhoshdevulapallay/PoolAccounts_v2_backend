from django.db import models
from django.utils import timezone


# Shortfall related models
class ShortfallBaseModel(models.Model):
    Fin_year=models.CharField(max_length=15,blank=True)
    Letter_date=models.DateField(default=None,blank=True,null=True)
    Due_date=models.DateField(default=None,blank=True,null=True)
    
    # Deviation Data also 
    Entity=models.TextField(default=None)
    Final_charges=models.FloatField(default=None,blank=True)
    Fin_code=models.CharField(max_length=100 ,default=None)    

    def __str__(self):
        return self.Fin_code
    
    class Meta:
        db_table = 'shortfall_basemodel'
        unique_together=['Letter_date','Fin_code','Entity']

class ShortfallPayments(models.Model):
    Paid_date=models.DateField(default=None)
    Description=models.CharField(max_length=400,default=None,blank=True,null=True)
    Paid_amount=models.FloatField(blank=True)
    Other_info=models.TextField(default=None,blank=True,null=True)
    Bank_type=models.CharField(default=None,blank=True,null=True)
    paystatus_fk=models.ForeignKey(ShortfallBaseModel,on_delete=models.SET_NULL,null=True)
    approved_date=models.DateTimeField(default=timezone.now )
    Is_disbursed=models.BooleanField(default=False,blank=True,null=True)
    
    def __str__(self):
        return ""
    
    class Meta:
        db_table = 'shortfall_payments'
        unique_together=['Paid_date','Description','Paid_amount','paystatus_fk']
        