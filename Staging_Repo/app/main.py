from fastapi import FastAPI, Depends, HTTPException
from sqlalchemy.orm import Session
from . import models, crud, database

app = FastAPI()

# Create tables if not exists (simple migration)
models.Base.metadata.create_all(bind=database.engine)

def get_db():
    db = database.SessionLocal()
    try:
        yield db
    finally:
        db.close()

@app.get("/users")
def read_users(db: Session = Depends(get_db)):
    return crud.get_users(db)

@app.post("/users")
def add_user(name: str, email: str, db: Session = Depends(get_db)):
    return crud.create_user(db, name, email)

