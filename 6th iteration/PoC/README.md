# AI Assisted Software Verification Tool — React + FastAPI POC

This version separates the frontend and backend so upload progress animation runs in the browser while Python processes the uploaded requirements file.

## Project structure

```text
backend/
  main.py
  requirements.txt

frontend/
  index.html
  package.json
  src/
    main.jsx
    styles.css
```

## 1. Run the Python API backend (main.py)

open a terminal

cd "/Users/nicklee/Downloads/practise/SAD_Term Project/6th iteration/PoC/backend"
/Users/nicklee/Downloads/practise/.venv/bin/python -m uvicorn main:app --reload --host 127.0.0.1 --port 8000

## 2. Run the React frontend (main.jsx)

Open a second terminal:

cd "/Users/nicklee/Downloads/practise/SAD_Term Project/6th iteration/PoC/frontend"
npm run dev

## 3. Upload file format

Use a CSV or Excel file