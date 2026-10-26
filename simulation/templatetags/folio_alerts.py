"""Template adapter for the shared authorized alert presentation."""

from django import template

from simulation.alerts import build_alert_center

register = template.Library()
register.simple_tag(build_alert_center)
