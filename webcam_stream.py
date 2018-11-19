from threading import Thread, RLock
import graphics
import cv2
import datetime
from copy import copy
import queue


class WebcamVideoStream:
    def __init__(self, src=0, name=None, add_text=True):
        # initialize the video camera stream and read the first frame
        # from the stream
        self._th1 = Thread(target=self.update, args=())
        self._th2 = Thread(target=self.update_temporary, args=())
        self._mutex = RLock()

        self.stream = cv2.VideoCapture(src)
        (self.grabbed, self.clear) = self.stream.read()
        self.frame = copy(self.clear)
        self.r_frame = copy(self.frame)
        # initialize the variable used to indicate if the thread should
        # be stopped
        self.stopped = False

        # initialize coordinates for rectangle to be showed
        self.point_one = graphics.Point()
        self.point_two = graphics.Point()

        self.name = name or "Camera 1"
        self.text_flag = add_text

        # initialize masks
        self.masks = []
        self.mode = 0
        self.left_mb_clicked = 0
        self.right_mb_clicked = 0

        # initialize empty frame
        self.empty_fr = None
        self.empty = None
        self.set_empty()

        self.last_movement = datetime.datetime.now() - datetime.timedelta(minutes=5)

        self.tempo_size = 5 * 60 * self.stream.get(cv2.CAP_PROP_FPS)
        self.temporary_buf = queue.Queue(self.tempo_size)
        self.recording = None
        self.file_writer = None

    def start(self):
        # start the thread to read frames from the video stream
        self._th1.start()
        self._th2.start()
        return self

    def update(self):
        # keep looping infinitely until the thread is stopped
        while True:
            # if the thread indicator variable is set, stop the thread
            if self.stopped:
                return
            # otherwise, read the next frame from the stream

            (self.grabbed, self.clear) = self.stream.read()
            self.frame = copy(self.clear)

            # add name and text if need to
            if self.text_flag:
                cv2.putText(self.frame, "Camera 1", (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 255), 2)
                cv2.putText(self.frame, datetime.datetime.now().strftime("%A, %d/%m/%Y %H:%M:%S"),
                            (10, self.frame.shape[0] - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
            self.r_frame = copy(self.frame)
            # add frame to temporary buf
            self.temporary_buf.put(self.frame)

    def update_temporary(self):
        while True:
            # if the thread indicator variable is set, stop the thread
            if self.stopped:
                if self.file_writer:
                    self.file_writer.release()
                    self.file_writer = None
                    self.recording = False
                return
            # save if need to
            if self.recording:
                if not self.file_writer:
                    fourcc = cv2.VideoWriter_fourcc(*'XVID')
                    file_name = '{0}.avi'.format(datetime.datetime.now().strftime("%d_%m_%Y_%H-%M-%S"))
                    self.file_writer = cv2.VideoWriter(file_name, fourcc, self.stream.get(cv2.CAP_PROP_FPS),
                                                       (int(self.stream.get(cv2.CAP_PROP_FRAME_WIDTH)),
                                                        int(self.stream.get(cv2.CAP_PROP_FRAME_HEIGHT))))
                    print(self.file_writer.isOpened(), end=" - ")
                    print(file_name)
                frame = self.temporary_buf.get()
                self.file_writer.write(frame)
            else:
                if self.file_writer:
                    self.file_writer.release()
                    self.file_writer = None
                if self.temporary_buf.full():
                    self.temporary_buf.get()

    def read(self):
        # return the frame most recently read
        return self.grabbed, self.r_frame

    def stop(self):
        # indicate that the thread should be stopped
        self.stopped = True
        self._th1.join()
        self._th2.join()

    def mouse_event(self, event, x, y, flags, param):
        # if mouse have been clicked
        if event == cv2.EVENT_LBUTTONDOWN:
            # set rectangle coordinates (lb mode)
            self.left_mb_clicked = 1
            self.point_one.set(x, y)
            self.point_two.set(x, y)
        if event == cv2.EVENT_MOUSEMOVE:
            # change rectangle coordinates
            if self.left_mb_clicked or self.right_mb_clicked:
                self.point_two.set(x, y)
        if event == cv2.EVENT_LBUTTONUP:
            # save rectangle as mask
            self.left_mb_clicked = 0
            self.masks.append(graphics.Rectangle(self.point_one, self.point_two))
            self.update_empty()
        if event == cv2.EVENT_RBUTTONDOWN:
            # set rectangle coordinates (rb mode)
            self.right_mb_clicked = 1
            self.point_two.set(x, y)
        if event == cv2.EVENT_RBUTTONUP:
            # delete masks with those coordinates
            self.right_mb_clicked = 0
            temp = []
            for mask in self.masks:
                if not mask.check(self.point_two):
                    temp.append(mask)
            self.masks = temp
            self.update_empty()

    def update_empty(self):
        # updates empty
        self.empty = copy(self.empty_fr)
        for mask in self.masks:
            mask.show(self.empty, (0, 0, 0), cv2.FILLED)

    def set_empty(self):
        self.empty_fr = cv2.cvtColor(self.clear, cv2.COLOR_BGR2GRAY)
        self.empty_fr = cv2.GaussianBlur(self.empty_fr, (21, 21), 0)
        self.update_empty()

    def start_recording(self):
        self.recording = True

    def stop_recording(self):
        self.recording = False

    def find_diff(self, frame):
        if self.empty is None:
            return

        # convert frame to a grayscale and blur it
        gray = cv2.cvtColor(self.clear, cv2.COLOR_BGR2GRAY)
        gray = cv2.GaussianBlur(gray, (21, 21), 0)
        for mask in self.masks:
            mask.show(gray, (0, 0, 0), cv2.FILLED)
        # compute the absolute difference between the current frame and empty frame
        frame_delta = cv2.absdiff(self.empty, gray)
        thresh = cv2.threshold(frame_delta, 25, 255, cv2.THRESH_BINARY)[1]

        # dilate the thresholded image to fill in holes, then find contours
        # on thresholded image
        thresh = cv2.dilate(thresh, None, iterations=2)
        cnts = cv2.findContours(thresh.copy(), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        cnts = cnts[1]
        cv2.imshow("Camera 1_thresh", thresh)
        cv2.imshow("Empty", self.empty_fr)
        # loop over the contours
        ret = False
        for c in cnts:
            # if the contour is too small, ignore it
            if cv2.contourArea(c) < 500:
                continue
            ret = True
            self.last_movement = datetime.datetime.now()
            # compute the bounding box for the contour, draw it on the frame,
            # and update the text
            (x, y, w, h) = cv2.boundingRect(c)
            cv2.rectangle(frame, (x, y), (x + w, y + h), (0, 255, 0), 2)
        return ret
