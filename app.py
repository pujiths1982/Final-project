from flask import Flask, render_template, Response, jsonify
import cv2
from ultralytics import YOLO
import numpy as np
from datetime import datetime
import threading
import pygame

app = Flask(__name__)

model = YOLO('yolo12n.pt')

OBSTACLE_CLASSES = {
    0: 'person', 1: 'bicycle', 2: 'car', 3: 'motorcycle', 5: 'bus',
    7: 'truck', 9: 'traffic light', 11: 'stop sign', 13: 'bench'
}

ALERT_CLASSES = {0, 1, 2, 3, 5, 7}

pygame.mixer.init()

camera = None
camera_lock = threading.Lock()
detection_stats = {
    'total_detections': 0,
    'last_detection_time': None,
    'current_obstacles': []
}

def play_alert_sound():
    try:
        pygame.mixer.music.load('static/alert.mp3')
        pygame.mixer.music.play()
    except:
        pass

def get_camera():
    global camera
    with camera_lock:
        if camera is None or not camera.isOpened():
            camera = cv2.VideoCapture(0)
            camera.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
            camera.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)
            camera.set(cv2.CAP_PROP_FPS, 30)
    return camera

def generate_frames():
    global detection_stats
    alert_triggered = False
    frame_count = 0
    
    while True:
        camera = get_camera()
        success, frame = camera.read()
        
        if not success:
            break
        
        frame_count += 1
        
        if frame_count % 2 == 0:
            results = model(frame, conf=0.5, verbose=False)
            
            current_obstacles = []
            alert_needed = False
            
            for result in results:
                boxes = result.boxes
                for box in boxes:
                    class_id = int(box.cls[0])
                    confidence = float(box.conf[0])
                    
                    if class_id in OBSTACLE_CLASSES:
                        x1, y1, x2, y2 = map(int, box.xyxy[0])
                        label = OBSTACLE_CLASSES[class_id]
                        
                        current_obstacles.append({
                            'class': label,
                            'confidence': confidence
                        })
                        
                        color = (0, 0, 255) if class_id in ALERT_CLASSES else (0, 255, 0)
                        
                        cv2.rectangle(frame, (x1, y1), (x2, y2), color, 2)
                        
                        label_text = f'{label}: {confidence:.2f}'
                        label_size = cv2.getTextSize(label_text, cv2.FONT_HERSHEY_SIMPLEX, 0.6, 2)[0]
                        
                        cv2.rectangle(frame, (x1, y1 - label_size[1] - 10), 
                                    (x1 + label_size[0], y1), color, -1)
                        cv2.putText(frame, label_text, (x1, y1 - 5), 
                                  cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)
                        
                        if class_id in ALERT_CLASSES:
                            alert_needed = True
            
            detection_stats['current_obstacles'] = current_obstacles
            detection_stats['total_detections'] = len(current_obstacles)
            
            if alert_needed and not alert_triggered:
                threading.Thread(target=play_alert_sound, daemon=True).start()
                alert_triggered = True
                detection_stats['last_detection_time'] = datetime.now().strftime('%H:%M:%S')
            elif not alert_needed:
                alert_triggered = False
            
            if alert_needed:
                cv2.putText(frame, 'ALERT: OBSTACLE DETECTED!', (50, 50),
                          cv2.FONT_HERSHEY_SIMPLEX, 1.2, (0, 0, 255), 3)
        
        ret, buffer = cv2.imencode('.jpg', frame, [cv2.IMWRITE_JPEG_QUALITY, 85])
        frame = buffer.tobytes()
        
        yield (b'--frame\r\n'
               b'Content-Type: image/jpeg\r\n\r\n' + frame + b'\r\n')

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/video_feed')
def video_feed():
    return Response(generate_frames(), 
                    mimetype='multipart/x-mixed-replace; boundary=frame')

@app.route('/detection_stats')
def get_detection_stats():
    return jsonify(detection_stats)

@app.route('/stop_camera')
def stop_camera():
    global camera
    with camera_lock:
        if camera is not None:
            camera.release()
            camera = None
    return jsonify({'status': 'stopped'})

if __name__ == '__main__':
    try:
        app.run(debug=True, host='0.0.0.0', port=5000, threaded=True)
    finally:
        if camera is not None:
            camera.release()
        cv2.destroyAllWindows()