from django.contrib import admin
from django.urls import path, include
from django.views.generic import RedirectView
from src.phase1.test_case_manager.views import test_generation_from_prompt

urlpatterns = [

    path('api/test-cases/generate-from-prompt', test_generation_from_prompt, name='direct_api_endpoint_no_slash'),
    path('admin/', admin.site.urls),
    path('', include('src.ui_components.urls')),  # Root UI components
    path('requirements/', include('src.phase1.llm_test_scenario_generator.urls')),  # Add this line
    path('test-cases/', include(('src.phase1.test_case_manager.urls', 'test_generation'), namespace='test_generation')),
]