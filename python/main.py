import os
import logging
import pathlib
from fastapi import FastAPI, Form, HTTPException, Depends, UploadFile, File, Query
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware
import sqlite3
from pydantic import BaseModel
from contextlib import asynccontextmanager
import json
import hashlib
import sqlite3
import threading
import time

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
    conn = sqlite3.connect(db)
    cursor = conn.cursor()
    items_file = pathlib.Path(__file__).parent.resolve() / "db" / "items.sql"
    categories_file = pathlib.Path(__file__).parent.resolve() / "db" / "categories.sql"
    with open(items_file, "r") as f:
        cursor.executescript(f.read())
    with open(categories_file, "r") as f:
        cursor.executescript(f.read())
    conn.commit()
    conn.close()

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
def add_item(
    name: str = Form(...),
    category: str = Form(...),
    image: UploadFile = File(...),
    db: sqlite3.Connection = Depends(get_db),
):
    if not name:
        raise HTTPException(status_code=400, detail="name is required")
    if not category:
        raise HTTPException(status_code=400, detail="category is required")

    #STEP6 のためにコメントアウトしておく（念のため）
    # if not image:
    #     raise HTTPException(status_code=400, detail="image is required")

    image_bin = image.file.read()
    hashed_image = hashlib.sha256(image_bin).hexdigest()
    
    insert_item(Item(name=name, category=category, image=hashed_image), db)

    with open('images/' + hashed_image + '.jpg', 'wb') as f:
        f.write(image_bin)

    return AddItemResponse(**{"message": f"item received: {name}"})

@app.get("/items")
def get_items():
    with sqlite3.connect(db) as conn:
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute('''
                    SELECT items.id, items.name, categories.name, items.image
                    FROM items
                    LEFT JOIN categories
                            ON categories.id = items.category_id
                       ''')
        col_names = [d[0] for d in cursor.description]
        rows = cursor.fetchall()
        items = [{colname:row[colname] for colname in col_names} for row in rows]
    return {'items' : items}

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

@app.get("/search")
def search_keyword(keyword):
    with sqlite3.connect(db) as conn:
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute('''
                        SELECT
                            items.id as id, 
                            items.name as name, 
                            categories.name as category, 
                            items.image as image
                        FROM items
                        LEFT JOIN categories
                            ON categories.id = items.category_id 
                        WHERE items.name like ?
                       ''', ('%' + keyword + '%',))
        rows = cursor.fetchall()
        col_names = ['name', 'category', 'image']
        items = [{colname:row[colname] for colname in col_names} for row in rows]
    
    return {'items' : items}

class Item(BaseModel):
    name:str
    category:str
    image:str

def insert_item(item: Item, db: sqlite3.Connection):
    # STEP 5 : add an implementation to store an item in the database
    cursor = db.cursor()
    cursor.execute('''
            INSERT INTO categories (name)
            SELECT ?
            WHERE NOT EXISTS(
                   SELECT 1 FROM categories WHERE name = ?
                   )
        ''', (item.category, item.category))
    cursor.execute('''
            SELECT id FROM categories 
            WHERE name =  ?
        ''', (item.category,))
    category_id = cursor.fetchone()[0]
    cursor.execute('''
            INSERT INTO items (name, category_id, image)
            VALUES (?, ?, ?)
        ''', (item.name, category_id, item.image))
    db.commit()
    cursor.close()
