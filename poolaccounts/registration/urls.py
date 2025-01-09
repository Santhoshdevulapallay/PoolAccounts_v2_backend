from django.contrib import admin
from django.urls import path ,include
from . import views
from rest_framework.decorators import permission_classes
from rest_framework.permissions import IsAuthenticated
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [

      path('check_login/',views.login),
      path('logout/',permission_classes([IsAuthenticated])(views.logout)),
      # get dashboard data
      path('get_dashboard_data/',permission_classes([IsAuthenticated])(views.getDashboardData)),

      #add bank and entity details
      path('new_registration/',permission_classes([IsAuthenticated])(views.newRegistration)),
      path('update_entity_registration/',permission_classes([IsAuthenticated])(views.updateEntityRegistration)),
      path('update_contact_registration/',permission_classes([IsAuthenticated])(views.updateContactRegistration)),
      path('get_all_entity_details/', permission_classes([IsAuthenticated])(views.getRegisteredEntities )),


      path('add_bank_details/',permission_classes([IsAuthenticated])(views.addBankDetails)),
      path('get_all_bank_details/', permission_classes([IsAuthenticated])(views.getBankDetails )),
      path('download_bankfiles/', permission_classes([IsAuthenticated])(views.downloadBankFiles)),
      # create user page
      path('get_all_dept_users/', permission_classes([IsAuthenticated])(views.allDeptUsers)),
      path('create_user/', permission_classes([IsAuthenticated])(views.createUser)),

      # fetch srpc bills
      path('fetch_website_read/', permission_classes([IsAuthenticated])(views.fetchedWeekFiles )),
      path('fetch_poolaccts_entities/', permission_classes([IsAuthenticated])(views.fetchPoolAcctsEntities )),
      
      path('upload_bank_stmt/', permission_classes([IsAuthenticated])(views.uploadBankStmt )),
      # disbursement priority configuration
      path('get_config_list/', permission_classes([IsAuthenticated])(views.getConfigList )),
      path('disburse_order/', permission_classes([IsAuthenticated])(views.disbursementOrder )),
      # employee 
      path('add_employee/', permission_classes([IsAuthenticated])(views.addEmployee )),
      # due date configuration
      path('duedates_config/', permission_classes([IsAuthenticated])(views.dueDatesConfig )),
      path('get_short_name_mappings/', permission_classes([IsAuthenticated])(views.shortNameMappings )),
      path('add_new_short_name/', permission_classes([IsAuthenticated])(views.addNewShortName )) ,

      path('temp_store/', views.tempStore ), 
      path('scuc_store/', permission_classes([IsAuthenticated])(views.scucStore )),
      # admin page
      path('admin/', admin.site.urls),
]
if settings.DEBUG:
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)