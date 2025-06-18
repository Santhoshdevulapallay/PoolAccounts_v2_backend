from django.contrib import admin
from django.urls import path ,include
from . import views
from rest_framework.decorators import permission_classes
from rest_framework.permissions import IsAuthenticated
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
      path('check_login/',views.login),
      path('logout/',views.logout),
      # get dashboard data
      path('get_dashboard_data/',views.getDashboardData),
      path('download_dasboard_bills/',views.downloadDashboardBill),

      #add bank and entity details
      path('new_registration/',views.newRegistration),
      path('update_entity_registration/',views.updateEntityRegistration),
      path('update_contact_registration/',views.updateContactRegistration),
      path('get_all_entity_details/', views.getRegisteredEntities ),
      path('get_fin_fc_names/', (views.getFinFCNames )),

      path('add_bank_details/',views.addBankDetails),
      path('get_all_bank_details/', views.getBankDetails ),
      path('download_bankfiles/', views.downloadBankFiles),
      # create user page
      path('get_all_dept_users/', views.allDeptUsers),
      path('create_user/', views.createUser),

      # fetch srpc bills
      path('fetch_website_read/', views.fetchedWeekFiles ),
      path('fetch_poolaccts_entities/', views.fetchPoolAcctsEntities ),
      
      path('upload_bank_stmt/', views.uploadBankStmt ),
      # disbursement priority configuration
      path('get_config_list/', views.getConfigList ),
      path('disburse_order/', views.disbursementOrder ),
      # employee 
      path('add_employee/', views.addEmployee ),
      # due date configuration
      path('duedates_config/', views.dueDatesConfig ),
      path('get_short_name_mappings/', views.shortNameMappings ),
      path('add_new_short_name/', views.addNewShortName ),

      path('temp_store/', views.tempStore ), 
      path('scuc_store/', views.scucStore ),
      # user module
      path('get_basic_details/', (views.getUtilBasicDetails )),
      path('get_lc_details/', (views.getLCDetails )),
      path('save_lc_details/', (views.saveLCDetails )),
      # admin page
      path('admin/', admin.site.urls),
]
if settings.DEBUG:
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)