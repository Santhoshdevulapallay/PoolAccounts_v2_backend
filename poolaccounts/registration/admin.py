from django.contrib import admin

from registration.models import *

admin.site.register([Registration,YearCalendar,PoolAccountTypes,BankShortNameMappings,PoolDuedates,DisbursementDates,MergedAccounts,SRPCInputFileName,DisbursementOrder])