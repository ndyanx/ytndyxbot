import time

# import requests

import aiofiles

# from urllib.parse import urlparse


class CookieManager:
    _instance = None
    _sites = ["https://coomer.su", "https://kemono.su"]
    _headers = {
        "accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7",
        "accept-language": "es-419,es;q=0.9",
        "cache-control": "no-cache",
        "pragma": "no-cache",
        "priority": "u=0, i",
        "sec-ch-ua": '"Microsoft Edge";v="131", "Chromium";v="131", "Not_A Brand";v="24"',
        "sec-ch-ua-mobile": "?0",
        "sec-ch-ua-platform": '"Windows"',
        "sec-fetch-dest": "document",
        "sec-fetch-mode": "navigate",
        "sec-fetch-site": "none",
        "sec-fetch-user": "?1",
        "upgrade-insecure-requests": "1",
        "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36 Edg/131.0.0.0",
    }

    def __new__(cls, cookie_path):
        if cls._instance is None:
            cls._instance = super(CookieManager, cls).__new__(cls)
            # cls._instance.scraper = requests.Session()
            cls._instance.cookie_path = cookie_path
            # cls._instance.last_update_time = time.time()
            # cls._instance._update_cookies()
        return cls._instance

    # def update_cookies(self) -> None:
    #     current_time = time.time()
    #     if current_time - self.last_update_time > 300:
    #         self._update_cookies()
    #         self.last_update_time = current_time

    # def _update_cookies(self) -> None:
    #     list_cookies = []
    #     for url in self._sites:
    #         response = self.scraper.get(url, headers=self._headers)
    #         list_cookies.append(response.cookies)
    #     domains_to_remove = [
    #         self._get_main_domain(site_url) for site_url in self._sites
    #     ]
    #     filtered_cookies = self._read_and_filter_cookies(domains_to_remove)
    #     netscape_cookies = self._cookies_to_netscape(list_cookies)
    #     with open(self.cookie_path, "w") as file:
    #         for line in filtered_cookies:
    #             file.write(line)
    #         for cookie in netscape_cookies:
    #             file.write(cookie + "\n")

    # def _get_main_domain(self, url) -> str:
    #     return ".".join(urlparse(url).netloc.split(".")[-2:])

    # def _read_and_filter_cookies(self, domains_to_remove) -> list:
    #     with open(self.cookie_path, "r") as file:
    #         lines = file.readlines()
    #     filtered_lines = [
    #         line
    #         for line in lines
    #         if not any(domain in line for domain in domains_to_remove)
    #     ]
    #     return filtered_lines

    # def _cookies_to_netscape(self, list_cookies) -> list:
    #     netscape_cookies = []
    #     for cookies in list_cookies:
    #         for cookie in cookies:
    #             netscape_cookies.append(
    #                 f"{cookie.domain}\tTRUE\t{cookie.path}\t{'TRUE' if cookie.secure else 'FALSE'}\t{cookie.expires}\t{cookie.name}\t{cookie.value}"
    #             )
    #     return netscape_cookies

    async def parse_netscape_cookies(self, netloc: str):
        netloc = "." + netloc
        cookies = {}

        async with aiofiles.open(self.cookie_path, "r") as f:
            async for line in f:
                # Ignorar líneas de comentarios o vacías
                if line.startswith("#") or not line.strip():
                    continue

                # Separar la línea en sus componentes
                parts = line.strip().split("\t")

                # Verificar si la línea tiene el formato correcto
                if len(parts) != 7:
                    continue

                domain, flag, path, secure, expiry, name, value = parts

                # Filtrar cookies que no correspondan al netloc solicitado
                if domain != netloc:
                    continue  # Si el dominio no coincide con netloc, saltar esta cookie

                # Convertir la fecha de expiración a un formato legible
                expiry = int(expiry)
                if (
                    expiry == 0
                ):  # Si la fecha de expiración es 0, significa que la cookie es de sesión
                    expiry = None
                else:
                    # Para cookies con fecha de expiración
                    expiry = time.strftime(
                        "%a, %d-%b-%Y %H:%M:%S GMT", time.gmtime(expiry)
                    )

                # Asegurarse de que las cookies son válidas para requests
                if domain.startswith("."):
                    domain = domain[
                        1:
                    ]  # El dominio comienza con un punto (ej: ".example.com")

                # Guardar la cookie solo si es del dominio que estamos buscando
                cookies[name] = value

        return cookies
