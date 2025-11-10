import os
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional
from bson import ObjectId

from database import db, create_document, get_documents

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Pydantic models for requests/responses
class TaskCreate(BaseModel):
    title: str
    description: Optional[str] = None
    priority: Optional[str] = None

class TaskUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    completed: Optional[bool] = None
    priority: Optional[str] = None


@app.get("/")
def read_root():
    return {"message": "Fantasy Task API is running"}


@app.get("/api/tasks")
def list_tasks():
    if db is None:
        raise HTTPException(status_code=500, detail="Database not configured")
    tasks = get_documents("task", {})
    # Convert ObjectId to string
    for t in tasks:
        t["id"] = str(t.get("_id"))
        t.pop("_id", None)
    return {"tasks": tasks}


@app.post("/api/tasks", status_code=201)
def create_task(payload: TaskCreate):
    if db is None:
        raise HTTPException(status_code=500, detail="Database not configured")
    from schemas import Task as TaskSchema
    data = TaskSchema(
        title=payload.title,
        description=payload.description,
        priority=payload.priority,
        completed=False,
    )
    new_id = create_document("task", data)
    # Fetch created doc
    doc = db["task"].find_one({"_id": ObjectId(new_id)})
    doc_out = {"id": str(doc.get("_id")), "title": doc.get("title"), "description": doc.get("description"), "completed": doc.get("completed", False), "priority": doc.get("priority"), "created_at": doc.get("created_at"), "updated_at": doc.get("updated_at")}
    return doc_out


@app.patch("/api/tasks/{task_id}")
def update_task(task_id: str, payload: TaskUpdate):
    if db is None:
        raise HTTPException(status_code=500, detail="Database not configured")
    try:
        oid = ObjectId(task_id)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid task id")

    updates = {k: v for k, v in payload.model_dump(exclude_none=True).items()}
    if not updates:
        return {"message": "No changes"}

    result = db["task"].update_one({"_id": oid}, {"$set": updates})
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Task not found")
    doc = db["task"].find_one({"_id": oid})
    doc_out = {"id": str(doc.get("_id")), "title": doc.get("title"), "description": doc.get("description"), "completed": doc.get("completed", False), "priority": doc.get("priority"), "created_at": doc.get("created_at"), "updated_at": doc.get("updated_at")}
    return doc_out


@app.delete("/api/tasks/{task_id}", status_code=204)
def delete_task(task_id: str):
    if db is None:
        raise HTTPException(status_code=500, detail="Database not configured")
    try:
        oid = ObjectId(task_id)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid task id")

    result = db["task"].delete_one({"_id": oid})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Task not found")
    return {}


@app.get("/test")
def test_database():
    """Test endpoint to check if database is available and accessible"""
    response = {
        "backend": "✅ Running",
        "database": "❌ Not Available",
        "database_url": None,
        "database_name": None,
        "connection_status": "Not Connected",
        "collections": []
    }
    
    try:
        from database import db
        
        if db is not None:
            response["database"] = "✅ Available"
            response["database_url"] = "✅ Configured"
            response["database_name"] = db.name if hasattr(db, 'name') else "✅ Connected"
            response["connection_status"] = "Connected"
            
            try:
                collections = db.list_collection_names()
                response["collections"] = collections[:10]
                response["database"] = "✅ Connected & Working"
            except Exception as e:
                response["database"] = f"⚠️  Connected but Error: {str(e)[:50]}"
        else:
            response["database"] = "⚠️  Available but not initialized"
            
    except ImportError:
        response["database"] = "❌ Database module not found (run enable-database first)"
    except Exception as e:
        response["database"] = f"❌ Error: {str(e)[:50]}"
    
    import os
    response["database_url"] = "✅ Set" if os.getenv("DATABASE_URL") else "❌ Not Set"
    response["database_name"] = "✅ Set" if os.getenv("DATABASE_NAME") else "❌ Not Set"
    
    return response


if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
