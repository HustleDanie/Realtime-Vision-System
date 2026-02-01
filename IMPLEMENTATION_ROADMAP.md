# 🚀 IMPLEMENTATION ROADMAP: Complete Your Portfolio

## Phase 1: Critical Missing Pieces (2-3 hours)

### Task 1.1: Create Retraining Trigger API Endpoint
**File to Create:** `src/monitoring_api/routers/retraining.py`
**Difficulty:** Easy (30 min)
**Importance:** 🔴 CRITICAL

```python
# Structure:
- GET /api/retraining/status -> Check if retraining in progress
- POST /api/retraining/trigger -> Manually trigger retraining
- GET /api/retraining/history -> Show past retraining events
- GET /api/retraining/conditions -> Show drift/label counts

# Integration Points:
- Import: scripts.retraining_trigger.should_retrain()
- Check: drift_json path, new_labels path
- If true: Execute scripts/train_yolo_dvc_mlflow.py
- Track: Start time, end time, status in database
```

**Acceptance Criteria:**
- ✅ Can check if retraining should happen
- ✅ Can manually trigger retraining
- ✅ Returns current status/progress
- ✅ Logs to database

---

### Task 1.2: Create Database Models for Labeling
**File to Modify:** `src/logging_service/database.py`
**Difficulty:** Easy (20 min)
**Importance:** 🔴 CRITICAL

Add these SQLAlchemy models:

```python
class LabelingQueue(Base):
    """Queue for manual labeling of uncertain predictions"""
    __tablename__ = "labeling_queue"
    
    id = Column(Integer, primary_key=True)
    prediction_id = Column(Integer, ForeignKey("prediction_logs.id"))
    image_path = Column(String(512))
    confidence_score = Column(Float)  # 0.4-0.7 uncertain range
    status = Column(String(20), default="pending")  # pending, labeled, approved
    created_at = Column(DateTime, default=datetime.utcnow)
    labeled_at = Column(DateTime, nullable=True)
    human_label = Column(String(100), nullable=True)
    reviewer_notes = Column(Text, nullable=True)
    flagged_reason = Column(String(100))  # "low_confidence", "drift", etc.

class ReviewedLabel(Base):
    """Reviewed and approved labels for retraining"""
    __tablename__ = "reviewed_labels"
    
    id = Column(Integer, primary_key=True)
    image_id = Column(String(255), unique=True)
    image_path = Column(String(512))
    label = Column(String(100))
    confidence = Column(Float)
    reviewer = Column(String(100))
    created_at = Column(DateTime, default=datetime.utcnow)
    used_for_training = Column(Boolean, default=False)
```

---

### Task 1.3: Extend Logging Service API
**File to Modify:** `src/logging_service/logger.py`
**Difficulty:** Medium (20 min)
**Importance:** 🟠 HIGH

Add methods:
```python
class VisionLogger:
    def get_labeling_queue(self, limit=50):
        """Get pending items for labeling"""
        
    def submit_label(self, queue_id, label, reviewer_notes):
        """Save human label and mark complete"""
        
    def approve_label(self, queue_id):
        """Approve label for training dataset"""
        
    def export_labels_for_training(self, output_dir):
        """Export approved labels in YOLO format"""
```

---

## Phase 2: Frontend UI Components (2 hours)

### Task 2.1: Create Labeling Queue Page
**File to Create:** `omnisearch-frontend/src/app/labeling-queue/page.tsx`
**Difficulty:** Medium (45 min)
**Importance:** 🔴 CRITICAL

Features needed:
```typescript
// Components:
- Queue Stats Card (pending, completed, approved)
- Image Viewer (show uncertain prediction with confidence)
- Label Selector (dropdown of defect types)
- Notes Input (optional reviewer notes)
- Action Buttons (Label, Skip, Flag as mistake)
- History Table (past labeled items)

// State Management:
- useEffect: Fetch queue from /api/inspection-logs?uncertain=true
- State: current_item, queue_items, loading, error
- Mutations: submit_label(), approve_label()

// API Calls:
- GET /api/labeling-queue -> Get pending items
- POST /api/labeling-queue/{id}/label -> Submit label
- GET /api/labeling-queue/stats -> Get statistics
```

**Mockup Structure:**
```
┌─────────────────────────────────────┐
│ LABELING QUEUE (23 pending)         │
├─────────────────────────────────────┤
│ ┌─────────────┐  Confidence: 0.68   │
│ │   IMAGE     │  Reason: Low Conf   │
│ │             │                     │
│ └─────────────┘  [Defect ▼]         │
│                  [Label] [Skip]     │
├─────────────────────────────────────┤
│ Recently Labeled:                   │
│ ✓ item_001 - Crack - 2min ago       │
│ ✓ item_002 - Dent - 5min ago        │
└─────────────────────────────────────┘
```

---

### Task 2.2: Add Retraining Status Widget
**File to Modify:** `omnisearch-frontend/src/components/dashboard-layout.tsx`
**Difficulty:** Easy (30 min)
**Importance:** 🟠 HIGH

Add widget showing:
```typescript
- Retraining Status (idle, running, completed)
- Progress Bar (if running)
- Last Retrained (timestamp)
- Trigger Button (if conditions met)
- Next Conditions Check (Drift? New Labels?)

// API Call:
- GET /api/retraining/status
- POST /api/retraining/trigger (optional)
```

---

### Task 2.3: Enhance Drift Monitoring Page
**File to Modify:** `omnisearch-frontend/src/app/drift-monitoring/page.tsx`
**Difficulty:** Medium (45 min)
**Importance:** 🟠 HIGH

Show:
```typescript
- Real-time Drift Metrics
  - Overall Drift Score (0-1)
  - P-value
  - Drift Share (%)
  
- Feature-Level Drift
  - Brightness drift
  - Blur drift
  - Color drift
  - Noise levels
  
- Drift Timeline Graph
  - Last 7 days
  - Highlight when > threshold
  
- Alert System
  - Red if drift > 0.7
  - Yellow if drift > 0.3
  - Green if normal

// API Calls:
- GET /api/metrics/drift -> Get drift data
- GET /api/metrics/drift/history -> Time series
```

---

## Phase 3: API Completion (1 hour)

### Task 3.1: Create Complete Retraining Router
**File:** `src/monitoring_api/routers/retraining.py`

```python
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
import subprocess
from pathlib import Path

router = APIRouter()

class RetrainingStatus(BaseModel):
    status: str  # "idle", "running", "completed", "failed"
    last_retrain_time: Optional[str]
    drift_detected: bool
    new_labels_count: int
    should_retrain: bool

@router.get("/status")
async def get_retraining_status() -> RetrainingStatus:
    # Check conditions using retraining_trigger.should_retrain()
    # Return status
    pass

@router.post("/trigger")
async def trigger_retraining():
    # Check if already running
    # Execute: python scripts/train_yolo_dvc_mlflow.py
    # Return job_id for monitoring
    pass

@router.get("/history")
async def get_retraining_history(limit: int = 10):
    # Query database for past retraining events
    pass

@router.get("/conditions")
async def check_conditions():
    # Return current drift level, new labels count
    # Explain why retraining should/shouldn't run
    pass
```

---

### Task 3.2: Create Labeling Queue Router
**File:** `src/monitoring_api/routers/labeling.py`

```python
@router.get("/queue")
async def get_labeling_queue(limit: int = 50, status: str = "pending"):
    # Return items from labeling_queue table
    pass

@router.post("/queue/{item_id}/label")
async def submit_label(item_id: int, label: str, notes: str = None):
    # Save label to database
    # Check if retraining should trigger
    pass

@router.get("/stats")
async def get_queue_stats():
    # Return: pending_count, labeled_count, approved_count
    pass

@router.get("/export")
async def export_for_training(format: str = "yolo"):
    # Export approved labels in YOLO format
    # Return download URL
    pass
```

---

## Phase 4: Database Setup (30 min)

### Task 4.1: Run Database Migrations

```bash
# In project root:
python -c "
from src.logging_service.database import Base, engine
Base.metadata.create_all(engine)
print('✓ Database tables created')
"
```

### Task 4.2: Initialize Tables

```sql
-- Create if not exists
CREATE TABLE IF NOT EXISTS labeling_queue (
    id INTEGER PRIMARY KEY,
    prediction_id INTEGER,
    image_path VARCHAR(512),
    confidence_score FLOAT,
    status VARCHAR(20) DEFAULT 'pending',
    created_at DATETIME,
    labeled_at DATETIME,
    human_label VARCHAR(100),
    reviewer_notes TEXT,
    flagged_reason VARCHAR(100)
);

CREATE TABLE IF NOT EXISTS reviewed_labels (
    id INTEGER PRIMARY KEY,
    image_id VARCHAR(255) UNIQUE,
    image_path VARCHAR(512),
    label VARCHAR(100),
    confidence FLOAT,
    reviewer VARCHAR(100),
    created_at DATETIME,
    used_for_training BOOLEAN DEFAULT FALSE
);
```

---

## Testing Checklist

### ✅ Unit Tests to Create

```python
# tests/test_retraining.py
- test_should_retrain_with_drift()
- test_should_retrain_with_labels()
- test_retraining_api_endpoint()

# tests/test_labeling.py
- test_enqueue_for_labeling()
- test_submit_label()
- test_export_labels()

# tests/test_active_learning.py
- test_uncertainty_sampling()
- test_low_confidence_flagging()
```

### ✅ Integration Tests

```bash
# Full pipeline test
1. Generate predictions with YOLO
2. Flag low-confidence items
3. Submit labels via API
4. Export labels for training
5. Trigger retraining
6. Verify new model registered
```

---

## Implementation Priority

**Must Have (Week 1):**
1. Task 1.1 - Retraining API
2. Task 1.2 - Database Models
3. Task 2.1 - Labeling UI
4. Task 3.1 - Retraining Router

**Should Have (Week 2):**
5. Task 1.3 - Logger Extensions
6. Task 2.2 - Retraining Widget
7. Task 3.2 - Labeling Router

**Nice to Have (Week 3):**
8. Task 2.3 - Drift Dashboard
9. Task 4.1/4.2 - DB migrations
10. Testing & documentation

---

## Expected Timeline

| Phase | Tasks | Time | Priority |
|-------|-------|------|----------|
| 1 | Retraining + Labels + API | 2-3 hrs | 🔴 CRITICAL |
| 2 | Labeling UI + Widgets | 1-2 hrs | 🟠 HIGH |
| 3 | API Routers | 1 hr | 🟠 HIGH |
| 4 | Database | 30 min | 🟡 MEDIUM |
| Testing | Unit + Integration | 1 hr | 🟡 MEDIUM |

**Total: 5-7 hours to 100% Portfolio Quality**

---

## Success Criteria

```
✅ Active learning pipeline: End-to-end working
✅ Manual labeling UI: Can label uncertain predictions
✅ Retraining trigger: Automatic when conditions met
✅ Drift dashboard: Real-time drift visualization
✅ Full integration: Camera → Model → Retrain → Deploy
✅ Demo ready: Can show full pipeline in 10 minutes
```

When all criteria met → **Ready for portfolio/interviews!**
