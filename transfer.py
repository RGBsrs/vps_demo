import time
import datetime
from typing import Any, Optional
from dataclasses import dataclass

from paramiko import SSHClient, AutoAddPolicy
import requests

links = [
    "http://chi.download.datapacket.com/100mb.bin",
    "http://chi.download.datapacket.com/1000mb.bin",
    "http://mad.download.datapacket.com/100mb.bin",
    "http://mad.download.datapacket.com/1000mb.bin",
    "http://tyo.download.datapacket.com/100mb.bin",
    "http://tyo.download.datapacket.com/1000mb.bin",
]


@dataclass
class VPS:
    name: str
    city: str
    host: str
    ip: str
    user: str
    key: str


def map_continent(continent):
    if continent:
        continent = continent.lower()
        if "america" in continent:
            continent = "america"
    return continent


def get_continent(query):
    url = f"http://ip-api.com/json/{query}?fields=status,message,continent"
    resp = requests.get(url)
    print(query)
    return map_continent(resp.json()["continent"])


class VPSFactory:
    __servers = {
        "america": {
            "name": "VPS 1",
            "city": "N. Virginia",
            "host": "ec2-3-86-70-167.compute-1.amazonaws.com",
            "ip": "3.86.70.167",
            "user": "ec2-user",
            "key": "keys/america_kp.pem",
        },
        "europe": {
            "name": "VPS 2",
            "city": "Frankfurt",
            "host": "ec2-3-72-45-196.eu-central-1.compute.amazonaws.com",
            "ip": "3.72.45.196",
            "user": "ec2-user",
            "key": "keys/europe_kp.pem",
        },
        "asia": {
            "name": "VPS 3",
            "city": "Singapore",
            "host": "ec2-18-139-226-152.ap-southeast-1.compute.amazonaws.com",
            "ip": "18.139.226.152",
            "user": "ec2-user",
            "key": "keys/asia_kp.pem",
        },
    }

    def __init__(
        self,
        continent: Optional[str] = None,
    ) -> None:
        self.continent = continent

    def get_vps(self):
        if self.continent:
            return VPS(**self.__servers[self.continent])

    def get_available_countries(self) -> list:
        return list(self.__servers.keys())


class FileTransfer:
    __default_load_path = "../../var/www/html/downloads"

    def __init__(self, link) -> None:
        self.link = link
        self.filename = link.replace("http://", "").split("/")[1]
        self.continent = self.get_continent_by_link(link)
        self._vps = VPSFactory(self.continent).get_vps()
        self.ssh_client = SSHClient()
        self.ssh_client.set_missing_host_key_policy(AutoAddPolicy)

    @property
    def vps(self):
        return self._vps.host

    def get_continent_by_link(self, link):
        query = link.replace("http://", "").split("/")[0]
        return get_continent(query)

    def __map_continent(self, continent):
        continent = continent.lower()
        if "america" in continent:
            continent = "america"
        return continent

    def _format_output(self, output):
        result = output.replace("'", "").split("\\n")
        time = result[-5].split("=")[1]
        date = result[-3].split(" (")[0]
        return f"{self._vps.name} {self._vps.city} {self._vps.ip}, {time}, {date}, http://{self._vps.ip}/downloads/{self.filename}"

    def __load_file_to_vps(self):
        self.ssh_client.connect(
            hostname=self._vps.host,
            username=self._vps.user,
            key_filename=self._vps.key,
        )
        stdin, stdout, stderr = self.ssh_client.exec_command(
            f"cd {self.__default_load_path} && wget {self.link}",
        )
        stdin.close()
        output = stdout.read()
        stdout.close()
        error = stderr.read()
        stderr.close()
        self.ssh_client.close()
        return self._format_output(str(error))

    def __transfer_file(self, target_vps: VPS):
        self.ssh_client.connect(
            hostname=self._vps.host,
            username=self._vps.user,
            key_filename=self._vps.key,
        )
        start_time = time.time()
        self.ssh_client.exec_command(
            f"""scp -i "keys/{target_vps.key}" -o StrictHostKeyChecking=no {self.__default_load_path}/{self.filename} {target_vps.user}@{target_vps.host}:{self.__default_load_path}""",
        )
        self.ssh_client.close()
        end_time = time.time()
        elapsed_time = round(end_time - start_time, 1)
        date = datetime.datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")
        return f"{self._vps.name} -> {target_vps.name} {target_vps.city} {target_vps.ip}, {elapsed_time}s, {date}, http://{target_vps.ip}/downloads/{self.filename}"

    def __replicate_file(self):
        available_continents = VPSFactory().get_available_countries()
        results = []
        for continent in available_continents:
            if continent != self.continent:
                results.append(self.__transfer_file(VPSFactory(continent).get_vps()))
        return results

    def run(self):
        load_result = self.__load_file_to_vps()
        replication_results = self.__replicate_file()
        return [load_result] + replication_results


class FileDownload:
    def __init__(self, link, downloader_ip) -> None:
        self.filename = link.replace("http://", "").split("/")[1]
        self.ip = downloader_ip
        self.continent = get_continent(self.ip)
        self._vps = VPSFactory(self.continent).get_vps()

    def download(self):
        download_link = f"http://{self._vps.ip}/downloads/{self.filename}"
        print(download_link)
        start_time = time.time()
        resp = requests.get(download_link)
        open(f"tmp/{self.filename}", "wb").write(resp.content)
        end_time = time.time()
        elapsed_time = round(end_time - start_time, 1)
        date = datetime.datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")
        return f"{self._vps.name} {self._vps.city} {self._vps.ip}, {elapsed_time}s, {date}, {download_link}"
