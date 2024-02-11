# import win32event
# import win32api
import sys
# from winerror import ERROR_ALREADY_EXISTS
# mutex = win32event.CreateMutex(None, False, 'name')
# last_error = win32api.GetLastError()
# if last_error == ERROR_ALREADY_EXISTS:
#    sys.exit(0)


import tkinter as tk
from tkinter.ttk import *
import cv2
from PIL import Image, ImageTk
from tkinter import filedialog
import pandas as pd
from ultralytics import YOLO
import cvzone
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email import encoders
import smtplib
import threading
from datetime import datetime

# Global variables for OpenCV-related objects and flags
cap = None
is_camera_on = False
frame_count = 0
frame_skip_threshold = 3
model = YOLO('best.pt')
video_paused = False

# Global variables for email sending
sender_email = "sudipdatta2002@gmail.com"
receiver_email = "2021csb006.sudip@students.iiests.ac.in"
sender_password = "pahifrmjjjwahdnr"
smtp_port = 587
smtp_server = "smtp.gmail.com"
subject = "Accident detected"
last_send_time = datetime(2024, 1, 1)

##########for sending emails##############
def send_email(accident_type, image):
    body = accident_type

    msg = MIMEMultipart()
    msg['From'] = sender_email
    msg['To'] = receiver_email
    msg['Subject'] = subject

    msg.attach(MIMEText(body, 'plain'))

    filename = "res.png"
    # folder = "./result/"
    # fullFileName = folder + filename

    # attachment = open(fullFileName, 'rb')
    is_success, im_buf_arr = cv2.imencode(".jpg", image)
    attachment = im_buf_arr.tobytes()


    attachment_package = MIMEBase('application', 'octet-stream')
    attachment_package.set_payload(attachment)
    encoders.encode_base64(attachment_package)
    attachment_package.add_header('Content-Disposition', "attachment; filename= " + filename)
    msg.attach(attachment_package)

    text = msg.as_string()


    print("Connecting to server")
    gmail_server = smtplib.SMTP(smtp_server, smtp_port)
    gmail_server.starttls()
    gmail_server.login(sender_email, sender_password)
    print("Successfully connected to server")
    print()

    print("Sending email to ", receiver_email)
    gmail_server.sendmail(sender_email, receiver_email, text)
    print("Email sent to ", receiver_email)
    print()

    gmail_server.quit()

    sys.exit()

#########################################

# Function to read objects.txt
def read_classes_from_file(file_path):
    with open(file_path, 'r') as file:
        classes = [line.strip() for line in file]
    return classes

# Function to start the webcam feed
def start_webcam():
    global cap, is_camera_on, video_paused
    if not is_camera_on:
        cap = cv2.VideoCapture(0)  # Use the default webcam (you can change the index if needed)
        is_camera_on = True
        video_paused = False
        update_canvas()  # Start updating the canvas

# Function to stop the webcam feed
def stop_webcam():
    global cap, is_camera_on, video_paused
    if cap is not None:
        cap.release()
        is_camera_on = False
        video_paused = False

# Function to pause or resume the video
def pause_resume_video():
    global video_paused
    video_paused = not video_paused

# Function to start video playback from a file
def select_file():
    global cap, is_camera_on, video_paused
    if is_camera_on:
        stop_webcam()  # Stop the webcam feed if running
    file_path = filedialog.askopenfilename(filetypes=[("Video files", "*.mp4 *.avi *.mov, *.jpg")])
    print(file_path)
    if file_path:
        is_camera_on = True
        video_paused = False
        if(file_path.endswith((".jpg", ".png"))):
            image = cv2.imread(file_path)
            update_canvas_with_image(image)
            return
        cap = cv2.VideoCapture(file_path)
        update_canvas()  # Start updating the canvas with the video

def update_canvas_with_image(image):
    image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
    image = cv2.resize(image, (1020, 500))
    selected_class = class_selection.get()
    accident_happened =False
    accident_class = ""
    global last_send_time

    results = model.predict(image, conf=conf_slider.get()/100, iou=iou_slider.get()/100)
    a = results[0].boxes.data
    px = pd.DataFrame(a).astype("float")
    for index, row in px.iterrows():
        x1 = int(row[0])
        y1 = int(row[1])
        x2 = int(row[2])
        y2 = int(row[3])
        conf = round(row[4], 2)
        d = int(row[5])
        c = class_list[d]
        if selected_class == "All" or c == selected_class:
            cv2.rectangle(image, (x1, y1), (x2, y2), (0, 0, 255), 2)
            cvzone.putTextRect(image, f'{c},{conf}', (x1, y1), 1, 1)

        if c.endswith('accident'):
            # cv2.imwrite("result/res.png", image)
            accident_happened = True
            accident_class = class_list[d]

    # image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
    photo = ImageTk.PhotoImage(image=Image.fromarray(image))
    canvas.img = photo
    canvas.create_image(0, 0, anchor=tk.NW, image=photo)

    current_time = datetime.now()
    diff = (current_time - last_send_time).total_seconds()
    print(diff)

    if accident_happened and diff>1:
        image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
        send_thread = threading.Thread(target=send_email, args=(accident_class, image, ))
        send_thread.start()
        last_send_time = current_time




# Function to update the Canvas with the webcam frame or video frame
def update_canvas():
    global is_camera_on, frame_count, video_paused
    if is_camera_on:
        if not video_paused:
            ret, frame = cap.read()
            if ret:
                frame_count += 1
                if frame_count % frame_skip_threshold != 0:
                    canvas.after(10, update_canvas)
                    return
                
                update_canvas_with_image(frame)

        canvas.after(10, update_canvas)

# Function to quit the application
def quit_app():
    stop_webcam()
    root.quit()
    root.destroy()

# Create the main Tkinter window
root = tk.Tk()
root.title("Accident Detector")

# Create a Canvas widget to display the webcam feed or video
canvas = tk.Canvas(root, width=1020, height=500)
canvas.pack(fill='both', expand=True)

class_list = read_classes_from_file('objects.txt')

class_selection = tk.StringVar()
class_selection.set("All")  # Default selection is "All"
class_selection_label = tk.Label(root, text="Select Class:")
class_selection_label.pack(side='left')
class_selection_entry = tk.OptionMenu(root, class_selection, "All", *class_list)  # Populate dropdown with classes from the text file
class_selection_entry.pack(side='left')

# Create a frame to hold the buttons
button_frame = tk.Frame(root)
button_frame.pack(fill='x')

# Create a "Play" button to start the webcam feed
play_button = tk.Button(button_frame, text="Play", command=start_webcam)
play_button.pack(side='left')

# Create a "Stop" button to stop the webcam feed
stop_button = tk.Button(button_frame, text="Stop", command=stop_webcam)
stop_button.pack(side='left')

# Create a "Select File" button to choose a video file
file_button = tk.Button(button_frame, text="Select File", command=select_file)
file_button.pack(side='left')

# Create a "Pause/Resume" button to pause or resume video
pause_button = tk.Button(button_frame, text="Pause/Resume", command=pause_resume_video)
pause_button.pack(side='left')

# Create a "Quit" button to close the application
quit_button = tk.Button(button_frame, text="Quit", command=quit_app)
quit_button.pack(side='left')

# create a slider frame to show sliders
slider_frame = tk.Frame(root)
slider_frame.pack(fill='x')

#create a  conf slider
conf_slider_label = tk.Label(slider_frame, text="Select conf label")
conf_slider_label.pack(side='left')
conf_slider = tk.Scale(slider_frame, from_=0, to=100, orient="horizontal")
conf_slider.set(50)
conf_slider.pack(side='left')

# create a iou slider
iou_slider_label = tk.Label(slider_frame, text="Select iou label")
iou_slider_label.pack(side='left')
iou_slider = tk.Scale(slider_frame, from_=0, to=100, orient="horizontal")
iou_slider.set(50)
iou_slider.pack(side='left')

# Display an initial image on the canvas (replace 'initial_image.jpg' with your image)
initial_image = Image.open('yolo.jpg')  # Replace 'initial_image.jpg' with your image path
initial_photo = ImageTk.PhotoImage(image=initial_image)
canvas.img = initial_photo
canvas.create_image(0, 0, anchor=tk.NW, image=initial_photo)

# Start the Tkinter main loop
root.mainloop()
