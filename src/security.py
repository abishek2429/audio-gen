"""Security utilities: SSRF protection, URL validation, and HMAC-SHA256 callback signing."""
import hmac
import hashlib
import ipaddress
import json
import logging
import socket
import urllib.parse
from typing import Optional, Dict, Any
import httpx

logger = logging.getLogger(__name__)


class SecurityException(Exception):
    """Base exception for security validation failures."""
    def __init__(self, message: str, code: str = "SECURITY_VIOLATION"):
        super().__init__(message)
        self.message = message
        self.code = code


class SSRFBlockedException(SecurityException):
    """Raised when a remote URL targets private, internal, or loopback network addresses."""
    def __init__(self, message: str):
        super().__init__(message, code="SSRF_BLOCKED")


class PayloadTooLargeException(SecurityException):
    """Raised when downloaded audio exceeds the maximum allowed payload size."""
    def __init__(self, message: str):
        super().__init__(message, code="PAYLOAD_TOO_LARGE")


class InvalidAudioContentException(SecurityException):
    """Raised when downloaded content is not valid audio."""
    def __init__(self, message: str):
        super().__init__(message, code="INVALID_AUDIO_CONTENT")


def is_private_or_restricted_ip(ip_str: str) -> bool:
    """Check if an IP string belongs to private, loopback, link-local, or multicast subnets."""
    try:
        ip = ipaddress.ip_address(ip_str)
        return (
            ip.is_private
            or ip.is_loopback
            or ip.is_reserved
            or ip.is_link_local
            or ip.is_multicast
            or ip.is_unspecified
        )
    except ValueError:
        return True


def validate_remote_url(url: str) -> str:
    """Validate remote URL scheme and verify that its hostname resolves exclusively to public IPs.

    Mitigates Server-Side Request Forgery (SSRF) against internal VPC services,
    cloud metadata endpoints (169.254.169.254), Docker bridges, and localhost.
    """
    parsed = urllib.parse.urlparse(url)
    if parsed.scheme not in ("http", "https"):
        raise SSRFBlockedException(f"Unsupported URL scheme '{parsed.scheme}'. Only http and https are allowed.")

    hostname = parsed.hostname
    if not hostname:
        raise SSRFBlockedException("URL must contain a valid hostname.")

    # Check for direct IP address in hostname
    try:
        ip = ipaddress.ip_address(hostname)
        if is_private_or_restricted_ip(str(ip)):
            raise SSRFBlockedException(f"Direct access to private or restricted IP '{hostname}' is forbidden.")
        return url
    except ValueError:
        pass  # Hostname is a domain name, proceed to DNS resolution

    # Resolve domain via DNS
    try:
        addr_info = socket.getaddrinfo(hostname, None, socket.AF_UNSPEC, socket.SOCK_STREAM)
    except socket.gaierror as e:
        raise SSRFBlockedException(f"DNS resolution failed for hostname '{hostname}': {e}")

    if not addr_info:
        raise SSRFBlockedException(f"No IP addresses resolved for hostname '{hostname}'")

    for family, socktype, proto, canonname, sockaddr in addr_info:
        resolved_ip = sockaddr[0]
        if is_private_or_restricted_ip(resolved_ip):
            logger.warning("SSRF blocked: '%s' resolved to private IP '%s'", hostname, resolved_ip)
            raise SSRFBlockedException(
                f"Hostname '{hostname}' resolves to restricted internal IP address '{resolved_ip}'."
            )

    return url


def validate_audio_magic_bytes(header_bytes: bytes) -> bool:
    """Verify audio file signature (WAV, MP3, FLAC, OGG, M4A)."""
    if len(header_bytes) < 4:
        return False
    # RIFF....WAVE (WAV)
    if header_bytes[:4] == b"RIFF":
        return True
    # ID3 or MPEG sync 0xFF 0xFB/0xF3/0xF2 (MP3)
    if header_bytes[:3] == b"ID3" or (header_bytes[0] == 0xFF and (header_bytes[1] & 0xE0) == 0xE0):
        return True
    # fLaC (FLAC)
    if header_bytes[:4] == b"fLaC":
        return True
    # OggS (OGG)
    if header_bytes[:4] == b"OggS":
        return True
    # ....ftyp (M4A/MP4)
    if len(header_bytes) >= 8 and header_bytes[4:8] == b"ftyp":
        return True
    return False


def fetch_remote_audio(
    url: str,
    max_bytes: int = 50 * 1024 * 1024,  # 50 MB
    timeout_s: float = 15.0,
) -> bytes:
    """Safely fetch remote narration audio with SSRF check, size limits, and format verification."""
    validate_remote_url(url)

    chunks = []
    downloaded_bytes = 0

    with httpx.Client(timeout=timeout_s, follow_redirects=False) as client:
        with client.stream("GET", url) as response:
            if response.status_code != 200:
                raise SecurityException(
                    f"Remote audio server returned HTTP {response.status_code}",
                    code="REMOTE_FETCH_FAILED",
                )

            # Check declared Content-Length header if available
            cl = response.headers.get("content-length")
            if cl and int(cl) > max_bytes:
                raise PayloadTooLargeException(
                    f"Audio file size ({cl} bytes) exceeds maximum limit of {max_bytes} bytes."
                )

            for chunk in response.iter_bytes(chunk_size=65536):
                downloaded_bytes += len(chunk)
                if downloaded_bytes > max_bytes:
                    raise PayloadTooLargeException(
                        f"Downloaded data exceeded maximum allowed size of {max_bytes} bytes."
                    )
                chunks.append(chunk)

    data = b"".join(chunks)
    if not validate_audio_magic_bytes(data[:16]):
        raise InvalidAudioContentException("Downloaded remote payload does not contain valid audio header bytes.")

    return data


def sign_callback_payload(payload_bytes: bytes, secret: str) -> str:
    """Generate HMAC-SHA256 signature for webhook callback authentication."""
    sig = hmac.new(secret.encode("utf-8"), payload_bytes, hashlib.sha256).hexdigest()
    return f"sha256={sig}"


def send_signed_callback(
    callback_url: str,
    payload: Dict[str, Any],
    secret: str,
    timeout_s: float = 10.0,
) -> bool:
    """Deliver webhook notification to callback_url with X-IncuBrix-Signature header."""
    validate_remote_url(callback_url)
    payload_bytes = json.dumps(payload, sort_keys=True).encode("utf-8")
    signature = sign_callback_payload(payload_bytes, secret)

    headers = {
        "Content-Type": "application/json",
        "X-IncuBrix-Signature": signature,
        "User-Agent": "IncuBrix-Webhook/0.1.0",
    }

    try:
        with httpx.Client(timeout=timeout_s) as client:
            resp = client.post(callback_url, content=payload_bytes, headers=headers)
            return resp.status_code in (200, 201, 202, 204)
    except Exception as e:
        logger.error("Callback delivery to '%s' failed: %s", callback_url, e)
        return False
