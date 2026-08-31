from fastapi import BackgroundTasks, FastAPI, File, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from backend.schemas import AuditDto, CreateAuditRequest, FindingStatusRequest, JobDto
from backend.service import UPLOAD_ROOT, create_audit, create_job, run_analysis, save_screens
from backend.storage import STORE

app = FastAPI(title="DarkAudit API", version="0.1.0")
app.add_middleware(CORSMiddleware, allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
                   allow_credentials=True, allow_methods=["*"], allow_headers=["*"])
UPLOAD_ROOT.mkdir(parents=True, exist_ok=True)
app.mount("/uploads", StaticFiles(directory=UPLOAD_ROOT), name="uploads")

@app.get("/health")
def health(): return {"status": "ok"}

@app.post("/api/v1/audits", response_model=AuditDto, status_code=201)
def post_audit(request: CreateAuditRequest): return create_audit(request)

@app.post("/api/v1/audits/{audit_id}/screens", response_model=AuditDto)
def post_screens(audit_id: str, files: list[UploadFile] = File(...), screen_ids: list[str] = Form(...), flow_steps: list[str] = Form(...)):
    try: return save_screens(audit_id, files, screen_ids, flow_steps)
    except KeyError: raise HTTPException(404, "Audit not found")
    except ValueError as exc: raise HTTPException(400, str(exc))

@app.post("/api/v1/audits/{audit_id}/analyze", response_model=JobDto, status_code=202)
def post_analysis(audit_id: str, tasks: BackgroundTasks):
    try: job = create_job(audit_id)
    except KeyError: raise HTTPException(404, "Audit not found")
    except ValueError as exc: raise HTTPException(400, str(exc))
    tasks.add_task(run_analysis, job.jobId)
    return job

@app.get("/api/v1/analysis-jobs/{job_id}", response_model=JobDto)
def get_job(job_id: str):
    if job_id not in STORE.jobs: raise HTTPException(404, "Job not found")
    return STORE.jobs[job_id]

@app.get("/api/v1/dashboard/summary")
def dashboard_summary():
    audits = sorted(STORE.audits.values(), key=lambda item: item.updatedAt, reverse=True)
    return {"activeAuditId": audits[0].id if audits else None, "audits": audits}

@app.patch("/api/v1/findings/{finding_id}")
def patch_finding(finding_id: str, request: FindingStatusRequest):
    for audit in STORE.audits.values():
        for finding in audit.findings:
            if finding.id == finding_id:
                finding.status = request.status
                return {"id": finding.id, "status": finding.status}
    raise HTTPException(404, "Finding not found")
