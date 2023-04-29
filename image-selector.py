#   image-selector.py - Selects an image from a directory, copies and prepares it for display.
#   Used in Home Assistant environment to display photos.
#   Refer to https://github.com/highdeserthacker/image-selector for more information.
#
# Given the root folder containing photos/images organized
#   by year (2022, 2023, etc), will randomly choose a file.
#   Choice is based on weighting, in which folders with more images will have 
#   a higher probability of selection.
#   Designed to be run from a cron, both for periodic regeneration of the weights
#   as well as picking a random image.
#   
#   Operations    --op generate|pick
#   
#     generate:  Scans the root dir and all children, generating the weighting.
#                Weights saved in csv file.
#               
#     pick:      Using weight file
#
#   
#   Parameters:
#     --input root directory
#     --weight [weight file name] (Optional) uses this as the file name+path for the weight file.
#     --output [dst file]. The destination file name+path.
#
# Debugging options
#     --debug 1..N. Optional debug level. 
#       0 (default) - no info logged
#       1 - trace info. Logs selected file name
#       2 - does not update destination file
#     -h: Help
#
#   Returns: 0 if ok, !=0 if error
#
# ================================================================
# Imports
# ================================================================
import sys                                            # sys.exit(), sys.path
import time
from datetime import datetime, date, timedelta        # datetime, localtime, timedelta
import os                                             # e.g. listdir(), remove()
import shutil
import random                                         # e.g. choices()
from PIL import Image, ImageFont, ImageDraw           # pillow package

import hdh_lib.log as log                             # hdh-lib package
import hdh_lib.file.csv as csv

# ================================================================
# Variables - User Adjustable
# ================================================================
_FONT_FILE= 'arial.ttf'
_ImgFileExtensions= ['.jpg', '.jpeg']                 # File types that will be included in selection of an image.
_MAX_IMAGE_SIZE_PIXELS= 1024                          
_MAX_WEIGHT_FILE_AGE_DAYS= 1                          # Number of days until the directory is fully rescanned for new items, with weights/probabilities updated.
_DFLT_WEIGHT_FILE_NAME='weights.csv'

# ================================================================
# Variables - Application
# ================================================================
_OP_GENERATE= 'generate'
_OP_PICK= 'pick'

_WeightFileName= ''


# ================================================================
# Initialization & Setup
# ================================================================
# Process command line args. argparse creates an args[] dict for the parameters (sans '--')..
# Refer to https://docs.python.org/3/library/argparse.html
import argparse

parser= argparse.ArgumentParser(description='photopicker')
parser.add_argument('-O', '--op', default='pick', required=False, help='Operation to perform. generate|pick')
parser.add_argument('-i', '--input', required=True, help='Root image/photo folder.')
parser.add_argument('-w', '--weight', required=False, help='Optional weight file path+name.')
parser.add_argument('-o', '--output', required=True, help='output file')
parser.add_argument('-d', '--debug', type=int, default=0, required=False, help='debug level. 1= info, 2=verbose')
args= vars(parser.parse_args())

Operation=  args['op']
_RootDir=   args['input']
TraceLevel= args['debug']

if (Operation == _OP_PICK) :
  _DstImgFile= args['output']

if args['weight'] :
  _WeightFileName= args['weight']


# ================================================================
# Set up logging - Note that it prints to stdout too.
log.setup(__file__)                                   # __file__ = of the form "/app/thisappname.py". Logs to e.g. /app/myappname.log

# ================================================================
# Font file to use, if any.
AppPath, AppName= os.path.split(__file__)
FontFileName= os.path.join(AppPath, _FONT_FILE)
_FONT_SPECIFIED= os.path.isfile(FontFileName)

# ================================================================
# Functions
# ================================================================
# IsMatchingFileType - determines whether given file has extension in the list.
# Returns: True if matching type.
def IsMatchingFileType(FileName, ExtensionList) :
  Result= False
  FileExt= os.path.splitext(FileName)[1]
  for AllowedExtension in ExtensionList :
    if AllowedExtension.lower() in FileExt.lower() :  # Account for e.g. ".jpg'"
      Result= True
      break

  return Result
  # end IsMatchingFileType

# ================================================================
# GenerateWeights - Scans the dirs, generates file counts from each to use as 
#   weighting. Saves to file.
# Returns: None
def GenerateWeights(RootDir, OutputFile) :
  FunctionName= "GenerateWeights()"

  DirDictArray= []
  nFiles= 0
  DirList= next(os.walk(RootDir))[1]                  
  # Recurse each of the annual subfolders and get a count of total number of files in each
  for DirItem in DirList :
    FileCount= 0
    WeightEntryDict= {
      'Dir'       : '',
      'Count'     : 0,
    }
    DirFullPath= os.path.join(RootDir, DirItem)
    for (root,dirs,files) in os.walk(DirFullPath) :         # This recurses
      for file in files : 
        if IsMatchingFileType(file, _ImgFileExtensions) :
          # Found an image file 
          FileCount += 1
          nFiles += 1

    if (TraceLevel > 0) :
      print("Dir: " + DirFullPath + " Count: " + str(FileCount))

    if (FileCount > 0) :
      WeightEntryDict['Dir']= DirItem
      WeightEntryDict['Count']= FileCount
      DirDictArray.append(WeightEntryDict)
    
  # Sort by alpha
  DirDictArray= sorted(DirDictArray, key=lambda i: i['Dir'])

  # Save the weights to csv file
  csv.write(DirDictArray, OutputFile, False)

  if (TraceLevel > 0) :
    log.write(FunctionName + ": generated weights for " + str(nFiles) + " files.")

  # end GenerateWeights

# ================================================================
# PickImage - loads the weight/count file, generates probabilities,
# and chooses a file.
# Returns: List - [0] Year, [1] File with path
def PickImage(RootDir, WeightFile) :
  FunctionName= "PickImage()"

  # Load the count/weight file
  DirDictArr= csv.read(WeightFile)                    # Returns array of dict items [{Dir: 'mydir1', Count: '34'}, ...]
  FileCount= 0
  DirList= []
  WeightList= []                                      # Needs to contain numbers (float, int)
  for row in DirDictArr :                             # Process the rows
    Count= float(row['Count'])
    FileCount += int(Count)
    DirList.append(row['Dir'])
    WeightList.append(Count)

  # Choose a Year dir based on probabilities
  ChosenDirList= random.choices(DirList, WeightList, k=1)
  ChosenDir= ChosenDirList[0]
  ChosenDirPath= os.path.join(RootDir, ChosenDir)  
  if (TraceLevel > 1) :
    print(FunctionName + " chose from " + ChosenDir)

  # Year dir is now chosen. Read entire subdir and choose a file randomly.
  # Alt: using the total count, choose a number 1..count randomly, then stop walking once we hit count. 2x more efficient on average.
  ChosenFileName= ''
  FileList= []
  for (root,dirs,files) in os.walk(ChosenDirPath) :   # This recurses. root contains full absolute path.
    #print("root:" + root + " dirs: " + str(dirs))    
    for file in files : 
      if IsMatchingFileType(file, _ImgFileExtensions) :
        # Found an image file 
        file= file.replace("'", r"\'")              # Apostrophes in filenames cause it to fail, remove them.
        FullFileName= os.path.join(root, file)
        FullFileName= os.path.normpath(FullFileName)  # Normalize path for differing OS's.          
        FileList.append(FullFileName)
  
  if (len(FileList) > 0) :
    ChosenFileName= random.choice(FileList)           # Choose a random file
  else :
    log.write(FunctionName + ": read failure " + ChosenDir)

  Results= [ChosenDir, ChosenFileName]
  
  if (TraceLevel > 0) :
    log.write(FunctionName + ": Dir: " + ChosenDir + " Image: " + ChosenFileName)

  return Results

  # end PickImage

# ================================================================
# PrepImage - resizes and annotates the image. Updates the file
#   with changes.
# Returns: nothing
def PrepImage(ImageFileName, ImageSize, AnnotationText) :
  FunctionName= "PickFile()"

  # Resize to ImageSize pixels wide max.
  OriginalImage= Image.open(ImageFileName)
  OriginalImage.thumbnail(ImageSize)

  # Annotate
  Canvas= ImageDraw.Draw(OriginalImage)
  AnnotationFont= ImageFont.load_default()
  if _FONT_SPECIFIED :
    AnnotationFont= ImageFont.truetype(FontFileName, 24)      # Size= 24 pix

  Canvas.text((32, 32), AnnotationText, font=AnnotationFont, fill='white')

  OriginalImage.save(ImageFileName)

  # end PrepImage

# ================================================================
# Main
# ================================================================
if (Operation == _OP_GENERATE) :
  # Generate the weights
  GenerateWeights(_RootDir, _WeightFileName)

elif (Operation == _OP_PICK) :
  # If weight file not specified, use default
  if (len(_WeightFileName) == 0) :
    AppPath, AppName= os.path.split(__file__)
    _WeightFileName= os.path.join(AppPath, _DFLT_WEIGHT_FILE_NAME)

  # Generate weight file if not present or too old
  DoWeightFile= False
  if (os.path.isfile(_WeightFileName)) :
    # File exists. See if it has expired.
    WeightFileDateTime= datetime.fromtimestamp(os.path.getmtime(_WeightFileName))

    WeightExpirationDateTime= WeightFileDateTime + timedelta(days=_MAX_WEIGHT_FILE_AGE_DAYS)
    if (TraceLevel > 0) :
      print("WeightExpirationDateTime: " + WeightExpirationDateTime.strftime('%Y-%m-%d %H:%M:%S'))

    if (datetime.now() >= WeightExpirationDateTime) :
      DoWeightFile= True

  else :
    DoWeightFile= True

  if (DoWeightFile) :
    GenerateWeights(_RootDir, _WeightFileName)


  # Pick a file randomly.
  Results= PickImage(_RootDir, _WeightFileName)
  Year= Results[0]
  PickFileName= Results[1]
  print(Year, PickFileName)

  if (len(PickFileName) > 0) :
    # Copy the selected file to tmp location. 
    DstPath, DstName= os.path.split(_DstImgFile)
    TmpFileName= os.path.join(DstPath, '.tmp-photo.jpg')
    shutil.copy(PickFileName, TmpFileName)

    # Resize and annotate the image
    ImageSize= (_MAX_IMAGE_SIZE_PIXELS, _MAX_IMAGE_SIZE_PIXELS)
    AnnotationText= Year + ' ' + os.path.split(PickFileName)[1]
    PrepImage(TmpFileName, ImageSize, AnnotationText)

    # Copy this file to the fixed destination photo name. Set the extension to same as src.
    if (TraceLevel < 2) :
      os.replace(TmpFileName, _DstImgFile)            # Set tmp file as destination file.

else :
  print("Unknown operation.")


# ================
sys.exit(0)
