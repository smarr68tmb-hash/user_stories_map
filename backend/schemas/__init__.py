"""
Pydantic schemas for API validation
"""
from .user import UserCreate, UserResponse, Token, TokenRefreshRequest, TokenData
from .story import (
    StoryCreate, 
    StoryUpdate, 
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
    ProjectResponse
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

