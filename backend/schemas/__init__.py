"""
Pydantic schemas for API validation
"""
from .user import UserCreate, UserResponse, Token, TokenRefreshRequest, TokenData
from .story import (
    StoryCreate, 
    StoryUpdate,
    StoryStatusUpdate,
    StoryMove, 
    StoryResponse,
    AIImproveRequest,
    AIImproveResponse,
    AIBulkImproveRequest,
    AIBulkImproveResponse
)
from .project import (
    RequirementsInput,
    EnhancementRequest,
    EnhancementResponse,
    TaskResponse,
    ActivityResponse,
    ReleaseResponse,
    ProjectResponse,
    ActivityCreate,
    ActivityUpdate,
    TaskCreate,
    TaskUpdate,
    TaskMove,
    ProjectUpdate,
)
from .analysis import (
    IssueSeverity,
    IssueType,
    ValidationIssue,
    ValidationResult,
    SimilarStory,
    SimilarityGroup,
    ConflictType,
    StoryConflict,
    SimilarityResult,
    FullAnalysisResult,
    AnalysisRequest
)
from .epic import (
    EpicCreate,
    EpicUpdate,
    EpicResponse,
    EpicWithStoriesResponse,
    EpicGenerateRequest,
    EpicGenerateResponse
)

__all__ = [
    # User schemas
    "UserCreate",
    "UserResponse",
    "Token",
    "TokenRefreshRequest",
    "TokenData",
    # Story schemas
    "StoryCreate",
    "StoryUpdate",
    "StoryStatusUpdate",
    "StoryMove",
    "StoryResponse",
    "AIImproveRequest",
    "AIImproveResponse",
    "AIBulkImproveRequest",
    "AIBulkImproveResponse",
    # Project schemas
    "RequirementsInput",
    "EnhancementRequest",
    "EnhancementResponse",
    "TaskResponse",
    "ActivityResponse",
    "ReleaseResponse",
    "ProjectResponse",
    "ProjectUpdate",
    "ActivityCreate",
    "ActivityUpdate",
    "TaskCreate",
    "TaskUpdate",
    "TaskMove",
    # Analysis schemas
    "IssueSeverity",
    "IssueType",
    "ValidationIssue",
    "ValidationResult",
    "SimilarStory",
    "SimilarityGroup",
    "ConflictType",
    "StoryConflict",
    "SimilarityResult",
    "FullAnalysisResult",
    "AnalysisRequest",
    # Epic schemas
    "EpicCreate",
    "EpicUpdate",
    "EpicResponse",
    "EpicWithStoriesResponse",
    "EpicGenerateRequest",
    "EpicGenerateResponse",
]

