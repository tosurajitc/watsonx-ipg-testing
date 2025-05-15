# src/phase2/uft_code_generator/urls.py

from django.urls import path
from src.phase2.uft_code_generator import views

# Create app_name for namespace
app_name = 'uft_code_generator'

urlpatterns = [
    # UFT Automation Analysis API endpoints
    path('analyze-test-case/', views.analyze_test_case, name='analyze_test_case'),
    path('preview-test-case/', views.preview_test_case, name='preview_test_case'),
    path('generate-full-script/', views.generate_full_script, name='generate_full_script'),
    path('test-endpoint/', views.test_endpoint, name='test_endpoint'),
    
    # Additional utility endpoints
    path('recommend-libraries/<str:test_case_id>/', views.recommend_libraries, name='recommend_libraries'),
    path('is-automatable/', views.is_test_case_automatable, name='is_automatable'),
    path('batch-analyze/', views.batch_analyze_test_cases, name='batch_analyze'),
    path('export-analysis/', views.export_analysis_results, name='export_analysis'),
]