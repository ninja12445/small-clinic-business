from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI()

# allow frontend to talk to backend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/hello")
def hello():
    return {"message": "Hello from Python backend"}

@app.get("/user")
def user():
    return {
        "name": "John",
        "age": 25
    }
    
# CD project, uvicorn main:app --reload --port 8000
# front end npm run dev  
# git branch, merge, PR
#  git clone https://github.com/ninja12445/small-clinic-business.git~

git clone https://github.com/ninja12445/small-clinic-business.git

Step 4.1: Stage file
git add README.md
Step 4.2: Commit
git commit -m "Add README file"