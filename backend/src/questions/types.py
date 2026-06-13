import json
from datetime import datetime
from typing import Annotated, Any, Literal, Optional

from pydantic import BaseModel, ConfigDict
from pydantic import Field as PydanticField
from sqlalchemy import Column, Text, UniqueConstraint
from sqlmodel import Field, Relationship, SQLModel

# NOTE: This module was made with AI

# ---------------------------------------------------------------------------
# enumerate
# ---------------------------------------------------------------------------

Visibility = Literal["private", "public"]

QuestionType = Literal[
    "multiple_choice",
    "short_answer",
    "long_answer",
]

Difficulty = Literal[
    "easy",
    "medium",
    "hard",
]

PaperSource = Literal[
    "hsc",
    "trial",
    "internal",
    "practice",
    "custom",
]

CourseLevel = Literal[
    "standard",
    "advanced",
    "extension_1",
    "extension_2",
]


class StrictBaseModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class SyllabusPoint(StrictBaseModel):
    syllabus_id: str = PydanticField(
        description="Identifier for the syllabus, e.g. 'hsc-physics-2025'."
    )
    point_code: str = PydanticField(
        description="Dot-point code within the syllabus, e.g. 'PH12-4.1.3'."
    )
    label: str | None = PydanticField(
        default=None,
        description="Human-readable label for the syllabus point.",
    )


class TextBlock(StrictBaseModel):
    kind: Literal["text"]
    text: str = PydanticField(min_length=1)


class ImageBlock(StrictBaseModel):
    kind: Literal["image"]
    url: str
    mime_type: str | None = None
    alt: str | None = None
    width: int | None = PydanticField(default=None, ge=1)
    height: int | None = PydanticField(default=None, ge=1)


class TableBlock(StrictBaseModel):
    kind: Literal["table"]
    html: str = PydanticField(min_length=1)


ContentBlock = Annotated[
    TextBlock | ImageBlock | TableBlock,
    PydanticField(discriminator="kind"),
]


class ChoiceOption(StrictBaseModel):
    label: str = PydanticField(
        pattern=r"^[A-Z]$",
        description="Option letter, e.g. A, B, C, D.",
    )
    content: list[ContentBlock] = PydanticField(min_length=1)


class QuestionPart(StrictBaseModel):
    label: str = PydanticField(
        pattern=r"^[a-z]+$",
        description="Part label, e.g. 'a', 'b', 'ii'.",
    )
    stimulus: list[ContentBlock] | None = PydanticField(
        default=None,
        description="Stimulus material for this sub-part.",
    )
    content: list[ContentBlock] = PydanticField(min_length=1)
    marks: int | None = PydanticField(default=None, ge=0)
    is_independent: bool | None = PydanticField(
        default=None,
        description="True if this part stands alone from the previous part's context.",
    )


# ---------------------------------------------------------------------------
# JSON column type adapter for SQLite
# ---------------------------------------------------------------------------


class JSONEncodedList(list):
    """Marker so SQLAlchemy knows to serialise as JSON text."""


# ---------------------------------------------------------------------------
# Junction / link tables (SQLModel with table=True)
# ---------------------------------------------------------------------------


class PaperOutcome(SQLModel, table=True):
    __tablename__ = "paper_outcomes"

    paper_id: str = Field(foreign_key="papers.id", primary_key=True)
    outcome_code: str = Field(primary_key=True)


class QuestionOutcome(SQLModel, table=True):
    __tablename__ = "question_outcomes"

    question_id: str = Field(foreign_key="questions.id", primary_key=True)
    outcome_code: str = Field(primary_key=True)


class QuestionSyllabusPointDB(SQLModel, table=True):
    """Syllabus dot-point references stored relationally for querying."""

    __tablename__ = "question_syllabus_points"

    id: int | None = Field(default=None, primary_key=True)
    question_id: str = Field(foreign_key="questions.id")
    syllabus_id: str
    point_code: str
    label: str | None = None


# ---------------------------------------------------------------------------
# Main table models
# ---------------------------------------------------------------------------


class PaperDB(SQLModel, table=True):
    """The `papers` table."""

    __tablename__ = "papers"

    id: str = Field(primary_key=True)
    title: str
    author_id: str
    subject: str
    syllabus_id: str | None = None
    year: int | None = None
    source: str | None = None  # PaperSource
    school: str | None = None
    course_level: str | None = None  # CourseLevel
    visibility: str = Field(default="private")  # Visibility
    question_count: int = Field(default=0)
    total_marks: int = Field(default=0)
    duration_minutes: int | None = None
    topics_json: str | None = Field(default=None, sa_column=Column(Text))
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    # Relationships
    questions: list["QuestionDB"] = Relationship(back_populates="paper")
    outcomes: list["PaperOutcome"] = Relationship()

    # --- JSON helpers ---

    def get_topics(self) -> list[str]:
        if not self.topics_json:
            return []
        return json.loads(self.topics_json)

    def set_topics(self, topics: list[str] | None) -> None:
        if topics is None:
            self.topics_json = None
        else:
            self.topics_json = json.dumps(topics)


class QuestionDB(SQLModel, table=True):
    """The `questions` table."""

    __tablename__ = "questions"
    __table_args__ = (UniqueConstraint("paper_id", "number"),)

    id: str = Field(primary_key=True)
    paper_id: str = Field(foreign_key="papers.id")
    author_id: str
    number: int
    type: str  # QuestionType
    marks: int = Field(default=0)

    # Complex nested data stored as JSON text
    stimulus_json: str | None = Field(default=None, sa_column=Column(Text))
    content_json: str | None = Field(default=None, sa_column=Column(Text))
    parts_json: str | None = Field(default=None, sa_column=Column(Text))
    options_json: str | None = Field(default=None, sa_column=Column(Text))
    topics_json: str | None = Field(default=None, sa_column=Column(Text))

    answer: str | None = None
    difficulty: str | None = None  # Difficulty

    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    # Relationships
    paper: Optional[PaperDB] = Relationship(back_populates="questions")
    outcomes: list["QuestionOutcome"] = Relationship()
    syllabus_points: list["QuestionSyllabusPointDB"] = Relationship()

    # --- JSON helpers ---

    def get_stimulus(self) -> list[ContentBlock] | None:
        if not self.stimulus_json:
            return None
        return _parse_content_blocks(self.stimulus_json)

    def set_stimulus(self, blocks: list[ContentBlock] | None) -> None:
        self.stimulus_json = _dump_blocks(blocks)

    def get_content(self) -> list[ContentBlock] | None:
        if not self.content_json:
            return None
        return _parse_content_blocks(self.content_json)

    def set_content(self, blocks: list[ContentBlock] | None) -> None:
        self.content_json = _dump_blocks(blocks)

    def get_parts(self) -> list[QuestionPart] | None:
        if not self.parts_json:
            return None
        raw = json.loads(self.parts_json)
        return [QuestionPart.model_validate(p) for p in raw]

    def set_parts(self, parts: list[QuestionPart] | None) -> None:
        if parts is None:
            self.parts_json = None
        else:
            self.parts_json = json.dumps([p.model_dump() for p in parts])

    def get_options(self) -> list[ChoiceOption] | None:
        if not self.options_json:
            return None
        raw = json.loads(self.options_json)
        return [ChoiceOption.model_validate(o) for o in raw]

    def set_options(self, options: list[ChoiceOption] | None) -> None:
        if options is None:
            self.options_json = None
        else:
            self.options_json = json.dumps([o.model_dump() for o in options])

    def get_topics(self) -> list[str]:
        if not self.topics_json:
            return []
        return json.loads(self.topics_json)

    def set_topics(self, topics: list[str] | None) -> None:
        if topics is None:
            self.topics_json = None
        else:
            self.topics_json = json.dumps(topics)


# ---------------------------------------------------------------------------
# API response models (not tables — used for serialization)
# ---------------------------------------------------------------------------


class QuestionRead(BaseModel):
    """Full question as returned by the API."""

    model_config = ConfigDict(from_attributes=True)

    id: str
    paper_id: str
    author_id: str
    number: int
    type: QuestionType
    marks: int
    stimulus: list[ContentBlock] | None = None
    content: list[ContentBlock] | None = None
    parts: list[QuestionPart] | None = None
    options: list[ChoiceOption] | None = None
    answer: str | None = None
    topics: list[str] = []
    outcomes: list[str] = []
    syllabus_points: list[SyllabusPoint] = []
    difficulty: Difficulty | None = None
    created_at: datetime
    updated_at: datetime


class PaperMetaRead(BaseModel):
    """Paper metadata without questions."""

    model_config = ConfigDict(from_attributes=True)

    id: str
    title: str
    author_id: str
    subject: str
    year: int | None = None
    source: PaperSource | None = None
    school: str | None = None
    course_level: CourseLevel | None = None
    topics: list[str] = []
    outcomes: list[str] = []
    visibility: Visibility = "private"
    question_count: int = 0
    total_marks: int = 0
    duration_minutes: int | None = None
    created_at: datetime
    updated_at: datetime


class PaperRead(PaperMetaRead):
    """Full paper with questions included."""

    syllabus_id: str | None = None
    questions: list[QuestionRead] = []


# ---------------------------------------------------------------------------
# Request/create models
# ---------------------------------------------------------------------------


class PaperCreate(BaseModel):
    title: str = PydanticField(min_length=1)
    subject: str
    syllabus_id: str | None = None
    year: int | None = PydanticField(default=None, ge=2000)
    source: PaperSource | None = None
    school: str | None = None
    course_level: CourseLevel | None = None
    topics: list[str] | None = None
    outcomes: list[str] | None = None
    visibility: Visibility = "private"
    duration_minutes: int | None = PydanticField(default=None, ge=0)


class PaperUpdate(BaseModel):
    title: str | None = PydanticField(default=None, min_length=1)
    subject: str | None = None
    syllabus_id: str | None = None
    year: int | None = PydanticField(default=None, ge=2000)
    source: PaperSource | None = None
    school: str | None = None
    course_level: CourseLevel | None = None
    topics: list[str] | None = None
    outcomes: list[str] | None = None
    visibility: Visibility | None = None
    duration_minutes: int | None = PydanticField(default=None, ge=0)


class QuestionCreate(BaseModel):
    type: QuestionType
    marks: int = PydanticField(ge=0)
    stimulus: list[ContentBlock] | None = None
    content: list[ContentBlock] | None = None
    parts: list[QuestionPart] | None = None
    options: list[ChoiceOption] | None = None
    answer: str | None = None
    topics: list[str] | None = None
    outcomes: list[str] | None = None
    syllabus_points: list[SyllabusPoint] | None = None
    difficulty: Difficulty | None = None


class QuestionUpdate(BaseModel):
    type: QuestionType | None = None
    marks: int | None = PydanticField(default=None, ge=0)
    stimulus: list[ContentBlock] | None = None
    content: list[ContentBlock] | None = None
    parts: list[QuestionPart] | None = None
    options: list[ChoiceOption] | None = None
    answer: str | None = None
    topics: list[str] | None = None
    outcomes: list[str] | None = None
    syllabus_points: list[SyllabusPoint] | None = None
    difficulty: Difficulty | None = None


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _parse_content_blocks(raw_json: str) -> list[Any]:
    """Parse a JSON string into a list of ContentBlock models."""
    data = json.loads(raw_json)
    blocks: list[Any] = []
    for item in data:
        kind = item.get("kind")
        if kind == "text":
            blocks.append(TextBlock.model_validate(item))
        elif kind == "image":
            blocks.append(ImageBlock.model_validate(item))
        elif kind == "table":
            blocks.append(TableBlock.model_validate(item))
    return blocks


def _dump_blocks(blocks: list[Any] | None) -> str | None:
    """Serialize a list of ContentBlock models to JSON string."""
    if blocks is None:
        return None
    return json.dumps([b.model_dump() for b in blocks])


def question_db_to_read(q: QuestionDB) -> QuestionRead:
    """Convert a QuestionDB row into a QuestionRead API model."""
    return QuestionRead(
        id=q.id,
        paper_id=q.paper_id,
        author_id=q.author_id,
        number=q.number,
        type=q.type,  # type: ignore[arg-type]
        marks=q.marks,
        stimulus=q.get_stimulus(),
        content=q.get_content(),
        parts=q.get_parts(),
        options=q.get_options(),
        answer=q.answer,
        topics=q.get_topics(),
        outcomes=[o.outcome_code for o in q.outcomes],
        syllabus_points=[
            SyllabusPoint(
                syllabus_id=sp.syllabus_id,
                point_code=sp.point_code,
                label=sp.label,
            )
            for sp in q.syllabus_points
        ],
        difficulty=q.difficulty,  # type: ignore[arg-type]
        created_at=q.created_at,
        updated_at=q.updated_at,
    )


def paper_db_to_meta_read(p: PaperDB) -> PaperMetaRead:
    """Convert a PaperDB row into a PaperMetaRead API model."""
    return PaperMetaRead(
        id=p.id,
        title=p.title,
        author_id=p.author_id,
        subject=p.subject,
        year=p.year,
        source=p.source,  # type: ignore[arg-type]
        school=p.school,
        course_level=p.course_level,  # type: ignore[arg-type]
        topics=p.get_topics(),
        outcomes=[o.outcome_code for o in p.outcomes],
        visibility=p.visibility,  # type: ignore[arg-type]
        question_count=p.question_count,
        total_marks=p.total_marks,
        duration_minutes=p.duration_minutes,
        created_at=p.created_at,
        updated_at=p.updated_at,
    )


def paper_db_to_read(p: PaperDB) -> PaperRead:
    """Convert a PaperDB row into a full PaperRead API model."""
    return PaperRead(
        id=p.id,
        title=p.title,
        author_id=p.author_id,
        subject=p.subject,
        syllabus_id=p.syllabus_id,
        year=p.year,
        source=p.source,  # type: ignore[arg-type]
        school=p.school,
        course_level=p.course_level,  # type: ignore[arg-type]
        topics=p.get_topics(),
        outcomes=[o.outcome_code for o in p.outcomes],
        visibility=p.visibility,  # type: ignore[arg-type]
        question_count=p.question_count,
        total_marks=p.total_marks,
        duration_minutes=p.duration_minutes,
        created_at=p.created_at,
        updated_at=p.updated_at,
        questions=[question_db_to_read(q) for q in p.questions],
    )