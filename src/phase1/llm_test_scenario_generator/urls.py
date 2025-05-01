from django.urls import path
from . import views

app_name = 'llm_test_scenario_generator'

urlpatterns = [
    # JIRA Requirements Ingestion
    path('jira-requirements/', views.jira_requirements, name='jira_requirements'),
    
    # File Upload for Requirements
    path('file-upload/', views.file_upload, name='file_upload'),
    
    # Manual Input for Requirements
    path('manual-input/', views.manual_input, name='manual_input'),
]