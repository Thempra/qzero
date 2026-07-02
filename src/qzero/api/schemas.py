"""Pydantic schemas for QZero REST API."""

from pydantic import BaseModel
from typing import Optional, List


class AnalyzeRequest(BaseModel):
    method: Optional[str] = "best"


class Alert(BaseModel):
    timestamp: str
    severity: str
    src_ip: str
    dst_ip: str
    protocol: str
    anomaly_score: float
    message: str


class StatusResponse(BaseModel):
    status: str
    message: str


class AnalyzeResponse(BaseModel):
    status: str
    filename: Optional[str] = None
    total_packets: Optional[int] = None
    features_extracted: Optional[int] = None
    method: Optional[str] = None
    results: Optional[dict] = None
    timestamp: Optional[str] = None
    message: Optional[str] = None
