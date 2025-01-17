# -*- coding: utf-8 -*-
import logging
import os
import platform
from datetime import datetime

import requests
from requests.auth import AuthBase

from qiniu.compat import is_py2, is_py3
from qiniu import config
import qiniu.auth
from . import __version__

_sys_info = '{0}; {1}'.format(platform.system(), platform.machine())
_python_ver = platform.python_version()

USER_AGENT = 'QiniuPython/{0} ({1}; ) Python/{2}'.format(
    __version__, _sys_info, _python_ver)

_session = None
_headers = {'User-Agent': USER_AGENT}


def __add_auth_headers(headers, auth):
    x_qiniu_date = datetime.utcnow().strftime('%Y%m%dT%H%M%SZ')
    if auth.disable_qiniu_timestamp_signature is not None:
        if not auth.disable_qiniu_timestamp_signature:
            headers['X-Qiniu-Date'] = x_qiniu_date
    elif os.getenv('DISABLE_QINIU_TIMESTAMP_SIGNATURE'):
        if os.getenv('DISABLE_QINIU_TIMESTAMP_SIGNATURE').lower() != 'true':
            headers['X-Qiniu-Date'] = x_qiniu_date
    else:
        headers['X-Qiniu-Date'] = x_qiniu_date
    return headers


def __return_wrapper(resp):
    if resp.status_code != 200 or resp.headers.get('X-Reqid') is None:
        return None, ResponseInfo(resp)
    resp.encoding = 'utf-8'
    try:
        ret = resp.json()
    except ValueError:
        logging.debug("response body decode error: %s" % resp.text)
        ret = {}
    return ret, ResponseInfo(resp)


def _init():
    session = requests.Session()
    adapter = requests.adapters.HTTPAdapter(
        pool_connections=config.get_default('connection_pool'),
        pool_maxsize=config.get_default('connection_pool'),
        max_retries=config.get_default('connection_retries'))
    session.mount('http://', adapter)
    global _session
    _session = session


def _post(url, data, files, auth, headers=None):
    if _session is None:
        _init()
    try:
        post_headers = _headers.copy()
        if headers is not None:
            for k, v in headers.items():
                post_headers.update({k: v})
        r = _session.post(
            url, data=data, files=files, auth=auth, headers=post_headers,
            timeout=config.get_default('connection_timeout'))
    except Exception as e:
        return None, ResponseInfo(None, e)
    return __return_wrapper(r)


def _put(url, data, files, auth, headers=None):
    if _session is None:
        _init()
    try:
        post_headers = _headers.copy()
        if headers is not None:
            for k, v in headers.items():
                post_headers.update({k: v})
        r = _session.put(
            url, data=data, files=files, auth=auth, headers=post_headers,
            timeout=config.get_default('connection_timeout'))
    except Exception as e:
        return None, ResponseInfo(None, e)
    return __return_wrapper(r)


def _get(url, params, auth, headers=None):
    if _session is None:
        _init()
    try:
        get_headers = _headers.copy()
        if headers is not None:
            for k, v in headers.items():
                get_headers.update({k: v})
        r = _session.get(
            url,
            params=params,
            auth=auth,
            timeout=config.get_default('connection_timeout'),
            headers=get_headers)
    except Exception as e:
        return None, ResponseInfo(None, e)
    return __return_wrapper(r)


class _TokenAuth(AuthBase):
    def __init__(self, token):
        self.token = token

    def __call__(self, r):
        r.headers['Authorization'] = 'UpToken {0}'.format(self.token)
        return r


def _post_with_token(url, data, token):
    return _post(url, data, None, _TokenAuth(token))


def _post_with_token_and_headers(url, data, token, headers):
    return _post(url, data, None, _TokenAuth(token), headers)


def _post_file(url, data, files):
    return _post(url, data, files, None)


def _post_with_auth(url, data, auth):
    return _post(url, data, None, qiniu.auth.RequestsAuth(auth))


def _get_with_auth(url, data, auth):
    return _get(url, data, qiniu.auth.RequestsAuth(auth))


def _post_with_auth_and_headers(url, data, auth, headers):
    return _post(url, data, None, qiniu.auth.RequestsAuth(auth), headers)


def _get_with_auth_and_headers(url, data, auth, headers):
    return _get(url, data, qiniu.auth.RequestsAuth(auth), headers)


def _post_with_qiniu_mac_and_headers(url, data, auth, headers):
    return _post(url, data, None, qiniu.auth.QiniuMacRequestsAuth(auth), headers)


def _put_with_auth(url, data, auth):
    return _put(url, data, None, qiniu.auth.RequestsAuth(auth))


def _put_with_token_and_headers(url, data, auth, headers):
    return _put(url, data, None, _TokenAuth(auth), headers)


def _put_with_auth_and_headers(url, data, auth, headers):
    return _put(url, data, None, qiniu.auth.RequestsAuth(auth), headers)


def _put_with_qiniu_mac_and_headers(url, data, auth, headers):
    return _put(url, data, None, qiniu.auth.QiniuMacRequestsAuth(auth), headers)


def _post_with_qiniu_mac(url, data, auth):
    qn_auth = qiniu.auth.QiniuMacRequestsAuth(
        auth
    ) if auth is not None else None
    headers = __add_auth_headers({}, auth)

    return _post(url, data, None, qn_auth, headers=headers)


def _get_with_qiniu_mac(url, params, auth):
    qn_auth = qiniu.auth.QiniuMacRequestsAuth(
        auth
    ) if auth is not None else None
    headers = __add_auth_headers({}, auth)

    return _get(url, params, qn_auth, headers=headers)


def _get_with_qiniu_mac_and_headers(url, params, auth, headers):
    if _session is None:
        _init()
    try:
        post_headers = _headers.copy()
        if headers is not None:
            for k, v in headers.items():
                post_headers.update({k: v})
        r = _session.get(
            url,
            params=params,
            auth=qiniu.auth.QiniuMacRequestsAuth(auth) if auth is not None else None,
            timeout=config.get_default('connection_timeout'),
            headers=post_headers)
    except Exception as e:
        return None, ResponseInfo(None, e)
    return __return_wrapper(r)


def _delete_with_qiniu_mac(url, params, auth):
    if _session is None:
        _init()
    try:
        r = _session.delete(
            url,
            params=params,
            auth=qiniu.auth.QiniuMacRequestsAuth(auth) if auth is not None else None,
            timeout=config.get_default('connection_timeout'),
            headers=_headers)
    except Exception as e:
        return None, ResponseInfo(None, e)
    return __return_wrapper(r)


def _delete_with_qiniu_mac_and_headers(url, params, auth, headers):
    if _session is None:
        _init()
    try:
        post_headers = _headers.copy()
        if headers is not None:
            for k, v in headers.items():
                post_headers.update({k: v})
        r = _session.delete(
            url,
            params=params,
            auth=qiniu.auth.QiniuMacRequestsAuth(auth) if auth is not None else None,
            timeout=config.get_default('connection_timeout'),
            headers=post_headers)
    except Exception as e:
        return None, ResponseInfo(None, e)
    return __return_wrapper(r)


class ResponseInfo(object):
    """七牛HTTP请求返回信息类

    该类主要是用于获取和解析对七牛发起各种请求后的响应包的header和body。

    Attributes:
        status_code: 整数变量，响应状态码
        text_body:   字符串变量，响应的body
        req_id:      字符串变量，七牛HTTP扩展字段，参考 http://developer.qiniu.com/docs/v6/api/reference/extended-headers.html
        x_log:       字符串变量，七牛HTTP扩展字段，参考 http://developer.qiniu.com/docs/v6/api/reference/extended-headers.html
        error:       字符串变量，响应的错误内容
    """

    def __init__(self, response, exception=None):
        """用响应包和异常信息初始化ResponseInfo类"""
        self.__response = response
        self.exception = exception
        if response is None:
            self.status_code = -1
            self.text_body = None
            self.req_id = None
            self.x_log = None
            self.error = str(exception)
        else:
            self.status_code = response.status_code
            self.text_body = response.text
            self.req_id = response.headers.get('X-Reqid')
            self.x_log = response.headers.get('X-Log')
            if self.status_code >= 400:
                if self.__check_json(response):
                    ret = response.json() if response.text != '' else None
                    if ret is None:
                        self.error = 'unknown'
                    else:
                        self.error = response.text
                else:
                    self.error = response.text
            if self.req_id is None and self.status_code == 200:
                self.error = 'server is not qiniu'

    def ok(self):
        return self.status_code == 200 and self.req_id is not None

    def need_retry(self):
        if self.__response is None or self.req_id is None:
            return True
        code = self.status_code
        if (code // 100 == 5 and code != 579) or code == 996:
            return True
        return False

    def connect_failed(self):
        return self.__response is None or self.req_id is None

    def __str__(self):
        if is_py2:
            return ', '.join(
                ['%s:%s' % item for item in self.__dict__.items()]).encode('utf-8')
        elif is_py3:
            return ', '.join(['%s:%s' %
                              item for item in self.__dict__.items()])

    def __repr__(self):
        return self.__str__()

    def __check_json(self, reponse):
        try:
            reponse.json()
            return True
        except Exception:
            return False
