from django.urls import path
from . import views

app_name = 'tracker'

urlpatterns = [
    path('', views.home, name='home'),
    path('profile/<str:username>/', views.profile, name='profile'),
    
    # API endpoints
    path('api/user/<str:username>/', views.api_user_data, name='api_user_data'),
    path('api/users/data/', views.api_user_data_multi, name='api_user_data_multi'),
    path('api/users/', views.api_users_list, name='api_users_list'),
    path('profiles/', views.profiles, name='profiles'),
    path('api/leaderboard/', views.api_leaderboard, name='api_leaderboard'),
    path('api/debug/<str:username>/', views.api_debug_raw, name='api_debug_raw'),
]