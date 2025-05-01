from django.urls import path
from . import views

app_name = 'ui_components'

urlpatterns = [
    path('', views.dashboard, name='dashboard'),
    path('requirements/', views.requirements, name='requirements'),
    path('test-generation/', views.test_generation, name='test_generation'),
    path('test-repository/', views.test_repository, name='test_repository'),
    path('test-execution/', views.test_execution, name='test_execution'),
    path('analysis/', views.analysis, name='analysis'),
    path('code-automation/', views.code_automation, name='code_automation'),
    path('reporting/', views.reporting, name='reporting'),
    path('settings/', views.settings_view, name='settings'),
    
    # Existing routes for requirements
    path('requirements/jira/', views.jira_requirements, name='jira_requirements'),
    path('requirements/file-upload/', views.file_upload, name='file_upload'),
    path('requirements/manual-input/', views.manual_input, name='manual_input'),
    
    # New routes for test generation & refinement
    path('test-generation/generate/', views.test_generation_generate, name='test_generation_generate'),
    path('test-generation/refine/', views.test_generation_refine, name='test_generation_refine'),
    path('test-generation/export-excel/', views.export_test_cases_excel, name='export_test_cases_excel'),
    path('test-generation/compare-repository/', views.compare_with_repository, name='compare_with_repository'),
]