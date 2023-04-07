"""aanmelden URL Configuration

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/3.0/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path, re_path
from .src import views
from .src import api

urlpatterns = [
    path('admin/', admin.site.urls),
    path('main/', views.Main.as_view(), name='main'),
    path('register/day/<str:day>/<str:pod>', views.Register.as_view(), name='register'),
    path('register/seen/<int:pk>/<str:seen>', views.MarkAsSeen.as_view(), name='seen'),
    path('register/manual/<str:day>/<str:pod>', views.RegisterManual.as_view(), name='register-manual'),
    path('deregister/day/<str:day>/<str:pod>', views.DeRegister.as_view(), name='deregister'),
    path('full/day/<str:day>/<str:pod>', views.Full.as_view(), name='full'),
    path('only_once/', views.OnlyOnce.as_view(), name='only_once'),
    path('stripcard_full/', views.StripcardFull.as_view(), name='stripcard_full'),
    path('report/', views.Report.as_view(), name='report'),
    path('logoff/', views.LogoffView.as_view(), name='logoff'),
    path('api/v2/free', api.FreeV2.as_view()),
    path('api/v1/mac_event', api.MacEvent.as_view()),
    path('api/v2/is_present/<str:day>/<str:pod>/<str:userid>', api.IsPresentV2.as_view()),
    path('api/v2/are_present/<str:day>/<str:pod>', api.ArePresentV2.as_view()),
    path('api/v1/present_since_date/<str:userid>/<int:year>/<int:month>/<int:day>', api.PresentSinceDate.as_view()),
    re_path(r'oauth/.*', views.LoginResponseView.as_view()),
    path('', views.LoginView.as_view(), name='login'),
]
