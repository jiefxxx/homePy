import base64
import json
import os

import libtorrent as lt


def gen_state(h, state):
    state_str = ['queued', 'checking', 'downloading metadata',
                 'downloading', 'finished', 'seeding', 'allocating',
                 'checking fastresume']
    if h.is_paused():
        return "paused"
    return state_str[state]


def torrent_to_dict(h, full=False):
    s = h.status()
    ret = {"name": h.name(),
           "hash": str(h.info_hash()),
           "peers": s.num_peers,
           "seeds": s.num_seeds,
           "progress": s.progress,
           "downRate": s.download_rate,
           "upRate": s.upload_rate,
           "size": s.total_wanted,
           "size_down": s.total_wanted_done,
           "size_up": s.all_time_upload,
           "state": gen_state(h, s.state),
           "position": s.queue_position}

    if not full:
        return ret

    ret["path"] = h.save_path() + h.name()
    ret["files"] = []
    files = h.get_torrent_info().files()
    for i in range(0, files.num_files()):
        ret["files"].append((i, files.file_path(i), h.file_priority(i)))

    return ret


class TorrentManager:
    def __init__(self, download_path="downloads", fast_resume_config="fast_resume.json"):
        self.ses = lt.session()
        self.ses.listen_on(6881, 689)
        self.download_path = download_path
        self.fast_resume_config = fast_resume_config
        self.torrents = []
        self.fast_resume()

    def fast_resume(self):
        if not os.path.exists(self.fast_resume_config):
            return
        with open(self.fast_resume_config, "r") as f:
            infos = json.load(f)
        for info in infos:
            print(info["name"])
            h = self.ses.add_torrent({'resume_data': base64.b64decode(info["data"]),
                                      'save_path': info["path"]})
            if h.is_valid():
                self.torrents.append(h)
            else:
                print("error")

    def add_torrent_file(self, path, paused=False, auto_managed=False):
        info = lt.torrent_info(path)
        h = self.ses.add_torrent({'ti': info,
                                  'save_path': self.download_path,
                                  'storage_mode': lt.storage_mode_t(2),
                                  'paused': paused,
                                  'auto_managed': auto_managed,
                                  'duplicate_is_error': True})

        if h.is_valid():
            self.torrents.append(h)

    def get(self, info_hash):
        for h in self.torrents:
            if info_hash == str(h.info_hash()):
                return h

    def get_info(self, info_hash=None, full=False):
        ret = []
        for h in self.torrents:
            if not info_hash or info_hash == str(h.info_hash()):
                ret.append(torrent_to_dict(h, full=full))
        return ret

    def pause(self, info_hash=None):
        for h in self.torrents:
            if not info_hash or info_hash == str(h.info_hash()):
                if h.is_paused():
                    h.resume()
                else:
                    h.pause()

    def files(self, info_hash):
        ret = []
        h = self.get(info_hash)
        files = h.get_torrent_info().files()
        for i in range(0, files.num_files()):
            ret.append(files.file_path(i))
        return ret

    def path(self, info_hash):
        h = self.get(info_hash)
        return h.save_path()+"/"+h.name()

    def remove(self, info_hash):
        h = self.get(info_hash)
        self.ses.remove_torrent(h)
        self.torrents.remove(h)

    def test(self):
        for torrent in self.torrents:
            files = torrent.get_torrent_info().files()
            print(files.name())
            for i in range(0, files.num_files()):
                print(files.file_path(i))
        return {"result": None}

    def close(self):
        count = 0
        self.ses.pause()
        for torrent in self.torrents:
            torrent.save_resume_data(lt.save_resume_flags_t.flush_disk_cache | lt.save_resume_flags_t.save_info_dict)
            count += 1

        data_to_save = []
        while count > 0:
            alert = self.ses.pop_alert()
            if type(alert) == lt.save_resume_data_alert:
                h = alert.handle
                data = lt.bencode(alert.resume_data)
                data_to_save.append({"name": h.get_torrent_info().name(),
                                     "data": base64.b64encode(data).decode(),
                                     "path": h.save_path()})
                count -= 1

        with open(self.fast_resume_config, "w") as f:
            json.dump(data_to_save, f)
