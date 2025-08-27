import logging
import random
import time
from fastapi import FastAPI, Request, Depends, HTTPException, status
from sqlalchemy.orm import Session

from . import auth, crud, models, schemas
from .database import SessionLocal, engine

# Create database tables
models.Base.metadata.create_all(bind=engine)

# --- OpenTelemetry Tracing Setup ---
from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor, ConsoleSpanExporter
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.sdk.resources import Resource

resource = Resource(attributes={"service.name": "fastapi-service"})
provider = TracerProvider(resource=resource)
otlp_exporter = OTLPSpanExporter(endpoint="tempo:4317", insecure=True)
provider.add_span_processor(BatchSpanProcessor(otlp_exporter))
provider.add_span_processor(BatchSpanProcessor(ConsoleSpanExporter()))
trace.set_tracer_provider(provider)
tracer = trace.get_tracer(__name__)

# --- Logging Setup ---
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s - trace_id=%(otelTraceID)s - span_id=%(otelSpanID)s',
)
logger = logging.getLogger(__name__)

# --- FastAPI App ---
app = FastAPI()

# --- Prometheus Instrumentation ---
from prometheus_fastapi_instrumentator import Instrumentator
Instrumentator().instrument(app).expose(app)

# Dependency to get DB session
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@app.middleware("http")
async def log_and_trace_middleware(request: Request, call_next):
    span = trace.get_current_span()
    trace_id = span.get_span_context().trace_id
    span_id = span.get_span_context().span_id
    old_factory = logging.getLogRecordFactory()
    def record_factory(*args, **kwargs):
        record = old_factory(*args, **kwargs)
        record.otelTraceID = format(trace_id, 'x')
        record.otelSpanID = format(span_id, 'x')
        return record
    logging.setLogRecordFactory(record_factory)
    response = await call_next(request)
    logging.setLogRecordFactory(old_factory)
    return response

@app.get("/")
def read_root():
    with tracer.start_as_current_span("read_root_span"):
        logger.info("Received request for root endpoint.")
        processing_time = random.uniform(0.1, 0.6)
        time.sleep(processing_time)
        logger.info(f"Root request processed in {processing_time:.2f} seconds.")
        return {"message": "Hello, Observability World!"}

@app.post("/signup/", response_model=schemas.User)
def create_user(user: schemas.UserCreate, db: Session = Depends(get_db)):
    with tracer.start_as_current_span("create_user_span"):
        db_user = crud.get_user_by_email(db, email=user.email)
        if db_user:
            logger.warning(f"Signup attempt for existing email: {user.email}")
            raise HTTPException(status_code=400, detail="Email already registered")
        logger.info(f"Creating new user for email: {user.email}")
        return crud.create_user(db=db, user=user)

@app.post("/login/", response_model=schemas.Token)
def login_for_access_token(form_data: schemas.UserLogin, db: Session = Depends(get_db)):
     with tracer.start_as_current_span("login_span"):
        user = auth.authenticate_user(db, email=form_data.email, password=form_data.password)
        if not user:
            logger.warning(f"Failed login attempt for email: {form_data.email}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Incorrect email or password",
                headers={"WWW-Authenticate": "Bearer"},
            )
        access_token = auth.create_access_token(data={"sub": user.email})
        logger.info(f"User logged in successfully: {user.email}")
        return {"access_token": access_token, "token_type": "bearer"}

@app.get("/users/me/", response_model=schemas.User)
async def read_users_me(current_user: models.User = Depends(auth.get_current_active_user)):
    with tracer.start_as_current_span("get_current_user_span"):
        logger.info(f"Fetching profile for user: {current_user.email}")
        return current_user
