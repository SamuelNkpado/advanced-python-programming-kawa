from rest_framework import viewsets, filters
from rest_framework.pagination import PageNumberPagination
from .models import Sector, WashingStation, Farmer, Plot, Delivery
from .serializers import (
    SectorSerializer, WashingStationSerializer, FarmerSerializer,
    PlotSerializer, DeliverySerializer,
)


class SectorViewSet(viewsets.ModelViewSet):
    queryset = Sector.objects.all()
    serializer_class = SectorSerializer


class WashingStationViewSet(viewsets.ModelViewSet):
    queryset = WashingStation.objects.all()
    serializer_class = WashingStationSerializer


class FarmerViewSet(viewsets.ModelViewSet):
    queryset = Farmer.objects.all()
    serializer_class = FarmerSerializer


class PlotViewSet(viewsets.ModelViewSet):
    """
    Plot registration and listing.
    Registering a plot here is also where Task 3's async risk-check
    gets triggered (added in the next step).
    """
    queryset = Plot.objects.select_related('farmer', 'sector', 'washing_station').all()
    serializer_class = PlotSerializer
    filter_backends = [filters.SearchFilter]
    search_fields = ['sector__name', 'washing_station__name']


class DeliveryFeedPagination(PageNumberPagination):
    """
    Task 4 performance foundation: paginated delivery feed.
    Small page size because Emmanuel's phone is on 2G at harvest peak —
    a smaller payload per request matters more than fewer requests overall.
    """
    page_size = 20
    page_size_query_param = 'page_size'
    max_page_size = 100


class DeliveryViewSet(viewsets.ModelViewSet):
    """
    Delivery recording, and the station-facing delivery feed.
    Deliveries are accepted regardless of the plot's risk_status —
    see ADR.md for the reasoning (Emmanuel cannot hold a farmer at
    the scale waiting on a registry check).
    """
    queryset = Delivery.objects.select_related(
        'plot', 'plot__sector', 'plot__washing_station'
    ).all().order_by('-recorded_at')
    serializer_class = DeliverySerializer
    pagination_class = DeliveryFeedPagination
    filter_backends = [filters.SearchFilter]
    search_fields = ['plot__washing_station__name']