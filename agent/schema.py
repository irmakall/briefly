"""The bulletin structure the model must fill in (FR-19).

Prices, rates and the date are NOT here: they come straight
from tool results and the clock (FR-21), so the model can't get them wrong.
"""
from pydantic import BaseModel, Field


class TechStory(BaseModel):
    """One technology story."""

    title: str = Field(description="Headline translated into Turkish.")
    source: str = Field(description="Original source name exactly as in the tool result, e.g. 'The Verge'.")
    why_it_matters: str = Field(description="1-2 sentences in Turkish on why this matters, based on the summary.")
    url: str = Field(description="The article url copied exactly from the get_tech_news result.")


class FinanceStory(BaseModel):
    """One company / finance news item."""

    company: str = Field(description="Company name as given in the get_financial_news result.")
    title: str = Field(description="Headline translated into Turkish.")
    comment: str = Field(description="A short comment in Turkish (1-2 sentences), based on the description.")
    url: str = Field(description="The article url copied exactly from the get_financial_news result.")


class Bulletin(BaseModel):
    """The full bulletin."""

    intro: str = Field(description="A short, friendly intro in Turkish (1-2 sentences).")
    tech: list[TechStory] = Field(description="The 5 most important tech stories.")
    finance_news: list[FinanceStory] = Field(description="Up to 3 company / finance news items. Empty list if there are none.")
