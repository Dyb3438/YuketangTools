import requests
from PyQt5.QtCore import pyqtSignal, QObject, QThread
import json
import cv2
import math
import time
import random

class Http(QObject):
    update = pyqtSignal(dict)
    def __init__(self, user_id, auth):
        super().__init__()
        self.user_id = user_id
        self.auth = auth

        self.session = requests.Session()
        self.threads = []
        self.thread_point = 0

        self.web_login()
        return
    
    def web_login(self):
        data = {"UserID": int(self.user_id), "Auth": str(self.auth)}
        self.session.post('https://changjiang.yuketang.cn/pc/web_login', data=json.dumps(data))
        return
    
    def course_list(self):
        list_ = self.session.get('https://changjiang.yuketang.cn/v2/api/web/courses/list?identity=2').json()
        return list_
    
    def online_learn_list(self, classroom):
        url = 'https://changjiang.yuketang.cn/v2/api/web/logs/learn/%d?actype=15&page=0&offset=999&sort=-1' % classroom
        list_ = self.session.get(url).json()
        return list_
    
    def online_courseware_list(self, classroom_id, courseware_id):
        url = 'https://changjiang.yuketang.cn/c27/online_courseware/xty/kls/pub_news/%d/' % courseware_id
        header = {
            'xtbz': 'ykt',
            'classroom-id': str(classroom_id)
        }
        list_ = self.session.get(url, headers=header).json()
        return list_
    
    def addVideoThread(self, video_info):
        video_info['user_id'] = self.user_id
        t = VideoThread(self.session, video_info)
        t.finished.connect(self.nextThread)
        t.updata_process.connect(self.update_process)
        self.threads.append(t)
        return
    
    def addPicThread(self, video_info):
        video_info['user_id'] = self.user_id
        t = PicThread(self.session, video_info)
        t.finished.connect(self.nextThread)
        t.updata_process.connect(self.update_process)
        self.threads.append(t)
        return
    
    def addCommentThread(self, video_info):
        video_info['user_id'] = self.user_id
        t = CommentThread(self.session, video_info)
        t.finished.connect(self.nextThread)
        t.updata_process.connect(self.update_process)
        self.threads.append(t)
        return
    
    def getThreadLength(self):
        return len(self.threads)
    
    def clearAllThread(self):
        self.stopAllThread()
        self.threads = []
        self.thread_point = 0
        return
    
    def startAllThread(self):
        for thread in self.threads:
            thread.start()
            self.thread_point += 1
            break
        return
    
    def nextThread(self):
        if self.thread_point >= len(self.threads):
            return
        print('next Thread')
        self.threads[self.thread_point].start()
        self.thread_point += 1
        return
    
    def stopAllThread(self):
        for thread in self.threads:
            thread.kill.emit()
        return
    
    def update_process(self, val):
        self.update.emit({
            'point': self.thread_point,
            'total': len(self.threads),
            'val': val
        })

class PicThread(QThread):
    kill = pyqtSignal()
    finished = pyqtSignal()
    updata_process = pyqtSignal(float)
    def __init__(self, session:requests.Session, pic_info):
        super().__init__()
        self.session = session
        self.pic_info = pic_info
        return
    
    def run(self):
        print('开始新的图文')
        self.updata_process.emit(0.)
        picture_info = self.getPictureTextInfo()
        sku_id = picture_info['data']['sku_id']
        self.updata_process.emit(0.5)
        self.recordPictureText(sku_id)
        self.finished.emit()
        self.updata_process.emit(1.0)
        return
    
    def getPictureTextInfo(self):
        url = 'https://changjiang.yuketang.cn/mooc-api/v1/lms/learn/leaf_info/%d/%d/' % (self.pic_info['classroom_id'], self.pic_info['id'])
        header = {
            'xtbz': 'ykt',
            'classroom-id': str(self.pic_info['classroom_id'])
        }
        list_ = self.session.get(url, headers=header).json()
        return list_
    
    def recordPictureText(self, sku_id):
        url = 'https://changjiang.yuketang.cn/mooc-api/v1/lms/learn/user_article_finish/%d/?cid=%d&sid=%d' % (self.pic_info['id'], self.pic_info['classroom_id'], sku_id)
        header = {
            'xtbz': 'ykt',
            'classroom-id': str(self.pic_info['classroom_id'])
        }
        list_ = self.session.get(url, headers=header).json()
        return list_



class VideoThread(QThread):
    kill = pyqtSignal()
    finished = pyqtSignal()
    updata_process = pyqtSignal(float)
    def __init__(self, session:requests.Session, video_info):
        super().__init__()
        self.session = session
        self.video_info = video_info
        self.kill_flag = False
        self.kill.connect(self.killThis)
        return
    
    def run(self):
        print('开始新的视频')
        self.updata_process.emit(0.)
        snapshot = self.getSnapshot()
        if len(snapshot['data'].keys()) != 0:
            if snapshot['data'][str(self.video_info['id'])]['completed'] == 1:
                self.finished.emit()
                self.updata_process.emit(1.)
                return
        last_point = 0
        video_url, sku_id, cc = self.getVideo()

        heartbeats = []
        self.sendHeartBeat(heartbeats)

        time.sleep(1.5)

        self.video_info['last_point'] = last_point
        self.video_info['video_len'] = 0.
        self.video_info['sku_id'] = sku_id
        self.video_info['cc'] = cc

        sq = 1
        heartbeats.append(self.loadstart(0, sq))
        sq += 1
        heartbeats.append(self.loadeddata(0, sq))
        self.video_info['video_len'] = video_len = self.getVideoLength(video_url)

        # if len(snapshot['data'].keys()) != 0:
            # self.video_info['last_point'] = last_point = snapshot['data'][str(self.video_info['id'])]['last_point']
        
        sq += 1
        heartbeats.append(self.playing(last_point, sq))
        sq += 1
        heartbeats.append(self.pause(last_point, sq))
        sq += 1
        heartbeats.append(self.stalled(last_point, sq))
        
        self.sendHeartBeat(heartbeats)
        heartbeats = []

        time.sleep(1.5)
        sq += 1
        heartbeats.append(self.play(last_point, sq))
        self.sendHeartBeat(heartbeats)
        heartbeats = []

        sq += 1
        heartbeats.append(self.playing(last_point, sq))
        time.sleep(4)
        sq += 1
        heartbeats.append(self.stalled(last_point, sq))
        while last_point < video_len:
            if self.kill_flag:
                self.finished.emit()
                return
            sq += 1
            heartbeats.append(self.heartbeat(last_point, sq))
            self.updata_process.emit(last_point / self.video_info['video_len'])
            if len(heartbeats) == 6:
                self.sendHeartBeat(heartbeats)
                heartbeats = []
            time.sleep(5)
            last_point += 100.
        sq += 1
        heartbeats.append(self.heartbeat(video_len, sq))
        self.sendHeartBeat(heartbeats)
        self.finished.emit()
        self.updata_process.emit(1.)
        return
    
    def getSnapshot(self):
        url = 'https://changjiang.yuketang.cn/video-log/get_video_watch_progress/?cid=%d&user_id=%d&classroom_id=%d&video_type=video&vtype=rate&video_id=%d&snapshot=1' \
            %(int(self.video_info['course_id']), int(self.video_info['user_id']), int(self.video_info['classroom_id']), int(self.video_info['id']))
        header = {
            'xtbz': 'ykt',
            'classroom-id': str(self.video_info['classroom_id'])
        }
        result = self.session.get(url, headers=header).json()
        return result
    
    def getVideo(self):
        url = "https://changjiang.yuketang.cn/mooc-api/v1/lms/learn/leaf_info/%d/%d/" % (int(self.video_info['classroom_id']), int(self.video_info['id']))
        header = {
            'xtbz': 'ykt',
            'classroom-id': str(self.video_info['classroom_id'])
        }
        result = self.session.get(url, headers=header).json()
        sku_id = result['data']['sku_id']
        url2 = "https://changjiang.yuketang.cn/api/open/audiovideo/playurl?video_id=%s&provider=cc&file_type=1&is_single=0&domain=changjiang.yuketang.cn" % result['data']['content_info']['media']['ccid']
        result2 = self.session.get(url2, headers=header).json()
        return result2['data']['playurl']['sources']['quality10'][0], sku_id, result['data']['content_info']['media']['ccid']
    
    def getVideoLength(self, video_url):
        cap = cv2.VideoCapture(video_url)
        # file_path是文件的绝对路径，防止路径中含有中文时报错，需要解码
        if cap.isOpened():  # 当成功打开视频时cap.isOpened()返回True,否则返回False
            # get方法参数按顺序对应下表（从0开始编号)
            rate = cap.get(5)  # 帧速率
            FrameNumber = cap.get(7)  # 视频文件的帧数
            duration = FrameNumber / rate  # 帧速率/视频总帧数 是时间，除以60之后单位是分钟
            time = math.ceil(duration * 10)
            return time / 10
        else:
            return 0
    
    def heartbeat(self, cp, sq):
        package = {
            'i': 100,
            'et': 'heartbeat',
            'p': 'web',
            'n': 'ali-cdn.xuetangx.com',
            'lob': 'ykt',
            'cp': cp,
            'fp': 0,
            'tp': int(self.video_info['last_point']),
            'sp': 1,
            'ts': int(time.time() * 1000),
            'u': int(self.video_info['user_id']),
            'uip': '',
            'c': int(self.video_info['course_id']),
            'v': int(self.video_info['id']),
            'skuid': int(self.video_info['sku_id']),
            'classroomid': str(self.video_info['classroom_id']),
            'cc': self.video_info['cc'],
            'd': self.video_info['video_len'],
            'pg': str(self.video_info['id']) + 'ui6j',
            'sq': sq,
            't': 'video',
            'cards_id': '',
            'slide': 0,
            'v_url': ''
        }
        return package
    
    def loadstart(self, cp, sq):
        package = {
            'i': 5,
            'et': 'loadstart',
            'p': 'web',
            'n': 'ali-cdn.xuetangx.com',
            'lob': 'ykt',
            'cp': cp,
            'fp': 0,
            'tp': 0,
            'sp': 1,
            'ts': int(time.time() * 1000),
            'u': int(self.video_info['user_id']),
            'uip': '',
            'c': int(self.video_info['course_id']),
            'v': int(self.video_info['id']),
            'skuid': int(self.video_info['sku_id']),
            'classroomid': str(self.video_info['classroom_id']),
            'cc': self.video_info['cc'],
            'd': self.video_info['video_len'],
            'pg': str(self.video_info['id']) + 'ui6j',
            'sq': sq,
            't': 'video',
            'cards_id': '',
            'slide': 0,
            'v_url': ''
        }
        return package
    
    def loadeddata(self, cp, sq):
        package = {
            'i': 5,
            'et': 'loadeddata',
            'p': 'web',
            'n': 'ali-cdn.xuetangx.com',
            'lob': 'ykt',
            'cp': cp,
            'fp': 0,
            'tp': 0,
            'sp': 1,
            'ts': int(time.time() * 1000),
            'u': int(self.video_info['user_id']),
            'uip': '',
            'c': int(self.video_info['course_id']),
            'v': int(self.video_info['id']),
            'skuid': int(self.video_info['sku_id']),
            'classroomid': str(self.video_info['classroom_id']),
            'cc': self.video_info['cc'],
            'd': self.video_info['video_len'],
            'pg': str(self.video_info['id']) + 'ui6j',
            'sq': sq,
            't': 'video',
            'cards_id': '',
            'slide': 0,
            'v_url': ''
        }
        return package
    
    def playing(self, cp, sq):
        package = {
            'i': 5,
            'et': 'playing',
            'p': 'web',
            'n': 'ali-cdn.xuetangx.com',
            'lob': 'ykt',
            'cp': cp,
            'fp': 0,
            'tp': int(self.video_info['last_point']),
            'sp': 1,
            'ts': int(time.time() * 1000),
            'u': int(self.video_info['user_id']),
            'uip': '',
            'c': int(self.video_info['course_id']),
            'v': int(self.video_info['id']),
            'skuid': int(self.video_info['sku_id']),
            'classroomid': str(self.video_info['classroom_id']),
            'cc': self.video_info['cc'],
            'd': self.video_info['video_len'],
            'pg': str(self.video_info['id']) + 'ui6j',
            'sq': sq,
            't': 'video',
            'cards_id': '',
            'slide': 0,
            'v_url': ''
        }
        return package
    
    def pause(self, cp, sq):
        package = {
            'i': 5,
            'et': 'pause',
            'p': 'web',
            'n': 'ali-cdn.xuetangx.com',
            'lob': 'ykt',
            'cp': cp,
            'fp': 0,
            'tp': int(self.video_info['last_point']),
            'sp': 1,
            'ts': int(time.time() * 1000),
            'u': int(self.video_info['user_id']),
            'uip': '',
            'c': int(self.video_info['course_id']),
            'v': int(self.video_info['id']),
            'skuid': int(self.video_info['sku_id']),
            'classroomid': str(self.video_info['classroom_id']),
            'cc': self.video_info['cc'],
            'd': self.video_info['video_len'],
            'pg': str(self.video_info['id']) + 'ui6j',
            'sq': sq,
            't': 'video',
            'cards_id': '',
            'slide': 0,
            'v_url': ''
        }
        return package
    
    def stalled(self, cp, sq):
        package = {
            'i': 5,
            'et': 'stalled',
            'p': 'web',
            'n': 'ali-cdn.xuetangx.com',
            'lob': 'ykt',
            'cp': cp,
            'fp': 0,
            'tp': int(self.video_info['last_point']),
            'sp': 1,
            'ts': int(time.time() * 1000),
            'u': int(self.video_info['user_id']),
            'uip': '',
            'c': int(self.video_info['course_id']),
            'v': int(self.video_info['id']),
            'skuid': int(self.video_info['sku_id']),
            'classroomid': str(self.video_info['classroom_id']),
            'cc': self.video_info['cc'],
            'd': self.video_info['video_len'],
            'pg': str(self.video_info['id']) + 'ui6j',
            'sq': sq,
            't': 'video',
            'cards_id': '',
            'slide': 0,
            'v_url': ''
        }
        return package
    
    def play(self, cp, sq):
        package = {
            'i': 5,
            'et': 'play',
            'p': 'web',
            'n': 'ali-cdn.xuetangx.com',
            'lob': 'ykt',
            'cp': cp,
            'fp': 0,
            'tp': int(self.video_info['last_point']),
            'sp': 1,
            'ts': int(time.time() * 1000),
            'u': int(self.video_info['user_id']),
            'uip': '',
            'c': int(self.video_info['course_id']),
            'v': int(self.video_info['id']),
            'skuid': int(self.video_info['sku_id']),
            'classroomid': str(self.video_info['classroom_id']),
            'cc': self.video_info['cc'],
            'd': self.video_info['video_len'],
            'pg': str(self.video_info['id']) + 'ui6j',
            'sq': sq,
            't': 'video',
            'cards_id': '',
            'slide': 0,
            'v_url': ''
        }
        return package
    
    

    def sendHeartBeat(self, hb):
        url = 'https://changjiang.yuketang.cn/video-log/heartbeat/'
        header = {
            'xtbz': 'ykt',
            'classroom-id': str(self.video_info['classroom_id']),
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/15.4 Safari/605.1.15',
            'Xt-Agent': 'web',
            'X-CSRFToken': self.session.cookies['csrftoken'],
            'Accept': 'application/json, text/plain, */*',
            'Content-Type': 'application/json;charset=utf-8'
        }
        response = self.session.post(url, data=json.dumps({
            'heart_data': hb
        }), headers=header)
        print(response.json())
        print(hb)
        return response.json()

    def killThis(self):
        self.kill_flag = True
    

class CommentThread(QThread):
    kill = pyqtSignal()
    finished = pyqtSignal()
    updata_process = pyqtSignal(float)
    def __init__(self, session:requests.Session, comment_info):
        super().__init__()
        self.session = session
        self.comment_info = comment_info
        return
    
    def run(self):
        print('开始新的讨论')
        self.updata_process.emit(0.)
        comment_info = self.getCommentInfo()
        sku_id = comment_info['data']['sku_id']
        self.updata_process.emit(0.5)
        state = self.getCommentState()
        if state['data']:
            self.finished.emit()
            self.updata_process.emit(1.0)
        else:
            discussion = self.getDiscussion(sku_id)
            discussion_id = discussion['data']['id']
            total_discussion = self.getTotalDiscussion(discussion_id)
            if total_discussion['data']['new_comment_list']['count'] != 0:
                id = random.choice(range(min(total_discussion['data']['new_comment_list']['count'], 10)))
                comment = total_discussion['data']['new_comment_list']['results'][id]['content']
                self.sendDiscussion(comment, discussion['data']['user_id'], discussion_id)
            self.finished.emit()
            self.updata_process.emit(1.0)
        return
    
    def getCommentInfo(self):
        url = "https://changjiang.yuketang.cn/mooc-api/v1/lms/learn/leaf_info/%d/%d/" % (self.comment_info['classroom_id'], self.comment_info['comment_id'])
        header = {
            'xtbz': 'ykt',
            'classroom-id': str(self.comment_info['classroom_id'])
        }
        list_ = self.session.get(url, headers=header).json()
        return list_
    
    def getCommentState(self):
        url = "https://changjiang.yuketang.cn/v/discussion/v2/student/comment/status/?leaf_id=%d&classroom_id=%d" % (self.comment_info['comment_id'], self.comment_info['classroom_id'])
        header = {
            'xtbz': 'ykt',
            'classroom-id': str(self.comment_info['classroom_id'])
        }
        list_ = self.session.get(url, headers=header).json()
        return list_
    
    def getDiscussion(self, sku_id):
        url = "https://changjiang.yuketang.cn/v/discussion/v2/unit/discussion/?classroom_id=%d&sku_id=%d&leaf_id=%d&topic_type=4&channel=xt" % (self.comment_info['classroom_id'], sku_id, self.comment_info['comment_id'])
        header = {
            'xtbz': 'ykt',
            'classroom-id': str(self.comment_info['classroom_id'])
        }
        list_ = self.session.get(url, headers=header).json()
        return list_
    
    def getTotalDiscussion(self, discussion_id):
        url = "https://changjiang.yuketang.cn/v/discussion/v2/comment/list/%d/?offset=0&limit=10&web=web" % (discussion_id)
        header = {
            'xtbz': 'ykt',
            'classroom-id': str(self.comment_info['classroom_id'])
        }
        list_ = self.session.get(url, headers=header).json()
        return list_
    
    def sendDiscussion(self, comment, to_user, discussion_id):
        url = "https://changjiang.yuketang.cn/v/discussion/v2/comment/"
        data = {"to_user": to_user, "topic_id":discussion_id,"content":comment}
        header = {
            'xtbz': 'ykt',
            'classroom-id': str(self.comment_info['classroom_id']),
            'X-CSRFToken': self.session.cookies['csrftoken'],
            'Xt-Agent': 'web',
            'Content-Type': 'application/json;charset=utf-8'
        }
        self.session.post(url, data=json.dumps(data), headers=header)
        return

