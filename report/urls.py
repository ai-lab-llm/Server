# report/urls.py
from django.urls import path
from .views import report

app_name = "report" 

urlpatterns = [
    path("", report, name="report_page"),      
]
