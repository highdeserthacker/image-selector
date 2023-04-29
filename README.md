# image-selector

## Operation
Python program to choose a photo/image file randomly from a hierarchical directory and copy to a destination. Can use this with Home Assistant to display a randomly selected photo.

It is intended for use with photo images organized with one sub-directory per year. e.g. my-photo-dir/2022, my-photo-dir/2023, etc.

This program chooses a sub-directory at random (e.g. 2023), based on the weighting of the total number of images in the subdirectory (more images results in more likely selection). It then randomly chooses a single image within.

## Features
- Point it at your existing image collection. It does not require you to copy any photos to a specialized folder or database.
- Randomly selects a image, accounting for the variation in the number of images each directory, so that smaller directories don't dominate selection.
- User specified output file. e.g. a simulated camera feed in Home Assistant.
- Handles large image sets. e.g. does not traverse all subdirectories each run.
- Formats the image to fit the allocated area. This also reduces the size of larger images. The settings for this can be edited in the .py file.
- Supports file types .jpg, .jpeg. Edit the script to add additional types. See `_ImgFileExtensions`


## Requirements
Python 3.6+


## Installation
Create a directory for your program. This directory must be writable by the program.
Download image-selector repo at https://github.com/highdeserthacker/image-selector
pip install pillow
pip install hdh-lib


## Running
Example:
`python3 -u  image-selector.py  --input /your-image-folder  --output /somedir/outputimage.jpg  `

To record the selected image to the log, add the following switch: `--debug 1`

Run it on a cron (on Windows, a Scheduled Task) to select different images on a schedule. In my case, it chooses a new image every 5 minutes.

## Home Assistant
Here is an example setup for Home Assistant, with the output file specified as family-photo.jpg.

Edit configuration.yaml
~~~
camera:
  - platform: local_file
    name: camera_photos
    file_path: /config/www/family-photo.jpg
~~~    
