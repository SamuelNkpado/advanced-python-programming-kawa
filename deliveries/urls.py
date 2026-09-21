from rest_framework.routers import DefaultRouter
from .views import (
    SectorViewSet, WashingStationViewSet, FarmerViewSet,
    PlotViewSet, DeliveryViewSet,
)

router = DefaultRouter()
router.register(r'sectors', SectorViewSet)
router.register(r'washing-stations', WashingStationViewSet)
router.register(r'farmers', FarmerViewSet)
router.register(r'plots', PlotViewSet)
router.register(r'deliveries', DeliveryViewSet)

urlpatterns = router.urls
