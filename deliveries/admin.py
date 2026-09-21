from django.contrib import admin
from .models import Sector, WashingStation, Farmer, Plot, Delivery

admin.site.register(Sector)
admin.site.register(WashingStation)
admin.site.register(Farmer)
admin.site.register(Plot)
admin.site.register(Delivery)