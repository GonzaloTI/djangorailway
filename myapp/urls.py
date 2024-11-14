# import the path function from urls module to define url patterns
from django.urls import path

# import views from the current directory to use in url patterns
from . import views
# import specific views functions directly for easy access

# urlpatterns list to hold the url configurations
urlpatterns = [
    # routes to 'home' view and named as 'home'
    path('', views.home, name='home'),
    # routes to 'about' view and named as 'about'
    path('about/', views.about, name='about'),
    # routes to 'register' view and named as 'register'
    path('register/', views.register, name='register'),
    # routes to 'verify_email' view and named as 'verify_email'
    path('verify_email/', views.verify_email, name='verify_email'),
    # routes to 'user_login' view and named as 'login'
    path('login/', views.user_login, name='login'),
    
    path('inteligencia_de_negocios/', views.KIP1, name='kpi1'),
    path('inteligencia_de_negocios1/', views.KIP2, name='kpi2'),
    path('inteligencia_de_negocios2/', views.KIP3, name='kpi3'),
    path('inteligencia_de_negocios3/', views.KIP4, name='kpi4'),
    path('inteligencia_de_negocios4/', views.KIP5, name='kpi5'),
    
    path('inteligencia_de_negocios7/', views.KIP6, name='kpi6'),
    
    path('cargardatos/', views.cargar, name='cargar'),
    
    path('analitics/', views.analitics, name='analitics'),
    
    path('cargar test/', views.cargar_tests, name='cargar_tests'),
    
    
    
    
    path('realizar_consulta/', views.realizar_consulta, name='realizar_consulta'),

    
    path('Home_KPI/', views.KPIhome, name='homekpi'),
   
    # routes to 'signout' view and named as 'signout'
    path('signout/', views.signout, name='signout'),
    # routes to 'xss_page' view and named as 'xss_page'
  
 
    
]
