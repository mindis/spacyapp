# from django.conf.urls import url, include
from django.urls import path, include
from django.conf import settings
from django.contrib import admin
from rest_framework import routers
from rest_framework.documentation import include_docs_urls

router = routers.DefaultRouter()
urlpatterns = [
    path('api/', include(router.urls)),
    path('api-auth/', include('rest_framework.urls', namespace='rest_framework')),
    path('docs/', include_docs_urls(title='NLP-API')),
    path('admin/', admin.site.urls),
    path('query/', include('enrich.urls', namespace='enrich')),
    path('', include('webpage.urls', namespace='webpage')),
]

if 'spacyal' in settings.INSTALLED_APPS:
    urlpatterns.append(
        path('spacyal_api/', include('spacyal.api_urls'))
    )
    urlpatterns.append(
        path('spacyal/', include('spacyal.urls')))
