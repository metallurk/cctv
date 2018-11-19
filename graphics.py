import cv2

class Point:
    def __init__(self, x=-1, y=-1):
        self.x = x
        self.y = y
        self.is_set = False

    def set(self, _x, _y):
        self.x = _x
        self.y = _y
        self.is_set = True

    def clear(self):
        self.is_set = False

    def __bool__(self):
        return self.is_set

    def get(self):
        return self.x, self.y


class Rectangle:
    def __init__(self, p1, p2):
        self.x1 = min(p1.x, p2.x)
        self.x2 = max(p1.x, p2.x)
        self.y1 = min(p1.y, p2.y)
        self.y2 = max(p1.y, p2.y)

    def show(self, frame, color=(255, 0, 0), thickness=2):
        cv2.rectangle(frame, (self.x1, self.y1), (self.x2, self.y2), color, thickness)

    def check(self, p):
        if self.x1 <= p.x <= self.x2 and self.y1 <= p.y <= self.y2:
            return True
        return False
