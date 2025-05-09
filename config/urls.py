from django.contrib import admin
from django.urls import path, include
from django.views.generic import RedirectView

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include('src.ui_components.urls')),  # Root UI components
    path('requirements/', include('src.phase1.llm_test_scenario_generator.urls')),  # Add this line
    path('test-cases/', include(('src.phase1.test_case_manager.urls', 'test_generation'), namespace='test_generation')),
]