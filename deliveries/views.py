import logging
import threading
from django.utils import timezone
from rest_framework import viewsets, filters
from rest_framework.pagination import PageNumberPagination
from .models import Sector, WashingStation, Farmer, Plot, Delivery, PriceSchedule
from .serializers import (
    SectorSerializer, WashingStationSerializer, FarmerSerializer,
    PlotSerializer, DeliverySerializer, PriceScheduleSerializer
)
from .risk_registry import check_plot_risk, RegistryUnavailableError

logger = logging.getLogger('deliveries')


def run_risk_check(plot_id: int):
    """
    Background task: check a plot's risk status against the (simulated)
    external registry, and update the record once resolved.
    Runs in its own thread so it never blocks the HTTP request that
    triggered it.
    """
    logger.info(f"Risk check started for plot {plot_id}")
    try:
        result = check_plot_risk(plot_id)
        Plot.objects.filter(id=plot_id).update(
            risk_status=result,
            risk_checked_at=timezone.now(),
        )
        logger.info(f"Risk check completed for plot {plot_id}: {result}")
    except RegistryUnavailableError as e:
        # Registry was down. We deliberately do NOT change risk_status here -
        # it stays 'pending', which is our documented position: deliveries
        # from a plot whose check never succeeds are still accepted, just
        # flagged as unverified via risk_status remaining 'pending'.
        logger.warning(f"Risk check failed for plot {plot_id}: {e}")
    except Exception as e:
        # Catch-all so a bug in the check never crashes the background
        # thread silently without a trace.
        logger.error(f"Unexpected error checking plot {plot_id}: {e}")


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
    Registering a plot here also queues an async risk check (Task 3) -
    it runs in a background thread and does not block this response.
    """
    queryset = Plot.objects.select_related('farmer', 'sector', 'washing_station').all()
    serializer_class = PlotSerializer
    filter_backends = [filters.SearchFilter]
    search_fields = ['sector__name', 'washing_station__name']

    def perform_create(self, serializer):
        plot = serializer.save()
        thread = threading.Thread(target=run_risk_check, args=(plot.id,), daemon=True)
        thread.start()
        logger.info(f"Queued async risk check for plot {plot.id}")


class DeliveryFeedPagination(PageNumberPagination):
    """
    Task 4 performance foundation: paginated delivery feed.
    Small page size because Emmanuel's phone is on 2G at harvest peak -
    a smaller payload per request matters more than fewer requests overall.
    """
    page_size = 20
    page_size_query_param = 'page_size'
    max_page_size = 100


class DeliveryViewSet(viewsets.ModelViewSet):
    """
    Delivery recording, and the station-facing delivery feed.
    Deliveries are accepted regardless of the plot's risk_status -
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

class PriceScheduleViewSet(viewsets.ReadOnlyModelViewSet):
    """
    Task 4 mandatory endpoint: GET /api/price-schedule/
    Read-only - price management (who sets prices, approval flow) is
    out of scope for this MVP; see ADR.md.
    """
    queryset = PriceSchedule.objects.filter(is_active=True).order_by('-effective_from')
    serializer_class = PriceScheduleSerializer
    