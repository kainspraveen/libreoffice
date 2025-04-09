from fastapi import FastAPI, Request, Form, UploadFile
from fastapi.responses import StreamingResponse, JSONResponse
from typing import List, Annotated
import uuid
import asyncio
import config
from pathlib import Path
import aiofiles
import aiofiles.os
from aiofiles.os import path
import os
import shutil
import io
import zipfile
import uno
import time
import hashlib
# import subprocess
from com.sun.star.beans import PropertyValue
from com.sun.star.connection import NoConnectException
import subprocess

app = FastAPI()

# subprocess.Popen("top")

STAGING_DIRECTORY_IN = Path(
    __file__).parent.absolute() / config.STAGING_DIR / "in"
STAGING_DIRECTORY_OUT = Path(
    __file__).parent.absolute() / config.STAGING_DIR / "out"

tries = 0
props = []
prop = PropertyValue()
prop.Name = "Hidden"
prop.Value = True
props.append(prop)

properties_tuple = tuple(props)

local_context = uno.getComponentContext()
resolver = local_context.ServiceManager.createInstanceWithContext(
    "com.sun.star.bridge.UnoUrlResolver", local_context)
while tries<10:    
    try:
        context = resolver.resolve(
            "uno:socket,host=127.0.0.1,port=2002;urp;StarOffice.ComponentContext")
        print("Connected Successfully: Resolved context")
        break
    except NoConnectException as e:
        print(f"Trying for {tries} time, Could not connect to LibreOffice: ", e)
        print("sleeping for  5 seconds before trying")
        tries+=1
        time.sleep(5)
        if tries>=10:
            raise NoConnectException
print("before service manager init... with context: ",context)
smgr = context.ServiceManager
print("service manager init done: ", smgr)
desktop = smgr.createInstanceWithContext("com.sun.star.frame.Desktop", context)

def get_file_hash(file_object):
   hasher = hashlib.sha256()
   for chunk in iter(lambda: file_object.read(), b""):
       hasher.update(chunk)
   file_object.seek(0)  # reset pointer if needed
   return hasher.hexdigest()

def convert_to_pdf(input_path:str, output_path:str, mime_type:str):
    print("call to convert_to_pdf function....")

    # Open document
    file_url = uno.systemPathToFileUrl(os.path.abspath(input_path))
    print("File url: ", file_url)
    document = None
    tries = 0
    while tries<10 and document is None:
        document = desktop.loadComponentFromURL(file_url, "_blank", 0, properties_tuple)
        if document != None:
            print("Document init successfull in ", tries, " tries")
            break
        print("Tried init document ", tries, "times, retrying again after 5 Seconds after ",time.time())
        tries+=1
        time.sleep(5)
        
    # import subprocess
    # print(subprocess.Popen("cat /tmp/libreoffice.log"))
    # Export as PDF
    pdf_url = uno.systemPathToFileUrl(os.path.abspath(output_path))
    print(pdf_url)
    export_args = (
        uno.createUnoStruct("com.sun.star.beans.PropertyValue"),
    )
    export_args[0].Name = "FilterName"
    export_args[0].Value = "writer_pdf_Export"
    
    

    if mime_type in ["application/msword", "application/vnd.openxmlformats-officedocument.wordprocessingml.document"]:
        export_args[0].Value = "writer_pdf_Export"

    elif mime_type in ["application/vnd.ms-powerpoint", "application/vnd.openxmlformats-officedocument.presentationml.presentation"]:
        export_args[0].Value = "impress_pdf_Export"

    else:
        export_args[0].Value = "writer_pdf_Export"  # default

    document.storeToURL(pdf_url, export_args)
    document.close(True)
    print(f"Converted to PDF: {output_path}")

@app.get("/loco/")
async def root():
	return JSONResponse(content={"message": "Welcome to LoCo Service - Libreoffice Converter"})

@app.post("/loco/convert_sub")
async def convert_sub(files: Annotated[List[UploadFile], Form()]):
    request_id = str(uuid.uuid4())
    dispatch_info = []

    # Create a Temp Dir for each request
    TEMP_DIR_IN = STAGING_DIRECTORY_IN / request_id
    TEMP_DIR_OUT = STAGING_DIRECTORY_OUT / request_id

    

    TEMP_DIR_IN.mkdir(parents=True, exist_ok=True, mode=0o777)
    TEMP_DIR_OUT.mkdir(parents=True, exist_ok=True, mode=0o777)
    # os.chmod(TEMP_DIR_IN, 0o777)
    # os.chmod(TEMP_DIR_OUT, 0o777)
    for i, file in enumerate(files):
        file_name = file.filename
        # Process files
        input_path = TEMP_DIR_IN / file.filename

        mime_type = file.content_type

        with open(input_path, "wb") as file_:
            shutil.copyfileobj(file.file, file_)
        await file.seek(0)
        uploaded_hash = get_file_hash(file.file)

        # os.fsync()

        out_filename = file.filename.rsplit('.', 1)[0] + ".pdf"
        output_path = TEMP_DIR_OUT / out_filename
        print("Input, Output Paths: ", input_path, output_path)
        print("check if file exists : ", os.path.exists(input_path))
        print("Size of file object vs uploadfile",
              os.path.getsize(input_path), file.size)
        with open(input_path, "rb") as f:
            c = f.read()
            f.seek(0)
            written_hash = get_file_hash(f)
            f.flush()
        print("Read file: ", str(c)[:100])
        print("verifying hash of files: ", uploaded_hash, written_hash)
        print(str(output_path.parent))
        # time.sleep(5)
        process = await asyncio.create_subprocess_shell(
            f"C:\\Users\\kuvukai\\dev\\libreoffice\\program\\soffice --headless --nologo --nofirststartwizard --convert-to pdf:writer_pdf_Export {str(input_path)} --outdir {str(output_path.parent)}")
        # time.sleep(20)
        print(process)
        stdout, stderr = await process.communicate()
        if process.returncode == 0:
            print(f'Success: {stdout}')
        else:
            print(f'Error: {stderr}')
    return StreamingResponse(zip_directory(in_directory_path=str(TEMP_DIR_IN), out_directory_path=str(TEMP_DIR_OUT)))

@app.post("/loco/convert")
async def convert(files: Annotated[List[UploadFile], Form()]):
    request_id = str(uuid.uuid4())
    dispatch_info = []

    #Create a Temp Dir for each request
    TEMP_DIR_IN = STAGING_DIRECTORY_IN / request_id
    TEMP_DIR_OUT = STAGING_DIRECTORY_OUT / request_id

    TEMP_DIR_IN.mkdir(parents=True, exist_ok=True)
    TEMP_DIR_OUT.mkdir(parents=True, exist_ok=True)

    TEMP_DIR_IN.mkdir(parents=True, exist_ok=True, mode=0o777)
    TEMP_DIR_OUT.mkdir(parents=True, exist_ok=True, mode=0o777)

    for i, file in enumerate(files):
        file_name = file.filename
        #Process files
        input_path = TEMP_DIR_IN / file.filename

        
        mime_type = file.content_type
        content = await file.read()
        with open(input_path, "wb") as file_:
            file_.write(content)
            file_.seek(0)
        await file.seek(0)
        file.file.seek(0)
        uploaded_hash = get_file_hash(file.file)
        await file.seek(0)

        
        # os.fsync()

        out_filename = file.filename.rsplit('.', 1)[0] + ".pdf"
        output_path = TEMP_DIR_OUT / out_filename
        print("Input, Output Paths: ", input_path, output_path)
        print("check if file exists : ",os.path.exists(input_path))
        print("Size of file object vs uploadfile", os.path.getsize(input_path), file.size)
        with open(input_path, "rb") as f:
            c = f.read()
            f.seek(0)
            written_hash = get_file_hash(f)
        print("Read file: ", str(c)[:100])
        print("verifying hash of files: ", uploaded_hash, written_hash)

        os.chmod(input_path, 0o777)
        # os.chmod(output_path, 0o777)
        convert_to_pdf(str(input_path), str(output_path), mime_type)
    return StreamingResponse(zip_directory(in_directory_path = str(TEMP_DIR_IN), out_directory_path = str(TEMP_DIR_OUT)))



def zip_directory(in_directory_path: str, out_directory_path: str):
	memory_file = io.BytesIO()
	with zipfile.ZipFile(memory_file, 'w', zipfile.ZIP_DEFLATED) as zipf:
		for root, dirs, files in os.walk(out_directory_path):
			for file in files:
				file_path = os.path.join(root, file)
				with open(file_path, 'rb') as f:
					file_content = f.read()
					zipf.writestr(os.path.relpath(file_path, out_directory_path), file_content)
					
	memory_file.seek(0)
	try:
		yield memory_file.read()
		
	finally:
		
		"""Clearing Temperory Files"""
		print("inside finally... ")
		shutil.rmtree(in_directory_path)
		shutil.rmtree(out_directory_path)
