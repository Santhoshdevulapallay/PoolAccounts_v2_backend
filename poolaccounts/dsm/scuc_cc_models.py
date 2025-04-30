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