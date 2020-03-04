import asyncio
import logging
import os
import zipfile

from pynet.http.exceptions import HTTPError
from streaming_form_data import StreamingFormDataParser
from streaming_form_data.targets import FileTarget, ValueTarget

import pythread
from pynet.http.handler import HTTPHandler
from pynet.http.server import HTTPServer

from torrent import TorrentManager

logging.basicConfig(level=logging.DEBUG)


def compress_folder(zip_file, path, arc_folder="/"):
    for sub_path in os.listdir(path):
        if os.path.isfile(os.path.join(path, sub_path)):
            zip_file.write(os.path.join(path, sub_path), arcname=os.path.join(arc_folder, sub_path))
        elif os.path.isdir(os.path.join(path, sub_path)):
            compress_folder(zip_file, os.path.join(path, sub_path), arc_folder=os.path.join(arc_folder, sub_path))
        else:
            print("error", sub_path)


class MainHandler(HTTPHandler):
    def GET(self, url):
        self.html_render("index.html")


class HtmlTorrentHandler(HTTPHandler):
    async def prepare(self):
        ret = await HTTPHandler.prepare(self)
        if self.header.query == "POST":
            self.data = StreamingFormDataParser(headers={'Content-Type': self.header.fields.get("Content-Type")})
            self.user_data["torrentFile"] = FileTarget("temp_torrent.torrent")
            self.data.register('file', self.user_data["torrentFile"])
            print(self.header.fields.get("Content-Length"))
        return ret

    def write(self, data_chunk):
        print(len(data_chunk))
        self.data.data_received(data_chunk)

    async def POST(self, url):
        print(self.user_data["torrentFile"].filename)
        self.user_data["TorrentManager"].add_torrent_file(self.user_data["torrentFile"].filename)
        self.response.text(200, "ok")

    def GET(self, url):
        info_hash = url.get("hash", default=None)
        if not info_hash:
            return self.html_render("torrent.html")
        info = self.user_data["TorrentManager"].get_info(info_hash=info_hash, full=True)[0]
        self.html_render("torrent_info.html", torrent_info=info)


class ApiTorrentHandler(HTTPHandler):
    compression = "gzip"

    def GET(self, url):
        info_hash = url.get("hash", default=None)
        full = url.get("full", default=False, data_type=bool)

        if url.regex[0] == "info":
            self.response.json(200, self.user_data["TorrentManager"].get_info(info_hash=info_hash, full=full))
        elif url.regex[0] == "pause":
            self.user_data["TorrentManager"].pause(info_hash=info_hash)
            self.response.text(200, "ok")
        elif url.regex[0] == "remove":
            if not info_hash:
                raise HTTPError(400)
            self.user_data["TorrentManager"].remove(info_hash)
            self.response.json(200, "ok")
        elif url.regex[0] == "download":
            if not info_hash:
                raise HTTPError(400)
            path = self.user_data["TorrentManager"].path(info_hash)
            if os.path.isfile(path):
                self.file(path, attachment=True)
            elif os.path.isdir(path):
                print(path)
                with zipfile.ZipFile(os.path.basename(path) + '.zip', 'w') as zipObj:
                    compress_folder(zipObj, path)
                self.file(os.path.basename(path)+'.zip', attachment=True)
            else:
                raise Exception("files not found for hash:", info_hash)
        else:
            raise HTTPError(404)


class JavascriptHandler(HTTPHandler):
    def GET(self, url):
        self.file("js/" + url.regex[0], cached=True)


tm = TorrentManager()

http_server = HTTPServer(template_dir="template/")

http_server.router.add_route("/", MainHandler)
http_server.router.add_route("/index.html", MainHandler)
http_server.router.add_route("/torrent.html", HtmlTorrentHandler, user_data={"TorrentManager": tm})
http_server.router.add_route("/torrent/(.*)", ApiTorrentHandler, user_data={"TorrentManager": tm})
http_server.router.add_route("/js/(.*)", JavascriptHandler)
http_server.start()

http_server.run_forever()
tm.close()
