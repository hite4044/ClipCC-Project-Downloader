__author__ = "hite4044 <695663633@qq.com>"

import requests
import warnings
from os import mkdir
from time import time
from re import findall
from zipfile import ZipFile
from Crypto.Cipher import AES
from bs4 import BeautifulSoup
from os.path import join, isdir
from Crypto.Util.Padding import pad
from DownloadKit import DownloadKit
from json import loads as json_loads, dump as json_dump

warnings.filterwarnings("ignore")
ASSETS_URL = "https://api.codingclip.com/v1/project/asset"


def filter_file_name(file_name: str):
    replaces = list('/\\:*?"<>|')
    for char in replaces:
        file_name = file_name.replace(char, "_")
    return file_name


def format_size(size):
    kb = 1024
    mb = kb * 1024
    gb = mb * 1024
    tb = gb * 1024

    if size >= tb:
        return "%.2f TB" % float(size / tb)
    if size >= gb:
        return "%.2f GB" % float(size / gb)
    if size >= mb:
        return "%.2f MB" % float(size / mb)
    if size >= kb:
        return "%.2f KB" % float(size / kb)


class Project:
    def __init__(self, _id: int):
        self._id = _id

        self.raw_data: bytearray = bytearray()
        self.json_text: str = ""
        self.title: str = "ClipCC Project"
        self.json: dict = {}
        self.resource_list = []

    def get_project_title(self):
        print("获取作品标题")
        try:
            html = requests.get(f"https://codingclip.com/project/{self._id}").text
            soup = BeautifulSoup(html, "html.parser")
            self.title = soup.find("h5", attrs={"class": "nextui-c-PJLV-ievZJdq-css"}).text
        except requests.exceptions.ConnectionError:
            print("无法获取作品信息: 连接错误")
        except AttributeError:
            print("提取标题失败")

    def get_raw_data(self):
        print("下载作品元数据")
        url = "https://api.codingclip.com/v1/project/publicJson"
        params = {"id": self._id, "t": str(int(time() * 1000))}
        self.raw_data = bytearray(requests.get(url, params=params).content)
        print("下载完成, 元数据大小:", format_size(len(self.raw_data)))

    def decrypt_raw_data(self):
        print("解密元数据")
        try:
            self.json_text = self.raw_data.decode()
        except UnicodeDecodeError:
            key = b'clipccyydsclipccyydsclipccyydscc'
            iv = b'clipteamyydsclip'
            decrypter = AES.new(key, AES.MODE_CBC, IV=iv)
            self.json_text = decrypter.decrypt(pad(self.raw_data, AES.block_size))
            self.json_text = self.json_text[:self.json_text.rfind(b'"}}') + 3]
            self.json_text = self.json_text.decode()
        print("解密完成, 解密后数据大小:", format_size(len(self.json_text.encode())))

    def get_project_json(self):
        print("加载JSON...")
        self.json = json_loads(self.json_text)  # 加载为json
        if isinstance(self.json, dict) and self.json.get("code"):
            print("获取项目JSON失败:", self.json.get("message"))
            raise ValueError("获取项目数据失败:", self.json.get("message"))

    def get_asset_urls(self):
        print("过滤出资源名")
        self.resource_list = findall(r"[0-9a-z]{32}\.\w{2,4}", self.json_text)  # 筛选资源名
        print("共找到资源 %d 个" % len(self.resource_list))

    def download_assets(self, root_path: str):
        self.get_asset_urls()  # 获取资源
        print("开始下载项目资源文件")
        kit = DownloadKit(goal_path=root_path, roads=15, file_exists="skip")  # 创建下载对象
        kit.set.interval(0.5)  # 重试间隔设置0.5秒
        for basename in self.resource_list:
            url = f"{ASSETS_URL}/{basename}"  # 拼接资源地址
            kit.add(url)  # 添加下载任务
        kit.wait(show=True)  # 显示下载进度

    def save_project_json(self, root_path: str):
        print("保存 project.json")
        with open(join(root_path, "project.json"), "w+", encoding="utf-8") as f:
            json_dump(self.json, f, ensure_ascii=False, indent=4)

    def write_zip(self, root_path: str, files_path: str):
        print("开始写入压缩包", flush=True)
        sb3_name = filter_file_name(self.title)
        try:
            with ZipFile(join(root_path, sb3_name + ".sb3"), "w", compresslevel=5) as _zip:
                file_list = self.resource_list.copy()
                file_list.append("project.json")
                print("文件数量:", len(file_list))
                for basename in file_list:
                    print("\r写入文件:", basename, end=" " * 32)
                    fp = join(files_path, basename)
                    with open(fp, "rb") as file:
                        _zip.writestr(basename, file.read())
                print()
            print("项目sb3已保存至:", join(root_path, sb3_name + ".sb3"))
        except PermissionError:
            print("项目sb3保存失败, 请检查文件是否被占用")

    def download_project(self, root_path: str):
        self.get_project_title()
        self.get_raw_data()
        self.decrypt_raw_data()
        self.get_project_json()

        dir_name = filter_file_name(self.title)
        files_path = join(root_path, dir_name)
        if not isdir(files_path):
            mkdir(files_path)
        self.download_assets(files_path)
        self.save_project_json(files_path)
        self.write_zip(root_path, files_path)


if __name__ == "__main__":
    project = Project(4864)
    project.download_project("test")
