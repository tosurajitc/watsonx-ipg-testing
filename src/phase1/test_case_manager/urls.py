from django.urls import path
from src.phase1.test_case_manager import views as test_case_views

app_name = 'test_case_manager'

urlpatterns = [

    path('api/test-cases/generate/', test_case_views.test_generation_generate, name='test_generation_generate'),
    path('api/test-cases/generate-from-prompt/', test_case_views.test_generation_from_prompt, name='test_generation_from_prompt'),
    path('api/test-cases/refine/', test_case_views.test_generation_refine, name='test_generation_refine'),
    path('api/test-cases/export-excel/', test_case_views.test_generation_export_excel, name='test_generation_export_excel'),
    path('test-cases/api/test-llm-connection/', test_case_views.test_llm_connection, name='test_llm_connection'),
    path('api/test-cases/apply-refinements/', test_case_views.apply_test_case_refinements, name='apply_test_case_refinements'),  

 
]