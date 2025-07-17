"""
alerts.py - Alerting framework for VisionVend

This module provides a comprehensive alerting system that:
- Sends notifications via multiple channels (email, Slack, webhooks)
- Defines alert rules with thresholds and conditions
- Implements rate limiting to prevent alert storms
- Supports escalation paths for unresolved issues
- Integrates with monitoring metrics
- Handles critical system alerts for machine failures, payment issues, and inventory problems

Usage:
    from VisionVend.monitoring.alerts import AlertManager, AlertRule, AlertSeverity
    
    # Create alert manager
    alert_manager = AlertManager()
    
    # Add notification channels
    alert_manager.add_channel(EmailChannel(recipients=["admin@example.com"]))
    alert_manager.add_channel(SlackChannel(webhook_url="https://hooks.slack.com/..."))
    
    # Define alert rules
    alert_manager.add_rule(
        AlertRule(
            name="low_inventory",
            condition=lambda metrics: metrics.get("inventory_level", 100) < 20,
            severity=AlertSeverity.WARNING,
            message="Inventory running low: {inventory_level}%"
        )
    )
    
    # Trigger alerts
    alert_manager.check_and_alert({"inventory_level": 15})
"""

import asyncio
import datetime
import json
import logging
import os
import re
import smtplib
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from enum import Enum, auto
from typing import Any, Callable, Dict, List, Optional, Set, Tuple, Union

import aiohttp
import jinja2
from pydantic import BaseModel, EmailStr, HttpUrl, validator

# Configure logging
logger = logging.getLogger("visionvend.monitoring.alerts")


# Alert severity levels
class AlertSeverity(str, Enum):
    """Alert severity levels"""
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"
    
    @property
    def emoji(self) -> str:
        """Get emoji for severity level"""
        return {
            AlertSeverity.INFO: "ℹ️",
            AlertSeverity.WARNING: "⚠️",
            AlertSeverity.ERROR: "❌",
            AlertSeverity.CRITICAL: "🚨"
        }.get(self, "")
    
    @property
    def color(self) -> str:
        """Get color for severity level"""
        return {
            AlertSeverity.INFO: "#2196F3",  # Blue
            AlertSeverity.WARNING: "#FF9800",  # Orange
            AlertSeverity.ERROR: "#F44336",  # Red
            AlertSeverity.CRITICAL: "#9C27B0"  # Purple
        }.get(self, "#757575")  # Gray default


# Alert state
class AlertState(str, Enum):
    """Alert state"""
    ACTIVE = "active"
    ACKNOWLEDGED = "acknowledged"
    RESOLVED = "resolved"
    ESCALATED = "escalated"


# Alert models
class Alert(BaseModel):
    """Alert model"""
    id: str
    name: str
    severity: AlertSeverity
    message: str
    details: Dict[str, Any] = {}
    state: AlertState = AlertState.ACTIVE
    created_at: datetime.datetime = field(default_factory=datetime.datetime.utcnow)
    updated_at: datetime.datetime = field(default_factory=datetime.datetime.utcnow)
    acknowledged_at: Optional[datetime.datetime] = None
    resolved_at: Optional[datetime.datetime] = None
    escalated_at: Optional[datetime.datetime] = None
    acknowledged_by: Optional[str] = None
    resolved_by: Optional[str] = None
    source: str = "visionvend"
    tags: List[str] = []
    
    class Config:
        arbitrary_types_allowed = True
    
    def acknowledge(self, by: Optional[str] = None) -> None:
        """Acknowledge the alert"""
        self.state = AlertState.ACKNOWLEDGED
        self.acknowledged_at = datetime.datetime.utcnow()
        self.acknowledged_by = by
        self.updated_at = datetime.datetime.utcnow()
    
    def resolve(self, by: Optional[str] = None) -> None:
        """Resolve the alert"""
        self.state = AlertState.RESOLVED
        self.resolved_at = datetime.datetime.utcnow()
        self.resolved_by = by
        self.updated_at = datetime.datetime.utcnow()
    
    def escalate(self) -> None:
        """Escalate the alert"""
        self.state = AlertState.ESCALATED
        self.escalated_at = datetime.datetime.utcnow()
        self.updated_at = datetime.datetime.utcnow()
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            "id": self.id,
            "name": self.name,
            "severity": self.severity,
            "message": self.message,
            "details": self.details,
            "state": self.state,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "acknowledged_at": self.acknowledged_at.isoformat() if self.acknowledged_at else None,
            "resolved_at": self.resolved_at.isoformat() if self.resolved_at else None,
            "escalated_at": self.escalated_at.isoformat() if self.escalated_at else None,
            "acknowledged_by": self.acknowledged_by,
            "resolved_by": self.resolved_by,
            "source": self.source,
            "tags": self.tags
        }


class AlertRule(BaseModel):
    """Alert rule"""
    name: str
    condition: Callable[[Dict[str, Any]], bool]
    severity: AlertSeverity = AlertSeverity.WARNING
    message: str
    details_template: Optional[str] = None
    cooldown: int = 300  # seconds
    escalation_timeout: Optional[int] = None  # seconds
    tags: List[str] = []
    enabled: bool = True
    last_triggered: Optional[datetime.datetime] = None
    
    class Config:
        arbitrary_types_allowed = True
    
    def check(self, metrics: Dict[str, Any]) -> bool:
        """
        Check if the rule condition is met
        
        Args:
            metrics: Metrics to check against
            
        Returns:
            True if condition is met, False otherwise
        """
        if not self.enabled:
            return False
        
        # Check cooldown
        if self.last_triggered and (datetime.datetime.utcnow() - self.last_triggered).total_seconds() < self.cooldown:
            return False
        
        # Check condition
        try:
            return self.condition(metrics)
        except Exception as e:
            logger.error(f"Error checking alert rule {self.name}: {e}")
            return False
    
    def format_message(self, metrics: Dict[str, Any]) -> str:
        """
        Format alert message with metrics
        
        Args:
            metrics: Metrics to format message with
            
        Returns:
            Formatted message
        """
        try:
            return self.message.format(**metrics)
        except KeyError as e:
            logger.warning(f"Missing key in alert message format: {e}")
            return self.message
        except Exception as e:
            logger.error(f"Error formatting alert message: {e}")
            return self.message
    
    def format_details(self, metrics: Dict[str, Any]) -> Dict[str, Any]:
        """
        Format alert details with metrics
        
        Args:
            metrics: Metrics to format details with
            
        Returns:
            Formatted details
        """
        if not self.details_template:
            return metrics
        
        try:
            template = jinja2.Template(self.details_template)
            rendered = template.render(**metrics)
            return json.loads(rendered)
        except Exception as e:
            logger.error(f"Error formatting alert details: {e}")
            return metrics


# Notification channels
class NotificationChannel(ABC):
    """Base class for notification channels"""
    
    def __init__(self, name: str, rate_limit: int = 60):
        """
        Initialize notification channel
        
        Args:
            name: Channel name
            rate_limit: Rate limit in seconds
        """
        self.name = name
        self.rate_limit = rate_limit
        self.last_notification = {}  # alert_id -> timestamp
    
    @abstractmethod
    async def send(self, alert: Alert) -> bool:
        """
        Send notification
        
        Args:
            alert: Alert to send
            
        Returns:
            True if notification was sent, False otherwise
        """
        pass
    
    def can_send(self, alert_id: str) -> bool:
        """
        Check if notification can be sent based on rate limit
        
        Args:
            alert_id: Alert ID
            
        Returns:
            True if notification can be sent, False otherwise
        """
        now = time.time()
        last_time = self.last_notification.get(alert_id, 0)
        if now - last_time >= self.rate_limit:
            self.last_notification[alert_id] = now
            return True
        return False
    
    def __str__(self) -> str:
        return f"{self.__class__.__name__}(name={self.name})"


class EmailChannel(NotificationChannel):
    """Email notification channel"""
    
    def __init__(
        self,
        name: str = "email",
        recipients: List[str] = None,
        smtp_host: str = "localhost",
        smtp_port: int = 25,
        smtp_user: Optional[str] = None,
        smtp_password: Optional[str] = None,
        use_tls: bool = False,
        from_email: str = "alerts@visionvend.com",
        template: Optional[str] = None,
        rate_limit: int = 300
    ):
        """
        Initialize email channel
        
        Args:
            name: Channel name
            recipients: List of email recipients
            smtp_host: SMTP host
            smtp_port: SMTP port
            smtp_user: SMTP username
            smtp_password: SMTP password
            use_tls: Whether to use TLS
            from_email: From email address
            template: Email template
            rate_limit: Rate limit in seconds
        """
        super().__init__(name, rate_limit)
        self.recipients = recipients or []
        self.smtp_host = smtp_host
        self.smtp_port = smtp_port
        self.smtp_user = smtp_user
        self.smtp_password = smtp_password
        self.use_tls = use_tls
        self.from_email = from_email
        self.template = template or self._default_template()
    
    def _default_template(self) -> str:
        """Get default email template"""
        return """
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="UTF-8">
            <title>{{ alert.severity.upper() }}: {{ alert.name }}</title>
            <style>
                body { font-family: Arial, sans-serif; margin: 0; padding: 20px; color: #333; }
                .alert { border: 1px solid #ddd; border-radius: 4px; padding: 15px; margin-bottom: 20px; }
                .alert-info { border-left: 5px solid #2196F3; }
                .alert-warning { border-left: 5px solid #FF9800; }
                .alert-error { border-left: 5px solid #F44336; }
                .alert-critical { border-left: 5px solid #9C27B0; }
                .header { font-size: 18px; font-weight: bold; margin-bottom: 10px; }
                .message { margin-bottom: 15px; }
                .details { background: #f5f5f5; padding: 10px; border-radius: 4px; }
                .footer { margin-top: 20px; font-size: 12px; color: #777; }
            </style>
        </head>
        <body>
            <div class="alert alert-{{ alert.severity }}">
                <div class="header">{{ alert.severity.upper() }}: {{ alert.name }}</div>
                <div class="message">{{ alert.message }}</div>
                {% if alert.details %}
                <div class="details">
                    <pre>{{ alert.details | tojson(indent=2) }}</pre>
                </div>
                {% endif %}
            </div>
            <div class="footer">
                Generated at {{ alert.created_at.strftime('%Y-%m-%d %H:%M:%S UTC') }}
                <br>
                VisionVend Alert System
            </div>
        </body>
        </html>
        """
    
    async def send(self, alert: Alert) -> bool:
        """
        Send email notification
        
        Args:
            alert: Alert to send
            
        Returns:
            True if email was sent, False otherwise
        """
        if not self.recipients:
            logger.warning("No recipients configured for email channel")
            return False
        
        if not self.can_send(alert.id):
            logger.debug(f"Rate limited email for alert {alert.id}")
            return False
        
        try:
            # Create message
            msg = MIMEMultipart("alternative")
            msg["Subject"] = f"{alert.severity.upper()}: {alert.name}"
            msg["From"] = self.from_email
            msg["To"] = ", ".join(self.recipients)
            
            # Render template
            template = jinja2.Template(self.template)
            html = template.render(alert=alert)
            
            # Attach HTML
            msg.attach(MIMEText(html, "html"))
            
            # Connect to SMTP server
            with smtplib.SMTP(self.smtp_host, self.smtp_port) as server:
                if self.use_tls:
                    server.starttls()
                
                if self.smtp_user and self.smtp_password:
                    server.login(self.smtp_user, self.smtp_password)
                
                # Send email
                server.send_message(msg)
            
            logger.info(f"Sent email alert {alert.id} to {len(self.recipients)} recipients")
            return True
            
        except Exception as e:
            logger.error(f"Error sending email alert {alert.id}: {e}")
            return False


class SlackChannel(NotificationChannel):
    """Slack notification channel"""
    
    def __init__(
        self,
        name: str = "slack",
        webhook_url: str = None,
        channel: Optional[str] = None,
        username: str = "VisionVend Alerts",
        icon_emoji: str = ":robot_face:",
        template: Optional[str] = None,
        rate_limit: int = 60
    ):
        """
        Initialize Slack channel
        
        Args:
            name: Channel name
            webhook_url: Slack webhook URL
            channel: Slack channel
            username: Bot username
            icon_emoji: Bot icon emoji
            template: Message template
            rate_limit: Rate limit in seconds
        """
        super().__init__(name, rate_limit)
        self.webhook_url = webhook_url
        self.channel = channel
        self.username = username
        self.icon_emoji = icon_emoji
        self.template = template or self._default_template()
    
    def _default_template(self) -> str:
        """Get default Slack template"""
        return """
        {
            "attachments": [
                {
                    "color": "{{ alert.severity.color }}",
                    "title": "{{ alert.severity.emoji }} {{ alert.name }}",
                    "text": "{{ alert.message }}",
                    "fields": [
                        {
                            "title": "Severity",
                            "value": "{{ alert.severity }}",
                            "short": true
                        },
                        {
                            "title": "Time",
                            "value": "{{ alert.created_at.strftime('%Y-%m-%d %H:%M:%S UTC') }}",
                            "short": true
                        }
                    ],
                    "footer": "VisionVend Alert System",
                    "ts": {{ alert.created_at.timestamp() | int }}
                }
            ]
        }
        """
    
    async def send(self, alert: Alert) -> bool:
        """
        Send Slack notification
        
        Args:
            alert: Alert to send
            
        Returns:
            True if notification was sent, False otherwise
        """
        if not self.webhook_url:
            logger.warning("No webhook URL configured for Slack channel")
            return False
        
        if not self.can_send(alert.id):
            logger.debug(f"Rate limited Slack notification for alert {alert.id}")
            return False
        
        try:
            # Render template
            template = jinja2.Template(self.template)
            payload_str = template.render(alert=alert)
            payload = json.loads(payload_str)
            
            # Add channel if specified
            if self.channel:
                payload["channel"] = self.channel
            
            # Add username and icon
            payload["username"] = self.username
            payload["icon_emoji"] = self.icon_emoji
            
            # Send to webhook
            async with aiohttp.ClientSession() as session:
                async with session.post(self.webhook_url, json=payload) as response:
                    if response.status >= 400:
                        error_text = await response.text()
                        logger.error(f"Error sending Slack alert {alert.id}: {response.status} - {error_text}")
                        return False
            
            logger.info(f"Sent Slack alert {alert.id}")
            return True
            
        except Exception as e:
            logger.error(f"Error sending Slack alert {alert.id}: {e}")
            return False


class WebhookChannel(NotificationChannel):
    """Webhook notification channel"""
    
    def __init__(
        self,
        name: str = "webhook",
        url: str = None,
        headers: Dict[str, str] = None,
        method: str = "POST",
        template: Optional[str] = None,
        rate_limit: int = 60
    ):
        """
        Initialize webhook channel
        
        Args:
            name: Channel name
            url: Webhook URL
            headers: HTTP headers
            method: HTTP method
            template: Message template
            rate_limit: Rate limit in seconds
        """
        super().__init__(name, rate_limit)
        self.url = url
        self.headers = headers or {"Content-Type": "application/json"}
        self.method = method.upper()
        self.template = template
    
    async def send(self, alert: Alert) -> bool:
        """
        Send webhook notification
        
        Args:
            alert: Alert to send
            
        Returns:
            True if notification was sent, False otherwise
        """
        if not self.url:
            logger.warning("No URL configured for webhook channel")
            return False
        
        if not self.can_send(alert.id):
            logger.debug(f"Rate limited webhook for alert {alert.id}")
            return False
        
        try:
            # Prepare payload
            if self.template:
                template = jinja2.Template(self.template)
                payload_str = template.render(alert=alert)
                try:
                    payload = json.loads(payload_str)
                except json.JSONDecodeError:
                    payload = payload_str
            else:
                payload = alert.to_dict()
            
            # Send to webhook
            async with aiohttp.ClientSession() as session:
                if self.method == "POST":
                    async with session.post(self.url, json=payload, headers=self.headers) as response:
                        if response.status >= 400:
                            error_text = await response.text()
                            logger.error(f"Error sending webhook alert {alert.id}: {response.status} - {error_text}")
                            return False
                elif self.method == "PUT":
                    async with session.put(self.url, json=payload, headers=self.headers) as response:
                        if response.status >= 400:
                            error_text = await response.text()
                            logger.error(f"Error sending webhook alert {alert.id}: {response.status} - {error_text}")
                            return False
                else:
                    logger.error(f"Unsupported HTTP method for webhook: {self.method}")
                    return False
            
            logger.info(f"Sent webhook alert {alert.id}")
            return True
            
        except Exception as e:
            logger.error(f"Error sending webhook alert {alert.id}: {e}")
            return False


# Escalation paths
class EscalationPath(BaseModel):
    """Escalation path for alerts"""
    
    name: str
    levels: List[Dict[str, Any]]
    current_level: int = 0
    
    class Config:
        arbitrary_types_allowed = True
    
    def next_level(self) -> Optional[Dict[str, Any]]:
        """
        Get next escalation level
        
        Returns:
            Next escalation level or None if no more levels
        """
        if self.current_level >= len(self.levels):
            return None
        
        level = self.levels[self.current_level]
        self.current_level += 1
        return level


# Alert manager
class AlertManager:
    """Alert manager for VisionVend"""
    
    def __init__(self):
        """Initialize alert manager"""
        self.rules: Dict[str, AlertRule] = {}
        self.channels: Dict[str, NotificationChannel] = {}
        self.escalation_paths: Dict[str, EscalationPath] = {}
        self.active_alerts: Dict[str, Alert] = {}
        self.alert_history: List[Alert] = []
        self.max_history = 1000
    
    def add_rule(self, rule: AlertRule) -> None:
        """
        Add alert rule
        
        Args:
            rule: Alert rule to add
        """
        self.rules[rule.name] = rule
        logger.info(f"Added alert rule: {rule.name}")
    
    def remove_rule(self, name: str) -> None:
        """
        Remove alert rule
        
        Args:
            name: Rule name
        """
        if name in self.rules:
            del self.rules[name]
            logger.info(f"Removed alert rule: {name}")
    
    def add_channel(self, channel: NotificationChannel) -> None:
        """
        Add notification channel
        
        Args:
            channel: Notification channel to add
        """
        self.channels[channel.name] = channel
        logger.info(f"Added notification channel: {channel.name}")
    
    def remove_channel(self, name: str) -> None:
        """
        Remove notification channel
        
        Args:
            name: Channel name
        """
        if name in self.channels:
            del self.channels[name]
            logger.info(f"Removed notification channel: {name}")
    
    def add_escalation_path(self, path: EscalationPath) -> None:
        """
        Add escalation path
        
        Args:
            path: Escalation path to add
        """
        self.escalation_paths[path.name] = path
        logger.info(f"Added escalation path: {path.name}")
    
    def remove_escalation_path(self, name: str) -> None:
        """
        Remove escalation path
        
        Args:
            name: Path name
        """
        if name in self.escalation_paths:
            del self.escalation_paths[name]
            logger.info(f"Removed escalation path: {name}")
    
    async def check_and_alert(self, metrics: Dict[str, Any]) -> List[Alert]:
        """
        Check all rules and send alerts if conditions are met
        
        Args:
            metrics: Metrics to check against
            
        Returns:
            List of triggered alerts
        """
        triggered_alerts = []
        
        for rule_name, rule in self.rules.items():
            if rule.check(metrics):
                # Create alert
                alert_id = f"{rule_name}_{int(time.time())}"
                message = rule.format_message(metrics)
                details = rule.format_details(metrics)
                
                alert = Alert(
                    id=alert_id,
                    name=rule.name,
                    severity=rule.severity,
                    message=message,
                    details=details,
                    tags=rule.tags
                )
                
                # Store alert
                self.active_alerts[alert_id] = alert
                self.alert_history.append(alert)
                
                # Trim history if needed
                if len(self.alert_history) > self.max_history:
                    self.alert_history = self.alert_history[-self.max_history:]
                
                # Update rule last triggered time
                rule.last_triggered = datetime.datetime.utcnow()
                
                # Send notifications
                await self.send_alert(alert)
                
                triggered_alerts.append(alert)
                logger.info(f"Triggered alert: {alert.name} ({alert.id})")
        
        return triggered_alerts
    
    async def send_alert(self, alert: Alert) -> None:
        """
        Send alert to all channels
        
        Args:
            alert: Alert to send
        """
        tasks = []
        
        for channel_name, channel in self.channels.items():
            tasks.append(channel.send(alert))
        
        # Send to all channels concurrently
        if tasks:
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # Log any errors
            for i, result in enumerate(results):
                if isinstance(result, Exception):
                    channel_name = list(self.channels.keys())[i]
                    logger.error(f"Error sending alert {alert.id} to channel {channel_name}: {result}")
    
    async def escalate_alert(self, alert_id: str, path_name: str) -> bool:
        """
        Escalate an alert
        
        Args:
            alert_id: Alert ID
            path_name: Escalation path name
            
        Returns:
            True if escalated, False otherwise
        """
        if alert_id not in self.active_alerts:
            logger.warning(f"Cannot escalate unknown alert: {alert_id}")
            return False
        
        if path_name not in self.escalation_paths:
            logger.warning(f"Unknown escalation path: {path_name}")
            return False
        
        alert = self.active_alerts[alert_id]
        path = self.escalation_paths[path_name]
        
        # Get next escalation level
        level = path.next_level()
        if not level:
            logger.warning(f"No more escalation levels for path: {path_name}")
            return False
        
        # Update alert
        alert.escalate()
        
        # Add escalation details
        alert.details["escalation"] = {
            "path": path_name,
            "level": path.current_level,
            "level_details": level
        }
        
        # Send notifications based on level configuration
        if "channels" in level:
            for channel_name in level["channels"]:
                if channel_name in self.channels:
                    await self.channels[channel_name].send(alert)
        
        logger.info(f"Escalated alert {alert_id} to level {path.current_level} on path {path_name}")
        return True
    
    def acknowledge_alert(self, alert_id: str, by: Optional[str] = None) -> bool:
        """
        Acknowledge an alert
        
        Args:
            alert_id: Alert ID
            by: Who acknowledged the alert
            
        Returns:
            True if acknowledged, False otherwise
        """
        if alert_id not in self.active_alerts:
            logger.warning(f"Cannot acknowledge unknown alert: {alert_id}")
            return False
        
        alert = self.active_alerts[alert_id]
        alert.acknowledge(by)
        
        logger.info(f"Acknowledged alert {alert_id}" + (f" by {by}" if by else ""))
        return True
    
    def resolve_alert(self, alert_id: str, by: Optional[str] = None) -> bool:
        """
        Resolve an alert
        
        Args:
            alert_id: Alert ID
            by: Who resolved the alert
            
        Returns:
            True if resolved, False otherwise
        """
        if alert_id not in self.active_alerts:
            logger.warning(f"Cannot resolve unknown alert: {alert_id}")
            return False
        
        alert = self.active_alerts[alert_id]
        alert.resolve(by)
        
        # Move to history
        del self.active_alerts[alert_id]
        
        logger.info(f"Resolved alert {alert_id}" + (f" by {by}" if by else ""))
        return True
    
    def get_active_alerts(self, severity: Optional[AlertSeverity] = None) -> List[Alert]:
        """
        Get active alerts
        
        Args:
            severity: Optional severity filter
            
        Returns:
            List of active alerts
        """
        if severity:
            return [a for a in self.active_alerts.values() if a.severity == severity]
        return list(self.active_alerts.values())
    
    def get_alert_history(
        self,
        limit: int = 100,
        severity: Optional[AlertSeverity] = None,
        start_time: Optional[datetime.datetime] = None,
        end_time: Optional[datetime.datetime] = None
    ) -> List[Alert]:
        """
        Get alert history
        
        Args:
            limit: Maximum number of alerts to return
            severity: Optional severity filter
            start_time: Optional start time filter
            end_time: Optional end time filter
            
        Returns:
            List of alerts from history
        """
        filtered = self.alert_history
        
        if severity:
            filtered = [a for a in filtered if a.severity == severity]
        
        if start_time:
            filtered = [a for a in filtered if a.created_at >= start_time]
        
        if end_time:
            filtered = [a for a in filtered if a.created_at <= end_time]
        
        # Sort by created_at descending
        filtered.sort(key=lambda a: a.created_at, reverse=True)
        
        return filtered[:limit]


# Predefined alert rules for VisionVend
class VisionVendAlerts:
    """Predefined alert rules for VisionVend"""
    
    @staticmethod
    def machine_offline(timeout_seconds: int = 300) -> AlertRule:
        """
        Alert when machine is offline
        
        Args:
            timeout_seconds: Seconds before machine is considered offline
            
        Returns:
            AlertRule
        """
        return AlertRule(
            name="machine_offline",
            condition=lambda m: m.get("machine_last_seen", 0) < (time.time() - timeout_seconds),
            severity=AlertSeverity.ERROR,
            message="Machine {machine_id} is offline. Last seen {machine_last_seen_human}.",
            details_template="""
            {
                "machine_id": "{{ machine_id }}",
                "last_seen": "{{ machine_last_seen_human }}",
                "offline_duration": "{{ offline_duration_human }}",
                "last_status": "{{ last_status }}"
            }
            """,
            cooldown=1800,  # 30 minutes
            tags=["machine", "connectivity"]
        )
    
    @staticmethod
    def payment_failure(threshold: int = 3, window_seconds: int = 900) -> AlertRule:
        """
        Alert on payment failures
        
        Args:
            threshold: Number of failures before alerting
            window_seconds: Time window to count failures
            
        Returns:
            AlertRule
        """
        return AlertRule(
            name="payment_failure",
            condition=lambda m: m.get("payment_failures", 0) >= threshold,
            severity=AlertSeverity.ERROR,
            message="Payment system experiencing failures. {payment_failures} failures in the last {payment_failure_window_human}.",
            details_template="""
            {
                "failures": {{ payment_failures }},
                "window": "{{ payment_failure_window_human }}",
                "last_error": "{{ payment_last_error }}",
                "error_codes": {{ payment_error_codes | tojson }}
            }
            """,
            cooldown=1800,  # 30 minutes
            tags=["payment", "stripe"]
        )
    
    @staticmethod
    def low_inventory(threshold_percent: int = 20) -> AlertRule:
        """
        Alert on low inventory
        
        Args:
            threshold_percent: Percentage threshold for low inventory
            
        Returns:
            AlertRule
        """
        return AlertRule(
            name="low_inventory",
            condition=lambda m: m.get("inventory_percent", 100) <= threshold_percent,
            severity=AlertSeverity.WARNING,
            message="Inventory running low: {inventory_percent}% remaining ({inventory_items} items).",
            details_template="""
            {
                "inventory_percent": {{ inventory_percent }},
                "inventory_items": {{ inventory_items }},
                "low_stock_products": {{ low_stock_products | tojson }}
            }
            """,
            cooldown=86400,  # 24 hours
            tags=["inventory", "stock"]
        )
    
    @staticmethod
    def door_left_open(threshold_seconds: int = 60) -> AlertRule:
        """
        Alert when door is left open
        
        Args:
            threshold_seconds: Seconds before door is considered left open
            
        Returns:
            AlertRule
        """
        return AlertRule(
            name="door_left_open",
            condition=lambda m: m.get("door_open", False) and m.get("door_open_duration", 0) > threshold_seconds,
            severity=AlertSeverity.WARNING,
            message="Door left open on machine {machine_id} for {door_open_duration_human}.",
            cooldown=300,  # 5 minutes
            tags=["machine", "door", "security"]
        )
    
    @staticmethod
    def temperature_out_of_range(min_temp: float = 2.0, max_temp: float = 8.0) -> AlertRule:
        """
        Alert when temperature is out of range (for refrigerated units)
        
        Args:
            min_temp: Minimum acceptable temperature (°C)
            max_temp: Maximum acceptable temperature (°C)
            
        Returns:
            AlertRule
        """
        return AlertRule(
            name="temperature_out_of_range",
            condition=lambda m: "temperature" in m and (m["temperature"] < min_temp or m["temperature"] > max_temp),
            severity=AlertSeverity.ERROR,
            message="Temperature out of range: {temperature}°C (acceptable range: {min_temp}°C to {max_temp}°C).",
            details_template="""
            {
                "temperature": {{ temperature }},
                "min_temp": {{ min_temp }},
                "max_temp": {{ max_temp }},
                "duration": "{{ temperature_duration_human }}",
                "machine_id": "{{ machine_id }}"
            }
            """,
            cooldown=1800,  # 30 minutes
            tags=["machine", "temperature", "refrigeration"]
        )
    
    @staticmethod
    def high_error_rate(threshold_percent: float = 10.0, min_requests: int = 10) -> AlertRule:
        """
        Alert on high error rate
        
        Args:
            threshold_percent: Error rate percentage threshold
            min_requests: Minimum number of requests before alerting
            
        Returns:
            AlertRule
        """
        return AlertRule(
            name="high_error_rate",
            condition=lambda m: (
                m.get("request_count", 0) >= min_requests and
                (m.get("error_count", 0) / m.get("request_count", 1)) * 100 >= threshold_percent
            ),
            severity=AlertSeverity.ERROR,
            message="High error rate: {error_rate:.1f}% ({error_count}/{request_count} requests).",
            details_template="""
            {
                "error_rate": {{ error_rate }},
                "error_count": {{ error_count }},
                "request_count": {{ request_count }},
                "top_errors": {{ top_errors | tojson }}
            }
            """,
            cooldown=900,  # 15 minutes
            tags=["api", "errors", "performance"]
        )
    
    @staticmethod
    def system_resource_usage(cpu_threshold: float = 90.0, memory_threshold: float = 90.0, disk_threshold: float = 90.0) -> AlertRule:
        """
        Alert on high system resource usage
        
        Args:
            cpu_threshold: CPU usage percentage threshold
            memory_threshold: Memory usage percentage threshold
            disk_threshold: Disk usage percentage threshold
            
        Returns:
            AlertRule
        """
        def check_resources(m):
            cpu_high = m.get("cpu_usage", 0) >= cpu_threshold
            memory_high = m.get("memory_usage", 0) >= memory_threshold
            disk_high = m.get("disk_usage", 0) >= disk_threshold
            return cpu_high or memory_high or disk_high
        
        return AlertRule(
            name="system_resource_usage",
            condition=check_resources,
            severity=AlertSeverity.WARNING,
            message="High system resource usage: CPU {cpu_usage:.1f}%, Memory {memory_usage:.1f}%, Disk {disk_usage:.1f}%.",
            details_template="""
            {
                "cpu_usage": {{ cpu_usage }},
                "memory_usage": {{ memory_usage }},
                "disk_usage": {{ disk_usage }},
                "cpu_threshold": {{ cpu_threshold }},
                "memory_threshold": {{ memory_threshold }},
                "disk_threshold": {{ disk_threshold }}
            }
            """,
            cooldown=1800,  # 30 minutes
            tags=["system", "resources", "performance"]
        )
    
    @staticmethod
    def mqtt_disconnection() -> AlertRule:
        """
        Alert on MQTT disconnection
        
        Returns:
            AlertRule
        """
        return AlertRule(
            name="mqtt_disconnection",
            condition=lambda m: not m.get("mqtt_connected", True),
            severity=AlertSeverity.ERROR,
            message="MQTT client disconnected. Last connected {mqtt_last_connected_human}.",
            cooldown=300,  # 5 minutes
            tags=["mqtt", "connectivity"]
        )
    
    @staticmethod
    def suspicious_activity(threshold: int = 3) -> AlertRule:
        """
        Alert on suspicious activity
        
        Args:
            threshold: Number of suspicious events before alerting
            
        Returns:
            AlertRule
        """
        return AlertRule(
            name="suspicious_activity",
            condition=lambda m: m.get("suspicious_events", 0) >= threshold,
            severity=AlertSeverity.CRITICAL,
            message="Suspicious activity detected: {suspicious_events} events.",
            details_template="""
            {
                "events": {{ suspicious_events }},
                "details": {{ suspicious_details | tojson }},
                "machine_id": "{{ machine_id }}"
            }
            """,
            cooldown=300,  # 5 minutes
            tags=["security", "suspicious"]
        )


# Helper functions
def format_duration(seconds: float) -> str:
    """
    Format duration in seconds to human-readable string
    
    Args:
        seconds: Duration in seconds
        
    Returns:
        Human-readable duration string
    """
    if seconds < 60:
        return f"{seconds:.1f} seconds"
    elif seconds < 3600:
        minutes = seconds / 60
        return f"{minutes:.1f} minutes"
    elif seconds < 86400:
        hours = seconds / 3600
        return f"{hours:.1f} hours"
    else:
        days = seconds / 86400
        return f"{days:.1f} days"


def setup_visionvend_alerts(alert_manager: AlertManager) -> AlertManager:
    """
    Set up VisionVend alerts with common rules
    
    Args:
        alert_manager: AlertManager instance
        
    Returns:
        Configured AlertManager
    """
    # Add common rules
    alert_manager.add_rule(VisionVendAlerts.machine_offline())
    alert_manager.add_rule(VisionVendAlerts.payment_failure())
    alert_manager.add_rule(VisionVendAlerts.low_inventory())
    alert_manager.add_rule(VisionVendAlerts.door_left_open())
    alert_manager.add_rule(VisionVendAlerts.temperature_out_of_range())
    alert_manager.add_rule(VisionVendAlerts.high_error_rate())
    alert_manager.add_rule(VisionVendAlerts.system_resource_usage())
    alert_manager.add_rule(VisionVendAlerts.mqtt_disconnection())
    alert_manager.add_rule(VisionVendAlerts.suspicious_activity())
    
    # Set up escalation paths
    standard_path = EscalationPath(
        name="standard",
        levels=[
            {
                "delay": 1800,  # 30 minutes
                "channels": ["email"]
            },
            {
                "delay": 3600,  # 1 hour
                "channels": ["email", "slack"]
            },
            {
                "delay": 7200,  # 2 hours
                "channels": ["email", "slack", "sms"]
            }
        ]
    )
    
    critical_path = EscalationPath(
        name="critical",
        levels=[
            {
                "delay": 900,  # 15 minutes
                "channels": ["email", "slack"]
            },
            {
                "delay": 1800,  # 30 minutes
                "channels": ["email", "slack", "sms"]
            },
            {
                "delay": 3600,  # 1 hour
                "channels": ["email", "slack", "sms", "phone"]
            }
        ]
    )
    
    alert_manager.add_escalation_path(standard_path)
    alert_manager.add_escalation_path(critical_path)
    
    return alert_manager
