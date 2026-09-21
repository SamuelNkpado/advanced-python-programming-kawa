from django.db import models


class Sector(models.Model):
    """An administrative sector where a plot is located."""
    name = models.CharField(max_length=100, unique=True)

    def __str__(self):
        return self.name


class WashingStation(models.Model):
    """A washing station that receives deliveries from plots."""
    name = models.CharField(max_length=100, unique=True)
    location = models.CharField(max_length=200, blank=True)

    def __str__(self):
        return self.name


class Farmer(models.Model):
    """A farmer delivering coffee cherries to a washing station."""
    name = models.CharField(max_length=150)
    phone_number = models.CharField(max_length=20)
    registered_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name


class Plot(models.Model):
    """A registered plot of land owned by a farmer."""

    class RiskStatus(models.TextChoices):
        PENDING = 'pending', 'Pending'
        CLEARED = 'cleared', 'Cleared'
        FLAGGED = 'flagged', 'Flagged'

    farmer = models.ForeignKey(Farmer, on_delete=models.CASCADE, related_name='plots')
    sector = models.ForeignKey(Sector, on_delete=models.PROTECT, related_name='plots')
    washing_station = models.ForeignKey(WashingStation, on_delete=models.PROTECT, related_name='plots')

    risk_status = models.CharField(
        max_length=10,
        choices=RiskStatus.choices,
        default=RiskStatus.PENDING,
    )
    risk_checked_at = models.DateTimeField(null=True, blank=True)

    registered_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Plot #{self.pk} ({self.farmer.name}, {self.sector.name})"


class Delivery(models.Model):
    """A single cherry delivery recorded against a plot."""
    plot = models.ForeignKey(Plot, on_delete=models.PROTECT, related_name='deliveries')
    weight_kg = models.DecimalField(max_digits=8, decimal_places=2)
    recorded_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name_plural = "Deliveries"

    def __str__(self):
        return f"Delivery #{self.pk} - {self.weight_kg}kg from Plot #{self.plot_id}"