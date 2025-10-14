from django.urls import path
from . import views

app_name = 'tracker'

urlpatterns = [
    path('', views.home, name='home'),
    path('profile/<str:username>/', views.profile, name='profile'),
    path('api/user/<str:username>/', views.api_user_data, name='api_user_data'),
    path('api/debug/<str:username>/', views.api_debug_raw, name='api_debug_raw'),
]