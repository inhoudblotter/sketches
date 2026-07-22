import re

# Centralized list of banned vendor/technology names to prevent Role Bleed.
# These terms should not appear in business-focused artifacts (like dictionaries, job stories, features).

BANNED_VENDORS = [
    r"Stripe",
    r"Sendgrid",
    r"Firebase",
    r"Twilio",
    r"AWS",
    r"GCP",
    r"Azure",
    r"PostgreSQL",
    r"MySQL",
    r"MongoDB",
    r"Redis",
    r"Kafka",
    r"GraphQL",
    r"REST",
    r"Kubernetes",
    r"Docker",
    r"Nginx",
    r"Jinja2?",
    r"WebSocket",
    r"gRPC",
    r"UUID",
    r"varchar",
    r"Moderator",
    r"crypto/ed25519",
    r"APNs",
    r"Firestore",
    r"SendGrid",
    r"Apple Push",
    r"FCM",
    r"RabbitMQ",
]

BANNED_VENDORS_PATTERN = r"(?i)\b(" + "|".join(BANNED_VENDORS) + r")\b"
BANNED_VENDORS_REGEX = re.compile(BANNED_VENDORS_PATTERN)
