import requests
import base64, random, string, time, io, uuid, struct, os

try:
    import pyotp
    HAS_PYOTP = True
except ImportError:
    HAS_PYOTP = False

try:
    from Cryptodome.Cipher import AES, PKCS1_v1_5
    from Cryptodome.PublicKey import RSA
    from Cryptodome.Random import get_random_bytes
    HAS_CRYPTO = True
except ImportError:
    try:
        from Crypto.Cipher import AES, PKCS1_v1_5
        from Crypto.PublicKey import RSA
        from Crypto.Random import get_random_bytes
        HAS_CRYPTO = True
    except ImportError:
        HAS_CRYPTO = False


class FacebookGetToken:
    """
    Đăng nhập Facebook, lấy token + cookie + pages + avatar.
    Tất cả exception đều raise để caller xử lý.
    """

    URL     = "https://b-graph.facebook.com/auth/login"
    API_KEY = "882a8490361da98702bf97a021ddc14d"
    SIG     = "214049b9f17c38bd767de53752b53946"
    ACCESS  = "275254692598279|585aec5b4c27376758abb7ffcb9db2af"

    def __init__(self, uid_or_email: str, password: str, auth: str = "",
                 machine_id: str = "_2KxZzOokdiTAQGEsqoFdRJk", proxy: dict = None):
        self.email      = uid_or_email
        self.raw_pass   = password
        self.auth       = (auth or "").replace(" ", "")
        
        # Sử dụng proxy được cung cấp
        if proxy:
            self.proxy = proxy
        else:
            # Proxy mặc định từ bạn cung cấp
            self.proxy = {
                "http": "http://cbtpo:ztngl@103.252.92.170:36825",
                "https": "http://cbtpo:ztngl@103.252.92.170:36825"
            }
        
        self.machine_id = machine_id
        self.device_id  = str(uuid.uuid4())
        self.adid       = str(uuid.uuid4())
        self.jazoest    = ''.join(random.choices(string.digits, k=5))

        self.HEADERS = {
            "content-type": "application/x-www-form-urlencoded",
            "x-fb-net-hni": "45201", "zero-rated": "0", "x-fb-sim-hni": "45201",
            "x-fb-connection-quality": "EXCELLENT",
            "x-fb-friendly-name": "authenticate",
            "x-fb-connection-bandwidth": "78032897",
            "x-tigon-is-retry": "False",
            "authorization": "OAuth null",
            "x-fb-connection-type": "WIFI",
            "x-fb-device-group": "3342",
            "priority": "u=3,i",
            "x-fb-http-engine": "Liger",
            "x-fb-client-ip": "True",
            "x-fb-server-cluster": "True",
            "x-fb-request-analytics-tags": (
                '{"network_tags":{"product":"350685531728","retry_attempt":"0"},'
                '"application_tags":"unknown"}'
            ),
            "user-agent": (
                "Dalvik/2.1.0 (Linux; U; Android 11; SM-G998B Build/RP1A.200720.012) "
                "[FBAN/FB4A;FBAV/417.0.0.33.65;FBPN/com.facebook.katana;FBLC/vi_VN;"
                "FBBV/480086274;FBCR/Viettel;FBMF/samsung;FBBD/samsung;FBDV/SM-G998B;"
                "FBSV/11;FBCA/armeabi-v7a:armeabi;FBDM/{density=2.0,width=1080,height=1920};"
                "FB_FW/1;FBRV/0;]"
            ),
        }

        self.password = self._encrypt_password(password) if HAS_CRYPTO else password

    def _encrypt_password(self, password: str) -> str:
        if not HAS_CRYPTO:
            return password
        try:
            url = "https://b-graph.facebook.com/pwd_key_fetch"
            params = {
                "version": "2", "flow": "CONTROLLER_INITIALIZATION", "method": "GET",
                "fb_api_req_friendly_name": "pwdKeyFetch",
                "fb_api_caller_class": "com.facebook.auth.login.AuthOperations",
                "access_token": "438142079694454|fc0a7caa49b192f64f6f5a6d9643bb28",
            }
            resp = requests.post(url, params=params, proxies=self.proxy, timeout=15).json()
            public_key = resp.get("public_key")
            key_id     = str(resp.get("key_id", "25"))

            rand_key = get_random_bytes(32)
            iv       = get_random_bytes(12)

            pubkey      = RSA.import_key(public_key)
            cipher_rsa  = PKCS1_v1_5.new(pubkey)
            enc_rand_key = cipher_rsa.encrypt(rand_key)

            current_time = int(time.time())
            cipher_aes   = AES.new(rand_key, AES.MODE_GCM, nonce=iv)
            cipher_aes.update(str(current_time).encode("utf-8"))
            enc_passwd, auth_tag = cipher_aes.encrypt_and_digest(password.encode("utf-8"))

            buf = io.BytesIO()
            buf.write(bytes([1, int(key_id)]))
            buf.write(iv)
            buf.write(struct.pack("<h", len(enc_rand_key)))
            buf.write(enc_rand_key)
            buf.write(auth_tag)
            buf.write(enc_passwd)

            encoded = base64.b64encode(buf.getvalue()).decode("utf-8")
            return f"#PWD_FB4A:2:{current_time}:{encoded}"
        except Exception as e:
            raise RuntimeError(f"Lỗi mã hoá mật khẩu: {e}")

    def _post(self, url: str, data: dict) -> dict:
        r = requests.post(url, headers=self.HEADERS, data=data,
                          proxies=self.proxy, timeout=20)
        return r.json()

    def _get(self, url: str, params: dict) -> dict:
        r = requests.get(url, params=params, proxies=self.proxy, timeout=15)
        return r.json()

    def _get_user_avatar(self, token: str) -> str:
        try:
            d = self._get("https://graph.facebook.com/me/picture",
                          {"type": "large", "redirect": "false", "access_token": token})
            return d.get("data", {}).get("url", "")
        except Exception:
            return ""

    def _get_page_avatar(self, page_id: str, page_token: str) -> str:
        try:
            d = self._get(f"https://graph.facebook.com/{page_id}/picture",
                          {"type": "large", "redirect": "false", "access_token": page_token})
            return d.get("data", {}).get("url", "")
        except Exception:
            return ""

    def _get_pages(self, user_token: str) -> list:
        try:
            d = self._get("https://graph.facebook.com/v19.0/me/accounts",
                          {"access_token": user_token,
                           "fields": "id,name,access_token,category,fan_count",
                           "limit": 100})
            return d.get("data", [])
        except Exception:
            return []

    def _get_page_real_id(self, page_id: str) -> str:
        try:
            url = f"https://www.facebook.com/{page_id}"
            r = requests.get(url, timeout=10, proxies=self.proxy,
                             headers={"User-Agent": "Mozilla/5.0"})
            if 'content="fb://profile/' in r.text:
                return r.text.split('content="fb://profile/')[1].split('"')[0]
        except Exception:
            pass
        return page_id

    def get_pages_full(self, user_token: str) -> list:
        pages_raw = self._get_pages(user_token)
        result = []
        for page in pages_raw:
            pid     = page.get("id", "")
            name    = page.get("name", "")
            token   = page.get("access_token", "")
            fans    = page.get("fan_count", 0)
            avatar  = self._get_page_avatar(pid, token)
            real_id = self._get_page_real_id(pid)
            result.append({
                "uid":     real_id,
                "page_id_graph": pid,
                "name":    name,
                "token":   token,
                "cookie":  "",
                "role":    "ADMIN",
                "fans":    fans,
                "avatar":  avatar,
            })
        return result

    def get_cookie_from_token(self, token: str) -> str:
        try:
            resp = requests.post(
                "https://api.facebook.com/method/auth.getSessionforApp",
                data={
                    "access_token": token,
                    "format": "json",
                    "new_app_id": "121876164619130",
                    "generate_session_cookies": "1",
                },
                proxies=self.proxy,
                timeout=15,
            ).json()

            if "session_cookies" in resp:
                return "; ".join(
                    f"{c['name']}={c['value']}"
                    for c in resp["session_cookies"] if c.get("name")
                )
            return ""
        except Exception as e:
            print(f"get_cookie_from_token error: {e}")
            return ""

    def login(self) -> dict:
        data = {
            "email": self.email,
            "password": self.password,
            "generate_session_cookies": "1",
            "locale": "vi_VN",
            "client_country_code": "VN",
            "access_token": self.ACCESS,
            "api_key": self.API_KEY,
            "adid": self.adid,
            "account_switcher_uids": f'["{self.email}"]',
            "source": "login",
            "machine_id": self.machine_id,
            "jazoest": self.jazoest,
            "meta_inf_fbmeta": "V2_UNTAGGED",
            "fb_api_req_friendly_name": "authenticate",
            "fb_api_caller_class": "Fb4aAuthHandler",
            "sig": self.SIG,
        }

        result = self._post(self.URL, data)

        if "error" in result:
            err_data = result["error"].get("error_data", {})
            if "login_first_factor" in err_data and "uid" in err_data:
                if not self.auth:
                    return {"ok": False, "msg": "Tài khoản yêu cầu 2FA nhưng không có secret key"}
                if not HAS_PYOTP:
                    return {"ok": False, "msg": "Cần cài pyotp để xử lý 2FA"}

                totp_code = pyotp.TOTP(self.auth).now()
                data2 = {
                    "locale": "vi_VN", "format": "json",
                    "email": self.email,
                    "device_id": self.device_id,
                    "access_token": self.ACCESS,
                    "generate_session_cookies": "true",
                    "generate_machine_id": "1",
                    "twofactor_code": totp_code,
                    "credentials_type": "two_factor",
                    "error_detail_type": "button_with_disabled",
                    "first_factor": err_data["login_first_factor"],
                    "password": self.password,
                    "userid": err_data["uid"],
                    "machine_id": err_data["login_first_factor"],
                }
                result = self._post(self.URL, data2)

            else:
                msg = result["error"].get("message", "Đăng nhập thất bại")
                return {"ok": False, "msg": msg}

        if "access_token" not in result:
            return {"ok": False, "msg": result.get("error", {}).get("message", "Không lấy được token")}

        token = result["access_token"]
        cookie_str = self.get_cookie_from_token(token)
        
        uid  = str(result.get("uid", ""))
        name = result.get("name", "")
        if not uid or not name:
            try:
                me = self._get("https://graph.facebook.com/me",
                               {"access_token": token, "fields": "id,name"})
                uid  = uid  or str(me.get("id", ""))
                name = name or me.get("name", "")
            except Exception:
                pass

        avatar = self._get_user_avatar(token)
        pages  = self.get_pages_full(token)

        return {
            "ok":     True,
            "token":  token,
            "cookie": cookie_str,
            "uid":    uid,
            "name":   name,
            "avatar": avatar,
            "pages":  pages,
        }
