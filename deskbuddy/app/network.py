"""Peer address parsing shared by messaging and handshakes."""
import ipaddress
from urllib.parse import urlsplit


def peer_target(address):
    address = address.strip()
    if not address or any(char.isspace() for char in address):
        raise ValueError("请输入有效的 IP 或主机名，可附带端口")
    try:
        ipv6 = ipaddress.IPv6Address(address)
    except ValueError:
        pass
    else:
        return f"[{ipv6}]:9000"
    parsed = urlsplit("http://" + address)
    if not parsed.hostname or parsed.username or parsed.password or parsed.path or parsed.query or parsed.fragment:
        raise ValueError("地址应为主机名或 IP:端口，不包含协议和路径")
    port = parsed.port if parsed.port is not None else 9000
    if not 1 <= port <= 65535:
        raise ValueError("端口必须在 1–65535 内")
    host = parsed.hostname
    return f"[{host}]:{port}" if ":" in host else f"{host}:{port}"


def sender_address(host, port=None):
    if not host:
        return ""
    if ":" in host:
        host = f"[{host}]"
    return f"{host}:{port or 9000}"
