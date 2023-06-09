import base64, execjs, hashlib, json, os, random, requests, secrets, string, time
from Crypto.Cipher import AES
from functools import reduce


class Funcaptcha:
    def __init__(
        self,
        api_key: str,
        site_url: str,
        service_url: str = None,
        user_agent: str = None,
    ) -> None:
        self.site_key = api_key
        self.service_url = service_url or "client-api.arkoselabs.com"
        self.site_url = site_url

        self.session = requests.Session()
        self.user_agent = (
            user_agent
            or "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/102.0.5005.63 Safari/537.36"
        )

        if not os.path.exists("./fingerprint.js"):
            data = requests.get(
                "https://raw.githubusercontent.com/xtekky/funcaptcha/main/src/static/fingerprint.js"
            )  # till I manage to upload a .js file, if its not detected, it automatically downloads it from the github repository
            open("./fingerprint.js", "a").write(data.text)

        self.pyjs = execjs.compile(open("./fingerprint.js").read())

    @staticmethod
    def _encrypt(data, key):
        data += chr(16 - len(data) % 16) * (16 - len(data) % 16)
        salt = b"".join(
            random.choice(string.ascii_lowercase).encode() for _ in range(8)
        )
        salted, dx = b"", b""
        while len(salted) < 48:
            dx = hashlib.md5(dx + key.encode() + salt).digest()
            salted += dx
        key = salted[:32]
        iv = salted[32 : 32 + 16]
        aes = AES.new(key, AES.MODE_CBC, iv)
        encrypted_data = {
            "ct": base64.b64encode(aes.encrypt(data.encode())).decode("utf-8"),
            "iv": iv.hex(),
            "s": salt.hex(),
        }
        return json.dumps(encrypted_data, separators=(",", ":"))

    @staticmethod
    def _decrypt(data, key):
        data = json.loads(data)
        dk = key.encode() + bytes.fromhex(data["s"])
        md5 = hashlib.md5(dk).digest()
        result = reduce(
            lambda x, y: x + y,
            [md5] + [hashlib.md5((md5[i - 1] + dk)).digest() for i in range(1, 3 + 1)],
        )
        aes = AES.new(result[:32], AES.MODE_CBC, bytes.fromhex(data["iv"]))
        data = aes.decrypt(base64.b64decode(data["ct"]))
        return data

    def get_browser_data(self):
        ts = time.time()
        timeframe = int(ts - (ts % 21600))
        key = self.user_agent + str(timeframe)

        fonts = [
            "Arial",
            "Arial Black",
            "Arial Narrow",
            "Book Antiqua",
            "Bookman Old Style",
            "Calibri",
            "Cambria",
            "Cambria Math",
            "Century",
            "Century Gothic",
            "Century Schoolbook",
            "Comic Sans MS",
            "Consolas",
            "Courier",
            "Courier New",
            "Garamond",
            "Georgia",
            "Helvetica",
            "Impact",
            "Lucida Bright",
            "Lucida Calligraphy",
            "Lucida Console",
            "Lucida Fax",
            "Lucida Handwriting",
            "Lucida Sans",
            "Lucida Sans Typewriter",
            "Lucida Sans Unicode",
            "Microsoft Sans Serif",
            "Monotype Corsiva",
            "MS Gothic",
            "MS PGothic",
            "MS Reference Sans Serif",
            "MS Sans Serif",
            "MS Serif",
            "Palatino Linotype",
            "Segoe Print",
            "Segoe Script",
            "Segoe UI",
            "Segoe UI Light",
            "Segoe UI Semibold",
            "Segoe UI Symbol",
            "Tahoma",
            "Times",
            "Times New Roman",
            "Trebuchet MS",
            "Verdana",
            "Wingdings",
            "Wingdings 2",
            "Wingdings 3",
        ]
        plugins = ["Chrome PDF Plugin", "Chrome PDF Viewer", "Native Client"]
        canvas_fp = -1424337346

        data = {"key": ["api_type", "p"], "value": ["js", 1]}

        data["key"].extend(["f", "n", "wh", "fe", "ife_hash", "cs", "jsbd"])
        data["value"].extend(
            [
                secrets.token_hex(16),
                base64.b64encode(str(int(ts)).encode("utf-8")).decode("utf-8"),
                f"{secrets.token_hex(16)}|{secrets.token_hex(16)}",
                [
                    "DNT:unknown",
                    "L:en-US",
                    "D:24",
                    "PR:1",
                    "S:1920,1080",
                    "AS:1920,1040",
                    "TO:-120",
                    "SS:true",
                    "LS:true",
                    "IDB:true",
                    "B:false",
                    "ODB:true",
                    "CPUC:unknown",
                    "PK:Win32",
                    f"CFP:{canvas_fp}",
                    "FR:false",
                    "FOS:false",
                    "FB:false",
                    f"JSF:{', '.join(fonts)}",
                    f"P:{', '.join(plugins)}",
                    "T:0,false,false",
                    "H:8",
                    "SWF:false",
                ],
                self.pyjs.call("x64hash128", ", ".join(data["value"][4]), 38),
                1,
                '{"HL":28,"NCE":true,"DA":null,"DR":null,"DMT":31,"DO":null,"DOT":31}',
            ]
        )

        data = json.dumps(data, separators=(",", ":"))
        data = Funcaptcha._encrypt(data, key)
        data = base64.b64encode(data.encode("utf-8")).decode("utf-8")
        return data

    def get_request_id(self, session_token):
        key = f"REQUESTED{session_token}ID"
        data = json.dumps(self.metadata, separators=(",", ":"))
        return Funcaptcha._encrypt(data, key)

    def getkey(self):

        bda_value = self.get_browser_data()

        nc_resp = self.session.post(
            url=f"https://{self.service_url}/fc/gt2/public_key/{self.site_key}",
            headers={
                "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
                "Origin": self.site_url,
                "Referer": self.site_url,
                "User-Agent": self.user_agent,
            },
            data={
                "bda": bda_value,
                "public_key": self.site_key,
                "site": self.site_url,
                "userbrowser": self.user_agent,
                "simulate_rate_limit": 0,
                "simulated": 0,
                "language": "en",
                "rnd": random.uniform(0, 1),
            },
        )

        full_token = (
            nc_resp.json()["token"]
            if "token" in nc_resp.text
            else print(" [ x ] Error getting token")
        )

        """
        session_token = full_token.split('|')[0]
        region = full_token.split('|')[1].split("=")[1]
        lang = full_token.split('|')[4].split("=")[1]
        analytics_tier = full_token.split('|')[6].split("=")[1]
        """

        return full_token
