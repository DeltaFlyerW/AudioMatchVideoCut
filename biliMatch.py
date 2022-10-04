from audioMatch import *


def log(*largs, mode='default', indent=None, args=None, end='\n', punc=','):
    from json import dumps
    if args is None:
        args = largs
    if mode == 'default':
        if indent is not None:
            try:
                text = dumps(args, ensure_ascii=False, indent=indent)
                text = text[1:-1]
            except:
                text = str(args)
                pass
        else:
            # for a in args:
            text = punc.join(map(str, args))
        try:
            print(text, end=end)
        except:
            for s in text:
                try:
                    print(s, end='')
                except:
                    pass
            print(end=end)
    if mode == 'list':
        print('[')
        for l in args:
            for o in l:
                text = str(o) + '\n'
                try:
                    print(text)
                except:
                    for s in text:
                        try:
                            print(s, end='')
                        except:
                            pass

        print(']')


def loadDanmuStandalone(path):
    import re
    fstr = open(path, encoding='utf-8').read()
    cid = re.search('<chatid>(.*?)</chatid>', fstr)
    if cid:
        cid = cid.group(1)
    else:
        cid = 0
    ldanmu = re.findall(r'(<d p=".*?</d>)', fstr, )
    info = re.search('<info>(.*?)</info>', fstr)
    if info is not None:
        from xml.sax.saxutils import unescape
        import json
        info = json.loads(unescape(info.group(1)))
    return ldanmu, cid, info


def mPrint(*args, end='\n'):
    global initPrint
    if initPrint == False:
        open('log.txt', 'w', encoding='utf-8').close()
        initPrint = True
    open('log.txt', 'a', encoding='utf-8').write(' '.join(map(str, args)) + end)
    print(*args, end=end)



try:
    # ForCMD
    import os
    import sys

    curPath = os.path.abspath(os.path.dirname(__file__))
    rootPath = os.path.split(curPath)[0]
    sys.path.append(rootPath)

    from moviepy.video.io.VideoFileClip import VideoFileClip
    from moviepy.audio.io.AudioFileClip import AudioFileClip

    import binascii
    import numpy as np

    initPrint = False


    class udanmu:

        @staticmethod
        def getmid(content, pattern, mode='nWarning', punc='()', repeatcount=-1, patternfront='', patternafter=''):
            if patternfront == '':
                patternfront = pattern[:pattern.find(punc)]
            if patternafter == '':
                patternafter = pattern[pattern.find(punc) + len(punc):]
                if patternafter == '':
                    patternafter = None

            beginbit = content.find(patternfront)
            if beginbit == -1:
                return -1
            beginbit += len(patternfront)
            if patternafter is not None:
                endbit = content.find(patternafter, beginbit)
                if endbit == -1:
                    if mode == 'Warning':
                        print(content)
                        print(pattern)
                        raise ValueError('GetMidError:NoEndBit')
                    return -2
            else:
                return content[beginbit:]
            if mode == 'Warning':
                if repeatcount == -1:
                    if udanmu.getmid(content[endbit:], pattern, punc, 'NoWarning', 1) != -1:
                        print(content)
                        print(pattern)
                        raise ValueError('GetMidWarning:RepeatPattern')
            else:
                if repeatcount > 1:
                    return udanmu.getmid(content[endbit:], pattern, punc, 'Warning', repeatcount - 1)
            return content[beginbit:endbit]

        @staticmethod
        def mfindc(mstr: str, keyword: str, count: int):
            pos = 0
            for i in range(count):
                pos = mstr.find(keyword, pos + len(keyword))
            return pos

        @staticmethod
        def mfindm(mstr, keyword, cstart):
            pstart = udanmu.mfindc(mstr, keyword, cstart)
            return mstr[pstart + len(keyword):mstr.find(keyword, pstart + len(keyword))]

        @staticmethod
        def ensureDir(path):
            from os.path import isdir
            from os import makedirs
            if not isdir(path):
                makedirs(path)
                return False
            else:
                return True

        @staticmethod
        def removeRepeatDanmu(ldanmu, reverse=False):  # 去除重复弹幕
            ldanmu = udanmu.sortById(ldanmu, reverse=reverse)

            tdanmuid = ''
            tldanmu = []
            for danmu in ldanmu:
                danmuid = udanmu.getiddanmu(danmu)
                if danmuid != tdanmuid:
                    tldanmu.append(danmu)
                    tdanmuid = danmuid
            udanmu.sortByTime(ldanmu)
            return tldanmu

        @staticmethod
        def sortById(ldanmu, reverse=False):
            # for d in ldanmu:
            ldanmu.sort(key=udanmu.getiddanmu, reverse=reverse)
            # ldanmu.sort(key=getiddanmu, reverse=reverse)
            return ldanmu

        @staticmethod
        def sortByTime(ldanmu, reverse=False):
            # for d in ldanmu:
            ldanmu.sort(key=lambda x: (float(udanmu.gettime(x)), udanmu.getcontent(x)), reverse=reverse)
            # ldanmu.sort(key=getiddanmu, reverse=reverse)
            return ldanmu

        @staticmethod
        def sortByPos(ldanmu, reverse=False):
            ldanmu.sort(key=lambda x: (float(udanmu.getPos(x)), udanmu.getcontent(x)), reverse=reverse)
            return ldanmu

        @staticmethod
        def addsort(oldanmu: list, nldanmu: list):
            if udanmu.gettime(nldanmu[0]) > udanmu.gettime(nldanmu[1]):
                nldanmu.reverse()
            if udanmu.gettime(oldanmu[0]) > udanmu.gettime(oldanmu[1]):
                oldanmu.reverse()
            for indanmu, ndanmu in enumerate(nldanmu):
                ntime = udanmu.gettime(ndanmu)
                otime = udanmu.gettime(oldanmu[-1])
                if ntime < otime:
                    oldanmu = oldanmu + nldanmu[indanmu:]
                    break
                if ndanmu in oldanmu:
                    continue
                fbreak = False
                for iodanmu in range(len(oldanmu)):
                    if iodanmu == 0: continue
                    otime = udanmu.gettime(oldanmu[-iodanmu - 1])
                    if otime > ntime:
                        oldanmu.insert(-iodanmu, ndanmu)
                        fbreak = True
                        break
                if not fbreak:
                    oldanmu = [ndanmu] + oldanmu
            return oldanmu

        @staticmethod
        def getPos(danmu):
            if isinstance(danmu, str):
                return float(danmu[danmu.find('"') + 1:danmu.find(',')])
            if isinstance(danmu, list):
                if len(danmu) > 8:
                    return danmu[0]

        @staticmethod
        def diffrence(oldanmu, nldanmu):  # 返回前者没有的弹幕
            if len(oldanmu) == 0:
                return nldanmu
            loid = set(map(udanmu.getiddanmu, oldanmu))
            lndanmu = []
            for danmu in nldanmu:
                did = udanmu.getiddanmu(danmu)
                if did not in loid:
                    lndanmu.append(danmu)
                loid.add(did)
            return lndanmu

        @staticmethod
        def merge(oldanmu, nldanmu):  # 合并弹幕
            oldanmu.extend(udanmu.diffrence(oldanmu, nldanmu))

        @staticmethod
        def getDanmutype(danmu):
            if isinstance(danmu, str):
                return int(udanmu.mfindm(danmu, ',', 1))
            if isinstance(danmu, list):
                if len(danmu) > 8:
                    return danmu[1]

        @staticmethod
        def getfontsize(danmu):
            if isinstance(danmu, str):
                return int(udanmu.mfindm(danmu, ',', 2))
            if isinstance(danmu, list):
                if len(danmu) > 8:
                    return danmu[2]

        @staticmethod
        def getcolor(danmu):
            if isinstance(danmu, str):
                return int(udanmu.mfindm(danmu, ',', 3))
            if isinstance(danmu, list):
                if len(danmu) > 8:
                    return danmu[3]

        @staticmethod
        def gettime(danmu):
            if isinstance(danmu, str):
                return int(udanmu.mfindm(danmu, ',', 4))
                # try:
                #     res= int(danmu[mfindc(danmu, ',', 4) + 1:mfindc(danmu, ',', 5)])
            #             # except Exception as e:
            #     print(danmu)
            #     raise e
            # return res

            if isinstance(danmu, list):
                if len(danmu) > 8:
                    return danmu[4]

        @staticmethod
        def getpooltype(danmu) -> int:
            if isinstance(danmu, str):
                return int(udanmu.mfindm(danmu, ',', 5))
            if isinstance(danmu, list):
                if len(danmu) > 8:
                    return danmu[5]

        @staticmethod
        def getuserhash(danmu):
            if isinstance(danmu, str):
                return udanmu.mfindm(danmu, ',', 6)
            if isinstance(danmu, list):
                if len(danmu) > 8:
                    return danmu[6]

        @staticmethod
        def getiddanmu(danmu):
            if isinstance(danmu, str):
                pstart = udanmu.mfindc(danmu, ',', 7) + 1
                pend = danmu.find(',', pstart)
                if pend != -1:
                    pend = min(pend, danmu.find('"', pstart))
                else:
                    pend = danmu.find('"', pstart)
                return danmu[pstart: pend]
            if isinstance(danmu, list):
                if len(danmu) > 8:
                    return danmu[6]

        @staticmethod
        def getcontent(danmu):
            if isinstance(danmu, str):
                return danmu[danmu.find('">') + 2:danmu.find('</d>')]
            if isinstance(danmu, list):
                if len(danmu) > 8:
                    return danmu[8]

        @staticmethod
        def dumpdanmu(danmuinfo):
            pos = str(round(danmuinfo[0], 3)).split('.')
            pos[1] = pos[1].ljust(5, '0')
            # wait(pos)
            sdanmu = f'<d p="{pos[0]}.{pos[1]},{",".join(map(str, danmuinfo[1:8]))}">{danmuinfo[8]}</d>'
            return sdanmu

        @staticmethod
        def applyOffset(danmu, offset):
            pos = udanmu.getPos(danmu) + offset
            return '<d p="' + str(pos + offset) + danmu[danmu.find(','):]

        @staticmethod
        def savedanmu(ldanmu: list, path, ndanmu=3000, slcid='0', info=None):  # 保存弹幕到文件中
            from xml.sax.saxutils import escape

            ltext = [
                '<?xml version="1.0" encoding="UTF-8"?><i><chatserver>chat.bilibili.com</chatserver><chatid>{}</chatid><mission>0</mission><maxlimit>{}</maxlimit><state>0</state><real_name>0</real_name><source>DF</source>'.format(
                    slcid, str(ndanmu))]
            if info != None:
                ltext.append(f'<info>{escape(json.dumps(info, ensure_ascii=False))}</info>')
            ltext.extend(ldanmu)
            ltext.append('</i>')

            open(path, 'w', encoding='utf-8').write(''.join(ltext))

        @staticmethod
        def getdanmufromfile(path):  # 从文件中读取弹幕,返回 (弹幕列表,弹幕服务器,弹幕池大小,cid)
            import re
            # if path[-3:] != 'xml':
            #     return []
            with open(path, 'r', encoding='utf-8') as f:
                fstr = f.read()
            # print(path)
            # cid = re.search(r'<chatid>(\d*)</chatid>', fstr).group(1)
            cid = udanmu.getmid(fstr, r'<chatid>()</chatid>', mode='n')
            chatserver = udanmu.getmid(fstr, r'<chatserver>()</chatserver>', mode='n')
            ndanmu = int(udanmu.getmid(fstr, '<maxlimit>()</maxlimit>', mode='n'))
            # if cid not in self.lcid:
            #     self.lcid.append(cid)
            p1 = r'(<d p=".*?</d>)'

            ldanmu = re.findall(p1, fstr, re.DOTALL)
            # if isinstance(cid, int):
            #     return []
            return ldanmu, chatserver, ndanmu, cid

        @staticmethod
        def setPosOffset(danmu, offset):
            return '<d p="' + str(udanmu.getPos(danmu) + offset) + danmu[danmu.find(','):]


    def copiedPath(spath: str, sortWindowsStyle=True):
        spath = spath.split('\n')
        spath = [s.strip().rstrip().strip('"').rstrip('"') for s in filter(lambda x: len(x.strip()) > 1, spath)]
        if sortWindowsStyle:
            # import re
            # spath.sort(key=lambda x: (int(re.findall(r'.*?(\d+)', x)[0]), x))
            import natsort
            return natsort.humansorted(spath)
        else:
            return spath


    def applyOffset(ldanmu, loffset, originBase=False):
        # [(0, 0), (142.047, 5.0), (444.191, 10.0), (486.313, 13.0), (614.316, 18.0), (1302.132, 22.0)]
        loffset = [[0, 0]] + loffset
        ioffset = 0
        udanmu.sortByPos(ldanmu)
        for idanmu, danmu in enumerate(ldanmu):
            if not originBase:
                if ioffset + 1 < len(loffset) and udanmu.getPos(ldanmu[idanmu]) >= loffset[ioffset + 1][0]:
                    ioffset += 1
            else:
                if ioffset + 1 < len(loffset) and udanmu.getPos(ldanmu[idanmu]) + loffset[ioffset][1] >= \
                        loffset[ioffset + 1][0]:
                    ioffset += 1
            ldanmu[idanmu] = udanmu.setPosOffset(danmu, loffset[ioffset][1])
        return ldanmu


    import json


    class mjson:
        @staticmethod
        def dump(obj, path, indent='\t', safe=False):
            class MyEncoder(json.JSONEncoder):
                def default(self, obj):
                    import numpy
                    if isinstance(obj, numpy.integer):
                        return int(obj)
                    elif isinstance(obj, numpy.floating):
                        return float(obj)
                    elif isinstance(obj, numpy.ndarray):
                        return obj.tolist()
                    else:
                        return super(MyEncoder, self).default(obj)

            lob = json.dumps(obj, ensure_ascii=False, indent=indent, cls=MyEncoder)
            if safe and os.path.isfile(path):
                open(path + '.tmp', 'w', encoding='utf-8').write(lob)
                os.remove(path)
                os.rename(path + '.tmp', path)
            else:

                open(path, 'w', encoding='utf-8').write(lob)

        @staticmethod
        def load(path, default=None):
            if default is None:
                k = open(path, 'r', encoding='utf-8').read()
                return json.loads(k)
            else:
                if not os.path.isfile(path):
                    return default
                else:
                    k = open(path, 'r', encoding='utf-8').read()
                    return json.loads(k)


    def parse(url, headers=None, timeout=5, proxies=None, session=None):
        import requests
        from requests.adapters import HTTPAdapter

        if headers is None:
            headers = {
                'accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.9',
                'accept-encoding': 'gzip, deflate', 'accept-language': 'zh-CN,zh;q=0.9,en;q=0.8,ja;q=0.7',
                'cache-control': 'max-age=0', 'dnt': '1', 'sec-fetch-dest': 'document', 'sec-fetch-mode': 'navigate',
                'sec-fetch-site': 'none', 'sec-fetch-user': '?1', 'upgrade-insecure-requests': '1',
                'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/83.0.4103.116 Safari/537.36'}
        if proxies == True:
            proxies = {
                'http': '127.0.0.1:7890',
                'https': '127.0.0.1:7890'
            }
        if session is None:
            from requests.adapters import HTTPAdapter
            from requests.packages.urllib3 import Retry
            retries = Retry(total=0,
                            backoff_factor=0.1,
                            status_forcelist=[500, 502, 503, 504])
            session = requests.session()
            http = requests.adapters.HTTPAdapter(max_retries=retries)
            session.mount('http://', http)
            session.mount('https://', http)
        response = session.get(url, headers=headers, timeout=timeout, proxies=proxies, verify=False, )
        if ('Content-Encoding' in response.headers and response.headers['Content-Encoding'] == 'br'):
            import brotli
            data = brotli.decompress(response.content)
            data = data.decode('utf-8')
        else:
            data = response.content.decode()
        return data


    from typing import List


    def copiedPath(spath: str, sortWindowsStyle=True) -> List[fpath]:
        spath = spath.split('\n')
        lpath = []
        for p in spath:
            if len(p.strip()) == 0:
                continue
            lpath.append(fpath(p.rstrip().strip().rstrip('"').strip('"')))
        if sortWindowsStyle:
            # import re
            # spath.sort(key=lambda x: (int(re.findall(r'.*?(\d+)', x)[0]), x))
            import natsort
            return natsort.humansorted(lpath)
        else:
            return lpath


    def help_message():
        return '' \
               '这是由DF开发的弹幕删减匹配工具,\n' \
               '以 https://github.com/AswinRetnakumar/PyDejaVu 这一项目为基础,\n' \
               '通过对删减版与完整版视频的音频特征进行提取和匹配,以获得删减片段的具体位置,\n' \
               '从而实现将删减版弹幕调整成完整版可用弹幕的目的.\n\n' \
               '使用前,需要准备好删减版和完整版的视频,若有删减版视频同名的弹幕文件在同目录下,' \
               '在使用后会在完整版视频目录下生成同名弹幕文件,否则会生成一个同名匹配结果.\n\n'


    def matchVideo(pOriginVideo, pClipedVideo, searchAllFirst=False, fWarn=True, uploadResult=False):

        pOriginVideo = fpath(pOriginVideo)
        if not pOriginVideo.exists():
            if fWarn:
                print(pOriginVideo, 'not exist')
            return
        if pOriginVideo.extension('xml').exists():
            log(pOriginVideo.fileName(), '已有同名弹幕文件,自动跳过')
            return
        if pOriginVideo.isDir():
            info = mjson.load(pOriginVideo / 'entry.json')
            biliInfo = {
                'cid': info['source']['cid'],
                'title': info['title'],
                'index': info['ep']['index'],
                'index_title': info['ep']['index_title'],
            }

            if not (pOriginVideo / info['type_tag'] / '0.blv').exists():
                pOriginVideo = pOriginVideo / info['type_tag'] / 'audio.m4s'
            else:
                pOriginVideo = pOriginVideo / info['type_tag'] / '0.blv'

        pClipedVideo = fpath(pClipedVideo)

        ldanmu = None
        if pClipedVideo.isDir():
            ldanmu, chatserver, ndanmu, cid = udanmu.getdanmufromfile(pClipedVideo / 'danmaku.xml')
            info = mjson.load(pClipedVideo / 'entry.json')
            biliInfo = {
                'cid': info['source']['cid'],
                'title': info['title'],
                'index': info['ep']['index'],
                'index_title': info['ep']['index_title'],
            }

            if not (pClipedVideo / info['type_tag'] / '0.blv').exists():
                pClipedVideo = pClipedVideo / info['type_tag'] / 'audio.m4s'
            else:
                pClipedVideo = pClipedVideo / info['type_tag'] / '0.blv'
        else:
            if pClipedVideo.extension('xml').exists():

                ldanmu, chatserver, ndanmu, cid = udanmu.getdanmufromfile(pClipedVideo.extension('xml'))
                log(pClipedVideo.extension('xml'))

                biliInfo = {
                    'cid': cid
                }
            else:
                biliInfo = {
                }
                log('[警告]', pClipedVideo.fileName(), '同目录下未找到同名弹幕文件,本次匹配仅会生成一个匹配结果文件!!')
                # return
        import re
        info = re.search(r'Av(\d+),P(\d+)', pClipedVideo.fileName())
        if not pOriginVideo.endswith('mp3') and not pOriginVideo.endswith('m4s'):
            oAudio = VideoFileClip(pOriginVideo).audio
        else:
            if pOriginVideo.endswith('m4s'):
                pOriginVideo = pOriginVideo.rename('mp3')
            oAudio = AudioFileClip(pOriginVideo)

        if not pClipedVideo.endswith('mp3') and not pClipedVideo.endswith('m4s'):
            nAudio = VideoFileClip(pClipedVideo).audio
        else:
            nAudio = AudioFileClip(pClipedVideo)
        ss = None
        ipage = None
        nRes = None

        try:
            if info is not None:
                aid = info.group(1)
                ipage = info.group(2)
                ipage = str(int(ipage) - 1)
                print('https://www.bilibili.com/video/av' + aid)
                page = parse('https://www.bilibili.com/video/av' + aid)
                ss = re.search(r'www.bilibili.com/bangumi/play/ss(\d+)', page, re.DOTALL)
                if ss is not None:
                    ss = ss.group(1)
                #     url = f'http://152.32.146.234:400/requestOffset?ss={str(ss)}&index={str(ipage)}' \
                #         f'&clip={str(nAudio.duration)}&complete={str(oAudio.duration)}'
                #     response = parse(url)
                #     if response[0] != 'n':
                #         response = json.loads(response)
                #         nRes = response['offset']
                #         print('已从服务器上匹配音频信息')
        except:
            warn()
        self = VideoAudio()
        if nRes is None:
            self.match(pClipedVideo, pOriginVideo, searchAllFirst, oAudio, nAudio, biliInfo, lang="zh")
        offset = []
        for p in nRes:
            offset.append((p['pos'], p['offset_seconds']))
        result = {
            'sourceFile': {
                'fileName': pOriginVideo.fileName(),
                'duration': self.oDuration,
            },
            'clippedFile': biliInfo,
            'offset': nRes
        }
        if ldanmu is not None:
            ldanmu = applyOffset(ldanmu, offset)
            udanmu.savedanmu(ldanmu, pOriginVideo.extension('xml'),
                             ndanmu=3000, slcid=cid, info=result
                             )
            print(pOriginVideo, '音频特征匹配完成,已生成对应弹幕')
        else:
            pClipedVideo.extension('_匹配结果.json').dump(result)
        self.result = offset
        import re
        if ss is None:
            ss = 0
            ipage = 0
        if uploadResult:
            try:
                parse(f'http://152.32.146.234:400/uploadOffset?ss={str(ss)}&index={str(ipage)}'
                      f'&offset={json.dumps(result, ensure_ascii=False)}'
                      f'&clip={str(nAudio.duration)}&complete={str(oAudio.duration)}')
            except:
                pass


    if __name__ == '__main__':
        try:
            # batchExec()
            # update(r'E:\DF_File\Temp\勇者义彦\勇者义彦\第01季\勇者义彦与魔王之城')
            print(help_message())
            print('请将删减版视频文件拖放至此窗口或输入其路径,然后单击回车:')
            lClipped = []
            while True:

                s = input()
                lClipped.append(s)
                if len(s) < 2:
                    break
                print('\r继续添加更多视频文件,或单击回车以继续:', end='')
            from time import sleep

            sleep(1)
            lClipped = copiedPath('\n'.join(lClipped))

            print('\n请将完整版视频文件拖放至此窗口或输入其路径,然后单击回车:')

            lOrigin = []
            while True:
                s = input()
                lOrigin.append(s)
                if len(s) < 2:
                    break
                print('\r继续添加更多视频文件,或单击回车以继续:', end='')

            lOrigin = copiedPath('\n'.join(lOrigin))

            assert len(lOrigin) == len(lClipped), f'输入的两类视频数量应当一致' \
                f' 完整版:{str(len(lOrigin))}件,删减版:{str(len(lClipped))}件'

            for oVideo, nVideo in zip(lOrigin, lClipped):
                print(nVideo.fileName(), '=>', oVideo.fileName())
            input('\n请检查两类视频是否对应,继续请按回车.\n'
                  '如有错误,先检查按文件名排序是否一致,\n'
                  '后重启程序以重新输入.\n')

            # import multiprocessing
            #
            # pool = multiprocessing.Pool(4)
            config = mjson.load("data/config.json")
            if config.get("uploadResult", True):
                print("匹配结果将上传至服务器, 用于加载外站弹幕, 可在data/config.json更改此项设置")

            for oVideo, nVideo in zip(lOrigin, lClipped):
                # pool.apply_async(videoAudio, (oVideo, nVideo))
                matchVideo(oVideo, nVideo, uploadResult=config.get("uploadResult", True))

            input('视频匹配已完成,本脚本还有配套的扩展程序,\n'
                  '可在B站自动加载匹配好的弹幕,\n'
                  '项目地址 https://github.com/DeltaFlyerW/DF_DanmakuExtension\n'
                  '欢迎加入开发者的小群吹水,809248863\n')
            # pool.close()
            # pool.join()

        except AssertionError:

            warn()
            input('请重启脚本')
        except:
            warn()
            input('脚本发生未知错误,如需排错,请联系开发者,\n'
                  f'并发送{os.getcwd()}\\log.txt 这一文件')

except:
    warn()
    input('www')
