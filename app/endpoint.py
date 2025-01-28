from fastapi import FastAPI, HTTPException, Depends
from pydantic import BaseModel, Field
from typing import Optional, List
from sqlalchemy import create_engine, Column, String, Text, Boolean, DateTime
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
from datetime import datetime, timedelta
import uuid
import os

# Database URL
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./test.db")

# SQLAlchemy setup
engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False} if "sqlite" in DATABASE_URL else {})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

app = FastAPI()

# Database models
class TaskModel(Base):
    __tablename__ = "tasks"
    id = Column(String, primary_key=True, index=True, default=lambda: str(uuid.uuid4()))
    title = Column(String(100), unique=True, nullable=False)
    description = Column(Text, nullable=True)
    status = Column(String, default="TODO")

class PomodoroSession(Base):
    __tablename__ = "pomodoro_sessions"
    id = Column(String, primary_key=True, index=True, default=lambda: str(uuid.uuid4()))
    task_id = Column(String, nullable=False)
    start_time = Column(DateTime, nullable=False)
    end_time = Column(DateTime, nullable=False)
    completed = Column(Boolean, default=False)

# Create database tables
Base.metadata.create_all(bind=engine)

# Dependency for DB session
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# Pydantic models
class Task(BaseModel):
    title: str = Field(..., min_length=3, max_length=100)
    description: Optional[str] = Field(None, max_length=300)
    status: str = Field(default="TODO", regex="^(TODO|IN_PROGRESS|DONE)$")

@app.get("/")
def read_root():
    return {"message": "Witaj w aplikacji TODO z obsługą Pomodoro!"}

@app.post("/tasks")
def create_task(task: Task, db: Session = Depends(get_db)):
    if db.query(TaskModel).filter(TaskModel.title == task.title).first():
        raise HTTPException(status_code=400, detail="Tytuł zadania musi być unikalny.")
    new_task = TaskModel(title=task.title, description=task.description, status=task.status)
    db.add(new_task)
    db.commit()
    db.refresh(new_task)
    return {"message": "Zadanie zostało utworzone.", "task": new_task}

@app.get("/tasks", response_model=List[dict])
def get_tasks(status: Optional[str] = None, db: Session = Depends(get_db)):
    query = db.query(TaskModel)
    if status:
        query = query.filter(TaskModel.status == status)
    return query.all()

@app.get("/tasks/{task_id}", response_model=dict)
def get_task(task_id: str, db: Session = Depends(get_db)):
    task = db.query(TaskModel).filter(TaskModel.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="Zadanie nie zostało znalezione.")
    return task

@app.put("/tasks/{task_id}")
def update_task(task_id: str, updated_task: Task, db: Session = Depends(get_db)):
    task = db.query(TaskModel).filter(TaskModel.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="Zadanie nie zostało znalezione.")

    if db.query(TaskModel).filter(TaskModel.title == updated_task.title, TaskModel.id != task_id).first():
        raise HTTPException(status_code=400, detail="Tytuł zadania musi być unikalny.")

    task.title = updated_task.title
    task.description = updated_task.description
    task.status = updated_task.status
    db.commit()
    return {"message": "Zadanie zostało zaktualizowane.", "task": task}

@app.delete("/tasks/{task_id}")
def delete_task(task_id: str, db: Session = Depends(get_db)):
    task = db.query(TaskModel).filter(TaskModel.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="Zadanie nie zostało znalezione.")

    db.delete(task)
    db.commit()
    return {"message": "Zadanie zostało usunięte."}

@app.post("/pomodoro")
def create_pomodoro(task_id: str, db: Session = Depends(get_db)):
    task = db.query(TaskModel).filter(TaskModel.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="Zadanie nie zostało znalezione.")

    if db.query(PomodoroSession).filter(PomodoroSession.task_id == task_id, PomodoroSession.completed == False).first():
        raise HTTPException(status_code=400, detail="Pomodoro dla tego zadania jest już aktywne.")

    start_time = datetime.now()
    end_time = start_time + timedelta(minutes=25)

    session = PomodoroSession(task_id=task_id, start_time=start_time, end_time=end_time, completed=False)
    db.add(session)
    db.commit()
    return {"message": "Timer Pomodoro został uruchomiony.", "session": session}

@app.post("/pomodoro/{task_id}/stop")
def stop_pomodoro(task_id: str, db: Session = Depends(get_db)):
    session = db.query(PomodoroSession).filter(PomodoroSession.task_id == task_id, PomodoroSession.completed == False).first()
    if not session:
        raise HTTPException(status_code=404, detail="Brak aktywnego Pomodoro dla tego zadania.")

    session.completed = True
    db.commit()
    return {"message": "Pomodoro zostało zatrzymane.", "session": session}

@app.get("/pomodoro/stats")
def get_pomodoro_stats(db: Session = Depends(get_db)):
    stats = {}
    sessions = db.query(PomodoroSession).filter(PomodoroSession.completed == True).all()
    for session in sessions:
        stats[session.task_id] = stats.get(session.task_id, 0) + 25

    return {"message": "Statystyki Pomodoro.", "stats": stats}
