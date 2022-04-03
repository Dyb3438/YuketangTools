from PyQt5 import QtGui, QtWidgets, Qt
from PyQt5.QtCore import QEvent, QObject, pyqtSignal, Qt

class CourseItem(QtWidgets.QWidget):
    MouseLClick = pyqtSignal()
    def __init__(self, course_name, class_name, teacher_name):
        super().__init__()
        self.course_name = course_name
        self.class_name = class_name
        self.teacher_name = teacher_name
        self.setFixedHeight(70)

        self.isHover = False
        return
    
    def __setattr__(self, __name, __value):
        if __name == 'isHover':
            self.__dict__['isHover'] = __value
            self.update()
        else:
            return super().__setattr__(__name, __value)
    
    def paintEvent(self, a0: QtGui.QPaintEvent) -> None:
        self.drawBackground()
        self.drawInfo()
        return super().paintEvent(a0)
    
    def drawBackground(self):
        p = QtGui.QPainter(self)
        if self.isHover:
            p.setBrush(QtGui.QColor.fromRgb(200, 150, 150))
        else:
            p.setBrush(QtGui.QColor.fromRgb(150, 150, 150))
        p.drawRect(0, 0, self.width(), self.height())
        return
    
    def drawInfo(self):
        p = QtGui.QPainter(self)
        p.setFont(QtGui.QFont("Courier New", 20))
        p.drawText(5, 20, self.course_name)
        
        p.setFont(QtGui.QFont("Courier New", 16))
        p.drawText(5, 45, self.class_name)
        p.drawText(5, 65, self.teacher_name)
        return
    
    def eventFilter(self, a0: 'QObject', a1: 'QEvent') -> bool:
        if a0 == self:
            if a1.type() == QEvent.Type.Enter:
                self.mouseEnter()
            elif a1.type() == QEvent.Type.Leave:
                self.mouseLeave()
            elif a1.type() == QEvent.Type.MouseButtonPress:
                self.mouseLClick()
        return super().eventFilter(a0, a1)
    
    def mouseLClick(self):
        self.MouseLClick.emit()
        return

    def mouseEnter(self):
        self.isHover = True
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        return
    
    def mouseLeave(self):
        self.isHover = False
        self.setCursor(Qt.CursorShape.ArrowCursor)
        return
