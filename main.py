from functools import partial
from websocket_lib import Websocket
from http_lib import Http
from component.CourseItem import CourseItem
from PyQt5 import QtCore, QtGui, QtWidgets
import sys
import requests

class MainWindow(QtWidgets.QWidget):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.setWindowTitle("雨课堂视频终端")
        self.resize(300, 300)

        self.is_login = False

        self.createBody()

        self.timer = QtCore.QTimer()
        
        self.websocket_thread = Websocket("wss://changjiang.yuketang.cn/wsapp/")
        self.http_server = None
        self.websocket_thread.login_qrcode.connect(self.showQRCode)
        self.websocket_thread.login_success.connect(self.loginSuccess)
        self.websocket_thread.start()
        return
    
    def createBody(self):
        if 'bodyLayout' not in self.__dict__.keys():
            self.bodyLayout = QtWidgets.QVBoxLayout()
            self.bodyLayout.setContentsMargins(0, 0, 0, 0)
            self.bodyLayout.setSpacing(0)
        
        if self.is_login is False:
            self.removeLayout(self.bodyLayout)
            self.qrcode = QtWidgets.QLabel()
            self.bodyLayout.addWidget(self.qrcode)
        else:
            self.removeLayout(self.bodyLayout)

        if self.layout() is None:
            self.setLayout(self.bodyLayout)
        return
    
    def removeLayout(self, layout):
        for i in reversed(range(layout.count())):
            if layout.itemAt(i).widget() is not None:
                layout.itemAt(i).widget().deleteLater()
            else:
                layout.takeAt(i)
        return
    
    def showQRCode(self, msg):
        qrcode = msg['ticket']
        data = requests.get(qrcode).content
        pixmap = QtGui.QPixmap()
        pixmap.loadFromData(data)
        pixmap = pixmap.scaled(300, 300)
        self.qrcode.setPixmap(pixmap)
        self.timer.singleShot(int(msg['expire_seconds']) * 1000, self.updateQRCode)
        return
    
    def updateQRCode(self):
        if self.is_login is False:
            print('update qrcode')
            self.websocket_thread.query_qrcode.emit()
        return
    
    def loginSuccess(self, msg):
        self.is_login = True
        # self.qrcode.setPixmap(QtGui.QPixmap())
        self.createBody()
        self.http_server = Http(msg['UserID'], msg['Auth'])
        self.http_server.update.connect(self.updateProcess)

        course_list = self.http_server.course_list()
        for course in course_list['data']['list']:
            widget = CourseItem(course['course']['name'], course['name'], course['teacher']['name'])
            widget.MouseLClick.connect(partial(self.selectCourse, course))
            self.bodyLayout.addWidget(widget)
        self.bodyLayout.addSpacerItem(QtWidgets.QSpacerItem(0, 0, vPolicy=QtWidgets.QSizePolicy.Policy.Expanding))
        return
    
    def selectCourse(self, courseInfo):
        self.removeLayout(self.bodyLayout)
        print(courseInfo)
        online_list = self.http_server.online_learn_list(courseInfo['classroom_id'])
        for activity in online_list['data']['activities']:
            courseware_id = int(activity['courseware_id'])
            courseware_list = self.http_server.online_courseware_list(courseInfo['classroom_id'], courseware_id)
            for picture_course in self.generate_pic_course(courseware_list['data']['content_info']):
                picture_course['classroom_id'] = courseInfo['classroom_id']
                picture_course['picture_id'] = picture_course['id']
                self.http_server.addPicThread(picture_course)
            
            for comment_course in self.generate_comment_course(courseware_list['data']['content_info']):
                comment_course['course_id'] = courseInfo['course']['id']
                comment_course['classroom_id'] = courseInfo['classroom_id']
                comment_course['comment_id'] = comment_course['id']
                self.http_server.addCommentThread(comment_course)

            for video_course in self.generate_video_course(courseware_list['data']['content_info']):
                video_course['course_id'] = courseInfo['course']['id']
                video_course['classroom_id'] = courseInfo['classroom_id']
                video_course['video_id'] = video_course['id']
                self.http_server.addVideoThread(video_course)
        
        self.http_server.startAllThread()
        self.drawRealTimeInfo()
        if self.http_server.getThreadLength() == 0:
            self.updateProcess({'point':0, 'total':0, 'val': 1})
        return

    def generate_pic_course(self, out_list):
        if type(out_list) == dict:
            out_list = [out_list]
        else:
            out_list = out_list
        for list_ in out_list:
            for li in list_:
                if li == 'leaf_list':
                    for course in list_[li]:
                        if course['leaf_type'] == 3:
                            yield course
                elif li == 'section_list':
                    for result in self.generate_pic_course(list_[li]):
                        yield result
    
    def generate_comment_course(self, out_list):
        if type(out_list) == dict:
            out_list = [out_list]
        else:
            out_list = out_list
        for list_ in out_list:
            for li in list_:
                if li == 'leaf_list':
                    for course in list_[li]:
                        if course['leaf_type'] == 4:
                            yield course
                elif li == 'section_list':
                    for result in self.generate_comment_course(list_[li]):
                        yield result

    def generate_video_course(self, out_list):
        if type(out_list) == dict:
            out_list = [out_list]
        else:
            out_list = out_list
        for list_ in out_list:
            for li in list_:
                if li == 'leaf_list':
                    for course in list_[li]:
                        if course['leaf_type'] == 0:
                            yield course
                elif li == 'section_list':
                    for result in self.generate_video_course(list_[li]):
                        yield result
    
    def drawRealTimeInfo(self):
        num = self.http_server.getThreadLength()
        self.totalNum = QtWidgets.QLabel('总共 ' + str(num) + ' 个图文讨论视频')
        self.totalNum.setFont(QtGui.QFont("Courier New", 20))
        self.totalNum.setFixedHeight(50)
        self.bodyLayout.addWidget(self.totalNum)

        self.now_process = QtWidgets.QLabel()
        self.now_process.setFont(QtGui.QFont("Courier New", 20))
        self.bodyLayout.addWidget(self.now_process)
        return
    
    def updateProcess(self, data):
        if data['point'] == data['total'] and data['val'] == 1.:
            self.now_process.setText("恭喜你，你已完成所有图文、讨论和视频")
        else:
            self.now_process.setText("目前进行第 %d 个任务: %0.2f%%" % (data['point'], data['val'] * 100))
        return
    
    def eventFilter(self, a0, a1):
        if isinstance(a0, QtWidgets.QWidget):
            index = self.bodyLayout.indexOf(a0)
            if index >= 0:
                widget = self.bodyLayout.itemAt(index).widget()
                widget.eventFilter(a0, a1)
        return super().eventFilter(a0, a1)
        
    




if __name__ == '__main__':
    app = QtWidgets.QApplication(sys.argv)
    app.setAttribute(QtCore.Qt.AA_UseHighDpiPixmaps)
    w = MainWindow()
    app.installEventFilter(w)
    w.show()
    sys.exit(app.exec_())