from django.urls import path
from src.phase1.test_case_manager.api.testcase_api_service import (
    generate_test_case,
    generate_test_cases_batch,
    generate_download,
    compare_with_repository
)

urlpatterns = [
    path('test-cases/generate', generate_test_case, name='api_generate_test_case'),
    path('test-cases/generate-batch', generate_test_cases_batch, name='api_generate_test_cases_batch'),
    path('test-cases/generate-download', generate_download, name='api_generate_download'),
    path('test-cases/compare-repository', compare_with_repository, name='api_compare_repository'),
]