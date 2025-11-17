#export request model to cURL

import shlex
from urllib.parse import urlparse, parse_qs, urlencode, urlunparse
from .models import RequestModel


def escape_shell_string(s: str) -> str:
    #proper escaping
    return shlex.quote(s)


def generate_curl_command(request: RequestModel, include_proxy: bool = False, proxy_http: str = "", proxy_https: str = "", ssl_verify: bool = True) -> str:
    """
    generate a cURL command string from a request model.
    
    Args:
        request: The request model to convert
        include_proxy: Whether to include proxy settings
        proxy_http: HTTP proxy URL
        proxy_https: HTTPS proxy URL
        ssl_verify: Whether to verify SSL certificates (default True)
    """
    parts = ["curl"]
    
    #method
    
    if request.method.value != "GET":
        parts.append(f"-X {request.method.value}")
    
    #url with query params
    
    url = request.url
    parsed = urlparse(url)
    existing_params = parse_qs(parsed.query, keep_blank_values=True)
    
    #add enabled query params
    
    for param in request.query_params:
        if param.enabled and param.key:
            existing_params[param.key] = [param.value]
    
    #rebuild url
    
    new_query = urlencode(existing_params, doseq=True)
    new_parsed = parsed._replace(query=new_query)
    full_url = urlunparse(new_parsed)
    
    parts.append(escape_shell_string(full_url))
    
    #headers
    
    for header in request.headers:
        if header.enabled and header.key:
            parts.append(f"-H {escape_shell_string(f'{header.key}: {header.value}')}")
    
    #auth
    
    if request.auth.auth_type.value == "basic":
        if request.auth.username or request.auth.password:
            auth_str = f"{request.auth.username}:{request.auth.password}"
            parts.append(f"-u {escape_shell_string(auth_str)}")
    elif request.auth.auth_type.value == "bearer":
        if request.auth.bearer_token:
            parts.append(f"-H {escape_shell_string(f'Authorization: Bearer {request.auth.bearer_token}')}")
    
    #body
    
    if request.body_type.value == "raw":
        if request.raw_body:
            parts.append(f"--data-raw {escape_shell_string(request.raw_body)}")
    elif request.body_type.value == "x-www-form-urlencoded":
        if request.form_data:
            form_parts = []
            for item in request.form_data:
                if item.enabled and item.key:
                    form_parts.append(f"{item.key}={item.value}")
            if form_parts:
                form_str = "&".join(form_parts)
                parts.append(f"--data {escape_shell_string(form_str)}")
    elif request.body_type.value == "multipart/form-data":
        for item in request.multipart_data:
            if item.enabled and item.key:
                if item.type == "file":
                    parts.append(f"-F {escape_shell_string(f'{item.key}=@{item.value}')}")
                else:
                    parts.append(f"-F {escape_shell_string(f'{item.key}={item.value}')}")
    
    #proxy
    
    if include_proxy:
        parsed_url = urlparse(full_url)
        if parsed_url.scheme == "https" and proxy_https:
            parts.append(f"--proxy {escape_shell_string(proxy_https)}")
        elif parsed_url.scheme == "http" and proxy_http:
            parts.append(f"--proxy {escape_shell_string(proxy_http)}")
    
    #ssl verify (default is on, so we only add if disabled)
    if not ssl_verify:
        parts.append("--insecure")
    
    return " ".join(parts)

