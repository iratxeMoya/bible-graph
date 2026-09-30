"""Modelos de respuesta de la API."""

from typing import Literal

from pydantic import BaseModel


class Node(BaseModel):
    id: int
    ref: str
    label: str
    book: str
    testament: Literal["AT", "NT"]
    text: str
    is_seed: bool
    hop: int


class Edge(BaseModel):
    source: int
    target: int
    weight: int
    target_end_id: int | None
    target_label: str


class SearchResponse(BaseModel):
    query: str
    total_matches: int
    truncated: bool
    nodes: list[Node]
    edges: list[Edge]


class Verse(BaseModel):
    id: int
    ref: str
    text: str


class PassageResponse(BaseModel):
    ref: str
    verses: list[Verse]
