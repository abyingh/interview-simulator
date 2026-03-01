from pydantic import BaseModel


class InterviewerResponseSchema(BaseModel):
    message: str
    is_interview_complete: bool


class ExtractedActionItem(BaseModel):
    action: str
    quote: str


class ExtractedActionsSchema(BaseModel):
    actions: list[ExtractedActionItem]


class RoleListSchema(BaseModel):
    roles: list[str]


class ThemeSummarySchema(BaseModel):
    theme_name: str
    summary: str
    key_quotes: list[str]
