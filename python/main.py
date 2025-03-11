import os
import logging
import pathlib
from fastapi import FastAPI, Form, HTTPException, Depends, UploadFile, File
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware
import sqlite3
from pydantic import BaseModel
from contextlib import asynccontextmanager
import json
import hashlib
import sqlite3

# Define the path to the images & sqlite3 database
images = pathlib.Path(__file__).parent.resolve() / "images"
db = pathlib.Path(__file__).parent.resolve() / "db" / "mercari.sqlite3"


def get_db():
    if not db.exists():
        yield

    conn = sqlite3.connect(db)
    conn.row_factory = sqlite3.Row  # Return rows as dictionaries
    try:
        yield conn
    finally:
        conn.close()


# STEP 5-1: set up the database connection
def setup_database():
    conn = sqlite3.connect("db/mercari.sqlite3")
    cursor = conn.cursor()
    


@asynccontextmanager
async def lifespan(app: FastAPI):
    setup_database()
    yield


app = FastAPI(lifespan=lifespan)

logger = logging.getLogger("uvicorn")
logger.level = logging.INFO
images = pathlib.Path(__file__).parent.resolve() / "images"
origins = [os.environ.get("FRONT_URL", "http://localhost:3000")]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=False,
    allow_methods=["GET", "POST", "PUT", "DELETE"],
    allow_headers=["*"],
)

class HelloResponse(BaseModel):
    message: str


@app.get("/", response_model=HelloResponse)
def hello():
    return HelloResponse(**{"message": "Hello, world!"})


class AddItemResponse(BaseModel):
    message: str


# add_item is a handler to add a new item for POST /items .
@app.post("/items", response_model=AddItemResponse)
async def add_item(
    name: str = Form(...),
    category: str = Form(...),
    image: UploadFile = File(...),
    db: sqlite3.Connection = Depends(get_db),
):
    if not name:
        raise HTTPException(status_code=400, detail="name is required")
    if not category:
        raise HTTPException(status_code=400, detail="category is required")
    if not image:
        raise HTTPException(status_code=400, detail="image is required")

    image_bin = await image.read()
    sha256 = hashlib.sha256(image_bin).hexdigest()
    
    insert_item(Item(name=name, category=category, image=sha256))

    with open('images/' + sha256 + '.jpg', 'wb') as f:
        f.write(image_bin)

    return AddItemResponse(**{"message": f"item received: {name}"})

@app.get("/items")
def get_items():
    with open('items.json') as f:
        d_update = json.load(f)
    return d_update

@app.get("/items/{item_id}")
def get_items(item_id:int):
    with open('items.json') as f:
        d_update = json.load(f)
    return d_update['items'][item_id]

# get_image is a handler to return an image for GET /images/{filename} .
@app.get("/image/{image_name}")
async def get_image(image_name):
    # Create image path
    image = images / image_name

    if not image_name.endswith(".jpg"):
        raise HTTPException(status_code=400, detail="Image path does not end with .jpg")

    ## No_image のハッシュ値と一致する画像が表示されたなら、その場合も同様に以下を実行する
    if not image.exists():
        logger.debug(f"Image not found: {image}")
        image = images / "default.jpg"

    return FileResponse(image)


class Item(BaseModel):
    name:str
    category:str
    image:str
    db: sqlite3.Connection

def insert_item(item: Item):
    # # STEP 4-1: add an implementation to store an item
    # with open('items.json') as f:
    #     d_update = json.load(f)

    d = {'name' : item.name, 'category': item.category, 'image_name':item.image}
    # d_update['items'].append(d)

    # with open('items.json', 'w') as f:
    #     json.dump(d_update, f, indent=2)
    
    # STEP 5 : add an implementation to store an item in the database
    cursor.execute("""
    INSERT INTO items (name, category, image_name) 
    VALUES (:name, :category, :image_name)
    """, d)




