from tv import *
from bili import *
import os
import subprocess
import urllib.parse
import sys


def _delete(f):
    if os.path.exists(f):
        os.remove(f)

if __name__ == '__main__':
    if len(sys.argv) != 2:
        os.exit(0)
    
    bv = sys.argv[1]

    t = Tv()
    devices = t.descover()
    b = BiliSpider(bv)
    b.detect_info()
    filename = b.downloadComment()

    xml2ass = 'DanmakuFactory.exe -i "{}" -o out.ass'.format(filename)
    _delete('out.ass')
    _delete('{}.flv'.format(bv))
    try:
        if subprocess.call(xml2ass, shell=True):
            raise Exception("{} failed".format(xml2ass))
        print('done')
    except Exception as e:
        print('xml2ass failed', e)


    v = "{}{}".format("http://127.0.0.1:8080/get?url=", urllib.parse.quote(b.media_info['video'][1]['url']))
    a = "{}{}".format("http://127.0.0.1:8080/get?url=", urllib.parse.quote(b.media_info['audio'][0]['url']))

    ffcommand = 'ffmpeg -i "{}" -i "{}"  -qscale "10" -vf subtitles=out.ass {}.flv'.format(v, a, bv)

    devices[1].play('http://192.168.0.103:8000/{}.flv'.format(b.bv))

    try:
        if subprocess.call(ffcommand, shell=True):
            raise Exception("{} failed".format(ffcommand))
        print('done')
    except Exception as e:
        print('ffmpeg failed', e)

    
    