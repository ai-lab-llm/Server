from django.urls import path
from report import views

app_name = 'report'

urlpatterns = [
    path('report_page/', views.report, name='report_page'),
]

