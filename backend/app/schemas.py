from pydantic import BaseModel, Field, HttpUrl


class AnalyzeRequest(BaseModel):
    repository_url: HttpUrl


class Finding(BaseModel):
    title: str
    severity: str = Field(pattern="^(critical|high|medium|low|info)$")
    file: str = "Not specified"
    line: int | None = None
    evidence: str = ""
    description: str
    recommendation: str


class AnalysisReport(BaseModel):
    report_id: str
    repository_url: str
    repository_name: str
    summary: str
    findings: list[Finding]
    strengths: list[str] = []
    limitations: list[str] = []
    generated_at: str
