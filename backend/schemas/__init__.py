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
]

