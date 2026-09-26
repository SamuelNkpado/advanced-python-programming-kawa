from rest_framework import serializers
from .models import Sector, WashingStation, Farmer, Plot, Delivery, PriceSchedule
from decimal import Decimal


class SectorSerializer(serializers.ModelSerializer):
    class Meta:
        model = Sector
        fields = ['id', 'name']


class WashingStationSerializer(serializers.ModelSerializer):
    class Meta:
        model = WashingStation
        fields = ['id', 'name', 'location']


class FarmerSerializer(serializers.ModelSerializer):
    class Meta:
        model = Farmer
        fields = ['id', 'name', 'phone_number', 'registered_at']
        read_only_fields = ['registered_at']


class PlotSerializer(serializers.ModelSerializer):
    # Read: show human-readable names. Write: accept IDs via the *_id fields below.
    sector_name = serializers.CharField(source='sector.name', read_only=True)
    washing_station_name = serializers.CharField(source='washing_station.name', read_only=True)

    class Meta:
        model = Plot
        fields = [
            'id', 'farmer', 'sector', 'sector_name',
            'washing_station', 'washing_station_name',
            'risk_status', 'risk_checked_at', 'registered_at',
        ]
        read_only_fields = ['risk_status', 'risk_checked_at', 'registered_at']


class DeliverySerializer(serializers.ModelSerializer):
    plot_sector = serializers.CharField(source='plot.sector.name', read_only=True)
    plot_washing_station = serializers.CharField(source='plot.washing_station.name', read_only=True)
    plot_risk_status = serializers.CharField(source='plot.risk_status', read_only=True)

    class Meta:
        model = Delivery
        fields = [
            'id', 'plot', 'plot_sector', 'plot_washing_station',
            'plot_risk_status', 'weight_kg', 'recorded_at',
        ]
        read_only_fields = ['recorded_at']

    def validate_weight_kg(self, value: Decimal) -> Decimal:
        if value <= 0:
            raise serializers.ValidationError("Delivery weight must be greater than zero.")
        return value


class PriceScheduleSerializer(serializers.ModelSerializer):
    class Meta:
        model = PriceSchedule
        fields = ['id', 'season_label', 'price_per_kg', 'effective_from', 'is_active']

    