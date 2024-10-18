from django.urls import path
from home import views

urlpatterns = [
    path('register/', views.handleRegister, name='handleRegister'),
    path('login/', views.handleLogin, name='handleLogin'),
    path('logout/', views.handleLogout, name='handleLogout'),
    path('sendresetlink/', views.sendResetLink, name='sendResetLink'),
    path('resetPassword/<int:user_id>/<str:token>/', views.resetPassword, name='resetPassword'),
    path('gadform/', views.gadForm, name='gadForm'),
    # path('gadcheck/', views.checkGadFormStatus,  name='checkGadFormStatus'),
]