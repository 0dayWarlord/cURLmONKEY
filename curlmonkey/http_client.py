#HTTP client

import logging
import time
from typing import Optional, Dict
from urllib.parse import urlencode, urlparse, urlunparse, parse_qs
import requests
from requests.auth import HTTPBasicAuth

from .models import RequestModel, ResponseModel, Settings, Environment

logger = logging.getLogger(__name__)


def substitute_variables(text: str, env_vars: Dict[str, str]) -> str:
    result = text
    for var_name, var_value in env_vars.items():
        placeholder = f"{{{{{var_name}}}}}"
        result = result.replace(placeholder, var_value)
    return result


def build_url(request: RequestModel, env_vars: Dict[str, str]) -> str:
    url = substitute_variables(request.url, env_vars)
    
    #strip quotes from url if present
    
    url = url.strip()
    if (url.startswith('"') and url.endswith('"')) or (url.startswith("'") and url.endswith("'")):
        url = url[1:-1]
    
    #parse existing url
    
    parsed = urlparse(url)
    existing_params = parse_qs(parsed.query, keep_blank_values=True)
    
    #add enabled query params
    
    for param in request.query_params:
        if param.enabled and param.key:
            existing_params[param.key] = [substitute_variables(param.value, env_vars)]
    
    #rebuild url
    
    new_query = urlencode(existing_params, doseq=True)
    new_parsed = parsed._replace(query=new_query)
    return urlunparse(new_parsed)


def build_headers(request: RequestModel, env_vars: Dict[str, str]) -> Dict[str, str]:
    headers = {}
    
    #add enabled headers
    
    for header in request.headers:
        if header.enabled and header.key:
            key = substitute_variables(header.key, env_vars)
            value = substitute_variables(header.value, env_vars)
            headers[key] = value
    
    #add auth headers
    
    if request.auth.auth_type.value == "bearer" and request.auth.bearer_token:
        token = substitute_variables(request.auth.bearer_token, env_vars)
        headers["Authorization"] = f"Bearer {token}"
    
    return headers


def build_body(request: RequestModel, env_vars: Dict[str, str]) -> Optional[tuple]:
    if request.body_type.value == "none":
        return (None, None, None)
    
    elif request.body_type.value == "raw":
        body_text = substitute_variables(request.raw_body, env_vars)
        if request.raw_body_type.value == "json":
            try:
                import json
                json_data = json.loads(body_text)
                return (None, None, json_data)
            except json.JSONDecodeError:
                #if invalid json, send as text
                
                return (body_text, None, None)
        else:
            return (body_text, None, None)
    
    elif request.body_type.value == "x-www-form-urlencoded":
        data = {}
        for item in request.form_data:
            if item.enabled and item.key:
                key = substitute_variables(item.key, env_vars)
                value = substitute_variables(item.value, env_vars)
                data[key] = value
        return (data, None, None)
    
    elif request.body_type.value == "multipart/form-data":
        data = {}
        files = {}
        for item in request.multipart_data:
            if item.enabled and item.key:
                key = substitute_variables(item.key, env_vars)
                if item.type == "file":
                    try:
                        file_path = substitute_variables(item.value, env_vars)
                        files[key] = open(file_path, 'rb')
                    except Exception as e:
                        logger.warning(f"Could not open file {item.value}: {e}")
                else:
                    value = substitute_variables(item.value, env_vars)
                    data[key] = value
        return (data, files, None)
    
    return (None, None, None)

#send an HTTP request synchronously

def send_request(request: RequestModel, settings: Settings, environments: Dict[str, Environment]) -> ResponseModel:
    start_time = time.time()
    response_model = ResponseModel()
    
    try:
        #get environment variables
        
        env = environments.get(request.environment, environments.get("Default", Environment()))
        env_vars = env.variables
        
        #build url
        
        url = build_url(request, env_vars)
        if not url:
            response_model.error = "URL is required"
            return response_model
        
        #build headers
        
        headers = build_headers(request, env_vars)
        
        #build body
        
        data, files, json_data = build_body(request, env_vars)
        
        #prepare auth
        
        auth = None
        if request.auth.auth_type.value == "basic":
            username = substitute_variables(request.auth.username, env_vars)
            password = substitute_variables(request.auth.password, env_vars)
            if username or password:
                auth = HTTPBasicAuth(username, password)
        
        #prepare proxies
        
        proxies = {}
        if settings.http_proxy:
            proxies["http"] = settings.http_proxy
        if settings.https_proxy:
            proxies["https"] = settings.https_proxy
        if not proxies:
            proxies = None
        
        #prepare method
        
        method = request.method.value
        
        #send request
        
        logger.info(f"Sending {method} request to {url}")
        response = requests.request(
            method=method,
            url=url,
            headers=headers,
            data=data,
            files=files,
            json=json_data,
            auth=auth,
            proxies=proxies,
            verify=settings.ssl_verify,
            timeout=settings.default_timeout,
            allow_redirects=True
        )
        
        #calculate time taken
        
        time_taken_ms = (time.time() - start_time) * 1000
        
        #build response model
        
        response_model.status_code = response.status_code
        response_model.reason = response.reason
        response_model.headers = dict(response.headers)
        response_model.body_bytes = response.content
        response_model.time_taken_ms = time_taken_ms
        
        #try to decode text
        
        try:
            response_model.body_text = response.text
        except:
            response_model.body_text = response.content.decode('utf-8', errors='replace')
        
        logger.info(f"Response: {response.status_code} ({time_taken_ms:.2f}ms)")
        
    except requests.exceptions.Timeout:
        response_model.error = f"Request timed out after {settings.default_timeout} seconds"
        response_model.time_taken_ms = (time.time() - start_time) * 1000
        logger.error("Request timeout")
    
    except requests.exceptions.SSLError as e:
        response_model.error = f"SSL error: {str(e)}"
        response_model.time_taken_ms = (time.time() - start_time) * 1000
        logger.error(f"SSL error: {e}")
    
    except requests.exceptions.ConnectionError as e:
        response_model.error = f"Connection error: {str(e)}"
        response_model.time_taken_ms = (time.time() - start_time) * 1000
        logger.error(f"Connection error: {e}")
    
    except Exception as e:
        response_model.error = f"Error: {str(e)}"
        response_model.time_taken_ms = (time.time() - start_time) * 1000
        logger.error(f"Request error: {e}", exc_info=True)
    
    finally:
        #close any open files
        if files:
            for file_obj in files.values():
                if hasattr(file_obj, 'close'):
                    file_obj.close()
    
    return response_model

