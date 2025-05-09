from django.urls import path
from . import views
from src.phase1.test_case_manager import views as test_case_views
from src.phase1.llm_test_scenario_generator import views as scenario_generator_views

app_name = 'ui_components'

urlpatterns = [
    path('', views.dashboard, name='dashboard'),
    path('requirements/', views.requirements, name='requirements'),
    path('test-cases/', views.test_generation, name='test_generation'),
    path('test-repository/', views.test_repository, name='test_repository'),
    path('test-execution/', views.test_execution, name='test_execution'),
    path('analysis/', views.analysis, name='analysis'),
    path('code-automation/', views.code_automation, name='code_automation'),
    path('reporting/', views.reporting, name='reporting'),
    path('settings/', views.settings_view, name='settings'),
    
    # Requirements routes
    path('requirements/jira/', scenario_generator_views.jira_requirements, name='jira_requirements'),
    path('requirements/manual-input/', scenario_generator_views.manual_input, name='manual_input'),
    path('requirements/file-upload/', scenario_generator_views.file_upload, name='file_upload'),
    path('requirements/results/', scenario_generator_views.requirements_results, name='requirements_results'),
    path('api/requirements/processed', scenario_generator_views.get_processed_requirements_api, name='api_requirements_processed'),

    # Authentication routes
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('preferences/', views.user_preferences, name='preferences'),
]