from django.contrib import admin
from django.urls import path
from dockadm.views import index, create_container, domainadd, projectadd

urlpatterns = [
    path('jkafkjalkfhqoiwhfioqwf/admin/', admin.site.urls),
    path('jkafkjalkfhqoiwhfioqwf', index, name='index'),
    path('jkafkjalkfhqoiwhfioqwf/create_container/', create_container, name='create_container'),
    path('jkafkjalkfhqoiwhfioqwf/projectadd/', projectadd, name='projectadd'),
    path('jkafkjalkfhqoiwhfioqwf/domainadd/', domainadd, name='domainadd')
]
