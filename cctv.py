import graphics
import webcam_stream
import cv2
import argparse
import json
import datetime


if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument("-r", "--rotate", action="store_true", default=0, help="Whether or not rotate image")
    ap.add_argument("-s", "--source", type=int, default=0, help="Source number")
    ap.add_argument('-f', "--file", type=str, default='', help="Saved masks")
    ap.add_argument("--save_filename", type=str, default="Camera1.json", help="File to save")
    args = vars(ap.parse_args())

    stream = webcam_stream.WebcamVideoStream(src=args["source"]).start()

    if args["file"]:
        with open(args["file"], "r") as f:
            saved_masks = json.load(f)
            for mask in saved_masks:
                stream.masks.append(graphics.Rectangle(graphics.Point(mask['x1'], mask['y1']),
                                                       graphics.Point(mask['x2'], mask['y2'])))
    stream.update_empty()

    while True:

        res, frame = stream.read()

        if not res:
            stream.stop()
            cv2.destroyAllWindows()
            print("NOT GRABBED")
            break

        if args["rotate"] > 0:
            frame = cv2.flip(frame, 1)

        move = stream.find_diff(frame)
        if move:
            stream.start_recording()

        key_pressed = cv2.waitKey(1)
        if key_pressed == 27:
            break
        elif stream.empty is None or key_pressed == ord('i'):
            stream.set_empty()
        elif key_pressed == ord('m'):
            cv2.putText(frame, "Money OUT", (10, 110), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 255), 2)
            filename = 'Money_OUT__{0}.png'.format(datetime.datetime.now().strftime("%d_%m_%Y_%H-%M-%S"))
            cv2.imwrite(filename, frame)
        elif key_pressed == ord('c'):
            cv2.putText(frame, "Card IN/OUT", (10, 80), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 255), 2)
            filename = 'Card_IN_OUT__{0}.png'.format(datetime.datetime.now().strftime("%d_%m_%Y_%H-%M-%S"))
            cv2.imwrite(filename, frame)
        elif key_pressed == ord('a'):
            # mask mode
            if stream.mode != 1:
                stream.mode = 1
            else:
                stream.mode = 0
        elif key_pressed == ord('s'):
            cv2.putText(frame, "Masks have been saved", (10, 140), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 255), 2)
            with open(args["save_filename"], "w") as f:
                json.dump(stream.masks, f, default=(lambda o: o.__dict__))

        if stream.recording:
            cv2.putText(frame, "REC", (600, 30), cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 255), 2)
            cv2.circle(frame, (681, 20), 10, (0, 0, 255), cv2.FILLED)
            # stop recording if no movements
            if (datetime.datetime.now() - stream.last_movement) / datetime.timedelta(seconds=1) > 5:
                stream.stop_recording()

        cv2.setMouseCallback("Camera 1", stream.mouse_event)
        if stream.left_mb_clicked:
            graphics.Rectangle(stream.point_one, stream.point_two).show(frame)
        if stream.mode:
            for rect in stream.masks:
                rect.show(frame)

        if stream.right_mb_clicked:
            for index, mask in enumerate(stream.masks):
                if mask.check(stream.point_two):
                    mask.show(frame, (0, 0, 255))

        cv2.imshow("Camera 1", frame)

    if stream.recording:
        stream.stop_recording()

    stream.stop()
    cv2.destroyAllWindows()
