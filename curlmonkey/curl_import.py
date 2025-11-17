#import cURL command into request model

import re
import shlex
from urllib.parse import urlparse, parse_qs, urlencode, urlunparse
from .models import RequestModel, HttpMethod, BodyType, RawBodyType, AuthType, AuthConfig, KeyValuePair, MultipartItem


def parse_curl_command(curl_string: str) -> RequestModel:
    """
    parse a cURL command string into a RequestModel
    
    raises ValueError if parsing fails
    """
    request = RequestModel()
    
    #remove 'curl' prefix if present
    
    curl_string = curl_string.strip()
    if curl_string.startswith("curl "):
        curl_string = curl_string[5:].strip()
    elif curl_string.startswith("curl\n"):
        curl_string = curl_string[5:].strip()
    
    #try to parse as shell command
    
    try:
        #handle quoted strings
        tokens = shlex.split(curl_string)
    except ValueError:
        tokens = []
        current = ""
        in_quotes = False
        quote_char = None
        for char in curl_string:
            if char in ('"', "'") and not in_quotes:
                in_quotes = True
                quote_char = char
            elif char == quote_char and in_quotes:
                in_quotes = False
                quote_char = None
            elif char == ' ' and not in_quotes:
                if current:
                    tokens.append(current)
                    current = ""
            else:
                current += char
        if current:
            tokens.append(current)
    
    if not tokens:
        raise ValueError("Empty cURL command")
    
    i = 0
    url = None
    method = "GET"
    headers = []
    data = None
    data_raw = None
    data_binary = None
    form_data = []
    auth_user = None
    auth_pass = None
    bearer_token = None
    
    while i < len(tokens):
        token = tokens[i]
        
        if token == "-X" or token == "--request":
            if i + 1 < len(tokens):
                method = tokens[i + 1].upper()
                i += 2
                continue
        elif token == "-H" or token == "--header":
            if i + 1 < len(tokens):
                header_str = tokens[i + 1]
                if ":" in header_str:
                    key, value = header_str.split(":", 1)
                    key = key.strip()
                    value = value.strip()
                    #check for authorization bearer
                    if key.lower() == "authorization" and value.lower().startswith("bearer "):
                        bearer_token = value[7:].strip()
                    else:
                        headers.append((key, value))
                i += 2
                continue
        elif token == "-d" or token == "--data":
            if i + 1 < len(tokens):
                data = tokens[i + 1]
                i += 2
                continue
        elif token == "--data-raw":
            if i + 1 < len(tokens):
                data_raw = tokens[i + 1]
                i += 2
                continue
        elif token == "--data-binary":
            if i + 1 < len(tokens):
                data_binary = tokens[i + 1]
                i += 2
                continue
        elif token == "-F" or token == "--form":
            if i + 1 < len(tokens):
                form_data.append(tokens[i + 1])
                i += 2
                continue
        elif token == "-u" or token == "--user":
            if i + 1 < len(tokens):
                auth_str = tokens[i + 1]
                if ":" in auth_str:
                    auth_user, auth_pass = auth_str.split(":", 1)
                else:
                    auth_user = auth_str
                i += 2
                continue
        elif token.startswith("--proxy"):
            #skip proxy settings
            if i + 1 < len(tokens):
                i += 2
            else:
                i += 1
            continue
        elif token.startswith("-") or token.startswith("--"):
            #unknown flag, skip it and its value if it has one
            i += 1
            continue
        else:
            #this might be the url
            if not url and (token.startswith("http://") or token.startswith("https://")):
                url = token
            elif not url:
                #try to treat as url anyway
                url = token
        
        i += 1
    
    if not url:
        raise ValueError("No URL found in cURL command")
    
    #set url and method
    
    request.url = url
    try:
        request.method = HttpMethod(method)
    except ValueError:
        request.method = HttpMethod.GET
    
    #parse url to extract query params
    
    parsed = urlparse(url)
    query_params = parse_qs(parsed.query, keep_blank_values=True)
    for key, values in query_params.items():
        for value in values:
            request.query_params.append(KeyValuePair(enabled=True, key=key, value=value))
    
    #set headers
    
    for key, value in headers:
        request.headers.append(KeyValuePair(enabled=True, key=key, value=value))
    
    #set auth
    
    if bearer_token:
        request.auth = AuthConfig(auth_type=AuthType.BEARER, bearer_token=bearer_token)
    elif auth_user:
        request.auth = AuthConfig(
            auth_type=AuthType.BASIC,
            username=auth_user,
            password=auth_pass or ""
        )
    
    #set body
    
    body_content = data_raw or data_binary or data
    if body_content:
        #check if it looks like json
        body_content = body_content.strip()
        if body_content.startswith("{") or body_content.startswith("["):
            request.body_type = BodyType.RAW
            request.raw_body_type = RawBodyType.JSON
            request.raw_body = body_content
        else:
            #check if it's form-encoded
            if "=" in body_content and "&" in body_content:
                request.body_type = BodyType.FORM_URLENCODED
                for pair in body_content.split("&"):
                    if "=" in pair:
                        key, value = pair.split("=", 1)
                        request.form_data.append(KeyValuePair(enabled=True, key=key, value=value))
            else:
                request.body_type = BodyType.RAW
                request.raw_body_type = RawBodyType.TEXT
                request.raw_body = body_content
    elif form_data:
        request.body_type = BodyType.MULTIPART
        for form_item in form_data:
            #parse form item: key=value or key=@filepath
            if "=" in form_item:
                key, value = form_item.split("=", 1)
                if value.startswith("@"):
                    #file upload
                    file_path = value[1:]
                    request.multipart_data.append(
                        MultipartItem(enabled=True, key=key, type="file", value=file_path)
                    )
                else:
                    request.multipart_data.append(
                        MultipartItem(enabled=True, key=key, type="text", value=value)
                    )
    
    return request

