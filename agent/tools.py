import httpx
from bs4 import BeautifulSoup
from langchain.tools import BaseTool
from typing import Type, Optional
from pydantic import BaseModel, Field


class SearchInput(BaseModel):
    query: str = Field(description="Search query for web search")
    max_results: int = Field(default=5, description="Maximum number of results to return")


class WebSearchTool(BaseTool):
    name: str = "web_search"
    description: str = "Search the web for current information, tutorials, documentation, or explanations. Use when you need up-to-date info or don't know the answer."
    args_schema: Type[BaseModel] = SearchInput

    def _run(self, query: str, max_results: int = 5) -> str:
        return self._search_duckduckgo(query, max_results)

    async def _arun(self, query: str, max_results: int = 5) -> str:
        return self._search_duckduckgo(query, max_results)

    def _search_duckduckgo(self, query: str, max_results: int) -> str:
        url = "https://html.duckduckgo.com/html/"
        params = {"q": query}
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        }

        try:
            with httpx.Client(timeout=10.0) as client:
                resp = client.post(url, data=params, headers=headers)
                resp.raise_for_status()
        except Exception as e:
            return f"Search failed: {e}"

        soup = BeautifulSoup(resp.text, "lxml")
        results = []

        for result in soup.select(".result__snippet")[:max_results]:
            text = result.get_text(strip=True)
            if text:
                results.append(text)

        if not results:
            for result in soup.select(".web-result-description")[:max_results]:
                text = result.get_text(strip=True)
                if text:
                    results.append(text)

        if not results:
            return "No results found."

        formatted = "\n\n".join(
            [f"[{i+1}] {r}" for i, r in enumerate(results)]
        )
        return f"Search results for '{query}':\n\n{formatted}"


class ExtractContentInput(BaseModel):
    url: str = Field(description="URL to extract content from")


class ExtractContentTool(BaseTool):
    name: str = "extract_content"
    description: str = "Extract readable text content from a specific URL. Use when search results mention a specific page you want to read fully."
    args_schema: Type[BaseModel] = ExtractContentInput

    def _run(self, url: str) -> str:
        return self._extract(url)

    async def _arun(self, url: str) -> str:
        return self._extract(url)

    def _extract(self, url: str) -> str:
        headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
        try:
            with httpx.Client(timeout=10.0, follow_redirects=True) as client:
                resp = client.get(url, headers=headers)
                resp.raise_for_status()
        except Exception as e:
            return f"Failed to fetch {url}: {e}"

        soup = BeautifulSoup(resp.text, "lxml")

        for tag in soup(["script", "style", "nav", "footer", "header", "aside", "noscript"]):
            tag.decompose()

        text = soup.get_text(separator="\n", strip=True)
        lines = [line.strip() for line in text.split("\n") if line.strip()]
        content = "\n".join(lines[:200])

        return f"Content from {url}:\n\n{content[:8000]}"