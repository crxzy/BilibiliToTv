import requests
import re
import json
import os

BV_URL = 'https://www.bilibili.com/video/{}'
COMMENT_URL = 'https://api.bilibili.com/x/v1/dm/list.so?oid={}'
MEDIA_INFO_EXPRESS = 'window.__playinfo__=([\s\S]*?)</script>'
MEDIA_NAME_EXPRESS = '<title(.*?)</title>'
CID_EXPRESS = 'cid=(\d*)&'

class BiliSpider:
    def __init__(self, bv):
        self.target_url = BV_URL.format(bv)
        self.bv = bv
        self.header = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/72.0.3626.121 Safari/537.36",
            "Referer": "http://www.bilibili.com"
        }
    def _replace(self, name):
        vn = name.replace(' ', '_').replace('\\', '').replace('/', '')
        vn = vn.replace('*', '').replace(':', '').replace('?', '').replace('<', '')
        vn = vn.replace('>', '').replace('\"', '').replace('|', '')
        return vn

    def detect_info(self):
        resp = requests.get(self.target_url, headers=self.header)
        result = {}

        html = resp.text
        raw = re.findall(MEDIA_INFO_EXPRESS, html, re.S)
        if  raw != []:
            name = re.findall(MEDIA_NAME_EXPRESS, html, re.S)[0].split('>')[1]
            name = self._replace(name)

            result['cid'] = re.findall(CID_EXPRESS, html, re.S)[0]

            result['media_name'] = name
            result['video'] = []
            result['audio'] = []

            media = json.loads(raw[0])            
            media = media['data']            
            video_len = len(media['dash']['video'])
            audio_len = len(media['dash']['audio'])
            dash = media['dash']

            for i in range(video_len):
                m = {}
                m['url'] = dash['video'][i]['baseUrl']
                m['mimeType'] = dash['video'][i]['mimeType']
                m['frameRate'] = dash['video'][i]['frameRate']
                m['bandwidth'] = dash['video'][i]['bandwidth']
                m['width'] = dash['video'][i]['width']
                m['height'] = dash['video'][i]['height']
                result['video'].append(m)

            for i in range(audio_len):
                m = {}
                m['url'] = dash['audio'][i]['baseUrl']
                m['mimeType'] = dash['audio'][i]['mimeType']
                m['bandwidth'] = dash['audio'][i]['bandwidth']
                result['audio'].append(m)

        self.media_info = result

    def _getCommentsURL(self):
        return COMMENT_URL.format(self.media_info['cid'])

    def downloadComment(self, path='.'):
        filename = "{}{}{}.xml".format(path, os.pathsep, self.bv)
        resp = requests.get(self._getCommentsURL())
        with open(filename, 'w', encoding='utf-8') as f:
            f.write(resp.text.encode('ISO-8859-1').decode('UTF-8'))
        return filename
