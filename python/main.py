from random import shuffle
import shutil
from math import fabs
import os
import logging
import pathlib
from re import I
import sqlite3
import hashlib
from turtle import circle
from fastapi import FastAPI, Form, HTTPException, UploadFile, File
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI()
logger = logging.getLogger("uvicorn")
logger.level = logging.INFO
images = pathlib.Path(__file__).parent.resolve() / "image"
origins = [ os.environ.get('FRONT_URL', 'http://localhost:3000') ]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=False,
    allow_methods=["GET","POST","PUT","DELETE"],
    allow_headers=["*"],
)

db_path = "../db/mercari.sqlite3"
con = sqlite3.connect(db_path, check_same_thread=False)
cur = con.cursor()

@app.on_event("startup")
def init_db():
    schema_path = "../db/items.db"
    if not cur.fetchone():
        with open(schema_path,"r") as s:
            create = s.read()
            cur.executescript(create)
            con.commit()
    logger.info("Completed database connection")
    return

@app.get("/")
def root():
    return {"message": "Hello, world!"}

@app.post("/items")
def add_item(name: str = Form(...), category: str = Form(...), image: UploadFile= File(...)):
    img = image.filename
    logger.info(f"Receive item: {name},{category},{img}")

    num = cur.execute("select max(rowid) from items").fetchone()[0] 
    if num== None:
        num = 1
    else:
        num = int(num) + 1

    imgname, imgextension = img.split(".")
    hashed_imgname = hashlib.sha256(imgname.encode('utf-8')).hexdigest() + "." + imgextension

    cur.execute("insert into items values(?,?,?,?)",(num,name,category,hashed_imgname))
    con.commit()

    image_dir = "images/{}".format(hashed_imgname)

    with open(image_dir,"wb") as buffer:
        shutil.copyfileobj(image.file,buffer)
        
    logger.info(f"append imtem in db: {name},{category},{img}")

    return {"message": f"item received: {name},{category},{img}"}


@app.get("/items")
def get_item():
    return cur.execute("select * from items").fetchall()


@app.get("/items/{item_id}")
def get_item(item_id):
    id_item = cur.execute("select * from items where id=:item_id",{"item_id":item_id}).fetchone()
    if id_item:
        return id_item
    else:
        return "Sorry but no items has id: {} :( ".format(item_id)


@app.get("/image/{items_image}")
async def get_image(items_image):
    # Create image path
    image = images / items_image

    if not items_image.endswith(".jpg"):
        raise HTTPException(status_code=400, detail="Image path does not end with .jpg")

    if not image.exists():
        logger.debug(f"Image not found: {image}")
        image = images / "default.jpg"

    return FileResponse(image)

@app.get("/search")
def search_name(keyword:str):
    logger.info("{}".format(keyword))
    try:
        keyitems = cur.execute("select * from items where name=:keyword",{"keyword":keyword}).fetchall()
    except:
        return "Sorry but any items are not existed :( "
    if len(keyitems) == 0:
        return "I'sorry but {} is not existed :( ".format(keyword)
    else:
        return keyitems

@app.on_event("shutdown")
def close_db():
    con.close()
    logger.info("Database Shutdown")
    return


