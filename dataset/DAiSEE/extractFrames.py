'''
	-The given code extracts all the frames for the entire dataset and saves these frames in the folder of the video clips.
	-Kindly have ffmpeg (https://www.ffmpeg.org/) (all credits) in order to successfully execute this script.
	-The script must in the a same directory as the Dataset Folder.
'''

import os
import subprocess

dataset = os.listdir('DataSet/')

def split_video(video_file, image_name_prefix, destination_path):
    return subprocess.check_output('ffmpeg -i "' + destination_path+video_file + '" ' + image_name_prefix + '%d.jpg -hide_banner', shell=True, cwd=destination_path)

for ttv in dataset:
    users = os.listdir('DataSet/'+ttv+'/')
    for user in users:
        currUser = os.listdir('DataSet/'+ttv+'/'+user+'/')
        for extract in currUser:
            clip = os.listdir('DataSet/'+ttv+'/'+user+'/'+extract+'/')[0]
            print (clip[:-4])
            path = os.path.abspath('.')+'/DataSet/'+ttv+'/'+user+'/'+extract+'/'
            split_video(clip, clip[:-4], path)

print ("================================================================================\n")
print ("Frame Extraction Successful")